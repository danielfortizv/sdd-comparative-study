# E2 · Kiro · Sesión de implementación 08 — Tarea 8

- **Fecha:** 2026-11-16
- **Tarea:** 8 — Definir el esquema de las tablas nuevas con FKs, unicidad e índices
- **Objetivo:** implementar el DDL de las 4 tablas nuevas de la Etapa 2 (beneficiary,
  recurring_schedule, transfer_limit, schedule_execution) con sus FKs, `UNIQUE(schedule_id,
  due_at)` e índices, integrado en el `migrate` transaccional de la Tarea 7.
- **Estado final:** COMPLETED

## Aclaración de la frontera Tarea 7 / Tarea 8

El `tasks.md` original mencionaba en la Tarea 7 "crear las tablas" y en la Tarea 8 "definir su
esquema con FKs/unicidad/índices". La implementación de la Tarea 7 **difirió explícitamente** el
DDL de las 4 tablas a la Tarea 8 (documentado en `tasks.md` y en la sesión 07). Operaciones DDL
realmente diferidas desde la Tarea 7 e incluidas ahora en la Tarea 8:

- `CREATE TABLE IF NOT EXISTS` de `beneficiary`, `recurring_schedule`, `transfer_limit`,
  `schedule_execution` (esta última con `UNIQUE(schedule_id, due_at)`).
- `CREATE INDEX IF NOT EXISTS` de los 4 índices (F13).
- Las FKs declaradas en esas tablas.

**No** se reescribe la evidencia de la Tarea 7 ni se afirma que la Tarea 7 ya creó las 4 tablas:
la Tarea 7 solo añadió columnas a `transfer` y el andamiaje transaccional; las tablas se crean
aquí. No se amplía el alcance ni cambia el total de 46 tareas de nivel superior.

## Refinamiento de seguimiento T-1

La Tarea 8 se dividió en subtareas 8.1–8.7 (DDL por entidad, FKs+índices, integración en
`migrate`, verificación), sin reestructurar 9–46. Las 7 subtareas quedaron `[x]`.

## Estado del repositorio

- **Commit (HEAD):** `da4209dc3ea9eda08f13de08abe29800bcdf6513` (sin commit nuevo).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio antes y después.
- **Código de aplicación modificado en esta tarea:** `backend/app/db.py` (DDL añadido al
  módulo de migración). `main.py` no se modificó en la Tarea 8 (su cambio fue de la Tarea 7).

## Hash de la base de datos histórica (antes y después)

- **Antes:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8`.
- **Después:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` — **sin cambios**.
- La DB histórica nunca fue objetivo de migración.

## Esquema SQL implementado (tablas y columnas)

- **`beneficiary`**: id PK, customer_id (FK→customer), name, bank, routing_number,
  account_number, created_at, deleted_at (borrado lógico).
- **`recurring_schedule`**: id PK, customer_id (FK→customer), type, from_kind, to_kind,
  beneficiary_id (FK→beneficiary), beneficiary_snapshot, amount_cents, description, frequency,
  status, requires_mfa, authorized, next_run_at, created_at.
- **`transfer_limit`**: customer_id PK (FK→customer), per_transfer_cents, daily_cents,
  updated_at.
- **`schedule_execution`**: id PK, schedule_id (FK→recurring_schedule), due_at, outcome,
  transfer_id (FK→transfer), created_at, **`UNIQUE(schedule_id, due_at)`**.

Montos en centavos INTEGER; fechas ISO-8601 UTC.

## FKs, unicidad e índices implementados

- **FKs:** beneficiary→customer; recurring_schedule→{customer, beneficiary};
  schedule_execution→{recurring_schedule, transfer}; transfer_limit→customer. (Se aplican con
  `PRAGMA foreign_keys=ON`, ya activado por `get_connection`.)
- **Unicidad:** `schedule_execution UNIQUE(schedule_id, due_at)` (clave de la idempotencia
  durable, DD-7); `transfer_limit` PK por `customer_id`.
- **Índices:** `idx_transfer_created_at`, `idx_transfer_type_status`, `idx_schedule_due`
  (status, next_run_at), `idx_beneficiary_customer` (customer_id, deleted_at).

### Limitación documentada (F13)

Las columnas `transfer.beneficiary_id` y `transfer.schedule_id` se añadieron por `ALTER TABLE`
en la Tarea 7. SQLite **no** permite añadir una cláusula FK a una tabla existente sin
reconstruirla. Para **no** reconstruir destructivamente la tabla heredada `transfer` (lo que
pondría en riesgo sus datos y su contrato, Req. 15.8), esas dos referencias **no** llevan FK
declarada; su integridad se garantizará a nivel de servicio en tareas posteriores. Alternativa
mínima compatible con el diseño aprobado, documentada aquí. Todas las FKs entre las tablas
**nuevas** sí se declaran.

## Límites de la transacción de migración

Todo el DDL (tablas, ALTER de `transfer`, backfill, índices) ocurre dentro de la **única**
transacción `BEGIN … COMMIT` de `migrate`, con `ROLLBACK` ante excepción. **Orden** (corregido,
ver abajo): tablas nuevas → `ALTER TABLE transfer ADD COLUMN` → backfill de `type` → índices.
Se usa `conn.execute` por sentencia (no `executescript`, que haría COMMIT implícito y rompería
la atomicidad).

## Comandos ejecutados y resultados reales

1. (Primera ejecución) `python -m pytest tests/test_schema_stage2.py -v` → **11 failed, 1
   passed**: fallo real `sqlite3.OperationalError: no such column: type` al crear
   `idx_transfer_type_status` **antes** del `ALTER` que añade `type`. La suite completa también
   falló (el startup llama a `migrate`).
2. (Corrección) Reordenado `migrate`: índices **después** del `ALTER TABLE` de `transfer`.
3. (Tras corrección) `python -m pytest tests/test_schema_stage2.py -v` → **12 passed in 0.57s**
   (exit 0).
4. `python -m pytest` (suite completa) → **69 passed, 101 warnings in 3.91s** (exit 0):
   51 (regresión Fase A) + 6 (migración T7) + 12 (esquema T8). **Passed 69 · Failed 0 ·
   Skipped 0.**

## Iteración correctiva

- **Defecto detectado por las pruebas:** orden de migración incorrecto (índice sobre
  `transfer.type` creado antes de añadir la columna). Era un defecto de **mi implementación**,
  no del baseline heredado.
- **Corrección:** mover la creación de índices al final, tras el `ALTER` y el backfill. No se
  debilitó ni eliminó ninguna aserción; el fallo se resolvió corrigiendo el código, no el test.

## Resultados de verificación (Tarea 8, no la suite de la Tarea 13)

12 pruebas en `tests/test_schema_stage2.py`: existencia de las 4 tablas; columnas exactas de
cada tabla; FKs declaradas (beneficiary/recurring_schedule/schedule_execution); los 4 índices;
`UNIQUE(schedule_id, due_at)` se aplica (IntegrityError en duplicado); idempotencia (re-migrar
no duplica tablas/índices); compatibilidad con DB ya migrada; saldos y 2 históricas intactos;
rollback no deja tablas parciales.

## Comportamiento de regresión

Las 51 pruebas de la Fase A y las 6 de la Tarea 7 siguen **verdes** (69/69 en total). Sin
regresiones. Las aserciones estrictas del historial siguen pasando (la API no expone aún `type`).

## Evidencia de aislamiento y preservación de la Etapa 1

- DB histórica: SHA-256 idéntico antes/después; no fue objetivo de migración.
- `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales residuales.
- `Etapa 1/Kiro` git limpio. En la Tarea 8 solo se modificó `app/db.py`.

## Resumen del diff de código

- `app/db.py`: +147 líneas acumuladas respecto al baseline de preparación (incluye T7 y T8):
  listas DDL `_STAGE2_TABLES` (4 tablas) y `_STAGE2_INDEXES` (4 índices), e integración en
  `migrate` (tablas → ALTER → backfill → índices). Aditivo; sin eliminar lógica existente.
- `app/main.py`: sin cambios nuevos en la Tarea 8 (su `+2/−1` fue de la Tarea 7).

## Métricas

- **Duración de la sesión:** N/D. pytest: 0,57 s (T8) y 3,91 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Archivos creados / modificados en esta tarea

| Acción | Archivo |
|---|---|
| Modificado | `Etapa 2/Kiro/backend/app/db.py` (DDL de 4 tablas + 4 índices en `migrate`) |
| Creado | `Etapa 2/Kiro/backend/tests/test_schema_stage2.py` (12 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (subtareas 8.x + Tarea 8) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_08_TAREA_08.md` (este registro) |

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 8 (y su refinamiento T-1). Tareas 9–46 sin iniciar y sin marcar;
  Tareas 1–7 preservadas; total de 46 tareas intacto.
- No se implementaron servicios, endpoints, transacciones financieras, scheduler, ACH,
  recurrentes ni enforcement de límites; no se modificó el frontend; no se cambiaron
  requisitos/diseño ni la Etapa 1 ni registros previos; sin dependencias nuevas.
- No se reclama que la suite de migración completa (Tarea 13) esté pasada.
