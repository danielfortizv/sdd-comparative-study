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

- [ ] 1. Preparar el arnés de pruebas del backend con base de datos aislada
  - Añadir `pytest` (y `httpx` si se usa `TestClient`) como dependencias **solo de desarrollo**,
    sin alterar `requirements.txt` de runtime (p. ej. `requirements-dev.txt`).
  - Crear un fixture que use una **DB SQLite temporal aislada** por test (parcheando `DB_PATH`),
    de modo que ninguna prueba toque `shift_bank.db` histórica ni datos experimentales.
  - _Requisitos: 15.8_ · _Diseño: §Estrategia de pruebas; §D (aislamiento)_

- [ ] 2. **(verificación)** Pruebas de regresión: cuentas y saldos iniciales
  - Verificar que al sembrar: Checking = 5.000.000,00 y Savings = 15.000.000,00; que existen
    exactamente dos cuentas con nombres amigables; que `GET /api/accounts` no expone IDs.
  - _Requisitos: 15.1_ · _Contrato: HER-01; A01_

- [ ] 3. **(verificación)** Pruebas de regresión: transferencias internas
  - Transferencia bajo umbral C→S se completa de inmediato (`COMPLETED`), saldos atómicos;
    rechazos: misma cuenta, monto ≤ 0, >2 decimales, fondos insuficientes.
  - _Requisitos: 15.2_ · _Contrato: HER-02; A02_

- [ ] 4. **(verificación)** Pruebas de regresión: MFA heredada
  - Monto ≥ 1.000.000 crea `PENDING_MFA` sin tocar saldos; código `123456` completa; código
    incorrecto mantiene pendiente (sin lockout); expiración a 5 min → `EXPIRED`; fondos
    insuficientes al confirmar → `FAILED`.
  - _Requisitos: 15.4_ · _Contrato: HER-03; A13_

- [ ] 5. **(verificación)** Pruebas de regresión: contratos de API e historial
  - Forma de respuesta de `GET /api/accounts`, `POST /api/transfers`, `/mfa` y `GET
    /api/transfers` (incluidas las dos históricas sembradas) idénticas a la Etapa 1; estados en
    MAYÚSCULAS; `direction {from,to}` con nombres amigables; sin saldo resultante.
  - _Requisitos: 15.1, 15.5_ · _Contrato: HER-01; A01_

- [ ] 6. **Checkpoint A — registrar la línea base de regresión**
  - Ejecutar la suite de regresión de E1 y registrar PASS/FAIL reales en
    `_experiment_logs/Kiro/pruebas/`. Este checkpoint fija el comportamiento heredado antes de
    cualquier cambio. No continuar a la Fase B sin un baseline verde registrado.
  - _Requisitos: 15.x_ · _Contrato: A20_

---

## Fase B — Evolución de la base de datos y cimientos compartidos

> Depende de: Fase A (baseline verde). Provee el esquema y utilidades que usan C, D, E.

- [ ] 7. Implementar la migración idempotente y transaccional del esquema (`db.py`)
  - Función `migrate(conn)` dentro de una única transacción (`BEGIN … COMMIT`, `ROLLBACK` ante
    fallo). Orden: (1) `CREATE TABLE IF NOT EXISTS` para `beneficiary`, `recurring_schedule`,
    `schedule_execution`, `transfer_limit`; (2) `CREATE INDEX IF NOT EXISTS`; (3) `ALTER TABLE
    transfer ADD COLUMN` con comprobación `PRAGMA table_info` para `type TEXT NOT NULL DEFAULT
    'internal'`, `beneficiary_id`, `beneficiary_snapshot`, `settled_at`, `refunded INTEGER
    DEFAULT 0`, `schedule_id`; (4) backfill `UPDATE transfer SET type='internal' WHERE type IS
    NULL`.
  - _Requisitos: 16.3, 15.8_ · _Diseño: §Migración (DD-5, F11, F12)_

- [ ] 8. Definir el esquema de las tablas nuevas con FKs, unicidad e índices
  - `beneficiary` (con `deleted_at` para borrado lógico), `recurring_schedule`,
    `schedule_execution` con **`UNIQUE(schedule_id, due_at)`**, `transfer_limit` (PK
    `customer_id`). FKs según diseño; índices `transfer(created_at)`, `transfer(type,status)`,
    `recurring_schedule(status,next_run_at)`, `beneficiary(customer_id,deleted_at)`.
  - _Requisitos: 16.3_ · _Diseño: §Modelo de datos; §FKs/unicidad/índices (F13, DD-7)_

- [ ] 9. Implementar la abstracción de reloj inyectable (`clock.py`)
  - Proveedor `now_utc()` inyectable, usado por settlement, vencimientos y expiración, para
    pruebas deterministas sin espera real.
  - _Requisitos: 10.5, 4.2_ · _Diseño: DD-3_

- [ ] 10. Extraer utilidades de transacción financiera reutilizables (`repository.py`)
  - Helper para ejecutar lectura de saldo + validación + débito + cambio de estado dentro de una
    única transacción `BEGIN IMMEDIATE` (reutilizable por interna, ACH y recurrente). No cambia
    la semántica de `apply_transfer` heredada; la generaliza.
  - _Requisitos: 15.7_ · _Diseño: §Consistencia transaccional (DD-4, F7, F8/F9)_

- [ ] 11. Sembrar los límites por defecto de forma idempotente (`seed.py`)
  - `INSERT` de `transfer_limit` (per-transfer 500.000.000; daily 1.000.000.000 centavos) solo
    si no existe. No altera la siembra de E1.
  - _Requisitos: 13.1_ · _Decisión: D01_

- [ ] 12. Integrar el arranque con `lifespan` sin duplicar la siembra (`main.py`)
  - Migrar `@app.on_event("startup")` a `lifespan`; orden: `init_schema → migrate → seed +
    siembra de límites → lanzar scheduler`; shutdown cancela el scheduler. Siembra idempotente.
  - _Requisitos: 16.1_ · _Diseño: §Integración del arranque_

- [ ] 13. **(verificación)** Pruebas de migración sobre una copia de DB de la Etapa 1
  - Aplicar `migrate()` a una **copia** de una DB sembrada de E1 y verificar: saldos e históricas
    idénticos; filas heredadas con `type='internal'`; tablas/índices nuevos presentes;
    idempotencia (re-ejecutar no cambia nada); ROLLBACK ante fallo simulado; sin tocar la DB
    original.
  - _Requisitos: 15.8, 16.3_ · _Contrato: A20_

---

## Fase C — Límites de transacción dinámicos

> Depende de: Fase B. Debe preceder a D y E (ACH y recurrentes aplican límites). Se integra con
> las internas **sin** cambiar su comportamiento observable.

- [ ] 14. Implementar el repositorio y servicio de límites (`limit_service.py`, `repository.py`)
  - Lectura/actualización de `transfer_limit`; `GET`/`PUT`. Validación de actualización (rechaza
    negativos y >2 decimales, reutiliza `money.parse_amount`) sin modificar los vigentes ante
    entrada inválida.
  - _Requisitos: 13.2, 13.3, 13.4, 13.5_ · _Contrato: LIM-01, LIM-02, LIM-09; A10_

- [ ] 15. Implementar el cálculo de consumo diario (día UTC) y la verificación de límites
  - Agregación sobre `transfer` en ventana `[00:00Z, 24:00Z)`: suma internas `COMPLETED` + ACH
    `pending`/`settled`, excluye ACH `failed` y estados no consumidos. `check(amount, now)`:
    rechaza si `> per_transfer` o `consumo + amount > daily`; permite igualdad exacta.
  - _Requisitos: 14.1, 14.2, 14.3, 14.4_ · _Contrato: LIM-03..06; A11, A12_

- [ ] 16. Integrar la verificación de límites en las transferencias internas (dentro de la transacción)
  - En la creación de transferencia interna, ejecutar lectura de saldo + límites + consumo diario
    + débito dentro de la **misma** transacción `BEGIN IMMEDIATE` (orden límites→MFA preservado).
    Sin cambiar la forma de API ni los estados MAYÚSCULAS.
  - _Requisitos: 14.1, 14.5, 14.6, 15.2_ · _Contrato: LIM-07; A14_ · _Diseño: F8/F9_

- [ ] 17. Implementar los endpoints de límites (`routers/limits.py`)
  - `GET /api/limits` (valores + consumo/disponibilidad opcional), `PUT /api/limits` (valida).
    Errores `INVALID_LIMIT`.
  - _Requisitos: 13.2, 13.3, 13.4_ · _Contrato: LIM-02, LIM-09_

- [ ] 18. **(verificación)** Pruebas de límites y concurrencia
  - Frontera exacta permitida (A11); diario 400+300+300 OK y el siguiente excede (A12); PIN
    correcto no salta límite (A14); actualización inválida rechazada; **dos operaciones
    concurrentes** no superan juntas el límite diario/saldo (serialización `BEGIN IMMEDIATE`).
  - _Requisitos: 14.1–14.6, 13.4_ · _Contrato: LIM-03..09; A11, A12, A14_

---

## Fase D — Beneficiarios y transferencias ACH directas

> Depende de: Fases B y C (esquema + límites). Reutiliza la MFA heredada.

- [ ] 19. Implementar beneficiarios: modelo, validación y enmascarado (`beneficiaries.py`, `repository.py`)
  - CRUD con propiedad del cliente mock; validación de formato: routing = 9 dígitos, cuenta =
    4–17 dígitos; borrado **lógico** (`deleted_at`); respuestas con `account_masked` (últimos 4);
    routing no enmascarado (F14).
  - _Requisitos: 1.1, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.5_ · _Contrato: ACH-01, ACH-02, ACH-03; A03_

- [ ] 20. Implementar los endpoints de beneficiarios (`routers/beneficiaries.py`)
  - `GET`/`POST`/`DELETE /api/beneficiaries`. Errores `INVALID_ROUTING`,
    `INVALID_ACCOUNT_NUMBER`, `NOT_FOUND`.
  - _Requisitos: 1.1, 1.5, 1.6, 2.2, 2.3_ · _Contrato: ACH-02, ACH-03_

- [ ] 21. Implementar la creación/autorización ACH y el estado `pending_auth` (`ach_service.py`)
  - Orden formato→fondos→**límites**→MFA. Si monto < umbral: transacción financiera única
    (`pending` + débito). Si ≥ umbral: crear `pending_auth` **sin débito** (estado no
    financiero, no cuenta para límites). Soporta beneficiario guardado o ad hoc (con opción de
    guardar). Guarda snapshot de beneficiario.
  - _Requisitos: 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 3.8, 8.7_ · _Contrato: ACH-04; A04, A09_ ·
    _Diseño: F3, F7_ · _Decisión: D04_

- [ ] 22. Implementar la confirmación MFA de ACH y el débito atómico (`ach_service.py`, `routers/ach.py`)
  - `POST /api/ach` y `POST /api/ach/{reference}/mfa`. En MFA correcta: revalidar límites/fondos
    y transicionar `pending_auth → pending` **con débito en una sola transacción**; código
    incorrecto mantiene `pending_auth` (reintento); expiración → `expired` sin débito. Nunca
    commitear `pending` sin débito.
  - _Requisitos: 3.3, 3.4, 3.5, 3.6, 3.7_ · _Contrato: ACH-05; A07, A13_ · _Diseño: F7_ ·
    _Decisión: D04_

- [ ] 23. Implementar la liquidación (settlement) autónoma e idempotente (`ach_service.py`)
  - Transición `pending → settled` con `settled_at`, disparada por el scheduler (independiente de
    request) cuando se cumple la condición de simulación (`ACH_SETTLEMENT_DELAY_SECONDS`, reloj
    inyectable). Sentencia atómica con guarda `WHERE status='pending'` (sin re-débito, idempotente
    sobre `settled`/`failed`).
  - _Requisitos: 4.1, 4.2, 4.3, 4.4_ · _Contrato: ACH-06, ACH-08; A07_ · _Diseño: DD-3_

- [ ] 24. Implementar el fallo ACH y el reembolso exactamente-una-vez (`ach_service.py`)
  - Transición a `failed` con reembolso del monto exacto al origen en una sentencia atómica con
    guarda `WHERE refunded=0` (`SET status='failed', refunded=1`). Mecanismo de fallo por regla
    de simulación determinista o gancho solo-de-test (sin endpoint admin público).
  - _Requisitos: 5.1, 5.2, 5.3, 5.4_ · _Contrato: ACH-07, ACH-08; A08_

- [ ] 25. Extender el historial unificado con entradas ACH (compat. hacia atrás) (`routers/transfers.py`, `schemas.py`)
  - `GET /api/transfers` añade `type` por entrada; internas conservan `direction {from,to}` +
    estados MAYÚSCULAS; ACH añaden `beneficiary` (enmascarado) + estados minúsculas. Sin
    renombrar/eliminar campos internos.
  - _Requisitos: 6.1, 6.2, 6.3, 6.4, 6.5_ · _Contrato: ACH-05, ACH-09; A01, A07_ ·
    _Decisión: D03, D05_

- [ ] 26. **(verificación)** Pruebas de ACH: éxito, fallo, reintentos e idempotencia
  - Routing 8/no numérico rechazado, 9 aceptado (A05); cuenta 3/18 rechazada, 4–17 aceptada
    (A06); `pending` debita una vez, settlement no re-debita (A07); fallo reembolsa una vez aun
    con transición reintentada (A08); sin débito antes de MFA; montos inválidos rechazados (A09);
    enmascarado en respuestas.
  - _Requisitos: 1–7_ · _Contrato: ACH-01..10; A03–A09_

---

## Fase E — Pagos recurrentes y scheduler autónomo

> Depende de: Fases B, C, D (esquema, límites, ciclo ACH reutilizado por recurrentes ACH).

- [ ] 27. Implementar la creación y persistencia de schedules (`recurring_service.py`, `repository.py`)
  - Crear schedule interno o ACH con origen/destino/monto/frecuencia válidos; estado inicial
    `active`; primera ejecución: fecha futura dada = primer vencimiento; omitida = creación + un
    intervalo completo (nunca inmediata). Snapshot de beneficiario para ACH (REC-11).
  - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7_ · _Contrato: REC-01..04, REC-11; A15, A16_

- [ ] 28. Implementar la autorización MFA en la creación de schedules sensibles
  - Si monto ≥ umbral: exigir MFA al crear; marcar `authorized=1`. Las ejecuciones automáticas no
    piden MFA interactiva.
  - _Requisitos: 8.6, 11.4_ · _Contrato: REC-09_ · _Decisión: D04, D02_

- [ ] 29. Implementar los controles de ciclo de vida y la reanudación sin catch-up (D06)
  - Pausar (`active→paused`), reanudar (`paused→active` recalculando `next_run_at` desde la
    reanudación, saltando ocurrencias perdidas, sin débitos acumulados), cancelar
    (`→cancelled`, terminal). Rechazar reanudar/modificar `cancelled` (`INVALID_STATE_TRANSITION`).
  - _Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_ · _Contrato: REC-06, REC-07, REC-08; A18_ ·
    _Decisión: D06_

- [ ] 30. Implementar la ejecución durable y atómica de ocurrencias (`recurring_service.process_due`)
  - Función **pura** `process_due(conn, now)` que, por cada schedule `active` con `next_run_at <=
    now`, en **una** transacción `BEGIN IMMEDIATE`: `INSERT` en `schedule_execution(schedule_id,
    due_at)` (la `UNIQUE` bloquea duplicados) → revalidar fondos/límites → crear movimiento
    (interno o ACH `pending`+débito) → avanzar `next_run_at`. Crash antes de COMMIT = ROLLBACK
    total; tras COMMIT, el reintento falla el INSERT.
  - _Requisitos: 10.3, 10.4, 11.1, 11.3_ · _Contrato: REC-05, ACH-08; A17, A19_ ·
    _Diseño: DD-7, F10_ · _Decisión: D07_

- [ ] 31. Implementar el manejo de fallo de negocio en la ejecución recurrente
  - Si la revalidación falla por fondos/límite: registrar `schedule_execution` con
    `outcome='failed'` **sin debitar** y avanzar `next_run_at` (no queda atascado).
  - _Requisitos: 11.2_ · _Contrato: REC-10; A19_

- [ ] 32. Implementar el scheduler de fondo (único worker) y su ciclo de vida (`scheduler.py`)
  - Una **única** tarea asyncio lanzada en `lifespan` (startup) que cada `SCHEDULER_TICK_SECONDS`
    invoca `process_due(now)` y el barrido de settlement ACH; cancelación limpia en shutdown;
    recuperación tras reinicio vía `next_run_at`/`schedule_execution`. Sin endpoint admin público.
  - _Requisitos: 10.1, 10.2, 10.6_ · _Contrato: REC-05; §3/§7_ · _Decisión: D02, D07_

- [ ] 33. Implementar los endpoints de recurrentes (`routers/recurring.py`)
  - `GET /api/recurring` (estado + próxima fecha), `POST /api/recurring`, `/pause`, `/resume`,
    `/cancel`.
  - _Requisitos: 12.1, 12.2_ · _Contrato: REC-12_

- [ ] 34. **(verificación)** Pruebas deterministas de recurrentes (reloj inyectable)
  - Diario sin fecha corre tras 1 día (A15); semanal/mensual 7/30 días (A16); internos y ACH
    ejecutan al vencer y actualizan saldo/movimientos/próxima fecha (A17); pausado no corre,
    reanudado elegible, cancelado terminal (A18); fallo por fondos/límite registra y avanza sin
    débito (A19); **exactamente-una-vez** ante doble tick / reintento / crash simulado (INSERT
    duplicado falla); reanudar sin catch-up (D06).
  - _Requisitos: 8–11_ · _Contrato: REC-01..12; A15–A19_ · _Diseño: DD-7_

---

## Fase F — Integración del frontend

> Depende de: Fases C, D, E (endpoints disponibles). Preserva la experiencia interna existente.

- [ ] 35. Extender el cliente de API y los tipos (`api/client.ts`, `types.ts`)
  - Funciones para beneficiarios, ACH (+mfa), recurrentes y límites; montos como `string`.
    `TransferHistoryItem` con `direction` opcional + `type` + `beneficiary?`; sin romper tipos
    internos.
  - _Requisitos: 6, 7, 12, 13, 16.2_ · _Diseño: UI-1_

- [ ] 36. Añadir navegación por secciones sin romper la vista interna (`App.tsx`)
  - Paneles/tabs para Transferencias, ACH, Beneficiarios, Recurrentes, Límites, Historial;
    preservar `AccountsPanel`/`TransferForm`/`HistoryList` existentes.
  - _Requisitos: 16.2, 7.1_ · _Contrato: ACH-09; A21_

- [ ] 37. Implementar el formulario ACH y la gestión de beneficiarios (`AchTransferForm.tsx`, `BeneficiariesPanel.tsx`)
  - Selección guardado/ad hoc, validación inmediata de routing/cuenta (bloquea envío), opción de
    guardar, reutilizar `MfaDialog` para ACH sensibles.
  - _Requisitos: 2.4, 7.1, 7.2, 7.3_ · _Contrato: ACH-09, ACH-10; A04, A05, A06_

- [ ] 38. Extender el historial para internas y ACH (`HistoryList.tsx`)
  - Renderizado condicional por `type`: internas con `direction`; ACH con beneficiario
    enmascarado + estado; extender `STATUS_LABEL` con etiquetas ACH (`pending`/`settled`/
    `failed`/`pending_auth`/`expired`) conservando el fallback.
  - _Requisitos: 6.1, 6.2, 6.3, 7.4_ · _Diseño: UI-1_ · _Decisión: D03, D05_

- [ ] 39. Implementar los paneles de recurrentes y de límites (`RecurringPanel.tsx`, `LimitsPanel.tsx`)
  - Recurrentes: crear, listar estado + próxima fecha, pausar/reanudar/cancelar con feedback.
    Límites: ver/editar, mostrar consumo del día y disponibilidad; feedback de carga/validación/
    éxito/error en toda la UI nueva.
  - _Requisitos: 12.1, 12.2, 12.3, 13.2, 13.3_ · _Contrato: REC-12, LIM-02; A21_

---

## Fase G — Verificación final y evidencia experimental

> Depende de: todas las fases anteriores. Solo verificación y registro; no cambia comportamiento.

- [ ] 40. **(verificación)** Ejecutar la suite de regresión de la Etapa 1
  - Re-ejecutar las pruebas de la Fase A sobre la aplicación extendida; confirmar cero
    regresiones en cuentas, internas, MFA e historial.
  - _Requisitos: 15.1–15.8_ · _Contrato: HER-01..06; A01, A02, A20_

- [ ] 41. **(verificación)** Ejecutar la suite completa de aceptación de la Etapa 2
  - Ejecutar todas las pruebas de C, D, E; mapear cada escenario **A01–A19** a su prueba y
    registrar PASS/FAIL reales.
  - _Requisitos: 1–14_ · _Contrato: A01–A19_

- [ ] 42. **(verificación)** A20 — build de producción del frontend + suite completa
  - Ejecutar `npm run build` (tsc + vite) y la suite backend completa; registrar salidas reales.
  - _Contrato: A20_

- [ ] 43. **(verificación)** A21 — inspección manual en navegador
  - Verificar navegación, formularios, validación inmediata, estados ACH y controles de
    schedules; registrar lo realmente observado (no inventar).
  - _Contrato: A21_

- [ ] 44. **(verificación)** Integridad de BD y preservación de datos de la Etapa 1
  - Confirmar que los saldos y transacciones históricas sembradas sobreviven a la migración y a
    la operación sin alteración.
  - _Requisitos: 15.8, 16.3_ · _Contrato: HER-01, HER-05_

- [ ] 45. Registrar resultados reales, iteraciones correctivas y limitaciones
  - Consignar en `_experiment_logs/Kiro/pruebas/` los PASS/FAIL, fallos encontrados,
    correcciones aplicadas y limitaciones remanentes. Sin fabricar resultados ni métricas.
  - _Contrato: A20, §7_

- [ ] 46. Recolectar evidencia estandarizada (código, pruebas, análisis estático)
  - Reunir la evidencia disponible de código/pruebas/análisis estático para las métricas del
    proyecto (p. ej. carpeta `sonarqube/`), sin modificar ni fabricar registros históricos.
  - _Contrato: §7_

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
