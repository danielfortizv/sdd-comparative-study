"""Integración transaccional de auditoría en operaciones financieras (Etapa 3, Tarea 12).

Verifica que cada transición financiera exitosa emite EXACTAMENTE una entrada de auditoría
encadenada DENTRO de la misma `financial_transaction` que aplica el cambio de dinero/estado, de
modo que dinero + auditoría se confirman atómicamente (R7.1) y la cadena permanece verificable
(`verify_chain`). Cubre los puntos de emisión de design.md §5.2:

- Transferencia interna COMPLETED (ruta inmediata, sin MFA) → 1 entrada
  `INTERNAL_TRANSFER_COMPLETED`.
- Transferencia interna confirmada por MFA → `MFA_CONFIRMED` + `INTERNAL_TRANSFER_COMPLETED`.
- ACH: creación `pending`, creación sensible `pending_auth`, confirmación MFA, settlement, fallo
  con reembolso → una entrada por transición (`ACH_PENDING`, `ACH_PENDING_AUTH`, `ACH_CONFIRMED`,
  `ACH_SETTLED`, `ACH_FAILED_REFUNDED`).
- Ejecución recurrente (`process_due`) → `RECURRING_EXECUTED`; una ocurrencia DUPLICADA (colisión
  UNIQUE, `skipped`) NO deja fila de auditoría (la IntegrityError revierte toda la transacción,
  incluida la append).

Además: los payloads NUNCA contienen dígitos de cuenta/routing sensibles (R5.6).

Reloj determinista (`ManualClock`) para settlement; sin esperas reales. DB temporal aislada por
prueba (nunca la DB histórica ni `SEED-3.md`).

_Requisitos: R5.1, R7.1, R7.5_ · _Diseño: §2.3, §2.7, §5.2_ · _AC: AC-05, AC-07_
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.ach_repository as ach_repo
import app.ach_service as ach_service
import app.audit as audit
import app.db as db
import app.recurring_service as recurring_service
import app.repository as repository
import app.service as service
from app.clock import iso, parse_iso

_CODE = "123456"
_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# Montos (COP). Umbral MFA = 1.000.000 → por debajo no exige MFA, a partir de él sí.
_SMALL = "250000.00"        # 25.000.000 centavos, sin MFA
_MFA_AMOUNT = "1000000.00"  # 100.000.000 centavos, exige MFA


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


def _assert_no_sensitive_digits(conn):
    """Ningún payload de auditoría debe contener la cuenta/routing del beneficiario (R5.6)."""
    for row in _audit_rows(conn):
        payload = row["payload"]
        assert _VALID_BEN["account_number"] not in payload, (row["event_type"], payload)
        assert _VALID_BEN["routing_number"] not in payload, (row["event_type"], payload)
        # Tampoco tokens de cifrado crudos.
        assert "enc:v1:" not in payload, (row["event_type"], payload)


# --- Transferencia interna COMPLETED (sin MFA) --------------------------------

def test_internal_completed_emite_una_entrada(conn):
    """Una transferencia interna inmediata (sin MFA) emite exactamente un COMPLETED."""
    result = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_SMALL, description="ahorro")
    assert result.status == "COMPLETED"

    assert _count(conn, audit.EVENT_INTERNAL_TRANSFER_COMPLETED) == 1
    rows = _audit_rows(conn)
    assert len(rows) == 1
    assert rows[0]["outcome"] == audit.OUTCOME_SUCCESS
    assert audit.verify_chain(conn).ok is True


# --- Transferencia interna confirmada por MFA ---------------------------------

def test_internal_mfa_emite_confirmed_y_completed(conn):
    """Confirmar una transferencia PENDING_MFA emite MFA_CONFIRMED + INTERNAL_TRANSFER_COMPLETED."""
    created = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="grande")
    assert created.status == "PENDING_MFA"
    # La creación PENDING_MFA no mueve dinero → no audita transición financiera.
    assert len(_audit_rows(conn)) == 0

    final = service.confirm_mfa(conn, reference=created.reference, code=_CODE)
    assert final == "COMPLETED"

    assert _count(conn, audit.EVENT_MFA_CONFIRMED) == 1
    assert _count(conn, audit.EVENT_INTERNAL_TRANSFER_COMPLETED) == 1
    # Exactamente dos transiciones auditadas para esta operación.
    assert len(_audit_rows(conn)) == 2
    assert audit.verify_chain(conn).ok is True


# --- ACH pending (sin MFA) ----------------------------------------------------

def test_ach_pending_emite_una_entrada(conn):
    res = ach_service.create_ach(
        conn, amount_raw=_SMALL, description="proveedor",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    assert res.status == "pending"

    assert _count(conn, audit.EVENT_ACH_PENDING) == 1
    assert len(_audit_rows(conn)) == 1
    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


# --- ACH sensible: pending_auth → (confirm) pending ---------------------------

def test_ach_pending_auth_y_confirm_emiten_una_cada_uno(conn):
    res = ach_service.create_ach(
        conn, amount_raw=_MFA_AMOUNT, description="grande",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    assert res.status == "pending_auth"
    assert _count(conn, audit.EVENT_ACH_PENDING_AUTH) == 1

    final = ach_service.confirm_ach_mfa(conn, reference=res.reference, code=_CODE)
    assert final == "pending"
    assert _count(conn, audit.EVENT_ACH_CONFIRMED) == 1

    # Dos transiciones (pending_auth + confirmación), ninguna duplicada.
    assert len(_audit_rows(conn)) == 2
    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


# --- ACH settlement -----------------------------------------------------------

def test_ach_settle_emite_una_entrada_solo_al_transicionar(conn):
    res = ach_service.create_ach(
        conn, amount_raw=_SMALL, description="proveedor",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    row = ach_repo.get_ach_by_reference(conn, res.reference)
    tid = row["id"]
    created = parse_iso(row["created_at"])

    # Antes del retardo de settlement: no transiciona ni audita.
    assert ach_service.settle_ach(conn, tid, now=created + timedelta(seconds=1)) is False
    assert _count(conn, audit.EVENT_ACH_SETTLED) == 0

    # Tras el retardo: transiciona y audita exactamente una vez.
    later = created + timedelta(seconds=ach_service.ACH_SETTLEMENT_DELAY_SECONDS + 1)
    assert ach_service.settle_ach(conn, tid, now=later) is True
    assert _count(conn, audit.EVENT_ACH_SETTLED) == 1

    # Idempotencia: un segundo settle no transiciona ni añade otra entrada.
    assert ach_service.settle_ach(conn, tid, now=later) is False
    assert _count(conn, audit.EVENT_ACH_SETTLED) == 1

    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


# --- ACH fallo + reembolso ----------------------------------------------------

def test_ach_fail_emite_una_entrada_solo_al_transicionar(conn):
    res = ach_service.create_ach(
        conn, amount_raw=_SMALL, description="proveedor",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    row = ach_repo.get_ach_by_reference(conn, res.reference)
    tid = row["id"]

    assert ach_service.fail_ach(conn, tid) is True
    assert _count(conn, audit.EVENT_ACH_FAILED_REFUNDED) == 1

    # Idempotencia del reembolso exactamente-una-vez: no re-transiciona ni re-audita.
    assert ach_service.fail_ach(conn, tid) is False
    assert _count(conn, audit.EVENT_ACH_FAILED_REFUNDED) == 1

    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True


# --- Ejecución recurrente: ejecutada y duplicado omitido ----------------------

def _make_internal_due(conn, *, created_now):
    """Crea un schedule interno con `next_run_at` vencido respecto a `_NOW`."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", description="ahorro", now=created_now)
    due = iso(_NOW)
    conn.execute(
        "UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    conn.commit()
    return res.id, due


def test_recurring_executed_emite_una_entrada(conn):
    sid, _due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))

    summary = recurring_service.process_due(conn, _NOW)
    assert summary.executed == 1 and summary.failed == 0 and summary.skipped == 0

    assert _count(conn, audit.EVENT_RECURRING_EXECUTED) == 1
    assert len(_audit_rows(conn)) == 1
    assert audit.verify_chain(conn).ok is True


def test_recurring_ocurrencia_duplicada_no_deja_auditoria(conn):
    """Una ocurrencia repetida (misma due_at) colisiona con la UNIQUE → skipped, SIN auditoría.

    Se fuerza el mismo vencimiento tras la primera ejecución para reproducir un tick solapado /
    reintento sobre una ocurrencia ya registrada. El INSERT en `schedule_execution` lanza
    IntegrityError y revierte toda la transacción, incluida la append de auditoría.
    """
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))

    # Primera ejecución: una entrada de auditoría.
    summary1 = recurring_service.process_due(conn, _NOW)
    assert summary1.executed == 1
    assert _count(conn, audit.EVENT_RECURRING_EXECUTED) == 1
    audit_after_first = len(_audit_rows(conn))
    assert audit_after_first == 1

    # Retroceder next_run_at al MISMO vencimiento ya procesado para forzar la colisión UNIQUE.
    conn.execute(
        "UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, sid))
    conn.commit()

    summary2 = recurring_service.process_due(conn, _NOW)
    assert summary2.skipped == 1 and summary2.executed == 0 and summary2.failed == 0

    # La ocurrencia OMITIDA no añadió ninguna fila de auditoría (el recuento no cambia).
    assert len(_audit_rows(conn)) == audit_after_first
    assert _count(conn, audit.EVENT_RECURRING_EXECUTED) == 1
    assert audit.verify_chain(conn).ok is True


# --- Conteo global: nº de entradas == nº de transiciones financieras ----------

def test_conteo_auditoria_igual_a_transiciones(conn):
    """La cuenta total de auditoría coincide con el número de transiciones financieras emitidas.

    Secuencia: 1 interna COMPLETED (1) + 1 MFA interna (2) + 1 ACH pending (1) + 1 ACH settle (1)
    = 5 transiciones → 5 entradas. Una ocurrencia duplicada recurrente NO aporta entrada.
    """
    # 1) interna sin MFA → 1
    service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_SMALL, description="a")
    # 2) interna con MFA → 2 (MFA_CONFIRMED + COMPLETED)
    c2 = service.create_transfer(
        conn, from_kind="checking", to_kind="savings",
        amount_raw=_MFA_AMOUNT, description="b")
    service.confirm_mfa(conn, reference=c2.reference, code=_CODE)
    # 3) ACH pending → 1
    ach = ach_service.create_ach(
        conn, amount_raw=_SMALL, description="c",
        from_kind="savings", adhoc=dict(_VALID_BEN))
    # 4) ACH settle → 1
    ach_row = ach_repo.get_ach_by_reference(conn, ach.reference)
    tid = ach_row["id"]
    later = parse_iso(ach_row["created_at"]) + timedelta(
        seconds=ach_service.ACH_SETTLEMENT_DELAY_SECONDS + 1)
    assert ach_service.settle_ach(conn, tid, now=later) is True

    assert len(_audit_rows(conn)) == 5
    _assert_no_sensitive_digits(conn)
    assert audit.verify_chain(conn).ok is True
