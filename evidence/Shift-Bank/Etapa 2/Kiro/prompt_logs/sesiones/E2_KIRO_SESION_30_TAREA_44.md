# E2 · Kiro · Sesión de implementación 30 — Tarea 44

- **Fecha:** 2026-11-16
- **Tarea:** 44 — (verificación) Integridad de BD y preservación de datos de la Etapa 1
- **Fase:** G — Verificación final y evidencia experimental
- **Objetivo:** Confirmar que los **saldos** y las **transacciones históricas** sembradas
  sobreviven a la migración de la Etapa 2 y a la operación normal **sin alteración**, y que la
  **DB histórica original** de la Etapa 1 nunca se modifica.
- **Alcance autorizado:** solo Tarea 44. Tarea de **verificación/evidencia pura**; **sin
  modificar código de producción**, pruebas, requisitos ni diseño.
- **Estado final:** COMPLETED — todas las verificaciones PASS; DB histórica E1 intacta.
- **Requisitos:** 15.8, 16.3 · **Contrato:** HER-01, HER-05.

## Naturaleza de la tarea

Tarea puramente de **verificación**. No crea ni modifica código de aplicación. Ejecuta las
pruebas de migración/preservación ya existentes y, además, una verificación independiente que
migra una **copia** de la DB histórica real de la Etapa 1 y comprueba de primera mano la
preservación de datos. Como evidencia de no-manipulación, se registra el SHA-256 de la DB
histórica antes y después de toda la sesión.

## Entorno de ejecución

- Ejecutado desde `Etapa 2/Kiro/backend` con el intérprete del entorno virtual
  (`.venv\Scripts\python.exe`).
- **Python 3.13.2**, **pytest 8.3.4**.
- **SO:** Windows; shell PowerShell.
- DB histórica de referencia: `Etapa 1/Kiro/backend/shift_bank.db` (36.864 bytes).

## Evidencia 1 — SHA-256 de la DB histórica (no manipulación)

| Momento | SHA-256 |
|---|---|
| Antes de la sesión | `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` |
| Después de la sesión | `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` |

Hash **idéntico** antes y después, e idéntico al registrado en las sesiones de la Fase D y en las
Tareas 40–42. La DB histórica de la Etapa 1 **nunca fue tocada**. Todas las pruebas y la
verificación independiente operan sobre **copias** en directorios temporales o sobre DB SQLite
temporales aisladas por fixture.

## Evidencia 2 — Suite de migración y preservación (pytest)

Comando:

```
.\.venv\Scripts\python.exe -m pytest tests/test_migration.py tests/test_migration_suite.py \
    tests/test_schema_stage2.py tests/test_regression_accounts.py \
    tests/test_regression_api_contracts.py -v
```

Resultado real: **46 passed, 0 failed, 0 skipped**, 1 warning (exit 0). Desglose:

- `tests/test_migration.py` — 6/6 PASS. Incluye `test_saldos_y_historicas_preservadas`
  (saldos y transferencias idénticos antes/después), `test_migracion_idempotente`,
  `test_clasificacion_type_internal`, `test_rollback_ante_fallo`.
- `tests/test_migration_suite.py` — 7/7 PASS. Incluye
  `test_migracion_sobre_copia_real_de_db_historica` (migra una **copia real** de la DB histórica
  de E1, verifica saldos/nº de transferencias intactos, tablas nuevas presentes y el SHA-256 de
  la original sin cambios), E2E, idempotencia en múltiples arranques, `seed_limits` y `lifespan`.
- `tests/test_schema_stage2.py` — 12/12 PASS. Incluye
  `test_saldos_y_historicas_intactos_tras_tarea8` y `test_rollback_no_deja_tablas_parciales`.
- `tests/test_regression_accounts.py` — 8/8 PASS. Saldos iniciales heredados, decimal-string de
  2 decimales, lectura que no altera saldos, sin IDs internos.
- `tests/test_regression_api_contracts.py` — 13/13 PASS. Historial con las históricas sembradas,
  estados en MAYÚSCULAS, `direction {from,to}`, sin identificadores internos.

Advertencia no bloqueante: 1 `DeprecationWarning` de `anyio.abc.BlockingPortal` (alias usado por
`starlette.testclient`); dependiente de la librería, no del código de la aplicación.

## Evidencia 3 — Verificación independiente sobre copia real de la DB histórica

Script efímero (creado y **eliminado** al terminar; no persiste en el repositorio) que copió la
DB histórica real a un directorio temporal, aplicó `app.db.migrate()` a la **copia**, re-migró
para comprobar idempotencia y verificó 9 invariantes. La DB histórica solo se abrió para copiar.

Estado observado de la DB histórica real (vía la copia):

- Saldos: `checking = 1.439.999.999` centavos; `savings = 560.000.001` centavos.
- Transferencias históricas: **11** filas.

Resultados (los 9 checks en **PASS**):

| Check | Resultado |
|---|---|
| Saldos idénticos antes/después de migrar | OK |
| Transferencias históricas idénticas (campo a campo, columnas E1) | OK |
| Idempotencia de saldos (re-migrar no cambia nada) | OK |
| Idempotencia de históricas | OK |
| Tablas nuevas presentes (`beneficiary`, `recurring_schedule`, `transfer_limit`, `schedule_execution`) | OK |
| Índices nuevos presentes (`idx_transfer_created_at`, `idx_transfer_type_status`, `idx_schedule_due`, `idx_beneficiary_customer`) | OK |
| Columnas nuevas en `transfer` (`type`, `beneficiary_id`, `beneficiary_snapshot`, `settled_at`, `refunded`, `schedule_id`) | OK |
| Filas heredadas clasificadas como `type='internal'` | OK |
| DB histórica ORIGINAL no tocada (SHA-256 igual) | OK |

Tablas tras migrar la copia: `account, beneficiary, customer, recurring_schedule,
schedule_execution, transfer, transfer_limit`. Saldos tras migrar: idénticos a los de antes
(`checking=1.439.999.999`, `savings=560.000.001`).

## Mapeo a requisitos y contrato

- **Req. 15.8** — El sistema no modifica los saldos heredados ni las transacciones históricas:
  verificado por los saldos/filas idénticos antes/después (pytest + verificación independiente) y
  por el SHA-256 invariante de la DB original.
- **Req. 16.3** — Migración aditiva que preserva los datos existentes: tablas/columnas/índices
  nuevos presentes, datos heredados intactos, idempotencia y rollback comprobados.
- **HER-01** — Cuentas, saldos, historial y modelo monetario (centavos enteros) heredados siguen
  funcionando sin cambios de forma: verificado por las pruebas de regresión de cuentas y de
  contrato de API.
- **HER-05** — Los fallos no dejan saldos ni estados inconsistentes: la migración es
  transaccional con ROLLBACK total ante fallo (`test_rollback_ante_fallo`,
  `test_rollback_no_deja_tablas_parciales`).

## Errores y correcciones

- Ninguno. Las 46 pruebas y las 9 verificaciones independientes pasaron en la primera ejecución.
  No se corrigió comportamiento ni se tocó ninguna prueba ni código de aplicación.

## No modificación de código de producción

Esta sesión solo ejecutó `pytest` (lectura) y un script de verificación efímero sobre una copia
temporal. El script fue **eliminado** al terminar. No se editó `app/`, ni las pruebas, ni el
frontend, ni la Etapa 1. Único artefacto persistente: este registro de evidencia y la marca de la
Tarea 44 en `tasks.md`.

## Métricas

- **Resultados:** 46/46 pruebas de migración/preservación/regresión PASS (exit 0) · 9/9
  verificaciones independientes PASS · 0 FAIL · 0 SKIP.
- **DB histórica E1:** SHA-256 `407B0E13…` sin cambios antes y después.
- **Duración:** N/D (no instrumentada). pytest reportó 2,54 s.
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 44. Las Tareas 43, 45 y 46 quedan según su estado previo; las Tareas
  1–42 se preservan intactas.
- No se modificó código de aplicación, pruebas, requisitos, diseño, la Etapa 1 ni registros
  previos. Sin dependencias nuevas.
