"""Aislamiento de DB sintética para la prueba de carga (Etapa 3, Tarea 18).

design.md §3.1 · requirements R10.1, R10.2 · AC-10.

Propósito
---------
Proveer los bloques de construcción para que la prueba de carga Locust (Tareas 19–23)
opere SIEMPRE contra una base de datos SQLite **sintética, desechable y aislada**, nunca
contra la base de datos histórica de la Etapa 2 ni `SEED-3.md`.

El punto crítico (R10.1 / AC-10) es el **orden**: se fija `DB_PATH` hacia el archivo
temporal y se establecen las claves de cifrado/auditoría de prueba en el entorno
**ANTES** de importar la aplicación. Esto replica exactamente la técnica del arnés de
pruebas (`backend/tests/conftest.py`), que parchea `app.config.DB_PATH` antes de arrancar
la app vía `TestClient`. Si la app se importara primero, `app.db` capturaría el `DB_PATH`
histórico y el `lifespan` validaría/usaría claves equivocadas: por eso el aislamiento DEBE
preceder a la importación.

Valores sintéticos (deterministas, SOLO carga)
----------------------------------------------
- Semilla aleatoria fija: `random.seed(LOADTEST_RANDOM_SEED)` → reproducibilidad (R10.2).
- Saldos amplios por cuenta: 10.000.000.000,00 COP (`1_000_000_000_000` centavos) en
  Checking y Savings. Suficientes para sostener 60 s de transferencias pequeñas sin agotar
  fondos (la mezcla de carga es ~10% transferencias de monto bajo).
- Límites amplios (no deben dispararse durante la carga):
  * por transferencia: 1.000.000.000,00 COP (`100_000_000_000` centavos).
  * diario acumulado:   1.000.000.000.000,00 COP (`100_000_000_000_000` centavos).
  Ambos muy por encima del consumo acumulado posible en 60 s, de modo que las
  transferencias de carga (montos pequeños, por debajo del umbral MFA de 1.000.000 COP)
  pasen TODOS los controles heredados (fondos + límites + sin MFA) y se completen como
  operaciones bancarias válidas, no como rechazos (R10.3; Tarea 19).

Claves de prueba (SOLO carga/pruebas)
-------------------------------------
Las claves son constantes claramente etiquetadas de SOLO carga, consistentes con los
valores del arnés (`conftest.py`). NO se hornean en el código de la app ni en
`requirements*.txt`: viven solo en este tooling de carga. La app sigue exigiendo claves
por entorno (fail-closed intacto).
"""

from __future__ import annotations

import os
import random
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

# --- Localización del backend para poder importar el paquete `app` -----------
#
# Este paquete `loadtest/` vive junto al backend (en la raíz del proyecto Kiro). Para
# importar `app.*` al ejecutar la carga, se añade el directorio `backend/` a `sys.path`
# ANTES de cualquier importación de la app, igual que hace `conftest.py` con su backend.
_LOADTEST_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _LOADTEST_DIR.parent / "backend"
if _BACKEND_ROOT.is_dir() and str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


# --- Material de clave SOLO-CARGA (consistente con conftest.py) ---------------
#
# `LOADTEST_ENC_KEY_B64` = base64 de 32 bytes b"shift-bank-stage3-test-key-32byt" (AES-256),
# idéntico al valor del arnés de pruebas para mantener coherencia. Claramente etiquetado
# como material de SOLO carga/pruebas; nunca es un secreto de producción.
LOADTEST_ENC_KID = "test"
LOADTEST_ENC_KEY_B64 = "c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ="
LOADTEST_ENC_KEYS = f"{LOADTEST_ENC_KID}:{LOADTEST_ENC_KEY_B64}"
LOADTEST_AUDIT_HMAC_KEY = "shift-bank-stage3-loadtest-audit-hmac-key"
LOADTEST_ADMIN_TOKEN = "shift-bank-stage3-loadtest-admin-token"

# --- Semilla aleatoria fija (reproducibilidad, R10.2) ------------------------
LOADTEST_RANDOM_SEED = 20240917

# --- Valores sintéticos de carga (deterministas, documentados) ---------------
#
# Saldos amplios por cuenta (centavos). 10.000.000.000,00 COP cada uno.
LOADTEST_CHECKING_BALANCE_CENTS = 1_000_000_000_000
LOADTEST_SAVINGS_BALANCE_CENTS = 1_000_000_000_000

# Límites amplios (centavos) que NO deben dispararse durante la carga.
# Por transferencia: 1.000.000.000,00 COP. Diario: 1.000.000.000.000,00 COP.
LOADTEST_PER_TRANSFER_LIMIT_CENTS = 100_000_000_000
LOADTEST_DAILY_LIMIT_CENTS = 100_000_000_000_000


def set_test_keys_env() -> None:
    """Fija el material de clave de SOLO-CARGA en el entorno del proceso.

    DEBE llamarse ANTES de importar la app (R10.1): el `lifespan` valida fail-closed las
    claves externas en el arranque. Usa asignación directa (no `setdefault`) para que el
    aislamiento de carga sea explícito y reproducible, salvo que el llamador ya las haya
    fijado idénticas. El material nunca se registra en logs.
    """
    os.environ["SHIFT_ENC_KEYS"] = LOADTEST_ENC_KEYS
    os.environ["SHIFT_ENC_ACTIVE_KID"] = LOADTEST_ENC_KID
    os.environ["SHIFT_AUDIT_HMAC_KEY"] = LOADTEST_AUDIT_HMAC_KEY
    os.environ["SHIFT_ADMIN_TOKEN"] = LOADTEST_ADMIN_TOKEN


def make_synthetic_db_path() -> Path:
    """Crea una ruta única para una DB SQLite sintética **desechable** en un temp dir.

    El archivo aún no existe; lo crea la inicialización de la app/conexión. Nunca apunta a
    la DB histórica (`backend/shift_bank.db`).
    """
    tmp_dir = Path(tempfile.gettempdir())
    return tmp_dir / f"shift_bank_loadtest_{uuid.uuid4().hex}.db"


def configure_isolation(db_path: Path | None = None) -> Path:
    """Configura el aislamiento ANTES de importar la app y devuelve la `DB_PATH` resuelta.

    Pasos (orden crítico para R10.1):

    1. Elegir/crear una ruta de DB sintética desechable.
    2. Fijar `os.environ["DB_PATH"]` y las claves de prueba en el entorno.
    3. Importar `app.config` y `app.db` y **parchear** su `DB_PATH` hacia el archivo
       sintético (igual que `conftest.py`). Se hace tras fijar el entorno; la app aún no se
       ha arrancado (no se importa `app.main`), así que ninguna conexión se ha abierto
       todavía contra la DB histórica.

    Devuelve la ruta sintética resuelta.
    """
    resolved = Path(db_path) if db_path is not None else make_synthetic_db_path()

    # (2) Entorno: DB_PATH + claves ANTES de importar/parchear la app (R10.1).
    #     `DB_PATH` se expone también como variable de entorno para procesos hijos
    #     (p. ej. el uvicorn que arranca la Tarea 20), que lo leerán al importar la app.
    os.environ["DB_PATH"] = str(resolved)
    set_test_keys_env()

    # (3) Parcheo de la ruta en el paquete `app` para el proceso actual. Se importan SOLO
    #     `config` y `db` (no `main`): la app no se arranca aquí, de modo que el aislamiento
    #     queda establecido antes de cualquier importación/arranque de la aplicación.
    import app.config as config
    import app.db as db

    config.DB_PATH = resolved
    db.DB_PATH = resolved

    return resolved


def seed_synthetic_db(db_path: Path) -> None:
    """Inicializa y siembra la DB sintética de forma determinista (R10.2).

    Reutiliza la secuencia de arranque de la app (idempotente):
    `init_schema → migrate → migrate_encryption → seed → seed_limits`, y luego **ajusta**
    saldos y límites a los valores sintéticos amplios de carga, de forma determinista. La
    semilla aleatoria se fija antes de sembrar para que cualquier aleatoriedad (p. ej.
    generación de datos futuros) sea reproducible entre corridas.

    Requiere que `configure_isolation` se haya ejecutado antes (claves en el entorno y
    `DB_PATH` parcheado), para no tocar la DB histórica.
    """
    # Semilla fija: reproducibilidad del arnés de carga (R10.2).
    random.seed(LOADTEST_RANDOM_SEED)

    # Importar la capa de datos (ya parcheada por configure_isolation).
    import app.db as db
    import app.seed as seed

    conn = db.get_connection(db_path)
    try:
        # Secuencia de arranque reutilizada (misma que `main._initialize_database`).
        db.init_schema(conn)
        db.migrate(conn)
        db.migrate_encryption(conn)
        seed.seed(conn)
        seed.seed_limits(conn)

        # Ajuste determinista a valores sintéticos amplios de carga.
        _apply_loadtest_values(conn)
        conn.commit()
    finally:
        conn.close()


def _apply_loadtest_values(conn: sqlite3.Connection) -> None:
    """Fija saldos amplios en ambas cuentas y límites amplios del cliente mock.

    Determinista: no depende de aleatoriedad. Idempotente (puede re-ejecutarse). Montos en
    centavos enteros, respetando el modelo de dinero heredado.
    """
    conn.execute(
        "UPDATE account SET balance_cents = ? WHERE kind = 'checking'",
        (LOADTEST_CHECKING_BALANCE_CENTS,),
    )
    conn.execute(
        "UPDATE account SET balance_cents = ? WHERE kind = 'savings'",
        (LOADTEST_SAVINGS_BALANCE_CENTS,),
    )

    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    if row is not None:
        customer_id = row["id"]
        # UPSERT de límites amplios (la fila se sembró en seed_limits; se cubre el caso general).
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            """INSERT INTO transfer_limit
                   (customer_id, per_transfer_cents, daily_cents, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(customer_id) DO UPDATE SET
                   per_transfer_cents = excluded.per_transfer_cents,
                   daily_cents = excluded.daily_cents,
                   updated_at = excluded.updated_at""",
            (
                customer_id,
                LOADTEST_PER_TRANSFER_LIMIT_CENTS,
                LOADTEST_DAILY_LIMIT_CENTS,
                now_iso,
            ),
        )


def teardown_synthetic_db(db_path: Path) -> None:
    """Elimina la DB sintética desechable y sus auxiliares de SQLite (-wal/-shm/-journal).

    No deja estado persistente. Seguro de llamar aunque algún archivo no exista.
    """
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()


def setup_loadtest_db(db_path: Path | None = None) -> Path:
    """Conveniencia: aísla + siembra en un solo paso y devuelve la `DB_PATH` resuelta.

    Equivale a `configure_isolation()` seguido de `seed_synthetic_db()`. Útil para el
    runner de carga (Tarea 20) y para la verificación/sanity local.
    """
    resolved = configure_isolation(db_path)
    seed_synthetic_db(resolved)
    return resolved


def _read_balances(db_path: Path) -> dict[str, int]:
    """Lee los saldos sembrados (centavos) para la verificación de sanity."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
        return {r["kind"]: r["balance_cents"] for r in rows}
    finally:
        conn.close()


def _read_limits(db_path: Path) -> dict[str, int]:
    """Lee los límites sembrados (centavos) para la verificación de sanity."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT per_transfer_cents, daily_cents FROM transfer_limit LIMIT 1"
        ).fetchone()
        if row is None:
            return {}
        return {
            "per_transfer_cents": row["per_transfer_cents"],
            "daily_cents": row["daily_cents"],
        }
    finally:
        conn.close()


def _main() -> int:
    """Sanity check ejecutable: aísla, siembra, verifica e importa la app limpiamente.

    Imprime la `DB_PATH` resuelta, los saldos/límites sembrados y confirma que la app
    importa contra la DB sintética sin tocar la histórica. Limpia la DB desechable al final.
    """
    # Snapshot de la DB histórica para demostrar que NO se toca.
    historic_db = _BACKEND_ROOT / "shift_bank.db"
    historic_existed_before = historic_db.exists()
    historic_mtime_before = historic_db.stat().st_mtime if historic_existed_before else None

    db_path = setup_loadtest_db()
    try:
        balances = _read_balances(db_path)
        limits = _read_limits(db_path)

        print("=== loadtest.isolation sanity check ===")
        print(f"Resolved DB_PATH (synthetic, disposable): {db_path}")
        print(f"DB file exists: {db_path.exists()}")
        print(f"Points at historic DB? {db_path.resolve() == historic_db.resolve()}")
        print("--- seeded balances (cents) ---")
        for kind, cents in sorted(balances.items()):
            print(f"  {kind:10s}: {cents:>20,d}  (COP {cents / 100:,.2f})")
        print("--- seeded limits (cents) ---")
        for key, cents in sorted(limits.items()):
            print(f"  {key:20s}: {cents:>20,d}  (COP {cents / 100:,.2f})")

        # Verificaciones de aislamiento (R10.1) y valores (R10.2).
        assert db_path.resolve() != historic_db.resolve(), "DB sintética == DB histórica (FAIL)"
        assert balances.get("checking") == LOADTEST_CHECKING_BALANCE_CENTS
        assert balances.get("savings") == LOADTEST_SAVINGS_BALANCE_CENTS
        assert limits.get("per_transfer_cents") == LOADTEST_PER_TRANSFER_LIMIT_CENTS
        assert limits.get("daily_cents") == LOADTEST_DAILY_LIMIT_CENTS

        # La app debe importar limpiamente contra la DB sintética (claves ya en el entorno).
        import app.main as main  # noqa: F401

        print("--- app import ---")
        print("  import app.main: OK (claves de carga válidas; DB sintética parcheada)")

        # La DB histórica no debe haber sido creada ni modificada por este arnés.
        historic_exists_after = historic_db.exists()
        historic_mtime_after = (
            historic_db.stat().st_mtime if historic_exists_after else None
        )
        historic_untouched = (
            historic_existed_before == historic_exists_after
            and historic_mtime_before == historic_mtime_after
        )
        print("--- historic DB ---")
        print(f"  historic DB untouched: {historic_untouched}")
        assert historic_untouched, "La DB histórica cambió (FAIL)"

        print("=== RESULT: PASS ===")
        return 0
    finally:
        teardown_synthetic_db(db_path)
        print(f"Teardown: removed synthetic DB {db_path} (+ -wal/-shm/-journal)")


if __name__ == "__main__":
    raise SystemExit(_main())
