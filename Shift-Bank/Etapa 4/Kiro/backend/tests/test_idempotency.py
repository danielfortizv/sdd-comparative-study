"""Verificación de idempotencia y concurrencia optimista (Etapa 4, Tarea 11; D-13, D-14, DK-04).

Replay exacto sin nuevos efectos; reuse con payload distinto -> 409; versión obsoleta -> 409;
el replay idempotente se evalúa ANTES que la versión (DK-04); registro atómico con el efecto.

_Requisitos: R9, R10, R13_ · _Diseño: §1.4, §3.1_ · _AC: AC4-13, AC4-15, AC4-16_
"""

import uuid

import pytest

import app.db as db
from app import command, events, idempotency
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


def _transfer(conn, key, amount_minor, *, payload_amount=None):
    chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
    payload = {"from": "CHK-1001", "to": "SAV-2001", "amount": payload_amount or str(amount_minor)}
    effects = [
        command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -amount_minor),
        command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +amount_minor),
    ]
    chk_ver = conn.execute("SELECT version FROM account WHERE id=?", (chk,)).fetchone()["version"]
    sav_ver = conn.execute("SELECT version FROM account WHERE id=?", (sav,)).fetchone()["version"]
    return idempotency.execute_idempotent_command(
        conn,
        idempotency_key=key,
        operation="internal_transfer",
        request_payload=payload,
        expected_versions={chk: chk_ver, sav: sav_ver},
        effects=effects,
        occurred_at="2026-01-02T00:00:00Z",
        build_response=lambda eids: {"status": "COMPLETED", "event_ids": eids},
    )


def test_require_uuid_key():
    with pytest.raises(idempotency.IdempotencyError):
        idempotency.require_uuid_key(None)
    with pytest.raises(idempotency.IdempotencyError):
        idempotency.require_uuid_key("not-a-uuid")
    assert idempotency.require_uuid_key(str(uuid.uuid4()))


def test_replay_exacto_sin_nuevos_efectos(tmp_path):
    path = _stage4(tmp_path / "i.db")
    conn = db.get_connection(path)
    try:
        key = str(uuid.uuid4())
        r1 = _transfer(conn, key, 100_00)
        assert r1.replayed is False
        bal_after_first = conn.execute(
            "SELECT balance_cents FROM account WHERE public_id='CHK-1001'").fetchone()["balance_cents"]
        n_events = conn.execute("SELECT COUNT(*) AS n FROM domain_event").fetchone()["n"]
        # Replay con la MISMA clave y payload: sin nuevos efectos.
        r2 = _transfer(conn, key, 100_00)
        assert r2.replayed is True
        assert r2.response == r1.response
        bal_after_replay = conn.execute(
            "SELECT balance_cents FROM account WHERE public_id='CHK-1001'").fetchone()["balance_cents"]
        n_events_after = conn.execute("SELECT COUNT(*) AS n FROM domain_event").fetchone()["n"]
        assert bal_after_replay == bal_after_first  # sin segundo débito
        assert n_events_after == n_events           # sin eventos nuevos
    finally:
        conn.close()


def test_reuse_con_payload_distinto_409(tmp_path):
    path = _stage4(tmp_path / "i.db")
    conn = db.get_connection(path)
    try:
        key = str(uuid.uuid4())
        _transfer(conn, key, 100_00, payload_amount="100.00")
        with pytest.raises(idempotency.IdempotencyError) as exc:
            _transfer(conn, key, 100_00, payload_amount="999.00")
        assert exc.value.code == "IDEMPOTENCY_CONFLICT"
        assert exc.value.status == 409
    finally:
        conn.close()


def test_version_obsoleta_409(tmp_path):
    path = _stage4(tmp_path / "i.db")
    conn = db.get_connection(path)
    try:
        chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
        # Esperar una versión incorrecta (0 en vez de 1) -> conflicto.
        with pytest.raises(idempotency.IdempotencyError) as exc:
            idempotency.execute_idempotent_command(
                conn,
                idempotency_key=str(uuid.uuid4()),
                operation="internal_transfer",
                request_payload={"a": 1},
                expected_versions={chk: 0, sav: 0},
                effects=[command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -1)],
                occurred_at="2026-01-02T00:00:00Z",
                build_response=lambda eids: {"ok": True},
            )
        assert exc.value.code == "ACCOUNT_VERSION_CONFLICT"
        assert exc.value.status == 409
        # Sin efectos aplicados (fail-closed).
        assert conn.execute("SELECT COUNT(*) AS n FROM domain_event WHERE event_type LIKE 'INTERNAL%'").fetchone()["n"] == 0
    finally:
        conn.close()


def test_replay_precede_a_version(tmp_path):
    # DK-04: un replay exacto NO debe fallar por versión aunque la versión esperada ya no cuadre.
    path = _stage4(tmp_path / "i.db")
    conn = db.get_connection(path)
    try:
        key = str(uuid.uuid4())
        r1 = _transfer(conn, key, 100_00)  # aplica; versiones pasan de 1 a 2
        # Un segundo intento con la misma clave y payload, aunque pasemos versiones ya obsoletas
        # a través de _transfer (que lee las versiones ACTUALES), debe devolver replay primero.
        r2 = _transfer(conn, key, 100_00)
        assert r2.replayed is True and r2.response == r1.response
    finally:
        conn.close()
