"""Verificación de la evolución de esquema de la Etapa 4 (Tarea 5; D-01/D-02/D-05/D-06/D-13/D-14).

Comprueba que `db.migrate` añade de forma aditiva e idempotente: columnas de `account`
(currency/public_id/version) y `transfer.currency`; las tablas nuevas `domain_event`,
`account_projection`, `idempotency_key`; sus índices y los triggers append-only de eventos; y que
la migración sigue siendo idempotente y transaccional sobre un esquema heredado.

_Requisitos: R1, R2, R6, R8, R9, R10, R15_ · _Diseño: §1_ · _AC: AC4-01, AC4-02, AC4-08, AC4-10,
AC4-14, AC4-15_
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


def _columns(path, table):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _tables(path):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()


def test_account_columnas_multidivisa(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    cols = _columns(path, "account")
    for c in ("currency", "public_id", "version"):
        assert c in cols


def test_transfer_columna_currency(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    assert "currency" in _columns(path, "transfer")


def test_tablas_nuevas_de_etapa4(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    t = _tables(path)
    for name in ("domain_event", "account_projection", "idempotency_key"):
        assert name in t


def test_backfill_currency_usd_en_filas_heredadas(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        acc = conn.execute("SELECT currency, version FROM account").fetchall()
        tr = conn.execute("SELECT currency FROM transfer").fetchall()
    finally:
        conn.close()
    assert all(r["currency"] == "USD" for r in acc)
    assert all(r["version"] == 0 for r in acc)
    assert all(r["currency"] == "USD" for r in tr)


def test_domain_event_append_only(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        conn.execute(
            """INSERT INTO domain_event
               (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
                currency, amount_minor, payload, occurred_at)
               VALUES ('e1','ACCOUNT_OPENED','a1',1,'op1','USD',250000,'{}','2026-01-01T00:00:00Z')"""
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM domain_event WHERE event_id='e1'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE domain_event SET amount_minor=0 WHERE event_id='e1'")
    finally:
        conn.close()


def test_domain_event_unico_por_agregado_version(tmp_path):
    path = tmp_path / "s4.db"
    _migrated_db(path)
    conn = db.get_connection(path)
    try:
        conn.execute(
            """INSERT INTO domain_event
               (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
                currency, amount_minor, payload, occurred_at)
               VALUES ('e1','X','a1',1,'op1','USD',1,'{}','2026-01-01T00:00:00Z')"""
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO domain_event
                   (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
                    currency, amount_minor, payload, occurred_at)
                   VALUES ('e2','X','a1',1,'op2','USD',1,'{}','2026-01-01T00:00:00Z')"""
            )
            conn.commit()
    finally:
        conn.close()


def test_migracion_etapa4_idempotente(tmp_path):
    path = tmp_path / "s4.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)
        first = (_columns(path, "account"), _tables(path))
        db.migrate(conn)
        second = (_columns(path, "account"), _tables(path))
    finally:
        conn.close()
    assert first == second
