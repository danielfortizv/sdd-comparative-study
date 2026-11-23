"""Pruebas de creación/persistencia y MFA en creación de pagos recurrentes (Fase E, Tareas 27–28).

Cubren el alcance de la Tarea 27 (creación/persistencia) y la Tarea 28 (MFA en creación):
- Creación interna y ACH con origen/destino/monto/frecuencia válidos.
- Estado inicial `active` (REC-03).
- Primera fecha de vencimiento (REC-04): fecha futura dada = ese vencimiento; omitida =
  creación + un intervalo completo (nunca inmediata) para diaria/semanal/mensual (A15/A16).
- Snapshot de beneficiario para ACH (REC-11): se conserva y sobrevive al borrado del
  beneficiario guardado.
- Autorización MFA en creación de schedules sensibles (Tarea 28, Req. 8.6, REC-09): monto ≥
  umbral exige MFA; con código correcto → `authorized=1`; sin código o con código incorrecto se
  rechaza y NO se persiste. Los no sensibles se crean directos con `authorized=1` sin MFA.
- Validaciones: frecuencia, monto, origen/destino, beneficiario, fecha de inicio no futura.
- La creación NO mueve saldos (no es una transferencia).

La ejecución de ocurrencias, el ciclo de vida y los endpoints son tareas posteriores y NO se
prueban aquí.

Se usa el reloj inyectable (`ManualClock`) para fechas deterministas, y una conexión directa
a la DB aislada (patrón de `test_ach.py`). El fixture `app_client` dispara el arranque
(migración + siembra) contra la DB temporal.

_Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7_ · _Contrato: REC-01..04, REC-11; A15, A16_
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

import app.ach_repository as ach_repo
import app.db as db
import app.recurring_service as recurring_service
import app.repository as repository
from app.clock import ManualClock, parse_iso


_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Instante base determinista para todas las pruebas de fechas.
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(app_client, isolated_db_path):
    """Conexión directa a la DB aislada ya migrada y sembrada (vía arranque de `app_client`)."""
    c = db.get_connection(isolated_db_path)
    try:
        yield c
    finally:
        c.close()


def _balances(conn):
    rows = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
    return {r["kind"]: r["balance_cents"] for r in rows}


# --- Creación interna ----------------------------------------------------------

def test_crear_schedule_interno_estado_active(conn):
    clock = ManualClock(_NOW)
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", description="ahorro diario",
        now=clock.now_utc())

    assert res.type == "internal"
    assert res.status == "active"                      # REC-03
    assert res.frequency == "daily"
    assert res.requires_mfa is False                   # 100.000 < umbral

    # Persistido con los campos correctos.
    stored = repository.get_schedule(conn, res.id)
    assert stored is not None
    assert stored.status == "active"
    assert stored.type == "internal"
    assert stored.from_kind == "checking" and stored.to_kind == "savings"
    assert stored.amount_cents == 10_000_000
    assert stored.beneficiary_id is None and stored.beneficiary_snapshot is None


def test_crear_schedule_no_mueve_saldos(conn):
    before = _balances(conn)
    recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="weekly",
        from_kind="checking", to_kind="savings", now=_NOW)
    assert _balances(conn) == before                   # creación ≠ transferencia


# --- Primera fecha de vencimiento (REC-04) -------------------------------------

def test_fecha_omitida_un_intervalo_diario(conn):
    """A15: sin fecha de inicio, diaria corre un día después (nunca inmediata)."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="1000.00", frequency="daily",
        from_kind="checking", to_kind="savings", start_at=None, now=_NOW)
    assert parse_iso(res.next_run_at) == _NOW + timedelta(days=1)
    assert parse_iso(res.next_run_at) > _NOW           # nunca inmediata


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_fecha_omitida_un_intervalo_por_frecuencia(conn, frequency, days):
    """A16: semanal/mensual = +7/+30 días; diaria = +1 día."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="1000.00", frequency=frequency,
        from_kind="checking", to_kind="savings", start_at=None, now=_NOW)
    assert parse_iso(res.next_run_at) == _NOW + timedelta(days=days)


def test_fecha_futura_dada_es_primer_vencimiento(conn):
    """REC-04/Req. 8.4: una fecha futura válida es el primer vencimiento exacto."""
    future = "2026-03-15T09:30:00Z"
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="1000.00", frequency="monthly",
        from_kind="checking", to_kind="savings", start_at=future, now=_NOW)
    assert res.next_run_at == future


def test_fecha_inicio_no_futura_rechazada(conn):
    """Una fecha de inicio pasada o igual a 'now' se rechaza (Req. 8.4 exige futura)."""
    for bad in ("2025-12-31T00:00:00Z", "2026-01-01T12:00:00Z"):  # pasada / == now
        with pytest.raises(recurring_service.RecurringError) as exc:
            recurring_service.create_schedule(
                conn, type="internal", amount_raw="1000.00", frequency="daily",
                from_kind="checking", to_kind="savings", start_at=bad, now=_NOW)
        assert exc.value.code == "INVALID_START_DATE"


def test_fecha_inicio_mal_formada_rechazada(conn):
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000.00", frequency="daily",
            from_kind="checking", to_kind="savings", start_at="no-es-fecha", now=_NOW)
    assert exc.value.code == "INVALID_START_DATE"


# --- Creación ACH + snapshot (REC-11) ------------------------------------------

def test_crear_schedule_ach_adhoc_guarda_snapshot(conn):
    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="50000.00", frequency="monthly",
        from_kind="savings", adhoc=_VALID_BEN, description="renta", now=_NOW)
    assert res.type == "ach" and res.status == "active"

    stored = repository.get_schedule(conn, res.id)
    assert stored.beneficiary_id is None               # ad hoc, no guardado
    snap = json.loads(stored.beneficiary_snapshot)
    assert snap == _VALID_BEN                           # snapshot completo persistido


def test_crear_schedule_ach_beneficiario_guardado(conn):
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    bid = ach_repo.create_beneficiary(
        conn, customer_id=cid, name=_VALID_BEN["name"], bank=_VALID_BEN["bank"],
        routing_number=_VALID_BEN["routing_number"],
        account_number=_VALID_BEN["account_number"], created_at="2026-01-01T00:00:00Z")

    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="50000.00", frequency="weekly",
        from_kind="checking", beneficiary_id=bid, now=_NOW)

    stored = repository.get_schedule(conn, res.id)
    assert stored.beneficiary_id == bid
    snap = json.loads(stored.beneficiary_snapshot)
    assert snap["account_number"] == _VALID_BEN["account_number"]


def test_snapshot_sobrevive_al_borrado_del_beneficiario(conn):
    """REC-11/Req. 8.7: el schedule retiene datos suficientes aunque el beneficiario se borre."""
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    bid = ach_repo.create_beneficiary(
        conn, customer_id=cid, name=_VALID_BEN["name"], bank=_VALID_BEN["bank"],
        routing_number=_VALID_BEN["routing_number"],
        account_number=_VALID_BEN["account_number"], created_at="2026-01-01T00:00:00Z")
    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="50000.00", frequency="daily",
        from_kind="checking", beneficiary_id=bid, now=_NOW)

    assert ach_repo.soft_delete_beneficiary(conn, cid, bid, "2026-01-02T00:00:00Z") is True

    stored = repository.get_schedule(conn, res.id)
    snap = json.loads(stored.beneficiary_snapshot)     # snapshot intacto tras el borrado
    assert snap["account_number"] == _VALID_BEN["account_number"]
    assert snap["routing_number"] == _VALID_BEN["routing_number"]


# --- Autorización MFA en creación de schedules sensibles (Tarea 28, Req. 8.6, REC-09) --------

def test_monto_sensible_con_mfa_correcta_queda_autorizado(conn):
    """Req. 8.6: monto ≥ umbral exige MFA al crear; con el código correcto → authorized=1."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="1000000.00", frequency="daily",
        from_kind="checking", to_kind="savings", mfa_code="123456", now=_NOW)
    assert res.requires_mfa is True                    # >= umbral 1.000.000
    assert res.authorized is True                      # MFA de creación superada

    stored = repository.get_schedule(conn, res.id)
    assert stored.requires_mfa == 1 and stored.authorized == 1
    assert stored.status == "active"


def test_monto_sensible_sin_mfa_rechazado_y_no_persiste(conn):
    """Sin código MFA, un schedule sensible se rechaza y no se persiste (no autorizado)."""
    before = conn.execute("SELECT COUNT(*) AS n FROM recurring_schedule").fetchone()["n"]
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000000.00", frequency="daily",
            from_kind="checking", to_kind="savings", now=_NOW)
    assert exc.value.code == "MFA_REQUIRED"
    after = conn.execute("SELECT COUNT(*) AS n FROM recurring_schedule").fetchone()["n"]
    assert after == before                             # nada persistido


def test_monto_sensible_mfa_incorrecta_rechazado_y_no_persiste(conn):
    """Un código MFA incorrecto se rechaza (INVALID_MFA_CODE) y no persiste el schedule."""
    before = conn.execute("SELECT COUNT(*) AS n FROM recurring_schedule").fetchone()["n"]
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000000.00", frequency="daily",
            from_kind="checking", to_kind="savings", mfa_code="000000", now=_NOW)
    assert exc.value.code == "INVALID_MFA_CODE"        # mismo código de error heredado
    after = conn.execute("SELECT COUNT(*) AS n FROM recurring_schedule").fetchone()["n"]
    assert after == before                             # nada persistido


def test_monto_sensible_ach_exige_mfa_en_creacion(conn):
    """La MFA de creación también aplica a schedules ACH sensibles."""
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="ach", amount_raw="1000000.00", frequency="monthly",
            from_kind="savings", adhoc=_VALID_BEN, now=_NOW)
    assert exc.value.code == "MFA_REQUIRED"

    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="1000000.00", frequency="monthly",
        from_kind="savings", adhoc=_VALID_BEN, mfa_code="123456", now=_NOW)
    assert res.requires_mfa is True and res.authorized is True


def test_monto_no_sensible_no_pide_mfa(conn):
    """Compatibilidad Tarea 27: por debajo del umbral se crea directo, authorized=1, sin MFA."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="999999.99", frequency="daily",
        from_kind="checking", to_kind="savings", now=_NOW)
    assert res.requires_mfa is False
    assert res.authorized is True
    stored = repository.get_schedule(conn, res.id)
    assert stored.requires_mfa == 0 and stored.authorized == 1


def test_mfa_code_ignorado_cuando_no_es_sensible(conn):
    """Un `mfa_code` pasado a un schedule no sensible no altera la creación directa."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", mfa_code="000000", now=_NOW)
    assert res.requires_mfa is False and res.authorized is True


# --- Validaciones --------------------------------------------------------------

def test_frecuencia_invalida_rechazada(conn):
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000.00", frequency="yearly",
            from_kind="checking", to_kind="savings", now=_NOW)
    assert exc.value.code == "INVALID_FREQUENCY"


def test_monto_invalido_rechazado(conn):
    for amt, code in [("0.00", "NON_POSITIVE_AMOUNT"), ("-1.00", "NON_POSITIVE_AMOUNT"),
                      ("1.001", "INVALID_AMOUNT")]:
        with pytest.raises(recurring_service.RecurringError) as exc:
            recurring_service.create_schedule(
                conn, type="internal", amount_raw=amt, frequency="daily",
                from_kind="checking", to_kind="savings", now=_NOW)
        assert exc.value.code == code


def test_destino_interno_invalido_rechazado(conn):
    # Mismo origen y destino.
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000.00", frequency="daily",
            from_kind="checking", to_kind="checking", now=_NOW)
    assert exc.value.code == "INVALID_DESTINATION"
    # Destino desconocido.
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="internal", amount_raw="1000.00", frequency="daily",
            from_kind="checking", to_kind="brokerage", now=_NOW)
    assert exc.value.code == "INVALID_DESTINATION"


def test_ach_sin_beneficiario_rechazado(conn):
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="ach", amount_raw="1000.00", frequency="daily",
            from_kind="checking", now=_NOW)
    assert exc.value.code == "INVALID_BENEFICIARY"


def test_ach_beneficiario_adhoc_formato_invalido_rechazado(conn):
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.create_schedule(
            conn, type="ach", amount_raw="1000.00", frequency="daily", from_kind="checking",
            adhoc={**_VALID_BEN, "routing_number": "123"}, now=_NOW)
    assert exc.value.code == "INVALID_ROUTING"


# --- Ciclo de vida: pausar / reanudar / cancelar (Tarea 29, Req. 9, REC-06/07/08, D06, A18) ---
#
# Reloj determinista (ManualClock) para verificar que la reanudación recalcula `next_run_at`
# desde el instante de reanudación (sin catch-up) y que las transiciones ilegales se rechazan
# con `INVALID_STATE_TRANSITION` sin mutar el estado ni mover saldos.


def _crear_active(conn, *, frequency="daily", now=_NOW):
    """Helper: crea un schedule interno no sensible en estado `active` y devuelve su id."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency=frequency,
        from_kind="checking", to_kind="savings", now=now)
    return res.id


def test_pausar_schedule_active(conn):
    """Req. 9.1 (REC-06): active → paused."""
    sid = _crear_active(conn)
    res = recurring_service.pause_schedule(conn, sid)
    assert res.status == "paused"
    assert repository.get_schedule(conn, sid).status == "paused"


def test_pausar_no_mueve_saldos(conn):
    sid = _crear_active(conn)
    before = _balances(conn)
    recurring_service.pause_schedule(conn, sid)
    assert _balances(conn) == before


def test_reanudar_recalcula_next_run_desde_reanudacion_sin_catch_up(conn):
    """Req. 9.2/9.6 (D06, A18): reanudar salta ocurrencias perdidas y recalcula desde la reanudación."""
    clock = ManualClock(_NOW)
    sid = _crear_active(conn, frequency="weekly", now=clock.now_utc())
    original_next = repository.get_schedule(conn, sid).next_run_at
    assert parse_iso(original_next) == _NOW + timedelta(days=7)

    recurring_service.pause_schedule(conn, sid)

    # Avanza el reloj MUCHO más allá de varias ocurrencias perdidas durante la pausa.
    clock.advance(days=30)
    resume_instant = clock.now_utc()
    before = _balances(conn)
    res = recurring_service.resume_schedule(conn, sid, now=resume_instant)

    assert res.status == "active"
    # next_run_at = reanudación + UN intervalo completo (no acumula las semanas perdidas).
    assert parse_iso(res.next_run_at) == resume_instant + timedelta(days=7)
    stored = repository.get_schedule(conn, sid)
    assert stored.status == "active"
    assert parse_iso(stored.next_run_at) == resume_instant + timedelta(days=7)
    # Sin débitos acumulados: reanudar no mueve saldos.
    assert _balances(conn) == before


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_reanudar_usa_el_intervalo_configurado(conn, frequency, days):
    clock = ManualClock(_NOW)
    sid = _crear_active(conn, frequency=frequency, now=clock.now_utc())
    recurring_service.pause_schedule(conn, sid)
    clock.advance(days=100)
    resume_instant = clock.now_utc()
    res = recurring_service.resume_schedule(conn, sid, now=resume_instant)
    assert parse_iso(res.next_run_at) == resume_instant + timedelta(days=days)


def test_cancelar_es_terminal(conn):
    """Req. 9.3/9.7 (REC-06/07): cancelar deja el schedule en estado terminal `cancelled`."""
    sid = _crear_active(conn)
    res = recurring_service.cancel_schedule(conn, sid)
    assert res.status == "cancelled"
    assert repository.get_schedule(conn, sid).status == "cancelled"


def test_cancelar_schedule_pausado(conn):
    """Se puede cancelar desde `paused` (ambas ramas del diagrama de ciclo de vida)."""
    sid = _crear_active(conn)
    recurring_service.pause_schedule(conn, sid)
    res = recurring_service.cancel_schedule(conn, sid)
    assert res.status == "cancelled"


def test_reanudar_cancelled_rechazado_sin_mutar(conn):
    """Req. 9.4/9.7 (REC-07/08): reanudar un `cancelled` se rechaza y la cancelación no se revierte."""
    sid = _crear_active(conn)
    recurring_service.cancel_schedule(conn, sid)
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.resume_schedule(conn, sid, now=_NOW)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    assert repository.get_schedule(conn, sid).status == "cancelled"  # estado intacto


def test_pausar_cancelled_rechazado_sin_mutar(conn):
    """Pausar un `cancelled` es una transición ilegal (terminal)."""
    sid = _crear_active(conn)
    recurring_service.cancel_schedule(conn, sid)
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.pause_schedule(conn, sid)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    assert repository.get_schedule(conn, sid).status == "cancelled"


def test_cancelar_cancelled_rechazado(conn):
    """Cancelar dos veces: la segunda es ilegal (ya terminal)."""
    sid = _crear_active(conn)
    recurring_service.cancel_schedule(conn, sid)
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.cancel_schedule(conn, sid)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_pausar_ya_pausado_rechazado(conn):
    sid = _crear_active(conn)
    recurring_service.pause_schedule(conn, sid)
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.pause_schedule(conn, sid)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_reanudar_active_rechazado(conn):
    """Reanudar un schedule que ya está `active` es ilegal."""
    sid = _crear_active(conn)
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.resume_schedule(conn, sid, now=_NOW)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_ciclo_de_vida_schedule_inexistente_not_found(conn):
    """La propiedad/existencia se exige igual que en el resto del servicio (NOT_FOUND)."""
    for fn in (recurring_service.pause_schedule, recurring_service.cancel_schedule):
        with pytest.raises(recurring_service.RecurringError) as exc:
            fn(conn, "no-existe")
        assert exc.value.code == "NOT_FOUND"
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.resume_schedule(conn, "no-existe", now=_NOW)
    assert exc.value.code == "NOT_FOUND"
