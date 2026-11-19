"""Verificación del esquema de la Etapa 2 — tablas, FKs, índices, unicidad (Tarea 8).

Verificación mínima del DDL de las 4 tablas nuevas y sus constraints/índices, integrado en el
`migrate` transaccional. NO es la suite de migración completa (Tarea 13).

Cada prueba construye una DB temporal con el esquema heredado de la Etapa 1 y aplica `migrate`.
Nunca usa la DB histórica como objetivo.

_Requisitos: 16.3_ · _Diseño: §Modelo de datos; §FKs/unicidad/índices (F13, DD-7)_
"""

import sqlite3
import uuid

import app.db as db
from app.seed import seed


def _legacy_db(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        seed(conn)
    finally:
        conn.close()


def _migrated_db(path):
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)
    finally:
        conn.close()


def _tables(path):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()


def _columns(path, table):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _indexes(path):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    finally:
        conn.close()


# --- Existencia de tablas y columnas ------------------------------------------

def test_cuatro_tablas_nuevas_existen(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    tables = _tables(path)
    for t in ("beneficiary", "recurring_schedule", "transfer_limit", "schedule_execution"):
        assert t in tables
    # Las heredadas siguen existiendo.
    for t in ("customer", "account", "transfer"):
        assert t in tables


def test_columnas_beneficiary(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "beneficiary")
    assert cols == {"id", "customer_id", "name", "bank", "routing_number",
                    "account_number", "created_at", "deleted_at"}


def test_columnas_recurring_schedule(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "recurring_schedule")
    assert cols == {"id", "customer_id", "type", "from_kind", "to_kind", "beneficiary_id",
                    "beneficiary_snapshot", "amount_cents", "description", "frequency",
                    "status", "requires_mfa", "authorized", "next_run_at", "created_at"}


def test_columnas_transfer_limit(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "transfer_limit")
    assert cols == {"customer_id", "per_transfer_cents", "daily_cents", "updated_at"}


def test_columnas_schedule_execution(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "schedule_execution")
    assert cols == {"id", "schedule_id", "due_at", "outcome", "transfer_id", "created_at"}


# --- FKs e índices ------------------------------------------------------------

def test_foreign_keys_declaradas(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        # beneficiary → customer
        fk_ben = conn.execute("PRAGMA foreign_key_list(beneficiary)").fetchall()
        assert any(r["table"] == "customer" for r in fk_ben)
        # recurring_schedule → customer y beneficiary
        fk_sch = {r["table"] for r in conn.execute(
            "PRAGMA foreign_key_list(recurring_schedule)").fetchall()}
        assert {"customer", "beneficiary"}.issubset(fk_sch)
        # schedule_execution → recurring_schedule y transfer
        fk_exec = {r["table"] for r in conn.execute(
            "PRAGMA foreign_key_list(schedule_execution)").fetchall()}
        assert {"recurring_schedule", "transfer"}.issubset(fk_exec)
    finally:
        conn.close()


def test_indices_creados(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    idx = _indexes(path)
    for name in ("idx_transfer_created_at", "idx_transfer_type_status",
                 "idx_schedule_due", "idx_beneficiary_customer"):
        assert name in idx


def test_unique_schedule_execution_se_aplica(tmp_path):
    """La restricción UNIQUE(schedule_id, due_at) impide ocurrencias duplicadas."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        # Crear un schedule para satisfacer la FK.
        sched_id = str(uuid.uuid4())
        cust = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
        conn.execute(
            """INSERT INTO recurring_schedule
               (id, customer_id, type, from_kind, amount_cents, frequency, status,
                next_run_at, created_at)
               VALUES (?, ?, 'internal', 'checking', 1000, 'daily', 'active',
                       '2026-11-16T00:00:00Z', '2026-11-16T00:00:00Z')""",
            (sched_id, cust),
        )
        due = "2026-11-17T00:00:00Z"
        conn.execute(
            "INSERT INTO schedule_execution (id, schedule_id, due_at, outcome, created_at) "
            "VALUES (?, ?, ?, 'executed', ?)",
            (str(uuid.uuid4()), sched_id, due, "2026-11-17T00:00:00Z"),
        )
        conn.commit()
        # Segundo INSERT de la misma (schedule_id, due_at) debe fallar por UNIQUE.
        import pytest
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO schedule_execution (id, schedule_id, due_at, outcome, created_at) "
                "VALUES (?, ?, ?, 'executed', ?)",
                (str(uuid.uuid4()), sched_id, due, "2026-11-17T01:00:00Z"),
            )
            conn.commit()
    finally:
        conn.close()


# --- Idempotencia, compatibilidad y preservación ------------------------------

def test_migracion_idempotente_con_tablas(tmp_path):
    """Re-ejecutar migrate() no duplica tablas ni índices."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    tablas1, idx1 = _tables(path), _indexes(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)  # segunda vez
    finally:
        conn.close()
    assert _tables(path) == tablas1
    assert _indexes(path) == idx1


def test_compatible_con_db_ya_migrada_en_tarea7(tmp_path):
    """Una DB que ya pasó una migración previa admite migrate() de nuevo sin error."""
    path = tmp_path / "m.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)  # primera (equivale a T7+T8 combinadas)
        db.migrate(conn)  # de nuevo (simula arranque posterior)
    finally:
        conn.close()
    assert {"beneficiary", "recurring_schedule", "transfer_limit",
            "schedule_execution"}.issubset(_tables(path))


def test_saldos_y_historicas_intactos_tras_tarea8(tmp_path):
    path = tmp_path / "m.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        before_acc = {r["kind"]: r["balance_cents"] for r in
                      conn.execute("SELECT kind, balance_cents FROM account").fetchall()}
        before_n = conn.execute("SELECT COUNT(*) AS n FROM transfer").fetchone()["n"]
    finally:
        conn.close()

    conn = db.get_connection(path)
    try:
        db.migrate(conn)
    finally:
        conn.close()

    conn = db.get_connection(path)
    try:
        after_acc = {r["kind"]: r["balance_cents"] for r in
                     conn.execute("SELECT kind, balance_cents FROM account").fetchall()}
        after_n = conn.execute("SELECT COUNT(*) AS n FROM transfer").fetchone()["n"]
    finally:
        conn.close()

    assert after_acc == before_acc
    assert after_n == before_n == 2


def test_rollback_no_deja_tablas_parciales(tmp_path, monkeypatch):
    """Si la migración falla a mitad, no quedan tablas nuevas a medias (rollback total)."""
    path = tmp_path / "m.db"
    _legacy_db(path)
    before_tables = _tables(path)

    # Forzar fallo después de crear algunas tablas: parchear _column_exists (usado tras el DDL).
    def boom(conn, table, column):
        raise sqlite3.OperationalError("fallo simulado tras crear tablas")

    monkeypatch.setattr(db, "_column_exists", boom)

    conn = db.get_connection(path)
    try:
        import pytest
        with pytest.raises(sqlite3.OperationalError):
            db.migrate(conn)
    finally:
        conn.close()

    # Rollback: las tablas nuevas NO deben persistir.
    after_tables = _tables(path)
    assert after_tables == before_tables
    assert "beneficiary" not in after_tables
