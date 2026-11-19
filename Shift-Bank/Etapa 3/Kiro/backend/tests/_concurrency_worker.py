"""Worker de concurrencia multiproceso para `test_concurrency_sqlite.py` (Etapa 3, Tarea 16).

Este módulo NO es una prueba: es un script auxiliar que la prueba lanza como un PROCESO
independiente (vía `subprocess` con el intérprete del `.venv`) para ejercer la concurrencia real
de SQLite entre procesos distintos que comparten el MISMO archivo de base de datos
(design.md §2.8, §6; R8.4, R17.2).

Contrato de invocación (todo por entorno + argumentos, sin estado compartido en memoria):

- `DB_PATH` apunta al archivo SQLite compartido ya migrado/sembrado por la prueba madre.
  Se inyecta parcheando `app.config.DB_PATH` / `app.db.DB_PATH` ANTES de importar la app,
  replicando la técnica del arnés (`conftest.py`).
- `SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`, `SHIFT_ADMIN_TOKEN` se
  heredan del entorno (la prueba madre los propaga desde los valores de prueba de `conftest`),
  de modo que la configuración fail-closed de cifrado/auditoría del proceso hijo sea válida y
  la cadena HMAC use la MISMA clave que la madre.

Uso:
    python -m tests._concurrency_worker <db_path> <role> <iterations> <amount_cents>

    role         : "writer" (ejecuta transferencias internas pequeñas) | "reader" (consulta
                   saldos/historial). El writer también lee al final para dejar el proceso limpio.
    iterations   : número acotado de operaciones a realizar.
    amount_cents : monto por transferencia (muy por debajo del umbral MFA para completar directo).

El writer alterna la dirección (checking↔savings) para no agotar fondos y para que la suma de
saldos se conserve exactamente (cada transferencia interna mueve dinero entre las dos cuentas
propias; el total es invariante). Maneja el `database is locked` transitorio con reintento
acotado respaldado por `PRAGMA busy_timeout`; un escritor correctamente serializado por
`BEGIN IMMEDIATE` termina teniendo éxito.

Salida: imprime en stdout una línea JSON con el resultado (operaciones completadas, errores) y
sale con código 0 si no hubo error irrecuperable, !=0 en caso contrario. La prueba madre valida
los invariantes reales (conservación de dinero, cadena de auditoría, seq sin huecos) tras unir.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# El `.venv` de pruebas ya tiene el backend importable, pero al lanzarse como proceso hijo con
# `-m tests._concurrency_worker` el cwd es `backend/`, por lo que `app` es importable. Aseguramos
# además que `backend/` esté en sys.path por si se invoca por ruta absoluta.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


# Retardo base entre reintentos ante `database is locked` (segundos). Pequeño y acotado: el
# `busy_timeout` de SQLite ya hace la mayor parte de la espera dentro del propio driver.
_RETRY_BASE_SLEEP = 0.02
_MAX_RETRIES = 50
_BUSY_TIMEOUT_MS = 5000


def _open_shared_connection(db_path: str) -> sqlite3.Connection:
    """Abre una conexión al archivo compartido con los MISMOS PRAGMAs que `db.get_connection`.

    Parchea `config.DB_PATH`/`db.DB_PATH` hacia el archivo compartido antes de usar la capa de
    DB, igual que el arnés de pruebas, y añade `PRAGMA busy_timeout` para absorber la contención
    transitoria del único escritor (WAL mantiene las lecturas no bloqueadas).
    """
    import app.config as config
    import app.db as db

    shared = Path(db_path)
    config.DB_PATH = shared
    db.DB_PATH = shared

    conn = db.get_connection(shared)  # WAL + foreign_keys ya fijados aquí
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    return conn


def _run_writer(conn: sqlite3.Connection, iterations: int, amount_cents: int) -> dict:
    """Ejecuta `iterations` transferencias internas pequeñas alternando la dirección.

    Usa la capa de servicio heredada (`service.create_transfer`), que compone el débito y la
    entrada de auditoría DENTRO de `financial_transaction` (BEGIN IMMEDIATE). Reintenta de forma
    acotada ante `database is locked`; un escritor serializado termina con éxito.
    """
    import app.service as service

    amount_raw = f"{amount_cents // 100}.{amount_cents % 100:02d}"
    completed = 0
    retries = 0

    for i in range(iterations):
        from_kind, to_kind = ("checking", "savings") if i % 2 == 0 else ("savings", "checking")
        attempt = 0
        while True:
            try:
                result = service.create_transfer(
                    conn,
                    from_kind=from_kind,
                    to_kind=to_kind,
                    amount_raw=amount_raw,
                    description=f"worker-{os.getpid()}-{i}",
                )
                if result.status == "COMPLETED":
                    completed += 1
                break
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt >= _MAX_RETRIES:
                    raise
                attempt += 1
                retries += 1
                time.sleep(_RETRY_BASE_SLEEP)
            except service.DomainError:
                # Un rechazo de negocio (p. ej. fondos insuficientes) NO es un fallo de
                # concurrencia; se cuenta como no-completada y se continúa. Con montos pequeños
                # y direcciones alternas esto no debería ocurrir, pero se maneja sin abortar.
                break

    return {"role": "writer", "pid": os.getpid(), "completed": completed, "lock_retries": retries}


def _run_reader(conn: sqlite3.Connection, iterations: int) -> dict:
    """Lee saldos e historial `iterations` veces; en WAL no debe bloquearse por el escritor."""
    import app.repository as repository
    import app.service as service

    reads = 0
    for _ in range(iterations):
        checking = repository.get_account(conn, "checking")
        savings = repository.get_account(conn, "savings")
        # Lectura de historial (misma ruta que la API de historial).
        history = service.list_history(conn)
        assert checking is not None and savings is not None
        _ = len(history)
        reads += 1
        time.sleep(_RETRY_BASE_SLEEP)

    return {"role": "reader", "pid": os.getpid(), "reads": reads}


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print(json.dumps({"error": "usage: <db_path> <role> <iterations> <amount_cents>"}))
        return 2

    db_path = argv[1]
    role = argv[2]
    iterations = int(argv[3])
    amount_cents = int(argv[4])

    conn = _open_shared_connection(db_path)
    try:
        if role == "writer":
            out = _run_writer(conn, iterations, amount_cents)
        elif role == "reader":
            out = _run_reader(conn, iterations)
        else:
            print(json.dumps({"error": f"unknown role {role!r}"}))
            return 2
    except Exception as exc:  # noqa: BLE001 - reportar cualquier fallo del proceso hijo
        print(json.dumps({"role": role, "pid": os.getpid(), "error": repr(exc)}))
        return 1
    finally:
        conn.close()

    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
