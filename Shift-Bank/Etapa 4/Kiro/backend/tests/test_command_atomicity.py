"""Verificación del patrón de comando atómico (Etapa 4, Tarea 10; D-09, D-11, DK-03).

Evento(s) + proyección + versión + auditoría se confirman juntos; un fallo inyectado revierte
todo (fail-closed), sin estados parciales ni doble aplicación.

_Requisitos: R7, R8, R13_ · _Diseño: §3.1, §4_ · _AC: AC4-09, AC4-12_
"""

import sqlite3

import pytest

import app.db as db
from app import command, events, projections
from app.seed import seed_stage4


def _stage4(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        db.migrate(conn)
        seed_stage4(conn)
    finally:
        conn.close()
    return path


def _aid(conn, public_id):
    return conn.execute("SELECT id FROM account WHERE public_id = ?", (public_id,)).fetchone()["id"]


def _snapshot(conn):
    acc = {r["public_id"]: (r["balance_cents"], r["version"]) for r in conn.execute(
        "SELECT public_id, balance_cents, version FROM account").fetchall()}
    n_events = conn.execute("SELECT COUNT(*) AS n FROM domain_event").fetchone()["n"]
    n_audit = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
    return acc, n_events, n_audit


def test_version_incrementa_una_vez_por_cuenta(tmp_path):
    path = _stage4(tmp_path / "c.db")
    conn = db.get_connection(path)
    try:
        chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
        command.run_command(
            conn,
            effects=[
                command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -100_00),
                command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +100_00),
            ],
            occurred_at="2026-01-02T00:00:00Z",
        )
        vers = {r["public_id"]: r["version"] for r in conn.execute(
            "SELECT public_id, version FROM account").fetchall()}
        assert vers["CHK-1001"] == 2 and vers["SAV-2001"] == 2  # +1 cada una (desde 1)
    finally:
        conn.close()


def test_fallo_inyectado_revierte_todo(tmp_path, monkeypatch):
    path = _stage4(tmp_path / "c.db")
    conn = db.get_connection(path)
    try:
        before = _snapshot(conn)
        chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")

        # Forzar fallo tras aplicar el primer efecto: parchear la auditoría para que lance.
        def boom(*a, **k):
            raise sqlite3.OperationalError("fallo simulado de auditoría")

        monkeypatch.setattr("app.command.audit.append_in_tx", boom)

        with pytest.raises(sqlite3.OperationalError):
            command.run_command(
                conn,
                effects=[
                    command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -100_00),
                    command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +100_00),
                ],
                occurred_at="2026-01-02T00:00:00Z",
                audit_spec=command.AuditSpec("INTERNAL_TRANSFER_COMPLETED", "success", "t:1", {}),
            )
        after = _snapshot(conn)
        # Nada cambió: saldos, versiones, nº de eventos y de auditoría intactos (fail-closed).
        assert after == before
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()


def test_cuenta_desconocida_no_aplica_efectos(tmp_path):
    path = _stage4(tmp_path / "c.db")
    conn = db.get_connection(path)
    try:
        before = _snapshot(conn)
        chk = _aid(conn, "CHK-1001")
        with pytest.raises(command.CommandError):
            command.run_command(
                conn,
                effects=[
                    command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -100_00),
                    command.AccountEffect("no-existe", events.EVENT_INTERNAL_TRANSFER_CREDITED, +100_00),
                ],
                occurred_at="2026-01-02T00:00:00Z",
            )
        assert _snapshot(conn) == before
    finally:
        conn.close()
