# Diseño — Shift Bank (Etapa 2: Complejidad funcional y estado)

## Visión general

La Etapa 2 extiende la aplicación de la Etapa 1 (brownfield) añadiendo tres capacidades —ACH a
terceros, pagos recurrentes y límites dinámicos— sobre la misma arquitectura por capas de
FastAPI + `sqlite3` (sin ORM) y el frontend React + TypeScript con CSS puro. El diseño
**reutiliza** los pilares de la Etapa 1 (dinero en centavos `INTEGER`, decimal-string en API,
atomicidad con `BEGIN IMMEDIATE`, expiración/MFA perezosa) y los **extiende** sin reescritura.

Principios rectores (derivados del contrato y de D01–D06):

1. **Compatibilidad hacia atrás absoluta.** Las respuestas y estados de las transferencias
   internas de la Etapa 1 no cambian de forma (Requisito 15, D03, D05). Las extensiones son
   aditivas.
2. **Corrección financiera e idempotencia durable.** Todo cambio de saldo ocurre dentro de una
   **única** transacción SQLite que agrupa la lectura de saldo/límites, la validación, el débito
   y el avance de estado. El débito ACH, el reembolso y cada ocurrencia recurrente son
   **exactamente-una-vez** combinando (a) una **restricción UNIQUE durable** sobre la identidad
   de la ocurrencia/efecto y (b) guardas de transición de estado dentro de esa transacción
   (Requisitos 3, 4, 5, 10, 11; D07). La idempotencia reside en el modelo de datos, no en la
   suposición de un único proceso.
3. **Autoridad de negocio en el servicio.** Las nuevas reglas (validación ACH, límites, MFA,
   scheduler) viven en la capa de servicio; los routers solo traducen a HTTP.
4. **Determinismo verificable.** La lógica dependiente del tiempo (settlement, vencimiento de
   schedules) se separa del disparador temporal real y usa un **reloj inyectable** para pruebas
   deterministas (D02, Requisitos 4.2, 10.5).
5. **Alcance mínimo.** Sin ORM, sin dependencias innecesarias, sin funcionalidad de Etapa 3/4.

### Mapa de arquitectura (Etapa 2)

```
┌───────────────────────────────────────────────┐        ┌──────────────────────────────────────────────┐
│  Frontend (React + TS, Vanilla CSS)            │        │  Backend (FastAPI, Python, sqlite3)           │
│                                                │        │                                                │
│  Navegación por secciones (sin router nuevo):  │  HTTP  │  Routers:                                      │
│   ┌──────────┐ ┌───────────┐ ┌──────────────┐  │  JSON  │   accounts · transfers · ach · beneficiaries  │
│   │ Accounts │ │ Transfers │ │ ACH / Benef. │  │◀─────▶│   recurring · limits                           │
│   └──────────┘ └───────────┘ └──────────────┘  │ string │        │                                       │
│   ┌───────────┐ ┌───────────┐ ┌─────────────┐  │        │        ▼                                       │
│   │ Recurring │ │  Limits   │ │  History    │  │        │  Service (reglas de negocio)                   │
│   └───────────┘ └───────────┘ └─────────────┘  │        │   transfer_service · ach_service               │
│   api/client.ts (montos como string)           │        │   recurring_service · limit_service · mfa      │
└───────────────────────────────────────────────┘        │        │                                       │
                                                           │        ▼                                       │
                                        ┌──────────────────┤  Repository (SQL puro, transacciones atómicas) │
                                        │  Scheduler        │        │                                       │
                                        │  (background,     │        ▼                                       │
                                        │  reloj inyectable)│  SQLite (INTEGER centavos, ISO-8601 UTC)       │
                                        └───────────────────┤  + migración idempotente de esquema            │
                                                           └──────────────────────────────────────────────┘
```

### Decisiones de diseño y justificación (resumen)

| # | Decisión | Justificación | Alternativa descartada |
|---|---|---|---|
| DD-1 | Reutilizar la tabla `transfer` con una columna discriminadora `type` (`internal`/`ach`) y columnas ACH anulables, en vez de una tabla ACH separada | Historial unificado sin recurso aparte (ACH-05/A07), compatibilidad del shape interno (D05) | Tabla `ach_transfer` separada → complica `GET /api/transfers` unificado |
| DD-2 | Scheduler como **tarea de fondo asyncio** nativa de FastAPI (lifespan), no una librería externa | Evita dependencia nueva (D02, alcance); FastAPI ya corre un loop asyncio; arranque/apagado limpios vía `lifespan` | APScheduler/Celery → dependencia e infraestructura innecesarias para un solo proceso |
| DD-3 | Lógica de "procesar vencidos" **pura**, con `now` inyectable, separada del disparador temporal | Pruebas deterministas sin espera real (D02, Req. 10.5, 4.2) | Acoplar tiempo real al procesamiento → no testable de forma determinista |
| DD-4 | Idempotencia financiera por **restricción UNIQUE durable + guarda de transición de estado en la misma transacción** | Exactamente-una-vez para débito/reembolso/ocurrencia ante reintento, crash o concurrencia (ACH-08, Req. 10.3, D07), sin sistema de transacciones distribuidas | Solo guarda de estado sin registro durable → no sobrevive a crash entre pasos; claves externas/outbox → sobreingeniería |
| DD-7 | Registro durable `schedule_execution` con `UNIQUE(schedule_id, due_at)`; ejecución, movimiento, débito y avance de `next_run_at` en **una** transacción | Garantiza exactamente-una-vez por ocurrencia aun tras crash/retry/tick concurrente (F10, D07) | `UPDATE` condicional suelto → re-ejecuta la ocurrencia si el proceso cae entre débito y avance de fecha |
| DD-5 | Migración de esquema **idempotente aditiva** (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN` con comprobación) en el `startup` | No destruye datos sembrados de E1 (Req. 16.3) y mantiene el patrón de E1 | Herramienta de migraciones (Alembic) → ORM/dependencia, fuera de alcance |
| DD-6 | Límites almacenados en una fila única por cliente mock; consumo diario **calculado** por agregación, no almacenado | Evita contadores desincronizados; día UTC documentado (LIM-06) | Contador diario materializado → riesgo de doble conteo en transiciones |

---

## Arquitectura del backend

Se conservan las capas de la Etapa 1 (routers → service → repository → sqlite3) y se añaden
módulos nuevos siguiendo el mismo estilo. Estructura propuesta (aditiva):

```
backend/app/
├─ main.py            # (MOD) registra routers nuevos + ciclo de vida del scheduler (lifespan)
├─ config.py          # (MOD) + límites por defecto, parámetros de settlement y del scheduler
├─ db.py              # (MOD) migración idempotente: tablas y columnas nuevas
├─ money.py           # (SIN CAMBIO) reutilizado para validación/formhowever de montos
├─ seed.py            # (MOD mínimo) siembra de límites por defecto (idempotente)
├─ repository.py      # (MOD) + acceso a beneficiarios, ACH, schedules, límites
├─ service.py         # (SIN CAMBIO funcional) transferencias internas; se extrae lógica común
├─ clock.py           # (NUEVO) proveedor de tiempo inyectable (now_utc) para determinismo
├─ beneficiaries.py   # (NUEVO) reglas de beneficiarios (validación de formato, enmascarado)
├─ ach_service.py     # (NUEVO) ciclo de vida ACH: crear/autorizar, settlement, fallo/reembolso
├─ recurring_service.py # (NUEVO) schedules: crear, pausar/reanudar/cancelar, procesar vencidos
├─ limit_service.py   # (NUEVO) lectura/actualización de límites y verificación (por op + diaria)
├─ scheduler.py       # (NUEVO) disparador de fondo (asyncio) que invoca la lógica pura
└─ routers/
   ├─ accounts.py     # (SIN CAMBIO)
   ├─ transfers.py    # (MOD mínimo) historial unificado incluye ACH; internas sin cambio de forma
   ├─ ach.py          # (NUEVO) POST /api/ach, POST /api/ach/{reference}/mfa
   ├─ beneficiaries.py# (NUEVO) CRUD de beneficiarios
   ├─ recurring.py    # (NUEVO) CRUD + pausa/reanudación/cancelación de schedules
   └─ limits.py       # (NUEVO) GET/PUT de límites
```

> Nota: los nombres de archivo/módulo son orientativos; la responsabilidad de cada capa es lo
> vinculante. No se introduce ORM ni frameworks nuevos (Requisito 16.1).

---

## Modelo de datos (evolución de esquema SQLite)

Se preservan las tablas `customer`, `account` y `transfer` de la Etapa 1. La evolución es
**aditiva e idempotente** (DD-5): columnas nuevas anulables sobre `transfer` y tablas nuevas.
Montos siempre en **centavos `INTEGER`**; fechas en **ISO-8601 UTC**.

### Tabla `transfer` (extendida — columnas nuevas anulables)

| Columna (nueva) | Tipo | Notas |
|---|---|---|
| `type` | TEXT NOT NULL DEFAULT `'internal'` | `internal` \| `ach`. El `DEFAULT 'internal'` clasifica automáticamente las filas heredadas como internas incluso sin backfill (F12); la migración además ejecuta un backfill explícito por robustez. |
| `beneficiary_id` | TEXT NULL | FK opcional a `beneficiary.id` (solo ACH con beneficiario guardado). |
| `beneficiary_snapshot` | TEXT NULL | JSON con nombre, banco y cuenta (snapshot para ACH; permite ejecutar aunque el beneficiario se elimine — REC-11, Req. 1.6/8.7). |
| `settled_at` | TEXT NULL | Marca de liquidación ACH (`settled`). |
| `refunded` | INTEGER | 0/1; guarda de reembolso exactamente-una-vez (ACH `failed`). Default 0. |
| `schedule_id` | TEXT NULL | FK opcional a `recurring_schedule.id` si la transferencia fue generada por una ocurrencia recurrente. |

- Las filas internas conservan su semántica: `status` ∈ MAYÚSCULAS (`PENDING_MFA`/`COMPLETED`/
  `FAILED`/`EXPIRED`), `type='internal'`, columnas ACH en NULL.
- Las filas ACH **financieramente activas** usan `status` ∈ minúsculas
  (`pending`/`settled`/`failed`), `type='ach'`.
- **Estado de autorización ACH pendiente de MFA (F3):** una ACH sensible que aún no ha superado
  la MFA se representa con `status = 'pending_auth'` (minúsculas, `type='ach'`). Este estado es
  **no financiero**: la cuenta **no** se debita y la transferencia **no** cuenta para el consumo
  diario ni aparece como `pending` en el historial financiero hasta que la MFA es correcta y
  transiciona a `pending` con débito. `pending_auth` es distinto del `pending` financieramente
  activo (preserva D03/D04 y el Req. 3.6). Expira igual que la ventana MFA heredada (5 min) →
  `expired` (minúsculas, sin débito).
- La columna `status` almacena los conjuntos interno (MAYÚSCULAS) y ACH (minúsculas) sin
  colisión (D03).

### Tabla `beneficiary` (nueva)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | TEXT PK | UUID interno (nunca expuesto). |
| `customer_id` | TEXT FK | Propiedad del cliente mock (ACH-02). |
| `name` | TEXT | Nombre del beneficiario. |
| `bank` | TEXT | Banco. |
| `routing_number` | TEXT | 9 dígitos (validado en servicio; se almacena tal cual). |
| `account_number` | TEXT | 4–17 dígitos. **No se expone completo**; la API devuelve solo máscara. |
| `created_at` | TEXT | ISO-8601 UTC. |
| `deleted_at` | TEXT NULL | Borrado **lógico**: deja de ofrecerse sin romper referencias (Req. 1.6). |

> Enmascarado (D05, Req. 1.5/6.3/6.4): la API nunca devuelve `account_number` completo; expone
> `account_masked` = `"••••" + últimos 4 dígitos`. El número completo solo vive en persistencia.

### Tabla `recurring_schedule` (nueva)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | TEXT PK | UUID interno. |
| `customer_id` | TEXT FK | Cliente mock. |
| `type` | TEXT | `internal` \| `ach` (tipo del pago que genera). |
| `from_kind` | TEXT | Cuenta de origen (`checking`/`savings`). |
| `to_kind` | TEXT NULL | Destino interno (si `type='internal'`). |
| `beneficiary_id` | TEXT NULL | Beneficiario (si `type='ach'`). |
| `beneficiary_snapshot` | TEXT NULL | Snapshot JSON de destino ACH (REC-11). |
| `amount_cents` | INTEGER | Monto por ocurrencia. |
| `description` | TEXT | Descripción. |
| `frequency` | TEXT | `daily` \| `weekly` \| `monthly` (1/7/30 días, REC-02). |
| `status` | TEXT | `active` \| `paused` \| `cancelled`. |
| `requires_mfa` | INTEGER | 1 si monto ≥ umbral (autorizado en creación, Req. 8.6). |
| `authorized` | INTEGER | 1 si la MFA de creación fue satisfecha (o no requerida). |
| `next_run_at` | TEXT | Próxima fecha de vencimiento (ISO-8601 UTC). |
| `created_at` | TEXT | ISO-8601 UTC. |

### Tabla `schedule_execution` (nueva — idempotencia durable de ocurrencias, F10/DD-7)

Registro durable de cada ocurrencia recurrente ejecutada o intentada. Es el mecanismo que
garantiza exactamente-una-vez por ocurrencia (F10, D07).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | TEXT PK | UUID interno. |
| `schedule_id` | TEXT FK | Referencia a `recurring_schedule.id`. |
| `due_at` | TEXT | Fecha de vencimiento **original** de la ocurrencia (ISO-8601 UTC). Parte de la identidad. |
| `outcome` | TEXT | `executed` \| `failed` (negocio: fondos/límite). |
| `transfer_id` | TEXT NULL | Movimiento generado (si `executed`). |
| `created_at` | TEXT | ISO-8601 UTC. |

- **Identidad estable de la ocurrencia:** `(schedule_id, due_at)`, donde `due_at` es la fecha de
  vencimiento original (no la de ejecución). Es determinista y reproducible.
- **Restricción:** `UNIQUE(schedule_id, due_at)`. Un segundo intento de ejecutar la misma
  ocurrencia (reintento, tick solapado) hace fallar el `INSERT` y aborta la transacción, sin
  repetir el efecto financiero.
- Tanto las ocurrencias `executed` como las `failed` (por fondos/límite) insertan un registro,
  de modo que una ocurrencia fallida tampoco se reintenta como nueva (su fecha avanza, Req. 11.2).

### Tabla `transfer_limit` (nueva)

| Columna | Tipo | Notas |
|---|---|---|
| `customer_id` | TEXT PK | Cliente mock (una fila). |
| `per_transfer_cents` | INTEGER | Default **500.000.000** (5.000.000,00 COP, D01). |
| `daily_cents` | INTEGER | Default **1.000.000.000** (10.000.000,00 COP, D01). |
| `updated_at` | TEXT | ISO-8601 UTC. |

El **consumo diario** no se almacena: se calcula por agregación (DD-6, ver §Límites).

### Claves foráneas, unicidad e índices (F13)

- **Claves foráneas** (E1 ya activa `PRAGMA foreign_keys = ON`):
  `beneficiary.customer_id → customer.id`; `recurring_schedule.customer_id → customer.id`;
  `recurring_schedule.beneficiary_id → beneficiary.id` (NULL permitido);
  `transfer.beneficiary_id → beneficiary.id` (NULL); `transfer.schedule_id →
  recurring_schedule.id` (NULL); `schedule_execution.schedule_id → recurring_schedule.id`;
  `schedule_execution.transfer_id → transfer.id` (NULL); `transfer_limit.customer_id →
  customer.id`.
- **Unicidad:** `schedule_execution UNIQUE(schedule_id, due_at)` (idempotencia durable);
  `transfer_limit` PK por `customer_id` (una fila por cliente).
- **Índices** (soportan historial, límite diario y scheduler):
  `idx_transfer_created_at` sobre `transfer(created_at)`;
  `idx_transfer_type_status` sobre `transfer(type, status)` (consumo diario por estado);
  `idx_schedule_due` sobre `recurring_schedule(status, next_run_at)` (selección de vencidos);
  `idx_beneficiary_customer` sobre `beneficiary(customer_id, deleted_at)`.

### Estrategia de migración idempotente y transaccional (DD-5, Req. 16.3; F11/F12)

En el `startup` (tras `init_schema` de E1), una función `migrate(conn)` se ejecuta **dentro de
una única transacción** (`BEGIN … COMMIT`, con `ROLLBACK` ante excepción). SQLite soporta DDL
transaccional (`CREATE TABLE`, `ALTER TABLE ADD COLUMN`), de modo que un fallo a mitad revierte
el esquema por completo (F11). Orden de pasos (esquema antes que normalización de datos):

1. `CREATE TABLE IF NOT EXISTS` para `beneficiary`, `recurring_schedule`, `schedule_execution`,
   `transfer_limit`, con sus restricciones (incl. `UNIQUE(schedule_id, due_at)`).
2. Crear los índices con `CREATE INDEX IF NOT EXISTS` (F13).
3. Para cada columna nueva de `transfer`, comprobar `PRAGMA table_info(transfer)` y aplicar
   `ALTER TABLE transfer ADD COLUMN …` solo si falta (SQLite no soporta `ADD COLUMN IF NOT
   EXISTS`). La columna `type` se añade con `DEFAULT 'internal' NOT NULL`, de modo que las filas
   heredadas quedan clasificadas como internas automáticamente (F12).
4. **Backfill de robustez** (tras el paso 3): `UPDATE transfer SET type='internal' WHERE type IS
   NULL` — redundante con el `DEFAULT`, garantiza que ninguna fila heredada quede con tipo NULL
   o desconocido aunque la columna existiera de una migración previa sin default.
5. Siembra idempotente de la fila de límites por defecto (`INSERT … WHERE NOT EXISTS`).

Propiedades:

- **Idempotente:** seguro re-ejecutar en cada arranque (todas las operaciones son
  condicionales a la existencia de tabla/columna/fila).
- **Preserva E1:** no toca `account` ni las filas de `transfer` históricas; saldos y
  transferencias sembradas intactos (Req. 15.8, 16.3).
- **Sin duplicar datos mock:** el seed de E1 (`is_seeded`) y la siembra de límites son
  idempotentes.
- **Orden correcto:** el esquema (pasos 1–3) precede a la normalización/backfill (paso 4) y a la
  siembra (paso 5).
- **Testable sobre copia:** la migración se verifica aplicándola a una **copia** de una DB
  sembrada de la Etapa 1, comprobando que saldos e históricas quedan idénticos y que el esquema
  nuevo existe, **sin modificar la DB original** (A20).

---

## A. Diseño de transferencias ACH y beneficiarios

### Beneficiarios (Requisitos 1, 2)

- **Validación de formato** (en `beneficiaries.py`, autoridad de servicio): routing = exactamente
  9 dígitos numéricos (ACH-03, Req. 2.2); cuenta = 4–17 dígitos numéricos (ACH-03, Req. 2.3). El
  frontend replica la validación para feedback inmediato (ACH-10, Req. 2.4/7.3), pero la
  autoridad es el backend.
- **Propiedad y aislamiento** (ACH-02, Req. 1.4): todas las consultas filtran por `customer_id`
  del cliente mock.
- **Guardado vs ad hoc** (Req. 1.2/1.3): una ACH puede referenciar `beneficiary_id` (guardado) o
  llevar los datos inline (ad hoc), con opción de persistir el ad hoc en la misma operación.
- **Borrado lógico** (Req. 1.6): `deleted_at` marca el beneficiario como no ofertable sin romper
  transferencias/schedules que lo referencien, apoyado por `beneficiary_snapshot`.
- **Enmascarado** (D05, Req. 1.5): respuestas con `account_masked` únicamente.

### Ciclo de vida ACH (Requisitos 3, 4, 5)

Máquina de estados ACH (minúsculas, D03):

```
                 validación formato + monto (>0, ≤2 dec)      ── inválido ─▶ rechazo 400 (sin débito)
 solicitud ACH ─▶ fondos suficientes
                 límites (por op + diario)                    ── excede  ─▶ rechazo 400/409 (sin débito)
                      │
          monto<umbral│                         monto≥umbral (sensible)
                      ▼                                   ▼
             autoriza directo                      requiere MFA (código 123456, 5 min)
                      │                         ┌─────────┼─────────────────────┐
                      │                correcto+válida   incorrecto           expirada
                      │                      │        (reintento, 401)      (EXPIRED→sin débito)
                      ▼                      ▼
             ┌─────── débito inmediato ──────┐   (Req. 3.5/3.6: sin débito antes de MFA OK)
             ▼
          pending ──(condición settlement simulada, determinista)──▶ settled   (sin re-débito)
             │
             └──(fallo de proceso)──▶ failed  ──(reembolso exactamente-una-vez: refunded 0→1)──▶
```

Reglas clave:

- **Orden de comprobaciones** (D04, LIM-07, Req. 3.4/14.5): formato → fondos → **límites** →
  (si sensible) **MFA**. Un código MFA correcto nunca salta límites ni fondos. Las comprobaciones
  previas a la MFA dan feedback temprano, pero **todas las restricciones financieras se
  revalidan dentro de la transacción financiera final** (ver F8/F9).
- **Transacción financiera única de activación ACH (F7):** para una ACH que ya superó la MFA
  requerida (o que no la requería), dentro de **una sola** transacción `BEGIN IMMEDIATE … COMMIT`
  se: (1) revalidan saldo y límites; (2) crea/finaliza la fila ACH; (3) debita la cuenta de
  origen; (4) fija `status='pending'` (financieramente activo); (5) persiste `settled_at=NULL`,
  `refunded=0` y los datos del beneficiario. **El sistema nunca commitea una ACH `pending`
  (financieramente activa) sin su débito correspondiente.** Un fallo antes del COMMIT no deja
  efecto parcial (ROLLBACK total).
- **Estado de autorización vs activo (F3, Req. 3.6):** para ACH sensibles, la fila se crea en
  `status='pending_auth'` (estado **no financiero**, sin débito, no contado para límites). Solo
  tras MFA correcta se ejecuta la transacción financiera única anterior, que transiciona
  `pending_auth → pending` con débito. Si la MFA falla repetidamente sigue en `pending_auth`
  (reintento, sin lockout); si expira pasa a `expired` sin débito (Req. 3.6). `pending_auth` y
  `expired` (ACH) nunca mueven saldos.
- **Settlement** (Requisito 4): la condición de elegibilidad es una ACH autorizada en `pending`
  (4.1); la transición `pending→settled` ocurre cuando se cumple la **condición de simulación
  documentada** (DD-3): transcurrido un retardo configurable `ACH_SETTLEMENT_DELAY_SECONDS`
  desde el débito, evaluado con el reloj inyectable. El settlement lo dispara el **mismo
  scheduler de fondo** (no una petición de usuario): `process_due` también barre las ACH
  `pending` elegibles, de forma independiente de cualquier request HTTP. La transición es una
  única sentencia atómica con guarda (`UPDATE … SET status='settled', settled_at=? WHERE
  reference=? AND status='pending'`): no hay segundo débito (4.3) y reprocesar una ACH ya
  `settled`/`failed` no aplica cambios (la guarda `WHERE status='pending'` no coincide),
  garantizando idempotencia (4.4).
- **Fallo y reembolso exactamente-una-vez** (Requisito 5, ACH-07/08): la transición a `failed`
  comprueba y fija `refunded` dentro de la misma transacción (`UPDATE … SET status='failed',
  refunded=1 … WHERE refunded=0`); si la guarda no aplica (ya reembolsada), no reembolsa de
  nuevo. El reembolso reintegra exactamente `amount_cents` al origen.

> La simulación del fallo ACH es un mecanismo interno controlado (p. ej. una regla
> determinista de la simulación o un disparador clasificado **solo-de-test**, nunca un endpoint
> administrativo público — contrato §2/§7). El contrato no exige un reembolso con asiento
> compensatorio adicional visible (Req. 5.3).

### Consistencia transaccional e idempotencia (DD-4)

Todas las mutaciones de saldo (débito ACH, reembolso, aplicación interna, ocurrencia recurrente)
se ejecutan dentro de una única transacción SQLite con **guarda de estado** en el `WHERE`, de
modo que una transición ya aplicada no se repite. Esto garantiza exactamente-una-vez ante
reintentos o actividad concurrente del scheduler (ACH-08, Req. 3.7, 4.4, 5.2, 5.4, 10.3).

---

## B. Diseño de pagos recurrentes

### Persistencia y cálculo de fechas (Requisitos 8, 9)

- Un `recurring_schedule` guarda origen, destino (interno o snapshot ACH), monto, frecuencia,
  estado, `next_run_at` y banderas de autorización.
- **Primera ejecución** (REC-04, Req. 8.4/8.5): si hay fecha de inicio futura válida, `next_run_at`
  = esa fecha; si se omite, `next_run_at` = creación + un intervalo completo (nunca inmediata).
- **Intervalos** (REC-02): `daily`=+1 día, `weekly`=+7 días, `monthly`=+30 días.
- **Autorización MFA en creación** (Req. 8.6, D04, REC-09): si monto ≥ umbral, la creación exige
  MFA; `authorized=1` al superarla. Las ejecuciones automáticas no piden MFA (Req. 11.4).

### Ciclo de vida del schedule (Requisito 9, D06)

```
          crear ─▶ active ──pausar──▶ paused ──reanudar──▶ active
                     │                   │  (D06: recalcula next_run_at desde reanudación,
                     │                   │   salta ocurrencias perdidas, sin catch-up)
                     └──cancelar──┐      └──cancelar──┐
                                  ▼                   ▼
                              cancelled (terminal, no reanudable — Req. 9.7)
```

- `paused`/`cancelled` nunca ejecutan (REC-08, Req. 9.5), aun con `next_run_at` vencido.
- **Reanudación sin catch-up** (D06, Req. 9.6): al reanudar, se descartan las ocurrencias
  vencidas durante la pausa y `next_run_at` se recalcula desde el instante de reanudación con el
  intervalo configurado; no hay pagos duplicados ni débitos acumulados.
- `cancelled` es terminal (REC-07, Req. 9.7): rechaza reanudar/modificar sin mutar estado.

### Scheduler de fondo (Requisitos 10, 11; D02; DD-2/DD-3)

- **Mecanismo elegido (DD-2):** una **tarea asyncio de fondo** lanzada en el `lifespan` de
  FastAPI (startup) y cancelada limpiamente en el shutdown (Req. 10.2). Se elige frente a
  librerías externas (APScheduler/Celery) porque: el backend ya ejecuta un event loop asyncio;
  es un único proceso de baja concurrencia; evita dependencias nuevas (Req. 16.1, alcance);
  y el `lifespan` ofrece arranque/apagado deterministas.

#### Modelo de worker (F10-bis, D07)

- **Arranque de exactamente un scheduler:** en el `lifespan` de FastAPI (startup) se crea **una
  sola** tarea asyncio de scheduler (`asyncio.create_task`), referenciada en el estado de la app.
  La Etapa 2 se opera con **un único proceso/worker de backend** (D07), por lo que existe
  exactamente una instancia del scheduler.
- **Apagado limpio:** en el shutdown del `lifespan`, la tarea se cancela (`task.cancel()`) y se
  espera su término (`await` con manejo de `CancelledError`); la tarea no inicia un nuevo ciclo
  una vez señalada la cancelación.
- **Tras reinicio del backend:** como `next_run_at` y `schedule_execution` están persistidos, al
  reiniciar el scheduler reanuda procesando los vencidos pendientes; las ocurrencias ya
  registradas en `schedule_execution` no se repiten (la `UNIQUE` lo impide). Los `paused`/
  `cancelled` siguen excluidos.
- **Protección ante invocaciones concurrentes:** la garantía de exactamente-una-vez **no**
  depende del número de procesos: reside en la restricción `UNIQUE(schedule_id, due_at)` de
  `schedule_execution` y en la transacción atómica (ver abajo). Aun si existieran dos
  disparadores, el segundo `INSERT` de la misma ocurrencia fallaría y abortaría.
- **Por qué multi-worker no es parte de la Etapa 2 (D07):** desplegar con varios workers
  arrancaría varios schedulers; se evita por decisión operativa (D07) sin introducir
  infraestructura distribuida, elección de líder ni bloqueos externos. **Limitación operativa
  futura:** un despliegue multi-worker requeriría coordinar el arranque del scheduler (una sola
  instancia) o un mecanismo de toma de trabajo; la idempotencia durable ya protege el efecto
  financiero en ese escenario, pero la planificación quedaría fuera del alcance actual.

#### Ejecución durable y atómica de ocurrencias (F10, DD-7)

- **Separación disparador/lógica (DD-3):** la tarea de fondo solo "despierta" periódicamente
  (intervalo `SCHEDULER_TICK_SECONDS`) y llama a `recurring_service.process_due(conn, now)`, una
  **función pura** que recibe `now` inyectable y procesa los schedules `active` con
  `next_run_at <= now`. Las pruebas invocan `process_due` con un reloj simulado, sin esperar en
  tiempo real (Req. 10.5, A15/A16/A17/A19).
- **Identidad durable de la ocurrencia:** `(schedule_id, due_at)`, con `due_at` = el
  `next_run_at` **original** leído (fecha de vencimiento de esa ocurrencia).
- **Transacción única por ocurrencia (F10):** para cada ocurrencia vencida, dentro de **una
  sola** transacción `BEGIN IMMEDIATE … COMMIT`:
  1. `INSERT` en `schedule_execution(schedule_id, due_at, …)` — la `UNIQUE(schedule_id, due_at)`
     garantiza que una ocurrencia ya procesada (reintento, tick solapado, re-ejecución tras
     crash con la fecha aún sin avanzar) **falle el INSERT** y aborte sin efecto.
  2. Revalidar saldo y límites vigentes (misma transacción, F8).
  3. Si pasa: crear el movimiento (interno o ACH `pending` con débito), aplicar el débito.
  4. Avanzar `next_run_at` al siguiente intervalo.
  Todo se confirma junto o se revierte junto.
- **Crash antes del COMMIT (Req. 10.3, puntos 4–5 de F10):** ROLLBACK total — no hay registro de
  ejecución, ni débito, ni avance de fecha; al reiniciar, la ocurrencia se reintenta como nueva,
  exactamente una vez.
- **COMMIT exitoso:** un reintento posterior encuentra la fila `schedule_execution` existente y
  el INSERT falla → no repite el efecto financiero.
- **Revalidación en cada corrida (Req. 11.1, LIM-08):** saldo y límites se revalidan dentro de la
  transacción. Una ejecución ACH aplica el mismo ciclo ACH (`pending` + débito; Req. 11.3).
- **Manejo de fallo de negocio (Req. 11.2, REC-10):** si la revalidación falla por fondos o
  límite, se registra la ocurrencia como `outcome='failed'` **sin debitar** (el `INSERT` de
  `schedule_execution` se confirma con `failed` y `transfer_id=NULL`) y `next_run_at` avanza al
  siguiente intervalo, de modo que el schedule no queda atascado ni la ocurrencia fallida se
  reintenta.
- **D06 preservado:** al reanudar un `paused`, `next_run_at` se recalcula desde la reanudación;
  las ocurrencias saltadas durante la pausa nunca entran en `process_due` (su `due_at` no se
  genera), por lo que no se ejecutan retroactivamente.
- **`paused`/`cancelled`:** `process_due` solo selecciona `status='active'`; nunca generan
  ejecuciones financieras (Req. 9.5).

---

## C. Diseño de límites dinámicos

### Almacenamiento y actualización (Requisito 13, LIM-01/02/09)

- Una fila `transfer_limit` por cliente mock, sembrada con los defaults D01
  (per-transfer 500.000.000; daily 1.000.000.000 centavos).
- `GET /api/limits` devuelve valores vigentes (decimal-string) y, opcionalmente, consumo del día
  y disponibilidad (LIM-02, Req. 13.2).
- `PUT /api/limits` valida (LIM-09, Req. 13.4): rechaza negativos o con precisión fuera de 2
  decimales, sin modificar los vigentes ante entrada inválida. Reutiliza `money.parse_amount`.

### Cálculo y aplicación (Requisito 14, LIM-03..08)

- **Consumo diario (DD-6, LIM-06, Req. 14.3):** se calcula por agregación sobre `transfer` dentro
  de la **ventana de día UTC** actual `[00:00Z, 24:00Z)`:
  - Suma `amount_cents` de internas `COMPLETED` **+** ACH `pending`/`settled`.
  - **Excluye** ACH `failed` (tras reembolso) y estados no consumidos (`PENDING_MFA`,
    `EXPIRED`), evitando doble conteo de transiciones.
- **Verificación autoritativa dentro de la transacción financiera (F8/F9):** la verificación
  autoritativa de saldo y límites **no** se hace antes de abrir la transacción de escritura. Los
  siguientes pasos ocurren **dentro de la misma transacción `BEGIN IMMEDIATE`** usada para el
  débito, para interna, ACH y ejecución recurrente:
  1. Leer el saldo actual de la cuenta de origen.
  2. Leer los límites vigentes (`transfer_limit`).
  3. Calcular el consumo diario acumulado por agregación (ventana día UTC).
  4. Validar saldo disponible y límites (por transferencia + diario).
  5. Ejecutar el débito y persistir la operación financiera.
  - **Por transferencia (LIM-03, Req. 14.1):** rechaza si `amount > per_transfer`.
  - **Diario (LIM-04, Req. 14.2):** rechaza si `consumo_dia + amount > daily`.
  - **Frontera exacta (LIM-05, Req. 14.4):** permite igualdad exacta (`==`) si lo demás pasa.
  Un check previo a la transacción (p. ej. para feedback temprano antes de pedir MFA) es
  admisible, pero **no es autoritativo**: siempre se revalida en la transacción final.
- **Orden vs MFA (LIM-07, Req. 14.5, D04):** la verificación de límites ocurre **antes** de
  completar MFA, en internas, ACH y recurrentes. Un PIN correcto nunca supera un límite.
- **Recurrentes (LIM-08, Req. 14.6):** se re-evalúan límites y saldo en cada corrida, dentro de
  la misma transacción que crea el movimiento y el registro de ejecución (DD-7).
- **Por qué es seguro ante concurrencia (F9):** SQLite con `BEGIN IMMEDIATE` adquiere un lock de
  escritura **exclusivo** al inicio de la transacción, serializando a un único escritor a la vez
  (las demás escrituras esperan o reciben `SQLITE_BUSY`). Como la lectura de saldo/consumo (pasos
  1–3) y el débito (paso 5) están en la **misma** transacción de escritura, dos operaciones
  concurrentes no pueden ambas leer un consumo "viejo" y superar el límite diario o el saldo: la
  segunda ve el efecto de la primera ya committeado. Esto elimina la ventana TOCTOU. El scheduler
  usa el mismo patrón `BEGIN IMMEDIATE`, por lo que compite correctamente con las peticiones HTTP
  bajo la misma serialización (coherente con D07: un solo proceso, pero la garantía no depende de
  ello).
- Se preservan la **ventana de día UTC** y la **exclusión de ACH `failed`** del consumo diario
  (LIM-06).

---

## D. Compatibilidad con la Etapa 1

Se preservan (Requisito 15, 16): backend FastAPI por capas; `sqlite3` sin ORM; centavos
`INTEGER` + decimal-string + COP; frontend React/TS + CSS puro; cuentas, saldos y transferencias
históricas sembradas; transferencias internas con estados MAYÚSCULAS y la misma forma de API;
MFA (código `123456`, umbral 1.000.000, 5 min, sin lockout); cliente mock ya autenticado.

- `GET /api/accounts` y el `POST /api/transfers` / `POST /api/transfers/{ref}/mfa` internos **no
  cambian de contrato**.
- `GET /api/transfers` se **extiende aditivamente**: cada entrada gana un campo `type`; las
  internas conservan `direction {from,to}` y estado MAYÚSCULAS; las ACH añaden `beneficiary`
  (enmascarado) y estado minúsculas (D05, Req. 6). El frontend heredado ya hace
  `t.status.toLowerCase()` para los badges, por lo que tolera ambos conjuntos sin ruptura.
  Es un **cambio aditivo compatible** del contrato de ese endpoint: el único consumidor es el
  frontend propio, que se actualiza en paralelo; las entradas internas conservan su shape.
- La migración (DD-5) no toca los datos sembrados.

### Integración del arranque (startup hook + lifespan + seed)

E1 ejecuta la inicialización en `@app.on_event("startup")` (`init_schema` + `seed`). El diseño
migra ese arranque al patrón `lifespan` de FastAPI para integrar el scheduler **sin duplicar ni
omitir** la siembra:

1. En el **startup** del `lifespan`, en este orden: `init_schema(conn)` (E1, idempotente) →
   `migrate(conn)` (E2, transaccional e idempotente) → `seed(conn)` (E1, idempotente) + siembra
   de límites (idempotente) → lanzar la **única** tarea del scheduler.
2. En el **shutdown**, cancelar la tarea del scheduler y cerrar recursos.

La siembra sigue siendo idempotente (`is_seeded` de E1 y `INSERT … WHERE NOT EXISTS` para
límites), por lo que reiniciar no duplica datos. Se reemplaza el hook `on_event` por `lifespan`
sin cambiar el comportamiento observable del arranque.

### Datos del snapshot de beneficiario (para ACH recurrente)

`beneficiary_snapshot` (JSON TEXT, en `transfer` y en `recurring_schedule`) contiene los campos
mínimos para ejecutar una ACH aunque el beneficiario guardado se elimine (REC-11, Req. 1.6/8.7):
`name`, `bank`, `routing_number`, `account_number`. Es un snapshot **inmutable** tomado al
autorizar; no se consulta por su interior en SQL (solo se lee para ejecutar y para enmascarar en
respuestas). **Relación con el enmascarado (D05):** el snapshot persiste el número completo
(necesario para ejecutar el pago), pero **las respuestas de API nunca lo exponen**: derivan
`account_masked` (últimos 4 dígitos) tanto del beneficiario guardado como del snapshot.

### Política de exposición del número de routing (F14)

El contrato solo exige enmascarar el **número de cuenta** del beneficiario (D05). El
`routing_number` (9 dígitos, identificador público de banco, no secreto) **no se enmascara**: se
devuelve completo en las respuestas de beneficiario/historial ACH. No se añaden medidas de
seguridad ajenas al contrato (cifrado, etc.; eso es alcance de Etapa 3).

---

## API HTTP

Base `/api`. Montos siempre decimal-string. Errores con la forma heredada
`{ "error": { "code", "message" } }`. Códigos nuevos se añaden al mapa existente.

### Endpoints preservados (sin cambio de contrato)

- `GET /api/accounts`
- `POST /api/transfers`, `POST /api/transfers/{reference}/mfa` (internas)

### Endpoint extendido

- `GET /api/transfers` (historial unificado). Ejemplo de entrada ACH añadida:
  ```json
  {
    "type": "ach",
    "date": "2026-11-16T10:00:00Z",
    "amount": "250000.00",
    "description": "Pago proveedor",
    "status": "pending",
    "beneficiary": { "name": "ACME SA", "bank": "Banco X", "account_masked": "••••6789" }
  }
  ```
  Entrada interna (sin cambios respecto a E1):
  ```json
  {
    "type": "internal",
    "date": "2026-11-16T09:00:00Z",
    "direction": { "from": "Checking", "to": "Savings" },
    "amount": "100000.00",
    "description": "Ahorro",
    "status": "COMPLETED"
  }
  ```

### Endpoints nuevos (contratos resumidos)

| Método | Ruta | Propósito | Requisitos |
|---|---|---|---|
| `GET` | `/api/beneficiaries` | Lista beneficiarios (cuenta enmascarada) | 1.5 |
| `POST` | `/api/beneficiaries` | Crea beneficiario (valida formato) | 1.1, 2.x |
| `DELETE` | `/api/beneficiaries/{id}` | Borrado lógico | 1.6 |
| `POST` | `/api/ach` | Crea ACH; si <umbral → `pending`+débito (1 transacción); si ≥umbral → `pending_auth` (sin débito) | 3.x |
| `POST` | `/api/ach/{reference}/mfa` | Confirma MFA; en éxito transiciona `pending_auth`→`pending`+débito (1 transacción) | 3.3, 3.4, 3.5 |
| `GET` | `/api/recurring` | Lista schedules (estado + próxima fecha) | 12.1 |
| `POST` | `/api/recurring` | Crea schedule (MFA si sensible) | 8.x |
| `POST` | `/api/recurring/{id}/pause` | Pausa | 9.1 |
| `POST` | `/api/recurring/{id}/resume` | Reanuda (D06, sin catch-up) | 9.2, 9.6 |
| `POST` | `/api/recurring/{id}/cancel` | Cancela (terminal) | 9.3, 9.7 |
| `GET` | `/api/limits` | Lee límites + consumo/disponibilidad | 13.2 |
| `PUT` | `/api/limits` | Actualiza límites (valida) | 13.3, 13.4 |

### Mapa de errores (extiende el de E1)

| Código | HTTP | Situación |
|---|---|---|
| `INVALID_ROUTING` | 400 | Routing ≠ 9 dígitos (ACH-03/10) |
| `INVALID_ACCOUNT_NUMBER` | 400 | Cuenta fuera de 4–17 dígitos (ACH-03) |
| `NON_POSITIVE_AMOUNT` / `INVALID_AMOUNT` | 400 | Monto ACH ≤0 o >2 decimales (Req. 3.8) |
| `INSUFFICIENT_FUNDS` | 400/409 | Fondos insuficientes (crear/confirmar) |
| `LIMIT_EXCEEDED_PER_TRANSFER` | 409 | Supera límite por transferencia (LIM-03) |
| `LIMIT_EXCEEDED_DAILY` | 409 | Supera límite diario (LIM-04) |
| `INVALID_MFA_CODE` | 401 | Código MFA incorrecto (interna o ACH `pending_auth`; reintento) |
| `EXPIRED` | 409 | MFA expirada (interna `EXPIRED` o ACH `pending_auth`→`expired`; sin débito) |
| `INVALID_LIMIT` | 400 | Actualización de límite inválida (LIM-09) |
| `INVALID_STATE_TRANSITION` | 409 | Reanudar/modificar `cancelled` (REC-07) |
| `NOT_FOUND` | 404 | Beneficiario/schedule/referencia inexistente |

---

## Diseño del frontend (React + TypeScript, Vanilla CSS)

Se preserva la app de una sola página y se añade **navegación por secciones** (tabs/paneles)
sin introducir un router pesado nuevo, para no alterar la experiencia existente (Req. 16.2):

- **AccountsPanel**, **TransferForm (interno)**, **HistoryList**: se preservan; `HistoryList` se
  extiende para renderizar entradas ACH (beneficiario enmascarado + estado minúsculas) y
  diferenciar por `type` (D05, Req. 6/7).
- **Compatibilidad de `HistoryList` y tipos TS (UI-1):**
  - `STATUS_LABEL` (hoy con claves MAYÚSCULAS `COMPLETED`/`PENDING_MFA`/`FAILED`/`EXPIRED`) se
    **extiende** con las etiquetas ACH en minúsculas (`pending`, `settled`, `failed`,
    `pending_auth`, `expired`). El acceso existente `STATUS_LABEL[t.status]` conserva su fallback
    a `t.status` para claves ausentes, por lo que no rompe. El badge `badge-${t.status.
    toLowerCase()}` ya tolera ambos conjuntos.
  - El tipo `TransferHistoryItem` se vuelve **compatible** haciendo `direction` **opcional** y
    añadiendo `type: "internal" | "ach"` y `beneficiary?` opcional. Las entradas internas
    **conservan** su `direction { from, to }` intacto (D05); el renderizado usa `type` para
    decidir entre mostrar `direction` (interna) o `beneficiary` enmascarado (ACH). Ningún campo
    interno existente se renombra ni elimina.
  - El renderizado condicional por `type` evita que una entrada ACH (sin `direction`) rompa la
    lista; las internas se muestran exactamente como en la Etapa 1.
- **AchTransferForm** (nuevo): selección de beneficiario guardado o ad hoc, validación inmediata
  de routing/cuenta (ACH-10, Req. 7.3), opción de guardar, visibilidad de estado.
- **BeneficiariesPanel** (nuevo): alta/listado/baja con cuenta enmascarada.
- **RecurringPanel** (nuevo): crear schedule, listar estado + próxima fecha, pausar/reanudar/
  cancelar con feedback (Req. 12).
- **LimitsPanel** (nuevo): ver/editar límites, mostrar consumo del día y disponibilidad (Req. 13).
- `api/client.ts` y `types.ts` se extienden con las nuevas operaciones y tipos; montos siguen
  siendo `string` (decimal-string).

Flujo MFA de ACH: reutiliza `MfaDialog` (mismo código `123456`, contador a `expires_at`), ahora
también para ACH sensibles y para la creación de schedules sensibles.

---

## Estrategia de pruebas y verificación

> No se implementan pruebas en esta fase (pertenecen a `tasks.md`/implementación). Esta sección
> documenta la **estrategia** para A20/A21.

- **Suite de regresión de E1 (A20):** dado que la Etapa 1 no heredó pruebas, se creará una suite
  que fije el comportamiento heredado (cuentas, internas, MFA, historial) antes de extender, para
  detectar regresiones.
- **Pruebas de aceptación de E2 (A01–A19):** una por escenario, usando el **reloj inyectable**
  para settlement y vencimientos (determinismo, DD-3): p. ej. A15 (diario sin fecha corre tras 1
  día), A16 (7/30 días), A12 (400+300+300 ok, siguiente excede), A08 (reembolso único con
  transición reintentada).
- **Idempotencia:** pruebas que reprocesan transiciones (`settle` dos veces, `fail` dos veces,
  doble tick del scheduler) y verifican que saldo y estado no cambian (ACH-08, Req. 10.3).
- **Build de frontend (A20):** `npm run build` (tsc + vite) como verificación de tipos/compilación.
- **Inspección manual (A21):** navegación, formularios, validación inmediata, estados y controles
  de schedules en el navegador; se reporta lo observado.

---

## Trazabilidad requisito → diseño

| Requisito E2 | Componentes de diseño |
|---|---|
| 1 (beneficiarios) | tabla `beneficiary`, `beneficiaries.py`, routers/beneficiaries, enmascarado, borrado lógico |
| 2 (validación formato) | `beneficiaries.py` (routing 9 / cuenta 4–17), validación en frontend |
| 3 (crear/autorizar ACH) | `ach_service` (orden formato→fondos→límites→MFA), débito atómico, `money`, mapa de errores |
| 4 (settlement) | `ach_service.settle` disparado por scheduler (independiente de request) + condición simulada determinista (reloj), guarda idempotente `WHERE status='pending'` |
| 5 (fallo/reembolso) | `ach_service.fail` con guarda `refunded 0→1` en una sentencia atómica |
| 6 (historial unificado) | `transfer.type`, `GET /api/transfers` extendido, enmascarado |
| 7 (UX ACH) | AchTransferForm, BeneficiariesPanel, validación inmediata, estados |
| 8 (crear recurrente) | tabla `recurring_schedule`, `recurring_service.create`, MFA en creación |
| 9 (ciclo schedule, D06) | estados + `resume` sin catch-up (recalcula `next_run_at`) |
| 10 (scheduler) | `scheduler.py` (asyncio/lifespan, un solo worker D07) + `process_due(now)` pura; idempotencia durable `schedule_execution UNIQUE(schedule_id, due_at)` (DD-7) |
| 11 (revalidación/fallo) | `recurring_service.process_due` revalida fondos/límites en la transacción; registra `executed`/`failed`; avanza `next_run_at` |
| 12 (UI recurrentes) | RecurringPanel |
| 13 (config límites) | tabla `transfer_limit`, `limit_service`, `GET/PUT /api/limits` |
| 14 (aplicación límites) | `limit_service.check` (por op + diario UTC), orden antes de MFA |
| 15 (compat. E1) | migración aditiva, contratos internos sin cambio, estados MAYÚSCULAS |
| 16 (alcance técnico) | sin ORM/dependencias nuevas, migración idempotente, React/TS/CSS |

Cobertura de contrato: ACH-01..10 → §A; REC-01..12 → §B; LIM-01..09 → §C; HER-01..06 → §D;
A01..A19 → estrategia de pruebas; A20/A21 → §verificación.

---

## Riesgos, supuestos y temas abiertos (de diseño)

1. **Riesgo — `ALTER TABLE` en SQLite:** no soporta `ADD COLUMN IF NOT EXISTS`; se mitiga
   comprobando `PRAGMA table_info` antes de alterar (DD-5). Riesgo bajo, mitigado.
2. **Riesgo — concurrencia scheduler vs petición de usuario:** dos escrituras simultáneas sobre
   saldos. Se mitiga con `BEGIN IMMEDIATE` (serializa escrituras, un único escritor), la lectura
   de saldo/consumo **dentro** de esa misma transacción (F8/F9) y la restricción durable
   `UNIQUE(schedule_id, due_at)` para ocurrencias (DD-7). Resuelto a nivel de diseño.
3. **Supuesto — condición de settlement:** se modela como retardo configurable
   `ACH_SETTLEMENT_DELAY_SECONDS` evaluado con reloj inyectable; es una simulación, no una regla
   bancaria real (contrato §2). Valor concreto se fija en `config.py` durante implementación.
4. **Supuesto — mecanismo de fallo ACH:** disparado por una regla de simulación determinista o un
   gancho solo-de-test, nunca por endpoint administrativo público (contrato §2/§7).
5. **Supuesto — recuperación del scheduler al reinicio:** `next_run_at` y `schedule_execution`
   se persisten; al reiniciar, el scheduler reanuda los vencidos pendientes y la `UNIQUE
   (schedule_id, due_at)` impide repetir ocurrencias ya ejecutadas (D02, D07). `paused`/
   `cancelled` siguen excluidos.
6. **Modelo de un solo worker (D07):** el experimento opera con un único proceso de backend y un
   único scheduler. La idempotencia financiera **no** depende de ello (reside en la `UNIQUE` +
   transacción); multi-worker queda fuera del alcance operativo de la Etapa 2, sin introducir
   infraestructura distribuida (limitación operativa documentada).
7. **Abierto (a `tasks.md`):** nombres finales de módulos/campos y el orden exacto de tareas de
   implementación, incluida la suite de regresión de E1.

Ninguno introduce requisitos de negocio nuevos: son decisiones técnicas dentro de la
responsabilidad de diseño de Kiro, documentadas y justificadas, o supuestos de simulación
acotados por el contrato.
