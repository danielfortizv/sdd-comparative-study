# Plan de implementación — Shift Bank (Etapa 2: Complejidad funcional y estado)

> Cada tarea deriva de un requisito aprobado (`requirements.md`) o de un componente del diseño
> (`design.md`), e incorpora las decisiones E2-KIRO-D01..D07. Las referencias `_Requisitos: X.Y_`
> apuntan a criterios de aceptación; `_Diseño:_` a secciones/decisiones de diseño. Las tareas son
> incrementales, trazables y verificables; la corrección financiera y la evolución de la BD
> preceden a la funcionalidad de alto nivel. No se añade funcionalidad fuera del alcance aprobado
> (ACH, recurrentes, límites) ni tecnologías nuevas (sin ORM, sin scheduler distribuido).
>
> Convención: `[ ]` tarea pendiente. Las tareas marcadas **(verificación)** son de prueba/
> validación; el resto son de implementación. El orden de numeración es el orden de ejecución
> recomendado; las dependencias explícitas se indican por fase.

---

## Fase A — Protección del baseline y pruebas de regresión de la Etapa 1

> Dado que la Etapa 1 no heredó pruebas automatizadas, se fija su comportamiento **antes** de
> modificar nada. Depende de: nada (primera fase).

- [x] 1. Preparar el arnés de pruebas del backend con base de datos aislada
  - Añadir `pytest` (y `httpx` si se usa `TestClient`) como dependencias **solo de desarrollo**,
    sin alterar `requirements.txt` de runtime (p. ej. `requirements-dev.txt`).
  - Crear un fixture que use una **DB SQLite temporal aislada** por test (parcheando `DB_PATH`),
    de modo que ninguna prueba toque `shift_bank.db` histórica ni datos experimentales.
  - _Requisitos: 15.8_ · _Diseño: §Estrategia de pruebas; §D (aislamiento)_
  - _Completada 2026-11-16: `requirements-dev.txt`, `pytest.ini`, `tests/conftest.py`,
    `tests/test_harness.py`; 4/4 pruebas del arnés PASS; DB histórica no tocada. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_01_TAREA_01.md`._

- [x] 2. **(verificación)** Pruebas de regresión: cuentas y saldos iniciales
  - Verificar que al sembrar: Checking = 5.000.000,00 y Savings = 15.000.000,00; que existen
    exactamente dos cuentas con nombres amigables; que `GET /api/accounts` no expone IDs.
  - _Requisitos: 15.1_ · _Contrato: HER-01; A01_
  - _Completada 2026-11-16: `tests/test_regression_accounts.py` (8 pruebas); 8/8 PASS, suite
    completa 12/12 PASS; DB histórica no tocada. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_02_TAREA_02.md`._

- [x] 3. **(verificación)** Pruebas de regresión: transferencias internas
  - Transferencia bajo umbral C→S se completa de inmediato (`COMPLETED`), saldos atómicos;
    rechazos: misma cuenta, monto ≤ 0, >2 decimales, fondos insuficientes.
  - _Requisitos: 15.2_ · _Contrato: HER-02; A02_
  - _Completada 2026-11-16: `tests/test_regression_internal_transfers.py` (12 pruebas, ruta sin
    MFA); 12/12 PASS, suite completa 24/24 PASS; DB histórica no tocada. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_03_TAREA_03.md`._

- [x] 4. **(verificación)** Pruebas de regresión: MFA heredada
  - Monto ≥ 1.000.000 crea `PENDING_MFA` sin tocar saldos; código `123456` completa; código
    incorrecto mantiene pendiente (sin lockout); expiración a 5 min → `EXPIRED`; fondos
    insuficientes al confirmar → `FAILED`.
  - _Requisitos: 15.4_ · _Contrato: HER-03; A13_
  - _Completada 2026-11-16: `tests/test_regression_mfa.py` (14 pruebas; reloj determinista vía
    monkeypatch de `service._now_utc`); 14/14 PASS, suite completa 38/38 PASS; DB histórica no
    tocada. Ver `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_04_TAREA_04.md`._

- [x] 5. **(verificación)** Pruebas de regresión: contratos de API e historial
  - Forma de respuesta de `GET /api/accounts`, `POST /api/transfers`, `/mfa` y `GET
    /api/transfers` (incluidas las dos históricas sembradas) idénticas a la Etapa 1; estados en
    MAYÚSCULAS; `direction {from,to}` con nombres amigables; sin saldo resultante.
  - _Requisitos: 15.1, 15.5_ · _Contrato: HER-01; A01_
  - _Completada 2026-11-16: `tests/test_regression_api_contracts.py` (13 pruebas); 13/13 PASS,
    suite completa 51/51 PASS; DB histórica no tocada. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_05_TAREA_05.md`._

- [x] 6. **Checkpoint A — registrar la línea base de regresión**
  - Ejecutar la suite de regresión de E1 y registrar PASS/FAIL reales en
    `_experiment_logs/Kiro/pruebas/`. Este checkpoint fija el comportamiento heredado antes de
    cualquier cambio. No continuar a la Fase B sin un baseline verde registrado.
  - _Requisitos: 15.x_ · _Contrato: A20_
  - _Completada 2026-11-16: checkpoint A PASS — 51/51 pruebas verdes; fuentes `backend/app`
    idénticas al baseline por SHA-256; DB histórica intacta. Consideración futura del campo
    aditivo `type` documentada. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_06_CHECKPOINT_A.md`._

---

## Fase B — Evolución de la base de datos y cimientos compartidos

> Depende de: Fase A (baseline verde). Provee el esquema y utilidades que usan C, D, E.

- [x] 7. Implementar la migración idempotente y transaccional del esquema (`db.py`)
  - Función `migrate(conn)` dentro de una única transacción (`BEGIN … COMMIT`, `ROLLBACK` ante
    fallo). Orden: (1) `CREATE TABLE IF NOT EXISTS` para `beneficiary`, `recurring_schedule`,
    `schedule_execution`, `transfer_limit`; (2) `CREATE INDEX IF NOT EXISTS`; (3) `ALTER TABLE
    transfer ADD COLUMN` con comprobación `PRAGMA table_info` para `type TEXT NOT NULL DEFAULT
    'internal'`, `beneficiary_id`, `beneficiary_snapshot`, `settled_at`, `refunded INTEGER
    DEFAULT 0`, `schedule_id`; (4) backfill `UPDATE transfer SET type='internal' WHERE type IS
    NULL`.
  - _Requisitos: 16.3, 15.8_ · _Diseño: §Migración (DD-5, F11, F12)_
  - **Subtareas (refinamiento T-1 de la auditoría del plan):**
  - [x] 7.1 Implementar el andamiaje transaccional idempotente `migrate(conn)` (`BEGIN`/`COMMIT`/
        `ROLLBACK`), seguro de re-ejecutar en cada arranque. _Diseño: §Migración (F11)_
  - [x] 7.2 Implementar un helper que detecte columnas existentes vía `PRAGMA table_info` antes
        de `ALTER TABLE ADD COLUMN` (SQLite no soporta `ADD COLUMN IF NOT EXISTS`). _Diseño: F12_
  - [x] 7.3 Añadir las columnas nuevas a `transfer`: `type TEXT NOT NULL DEFAULT 'internal'`,
        `beneficiary_id`, `beneficiary_snapshot`, `settled_at`, `refunded INTEGER DEFAULT 0`,
        `schedule_id` (solo si faltan). _Requisitos: 16.3_ · _Diseño: F12_
  - [x] 7.4 Backfill de robustez `UPDATE transfer SET type='internal' WHERE type IS NULL` para
        clasificar las filas internas heredadas. _Requisitos: 15.8_ · _Diseño: F12_
  - [x] 7.5 Enganchar `migrate(conn)` tras `init_schema` preservando la conexión heredada y las
        convenciones monetarias; sin tocar `account` ni las filas históricas de `transfer`.
        _Requisitos: 15.8, 16.3_
  - > Frontera T7/T8: el DDL detallado de las tablas nuevas (`beneficiary`, `recurring_schedule`,
    > `schedule_execution`, `transfer_limit`) con sus FKs, unicidad e índices pertenece a la
    > **Tarea 8** y NO se implementa aquí. La Tarea 7 cubre el andamiaje transaccional y la
    > evolución de la tabla heredada `transfer`.
  - _Completada 2026-11-16: `app/db.py` (`migrate`, `_column_exists`) + `app/main.py` (enganche
    tras `init_schema`); `tests/test_migration.py` 6/6 PASS; suite completa 57/57 PASS; DB
    histórica intacta (SHA-256 sin cambios). Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_07_TAREA_07.md`._

- [x] 8. Definir el esquema de las tablas nuevas con FKs, unicidad e índices
  - `beneficiary` (con `deleted_at` para borrado lógico), `recurring_schedule`,
    `schedule_execution` con **`UNIQUE(schedule_id, due_at)`**, `transfer_limit` (PK
    `customer_id`). FKs según diseño; índices `transfer(created_at)`, `transfer(type,status)`,
    `recurring_schedule(status,next_run_at)`, `beneficiary(customer_id,deleted_at)`.
  - _Requisitos: 16.3_ · _Diseño: §Modelo de datos; §FKs/unicidad/índices (F13, DD-7)_
  - **Subtareas (refinamiento T-1 de la auditoría del plan):**
  - [x] 8.1 DDL de `beneficiary` (id PK, `customer_id` FK, name, bank, routing_number,
        account_number, created_at, `deleted_at` para borrado lógico). _Requisitos: 1.x_
  - [x] 8.2 DDL de `recurring_schedule` (id PK, `customer_id`/`beneficiary_id` FK, from_kind,
        to_kind, beneficiary_snapshot, amount_cents, description, frequency, status,
        requires_mfa, authorized, next_run_at, created_at). _Diseño: D02, D06_
  - [x] 8.3 DDL de `transfer_limit` (PK `customer_id` FK, per_transfer_cents, daily_cents,
        updated_at). _Requisitos: 13.x_
  - [x] 8.4 DDL de `schedule_execution` (id PK, `schedule_id` FK, due_at, outcome,
        `transfer_id` FK, created_at) con **`UNIQUE(schedule_id, due_at)`**. _Diseño: DD-7, F10_
  - [x] 8.5 FKs entre tablas nuevas y hacia `customer`/`transfer`/`recurring_schedule`, e índices
        `transfer(created_at)`, `transfer(type,status)`, `recurring_schedule(status,next_run_at)`,
        `beneficiary(customer_id,deleted_at)`. _Diseño: §FKs/unicidad/índices (F13)_
  - [x] 8.6 Integrar el DDL en la transacción de `migrate` (tablas → ALTER de `transfer` →
        backfill → índices), idempotente y con rollback; sin reconstruir destructivamente
        `transfer`. _Requisitos: 16.3_ · _Diseño: §Migración (F11)_
  - [x] 8.7 **(verificación)** Pruebas mínimas de esquema: existencia de tablas/columnas, FKs,
        índices, `UNIQUE(schedule_id, due_at)`, idempotencia, compatibilidad con DB ya migrada en
        la Tarea 7, saldos/históricas intactos, rollback. _Requisitos: 16.3_
  - _Completada 2026-11-16: `app/db.py` (4 tablas + 4 índices integrados en `migrate`);
    `tests/test_schema_stage2.py` 12/12 PASS; suite completa 69/69 PASS; DB histórica intacta.
    Corrección de orden aplicada (índice sobre `type` tras el ALTER). Limitación F13 documentada
    (FKs de `transfer.beneficiary_id`/`schedule_id` no declarables vía ALTER). Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_08_TAREA_08.md`._

- [x] 9. Implementar la abstracción de reloj inyectable (`clock.py`)
  - Proveedor `now_utc()` inyectable, usado por settlement, vencimientos y expiración, para
    pruebas deterministas sin espera real.
  - _Requisitos: 10.5, 4.2_ · _Diseño: DD-3_
  - _Completada 2026-11-16: `app/clock.py` (`Clock`/`SystemClock`/`ManualClock`, helpers
    `iso`/`parse_iso`/`utc_day_bounds`); `tests/test_clock.py` 10/10 PASS; suite completa 79/79
    PASS; MFA 14/14 intactas (`service._now_utc` no modificado). DB histórica intacta. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_09_TAREA_09.md`._

- [x] 10. Extraer utilidades de transacción financiera reutilizables (`repository.py`)
  - Helper para ejecutar lectura de saldo + validación + débito + cambio de estado dentro de una
    única transacción `BEGIN IMMEDIATE` (reutilizable por interna, ACH y recurrente). No cambia
    la semántica de `apply_transfer` heredada; la generaliza.
  - _Requisitos: 15.7_ · _Diseño: §Consistencia transaccional (DD-4, F7, F8/F9)_
  - **Subtareas (refinamiento T-1 de la auditoría del plan):**
  - [x] 10.1 Implementar un context manager `financial_transaction(conn)` que abra
        `BEGIN IMMEDIATE`, haga `COMMIT` al salir sin excepción y `ROLLBACK` ante error, sin
        commits intermedios. _Diseño: DD-4, F8/F9_
  - [x] 10.2 Permitir componer múltiples operaciones de repositorio bajo la misma conexión y
        transacción (el llamador es dueño de la transacción). _Diseño: §Consistencia transaccional_
  - [x] 10.3 Definir y documentar la política de anidamiento (no se abren transacciones anidadas;
        error claro si ya hay una activa) sin savepoints salvo necesidad real. _Diseño: F11_
  - [x] 10.4 Garantizar que no hay commits ocultos (`executescript` prohibido dentro de la
        transacción) y compatibilidad con `get_connection` heredado. _Diseño: F11_
  - [x] 10.5 No alterar `apply_transfer` ni el comportamiento interno heredado (solo añadir el
        helper reutilizable). _Requisitos: 15.7_
  - [x] 10.6 **(verificación)** Pruebas del helper: commit exitoso, rollback ante excepción,
        atomicidad multi-operación, fallo en 2.ª operación no preserva la 1.ª, conexiones
        independientes y locking, composición de operaciones de repositorio, sin commits
        intermedios, con DB aislada. _Requisitos: 15.7_
  - _Completada 2026-11-16: `app/txn.py` (`financial_transaction`, `TransactionError`);
    `tests/test_txn.py` 9/9 PASS; suite completa 88/88 PASS; `repository.py` sin cambios
    (comportamiento heredado intacto). Ubicación en módulo nuevo `txn.py` (no `repository.py`)
    para no tocar `apply_transfer`. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_10_TAREA_10.md`._

- [x] 11. Sembrar los límites por defecto de forma idempotente (`seed.py`)
  - `INSERT` de `transfer_limit` (per-transfer 500.000.000; daily 1.000.000.000 centavos) solo
    si no existe. No altera la siembra de E1.
  - _Requisitos: 13.1_ · _Decisión: D01_
  - _Completada 2026-11-16 (lote T11–T13): `config.py` (defaults D01) + `seed.py` (`seed_limits`
    idempotente). Ver `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_11-13_LOTE.md`._

- [x] 12. Integrar el arranque con `lifespan` sin duplicar la siembra (`main.py`)
  - Migrar `@app.on_event("startup")` a `lifespan`; orden: `init_schema → migrate → seed +
    siembra de límites → lanzar scheduler`; shutdown cancela el scheduler. Siembra idempotente.
  - _Requisitos: 16.1_ · _Diseño: §Integración del arranque_
  - _Completada 2026-11-16 (lote T11–T13): `main.py` usa `lifespan` (orden init_schema→migrate→
    seed→seed_limits); el lanzamiento del scheduler queda para la Tarea 32 (punto preparado).
    Eliminados los warnings de `on_event` (101→1). Ver registro del lote._

- [x] 13. **(verificación)** Pruebas de migración sobre una copia de DB de la Etapa 1
  - Aplicar `migrate()` a una **copia** de una DB sembrada de E1 y verificar: saldos e históricas
    idénticos; filas heredadas con `type='internal'`; tablas/índices nuevos presentes;
    idempotencia (re-ejecutar no cambia nada); ROLLBACK ante fallo simulado; sin tocar la DB
    original.
  - _Requisitos: 15.8, 16.3_ · _Contrato: A20_
  - _Completada 2026-11-16 (lote T11–T13): `tests/test_migration_suite.py` (7 pruebas, incluida
    migración sobre **copia real** de la DB histórica + E2E + idempotencia + seed_limits +
    lifespan); 7/7 PASS; suite completa 95/95 PASS; DB histórica intacta. Ver registro del lote._

---

## Fase C — Límites de transacción dinámicos

> Depende de: Fase B. Debe preceder a D y E (ACH y recurrentes aplican límites). Se integra con
> las internas **sin** cambiar su comportamiento observable.

- [x] 14. Implementar el repositorio y servicio de límites (`limit_service.py`, `repository.py`)
  - Lectura/actualización de `transfer_limit`; `GET`/`PUT`. Validación de actualización (rechaza
    negativos y >2 decimales, reutiliza `money.parse_amount`) sin modificar los vigentes ante
    entrada inválida.
  - _Requisitos: 13.2, 13.3, 13.4, 13.5_ · _Contrato: LIM-01, LIM-02, LIM-09; A10_
  - _Completada 2026-11-16 (lote Fase C): `limit_service.py` (`get_limits`/`update_limits`)._

- [x] 15. Implementar el cálculo de consumo diario (día UTC) y la verificación de límites
  - Agregación sobre `transfer` en ventana `[00:00Z, 24:00Z)`: suma internas `COMPLETED` + ACH
    `pending`/`settled`, excluye ACH `failed` y estados no consumidos. `check(amount, now)`:
    rechaza si `> per_transfer` o `consumo + amount > daily`; permite igualdad exacta.
  - _Requisitos: 14.1, 14.2, 14.3, 14.4_ · _Contrato: LIM-03..06; A11, A12_
  - **Subtareas (refinamiento T-1, tarea de alto riesgo):**
  - [x] 15.1 `daily_consumption_cents(conn, now)`: agregación por ventana de día UTC
        (`clock.utc_day_bounds`), contando internas `COMPLETED` + ACH `pending`/`settled`. _LIM-06_
  - [x] 15.2 `check(conn, amount_cents, now)`: rechaza `> per_transfer` (LIM-03) o
        `consumo + amount > daily` (LIM-04); permite igualdad exacta (LIM-05). _LIM-03..05_

- [x] 16. Integrar la verificación de límites en las transferencias internas (dentro de la transacción)
  - En la creación de transferencia interna, ejecutar lectura de saldo + límites + consumo diario
    + débito dentro de la **misma** transacción `BEGIN IMMEDIATE` (orden límites→MFA preservado).
    Sin cambiar la forma de API ni los estados MAYÚSCULAS.
  - _Requisitos: 14.1, 14.5, 14.6, 15.2_ · _Contrato: LIM-07; A14_ · _Diseño: F8/F9_
  - **Subtareas (refinamiento T-1, tarea de alto riesgo):**
  - [x] 16.1 `repository.apply_transfer_in_tx` (débito+crédito+estado SIN gestionar la
        transacción), para componer con `financial_transaction`. `apply_transfer` heredado intacto.
  - [x] 16.2 Camino interno COMPLETED: crear fila + revalidar límites + débito en una sola
        `financial_transaction`; si el límite falla → FAILED sin débito. _F8/F9_
  - [x] 16.3 Verificación de límites en `confirm_mfa` antes del débito, en la misma transacción
        (LIM-07/A14: un PIN correcto no salta el límite). _LIM-07_
  - [x] 16.4 Mapear `LIMIT_EXCEEDED_PER_TRANSFER`/`LIMIT_EXCEEDED_DAILY` → HTTP 409 en el router.

- [x] 17. Implementar los endpoints de límites (`routers/limits.py`)
  - `GET /api/limits` (valores + consumo/disponibilidad opcional), `PUT /api/limits` (valida).
    Errores `INVALID_LIMIT`.
  - _Requisitos: 13.2, 13.3, 13.4_ · _Contrato: LIM-02, LIM-09_
  - _Completada 2026-11-16 (lote Fase C): `routers/limits.py` registrado en `main.py`._

- [x] 18. **(verificación)** Pruebas de límites y concurrencia
  - Frontera exacta permitida (A11); diario 400+300+300 OK y el siguiente excede (A12); PIN
    correcto no salta límite (A14); actualización inválida rechazada; **dos operaciones
    concurrentes** no superan juntas el límite diario/saldo (serialización `BEGIN IMMEDIATE`).
  - _Requisitos: 14.1–14.6, 13.4_ · _Contrato: LIM-03..09; A11, A12, A14_
  - _Completada 2026-11-16 (lote Fase C): `tests/test_limits.py` 11/11 PASS (incluye concurrencia
    T-8 con conexiones distintas); suite completa 106/106 PASS; DB histórica intacta. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_14-18_FASE_C.md`._

---

## Fase D — Beneficiarios y transferencias ACH directas

> Depende de: Fases B y C (esquema + límites). Reutiliza la MFA heredada.

- [x] 19. Implementar beneficiarios: modelo, validación y enmascarado (`beneficiaries.py`, `repository.py`)
  - CRUD con propiedad del cliente mock; validación de formato: routing = 9 dígitos, cuenta =
    4–17 dígitos; borrado **lógico** (`deleted_at`); respuestas con `account_masked` (últimos 4);
    routing no enmascarado (F14).
  - _Requisitos: 1.1, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.5_ · _Contrato: ACH-01, ACH-02, ACH-03; A03_

- [x] 20. Implementar los endpoints de beneficiarios (`routers/beneficiaries.py`)
  - `GET`/`POST`/`DELETE /api/beneficiaries`. Errores `INVALID_ROUTING`,
    `INVALID_ACCOUNT_NUMBER`, `NOT_FOUND`.
  - _Requisitos: 1.1, 1.5, 1.6, 2.2, 2.3_ · _Contrato: ACH-02, ACH-03_

- [x] 21. Implementar la creación/autorización ACH y el estado `pending_auth` (`ach_service.py`)
  - Orden formato→fondos→**límites**→MFA. Si monto < umbral: transacción financiera única
    (`pending` + débito). Si ≥ umbral: crear `pending_auth` **sin débito** (estado no
    financiero, no cuenta para límites). Soporta beneficiario guardado o ad hoc (con opción de
    guardar). Guarda snapshot de beneficiario.
  - _Requisitos: 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 3.8, 8.7_ · _Contrato: ACH-04; A04, A09_ ·
    _Diseño: F3, F7_ · _Decisión: D04_
  - **Subtareas (refinamiento T-1, tarea de alto riesgo):**
  - [x] 21.1 Resolución/validación de beneficiario (guardado con propiedad, o ad hoc con formato)
        y snapshot. _ACH-01..03_
  - [x] 21.2 Validación de monto (positivo, ≤2 decimales), fondos y límites (pre-chequeo).
        _3.1, 3.8_
  - [x] 21.3 Camino no sensible: `pending` + débito en una sola `financial_transaction`
        (revalida fondos/límites dentro). _F7, F8/F9_
  - [x] 21.4 Camino sensible: `pending_auth` SIN débito (estado no financiero). _F3, 3.6_
  - [x] 21.5 Opción de guardar un beneficiario ad hoc en la misma operación. _1.3_

- [x] 22. Implementar la confirmación MFA de ACH y el débito atómico (`ach_service.py`, `routers/ach.py`)
  - `POST /api/ach` y `POST /api/ach/{reference}/mfa`. En MFA correcta: revalidar límites/fondos
    y transicionar `pending_auth → pending` **con débito en una sola transacción**; código
    incorrecto mantiene `pending_auth` (reintento); expiración → `expired` sin débito. Nunca
    commitear `pending` sin débito.
  - _Requisitos: 3.3, 3.4, 3.5, 3.6, 3.7_ · _Contrato: ACH-05; A07, A13_ · _Diseño: F7_ ·
    _Decisión: D04_
  - **Subtareas (refinamiento T-1, tarea de alto riesgo):**
  - [x] 22.1 `POST /api/ach` (crea/autoriza) y `POST /api/ach/{reference}/mfa` (confirma), con el
        alias `from` → `from_` corregido. _ACH-04, ACH-05_
  - [x] 22.2 MFA correcta: `pending_auth → pending` + débito en una sola `financial_transaction`;
        nunca `pending` sin débito. _F7, 3.5_
  - [x] 22.3 Código incorrecto → mantiene `pending_auth` (401, reintento); expiración → `expired`
        sin débito; fondos/límite insuficientes al confirmar → `failed` sin débito. _3.6, 3.7_

- [x] 23. Implementar la liquidación (settlement) autónoma e idempotente (`ach_service.py`)
  - Transición `pending → settled` con `settled_at`, disparada por el scheduler (independiente de
    request) cuando se cumple la condición de simulación (`ACH_SETTLEMENT_DELAY_SECONDS`, reloj
    inyectable). Sentencia atómica con guarda `WHERE status='pending'` (sin re-débito, idempotente
    sobre `settled`/`failed`).
  - _Requisitos: 4.1, 4.2, 4.3, 4.4_ · _Contrato: ACH-06, ACH-08; A07_ · _Diseño: DD-3_

- [x] 24. Implementar el fallo ACH y el reembolso exactamente-una-vez (`ach_service.py`)
  - Transición a `failed` con reembolso del monto exacto al origen en una sentencia atómica con
    guarda `WHERE refunded=0` (`SET status='failed', refunded=1`). Mecanismo de fallo por regla
    de simulación determinista o gancho solo-de-test (sin endpoint admin público).
  - _Requisitos: 5.1, 5.2, 5.3, 5.4_ · _Contrato: ACH-07, ACH-08; A08_

- [x] 25. Extender el historial unificado con entradas ACH (compat. hacia atrás) (`routers/transfers.py`, `schemas.py`)
  - `GET /api/transfers` añade `type` por entrada; internas conservan `direction {from,to}` +
    estados MAYÚSCULAS; ACH añaden `beneficiary` (enmascarado) + estados minúsculas. Sin
    renombrar/eliminar campos internos.
  - _Requisitos: 6.1, 6.2, 6.3, 6.4, 6.5_ · _Contrato: ACH-05, ACH-09; A01, A07_ ·
    _Decisión: D03, D05_

- [x] 26. **(verificación)** Pruebas de ACH: éxito, fallo, reintentos e idempotencia
  - Routing 8/no numérico rechazado, 9 aceptado (A05); cuenta 3/18 rechazada, 4–17 aceptada
    (A06); `pending` debita una vez, settlement no re-debita (A07); fallo reembolsa una vez aun
    con transición reintentada (A08); sin débito antes de MFA; montos inválidos rechazados (A09);
    enmascarado en respuestas.
  - _Requisitos: 1–7_ · _Contrato: ACH-01..10; A03–A09_
  - _Completada 2026-11-16 (lote Fase D): `tests/test_ach.py` 16/16 PASS; suite completa 122/122
    PASS. Ver `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_19-26_FASE_D.md`._

---

## Fase E — Pagos recurrentes y scheduler autónomo

> Depende de: Fases B, C, D (esquema, límites, ciclo ACH reutilizado por recurrentes ACH).

- [x] 27. Implementar la creación y persistencia de schedules (`recurring_service.py`, `repository.py`)
  - Crear schedule interno o ACH con origen/destino/monto/frecuencia válidos; estado inicial
    `active`; primera ejecución: fecha futura dada = primer vencimiento; omitida = creación + un
    intervalo completo (nunca inmediata). Snapshot de beneficiario para ACH (REC-11).
  - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7_ · _Contrato: REC-01..04, REC-11; A15, A16_

- [x] 28. Implementar la autorización MFA en la creación de schedules sensibles
  - Si monto ≥ umbral: exigir MFA al crear; marcar `authorized=1`. Las ejecuciones automáticas no
    piden MFA interactiva.
  - _Requisitos: 8.6, 11.4_ · _Contrato: REC-09_ · _Decisión: D04, D02_

- [x] 29. Implementar los controles de ciclo de vida y la reanudación sin catch-up (D06)
  - Pausar (`active→paused`), reanudar (`paused→active` recalculando `next_run_at` desde la
    reanudación, saltando ocurrencias perdidas, sin débitos acumulados), cancelar
    (`→cancelled`, terminal). Rechazar reanudar/modificar `cancelled` (`INVALID_STATE_TRANSITION`).
  - _Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_ · _Contrato: REC-06, REC-07, REC-08; A18_ ·
    _Decisión: D06_

- [x] 30. Implementar la ejecución durable y atómica de ocurrencias (`recurring_service.process_due`)
  - Función **pura** `process_due(conn, now)` que, por cada schedule `active` con `next_run_at <=
    now`, en **una** transacción `BEGIN IMMEDIATE`: `INSERT` en `schedule_execution(schedule_id,
    due_at)` (la `UNIQUE` bloquea duplicados) → revalidar fondos/límites → crear movimiento
    (interno o ACH `pending`+débito) → avanzar `next_run_at`. Crash antes de COMMIT = ROLLBACK
    total; tras COMMIT, el reintento falla el INSERT.
  - _Requisitos: 10.3, 10.4, 11.1, 11.3_ · _Contrato: REC-05, ACH-08; A17, A19_ ·
    _Diseño: DD-7, F10_ · _Decisión: D07_

- [x] 31. Implementar el manejo de fallo de negocio en la ejecución recurrente
  - Si la revalidación falla por fondos/límite: registrar `schedule_execution` con
    `outcome='failed'` **sin debitar** y avanzar `next_run_at` (no queda atascado).
  - _Requisitos: 11.2_ · _Contrato: REC-10; A19_

- [x] 32. Implementar el scheduler de fondo (único worker) y su ciclo de vida (`scheduler.py`)
  - Una **única** tarea asyncio lanzada en `lifespan` (startup) que cada `SCHEDULER_TICK_SECONDS`
    invoca `process_due(now)` y el barrido de settlement ACH; cancelación limpia en shutdown;
    recuperación tras reinicio vía `next_run_at`/`schedule_execution`. Sin endpoint admin público.
  - _Requisitos: 10.1, 10.2, 10.6_ · _Contrato: REC-05; §3/§7_ · _Decisión: D02, D07_

- [x] 33. Implementar los endpoints de recurrentes (`routers/recurring.py`)
  - `GET /api/recurring` (estado + próxima fecha), `POST /api/recurring`, `/pause`, `/resume`,
    `/cancel`.
  - _Requisitos: 12.1, 12.2_ · _Contrato: REC-12_

- [x] 34. **(verificación)** Pruebas deterministas de recurrentes (reloj inyectable)
  - Diario sin fecha corre tras 1 día (A15); semanal/mensual 7/30 días (A16); internos y ACH
    ejecutan al vencer y actualizan saldo/movimientos/próxima fecha (A17); pausado no corre,
    reanudado elegible, cancelado terminal (A18); fallo por fondos/límite registra y avanza sin
    débito (A19); **exactamente-una-vez** ante doble tick / reintento / crash simulado (INSERT
    duplicado falla); reanudar sin catch-up (D06).
  - _Requisitos: 8–11_ · _Contrato: REC-01..12; A15–A19_ · _Diseño: DD-7_

---

## Fase F — Integración del frontend

> Depende de: Fases C, D, E (endpoints disponibles). Preserva la experiencia interna existente.

- [x] 35. Extender el cliente de API y los tipos (`api/client.ts`, `types.ts`)
  - Funciones para beneficiarios, ACH (+mfa), recurrentes y límites; montos como `string`.
    `TransferHistoryItem` con `direction` opcional + `type` + `beneficiary?`; sin romper tipos
    internos.
  - _Requisitos: 6, 7, 12, 13, 16.2_ · _Diseño: UI-1_

- [x] 36. Añadir navegación por secciones sin romper la vista interna (`App.tsx`)
  - Paneles/tabs para Transferencias, ACH, Beneficiarios, Recurrentes, Límites, Historial;
    preservar `AccountsPanel`/`TransferForm`/`HistoryList` existentes.
  - _Requisitos: 16.2, 7.1_ · _Contrato: ACH-09; A21_

- [x] 37. Implementar el formulario ACH y la gestión de beneficiarios (`AchTransferForm.tsx`, `BeneficiariesPanel.tsx`)
  - Selección guardado/ad hoc, validación inmediata de routing/cuenta (bloquea envío), opción de
    guardar, reutilizar `MfaDialog` para ACH sensibles.
  - _Requisitos: 2.4, 7.1, 7.2, 7.3_ · _Contrato: ACH-09, ACH-10; A04, A05, A06_

- [x] 38. Extender el historial para internas y ACH (`HistoryList.tsx`)
  - Renderizado condicional por `type`: internas con `direction`; ACH con beneficiario
    enmascarado + estado; extender `STATUS_LABEL` con etiquetas ACH (`pending`/`settled`/
    `failed`/`pending_auth`/`expired`) conservando el fallback.
  - _Requisitos: 6.1, 6.2, 6.3, 7.4_ · _Diseño: UI-1_ · _Decisión: D03, D05_

- [x] 39. Implementar los paneles de recurrentes y de límites (`RecurringPanel.tsx`, `LimitsPanel.tsx`)
  - Recurrentes: crear, listar estado + próxima fecha, pausar/reanudar/cancelar con feedback.
    Límites: ver/editar, mostrar consumo del día y disponibilidad; feedback de carga/validación/
    éxito/error en toda la UI nueva.
  - _Requisitos: 12.1, 12.2, 12.3, 13.2, 13.3_ · _Contrato: REC-12, LIM-02; A21_

---

## Fase G — Verificación final y evidencia experimental

> Depende de: todas las fases anteriores. Solo verificación y registro; no cambia comportamiento.

- [x] 40. **(verificación)** Ejecutar la suite de regresión de la Etapa 1
  - Re-ejecutar las pruebas de la Fase A sobre la aplicación extendida; confirmar cero
    regresiones en cuentas, internas, MFA e historial.
  - _Requisitos: 15.1–15.8_ · _Contrato: HER-01..06; A01, A02, A20_
  - _Completada 2026-11-16: suite de la Fase A re-ejecutada sobre la app extendida (Fases B–F):
    `test_regression_accounts.py` 8, `test_regression_internal_transfers.py` 12,
    `test_regression_mfa.py` 14, `test_regression_api_contracts.py` 13, `test_harness.py` 4 →
    **51/51 PASS** (exit 0). Suite completa `pytest -q` → **220/220 PASS, 0 FAIL, 0 SKIP**.
    CERO regresiones; único cambio observable = campo aditivo `type` (D03/D05). DB histórica E1
    sin cambios (SHA-256 `407B0E13…`); sin código de producción modificado. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_27_TAREA_40.md`._

- [x] 41. **(verificación)** Ejecutar la suite completa de aceptación de la Etapa 2
  - Ejecutar todas las pruebas de C, D, E; mapear cada escenario **A01–A19** a su prueba y
    registrar PASS/FAIL reales.
  - _Requisitos: 1–14_ · _Contrato: A01–A19_
  - _Completada 2026-11-16: suite completa `pytest -q` → **220/220 PASS** (exit 0); archivos de
    aceptación C/D/E + regresión de contrato/internas en modo verboso → **150/150 PASS**
    (exit 0); 0 FAIL, 0 SKIP. Los **19** escenarios **A01–A19** quedan mapeados a su(s) prueba(s)
    con resultado real PASS (tabla en el registro). Garantías transversales verificadas:
    exactamente-una-vez (doble tick/reintento/crash/`UNIQUE`), reanudar sin catch-up (D06),
    concurrencia de límites (T-8) y scheduler de único worker. Sin código de producción
    modificado; DB histórica E1 intacta (SHA-256 `407B0E13…`). Entorno: venv Python 3.13.2,
    pytest 8.3.4. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_28_TAREA_41.md`._

- [x] 42. **(verificación)** A20 — build de producción del frontend + suite completa
  - Ejecutar `npm run build` (tsc + vite) y la suite backend completa; registrar salidas reales.
  - _Contrato: A20_
  - _Completada 2026-11-16: build de producción del frontend `npm run build` (`tsc && vite
    build`) → **exit 0**, 41 módulos transformados, artefactos en `frontend/dist/`
    (`index.html` 395 B, `assets/index-*.css` 4.521 B, `assets/index-*.js` 169.917 B); `tsc` sin
    errores. Suite backend completa `python -m pytest -q` (venv, Python 3.13.2, pytest 8.3.4) →
    **220 passed, 0 failed, 0 skipped, 1 warning** (exit 0). Entorno frontend: Node v24.19.0,
    npm 11.17.0, vite v5.4.21. DB histórica E1 intacta (SHA-256 `407B0E13…`); sin código de
    producción modificado. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_29_TAREA_42.md`._

- [-] 43. **(verificación)** A21 — inspección manual en navegador
  - Verificar navegación, formularios, validación inmediata, estados ACH y controles de
    schedules; registrar lo realmente observado (no inventar).
  - _Contrato: A21_

- [x] 44. **(verificación)** Integridad de BD y preservación de datos de la Etapa 1
  - Confirmar que los saldos y transacciones históricas sembradas sobreviven a la migración y a
    la operación sin alteración.
  - _Requisitos: 15.8, 16.3_ · _Contrato: HER-01, HER-05_
  - _Completada 2026-11-16: pruebas de migración/preservación/regresión
    (`test_migration.py` 6, `test_migration_suite.py` 7, `test_schema_stage2.py` 12,
    `test_regression_accounts.py` 8, `test_regression_api_contracts.py` 13) → **46/46 PASS**
    (exit 0). Verificación independiente adicional migrando una **copia real** de la DB histórica
    de E1: saldos (`checking=1.439.999.999`, `savings=560.000.001`) y 11 transferencias
    históricas idénticos antes/después; idempotencia; tablas/índices/columnas nuevos presentes;
    filas heredadas `type='internal'` → **9/9 checks PASS**. DB histórica E1 intacta (SHA-256
    `407B0E13…` idéntico antes y después de la sesión). Sin código de producción modificado;
    script de verificación efímero eliminado. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_30_TAREA_44.md`._

- [x] 45. Registrar resultados reales, iteraciones correctivas y limitaciones
  - Consignar en `_experiment_logs/Kiro/pruebas/` los PASS/FAIL, fallos encontrados,
    correcciones aplicadas y limitaciones remanentes. Sin fabricar resultados ni métricas.
  - _Contrato: A20, §7_
  - _Completada 2026-11-16: consolidado en
    `_experiment_logs/Kiro/pruebas/E2_KIRO_RESULTADOS_PRUEBAS.md`. Re-ejecución fresca: suite
    completa **220/220 PASS** (exit 0, 14,12 s) y regresión Fase A **51/51 PASS** (exit 0); A20
    = build de producción del frontend exit 0 + suite 220/220; A01–A19 mapeados 19/19 verdes;
    integridad/preservación de E1 46/46 PASS + 9/9 checks. **Una** iteración correctiva real
    documentada (orden de migración en la Tarea 8, resuelta corrigiendo el código).
    Limitaciones remanentes: F13 (FK no declarable vía ALTER en `transfer`), campo aditivo
    `type`, **A21 manual pendiente** (Tarea 43), advertencia de dependencia no bloqueante,
    métricas no instrumentadas. DB histórica E1 intacta (SHA-256 `407B0E13…`, 36.864 bytes);
    sin código de producción modificado. Sin fabricar resultados ni métricas._

- [x] 46. Recolectar evidencia estandarizada (código, pruebas, análisis estático)
  - Reunir la evidencia disponible de código/pruebas/análisis estático para las métricas del
    proyecto (p. ej. carpeta `sonarqube/`), sin modificar ni fabricar registros históricos.
  - _Contrato: §7_
  - _Completada 2026-11-16: evidencia recolectada con números reales ejecutados en fresco.
    **Código:** `app/` 24 archivos/2.896 líneas, `tests/` 18/3.270, frontend `src/` 14/2.180.
    **Pruebas:** `pytest -q` → **220/220 PASS** (exit 0, 14,33 s); 210 funciones `test_`, 577
    `assert`. **Análisis estático:** `tsc --noEmit` → **0 errores, exit 0** (TS 5.9.3), único
    disponible; **SonarQube no ejecutado y no configurado** en E2·Kiro (no hay
    `sonar-project.properties`; sin linter Python en el `.venv`; sin ESLint) — **no se fabrican**
    métricas de SonarQube (antecedente de otra etapa:
    `Etapa 1/_experiment_logs/Kiro/sonarqube_scan_001.txt`). Evidencia en
    `_experiment_logs/Kiro/sonarqube/README.md` y
    `_experiment_logs/Kiro/pruebas/E2_KIRO_EVIDENCIA_ESTANDARIZADA.md`. DB histórica E1 intacta
    (SHA-256 `407B0E13…`, 36.864 bytes); sin código de producción modificado. Ver
    `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_31_TAREA_46.md`._


---

## Fase H — Pasada correctiva de SonarQube (PRE scan manual del investigador)

> Depende de: todas las fases anteriores. Entrada: evidencia PRE en
> `_experiment_logs/Kiro/sonarqube/` (Quality Gate OK, 1 bug, 58 code smells, 0
> vulnerabilidades, 4.236 NCLOC, 0% duplicación, 318 min de deuda, 0% coverage sin datos
> importados). Solo correcciones consistentes con el comportamiento aprobado (requisitos, diseño,
> D01-D07). **No** se re-ejecuta SonarQube (el POST scan lo corre el investigador). La evidencia
> PRE no se modifica. Preserva comportamiento heredado E1, atomicidad financiera, MFA,
> idempotencia y contratos de API. A21 (Tarea 43) sigue pendiente de evidencia manual real.

- [x] 47. **(correctivo)** Corregir el bug real del scheduler (re-lanzar `CancelledError`)
  - `python:S7497` (BUG, RELIABILITY/HIGH) en `backend/app/scheduler.py` L167: en
    `Scheduler.stop()` el `except asyncio.CancelledError: pass` absorbe la cancelación sin
    re-lanzarla. Distinguir la cancelación de la **tarea worker** (esperada: se absorbe tras
    `task.cancel()`) de la cancelación del **propio `stop()`** por el llamador (debe
    propagarse). Preservar el apagado limpio (Req. 10.2) y las pruebas de `test_scheduler.py`.
  - _Requisitos: 10.2_ · _Contrato: REC-05_ · _SonarQube: S7497_

- [x] 48. **(correctivo)** Eliminar el literal SQL duplicado (CRITICAL)
  - `python:S1192` (CRITICAL, MAINTAINABILITY/HIGH) en `backend/app/repository.py` L308/315/
    479: el literal `"SELECT * FROM recurring_schedule WHERE id = ?"` aparece 3 veces. Definir
    una constante de módulo y reutilizarla. Sin cambio de comportamiento ni de SQL emitido.
  - _SonarQube: S1192_

- [x] 49. **(correctivo)** Legibilidad frontend de bajo riesgo (ternarios anidados, función, props)
  - `typescript:S3358` (MAJOR) ×2: extraer el ternario anidado a una variable/función en
    `HistoryList.tsx` L65 y `RecurringPanel.tsx` L106. `typescript:S7721` (MAJOR):
    mover `statusMessage` al scope exterior en `AchTransferForm.tsx` L58.
    `typescript:S6759` (MINOR) ×8: marcar las props de los componentes como `Readonly<>`
    (AccountsPanel, AchTransferForm, BeneficiariesPanel, HistoryList, LimitsPanel, MfaDialog,
    RecurringPanel, TransferForm). Cambios no conductuales; el build de producción debe seguir
    verde y la UI heredada intacta (A21 pendiente de evidencia manual).
  - _Requisitos: 16.2_ · _SonarQube: S3358, S7721, S6759_

- [x] 50. **(verificación)** Suite backend completa + build de producción del frontend tras las correcciones
  - Ejecutar pruebas enfocadas (`test_scheduler.py`, repositorio/recurrentes) y la suite backend
    completa (`pytest -q`), más `npm run build` (tsc + vite). Registrar PASS/FAIL reales, los
    issues corregidos y los **remanentes conscientemente diferidos** (p. ej. S6772 "ambiguous
    spacing" ×37, S107 15 parámetros, S8410/S8409 convención FastAPI, S8786 regex y S6819 en
    componentes heredados E1) con su justificación. La evidencia PRE no se toca; el POST scan lo
    corre el investigador. **No** marcar A21 (Tarea 43) sin evidencia manual real de navegador.
  - _Contrato: A20, §7_ · _SonarQube: pasada correctiva_
---

## Resumen de dependencias

```
A (regresión baseline) ─▶ B (BD + cimientos) ─┬─▶ C (límites) ─┐
                                              │                 ├─▶ D (ACH) ─▶ E (recurrentes) ─▶ F (frontend) ─▶ G (verificación)
                                              └─────────────────┘
```

- A precede a todo (fija el baseline antes de modificar).
- B provee esquema y utilidades a C, D, E.
- C precede a D y E (los límites se aplican a ACH y recurrentes).
- D precede a E (los recurrentes ACH reutilizan el ciclo ACH).
- F tras los endpoints de C/D/E; G al final.

## Cobertura requisito → tarea (R1–R16)

| Req. | Tareas | Req. | Tareas |
|---|---|---|---|
| R1 | 19, 20, 26 | R9 | 29, 34 |
| R2 | 19, 20, 37, 26 | R10 | 30, 32, 34 |
| R3 | 21, 22, 26 | R11 | 30, 31, 34 |
| R4 | 23, 26 | R12 | 33, 39 |
| R5 | 24, 26 | R13 | 11, 14, 17, 39 |
| R6 | 25, 38 | R14 | 15, 16, 18 |
| R7 | 37, 38, 43 | R15 | 2–5, 16, 40, 44 |
| R8 | 27, 28, 34 | R16 | 7, 12, 35, 36 |

Todos los R1–R16 están representados. Los 86 criterios tienen ruta de implementación +
verificación (fases C/D/E implementan; A/G y las tareas **(verificación)** validan). Cobertura de
contrato: ACH-01..10 (19–26), REC-01..12 (27–34), LIM-01..09 (14–18), HER-01..06 (2–5, 16, 40,
44); A01..A19 (41), A20 (40, 42, 45), A21 (43).

## Correcciones de la auditoría reflejadas

- F10/DD-7 → tareas 8 (`UNIQUE`) y 30 (ejecución atómica durable).
- F10-bis/D07 → tarea 32 (único worker).
- F7 → tareas 21, 22 (creación+débito atómicos; `pending_auth`).
- F8/F9 → tareas 15, 16, 30 (validación dentro de la transacción).
- F11 → tarea 7 (migración transaccional) y 13 (pruebas).
- F12 → tarea 7 (`DEFAULT 'internal'` + backfill).
- F3 → tarea 21 (`pending_auth`). F13 → tarea 8. UI-1 → tareas 35, 38. Startup → tarea 12.

## Primera tarea recomendada

**Tarea 1 — Preparar el arnés de pruebas del backend con base de datos aislada.** Debe ejecutarse
primero porque: (a) habilita toda la Fase A, que fija el baseline de la Etapa 1 **antes** de
cualquier modificación (requisito del protocolo experimental y de A20, dado que E1 no heredó
pruebas); (b) establece el aislamiento con DB temporal que protege los datos históricos (Req.
15.8); y (c) sin arnés de pruebas no es posible registrar el checkpoint A ni detectar regresiones
en las fases siguientes. Es la base de verificación sobre la que se apoya el resto del plan.
