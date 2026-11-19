"""Auditoría de eventos de configuración sensible (Etapa 3, Tarea 13).

Verifica que las acciones de configuración/administración —alta/baja de beneficiario,
actualización de límites y ciclo de vida de schedule (pausar/reanudar/cancelar)— emiten
EXACTAMENTE una entrada de auditoría del tipo correcto, cada una DENTRO de la misma
`financial_transaction` que aplica su cambio (atomicidad, R5.2; design.md §2.7, §5.2), mientras
que las consultas de solo lectura (listar beneficiarios/límites/recurrentes, historial) NO
generan auditoría (R5.5).

Cobertura de la tarea:

- `BENEFICIARY_CREATED` en `POST /api/beneficiaries`; `BENEFICIARY_DELETED` en
  `DELETE /api/beneficiaries/{id}` (solo cuando la baja transiciona).
- `LIMIT_UPDATED` en `limit_service.update_limits`.
- `SCHEDULE_PAUSED` / `SCHEDULE_RESUMED` / `SCHEDULE_CANCELLED` en el ciclo de vida de schedule.
- Atomicidad (fail-closed, R7.2): si `audit.append_in_tx` se fuerza a fallar, el cambio de
  configuración NO persiste (ROLLBACK) para beneficiario, límite y schedule.
- Lecturas sin auditoría (R5.5).
- `verify_chain` íntegra tras las emisiones; payloads NO sensibles (R5.6): sin cuenta/routing en
  claro ni tokens `enc:`.

DB temporal aislada por prueba (nunca la DB histórica ni `SEED-3.md`). Decisión documentada
(Tarea 13): el alta de beneficiario vía `ach_service.create_ach` (save_adhoc) NO emite
`BENEFICIARY_CREATED` —esa ruta ya queda cubierta por el evento `ACH_*`—; `BENEFICIARY_CREATED`
se emite solo en la ruta explícita `POST /api/beneficiaries`.

_Requisitos: R5.2, R5.5_ · _Diseño: §2.7, §5.2_ · _AC: AC-05_
"""

from datetime import datetime, timezone

import pytest

import app.audit as audit
import app.ach_repository as ach_repo
import app.db as db
import app.limit_service as limit_service
import app.recurring_service as recurring_service

_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(app_client, isolated_db_path):
    """Conexión directa a la DB aislada ya migrada/sembrada por el arranque de la app."""
    c = db.get_connection(isolated_db_path)
    try:
        yield c
    finally:
        c.close()


def _audit_rows(conn):
    return conn.execute(
        "SELECT seq, event_type, outcome, entity_ref, payload FROM audit_log ORDER BY seq ASC"
    ).fetchall()


def _count(conn, event_type):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM audit_log WHERE event_type = ?", (event_type,)
    ).fetchone()["n"]


def _audit_total(conn):
    return conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]


def _assert_no_sensitive_digits(conn):
    """Ningún payload de auditoría contiene cuenta/routing en claro ni token `enc:` (R5.6)."""
    for row in _audit_rows(conn):
        payload = row["payload"]
        assert _VALID_BEN["account_number"] not in payload, (row["event_type"], payload)
        assert _VALID_BEN["routing_number"] not in payload, (row["event_type"], payload)
        assert "enc:v1:" not in payload, (row["event_type"], payload)


def _create_beneficiary_api(app_client) -> str:
    resp = app_client.post("/api/beneficiaries", json=_VALID_BEN)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- Beneficiarios: alta / baja ------------------------------------------------

def test_beneficiary_created_emite_una_entrada(app_client, conn):
    bid = _create_beneficiary_api(app_client)

    assert _count(conn, audit.EVENT_BENEFICIARY_CREATED) == 1
    rows = _audit_rows(conn)
    assert len(rows) == 1
    assert rows[0]["outcome"] == audit.OUTCOME_SUCCESS
    assert rows[0]["entity_ref"] == f"beneficiary:{bid}"
    # Payload no sensible: banco + cuenta enmascarada (últimos 4), nunca la cuenta completa.
    payload = rows[0]["payload"]
    assert "Banco X" in payload
    assert "3210" in payload  # últimos 4 de la cuenta (enmascarado)
    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


def test_beneficiary_deleted_emite_una_entrada(app_client, conn):
    bid = _create_beneficiary_api(app_client)
    base = _audit_total(conn)

    resp = app_client.delete(f"/api/beneficiaries/{bid}")
    assert resp.status_code == 200, resp.text

    assert _count(conn, audit.EVENT_BENEFICIARY_DELETED) == 1
    assert _audit_total(conn) == base + 1
    rows = _audit_rows(conn)
    assert rows[-1]["entity_ref"] == f"beneficiary:{bid}"
    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


def test_beneficiary_delete_inexistente_no_audita(app_client, conn):
    """Una baja de un id inexistente devuelve 404 y NO genera entrada de auditoría."""
    base = _audit_total(conn)
    resp = app_client.delete("/api/beneficiaries/no-such-id")
    assert resp.status_code == 404
    assert _audit_total(conn) == base
    assert _count(conn, audit.EVENT_BENEFICIARY_DELETED) == 0


# --- Límites -------------------------------------------------------------------

def test_limit_updated_emite_una_entrada(conn):
    updated = limit_service.update_limits(
        conn, per_transfer_raw="500000.00", daily_raw="2000000.00", now=_NOW)
    assert updated.per_transfer_cents == 50000000
    assert updated.daily_cents == 200000000

    assert _count(conn, audit.EVENT_LIMIT_UPDATED) == 1
    rows = _audit_rows(conn)
    assert len(rows) == 1
    assert rows[0]["outcome"] == audit.OUTCOME_SUCCESS
    # payload no sensible: solo los nuevos límites en centavos.
    assert "50000000" in rows[0]["payload"]
    assert "200000000" in rows[0]["payload"]
    assert audit.verify_chain(conn).ok is True


def test_limit_update_invalido_no_audita_ni_cambia(conn):
    """Una entrada inválida lanza LimitError, sin auditar ni modificar los límites vigentes."""
    before = limit_service.get_limits(conn)
    with pytest.raises(limit_service.LimitError):
        limit_service.update_limits(
            conn, per_transfer_raw="-10.00", daily_raw=None, now=_NOW)
    assert _audit_total(conn) == 0
    after = limit_service.get_limits(conn)
    assert (after.per_transfer_cents, after.daily_cents) == (
        before.per_transfer_cents, before.daily_cents)


# --- Ciclo de vida de schedule -------------------------------------------------

def _create_schedule(conn) -> str:
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="weekly",
        from_kind="checking", to_kind="savings", description="ahorro", now=_NOW)
    return res.id


def test_schedule_pause_resume_cancel_emiten_una_cada_uno(conn):
    sid = _create_schedule(conn)
    # La creación de un schedule interno no financiero no audita (no es una transición auditada).
    assert _audit_total(conn) == 0

    recurring_service.pause_schedule(conn, sid)
    assert _count(conn, audit.EVENT_SCHEDULE_PAUSED) == 1

    recurring_service.resume_schedule(conn, sid, now=_NOW)
    assert _count(conn, audit.EVENT_SCHEDULE_RESUMED) == 1

    recurring_service.cancel_schedule(conn, sid)
    assert _count(conn, audit.EVENT_SCHEDULE_CANCELLED) == 1

    rows = _audit_rows(conn)
    assert [r["event_type"] for r in rows] == [
        audit.EVENT_SCHEDULE_PAUSED,
        audit.EVENT_SCHEDULE_RESUMED,
        audit.EVENT_SCHEDULE_CANCELLED,
    ]
    for r in rows:
        assert r["entity_ref"] == f"schedule:{sid}"
        # payload no sensible: status + frequency.
        assert "weekly" in r["payload"]
    assert audit.verify_chain(conn).ok is True


def test_schedule_transicion_ilegal_no_audita(conn):
    """Pausar dos veces: la segunda es ilegal (INVALID_STATE_TRANSITION) y NO audita."""
    sid = _create_schedule(conn)
    recurring_service.pause_schedule(conn, sid)
    assert _count(conn, audit.EVENT_SCHEDULE_PAUSED) == 1

    with pytest.raises(recurring_service.RecurringError):
        recurring_service.pause_schedule(conn, sid)
    # Sigue habiendo exactamente una entrada de pausa (la transición ilegal no auditó).
    assert _count(conn, audit.EVENT_SCHEDULE_PAUSED) == 1


# --- Lecturas sin auditoría (R5.5) --------------------------------------------

def test_lecturas_no_generan_auditoria(app_client, conn):
    """GET de beneficiarios/límites/recurrentes/historial no deja ninguna entrada (R5.5)."""
    # Sembrar un beneficiario (1 entrada de alta) y luego solo LEER.
    _create_beneficiary_api(app_client)
    base = _audit_total(conn)
    assert base == 1

    assert app_client.get("/api/beneficiaries").status_code == 200
    assert app_client.get("/api/limits").status_code == 200
    assert app_client.get("/api/recurring").status_code == 200
    # Historial de transferencias (lectura).
    hist = app_client.get("/api/transfers")
    assert hist.status_code in (200, 404)  # tolera variación de ruta heredada

    assert _audit_total(conn) == base  # ninguna lectura añadió auditoría


# --- Atomicidad / rollback (fail-closed, R7.2) --------------------------------

def test_rollback_beneficiario_si_falla_auditoria(app_client, conn, monkeypatch):
    """Si `audit.append_in_tx` falla durante el alta, el beneficiario NO persiste (ROLLBACK)."""
    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado de persistencia de auditoría")

    monkeypatch.setattr(audit, "append_in_tx", _boom)

    # El `TestClient` re-lanza las excepciones del servidor (raise_server_exceptions=True): el
    # fallo del `append` dentro de la `financial_transaction` se propaga y el context manager
    # hace ROLLBACK ANTES de salir del endpoint.
    with pytest.raises(RuntimeError):
        app_client.post("/api/beneficiaries", json=_VALID_BEN)

    # Ni beneficiario ni entrada de auditoría quedaron persistidos (sin alta parcial, R7.2).
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    assert ach_repo.list_beneficiaries(conn, cid) == []
    assert _audit_total(conn) == 0


def test_rollback_limite_si_falla_auditoria(conn, monkeypatch):
    """Si `audit.append_in_tx` falla durante la actualización de límites, el cambio NO persiste."""
    before = limit_service.get_limits(conn)

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado de persistencia de auditoría")

    monkeypatch.setattr(audit, "append_in_tx", _boom)

    with pytest.raises(RuntimeError):
        limit_service.update_limits(
            conn, per_transfer_raw="999999.00", daily_raw="999999.00", now=_NOW)

    after = limit_service.get_limits(conn)
    assert (after.per_transfer_cents, after.daily_cents) == (
        before.per_transfer_cents, before.daily_cents)
    assert _audit_total(conn) == 0


def test_rollback_schedule_si_falla_auditoria(conn, monkeypatch):
    """Si `audit.append_in_tx` falla al pausar, el schedule sigue `active` (ROLLBACK)."""
    sid = _create_schedule(conn)
    before = recurring_service.repository.get_schedule(conn, sid)
    assert before.status == "active"

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado de persistencia de auditoría")

    monkeypatch.setattr(audit, "append_in_tx", _boom)

    with pytest.raises(RuntimeError):
        recurring_service.pause_schedule(conn, sid)

    after = recurring_service.repository.get_schedule(conn, sid)
    assert after.status == "active"  # la transición se revirtió
    assert _audit_total(conn) == 0
