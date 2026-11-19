# Design Document

> Diseño implementation-ready de la Etapa 3 (Opción A) en el formato nativo de Kiro. Las
> decisiones técnicas se basan en el código heredado real de la Etapa 2 de Kiro (FastAPI +
> `sqlite3` directo, sin ORM; configuración por constantes en `app/config.py` con `DB_PATH`).
> No se asume SQLAlchemy ni `DATABASE_URL`. No se copian soluciones de otras herramientas SDD.

## Overview

## Visión general

La Etapa 3 añade cuatro capacidades transversales —cifrado (reposo+tránsito), auditoría
inmutable verificable, pruebas de carga reproducibles y despliegue contenedorizado— **sobre** la
arquitectura por capas heredada, de forma **aditiva** y sin alterar los contratos de API ni los
invariantes financieros de las Etapas 1 y 2.

Principios rectores:

1. **Aditividad y compatibilidad.** El cifrado y la auditoría se insertan en los puntos de
   persistencia y en el límite transaccional ya existentes (`txn.financial_transaction`,
   `repository`, `ach_repository`), sin cambiar formas de respuesta ni estados observables.
2. **Un solo punto de verdad transaccional.** Todo cambio financiero ya ocurre dentro de
   `financial_transaction` (`BEGIN IMMEDIATE`). La entrada de auditoría se escribe **dentro de esa
   misma transacción**, logrando atomicidad auditoría+dinero sin un segundo mecanismo.
3. **Fail-closed por defecto.** Sin clave válida de cifrado o de auditoría, el sistema no
   arranca ni opera sobre datos sensibles; nunca hay respaldo en texto plano.
4. **Criptografía estándar revisada.** Se usa una biblioteca establecida (`cryptography`); no se
   implementa criptografía propia. HMAC y comparación en tiempo constante vienen de `hmac`/
   `hashlib` de la stdlib.
5. **Determinismo verificable y reproducibilidad.** La carga usa DB sintética aislada, semillas
   fijas y reporte legible por máquina; la auditoría es verificable por recomputación.

## Architecture

### Integración con la arquitectura existente

```
Navegador ──HTTPS──> Nginx (TLS termina aquí; sirve assets; proxy /api) ──HTTP interno──> FastAPI
                                                                                            │
  routers (accounts, transfers, ach, beneficiaries, recurring, limits, [audit NUEVO])       │
        │  traducen HTTP; inyectan conn vía Depends(get_connection)                          │
        ▼                                                                                     │
  service / ach_service / recurring_service / limit_service   ── autoridad de negocio ──      │
        │  componen operaciones dentro de txn.financial_transaction (BEGIN IMMEDIATE)         │
        ▼                                                                                     │
  repository / ach_repository  ── SQL puro ──  + crypto.encrypt/decrypt en los bordes de E/S  │
        │                         + audit.append_in_tx(conn, event) dentro de la misma tx      │
        ▼                                                                                     ▼
  sqlite3 (DB_PATH, PRAGMA foreign_keys=ON)  tablas heredadas + audit_log (NUEVO, append-only) │
        persistido en volumen Docker (despliegue)                                             ─┘
```

Puntos de inserción (seams) reales del código heredado:

- **Cifrado (bordes de E/S del repositorio).** Los únicos lugares donde los identificadores
  sensibles entran o salen de SQLite: `ach_repository.create_beneficiary`,
  `ach_repository.list_beneficiaries` / `get_beneficiary`, `ach_repository.create_ach_no_commit`
  (`beneficiary_snapshot`), `repository.create_schedule` (`beneficiary_snapshot`),
  `recurring_service._execute_ach_occurrence` (snapshot reutilizado) y la lectura de
  `beneficiary_snapshot` en `routers/transfers.py`. El cifrado/descifrado se aplica en esa
  frontera; la capa de servicio y la API siguen viendo valores en claro y enmascaran igual que
  hoy (`beneficiaries.public_view`).
- **Auditoría (límite transaccional).** `txn.financial_transaction` y las operaciones de
  servicio que lo usan (`service.create_transfer`/`confirm_mfa`, `ach_service.*`,
  `recurring_service.*`, `limit_service.update`, beneficiarios) obtienen una llamada
  `audit.append_in_tx(conn, event)` **antes del COMMIT**.
- **Arranque/configuración.** `config.py` (claves externas), `main.py` (`lifespan`: validación
  fail-closed de claves + migración de cifrado + anclaje de auditoría), `db.py` (DDL de
  `audit_log` en `migrate`).

### Módulos afectados (exactos)

| Módulo | Cambio | Motivo |
|--------|--------|--------|
| `app/config.py` | (MOD) leer `SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY` de entorno; sin valores por defecto inseguros | Claves externas (D-E3-01/02) |
| `app/crypto.py` | (NUEVO) AEAD por campo (AES-256-GCM) con formato versionado; carga/validación de claves; errores tipados | Cifrado en reposo (R1, R2) |
| `app/audit.py` | (NUEVO) serialización canónica, cadena HMAC, `append_in_tx`, `verify_chain`, ancla de cola | Auditoría (R5–R8) |
| `app/db.py` | (MOD) DDL de `audit_log` + triggers append-only en `migrate`; migración de cifrado idempotente/transaccional | Esquema auditoría + migración cifrado (R3, R6) |
| `app/ach_repository.py` | (MOD) cifrar al escribir / descifrar al leer `account_number`, `routing_number`, `beneficiary_snapshot` | Cifrado (R1) |
| `app/repository.py` | (MOD) cifrar `beneficiary_snapshot` en `create_schedule`; helpers de lectura descifrada | Cifrado (R1) |
| `app/service.py`, `app/ach_service.py`, `app/recurring_service.py`, `app/limit_service.py` | (MOD mínimo) emitir eventos de auditoría dentro de la transacción; auditar rechazos | Auditoría atómica (R5, R7) |
| `app/routers/*.py` | (MOD mínimo) descifrado transparente ya resuelto en repo; nuevo `routers/audit.py` protegido | Verificación auditoría (R8) |
| `app/main.py` | (MOD) validación fail-closed de claves en `lifespan`; invocar migración de cifrado; registrar router de auditoría | Arranque seguro (R2, R12) |
| `app/seed.py` | (SIN CAMBIO funcional) la siembra crea datos; el cifrado actúa en el repo | — |
| `backend/requirements.txt` | (MOD) añadir `cryptography` (runtime) | AEAD estándar (R18) |
| `backend/requirements-dev.txt` | (MOD) añadir `locust` (solo pruebas) | Carga (R9, R18) |
| `loadtest/` | (NUEVO) locustfile, aislamiento de DB, runner, verificación de invariantes, reporte | Carga (R9, R10) |
| `deploy/` (compose, Dockerfiles, nginx, `.env.example`, certs dir) | (NUEVO) | Despliegue (R11–R13) |
| `frontend` build | (SIN CAMBIO de código) servido por Nginx; API relativa vía proxy | Despliegue (R4, R11) |

---

## Components and Interfaces

## 1. Cifrado de datos sensibles (D-E3-01 → R1, R2, R3, R4)

### 1.1 Algoritmo AEAD y justificación

- **Primitiva:** **AES-256-GCM** vía `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
  AES-GCM es AEAD (confidencialidad + integridad autenticada): un texto cifrado manipulado o una
  clave incorrecta fallan la verificación del tag en el descifrado, satisfaciendo R1.5/R2.5 y
  AC-03. Se elige AES-256-GCM por ser estándar, estar acelerado por hardware y venir en una
  biblioteca revisada (`cryptography`), evitando criptografía propia (R18.2).
- **Alternativa descartada:** Fernet (AES-128-CBC+HMAC) de `cryptography`. Es válida y más
  simple, pero AES-256-GCM da AEAD nativo de 256 bits y un formato versionado explícito que
  encaja mejor con el versionado de clave requerido (R2.4). Se documenta como alternativa
  razonable; la decisión final de 256-GCM se justifica por el control del formato y el nonce.
- **Nonce:** 96 bits aleatorios (`os.urandom(12)`) por operación de cifrado; nunca reutilizado
  con la misma clave (cada escritura genera nonce nuevo). No se usan datos asociados (AAD) salvo
  la cabecera de versión (ver 1.2), que se incluye como AAD para ligar el texto cifrado a su kid.

### 1.2 Formato del campo cifrado (versionado)

Cada valor cifrado se almacena como **texto** (la columna sigue siendo `TEXT`, sin cambio de
esquema para `beneficiary`/`snapshot`), con el formato autodescriptivo:

```
enc:v1:<kid>:<base64url(nonce)>:<base64url(ciphertext||tag)>
```

- `enc:v1` — prefijo/magic y versión de formato (permite evolucionar el esquema).
- `<kid>` — identificador de la clave activa usada (p. ej. `k1`); habilita descifrado con la
  clave correcta y manejo de claves obsoletas (R2.4). El prefijo `enc:v1:<kid>` se pasa como
  **AAD** del AES-GCM, de modo que alterar el kid invalida el tag.
- El prefijo `enc:` es el discriminador para distinguir, durante la migración idempotente, un
  valor ya cifrado de uno en claro (R3.1). Un valor sin ese prefijo se considera texto plano
  pendiente de migrar (solo durante la migración; en operación normal todo valor sensible leído
  debe estar cifrado o la lectura falla fail-closed).

### 1.3 Módulo `app/crypto.py` (API interna)

- `load_keys()` — lee `SHIFT_ENC_KEYS` (p. ej. `k1:<base64-32bytes>,k0:<...>`) y
  `SHIFT_ENC_ACTIVE_KID` del entorno. Decodifica y valida longitud (32 bytes). Devuelve un
  mapa `{kid: key}` + kid activo. **No** hay clave por defecto embebida.
- `encrypt(plaintext: str) -> str` — cifra con la clave activa; produce el formato 1.2.
- `decrypt(token: str) -> str` — parsea el formato, selecciona la clave por `kid`, verifica el
  tag; lanza `DecryptionError` si el kid es desconocido/obsoleto-ausente o el tag no verifica.
- `is_encrypted(value: str) -> bool` — True si empieza por `enc:v1:` (ayuda a la migración).
- `CryptoConfigError` — clave ausente/ inválida al cargar (fail-closed en arranque).
- `DecryptionError` — fallo de integridad o kid no disponible (fail-closed en operación).
- **Higiene de secretos:** el módulo nunca registra claves ni textos cifrados; los errores no
  incluyen material sensible (R2.6, R15.2).

### 1.4 Configuración de claves (externa, fail-closed)

- Variables de entorno (en `.env` no versionado; `.env.example` con placeholders):
  - `SHIFT_ENC_KEYS` — lista `kid:base64key` separada por comas (una o más; soporta rotación
    manual: varias claves para descifrar, una activa para cifrar).
  - `SHIFT_ENC_ACTIVE_KID` — kid con el que se cifra de ahora en adelante.
  - `SHIFT_AUDIT_HMAC_KEY` — clave HMAC de la cadena de auditoría (sección 2).
- **Validación en `lifespan` (startup):** `main.py` invoca `crypto.load_keys()` y
  `audit.load_key()`; si cualquiera falta o es inválida, el arranque **aborta** (excepción no
  capturada en `lifespan` → el proceso no sirve tráfico). Esto implementa R2.2, R12.2, AC-12/13
  (fail-closed). No existe ruta que escriba/lea sensibles sin clave (R2.3).

### 1.5 Puntos de cifrado/descifrado (en el repositorio, exactos)

| Operación heredada | Acción Etapa 3 |
|--------------------|----------------|
| `ach_repository.create_beneficiary(...)` | cifrar `account_number`, `routing_number` antes del INSERT |
| `ach_repository.list_beneficiaries` / `get_beneficiary` | descifrar ambos campos al construir las filas de retorno (el servicio y `public_view` siguen recibiendo claro) |
| `ach_repository.create_ach_no_commit(... beneficiary_snapshot=...)` | el `snapshot` JSON contiene cuenta/routing: se cifra el JSON completo como un único token antes del INSERT |
| `ach_repository.get_ach_by_reference` (devuelve `beneficiary_snapshot`) | descifrar el snapshot al leer |
| `repository.create_schedule(... beneficiary_snapshot=...)` | cifrar el snapshot JSON antes del INSERT |
| lectura de schedule / ejecución recurrente ACH | descifrar el snapshot antes de reutilizarlo |
| `routers/transfers.py` (historial, parsea `beneficiary_snapshot`) | descifrar antes de `json.loads`; enmascarar igual que hoy |

Decisión: **cifrar el `beneficiary_snapshot` como un token único** (todo el JSON), no campo a
campo, porque el snapshot se persiste y se lee como una unidad y así el cambio es mínimo y
localizado. Para la tabla `beneficiary`, se cifran los **dos campos** por separado (`account_
number`, `routing_number`) porque se consultan/mapean individualmente. El `name` y `bank` no son
identificadores bancarios sensibles según D-E3-01 y se dejan en claro (se documenta el límite de
alcance).

### 1.6 Migración de cifrado de datos existentes (R3)

- Nueva función `db.migrate_encryption(conn)` invocada tras `db.migrate(conn)` en el arranque y
  disponible como paso idempotente.
- Recorre `beneficiary` (cuenta/routing), `transfer` (`beneficiary_snapshot` de filas ACH) y
  `recurring_schedule` (`beneficiary_snapshot`). Para cada valor: si `crypto.is_encrypted` es
  falso y no es nulo/vacío, lo cifra y actualiza la fila; si ya está cifrado, lo omite
  (idempotencia, R3.1).
- **Transaccional con rollback (R3.2):** toda la migración de cifrado se ejecuta dentro de una
  única transacción (`BEGIN` ... `COMMIT`, patrón idéntico a `db.migrate`); ante cualquier
  excepción (p. ej. corrupción/valor no decodificable) hace `ROLLBACK` completo, sin dejar
  mezcla de cifrado/claro. Al terminar con éxito, no queda ningún sensible en claro (R3.4).
- Se integra con la migración aditiva idempotente existente del arranque y preserva datos y
  contratos (R3.3). La migración es segura de re-ejecutar en cada arranque.

### 1.7 Seguridad en tránsito (R4)

- TLS **termina en Nginx** (sección 4). El backend recibe HTTP solo por la red interna de Docker
  Compose, no expuesta al host salvo el puerto de Nginx. Se documenta que uvicorn no termina TLS
  (opción B descartada por D-E3-04/4b).
- El frontend heredado usa `BASE_URL = "http://localhost:8000"` en `api/client.ts`. Para el
  despliegue, Nginx sirve el frontend y hace proxy de `/api` al backend; el diseño prevé que el
  build de producción apunte a un **origen relativo** (mismo host HTTPS) en lugar del localhost
  absoluto. Esto se resuelve por configuración de build/proxy **sin cambiar la lógica** del
  cliente (p. ej. base de API relativa), preservando el contrato (R4, R14.4). El detalle exacto
  (variable de entorno de Vite o reescritura de proxy) se fija en tareas; ambas opciones
  preservan el contrato de API.

---

## 2. Auditoría inmutable verificable (D-E3-02 → R5, R6, R7, R8)

### 2.1 Esquema `audit_log` (DDL en `db.migrate`)

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,  -- orden total, monotónico
    event_type  TEXT NOT NULL,     -- p.ej. INTERNAL_TRANSFER_COMPLETED, ACH_SETTLED, MFA_FAILED
    outcome     TEXT NOT NULL,     -- success | rejected
    entity_ref  TEXT,              -- referencia pública (reference/kind), NUNCA id interno ni PII
    occurred_at TEXT NOT NULL,     -- ISO-8601 UTC
    payload     TEXT NOT NULL,     -- JSON canónico de metadatos no sensibles
    prev_hmac   TEXT NOT NULL,     -- HMAC de la entrada previa ("" para la génesis)
    entry_hmac  TEXT NOT NULL      -- HMAC(serialización canónica || prev_hmac)
);
```

- `seq` AUTOINCREMENT da un orden total estable; la cadena se encadena por `prev_hmac`.
- `payload` contiene solo metadatos no sensibles (montos en centavos, estados, tipo, frecuencia,
  referencia pública). **Nunca** cuenta/routing en claro ni cifrado crudo (R5.6, AC-02).

### 2.2 Serialización canónica del evento

- Una entrada se serializa de forma **determinista** antes de calcular su HMAC: JSON con claves
  ordenadas y separadores fijos sobre la tupla `(seq, event_type, outcome, entity_ref,
  occurred_at, payload_canónico)`. El `payload` se canonicaliza igual (claves ordenadas, sin
  espacios). Esto garantiza que la verificación recompute exactamente el mismo material (R6.3).
- La canonicalización vive en `audit._canonical(entry) -> bytes` (JSON `sort_keys=True,
  separators=(",", ":")`, UTF-8).

### 2.3 Cadena HMAC con clave externa

- `entry_hmac = HMAC-SHA256(key=SHIFT_AUDIT_HMAC_KEY, msg=prev_hmac_utf8 || canonical(entry))`,
  en hex. La génesis usa `prev_hmac = ""`.
- `SHIFT_AUDIT_HMAC_KEY` se provee por entorno (fail-closed si falta/ inválida). La verificación
  usa `hmac.compare_digest` (tiempo constante).
- `audit.append_in_tx(conn, event)`:
  1. Lee el último `(seq, entry_hmac)` (`SELECT ... ORDER BY seq DESC LIMIT 1`).
  2. Calcula `entry_hmac` con `prev_hmac` = el último (o `""`).
  3. `INSERT` la fila. **No hace commit**: se ejecuta dentro de la transacción del llamador
     (`financial_transaction`), de modo que dinero + auditoría se confirman juntos (R7.1).

### 2.4 Protección append-only (endurecimiento)

- Triggers SQLite creados en `db.migrate` que **abortan** UPDATE y DELETE sobre `audit_log`:

```sql
CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
```

- Esto impide modificaciones ordinarias desde la aplicación o SQL casual (R6.1/R6.2, AC-06). Se
  documenta el límite: un administrador puede eliminar los triggers o reescribir el archivo (ver
  2.7); no es WORM absoluto.

### 2.5 Verificación de la cadena

- `audit.verify_chain(conn) -> VerifyResult`: recorre `audit_log` por `seq` ascendente,
  recomputa `entry_hmac` encadenando `prev_hmac`, y comprueba: (a) cada `entry_hmac` coincide
  (detecta manipulación de contenido), (b) `prev_hmac` de cada fila == `entry_hmac` de la
  anterior (detecta reordenamiento/ruptura), (c) `seq` es contiguo y creciente (detecta
  **eliminación intermedia** por hueco de secuencia). Devuelve íntegra o el `seq` del primer
  fallo (R6.4/R6.5, AC-05/06).
- Expuesta por `routers/audit.py` como operación administrativa protegida (ver 2.6) y usable por
  pruebas y por el runner de carga (verificación post-run, R10.4).

### 2.6 Acceso protegido a la verificación

- La verificación administrativa NO es un endpoint público anónimo (R8.2). Dado el modelo de
  cliente mock heredado (sin login real), el acceso se protege con un **token administrativo**
  provisto por entorno (`SHIFT_ADMIN_TOKEN`), exigido por cabecera; sin token válido → 401/404.
  Se documenta como mecanismo de simulación coherente con el alcance (no es gestión de
  identidades real, que es no-objetivo). La rutina de verificación también es invocable fuera de
  HTTP (pruebas/CLI) sin exponerla públicamente.

### 2.7 Atomicidad, rechazos y fail-closed

- **Éxito financiero (R7.1):** el servicio llama `audit.append_in_tx(conn, evento_success)`
  dentro del mismo `with financial_transaction(conn):` que aplica el débito/estado. Si el
  `append` o el `INSERT` de auditoría lanza, el context manager hace `ROLLBACK`: ni dinero ni
  auditoría se confirman (R7.2, AC-07). No quedan saldos/transferencias/beneficiarios parciales.
- **Rechazos y PIN inválido (R5.3, R7.3, R7.4):** una operación rechazada (fondos, límite, MFA
  incorrecta, lockout) se audita en una transacción **propia y pequeña** que inserta solo la
  entrada de auditoría del rechazo y hace COMMIT, sin tocar saldos. Clave: el rechazo NO ocurre
  dentro de una transacción financiera que mueva dinero; por eso auditar el rechazo no
  compromete ninguna mutación (AC-08). Para MFA inválida, el flujo heredado ya no debita; se
  añade solo la escritura de auditoría del intento fallido.
- **Eventos no financieros (beneficiarios, límites, ciclo de vida de schedule):** se auditan en
  la misma transacción que su cambio de configuración (esas operaciones ya usan `conn.commit()`;
  se envuelven o se les añade el `append` antes del commit para mantener atomicidad).

### 2.8 Concurrencia (R8.3, R8.4, AC-09)

- La cadena depende de leer el último `entry_hmac` y luego insertar. La correcta serialización la
  da `BEGIN IMMEDIATE` heredado: adquiere el lock de escritura al inicio de la transacción, por
  lo que dos escritores no entrelazan sus lecturas/escrituras de la cola de la cadena. El
  resultado es una secuencia `seq` sin huecos y una cadena verificable aun bajo escritores
  concurrentes y **procesos independientes** que comparten el archivo.
- **Lecturas no bloqueadas innecesariamente:** se habilita el modo WAL de SQLite
  (`PRAGMA journal_mode=WAL`) en el arranque, de modo que los lectores (saldos/historial) no
  bloqueen ni sean bloqueados por el único escritor, satisfaciendo "sin bloquear lecturas
  innecesariamente" (AC-09). WAL es aditivo y compatible con el esquema heredado.

### 2.9 Ancla de cola y límite de truncación (R6.6, Parte III del requisito)

- La verificación por recomputación detecta manipulación, reordenamiento y eliminación
  intermedia (hueco en `seq`), pero **no** la truncación de las entradas más recientes si el
  atacante recalcula un estado consistente. Mitigación de diseño: `audit` persiste un **ancla de
  cola** fuera de `audit_log` (fila en una tabla `audit_anchor` de una sola fila con el último
  `seq` y `entry_hmac`), actualizada en la misma transacción. `verify_chain` compara la cola real
  con el ancla y señala truncación si el ancla referencia un `seq` mayor que el último presente.
  Se documenta explícitamente que, si el administrador controla también el ancla y la clave HMAC,
  la truncación vuelve a ser indetectable (no se reclama inmutabilidad absoluta).

---

## 3. Pruebas de carga reproducibles (D-E3-03 → R9, R10)

### 3.1 Arquitectura y aislamiento

- Carpeta nueva `loadtest/` con: `locustfile.py`, `isolation.py`, `run_loadtest.py` (runner),
  `verify_invariants.py`, y salida en `loadtest/results/` (JSON + CSV de Locust).
- **Aislamiento antes de importar la app (R10.1, AC-10):** `run_loadtest.py` fija
  `SHIFT_*`/`DB_PATH` hacia una **DB SQLite sintética aislada** (archivo temporal dedicado) y
  establece claves de cifrado/auditoría de prueba por entorno **antes** de arrancar el servidor
  de la app, replicando la técnica del arnés (`conftest.py` parchea `config.DB_PATH`). La app se
  levanta con uvicorn sobre esa DB; nunca se tocan datos históricos.
- Datos sintéticos reproducibles: siembra determinista (cliente+cuentas con saldos amplios para
  sostener 60 s de transferencias pequeñas) con **semillas fijas** (`random.seed`) (R10.2).

### 3.2 Configuración de carga (exacta, no negociable)

- **Locust** como dependencia **solo de pruebas** (`requirements-dev.txt`).
- Usuarios: **30**; ramp-up: **5 usuarios/segundo**; **60 s de estado estable tras el ramp-up**.
  El runner espera a completar el ramp-up (30/5 = 6 s) y entonces mide 60 s de steady-state; el
  reporte separa claramente la ventana steady.
- Mezcla por pesos de tareas Locust: **60% GET saldos, 30% GET historial, 10% POST transferencia
  interna** pequeña y válida (montos muy por debajo del umbral MFA y de límites, para no disparar
  MFA ni rechazos de límite; respeta todos los controles, R10.3).
- **Distribución real medida (R9.4, AC-11):** el runner no asume los pesos; cuenta las
  peticiones realmente emitidas por ruta (a partir de las estadísticas de Locust) y reporta la
  distribución observada frente a la objetivo.

### 3.3 Métricas, umbrales y evidencia

- Reporte (JSON legible por máquina + resumen): p50/p95/p99 por tipo de operación, throughput,
  conteos de peticiones, **rechazos de negocio esperados** (p. ej. 4xx de validación contados
  aparte) vs **errores inesperados** (5xx / fallos de transporte), entorno (versión Python, SO,
  parámetros exactos). (R9.3)
- **Umbrales de aprobación (estrictos):** p95 lectura < 200 ms, p95 transferencia < 500 ms,
  errores inesperados < 1%. (R9.5, AC-11)
- **Preservación:** los artefactos originales (CSV de Locust, JSON del runner) se guardan sin
  sobrescribir (nombres con timestamp) para comparación baseline/posterior (R9.6, AC-11/16).
- **No optimizar antes del primer baseline (R9.7):** el orden de tareas captura el baseline antes
  de cualquier ajuste de rendimiento.

### 3.4 Verificación de corrección bajo concurrencia (R10.4, R10.5, AC-09)

- Tras la corrida, `verify_invariants.py`: (a) **conservación del dinero** — suma de saldos +
  neto de transferencias == invariante esperado dado el nº de transferencias COMPLETED; (b)
  ausencia de estados parciales; (c) `audit.verify_chain` íntegra incluido el ancla de cola.
  Cualquier violación marca la corrida como **fallida** independientemente del rendimiento
  (R10.5).
- **Concurrencia multiproceso enfocada (complementaria, R10.6/AC-09):** prueba que lanza dos
  conexiones/procesos (un escritor que transfiere, un lector que consulta saldos/historial)
  contra el mismo archivo SQLite en WAL, verificando que las lecturas no se bloquean
  innecesariamente y que la cadena de auditoría permanece verificable.

---

## 4. Despliegue contenedorizado (D-E3-04 → R4, R11, R12, R13)

### 4.1 Topología Docker Compose

- Carpeta `deploy/` con `docker-compose.yml` y dos servicios:
  - **backend**: imagen Python slim, instala `requirements.txt` (incluye `cryptography`), corre
    uvicorn; usuario **no root**; healthcheck que consulta un endpoint de salud; monta el
    **volumen** de datos en la ruta de `DB_PATH`.
  - **frontend/nginx**: build multistage (node build de Vite → assets estáticos) servidos por
    **Nginx**; Nginx termina **HTTPS** (certs montados), redirige HTTP→HTTPS y hace
    **reverse-proxy** de `/api` al backend por la **red interna** de Compose. El backend no
    publica puertos al host; solo Nginx expone 443 (y 80 para redirección). (R4, R11, AC-12)
- **Red interna aislada** de Compose entre nginx↔backend; el backend es inaccesible desde el
  host directamente (R4.3, R11.2).
- **Un solo scheduler (R11.3, R17.3):** una única réplica del servicio backend (sin
  escalado/replicas), de modo que exista exactamente una instancia del scheduler de fondo
  heredado (`lifespan` lanza uno). Se documenta que escalar el backend violaría la garantía y
  queda fuera de alcance.

### 4.2 TLS en Nginx

- Certificado **autofirmado provisionado externamente** (no versionado), montado por volumen/
  bind; `.gitignore` excluye el material privado. Config de Nginx: server 443 TLS + server 80
  con `return 301 https://`. (R4.1/R4.2/R4.4, AC-12)
- El frontend usa origen relativo para `/api` (servido por el mismo host HTTPS), evitando el
  `http://localhost:8000` absoluto en producción, sin cambiar la lógica del cliente.

### 4.3 Configuración, secretos y persistencia

- `.env` **no versionado** con `SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`,
  `SHIFT_ADMIN_TOKEN`; `.env.example` versionado con placeholders (sin secretos reales). Compose
  inyecta el `.env` como variables de entorno del backend. (R12.1, AC-12/13)
- **Fail-closed (R12.2):** si faltan/ son inválidas las claves, el backend no arranca (validación
  en `lifespan`); el healthcheck nunca pasa y Compose reporta el servicio como no saludable.
- **Persistencia (R12.3, R13.4, AC-13):** volumen Docker nombrado montado en la ruta de
  `DB_PATH`; el archivo SQLite (incluida `audit_log` y `audit_anchor`) sobrevive reinicios. La
  inicialización/migración en `lifespan` es idempotente (R12.4). Imágenes sin DB histórica ni
  secretos horneados (R12.5): `.dockerignore` excluye `*.db`, `.env`, certs.

### 4.4 Verificación local del despliegue (R13, AC-12/13)

- Script/documento de verificación que ejecuta: `docker compose config`, build, `up` con
  healthchecks saludables; smoke de **HTTPS** + **redirección** HTTP→HTTPS + **proxy** de `/api`;
  una operación bancaria + MFA + creación de beneficiario (comprobando cifrado en la DB del
  volumen) + `verify_chain` de auditoría; **reinicio** del stack y verificación de que datos
  cifrados y cadena sobreviven; arranque **fail-closed** quitando una clave; uso de **volúmenes
  desechables aislados** para no tocar datos reales. Solo local; sin hosting externo/K8s/CI-CD.

---

## Data Models

## 5. Modelo de datos y catálogo de eventos de auditoría

### 5.1 Cambios de esquema (todos aditivos, en `db.migrate`)

- `audit_log` (sección 2.1) + triggers append-only + `audit_anchor(id INTEGER PRIMARY KEY CHECK
  (id=1), last_seq INTEGER NOT NULL, last_hmac TEXT NOT NULL)`.
- `PRAGMA journal_mode=WAL` fijado en el arranque (compatible, mejora concurrencia lectora).
- Columnas sensibles existentes (`beneficiary.account_number`, `beneficiary.routing_number`,
  `transfer.beneficiary_snapshot`, `recurring_schedule.beneficiary_snapshot`) **no cambian de
  tipo** (siguen `TEXT`); cambia su **contenido** (token `enc:v1:...`).

### 5.2 Catálogo de eventos (payload no sensible)

| event_type | outcome | origen (servicio) |
|------------|---------|-------------------|
| INTERNAL_TRANSFER_CREATED / COMPLETED / FAILED / EXPIRED | success/rejected | `service` |
| MFA_CONFIRMED / MFA_FAILED / MFA_EXPIRED | success/rejected | `service`, `ach_service` |
| ACH_CREATED / ACH_PENDING_AUTH / ACH_SETTLED / ACH_FAILED_REFUNDED | success | `ach_service` |
| ACH_REJECTED (fondos/límite/formato) | rejected | `ach_service` |
| RECURRING_EXECUTED / RECURRING_FAILED | success/rejected | `recurring_service` |
| BENEFICIARY_CREATED / BENEFICIARY_DELETED | success | `ach_repository`/router |
| LIMIT_UPDATED | success | `limit_service` |
| SCHEDULE_PAUSED / RESUMED / CANCELLED | success | `recurring_service` |

Ningún payload incluye cuenta/routing en claro; usa `entity_ref` público (p. ej. `reference`,
`kind`, `beneficiary masked`) y montos en centavos.

## 6. Modelo de concurrencia multiproceso real (AC-09)

- Escritura: serializada por `BEGIN IMMEDIATE` (lock de escritor). La lectura del último HMAC y
  el INSERT de la entrada de auditoría ocurren dentro del mismo lock, garantizando cadena sin
  huecos incluso con escritores de **procesos distintos** sobre el mismo archivo.
- Lectura: en WAL, los lectores (saldos/historial) no bloquean al escritor ni son bloqueados,
  cumpliendo "dos conexiones lector/escritor sin bloquear lecturas innecesariamente".
- Pruebas (sección 7) ejercen dos conexiones y, de forma complementaria, dos procesos.

---

## Testing Strategy

## 7. Estrategia de pruebas (por requisito y por AC)

Se preserva el arnés heredado (`conftest.py`: DB temporal por prueba parcheando `config.DB_PATH`
antes de importar la app). Las pruebas nuevas fijan claves de cifrado/auditoría de prueba por
entorno en el arranque del fixture.

| Área / prueba (archivo propuesto) | Verifica | Requisitos | AC |
|-----------------------------------|----------|------------|----|
| `test_crypto.py` | round-trip AEAD; formato `enc:v1:kid`; nonce único; tag inválido→`DecryptionError`; kid desconocido→error; claves ausente/inválida→`CryptoConfigError`; sin fallback claro | R1, R2 | AC-02, AC-03 |
| `test_encryption_at_rest.py` | tras crear beneficiario/ACH/schedule, las columnas en SQLite empiezan por `enc:` (no hay claro); la API sigue devolviendo enmascarado | R1 | AC-02, AC-04 |
| `test_encryption_migration.py` | migración idempotente (2ª corrida no recifra); rollback ante valor corrupto; sin claro al finalizar; datos heredados intactos | R3 | AC-04 |
| `test_audit_chain.py` | cadena HMAC válida; `verify_chain` íntegra; serialización canónica estable | R5, R6, R8 | AC-05 |
| `test_audit_tamper.py` | manipular payload/orden/eliminar intermedia rompe verificación en el seq correcto; UPDATE/DELETE abortados por trigger; ancla detecta truncación (dentro del modelo) | R6 | AC-06 |
| `test_audit_atomicity.py` | éxito financiero → dinero+auditoría juntos; fallo de auditoría simulado → ROLLBACK sin saldo/transfer/beneficiario parcial; PIN inválido → sin débito pero auditado; rechazos auditados sin mutación | R5, R7 | AC-07, AC-08 |
| `test_audit_access.py` | verificación administrativa exige token; sin token → no autorizado | R8 | AC-05 |
| `test_concurrency_sqlite.py` | dos conexiones lector/escritor en WAL sin bloqueo innecesario; cadena verificable; (complementario) dos procesos | R8, R10, R17 | AC-09 |
| regresión heredada (Pytest existente) | todas las suites E1/E2 verdes sobre datos cifrados | R14 | AC-01 |
| `loadtest/` (runner + verify) | config 30/5/60 y mezcla 60/30/10; p95/err; distribución real; invariantes + cadena post-run | R9, R10 | AC-10, AC-11, AC-09 |
| verificación de despliegue (script/doc) | build/up/health/HTTPS/redirect/proxy; banca+MFA+cifrado+auditoría; persistencia al reiniciar; fail-closed sin clave; no-root | R4, R11, R12, R13 | AC-12, AC-13 |
| frontend | `tsc && vite build` verde; Vitest si se configura | R19 | AC-14 |

Mapa inverso AC→prueba: AC-01 regresión E1/E2; AC-02/03 `test_crypto`/`test_encryption_at_rest`;
AC-04 `test_encryption_migration`; AC-05 `test_audit_chain`/`test_audit_access`; AC-06
`test_audit_tamper`; AC-07/08 `test_audit_atomicity`; AC-09 `test_concurrency_sqlite` + verify de
carga; AC-10/11 `loadtest/`; AC-12/13 verificación de despliegue; AC-14/15/16 obligaciones de
evidencia (Pytest/Vitest/build, SonarQube, verificación de métricas).

---

## 8. Orden de implementación, dependencias y gates de verificación

Orden dependency-ordered pensado para generar `tasks.md` sin más descubrimiento. Cada fase
termina en un **gate** verificable.

1. **Baseline y arnés (gate G0).** Ejecutar la suite heredada (Pytest) y el build de frontend
   para fijar el verde de partida; capturar el **baseline de SonarQube** con cobertura importada
   **antes** de cualquier cambio (AC-15, R19.3; R9.7 "no optimizar antes del baseline").
2. **Config + `crypto.py` (gate G1).** Lectura fail-closed de claves; AEAD round-trip y manejo de
   fallos (`test_crypto`). Sin tocar aún el repositorio. Dep: ninguna.
3. **Cifrado en reposo en el repositorio (gate G2).** Insertar encrypt/decrypt en los puntos de
   `ach_repository`/`repository`/`transfers` (sección 1.5). Gate: `test_encryption_at_rest` +
   regresión E1/E2 verde sobre datos cifrados (AC-01, AC-02). Dep: G1.
4. **Migración de cifrado (gate G3).** `db.migrate_encryption` idempotente/transaccional +
   `test_encryption_migration` (AC-04). Dep: G2.
5. **Esquema de auditoría + `audit.py` (gate G4).** DDL `audit_log`/`audit_anchor`/triggers/WAL;
   HMAC chain, serialización canónica, `append_in_tx`, `verify_chain`, ancla. Gate:
   `test_audit_chain`/`test_audit_tamper`/`test_audit_access` (AC-05, AC-06). Dep: G1 (claves).
6. **Integración transaccional de auditoría (gate G5).** Emitir eventos en `service`,
   `ach_service`, `recurring_service`, `limit_service`, beneficiarios; auditar rechazos y
   MFA fallida; atomicidad + fail-closed. Gate: `test_audit_atomicity` + regresión verde
   (AC-07, AC-08, AC-01). Dep: G4.
7. **Concurrencia (gate G6).** WAL + pruebas lector/escritor y multiproceso
   (`test_concurrency_sqlite`) (AC-09). Dep: G5.
8. **Pruebas de carga (gate G7).** `loadtest/` con aislamiento, config 30/5/60, mezcla 60/30/10,
   reporte y verificación de invariantes+cadena; capturar **primer baseline de carga** (AC-10,
   AC-11). Dep: G6 (correctitud estable antes de medir).
9. **Despliegue (gate G8).** `deploy/` (compose, Dockerfiles, nginx TLS/redirect/proxy, `.env.
   example`, volumen, no-root, healthchecks) + verificación local (AC-12, AC-13). Dep: G5
   (app funcional cifrada+auditada).
10. **Evidencia final (gate G9).** Regresión completa Pytest + build frontend (+Vitest si
    existe) con stdout/fallos preservados (AC-14); **SonarQube final** con idéntico alcance y
    cobertura importada, comparado con el baseline G0 (AC-15); verificación de documentación/
    métricas contra evidencia cruda (AC-16). Dep: G7, G8.

Dependencias clave: claves (G1) habilitan cifrado (G2→G3) y auditoría (G4→G5); la correctitud
estable (G5/G6) precede a la medición de carga (G7) para no optimizar antes del baseline; el
despliegue (G8) necesita la app cifrada+auditada; la evidencia (G9) cierra.

## 9. Evidencia SonarQube (baseline antes de remediación y final)

- **Baseline (G0):** escaneo antes de introducir cambios de Etapa 3, con cobertura importada
  (Pytest coverage del backend), alcance de proyecto fijo; se preservan los artefactos JSON/CLI
  crudos. El investigador ejecuta SonarQube; el diseño solo define la obligación y el alcance.
- **Final (G9):** escaneo tras la implementación con **idéntico alcance** y **misma importación
  de cobertura**, comparable 1:1 con el baseline (AC-15). Las métricas documentadas se verifican
  contra el JSON/CLI original sin fabricar (AC-16). Esta es una **obligación de verificación**,
  no una funcionalidad bancaria (R19).

## Error Handling

> El manejo de errores se especifica en contexto: CryptoConfigError/DecryptionError (secciones 1.3-1.4, fail-closed), fallo de persistencia de auditoría con ROLLBACK y auditoría de rechazos (sección 2.7), y errores de verificación de cadena (secciones 2.5/2.9). Resumen de límites a continuación.

## 10. Límites del modelo de amenazas (recapitulación)

- No es conocimiento cero: el backend descifra para operar (D-E3-01).
- No hay inmutabilidad absoluta frente a un administrador con control de DB + app + secretos: con
  la clave HMAC y el ancla, podría reconstruir una cadena/ truncación consistente (D-E3-02).
- La truncación de cola solo se detecta con el ancla externa; si el ancla también está
  comprometida, no es detectable (sección 2.9).
- Los triggers append-only frenan UPDATE/DELETE ordinarios, no a un DBA que altere el esquema.
- TLS autofirmado y claves por entorno son adecuados para la simulación local, no para
  producción (sin KMS/rotación/CA).

## 11. Decisiones de diseño (resumen y tradeoffs)

| # | Decisión | Justificación | Alternativa descartada |
|---|----------|---------------|------------------------|
| DT-1 | AES-256-GCM (lib `cryptography`) para campos | AEAD estándar, integridad nativa, versionado de kid vía AAD | Fernet (válida; menos control de formato/kid) |
| DT-2 | Token versionado `enc:v1:kid:nonce:ct` en columnas `TEXT` | Sin cambio de esquema; autodescriptivo; discrimina claro vs cifrado en migración | Columnas BLOB nuevas (cambio de esquema, migración más intrusiva) |
| DT-3 | Cifrar `beneficiary_snapshot` como token único; `beneficiary` campo a campo | Snapshot se lee/escribe como unidad; campos de beneficiary se mapean sueltos | Cifrar todo campo a campo (más complejidad sin beneficio) |
| DT-4 | Auditoría dentro de `financial_transaction` existente | Atomicidad dinero+auditoría sin segundo mecanismo (R7) | Log fuera de transacción (riesgo de mutación sin rastro) |
| DT-5 | Cadena HMAC-SHA256 con `seq` + `prev_hmac` + ancla de cola | Verificable; detecta manipulación/reorden/eliminación intermedia y (con ancla) truncación | Hash plano sin clave (falsificable); WORM externo (fuera de alcance) |
| DT-6 | Triggers SQLite anti UPDATE/DELETE | Endurecimiento append-only sin infra externa | Depender solo de disciplina de aplicación (más débil) |
| DT-7 | `PRAGMA journal_mode=WAL` | Lectores no bloqueados por el escritor único (AC-09) | DELETE journal heredado (lecturas pueden bloquearse) |
| DT-8 | Token admin por entorno para verificación de auditoría | Protege acceso sin introducir login real (fuera de alcance) | Endpoint público (violaría R8.2) |
| DT-9 | Nginx termina TLS + proxy `/api`; backend sin puerto al host | Cumple D-E3-04/4b; backend no expuesto | uvicorn TLS (descartado por decisión) |
| DT-10 | Locust solo-dev; runner aísla DB y mide distribución real | Reproducible, sin dependencia de runtime; honra R9.4 | Confiar en pesos de Locust (no mide realidad) |

## Correctness Properties

Propiedades verificables (cada una mapeada a pruebas en la sección 7):

### Property 1: Confidencialidad en reposo

Ningún identificador bancario sensible queda en texto plano en SQLite tras creación o migración.
_(R1, R3; `test_encryption_at_rest`, `test_encryption_migration`)_

**Validates: Requirements 1.1, 1.2, 1.3, 3.1, 3.4**

### Property 2: Atomicidad auditoría-dinero

Todo cambio financiero exitoso confirma exactamente una entrada de auditoría en la misma
transacción; ante fallo de auditoría, ROLLBACK total. _(R7; `test_audit_atomicity`)_

**Validates: Requirements 7.1, 7.2, 7.4**

### Property 3: Verificabilidad de la cadena

Manipulación, reordenamiento y eliminación intermedia son detectables; la truncación de cola es
detectable con el ancla externa. _(R6; `test_audit_tamper`)_

**Validates: Requirements 6.4, 6.5, 6.6**

### Property 4: Invariantes financieros bajo concurrencia

Conservación del dinero y exactamente-una-vez de ACH/recurrentes se preservan con escritores
concurrentes/multiproceso. _(R10, R17; `test_concurrency_sqlite`, verificación de carga)_

**Validates: Requirements 10.4, 10.5, 17.1, 17.2**

### Property 5: Fail-closed

Ante claves de cifrado/auditoría ausentes o inválidas, el sistema no opera sobre datos sensibles
ni arranca. _(R2, R12; `test_crypto`, verificación de despliegue)_

**Validates: Requirements 2.2, 12.2**

## 12. Confirmación de preservación (R14, AC-01)

- No se eliminan ni renombran endpoints, estados ni formatos; cifrado/auditoría son aditivos.
- El dinero sigue en centavos enteros; API en decimal-string; enmascarado idéntico.
- La atomicidad y la exactitud-una-vez heredadas se reutilizan (no se reimplementan).
- Un único scheduler garantizado por despliegue de una sola réplica de backend.

