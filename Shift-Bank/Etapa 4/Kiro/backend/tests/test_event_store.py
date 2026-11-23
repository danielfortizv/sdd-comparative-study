"""Verificación del almacén de eventos de dominio (Etapa 4, Tarea 8; D-05, D-09).

Append-only, separado de auditoría, versión única por agregado, lectura por agregado y por
operación compuesta.

_Requisitos: R6, R7_ · _Diseño: §1.2, §5_ · _AC: AC4-08, AC4-09_
"""

import sqlite3

import pytest

import app.db as db
from app import events
from app.seed import seed


def _migrated(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        seed(conn)
        db.migrate(conn)
    finally:
        conn.close()
    return path


def test_append_y_lectura_por_agregado(tmp_path):
    path = _migrated(tmp_path / "e.db")
    conn = db.get_connection(path)
    try:
        conn.execute("BEGIN")
        events.append_event_no_commit(
            conn, event_type=events.EVENT_ACCOUNT_OPENED, aggregate_id="a1",
            aggregate_ver=1, operation_id="op1", currency="USD", amount_minor=100,
            payload={"x": 1}, occurred_at="2026-01-01T00:00:00Z")
        events.append_event_no_commit(
            conn, event_type=events.EVENT_INTERNAL_TRANSFER_DEBITED, aggregate_id="a1",
            aggregate_ver=2, operation_id="op2", currency="USD", amount_minor=-40,
            payload={}, occurred_at="2026-01-01T00:01:00Z")
        conn.commit()
        evs = events.read_events(conn, "a1")
        assert [e.aggregate_ver for e in evs] == [1, 2]
        assert events.current_version(conn, "a1") == 2
        assert events.current_version(conn, "nope") == 0
    finally:
        conn.close()


def test_version_unica_por_agregado(tmp_path):
    path = _migrated(tmp_path / "e.db")
    conn = db.get_connection(path)
    try:
        conn.execute("BEGIN")
        events.append_event_no_commit(
            conn, event_type="X", aggregate_id="a1", aggregate_ver=1, operation_id="op1",
            currency="USD", amount_minor=1, payload={}, occurred_at="2026-01-01T00:00:00Z")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("BEGIN")
            events.append_event_no_commit(
                conn, event_type="Y", aggregate_id="a1", aggregate_ver=1, operation_id="op2",
                currency="USD", amount_minor=1, payload={}, occurred_at="2026-01-01T00:00:00Z")
            conn.commit()
    finally:
        conn.rollback()
        conn.close()


def test_evento_compuesto_por_operation_id(tmp_path):
    path = _migrated(tmp_path / "e.db")
    conn = db.get_connection(path)
    try:
        conn.execute("BEGIN")
        events.append_event_no_commit(
            conn, event_type=events.EVENT_CONVERSION_DEBITED, aggregate_id="a1",
            aggregate_ver=1, operation_id="opX", currency="USD", amount_minor=-100,
            payload={}, occurred_at="2026-01-01T00:00:00Z")
        events.append_event_no_commit(
            conn, event_type=events.EVENT_CONVERSION_CREDITED, aggregate_id="a2",
            aggregate_ver=1, operation_id="opX", currency="EUR", amount_minor=90,
            payload={}, occurred_at="2026-01-01T00:00:00Z")
        conn.commit()
        op = events.read_operation(conn, "opX")
        assert len(op) == 2
        assert {e.aggregate_id for e in op} == {"a1", "a2"}
    finally:
        conn.close()


def test_separado_de_audit_log(tmp_path):
    # El almacén de eventos no es la bitácora de auditoría: tablas distintas.
    path = _migrated(tmp_path / "e.db")
    conn = db.get_connection(path)
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "domain_event" in tables and "audit_log" in tables
    finally:
        conn.close()
