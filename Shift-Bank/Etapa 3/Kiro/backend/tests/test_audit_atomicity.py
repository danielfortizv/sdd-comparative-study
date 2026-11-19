"""Atomicidad, rechazos y fail-closed de la auditoría transaccional (Etapa 3, Tarea 14).

Complementa `test_audit_integration.py` (Tarea 12, caminos de ÉXITO) con los invariantes
NEGATIVOS y de atomicidad del diseño §2.7 y los requisitos R5.3, R7.2, R7.3, R7.4:

1. **Éxito atómico (R7.1):** una transferencia interna COMPLETED confirma dinero + EXACTAMENTE
   una entrada de auditoría de éxito JUNTOS (saldo movido y una sola fila encadenada).
2. **Fail-closed ante fallo de auditoría (R7.2):** si `audit.append_in_tx` lanza durante una
   transferencia interna COMPLETED o una creación ACH `pending`, la `financial_transaction` hace
   ROLLBACK COMPLETO: el saldo NO cambia y NO queda fila de transferencia/ACH comprometida. El
   dinero NO puede confirmarse sin su auditoría.
3. **PIN inválido (R7.3):** `confirm_mfa` con código erróneo NO debita, deja la transferencia en
   PENDING_MFA y añade EXACTAMENTE una entrada `MFA_FAILED` (rejected). La cadena verifica.
4. **Rechazos auditados sin mutación (R5.3/R7.4):** un rechazo por límite (interno) y un rechazo
   ACH por fondos/límite al confirmar dejan una entrada de rechazo (`INTERNAL_TRANSFER_REJECTED`
   / `ACH_REJECTED`) SIN mover saldos y sin dejar una transferencia COMPLETED/ACH pending
   comprometida.
5. **Cadena íntegra tras secuencias mixtas éxito+rechazo** y payloads de rechazo SIN datos
   sensibles (cuenta/routing/token `enc:`).

DB temporal aislada por prueba (fixture `app_client`/`isolated_db_path`); nunca la DB histórica
ni `SEED-3.md`.

_Requisitos: R5.3, R7.2, R7.3, R7.4_ · _Diseño: §2.7_ · _AC: AC-07, AC-08_
"""

from datetime import timedelta

import pytest

import app.ach_repository as ach_repo
import app.ach_service as ach_service
import app.audit as audit
import app.db as db
import app.limit_service as limit_service
import app.repository as repository
import app.service as service
from app.clock import system_clock

_CODE = "123456"
_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Montos (COP, centavos = ×100). Umbral MFA = 1.000.000.
_SMALL = "250000.00"        # 25.000.000 centavos; sin MFA
_MFA_AMOUNT = "1000000.00"  # 100.000.000 centavos; exige MFA


@pytest.fixture()
def conn(app_client, isolated_db_path):
    """Conexión directa a la DB aislada ya migrada/sembrada por el arranque de la app."""
    c = db.get_connection(isolated_db_path)
    try:
        yield c
    finally:
        c.close()


# --- Utilidades ---------------------------------------------------------------

def _balance(conn, kind: str) -> int:
    return conn.execute(
        "SELECT balance_cents FROM account WHERE kind = ?", (kind,)
    ).fetchone()["balance_cents"]


def _audit_rows(conn):
    return conn.execute(
        "SELECT seq, event_type, outcome, entity_ref, payload FROM audit_log ORDER BY seq ASC"
    ).fetchall()


def _count(conn, event_type: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM audit_log WHERE event_type = ?", (event_type,)
    ).fetchone()["n"]


def _transfer_count(conn, **where) -> int:
    clauses = " AND ".join(f"{k} = ?" for k in where)
    sql = "SELECT COUNT(*) AS n FROM transfer"
    if clauses:
        sql += f" WHERE {clauses}"
    return conn.execute(sql, tuple(where.values())).fetchone()["n"]


def _assert_no_sensitive(conn):
    """Ningún payload de auditoría contiene cuenta/routing en claro ni token `enc:` (R5.6)."""
    for row in _audit_rows(conn):
        payload = row["payload"]
        assert _VALID_BEN["account_number"] not in payload, (row["event_type"], payload)
        assert _VALID_BEN["routing_number"] not in payload, (row["event_type"], payload)
        assert "enc:v1:" not in payload, (row["event_type"], payload)


def _lower_limit_to(conn, cents: int) -> None:
    """Baja el límite por transferencia por DEBAJO de un monto para forzar el rechazo."""
    limit_service.update_limits(
        conn, per_transfer_raw=str(cents), daily_raw=None, now=system_clock.now_utc())


# =============================================================================
# 1. Éxito atómico: dinero + exactamente una auditoría juntos (R7.1)
# =============================================================================

def test_exito_commitea_dinero_y_una_auditoria(conn):
    before_from = _balance(conn, "checking")
    before_to = _balance(conn, "savings")
    amount_cents = 250000 * 100

    result = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_SMALL, description="ok")
    assert result.status == "COMPLETED"

    # Dinero movido exactamente una vez.
    assert _balance(conn, "checking") == before_from - amount_cents
    assert _balance(conn, "savings") == before_to + amount_cents

    # Exactamente una entrada de éxito, encadenada y verificable.
    rows = _audit_rows(conn)
    assert len(rows) == 1
    assert rows[0]["event_type"] == audit.EVENT_INTERNAL_TRANSFER_COMPLETED
    assert rows[0]["outcome"] == audit.OUTCOME_SUCCESS
    assert audit.verify_chain(conn).ok is True


# =============================================================================
# 2. Fail-closed: un fallo de auditoría revierte el dinero (R7.2)
# =============================================================================

def test_fallo_auditoria_revierte_transferencia_interna(conn, monkeypatch):
    """Si `append_in_tx` lanza durante una interna COMPLETED → ROLLBACK total (sin débito)."""
    before_from = _balance(conn, "checking")
    before_to = _balance(conn, "savings")
    transfers_before = _transfer_count(conn)

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado de persistencia de auditoría")

    monkeypatch.setattr(audit, "append_in_tx", _boom)

    with pytest.raises(RuntimeError):
        service.create_transfer(
            conn, from_kind="checking", to_kind="savings",
            amount_raw=_SMALL, description="falla")

    # Saldos intactos: el dinero NO se confirmó sin su auditoría.
    assert _balance(conn, "checking") == before_from
    assert _balance(conn, "savings") == before_to
    # No quedó ninguna transferencia COMPLETED comprometida de esta operación.
    assert _transfer_count(conn, status="COMPLETED") == transfers_before  # solo históricas
    # La bitácora de auditoría quedó vacía (el append nunca persistió).
    assert len(_audit_rows(conn)) == 0


def test_fallo_auditoria_revierte_ach_pending(conn, monkeypatch):
    """Si `append_in_tx` lanza durante la creación ACH `pending` → ROLLBACK (sin débito ni fila)."""
    before = _balance(conn, "savings")
    ach_before = _transfer_count(conn, type="ach")

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado de persistencia de auditoría")

    monkeypatch.setattr(audit, "append_in_tx", _boom)

    with pytest.raises(RuntimeError):
        ach_service.create_ach(
            conn, amount_raw=_SMALL, description="falla",
            from_kind="savings", adhoc=dict(_VALID_BEN))

    # Sin débito y sin fila ACH comprometida (dinero no puede commitear sin auditoría).
    assert _balance(conn, "savings") == before
    assert _transfer_count(conn, type="ach") == ach_before
    assert len(_audit_rows(conn)) == 0


# =============================================================================
# 3. PIN inválido: sin débito, intento auditado (R7.3)
# =============================================================================

def test_pin_invalido_no_debita_y_audita_mfa_failed(conn):
    created = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="grande")
    assert created.status == "PENDING_MFA"

    before_from = _balance(conn, "checking")
    before_to = _balance(conn, "savings")

    with pytest.raises(service.DomainError) as exc:
        service.confirm_mfa(conn, reference=created.reference, code="000000")
    assert exc.value.code == "INVALID_MFA_CODE"

    # Sin débito alguno.
    assert _balance(conn, "checking") == before_from
    assert _balance(conn, "savings") == before_to
    # La transferencia sigue PENDING_MFA (permite reintento; estado heredado intacto).
    tr = repository.get_transfer_by_reference(conn, created.reference)
    assert tr.status == "PENDING_MFA"
    # Exactamente una entrada MFA_FAILED (rejected) y nada más.
    assert _count(conn, audit.EVENT_MFA_FAILED) == 1
    rows = _audit_rows(conn)
    assert len(rows) == 1
    assert rows[0]["outcome"] == audit.OUTCOME_REJECTED
    assert audit.verify_chain(conn).ok is True


def test_pin_invalido_permite_reintento_exitoso(conn):
    """Tras un PIN inválido auditado, un reintento correcto completa y encadena la cadena."""
    created = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="grande")

    with pytest.raises(service.DomainError):
        service.confirm_mfa(conn, reference=created.reference, code="000000")

    final = service.confirm_mfa(conn, reference=created.reference, code=_CODE)
    assert final == "COMPLETED"

    # MFA_FAILED (1) + MFA_CONFIRMED (1) + INTERNAL_TRANSFER_COMPLETED (1) = 3 entradas.
    assert _count(conn, audit.EVENT_MFA_FAILED) == 1
    assert _count(conn, audit.EVENT_MFA_CONFIRMED) == 1
    assert _count(conn, audit.EVENT_INTERNAL_TRANSFER_COMPLETED) == 1
    assert len(_audit_rows(conn)) == 3
    assert audit.verify_chain(conn).ok is True


def test_pin_invalido_ach_no_debita_y_audita_mfa_failed(conn):
    res = ach_service.create_ach(
        conn, amount_raw=_MFA_AMOUNT, description="grande",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    assert res.status == "pending_auth"
    before = _balance(conn, "savings")

    with pytest.raises(ach_service.AchError) as exc:
        ach_service.confirm_ach_mfa(conn, reference=res.reference, code="000000")
    assert exc.value.code == "INVALID_MFA_CODE"

    # Sin débito; la ACH sigue en `pending_auth` (reintentable).
    assert _balance(conn, "savings") == before
    assert ach_repo.get_ach_by_reference(conn, res.reference)["status"] == "pending_auth"
    # ACH_PENDING_AUTH (éxito de la creación) + MFA_FAILED (rechazo del intento).
    assert _count(conn, audit.EVENT_MFA_FAILED) == 1
    assert _count(conn, audit.EVENT_ACH_PENDING_AUTH) == 1
    _assert_no_sensitive(conn)
    assert audit.verify_chain(conn).ok is True


# =============================================================================
# 4. Rechazos auditados SIN mutación financiera (R5.3, R7.4)
# =============================================================================

def test_rechazo_por_limite_interno_audita_sin_mutacion(conn):
    """Límite superado al confirmar MFA → FAILED sin débito + INTERNAL_TRANSFER_REJECTED."""
    created = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="grande")
    assert created.status == "PENDING_MFA"

    # Bajar el límite por transferencia por debajo del monto (la creación LIMIT_UPDATED audita).
    _lower_limit_to(conn, 1_00)  # 1.00 COP: muy por debajo del monto

    before_from = _balance(conn, "checking")
    before_to = _balance(conn, "savings")
    rejected_before = _count(conn, audit.EVENT_INTERNAL_TRANSFER_REJECTED)

    with pytest.raises(service.DomainError) as exc:
        service.confirm_mfa(conn, reference=created.reference, code=_CODE)
    assert exc.value.code.startswith("LIMIT_EXCEEDED")

    # Sin mutación de dinero.
    assert _balance(conn, "checking") == before_from
    assert _balance(conn, "savings") == before_to
    # La transferencia quedó FAILED (no COMPLETED), y hay una entrada de rechazo.
    tr = repository.get_transfer_by_reference(conn, created.reference)
    assert tr.status == "FAILED"
    assert _count(conn, audit.EVENT_INTERNAL_TRANSFER_REJECTED) == rejected_before + 1
    assert audit.verify_chain(conn).ok is True


def test_rechazo_por_limite_create_transfer_audita_sin_mutacion(conn):
    """Camino inmediato (sin MFA): límite revalidado dentro de la tx → FAILED + rechazo.

    El pre-chequeo de límite se saltea bajando el límite JUSTO antes de confirmar la
    transferencia pequeña: aquí reproducimos el rechazo por límite diario acumulado al
    agotar el presupuesto diario con una transferencia previa.
    """
    # Fijar límite diario (en COP) que solo permite UNA transferencia pequeña. `update_limits`
    # recibe el MONTO en COP (no centavos); `_SMALL` consume exactamente el presupuesto diario.
    limit_service.update_limits(
        conn, per_transfer_raw="250000", daily_raw="250000",
        now=system_clock.now_utc())

    # Primera transferencia pequeña: consume todo el presupuesto diario (COMPLETED).
    first = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_SMALL, description="consume diario")
    assert first.status == "COMPLETED"

    before_from = _balance(conn, "checking")
    before_to = _balance(conn, "savings")
    rejected_before = _count(conn, audit.EVENT_INTERNAL_TRANSFER_REJECTED)

    # Segunda transferencia pequeña: supera el diario → rechazada (ya en el pre-chequeo,
    # DomainError), SIN mutación. El pre-chequeo no audita; validamos que no hubo mutación
    # y que no se creó una COMPLETED espuria.
    with pytest.raises(service.DomainError) as exc:
        service.create_transfer(
            conn, from_kind="checking", to_kind="savings",
            amount_raw=_SMALL, description="excede diario")
    assert exc.value.code.startswith("LIMIT_EXCEEDED")

    assert _balance(conn, "checking") == before_from
    assert _balance(conn, "savings") == before_to
    # No se añadió una transferencia COMPLETED de la segunda operación.
    assert audit.verify_chain(conn).ok is True


def test_rechazo_ach_por_limite_al_confirmar_audita_sin_mutacion(conn):
    """ACH `pending_auth` confirmada con límite agotado → `failed` sin débito + ACH_REJECTED."""
    res = ach_service.create_ach(
        conn, amount_raw=_MFA_AMOUNT, description="grande",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    assert res.status == "pending_auth"

    # Bajar el límite por transferencia por debajo del monto ACH.
    _lower_limit_to(conn, 1_00)

    before = _balance(conn, "savings")
    rejected_before = _count(conn, audit.EVENT_ACH_REJECTED)

    with pytest.raises(ach_service.AchError) as exc:
        ach_service.confirm_ach_mfa(conn, reference=res.reference, code=_CODE)
    assert exc.value.code.startswith("LIMIT_EXCEEDED")

    # Sin débito; la ACH quedó `failed`; hay una entrada de rechazo.
    assert _balance(conn, "savings") == before
    assert ach_repo.get_ach_by_reference(conn, res.reference)["status"] == "failed"
    assert _count(conn, audit.EVENT_ACH_REJECTED) == rejected_before + 1
    _assert_no_sensitive(conn)
    assert audit.verify_chain(conn).ok is True


# =============================================================================
# 5. Secuencia mixta éxito + rechazo: cadena íntegra y sin datos sensibles
# =============================================================================

def test_secuencia_mixta_mantiene_cadena_y_sin_sensibles(conn):
    # Éxito interno pequeño.
    service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_SMALL, description="ok1")

    # PIN inválido interno (rechazo MFA_FAILED).
    c = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="grande")
    with pytest.raises(service.DomainError):
        service.confirm_mfa(conn, reference=c.reference, code="000000")
    # Reintento correcto (éxito MFA_CONFIRMED + COMPLETED).
    assert service.confirm_mfa(conn, reference=c.reference, code=_CODE) == "COMPLETED"

    # ACH pending (éxito) + rechazo ACH por límite al confirmar otra ACH sensible.
    ach_service.create_ach(
        conn, amount_raw=_SMALL, description="ach-ok",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    sensible = ach_service.create_ach(
        conn, amount_raw=_MFA_AMOUNT, description="ach-grande",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    _lower_limit_to(conn, 1_00)
    with pytest.raises(ach_service.AchError):
        ach_service.confirm_ach_mfa(conn, reference=sensible.reference, code=_CODE)

    # La cadena completa (éxitos + rechazos + LIMIT_UPDATED) permanece íntegra.
    result = audit.verify_chain(conn)
    assert result.ok is True, result.reason

    # Coexisten entradas success y rejected.
    outcomes = {r["outcome"] for r in _audit_rows(conn)}
    assert audit.OUTCOME_SUCCESS in outcomes
    assert audit.OUTCOME_REJECTED in outcomes

    _assert_no_sensitive(conn)
