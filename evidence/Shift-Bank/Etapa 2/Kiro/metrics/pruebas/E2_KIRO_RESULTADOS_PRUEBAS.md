# E2 · Kiro · Resultados reales, iteraciones correctivas y limitaciones (Tarea 45)

- **Fecha de consolidación:** 2026-11-16
- **Tarea:** 45 — Registrar resultados reales, iteraciones correctivas y limitaciones
- **Fase:** G — Verificación final y evidencia experimental
- **Contrato:** A20, §7
- **Naturaleza:** registro de **consolidación de evidencia**. No crea ni modifica código de
  aplicación, pruebas, requisitos ni diseño. Reúne los PASS/FAIL **reales**, los fallos
  encontrados, las correcciones aplicadas y las limitaciones remanentes ya documentados en las
  sesiones 01–30, y **vuelve a ejecutar** la suite para citar números frescos. **No se fabrican
  resultados ni métricas.**

> Fuentes primarias: las sesiones de implementación en
> `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_01..30_*.md` y las decisiones
> `_experiment_logs/Kiro/decisiones/E2-KIRO-D01..D07_*.md`. Este documento **no** reescribe esas
> fuentes; las resume y referencia.

---

## 1. Entorno de ejecución (re-verificado en esta sesión)

- Backend ejecutado desde `Etapa 2/Kiro/backend` con el intérprete del entorno virtual
  (`.venv\Scripts\python.exe`).
- **Python 3.13.2**, **pytest 8.3.4**.
- Frontend (build de producción, Tarea 42): **Node v24.19.0**, **npm 11.17.0**, **vite v5.4.21**,
  TypeScript ^5.6.3.
- **SO:** Windows; shell PowerShell.
- Pruebas sobre **DB SQLite temporales aisladas** por fixture; reloj inyectable `ManualClock`
  para los escenarios deterministas (recurrentes/settlement). Ninguna prueba toca la DB histórica
  de la Etapa 1.

---

## 2. Resultados reales de PASS/FAIL

### 2.1 Re-ejecución fresca en esta sesión (Tarea 45)

| Comando | Resultado | Exit |
|---|---|---|
| `python -m pytest -q` (suite completa) | **220 passed, 0 failed, 0 skipped, 1 warning** (14,12 s) | 0 |
| `python -m pytest tests/test_regression_accounts.py tests/test_regression_internal_transfers.py tests/test_regression_mfa.py tests/test_regression_api_contracts.py tests/test_harness.py -q` (regresión Fase A) | **51 passed, 0 failed, 0 skipped, 1 warning** (3,75 s) | 0 |

Estos números coinciden con los registrados en las Tareas 40–42 y 44, confirmando la
estabilidad de la suite. La única advertencia es un `DeprecationWarning` de
`anyio.abc.BlockingPortal` (alias usado por `starlette.testclient`); depende de la librería, no
del código de la aplicación, y no afecta a los resultados ni al código de salida.

### 2.2 Inventario completo de pruebas por archivo (recuento fresco `--collect-only`)

| Archivo | Dominio | Pruebas |
|---|---|---:|
| `tests/test_harness.py` | Arnés / aislamiento de DB temporal | 4 |
| `tests/test_regression_accounts.py` | Fase A — cuentas y saldos iniciales | 8 |
| `tests/test_regression_internal_transfers.py` | Fase A — transferencias internas heredadas | 12 |
| `tests/test_regression_mfa.py` | Fase A — MFA heredada | 14 |
| `tests/test_regression_api_contracts.py` | Fase A — contratos de API e historial | 13 |
| `tests/test_migration.py` | Fase B — migración idempotente/transaccional | 6 |
| `tests/test_schema_stage2.py` | Fase B — esquema de tablas nuevas | 12 |
| `tests/test_clock.py` | Fase B — reloj inyectable | 10 |
| `tests/test_txn.py` | Fase B — transacción financiera reutilizable | 9 |
| `tests/test_migration_suite.py` | Fase B — migración sobre copia real + E2E | 7 |
| `tests/test_limits.py` | Fase C — límites dinámicos y concurrencia | 11 |
| `tests/test_ach.py` | Fase D — beneficiarios + ACH | 16 |
| `tests/test_recurring.py` | Fase E — creación/MFA/ciclo de vida | 37 |
| `tests/test_recurring_execution.py` | Fase E — ejecución durable y atómica | 18 |
| `tests/test_recurring_api.py` | Fase E — endpoints recurrentes | 14 |
| `tests/test_recurring_verification.py` | Fase E — verificación A15–A19/D06/una-vez | 21 |
| `tests/test_scheduler.py` | Fase E — scheduler de fondo (único worker) | 8 |
| **Total** | | **220** |

> Nota: `test_recurring_verification.py` reporta **21** pruebas en el recuento fresco de esta
> sesión (la Tarea 41 había citado 20); la suma real sigue dando **220** en total y la suite
> completa pasa 220/220. Se cita el número observado en esta re-ejecución.

### 2.3 Hitos de verificación consolidados (números reales de las sesiones 06, 27–30)

| Hito | Fuente | Resultado real | Exit |
|---|---|---|---|
| Checkpoint A — baseline de regresión E1 | Sesión 06 (Tarea 6) | 51/51 PASS | 0 |
| Regresión E1 sobre la app extendida | Sesión 27 (Tarea 40) | 51/51 PASS · suite 220/220 PASS | 0 |
| Aceptación A01–A19 mapeada a prueba | Sesión 28 (Tarea 41) | 19/19 escenarios verdes · suite 220/220 PASS | 0 |
| A20 — build de producción del frontend | Sesión 29 (Tarea 42) | `tsc && vite build` OK, 41 módulos, artefactos en `dist/` | 0 |
| A20 — suite backend completa | Sesión 29 (Tarea 42) | 220/220 PASS | 0 |
| Integridad de BD / preservación E1 | Sesión 30 (Tarea 44) | 46/46 PASS pytest · 9/9 checks independientes | 0 |

#### Artefactos del build de producción del frontend (Tarea 42, reales)

| Artefacto | Tamaño | gzip |
|---|---:|---:|
| `dist/index.html` | 395 bytes | 0,27 kB |
| `dist/assets/index-CX77R-vI.css` | 4.521 bytes | 1,38 kB |
| `dist/assets/index-BufvD_Q2.js` | 169.917 bytes | 52,58 kB |

### 2.4 Mapa de aceptación A01–A19 → resultado

Los 19 escenarios de aceptación A01–A19 quedan mapeados a una o más pruebas automatizadas, todas
en **PASS**. La tabla detallada escenario → prueba(s) consta en la Sesión 28 (Tarea 41). Resumen:

| Escenario | Dominio | Resultado |
|---|---|---|
| A01 | Historial unificado / contratos | PASS |
| A02 | Transferencias internas heredadas | PASS |
| A03 | Beneficiarios (enmascarado) | PASS |
| A04 | ACH beneficiario guardado/ad hoc | PASS |
| A05 | Validación de routing (9 dígitos) | PASS |
| A06 | Validación de nº de cuenta (4–17) | PASS |
| A07 | ACH `pending`→`settled`, débito una vez | PASS |
| A08 | ACH `failed` + reembolso exactamente-una-vez | PASS |
| A09 | ACH rechaza monto inválido | PASS |
| A10 | Lectura/actualización de límites (D01) | PASS |
| A11 | Frontera exacta por transferencia | PASS |
| A12 | Consumo diario acumulado (400+300+300) | PASS |
| A13 | MFA heredada aplicada a ACH sensible | PASS |
| A14 | PIN correcto no salta el límite | PASS |
| A15 | Recurrente diario sin fecha corre tras 1 día | PASS |
| A16 | Frecuencia semanal/mensual (7/30 días) | PASS |
| A17 | Ejecución interna/ACH al vencer | PASS |
| A18 | Pausar/reanudar/cancelar (ciclo de vida) | PASS |
| A19 | Fallo por fondos/límite registra y avanza sin débito | PASS |

**Cobertura:** 19/19 escenarios con al menos una prueba verde; ninguno en FAIL.

### Garantías transversales verificadas (relacionadas con A07/A08/A17/A19)

- **Exactamente-una-vez** ante doble tick / reintento / crash simulado e INSERT duplicado que
  viola `UNIQUE(schedule_id, due_at)` (Sesión 28).
- **Reanudar sin catch-up (D06):** recalcula `next_run_at` desde la reanudación, sin ejecutar
  ocurrencias perdidas (Sesión 28).
- **Concurrencia de límites (T-8):** dos operaciones concurrentes (conexiones distintas) no
  superan juntas el límite diario/saldo, por serialización `BEGIN IMMEDIATE` (Sesión 28).
- **Scheduler de único worker:** arranque/parada/recuperación, sin endpoint admin público
  (8/8 en `test_scheduler.py`).

---

## 3. Fallos encontrados y correcciones aplicadas (iteraciones correctivas reales)

Durante la implementación solo se registró **una** iteración correctiva de código detectada por
las pruebas. Las demás tareas pasaron en la primera ejecución. No se fabrican fallos.

### 3.1 Tarea 8 — orden de migración incorrecto (índice sobre columna aún no creada)

- **Fuente:** Sesión 08 (Tarea 8).
- **Defecto detectado por la prueba:** la primera ejecución de `tests/test_schema_stage2.py` dio
  **11 failed, 1 passed** con `sqlite3.OperationalError: no such column: type` al crear el índice
  `idx_transfer_type_status` **antes** del `ALTER TABLE transfer ADD COLUMN type`. La suite
  completa también falló porque el arranque invoca `migrate`.
- **Diagnóstico:** defecto de **mi** implementación de la Tarea 8 (no del baseline heredado):
  dentro de la transacción de `migrate` los índices se creaban antes del `ALTER` que añade la
  columna `type`.
- **Corrección aplicada:** reordenar `migrate` para crear los índices **al final**, tras
  `CREATE TABLE` → `ALTER TABLE transfer ADD COLUMN` → backfill de `type`. No se debilitó ni
  eliminó ninguna aserción; el fallo se resolvió **corrigiendo el código**, no el test.
- **Resultado tras la corrección:** `tests/test_schema_stage2.py` 12/12 PASS; suite completa
  69/69 PASS en ese punto.

### 3.2 Decisión de ubicación en la Tarea 10 (no es un fallo; es una desviación justificada)

- **Fuente:** Sesión 10 (Tarea 10).
- **Situación:** el `tasks.md` nombraba la Tarea 10 "(`repository.py`)". Para **no alterar**
  `apply_transfer` ni el comportamiento heredado (regla explícita de la tarea y condición de las
  51 pruebas de regresión), el helper transaccional `financial_transaction` se implementó en un
  **módulo nuevo** `app/txn.py` en lugar de modificar `repository.py`.
- **Efecto:** `repository.py` quedó **sin cambios**; las 9 pruebas de `tests/test_txn.py` y las
  88 de la suite pasaron en la primera ejecución. No hubo iteración correctiva; se registra como
  decisión de diseño que preserva el baseline.

### 3.3 Síntesis de "sin correcciones" por sesión

Las sesiones 01–07, 09–30 registran explícitamente "Ninguno" en su apartado de errores y
correcciones: las pruebas pasaron en la primera ejecución. La única corrección de código fue la
de §3.1 (Tarea 8). No se corrigió comportamiento ni se tocó ninguna prueba en las tareas de
verificación (40–44).

---

## 4. Limitaciones remanentes y advertencias conocidas

Todas documentadas en sus sesiones de origen; se consolidan aquí sin ampliarlas.

### 4.1 F13 — FKs no declarables sobre columnas añadidas por `ALTER` en `transfer`

- **Fuente:** Sesión 08 (Tarea 8), Diseño F13.
- Las columnas `transfer.beneficiary_id` y `transfer.schedule_id` se añadieron por
  `ALTER TABLE ADD COLUMN`. SQLite **no** permite añadir una cláusula FK a una tabla existente
  sin reconstruirla. Para **no** reconstruir destructivamente la tabla heredada `transfer`
  (riesgo para sus datos y su contrato, Req. 15.8), esas dos referencias **no** llevan FK
  declarada a nivel de esquema; su integridad se garantiza a nivel de servicio. Todas las FKs
  entre las tablas **nuevas** sí se declaran. Limitación aceptada y mínima respecto al diseño
  aprobado.

### 4.2 Campo aditivo `type` en el historial unificado

- **Fuente:** Sesiones 06 (Checkpoint A) y 27 (Tarea 40); decisiones D03/D05.
- El único cambio observable respecto a la Etapa 1 en `GET /api/transfers` es el campo
  **aditivo** `type` por entrada (y `beneficiary` solo en entradas ACH). No altera los valores
  heredados (nombres amigables en `direction {from,to}`, estados internos en MAYÚSCULAS, montos
  decimal-string, ausencia de IDs internos y de saldo resultante). Las dos aserciones de snapshot
  estricto de la Fase A se adaptaron de forma aditiva en la Tarea 25 (seguir verificando los
  campos heredados; permitir el campo aditivo), documentado como adaptación planificada, no como
  corrección de regresión.

### 4.3 A21 — inspección manual en navegador pendiente

- **Fuente:** `tasks.md` Tarea 43 (estado `[-]`, no completada).
- La verificación A20 cubre el **build de producción** (Tarea 42, exit 0) y la suite completa
  (220/220). La inspección manual interactiva del navegador (A21 — navegación, formularios,
  validación inmediata, estados ACH, controles de schedules) es la Tarea 43 y **queda
  pendiente**; no se ha ejecutado ni se inventan observaciones para ella.

### 4.4 Advertencia no bloqueante de dependencia

- `DeprecationWarning: anyio.abc.BlockingPortal` emitido por `starlette.testclient`. Depende de
  la librería, no del código de la aplicación; no afecta resultados ni códigos de salida. (El
  patrón heredado `@app.on_event` que generaba ~101 warnings en la Fase A se eliminó al migrar a
  `lifespan` en la Tarea 12.)

### 4.5 Métricas no instrumentadas

- Duración de sesión, tokens, créditos e interacciones de herramientas **no** están expuestos al
  agente y **no** se estiman (se marcan N/D en todas las sesiones). Los únicos tiempos reales son
  los que reporta cada herramienta (p. ej. pytest 14,12 s en esta re-ejecución).

---

## 5. Preservación de la Etapa 1 (evidencia de no manipulación)

- **DB histórica `Etapa 1/Kiro/backend/shift_bank.db`:** SHA-256
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8`, **36.864 bytes** —
  recalculado en esta sesión e **idéntico** al registrado en las Sesiones 06, 08, 10 y 27–30. La
  DB histórica nunca fue objetivo de migración ni abierta por las pruebas.
- **`Etapa 2/Kiro/backend`:** no existen archivos `*.db`; las pruebas usan DB SQLite temporales
  aisladas; sin residuos.
- **Código de producción:** esta tarea solo ejecutó `pytest` (lectura) y escribió este registro;
  no se editó `app/`, ni las pruebas, ni el frontend, ni la Etapa 1.

---

## 6. Veredicto de la Tarea 45

Consolidación completada con datos **reales y verificados**:

- Suite backend completa: **220/220 PASS** (exit 0, re-ejecución fresca).
- Regresión Fase A: **51/51 PASS** (exit 0, re-ejecución fresca).
- Aceptación A01–A19: **19/19 escenarios verdes** (Tarea 41).
- Build de producción del frontend: **exit 0** con artefactos en `dist/` (Tarea 42).
- Integridad/preservación de datos de E1: **46/46 PASS + 9/9 checks**; DB histórica intacta
  (SHA-256 invariante).
- Iteraciones correctivas: **1** (orden de migración en la Tarea 8), resuelta corrigiendo el
  código.
- Limitaciones remanentes: F13 (FK por ALTER), campo aditivo `type`, **A21 manual pendiente**,
  advertencia de dependencia no bloqueante, métricas no instrumentadas.

Sin fabricar resultados ni métricas; sin modificar código de producción, pruebas, requisitos,
diseño, la Etapa 1 ni registros previos.

## 7. Archivos creados / modificados en esta tarea

| Acción | Archivo |
|---|---|
| Creado | `_experiment_logs/Kiro/pruebas/E2_KIRO_RESULTADOS_PRUEBAS.md` (este registro) |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (marca de la Tarea 45) |
