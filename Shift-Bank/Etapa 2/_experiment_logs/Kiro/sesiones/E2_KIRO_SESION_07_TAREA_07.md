# E2 · Kiro · Sesión de implementación 07 — Tarea 7

- **Fecha:** 2026-11-16
- **Tarea:** 7 — Migración idempotente y transaccional del esquema SQLite (`db.py`)
- **Objetivo y alcance:** evolución aditiva de la tabla heredada `transfer` (columnas de Etapa 2)
  mediante una función `migrate` transaccional, idempotente y no destructiva. **Primera tarea
  que modifica código de aplicación heredado.**
- **Estado final:** COMPLETED

## Refinamiento de seguimiento T-1 (auditoría del plan)

La Tarea 7 agrupaba varias operaciones en una sola casilla. Se dividió en subtareas nativas de
Kiro **solo para la Tarea 7**, preservando su alcance y referencias, sin reestructurar 8–46 ni
cambiar el total de 46 tareas de nivel superior:

- 7.1 andamiaje transaccional `migrate` (BEGIN/COMMIT/ROLLBACK, idempotente).
- 7.2 helper `_column_exists` (PRAGMA table_info) antes de `ALTER TABLE ADD COLUMN`.
- 7.3 añadir columnas nuevas a `transfer` (`type` con DEFAULT 'internal', `beneficiary_id`,
  `beneficiary_snapshot`, `settled_at`, `refunded`, `schedule_id`).
- 7.4 backfill `UPDATE transfer SET type='internal' WHERE type IS NULL`.
- 7.5 enganche tras `init_schema` en el arranque.

Las 5 subtareas quedaron marcadas `[x]`.

## Frontera Tarea 7 / Tarea 8 (dependencia reportada, no implementada)

El `tasks.md` solapaba "crear tablas nuevas" (mencionado en T7) con "definir el esquema de las
tablas nuevas con FKs/unicidad/índices" (T8). Para respetar la instrucción de no implementar lo
que pertenece a la Tarea 8: en la Tarea 7 se implementó **solo** el andamiaje transaccional y la
evolución de la tabla heredada `transfer`. El **DDL de `beneficiary`, `recurring_schedule`,
`schedule_execution`, `transfer_limit`** (con FKs, `UNIQUE(schedule_id, due_at)`, índices)
**queda para la Tarea 8** y NO se creó aquí. Esto se documentó explícitamente en `tasks.md`.

## Estado del repositorio

- **Commit (HEAD):** `da4209dc3ea9eda08f13de08abe29800bcdf6513` (sin commit nuevo en la sesión).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio antes y después.
- **Código de aplicación modificado (solo Tarea 7):** `backend/app/db.py`, `backend/app/main.py`.

## Hash de la base de datos histórica (antes y después)

- **Antes:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` (36 864 bytes).
- **Después:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` — **sin cambios**.
- Nota: el valor citado en la autorización de la Tarea 7
  (`407B0E132E76900FBF59412C31A2D8047A666F2BE1FF6B88531C89B4A8`) parece una transcripción
  truncada; el hash autoritativo recalculado es el de arriba (coincide con el del Checkpoint A).
- La DB histórica **nunca** se usó como objetivo de migración; es estrictamente de solo lectura.

## Cambios de código / esquema implementados

### `app/db.py` (+63 líneas)

- `_TRANSFER_NEW_COLUMNS`: lista de columnas nuevas de `transfer` con su cláusula de tipo.
- `_column_exists(conn, table, column)`: comprueba existencia vía `PRAGMA table_info`.
- `migrate(conn)`: dentro de `BEGIN … COMMIT` (con `ROLLBACK` ante excepción):
  - `ALTER TABLE transfer ADD COLUMN <c> <tipo>` para cada columna ausente:
    `type TEXT NOT NULL DEFAULT 'internal'`, `beneficiary_id TEXT`, `beneficiary_snapshot TEXT`,
    `settled_at TEXT`, `refunded INTEGER NOT NULL DEFAULT 0`, `schedule_id TEXT`.
  - `UPDATE transfer SET type='internal' WHERE type IS NULL` (backfill de robustez).

### `app/main.py` (+2 / −1)

- `from .db import ... migrate`.
- Llamada `migrate(conn)` en el `_startup`, entre `init_schema(conn)` y `seed(conn)`. **No** se
  cambió el mecanismo de arranque (`@app.on_event("startup")`); su migración a `lifespan`
  corresponde a la Tarea 12.

Resumen del diff: `db.py | 63 +`, `main.py | 3 (+2/−1)`. Cambios aditivos, sin eliminar ni
modificar lógica existente. No se introdujo ORM ni otro motor de almacenamiento; se preservan
`get_connection`, centavos `INTEGER` y las convenciones monetarias.

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_migration.py -v` → **6 passed in 0.25s** (exit 0).
2. `python -m pytest` (suite completa) → **57 passed, 101 warnings in 3.13s** (exit 0):
   51 de regresión (Fase A) + 6 de migración. **Passed 57 · Failed 0 · Skipped 0.**

## Resultados de verificación de la migración (Tarea 7, no la suite de la Tarea 13)

- `test_migracion_exitosa_sobre_esquema_heredado` — añade las 6 columnas sobre un esquema de E1.
- `test_migracion_idempotente` — segunda ejecución no cambia el conjunto de columnas.
- `test_saldos_y_historicas_preservadas` — saldos y las 2 históricas idénticos antes/después.
- `test_clasificacion_type_internal` — filas heredadas quedan `type='internal'` (ninguna NULL).
- `test_rollback_ante_fallo` — fallo simulado a mitad → ROLLBACK total, esquema sin cambios.
- `test_acceso_tras_migracion_con_conexion_heredada` — `get_connection()` sigue operando; la
  columna nueva es consultable.

Cada prueba usa una DB temporal con el esquema heredado de E1 (equivalente a una copia), nunca
la DB histórica.

## Comportamiento de regresión tras la migración

Las 51 pruebas de regresión de la Fase A siguen **verdes**. En particular, las aserciones
estrictas del historial (Tarea 5, "sin campo `type` en la respuesta") **siguen pasando**: la
Tarea 7 modifica solo el **esquema de BD**, no el router ni el schema de respuesta
`TransferHistoryItem`, por lo que la API no expone aún `type`. Coherente con la consideración de
compatibilidad futura documentada en el Checkpoint A (el ajuste "Stage 2-aware" se hará en la
Tarea 25). No se debilitó ni eliminó ninguna aserción.

## Evidencia de aislamiento y preservación de la Etapa 1

- DB histórica: SHA-256 idéntico antes/después; no fue objetivo de migración.
- `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales residuales.
- `Etapa 1/Kiro` git limpio. Solo se modificaron `app/db.py` y `app/main.py` en la copia de E2.

## Errores y correcciones

- Ninguno. Las 6 pruebas de migración y las 57 de la suite pasaron en la primera ejecución.

## Métricas

- **Duración de la sesión:** N/D (no instrumentada). pytest: 0,25 s (T7) y 3,13 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Archivos creados / modificados en esta tarea

| Acción | Archivo |
|---|---|
| Modificado | `Etapa 2/Kiro/backend/app/db.py` (migración) |
| Modificado | `Etapa 2/Kiro/backend/app/main.py` (enganche en startup) |
| Creado | `Etapa 2/Kiro/backend/tests/test_migration.py` (6 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (subtareas 7.x + Tarea 7) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_07_TAREA_07.md` (este registro) |

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 7 (y su refinamiento T-1). Tareas 8–46 sin iniciar y sin marcar;
  Tareas 1–6 preservadas.
- No se definió el DDL de las tablas nuevas (Tarea 8); no se implementaron beneficiarios,
  límites, ACH, recurrentes ni scheduler; no se modificaron requisitos/diseño ni la Etapa 1 ni
  registros previos; sin dependencias nuevas; sin ORM ni cambios de arquitectura.
- **No** se reclama que la suite de migración completa (Tarea 13) esté pasada.
