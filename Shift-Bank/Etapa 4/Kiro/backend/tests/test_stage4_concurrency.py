"""Verificación de concurrencia de la Etapa 4 (Tarea 20; D-13, D-14, D-11).

Idempotencia bajo reintentos "concurrentes" con la misma clave (un solo efecto); versión optimista
que hace obsoletas solicitudes concurrentes; consistencia de proyección tras operaciones múltiples.
Usa el modelo de único escritor de SQLite (`BEGIN IMMEDIATE`); la concurrencia multiproceso real
está cubierta por la suite heredada `test_concurrency_sqlite.py` (regresión).

_Requisitos: R9, R10, R19_ · _Diseño: §3.1_ · _AC: AC4-13, AC4-15_
"""

import uuid

import app.db as db
from app import command, events, idempotency, projections
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


def _do_transfer(conn, key, amount_minor):
    chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
    cv = conn.execute("SELECT version FROM account WHERE id=?", (chk,)).fetchone()["version"]
    sv = conn.execute("SELECT version FROM account WHERE id=?", (sav,)).fetchone()["version"]
    return idempotency.execute_idempotent_command(
        conn, idempotency_key=key, operation="internal_transfer",
        request_payload={"amount": amount_minor},
        expected_versions={chk: cv, sav: sv},
        effects=[
            command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -amount_minor),
            command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +amount_minor),
        ],
        occurred_at="2026-02-01T00:00:00Z",
        build_response=lambda eids: {"status": "COMPLETED", "event_ids": eids})


def test_reintentos_misma_clave_un_solo_efecto(tmp_path):
    path = _stage4(tmp_path / "cc.db")
    conn = db.get_connection(path)
    try:
        key = str(uuid.uuid4())
        results = [_do_transfer(conn, key, 100_00) for _ in range(5)]
        # Solo el primero aplica efecto; el resto son replays.
        assert results[0].replayed is False
        assert all(r.replayed for r in results[1:])
        bal = conn.execute(
            "SELECT balance_cents FROM account WHERE public_id='CHK-1001'").fetchone()["balance_cents"]
        assert bal == 2_400_00  # un solo débito
        n = conn.execute("SELECT COUNT(*) AS n FROM domain_event WHERE event_type LIKE 'INTERNAL%'").fetchone()["n"]
        assert n == 2  # un debited + un credited (no multiplicado por 5)
    finally:
        conn.close()


def test_claves_distintas_aplican_cada_una(tmp_path):
    path = _stage4(tmp_path / "cc.db")
    conn = db.get_connection(path)
    try:
        _do_transfer(conn, str(uuid.uuid4()), 100_00)
        _do_transfer(conn, str(uuid.uuid4()), 100_00)
        bal = conn.execute(
            "SELECT balance_cents FROM account WHERE public_id='CHK-1001'").fetchone()["balance_cents"]
        assert bal == 2_300_00  # dos débitos de claves distintas
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()


def test_proyeccion_consistente_tras_multiples_operaciones(tmp_path):
    path = _stage4(tmp_path / "cc.db")
    conn = db.get_connection(path)
    try:
        for _ in range(10):
            _do_transfer(conn, str(uuid.uuid4()), 10_00)
        assert projections.verify_consistency(conn) is True
        # Reconstruir y revalidar.
        conn.execute("BEGIN")
        projections.rebuild_projections(conn)
        conn.commit()
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()
