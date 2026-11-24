# T16 — Concurrencia real SQLite: lector/escritor (WAL) y multiproceso

- **Fecha/hora:** 2026-11-16T19:49:19-05:00
- **Tarea:** 16 (auto)(verificación) — Concurrencia real SQLite lector/escritor y multiproceso
- **Tipo:** solo pruebas (no se modificó el comportamiento de la aplicación)
- **Requisitos:** R8.3, R8.4, R17.1, R17.2 · **Diseño:** §2.8, §6 · **AC:** AC-09
- **Artefacto nuevo:** `backend/tests/test_concurrency_sqlite.py` (+ auxiliar
  `backend/tests/_concurrency_worker.py`)

## Entorno

| Componente | Versión |
|------------|---------|
| SO | Windows (win32) |
| Python (`.venv`) | 3.13.2 |
| SQLite (`sqlite3.sqlite_version`) | 3.45.3 |
| pytest | 8.3.4 |

Comandos exactos (desde `backend/`, con el intérprete del `.venv`):

```
.\.venv\Scripts\python.exe -m pytest tests/test_concurrency_sqlite.py -v
.\.venv\Scripts\python.exe -m pytest -q
```

## Qué se verifica (invariantes reales, no tiempos de pared)

El archivo añade 5 pruebas. Todas usan un **archivo SQLite desechable** bajo `tmp_path` (no
`:memory:`), migrado y sembrado replicando la secuencia de arranque
(`init_schema → migrate → migrate_encryption → seed → seed_limits`), sin lanzar el scheduler.
Nunca se tocan datos históricos ni `SEED-3.md`.

Todas las conexiones se abren con `app.db.get_connection` (que fija `PRAGMA journal_mode=WAL` y
`PRAGMA foreign_keys=ON`, design.md §2.8) y añaden `PRAGMA busy_timeout=5000` por conexión para
absorber la contención transitoria del único escritor con espera acotada del propio driver.

### 1) Lector/escritor en WAL (dos conexiones, misma máquina)

- **`test_reader_not_blocked_by_writer_holding_write_lock`**: el escritor abre
  `BEGIN IMMEDIATE` (toma el lock de escritor), aplica un débito y **no confirma**; en ese
  instante el lector —en OTRA conexión— lee saldos. Se asevera que el lector **no** recibe
  `database is locked` y que ve el snapshot consistente **pre-commit** (aislamiento WAL). El
  orden se coordina con `threading.Event` (no `sleep`), de modo que el resultado es
  determinista. Tras el commit, la suma de saldos sigue conservada.
  → Sin WAL (journal de rollback) el lector se bloquearía con `database is locked`; esta prueba
  valida directamente "lecturas no bloqueadas innecesariamente" (R17.1, §2.8).
- **`test_serialized_writer_sequence_never_locked_out`**: un lector en bucle mientras el
  escritor ejecuta 12 transferencias vía `service.create_transfer` (dentro de
  `financial_transaction`/`BEGIN IMMEDIATE`). Se asevera: todas las transferencias completan
  (ningún `database is locked` aborta al escritor serializado), el lector nunca se bloquea,
  dinero conservado, 12 filas COMPLETED (exactamente-una-vez), cadena íntegra y `seq` contiguo
  1..12 con ancla coherente.

### 2) Correctitud bajo concurrencia (hilos con conexiones separadas)

- **`test_concurrent_threads_money_conserved_and_chain_intact`**: 4 hilos × 8 transferencias
  = 32 transferencias concurrentes, cada hilo con su propia conexión. Tras unir:
  **conservación del dinero** (suma de saldos invariante), **exactamente-una-vez** (32 filas
  COMPLETED, ni duplicado ni pérdida), **`verify_chain` íntegra**, **`seq` contiguo** 1..32 sin
  huecos y **ancla coherente** (`audit_anchor.last_seq == N`).

### 3) Multiproceso independiente (procesos reales)

Los procesos hijos se lanzan con `subprocess` usando el intérprete del `.venv`
(`python -m tests._concurrency_worker <db_path> <role> <iters> <amount_cents>`), con `cwd` en
`backend/`. Al entorno del hijo se le propagan `DB_PATH` (archivo compartido) y las claves de
prueba `SHIFT_ENC_KEYS`/`SHIFT_ENC_ACTIVE_KID`/`SHIFT_AUDIT_HMAC_KEY`/`SHIFT_ADMIN_TOKEN`
(reutilizadas de `conftest`), de modo que la config fail-closed de cifrado/auditoría del hijo es
válida y la cadena HMAC usa la MISMA clave que la madre. Cada hijo abre su propia conexión vía
`db.get_connection` con los mismos PRAGMAs.

- **`test_independent_processes_no_corruption_money_conserved_chain_ok`**: un proceso escritor
  (10 transferencias) + un proceso lector (15 lecturas de saldos/historial). Tras unir:
  `PRAGMA integrity_check == ok` (sin corrupción), dinero conservado, 10 COMPLETED
  (exactamente-una-vez), cadena íntegra y `seq` contiguo 1..10, ancla coherente.
- **`test_two_writer_processes_chain_gap_free`**: dos procesos ESCRITORES concurrentes
  (8 + 8). Comprueba específicamente R8.4/§6: la serialización por `BEGIN IMMEDIATE` entre
  procesos produce una cadena HMAC verificable y `seq` **sin huecos** (contiguo 1..16), con
  `integrity_check == ok` y dinero conservado.

El worker maneja el `sqlite3.OperationalError: database is locked` transitorio con reintento
**acotado** (máx. 50) respaldado por `busy_timeout`; un escritor correctamente serializado
termina con éxito. Un error no-lock se propaga y hace fallar la prueba (no se enmascara un fallo
real como éxito).

## Resultados reales

### `pytest tests/test_concurrency_sqlite.py -v`

```
tests/test_concurrency_sqlite.py::test_reader_not_blocked_by_writer_holding_write_lock PASSED [ 20%]
tests/test_concurrency_sqlite.py::test_serialized_writer_sequence_never_locked_out        PASSED [ 40%]
tests/test_concurrency_sqlite.py::test_concurrent_threads_money_conserved_and_chain_intact PASSED [ 60%]
tests/test_concurrency_sqlite.py::test_independent_processes_no_corruption_money_conserved_chain_ok PASSED [ 80%]
tests/test_concurrency_sqlite.py::test_two_writer_processes_chain_gap_free                 PASSED [100%]
============================== 5 passed in 1.10s ==============================
```

### Suite completa `pytest -q`

```
341 passed, 1 warning in 18.93s
```

- **Baseline previo:** 336 passed (verificado antes de añadir el archivo).
- **Tras T16:** 336 + 5 = **341 passed**. Exit code 0.
- La única advertencia es la `DeprecationWarning` heredada de Starlette (`anyio.abc.BlockingPortal`),
  preexistente y ajena a esta tarea.

## Flakiness / determinismo

- No se asevera ningún tiempo de pared; solo invariantes de resultado (saldos finales, nº de
  COMPLETED, `verify_chain`, contigüidad de `seq`, ancla, `integrity_check`).
- El handshake lector/escritor usa `threading.Event` con `wait(timeout=...)` acotado, no
  `sleep`, eliminando carreras de tiempo.
- La contención del único escritor se absorbe con `PRAGMA busy_timeout` + reintento acotado ante
  `database is locked`; no hay bucles infinitos ni esperas ilimitadas.
- Se ejecutó el archivo **5 veces consecutivas**: 5/5 verdes (1.10–1.41 s por corrida), sin
  intermitencias.

## Preservación

- No se modificó código de la aplicación (tarea solo-pruebas). No se encontró ningún bug real de
  concurrencia: la serialización por `BEGIN IMMEDIATE` + WAL se comporta según diseño.
- No se alteraron datos históricos de la Etapa 2 ni `SEED-3.md`; toda la DB es desechable por
  prueba (`tmp_path`).
