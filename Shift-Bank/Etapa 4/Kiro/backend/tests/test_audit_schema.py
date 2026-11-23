"""Verificación del esquema de auditoría de la Etapa 3 — tablas, triggers, WAL (Tarea 9).

Verifica el DDL de auditoría añadido a `db.migrate` (design.md §2.1, §2.4, §2.9, §5.1):

- Tablas `audit_log` y `audit_anchor` presentes tras `migrate`.
- Triggers `audit_log_no_update` y `audit_log_no_delete` presentes.
- UPDATE y DELETE ordinarios sobre `audit_log` abortan (append-only, R6.1/R6.2, AC-06).
- `PRAGMA journal_mode` devuelve `wal` sobre un archivo de DB real (WAL persistente, §5.1).
- Idempotencia: ejecutar `migrate` dos veces no falla ni duplica objetos.

Cada prueba construye una DB temporal con el esquema heredado de la Etapa 1 y aplica `migrate`.
Nunca usa la DB histórica ni `SEED-3.md` como objetivo.

_Requisitos: R6.1, R6.2_ · _Diseño: §2.1, §2.4, §2.9, §5.1_ · _AC: AC-06_
"""

import sqlite3

import pytest

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


def _objects(path, obj_type):
    conn = db.get_connection(path)
    try:
        return {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ?", (obj_type,)
            ).fetchall()
        }
    finally:
        conn.close()


def _columns(path, table):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _insert_genesis(conn):
    """Inserta una entrada de auditoría mínima válida para probar UPDATE/DELETE."""
    conn.execute(
        """INSERT INTO audit_log
           (event_type, outcome, entity_ref, occurred_at, payload, prev_hmac, entry_hmac)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("TEST_EVENT", "success", "ref-1", "2026-11-16T00:00:00Z", "{}", "", "deadbeef"),
    )
    conn.commit()


# --- Existencia de tablas, columnas y triggers --------------------------------

def test_tablas_de_auditoria_existen(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    tables = _objects(path, "table")
    assert "audit_log" in tables
    assert "audit_anchor" in tables
    # Las tablas heredadas/E2 siguen existiendo (aditivo).
    for t in ("customer", "account", "transfer", "beneficiary"):
        assert t in tables


def test_columnas_audit_log(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "audit_log")
    assert cols == {
        "seq", "event_type", "outcome", "entity_ref",
        "occurred_at", "payload", "prev_hmac", "entry_hmac",
    }


def test_columnas_audit_anchor(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    cols = _columns(path, "audit_anchor")
    assert cols == {"id", "last_seq", "last_hmac"}


def test_triggers_append_only_existen(tmp_path):
    path = tmp_path / "m.db"
    _migrated_db(path)
    triggers = _objects(path, "trigger")
    assert "audit_log_no_update" in triggers
    assert "audit_log_no_delete" in triggers


# --- Protección append-only (R6.1/R6.2, AC-06) --------------------------------

def test_update_audit_log_aborta(tmp_path):
    """Un UPDATE ordinario sobre audit_log debe abortar por el trigger (append-only)."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        _insert_genesis(conn)
        with pytest.raises(sqlite3.IntegrityError) as exc:
            conn.execute("UPDATE audit_log SET outcome = 'rejected' WHERE seq = 1")
            conn.commit()
        assert "append-only" in str(exc.value)
        # La fila no cambió.
        row = conn.execute("SELECT outcome FROM audit_log WHERE seq = 1").fetchone()
        assert row["outcome"] == "success"
    finally:
        conn.close()


def test_delete_audit_log_aborta(tmp_path):
    """Un DELETE ordinario sobre audit_log debe abortar por el trigger (append-only)."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        _insert_genesis(conn)
        with pytest.raises(sqlite3.IntegrityError) as exc:
            conn.execute("DELETE FROM audit_log WHERE seq = 1")
            conn.commit()
        assert "append-only" in str(exc.value)
        # La fila sigue presente.
        n = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
        assert n == 1
    finally:
        conn.close()


def test_insert_audit_log_permitido(tmp_path):
    """El esquema append-only permite insertar nuevas entradas (solo bloquea UPDATE/DELETE)."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        _insert_genesis(conn)
        conn.execute(
            """INSERT INTO audit_log
               (event_type, outcome, entity_ref, occurred_at, payload, prev_hmac, entry_hmac)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("TEST_EVENT_2", "success", "ref-2", "2026-11-16T00:01:00Z", "{}", "deadbeef", "cafe"),
        )
        conn.commit()
        n = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
        assert n == 2
    finally:
        conn.close()


def test_audit_anchor_single_row_check(tmp_path):
    """La tabla ancla solo admite la fila id=1 (CHECK id=1)."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        conn.execute("INSERT INTO audit_anchor (id, last_seq, last_hmac) VALUES (1, 0, '')")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO audit_anchor (id, last_seq, last_hmac) VALUES (2, 0, '')")
            conn.commit()
    finally:
        conn.close()


# --- WAL persistente sobre archivo real (§5.1, DT-7) --------------------------

def test_journal_mode_wal_en_archivo_real(tmp_path):
    """Sobre un archivo de DB real, el modo de journaling es WAL tras migrate."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_wal_persistente_en_nueva_conexion(tmp_path):
    """WAL es una propiedad persistente del archivo: una conexión posterior ya lo reporta."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    # Nueva conexión completamente independiente.
    conn = sqlite3.connect(str(path))
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


# --- Idempotencia -------------------------------------------------------------

def test_migrate_idempotente_con_auditoria(tmp_path):
    """Ejecutar migrate() dos veces no falla ni duplica tablas/triggers de auditoría."""
    path = tmp_path / "m.db"
    _migrated_db(path)
    tables1, triggers1 = _objects(path, "table"), _objects(path, "trigger")
    conn = db.get_connection(path)
    try:
        db.migrate(conn)  # segunda vez
    finally:
        conn.close()
    assert _objects(path, "table") == tables1
    assert _objects(path, "trigger") == triggers1
    assert {"audit_log", "audit_anchor"}.issubset(_objects(path, "table"))
    assert {"audit_log_no_update", "audit_log_no_delete"}.issubset(_objects(path, "trigger"))
