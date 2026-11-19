# Design Document

> Diseño implementation-ready de la Etapa 4 (Opción A) en el formato nativo de Kiro. Las
> decisiones técnicas se basan en el código heredado real de la Etapa 3 de Kiro (FastAPI +
> `sqlite3` directo sin ORM; config por constantes en `app/config.py` con `DB_PATH`;
> `txn.financial_transaction` con `BEGIN IMMEDIATE`; `money.py` decimal-safe; `audit.py`
> HMAC+ancla; `crypto.py` AES-256-GCM). No se asume SQLAlchemy, broker, vendor cloud, API FX ni
> event-store externo. No se copian soluciones de otras herramientas SDD.

## Overview

## Visión general

La Etapa 4 añade cinco capacidades —multidivisa, conversión FX exacta, Event Sourcing del dominio
monetario, CQRS y control de concurrencia (idempotencia + versión optimista)— **sobre** la
arquitectura por capas heredada, de forma **aditiva** salvo donde el contrato de dinero
multidivisa obliga a adaptar (identidad de cuenta, moneda, headers de comando).

Principios rectores:

1. **Un solo punto de verdad transaccional.** Todo comando financiero ya ocurre dentro de
   `txn.financial_transaction` (`BEGIN IMMEDIATE`, único escritor). Evento(s) de dominio,
   actualización de proyección(es), auditoría HMAC, registro de idempotencia y bump de versión de
   cuenta se escriben **dentro de esa misma transacción** (DK-03, D-11). Atomicidad sin un segundo
   mecanismo de coordinación.
2. **Eventos ≠ auditoría.** El almacén de eventos de dominio (`domain_event`) es la fuente de
   verdad del estado; la bitácora `audit_log` (HMAC) es evidencia de cumplimiento. Coexisten,
   nunca se sustituyen (D-05).
3. **CQRS síncrono.** Las proyecciones (`account_projection`, historial) se actualizan en la misma
   transacción que emite los eventos; la reconstrucción reaplica eventos de forma determinista
   (D-06). Fail-closed ante inconsistencia.
4. **Exactitud monetaria.** Tasas racionales fijas (`Fraction`), `Decimal`/centavos por moneda,
   `ROUND_HALF_UP` una sola vez al final; sin floats financieros (D-03).
5. **Concurrencia explícita.** `Idempotency-Key` UUID y versión de cuenta esperada; replay
   idempotente se evalúa **antes** que la versión (DK-04, D-13/D-14).
6. **Reutilización primero (DK-05/DK-03).** Se reutilizan `money`, `txn`, `audit`, `crypto`,
   `limit_service`, el scheduler y los flujos ACH/recurrentes/MFA, adaptándolos a moneda en lugar
   de reescribirlos.
7. **Discontinuidad experimental honesta (DK-01).** La fixture de la Etapa 4 es un reset
   declarado, no una conversión; la verificación de migración/rollback es estructural.

## Architecture

### Integración con la arquitectura existente

```
Navegador ──HTTPS──> Nginx (TLS; assets; proxy /api) ──HTTP interno──> FastAPI
                                                                          │
  routers (accounts, transfers, conversions[NUEVO], ach, beneficiaries,   │
           recurring, limits, audit)                                       │
                                        │  Idempotency-Key + Expected-Version (middleware/deps)
                                        ▼
  command handlers (service / ach_service / recurring_service / conversion_service[NUEVO])
                                        │
                        txn.financial_transaction(conn)  (BEGIN IMMEDIATE, único escritor)
             ┌──────────────────────────┼───────────────────────────────────────────────┐
             ▼              ▼            ▼              ▼                 ▼                ▼
       domain_event   account_     account_        audit_log        idempotency_      (saldo/
       (append-only)  projection   version (bump)  (HMAC+ancla)     key (registro)    historial)
                                        │
                                        ▼
  query side (read models): list_accounts / history / limits derivan de account_projection
```

### Reglas de oposición clave (preservadas o adaptadas)

- **Preservado:** `BEGIN IMMEDIATE`, `money.py` (centavos/`Decimal`/2 decimales), `audit.py`
  (HMAC+ancla), `crypto.py` (AES-256-GCM), scheduler único, cifrado de `beneficiary_snapshot`.
- **Adaptado:** la tabla `account` gana `currency` y `public_id`; se relaja
  `UNIQUE(customer_id, kind)` a `UNIQUE(customer_id, kind, currency)`; las APIs de cuenta/historial
  exponen moneda e identificador público; límites/MFA pasan a equivalente USD.

## Components and Interfaces

### 1. Modelo de datos (esquema SQLite, migración aditiva en `db.migrate`)

Evolución aditiva, idempotente y transaccional (R15, DK-03), siguiendo el patrón heredado
(`_column_exists` antes de `ALTER`, DDL por sentencia dentro de `BEGIN`, `CREATE ... IF NOT
EXISTS`). **No** se eliminan tablas/columnas heredadas.

#### 1.1 `account` (extensión)

```
ALTER TABLE account ADD COLUMN currency  TEXT NOT NULL DEFAULT 'USD';   -- ISO-4217 {USD,EUR,GBP}
ALTER TABLE account ADD COLUMN public_id TEXT;                          -- CHK-1001, etc. (inmutable)
ALTER TABLE account ADD COLUMN version   INTEGER NOT NULL DEFAULT 0;    -- concurrencia optimista
-- índice de unicidad del id público; unicidad de negocio por (customer_id, kind, currency)
CREATE UNIQUE INDEX IF NOT EXISTS ux_account_public_id ON account (public_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_account_kind_ccy  ON account (customer_id, kind, currency);
```

- La identidad **interna** (`account.id` UUID) se preserva (DK-02). `public_id` y `currency` son
  aditivos. `version` arranca en 0 y se incrementa por evento aplicado a la cuenta (D-09/D-14).
- La restricción heredada `UNIQUE(customer_id, kind)` se sustituye funcionalmente por el índice
  `(customer_id, kind, currency)` (la cuenta checking USD y una futura checking EUR no colisionan).

#### 1.2 `domain_event` (NUEVO — almacén de eventos append-only, D-05)

```
CREATE TABLE IF NOT EXISTS domain_event (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,  -- orden total
    event_id       TEXT NOT NULL UNIQUE,               -- UUID del evento
    event_type     TEXT NOT NULL,                      -- catálogo §5
    aggregate_id   TEXT NOT NULL,                       -- account.id afectado (una fila por cuenta)
    aggregate_ver  INTEGER NOT NULL,                    -- versión resultante de esa cuenta (+1)
    operation_id   TEXT NOT NULL,                       -- agrupa un evento compuesto (misma op)
    currency       TEXT NOT NULL,
    amount_minor   INTEGER NOT NULL,                    -- delta en unidades menores (con signo)
    payload        TEXT NOT NULL,                       -- JSON canónico NO sensible
    occurred_at    TEXT NOT NULL,                       -- ISO-8601 UTC
    UNIQUE (aggregate_id, aggregate_ver)                -- no dos eventos con la misma versión
);
CREATE INDEX IF NOT EXISTS idx_event_aggregate ON domain_event (aggregate_id, aggregate_ver);
CREATE INDEX IF NOT EXISTS idx_event_operation ON domain_event (operation_id);
-- Triggers append-only (igual patrón que audit_log): abortan UPDATE/DELETE ordinarios.
```

- Un evento **compuesto** (p. ej. una conversión USD→EUR afecta a dos cuentas) se escribe como
  **varias filas** que comparten `operation_id`; cada fila incrementa la versión de **su**
  `aggregate_id` en +1 (D-09). `UNIQUE(aggregate_id, aggregate_ver)` impide aplicar dos veces la
  misma versión (anti-duplicado).
- Separado de `audit_log` físicamente y en propósito (D-05, R6.3).

#### 1.3 `account_projection` (NUEVO — read model CQRS, D-06)

```
CREATE TABLE IF NOT EXISTS account_projection (
    account_id    TEXT PRIMARY KEY,   -- = account.id
    public_id     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    currency      TEXT NOT NULL,
    balance_minor INTEGER NOT NULL,   -- saldo proyectado
    version       INTEGER NOT NULL,   -- == account.version, consistencia verificable
    updated_at    TEXT NOT NULL
);
```

- Fuente autoritativa de las **consultas** de saldo. Se actualiza en la **misma** transacción que
  `domain_event` (D-06). La reconstrucción (`rebuild_projections`) borra y reaplica todos los
  eventos por `aggregate_id`/`aggregate_ver` de forma determinista.
- Invariante de consistencia: `account_projection.version == account.version` y
  `balance_minor == Σ(amount_minor de eventos de esa cuenta)`. Si no cuadra → fail-closed.

#### 1.4 `idempotency_key` (NUEVO — D-13)

```
CREATE TABLE IF NOT EXISTS idempotency_key (
    id             TEXT PRIMARY KEY,   -- el UUID del header Idempotency-Key
    operation      TEXT NOT NULL,      -- 'internal_transfer' | 'conversion' | 'ach'
    request_hash   TEXT NOT NULL,      -- hash canónico del payload normalizado
    response_json  TEXT NOT NULL,      -- respuesta original serializada (para replay exacto)
    status_code    INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);
```

- Replay exacto: `id` existe y `request_hash` coincide → devolver `response_json`/`status_code`
  sin nuevos efectos (D-13-2). Reuse con payload distinto: `id` existe y `request_hash` difiere →
  **409 IDEMPOTENCY_CONFLICT** (D-13-3). El registro se inserta **dentro** de la transacción del
  comando (D-13-4, atomicidad).

#### 1.5 Tablas heredadas

`customer`, `transfer`, `beneficiary`, `recurring_schedule`, `schedule_execution`,
`transfer_limit`, `audit_log`, `audit_anchor` se **preservan**. `transfer` gana aditivamente
`currency TEXT` y, para FX, `to_currency`/`rate`/`dest_amount_minor` (o una tabla `conversion`
dedicada, ver §3). Las internas y ACH heredadas quedan clasificadas con `currency='USD'` en el
backfill de migración (consistente con la fixture D-02).

### 2. Módulo de dinero y FX (`money.py` extendido + `fx.py` NUEVO)

- **Reutiliza** `money.py` (parse/format/centavos/`Decimal`/`ROUND_HALF_UP`). Se parametriza por
  moneda (todas con 2 decimales en {USD, EUR, GBP}).
- **`fx.py` (NUEVO):** tabla de **tasas racionales fijas** como `fractions.Fraction` (exactas),
  p. ej. definidas respecto a USD. API interna:
  - `convert(amount_minor: int, src: str, dst: str) -> (dest_minor: int, rate: Fraction)`:
    calcula el destino como `Fraction` exacta y aplica `ROUND_HALF_UP` **una sola vez al final**
    al cuantizar a unidades menores (D-03). `src==dst` es identidad.
  - `usd_equivalent_minor(amount_minor: int, ccy: str) -> Decimal`: equivalente USD **sin
    redondear** (para el umbral MFA estricto `> 1,000.00`) y una variante redondeada para límites
    (D-07). El umbral MFA compara el valor **sin redondear** (D-07-2/R11.2).
- Sin servicio externo de tasas (SEED-4 §Decisiones; R20.2). Las tasas viven en `config.py` como
  constantes `Fraction` versionadas en el repo.

### 3. Comandos, eventos y servicios

#### 3.1 Patrón de comando (envoltura común, `command.py` NUEVO)

Una utilidad `with_command(conn, *, idempotency_key, operation, request, expected_versions)` que,
dentro de `financial_transaction`:

1. **Idempotencia primero (DK-04):** busca `idempotency_key`. Si existe y `request_hash` coincide
   → short-circuit con la respuesta original (sin efectos, sin tocar versión). Si difiere → 409.
2. **Versión optimista:** para cada cuenta afectada, compara `expected_version` con
   `account.version`; mismatch → **409 ACCOUNT_VERSION_CONFLICT** (D-14).
3. Ejecuta la lógica de negocio (validación de moneda, fondos, límites, MFA, débito/crédito).
4. **Efectos atómicos (D-11, DK-03):** `append_event` (una o varias filas con `operation_id`),
   `update_projection`, `audit.append_in_tx`, `insert_idempotency`, `bump account.version`.
5. COMMIT automático al salir sin excepción; cualquier fallo → ROLLBACK total (fail-closed).

`append_event` incrementa y usa `account.version+1` como `aggregate_ver`; `update_projection`
aplica el delta y fija `version` igual. La igualdad `projection.version == account.version` es la
guarda de consistencia (D-06-4).

#### 3.2 `conversion_service.py` (NUEVO — D-03, R4)

- Endpoint `POST /api/conversions` (router `conversions.py`). Entrada: `from_public_id`,
  `to_public_id`, `amount` (decimal-string de la moneda origen), `Idempotency-Key`,
  `Expected-Version` por cuenta.
- Valida monedas soportadas y que las cuentas pertenezcan al cliente mock; `fx.convert` calcula
  tasa y destino; debita origen (−amount_minor) y abona destino (+dest_minor); emite un evento
  **compuesto** (`CONVERSION_DEBITED` en la cuenta origen, `CONVERSION_CREDITED` en la destino,
  mismo `operation_id`), con la tasa y montos en el payload; respuesta expone tasa, origen,
  destino y los registros (R4-2).
- Límites/MFA en equivalente USD (reutiliza `limit_service` adaptado, §3.5).

#### 3.3 Transferencias internas (`service.py` adaptado — D-04, R5)

- Se exige **misma moneda** origen/destino; cross-currency → `CROSS_CURRENCY_NOT_ALLOWED` con
  mensaje que remite a `/api/conversions` (R5-2). El resto del flujo (MFA, fondos, estados,
  expiración perezosa) se preserva; el débito/crédito pasa por el patrón de comando (eventos +
  proyección + auditoría + idempotencia + versión).

#### 3.4 ACH y recurrentes (`ach_service.py`/`recurring_service.py` adaptados — D-08, R12)

- ACH: guardia **origen USD** (R12-1). Recurrentes internos: **misma moneda** (R12-2);
  recurrentes ACH: **USD** (R12-3). El ciclo ACH (`pending`→`settled`/`failed` con reembolso
  exactamente-una-vez) se preserva y ahora emite eventos de dominio en cada transición, sin doble
  débito/crédito (D-09, R7-2). El scheduler único se preserva (R19.3).

#### 3.5 Límites y MFA en equivalente USD (`limit_service.py` adaptado — D-07, R11)

- `check` y `daily_consumption` se calculan en **equivalente USD** (vía `fx.usd_equivalent_minor`)
  para todas las operaciones; límites `5,000.00` por operación y `10,000.00` diario (día UTC).
  Verificación autoritativa **dentro** de la transacción (sin TOCTOU, R11-3). MFA cuando el
  equivalente USD **sin redondear** es `> 1,000.00` (R11-2). Orden fondos → límites → MFA (R11-4).

### 4. Auditoría, cifrado y atomicidad (D-11, R13)

- `audit.py` y `crypto.py` se **reutilizan sin cambios de contrato**. Cada comando añade su
  entrada de auditoría dentro de la misma transacción (ya es el patrón de la Etapa 3). Nuevos
  `event_type` de auditoría para conversión (`CONVERSION_COMPLETED`/`REJECTED`) y para conflictos
  (idempotencia/versión rechazados se auditan como `rejected`, R13-4).
- Payloads de auditoría y de eventos NO contienen identificadores sensibles en claro ni material
  de clave (R13-4, R17.2).

### 5. Catálogo de eventos de dominio (§ referencia)

`ACCOUNT_OPENED` (seed), `INTERNAL_TRANSFER_DEBITED`/`CREDITED`, `CONVERSION_DEBITED`/`CREDITED`,
`ACH_DEBITED` (pending), `ACH_SETTLED`, `ACH_REFUNDED`, `RECURRING_DEBITED`/`CREDITED`. Cada uno
lleva `operation_id`, `aggregate_id`, `aggregate_ver`, `currency`, `amount_minor` (con signo) y
`payload` NO sensible. Las históricas de seed se emiten como pares debited/credited **sin** aplicar
saldo adicional (el saldo inicial es un `ACCOUNT_OPENED` con el valor de fixture; las históricas
son informativas y no re-mueven el balance — evita doble conteo, D-05/R6-4).

### 6. Frontend (React/TS — D-10, R14)

- `types.ts`: `Account` gana `public_id` y `currency`; montos siguen siendo `string`. Nuevos
  tipos de conversión (`ConversionRequest`/`Response` con `rate`, `from`, `to`).
- `AccountsPanel`: totales **separados por moneda**; total estimado USD etiquetado "estimado
  (solo visualización)" (R14-1/2). Nuevo `ConversionForm` que muestra tasa, origen y destino.
- Cliente API: añade los headers `Idempotency-Key` (UUID generado en cliente) y `Expected-Version`
  a transferencias/conversiones/ACH; maneja 409 de idempotencia/versión mostrando un mensaje de
  recarga. Formateo por moneda con 2 decimales (R14-3/4). Flujos heredados preservados (R14-5).

### 7. Migración y fixture (D-05, DK-01, R15)

- `db.migrate` (extendido): añade columnas de `account`, crea `domain_event`,
  `account_projection`, `idempotency_key` y triggers append-only; backfill `currency='USD'` para
  filas heredadas; todo en una transacción (rollback total ante fallo, R15-2).
- `seed` (Etapa 4): si la DB no tiene las cuentas D-02, siembra CHK-1001/SAV-2001/EUR-3001/GBP-4001
  con sus saldos y emite `ACCOUNT_OPENED` por cuenta; construye las proyecciones iniciales. **No**
  toca ni lee datos de la Etapa 3 (DK-01/R15-5). Idempotente.
- `rebuild_projections`: reconstrucción determinista desde `domain_event`; usada por un test de
  verificación y disponible como operación interna (R8-3, R15-3).

## Data Models

- **Account (interno):** `id` (UUID, interno, preservado), `customer_id`, `kind`, `display_name`,
  `balance_cents` (heredado, se mantiene sincronizado con la proyección), `currency`, `public_id`,
  `version`.
- **DomainEvent:** ver §1.2. **AccountProjection:** ver §1.3. **IdempotencyKey:** ver §1.4.
- **Conversion (expuesto):** `{ from: {public_id, amount, currency}, to: {public_id, amount,
  currency}, rate, status, event_ids }`.

## Error Handling

- Errores de dominio tipados con `code` estable → HTTP: `CROSS_CURRENCY_NOT_ALLOWED` (422),
  `UNSUPPORTED_CURRENCY` (422), `INSUFFICIENT_FUNDS` (422), `LIMIT_EXCEEDED_*` (422),
  `INVALID_MFA_CODE` (401/422 según el contrato heredado), `IDEMPOTENCY_KEY_REQUIRED`/`INVALID`
  (400), `IDEMPOTENCY_CONFLICT` (409), `ACCOUNT_VERSION_CONFLICT` (409), `PROJECTION_INCONSISTENT`
  (500, fail-closed). Todo rechazo es auditable y nunca aplica efectos parciales (R13-3).

## Testing Strategy

- **Unidad:** `fx` (tasas racionales, `ROUND_HALF_UP` una vez, conservación), `money` multidivisa,
  patrón de comando (idempotencia antes de versión).
- **Integración:** conversiones; internas misma-moneda y rechazo cross-currency; ACH/recurrentes
  con guardias de moneda; límites/MFA en equivalente USD; atomicidad compuesta
  evento+proyección+auditoría+idempotencia+versión y su fail-closed.
- **Event Sourcing/CQRS:** persistencia y replay; `rebuild_projections` determinista; sin doble
  conteo de seed/históricas; `UNIQUE(aggregate_id, aggregate_ver)` como anti-duplicado.
- **Concurrencia:** idempotencia bajo reintentos; versión optimista bajo solicitudes concurrentes
  (409); multiproceso SQLite lector/escritor con invariantes financieros y cadena de auditoría
  verificable.
- **Regresión:** suite heredada completa (Pytest) + Vitest + build; nunca se afirma verde sin
  observarlo (R16-2).
- **Carga:** arnés Locust heredado con DB sintética aislada; invariantes post-carga bajo
  multidivisa (R16-3).
- **Calidad:** SonarQube PRE y POST controlados por gates de investigador, comparables 1:1
  (R16-4).

## Design Decisions and Rationale

- **Eventos separados de auditoría (D-05):** dos tablas, dos propósitos. Reutilizar `audit_log`
  como event-store rompería D-05 y mezclaría cumplimiento con estado.
- **CQRS síncrono en la misma transacción (D-06/D-11):** SQLite de único escritor hace innecesario
  un bus asíncrono; la actualización síncrona garantiza consistencia inmediata y fail-closed sin
  dependencias externas (R20.2).
- **Idempotencia antes de versión (DK-04/D-13/D-14):** un replay exacto debe ser inocuo aunque la
  versión haya avanzado; comprobar versión primero rechazaría replays legítimos.
- **Reset de fixture, no conversión (DK-01):** declarar la discontinuidad mantiene la honestidad
  experimental; la preservación de datos se verifica estructuralmente (idempotencia, rollback,
  replay determinista), no por equivalencia de valor.
- **Preservar `balance_cents` heredado junto a la proyección:** evita romper código/llamadas
  heredadas mientras la proyección es la fuente autoritativa de lectura; ambos se mantienen
  sincronizados en la misma transacción y un test verifica su igualdad.

## Traceability (resumen)

Requisitos 1–3 → D-01/D-02/D-03/D-10 (§1, §2, §6). Requisito 4 → D-03 (§2, §3.2). Requisito 5 →
D-04 (§3.3). Requisitos 6–8 → D-05/D-06/D-09 (§1.2, §1.3, §3.1, §5, §7). Requisitos 9–10 →
D-13/D-14 (§1.4, §3.1). Requisitos 11–12 → D-07/D-08 (§3.4, §3.5). Requisito 13 → D-11 (§3.1, §4).
Requisito 14 → D-10 (§6). Requisitos 15–16 → D-05/D-12 (§7, Testing). NFR 17–20 → D-03/D-11/D-12
(transversal).
