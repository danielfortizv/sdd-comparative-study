"""Suite de migración de la Etapa 2 (Tarea 13) + siembra de límites (T11) + lifespan (T12).

Verifica la migración de extremo a extremo partiendo de un estado heredado de la Etapa 1
(incluida una **copia real** de la DB histórica, nunca la original), la siembra idempotente de
límites por defecto y la inicialización del arranque vía `lifespan`.

Amplía las verificaciones mínimas de las Tareas 7/8 con la perspectiva de migración completa.

_Requisitos: 15.8, 16.3, 13.1_ · _Diseño: §Migración (DD-5, F11, F12); Decisión: D01_
"""

import shutil
from pathlib import Path

import app.config as config
import app.db as db
from app.seed import seed, seed_limits


_HISTORICAL_DB = (
    Path(__file__).resolve().parents[4]
    / "Etapa 1" / "Kiro" / "backend" / "shift_bank.db"
)


def _legacy_db(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        seed(conn)
    finally:
        conn.close()


def _full_startup(path):
    """Reproduce el orden del arranque: init_schema → migrate → seed → seed_limits."""
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        db.migrate(conn)
        seed(conn)
        seed_limits(conn)
    finally:
        conn.close()


# --- Migración sobre una copia real de la DB histórica de la Etapa 1 ----------

def test_migracion_sobre_copia_real_de_db_historica(tmp_path):
    """Copiar la DB histórica de E1 y migrar la copia; la original no se toca."""
    if not _HISTORICAL_DB.exists():
        import pytest
        pytest.skip("DB histórica de E1 no disponible en este entorno")

    hist_hash_before = _file_sha256(_HISTORICAL_DB)
    copy_path = tmp_path / "copia_historica.db"
    shutil.copy2(_HISTORICAL_DB, copy_path)

    # Migrar la COPIA.
    conn = db.get_connection(copy_path)
    try:
        before_acc = {r["kind"]: r["balance_cents"] for r in
                      conn.execute("SELECT kind, balance_cents FROM account").fetchall()}
        before_transfers = conn.execute("SELECT COUNT(*) AS n FROM transfer").fetchone()["n"]
        db.migrate(conn)
        after_acc = {r["kind"]: r["balance_cents"] for r in
                     conn.execute("SELECT kind, balance_cents FROM account").fetchall()}
        after_transfers = conn.execute("SELECT COUNT(*) AS n FROM transfer").fetchone()["n"]
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()

    # Saldos y nº de transferencias de la copia intactos; tablas nuevas presentes.
    assert after_acc == before_acc
    assert after_transfers == before_transfers
    assert {"beneficiary", "recurring_schedule", "transfer_limit",
            "schedule_execution"}.issubset(tables)
    # La DB histórica ORIGINAL no cambió.
    assert _file_sha256(_HISTORICAL_DB) == hist_hash_before


def _file_sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Migración de extremo a extremo sobre estado heredado reconstruido --------

def test_migracion_end_to_end_desde_estado_heredado(tmp_path):
    path = tmp_path / "e2e.db"
    _legacy_db(path)
    # type no existe antes de migrar.
    conn = db.get_connection(path)
    try:
        cols_before = {r["name"] for r in conn.execute("PRAGMA table_info(transfer)").fetchall()}
        assert "type" not in cols_before
        db.migrate(conn)
        cols_after = {r["name"] for r in conn.execute("PRAGMA table_info(transfer)").fetchall()}
        types = {r["type"] for r in conn.execute("SELECT type FROM transfer").fetchall()}
    finally:
        conn.close()
    assert {"type", "beneficiary_id", "settled_at", "refunded", "schedule_id"}.issubset(cols_after)
    assert types == {"internal"}  # históricas clasificadas como internas


def test_migracion_idempotente_en_multiples_arranques(tmp_path):
    """Varias migraciones consecutivas (simulando reinicios) no corrompen ni duplican."""
    path = tmp_path / "restart.db"
    _legacy_db(path)
    for _ in range(3):
        conn = db.get_connection(path)
        try:
            db.migrate(conn)
        finally:
            conn.close()
    conn = db.get_connection(path)
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        n_acc = conn.execute("SELECT COUNT(*) AS n FROM account").fetchone()["n"]
    finally:
        conn.close()
    assert n_acc == 2
    assert {"beneficiary", "recurring_schedule", "transfer_limit",
            "schedule_execution"}.issubset(tables)


# --- Siembra de límites por defecto (Tarea 11) --------------------------------

def test_seed_limits_inserta_valores_por_defecto(tmp_path):
    path = tmp_path / "lim.db"
    _full_startup(path)
    conn = db.get_connection(path)
    try:
        row = conn.execute(
            "SELECT per_transfer_cents, daily_cents FROM transfer_limit").fetchone()
    finally:
        conn.close()
    assert row["per_transfer_cents"] == config.DEFAULT_PER_TRANSFER_LIMIT_CENTS == 500_000_000
    assert row["daily_cents"] == config.DEFAULT_DAILY_LIMIT_CENTS == 1_000_000_000


def test_seed_limits_idempotente_no_sobrescribe(tmp_path):
    """Re-sembrar no sobrescribe un límite ya modificado por el usuario."""
    path = tmp_path / "lim2.db"
    _full_startup(path)
    conn = db.get_connection(path)
    try:
        cust = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
        # Simular que el usuario cambió su límite.
        conn.execute(
            "UPDATE transfer_limit SET per_transfer_cents = 123456 WHERE customer_id = ?",
            (cust,))
        conn.commit()
        # Re-sembrar no debe sobrescribir.
        seed_limits(conn)
        val = conn.execute(
            "SELECT per_transfer_cents FROM transfer_limit WHERE customer_id = ?",
            (cust,)).fetchone()["per_transfer_cents"]
    finally:
        conn.close()
    assert val == 123456  # preservado


def test_seed_limits_una_sola_fila(tmp_path):
    """Arranques repetidos no crean filas de límite duplicadas."""
    path = tmp_path / "lim3.db"
    _full_startup(path)
    _full_startup(path)  # segundo "arranque"
    conn = db.get_connection(path)
    try:
        n = conn.execute("SELECT COUNT(*) AS n FROM transfer_limit").fetchone()["n"]
    finally:
        conn.close()
    assert n == 1


# --- Inicialización del arranque vía lifespan (Tarea 12) ----------------------

def test_lifespan_inicializa_sin_duplicar(app_client, isolated_db_path):
    """El arranque por lifespan deja cuentas, históricas y una fila de límites, sin duplicar."""
    # app_client ya disparó el lifespan (startup) contra la DB aislada.
    accounts = app_client.get("/api/accounts").json()["accounts"]
    assert len(accounts) == 2
    hist = app_client.get("/api/transfers").json()["transfers"]
    assert len(hist) == 2  # dos históricas, sin duplicar
    conn = db.get_connection(isolated_db_path)
    try:
        n_lim = conn.execute("SELECT COUNT(*) AS n FROM transfer_limit").fetchone()["n"]
        n_cust = conn.execute("SELECT COUNT(*) AS n FROM customer").fetchone()["n"]
    finally:
        conn.close()
    assert n_lim == 1
    assert n_cust == 1
