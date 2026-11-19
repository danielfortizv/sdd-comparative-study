# T9 — Esquema de auditoría y protección append-only (`db.migrate`)

- **Fecha/hora:** 2026-11-16T16:33:35 (local)
- **Tarea:** M2 · Tarea 9 (auto) — Esquema de auditoría y protección append-only
- **Requisitos:** R6.1, R6.2 · **Diseño:** §2.1, §2.4, §2.9, §5.1 · **AC:** AC-06
- **Entorno:** Windows, Python 3.13.2 (venv `backend/.venv`), pytest 8.3.4
- **Alcance preservado:** no se modificó `SEED-3.md` ni datos históricos de la Etapa 2; todas
  las pruebas usan DB SQLite temporal aislada (`tmp_path`).

## DDL añadido (en `app/db.py`, dentro de la transacción de `migrate`)

Todo aditivo e idempotente, ejecutado por sentencia con `conn.execute()` (sin `executescript`,
que haría COMMIT implícito y rompería la atomicidad/rollback de la migración).

1. **Tabla `audit_log`** (design §2.1) — `CREATE TABLE IF NOT EXISTS`:
   `seq INTEGER PRIMARY KEY AUTOINCREMENT`, `event_type TEXT NOT NULL`, `outcome TEXT NOT NULL`,
   `entity_ref TEXT`, `occurred_at TEXT NOT NULL`, `payload TEXT NOT NULL`,
   `prev_hmac TEXT NOT NULL`, `entry_hmac TEXT NOT NULL`.

2. **Tabla `audit_anchor`** (design §2.9/§5.1) — fila única `CREATE TABLE IF NOT EXISTS`:
   `id INTEGER PRIMARY KEY CHECK (id = 1)`, `last_seq INTEGER NOT NULL`, `last_hmac TEXT NOT NULL`.

3. **Triggers append-only** (design §2.4) — `CREATE TRIGGER IF NOT EXISTS`:
   - `audit_log_no_update`: `BEFORE UPDATE ON audit_log ... SELECT RAISE(ABORT, 'audit_log is append-only')`.
   - `audit_log_no_delete`: `BEFORE DELETE ON audit_log ... SELECT RAISE(ABORT, 'audit_log is append-only')`.

Las sentencias viven en las listas `_STAGE3_AUDIT_TABLES` y `_STAGE3_AUDIT_TRIGGERS`, y se
ejecutan dentro del `BEGIN ... COMMIT` existente de `migrate`, tras el DDL de la Etapa 2.

## Dónde se fija WAL

`PRAGMA journal_mode = WAL` se fija en **`get_connection`** (al abrir la conexión), NO dentro de
`migrate`. Razones:

- WAL es una propiedad **persistente** del archivo de base de datos: una vez aplicado, queda en
  modo WAL para conexiones futuras; re-fijarlo en cada apertura es idempotente y barato.
- Debe ejecutarse **fuera** de una transacción explícita: SQLite ignora el cambio de
  `journal_mode` dentro de un `BEGIN...COMMIT`. `get_connection` lo aplica antes de cualquier
  `BEGIN`, por lo que la transacción de `migrate` no se ve afectada.
- Para DB en memoria (`:memory:`) el modo permanece `memory`, lo cual es correcto y no rompe el
  aislamiento por prueba. Las pruebas de WAL usan DB basada en archivo (`tmp_path`).

## Comportamiento de los triggers (verificado)

- `UPDATE audit_log ...` → aborta con `sqlite3.IntegrityError` cuyo mensaje contiene
  `append-only`; la fila no cambia.
- `DELETE FROM audit_log ...` → aborta con `sqlite3.IntegrityError`; la fila permanece.
- `INSERT` sigue permitido (append-only solo bloquea UPDATE/DELETE).
- `audit_anchor` CHECK `id=1` rechaza una segunda fila con id distinto.

## Resultados reales de pytest

Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_audit_schema.py -v`

```
11 passed in 0.54s
```
(pruebas: existencia de tablas/columnas/triggers, UPDATE/DELETE abortan, INSERT permitido,
CHECK de `audit_anchor`, `journal_mode=wal` en archivo real + persistencia en nueva conexión,
idempotencia de `migrate`.)

Suite completa: `.\.venv\Scripts\python.exe -m pytest -q`

```
271 passed, 1 warning in 14.80s
```

- Baseline heredado previo a la tarea: **260 passed**.
- Tras la tarea: **271 passed** = 260 heredados + 11 nuevos. Cero regresiones.
- La única advertencia es la `DeprecationWarning` preexistente de Starlette/anyio (no relacionada
  con esta tarea).

## Veredicto

**PASS.** DDL idempotente de `audit_log`/`audit_anchor` + triggers append-only integrados en la
migración transaccional; WAL activo y persistente sobre archivo real sin romper el aislamiento ni
la suite heredada. R6.1/R6.2 y AC-06 cubiertos.
