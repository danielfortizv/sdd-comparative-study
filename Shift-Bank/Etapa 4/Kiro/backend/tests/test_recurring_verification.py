"""Verificación determinista de pagos recurrentes con reloj inyectable (Tarea 34).

Suite de **verificación** (no implementación) que mapea de forma explícita cada escenario de
aceptación A15–A19 y la decisión D06 al comportamiento observable del servicio recurrente, usando
el reloj inyectable `ManualClock` (clock.py) y `now` explícito: ejecución determinista sin espera
real (Req. 10.5, DD-3).

Mapa de cobertura (escenario de aceptación → prueba):

  - A15 — diario sin fecha de inicio corre tras UN día (nunca inmediato):
      `test_A15_diario_sin_fecha_corre_tras_un_dia`
  - A16 — semanal/mensual = +7/+30 días (REC-02):
      `test_A16_frecuencia_semanal_mensual_7_30_dias`
  - A17 — internos y ACH ejecutan al vencer y actualizan saldo/movimientos/próxima fecha:
      `test_A17_interno_ejecuta_actualiza_saldo_movimiento_fecha`,
      `test_A17_ach_ejecuta_pending_debito_inmediato`
  - A18 — pausado no corre; reanudado elegible; cancelado terminal:
      `test_A18_pausado_no_corre`, `test_A18_reanudado_vuelve_elegible_y_ejecuta`,
      `test_A18_cancelado_es_terminal_no_reanudable_ni_ejecutable`
  - A19 — fallo por fondos/límite registra `failed` y avanza SIN débito (no se atasca):
      `test_A19_fondos_insuficientes_registra_failed_y_avanza_sin_debito`,
      `test_A19_limite_excedido_registra_failed_y_avanza_sin_debito`
  - Exactamente-una-vez (DD-7, D07, ACH-08) ante doble tick / reintento / crash simulado:
      `test_exactamente_una_vez_doble_tick_del_scheduler`,
      `test_exactamente_una_vez_insert_duplicado_viola_unique`,
      `test_exactamente_una_vez_reintento_tras_crash_simulado`
  - D06 — reanudar sin catch-up (recalcula desde la reanudación, salta ocurrencias perdidas):
      `test_D06_reanudar_sin_catch_up_recalcula_desde_reanudacion`,
      `test_D06_reanudar_no_ejecuta_ocurrencias_perdidas`

Estas pruebas complementan a `test_recurring.py` (creación/MFA/ciclo de vida) y
`test_recurring_execution.py` (ejecución durable) consolidando la trazabilidad A15–A19/D06 y
añadiendo la verificación DIRECTA de la guarda `UNIQUE(schedule_id, due_at)` (INSERT duplicado
lanza `IntegrityError`) y del doble tick del scheduler, no cubiertas de forma explícita antes.

_Requisitos: 8, 9, 10, 11_ · _Contrato: REC-01..12; A15–A19_ · _Diseño: DD-7, D06_
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.db as db
import app.recurring_service as recurring_service
import app.repository as repository
import app.scheduler as scheduler
from app.clock import ManualClock, iso, parse_iso

_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Instante base determinista para todas las pruebas de esta suite.
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(app_client, isolated_db_path):
    """Conexión directa a la DB aislada ya migrada y sembrada (vía arranque de `app_client`)."""
    c = db.get_connection(isolated_db_path)
    try:
        yield c
    finally:
        c.close()


# --- Helpers -------------------------------------------------------------------

def _balances(conn):
    rows = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
    return {r["kind"]: r["balance_cents"] for r in rows}


def _executions(conn, schedule_id):
    return conn.execute(
        "SELECT * FROM schedule_execution WHERE schedule_id = ? ORDER BY created_at, due_at",
        (schedule_id,),
    ).fetchall()


def _force_due(conn, schedule_id, due_at_iso):
    """Fuerza el `next_run_at` de un schedule a un vencimiento concreto (ocurrencia vencida)."""
    conn.execute(
        "UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due_at_iso, schedule_id))
    conn.commit()


def _create_internal(conn, *, amount_raw="100000.00", frequency="daily", now):
    return recurring_service.create_schedule(
        conn, type="internal", amount_raw=amount_raw, frequency=frequency,
        from_kind="checking", to_kind="savings", description="ahorro", now=now)


# =============================================================================
# A15 — Primera ejecución tras UN intervalo cuando se omite la fecha de inicio
# =============================================================================

def test_A15_diario_sin_fecha_corre_tras_un_dia(conn):
    """A15 (Req. 8.5, REC-04): sin fecha de inicio, un schedule diario vence tras 1 día exacto.

    La primera ejecución NUNCA es inmediata en la creación: `next_run_at = now + 1 día`. Además,
    en el instante de creación el schedule no es elegible (`process_due` no lo toca).
    """
    clock = ManualClock(_NOW)
    res = _create_internal(conn, frequency="daily", now=clock.now_utc())

    assert parse_iso(res.next_run_at) == _NOW + timedelta(days=1)
    assert parse_iso(res.next_run_at) > _NOW  # nunca inmediata

    # En la creación no vence: nada se ejecuta (determinista dado `now`).
    before = _balances(conn)
    summary = recurring_service.process_due(conn, _NOW)
    assert summary.executed == 0 and summary.outcomes == []
    assert _balances(conn) == before

    # Al avanzar exactamente un día, la ocurrencia ya es elegible y ejecuta.
    clock.advance(days=1)
    summary = recurring_service.process_due(conn, clock.now_utc())
    assert summary.executed == 1


# =============================================================================
# A16 — Frecuencia: diaria/semanal/mensual = +1/+7/+30 días (REC-02)
# =============================================================================

@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_A16_frecuencia_semanal_mensual_7_30_dias(conn, frequency, days):
    """A16 (Req. 8.2, REC-02): la primera fecha omitida se fija a +1/+7/+30 días según frecuencia."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="1000.00", frequency=frequency,
        from_kind="checking", to_kind="savings", start_at=None, now=_NOW)
    assert parse_iso(res.next_run_at) == _NOW + timedelta(days=days)


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_A16_siguiente_fecha_avanza_por_intervalo(conn, frequency, days):
    """A16 (Req. 10.4): tras ejecutar una ocurrencia, `next_run_at` avanza el intervalo correcto."""
    res = _create_internal(conn, frequency=frequency, now=_NOW - timedelta(days=days))
    due = iso(_NOW)
    _force_due(conn, res.id, due)

    recurring_service.process_due(conn, _NOW)

    stored = repository.get_schedule(conn, res.id)
    assert parse_iso(stored.next_run_at) == parse_iso(due) + timedelta(days=days)


# =============================================================================
# A17 — Ejecución al vencer: interno y ACH actualizan saldo/movimientos/fecha
# =============================================================================

def test_A17_interno_ejecuta_actualiza_saldo_movimiento_fecha(conn):
    """A17 (Req. 10.4, REC-05): interno vencido mueve saldo, crea movimiento COMPLETED y avanza."""
    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.executed == 1 and summary.failed == 0 and summary.skipped == 0
    # Saldo: débito en checking, crédito en savings (movimiento interno).
    after = _balances(conn)
    assert after["checking"] == before["checking"] - 10_000_000
    assert after["savings"] == before["savings"] + 10_000_000

    # Movimiento interno COMPLETED ligado al schedule.
    rows = conn.execute(
        "SELECT status, type, schedule_id FROM transfer WHERE schedule_id = ?",
        (res.id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "COMPLETED" and rows[0]["type"] == "internal"

    # Ejecución registrada executed + transfer_id; próxima fecha +1 día desde el vencimiento.
    execs = _executions(conn, res.id)
    assert len(execs) == 1 and execs[0]["outcome"] == "executed"
    assert execs[0]["due_at"] == due and execs[0]["transfer_id"] is not None
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=1)


def test_A17_ach_ejecuta_pending_debito_inmediato(conn):
    """A17 + Req. 11.3: ACH recurrente aplica el ciclo ACH (`pending` con débito inmediato)."""
    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="50000.00", frequency="monthly",
        from_kind="savings", adhoc=_VALID_BEN, description="renta",
        now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.executed == 1
    after = _balances(conn)
    assert after["savings"] == before["savings"] - 5_000_000  # débito inmediato
    assert after["checking"] == before["checking"]            # ACH no abona interno

    row = conn.execute(
        "SELECT status, type FROM transfer WHERE schedule_id = ?", (res.id,)).fetchone()
    assert row["status"] == "pending" and row["type"] == "ach"

    # Próxima fecha +30 días (mensual) desde el vencimiento.
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=30)


# =============================================================================
# A18 — Ciclo de vida: pausado no corre, reanudado elegible, cancelado terminal
# =============================================================================

def test_A18_pausado_no_corre(conn):
    """A18 (Req. 9.1/9.5, REC-08): un `paused` nunca ejecuta, aun con `next_run_at` vencido."""
    res = _create_internal(conn, now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    recurring_service.pause_schedule(conn, res.id)
    _force_due(conn, res.id, due)  # vencido, pero pausado
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.executed == 0 and summary.outcomes == []
    assert _balances(conn) == before
    assert _executions(conn, res.id) == []


def test_A18_reanudado_vuelve_elegible_y_ejecuta(conn):
    """A18 (Req. 9.2): reanudar devuelve el schedule a `active` y lo hace elegible de nuevo."""
    clock = ManualClock(_NOW)
    res = _create_internal(conn, frequency="daily", now=clock.now_utc())
    recurring_service.pause_schedule(conn, res.id)

    # Reanudar en un instante posterior: next_run_at = reanudación + 1 día (D06, sin catch-up).
    clock.advance(days=3)
    resume_instant = clock.now_utc()
    lifecycle = recurring_service.resume_schedule(conn, res.id, now=resume_instant)
    assert lifecycle.status == "active"
    assert parse_iso(lifecycle.next_run_at) == resume_instant + timedelta(days=1)

    # Al alcanzar la nueva fecha, la ocurrencia ejecuta: el schedule está realmente elegible.
    clock.set(parse_iso(lifecycle.next_run_at))
    summary = recurring_service.process_due(conn, clock.now_utc())
    assert summary.executed == 1


def test_A18_cancelado_es_terminal_no_reanudable_ni_ejecutable(conn):
    """A18 (Req. 9.3/9.5/9.7, REC-07): `cancelled` es terminal: no ejecuta ni admite reanudar."""
    res = _create_internal(conn, now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    recurring_service.cancel_schedule(conn, res.id)
    _force_due(conn, res.id, due)  # vencido, pero cancelado
    before = _balances(conn)

    # No ejecuta aun estando vencido.
    summary = recurring_service.process_due(conn, _NOW)
    assert summary.outcomes == []
    assert _balances(conn) == before

    # No reanudable (terminal): la transición se rechaza sin mutar el estado.
    with pytest.raises(recurring_service.RecurringError) as exc:
        recurring_service.resume_schedule(conn, res.id, now=_NOW)
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    assert repository.get_schedule(conn, res.id).status == "cancelled"


# =============================================================================
# A19 — Fallo de negocio: registra `failed`, avanza y NO debita (no se atasca)
# =============================================================================

def test_A19_fondos_insuficientes_registra_failed_y_avanza_sin_debito(conn):
    """A19 (Req. 11.2, REC-10): fondos insuficientes → `failed` sin débito, `next_run_at` avanza."""
    res = _create_internal(conn, frequency="weekly", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    # Dejar la cuenta de origen con menos que el monto del schedule (10.000.000 centavos).
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (5_000_000,))
    conn.commit()
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.failed == 1 and summary.executed == 0 and summary.skipped == 0
    assert summary.outcomes[0].status == "failed"
    assert summary.outcomes[0].transfer_id is None
    assert _balances(conn) == before  # SIN débito parcial

    # Sin movimiento financiero; ejecución registrada failed sin transfer_id; fecha avanzada.
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM transfer WHERE schedule_id = ?",
        (res.id,)).fetchone()["n"] == 0
    execs = _executions(conn, res.id)
    assert len(execs) == 1
    assert execs[0]["outcome"] == "failed" and execs[0]["transfer_id"] is None
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=7)


def test_A19_limite_excedido_registra_failed_y_avanza_sin_debito(conn):
    """A19 (Req. 11.2, LIM-08, REC-10): exceder el límite por transferencia → `failed` sin débito."""
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    conn.execute(
        "UPDATE transfer_limit SET per_transfer_cents = ? WHERE customer_id = ?",
        (1_000, cid))  # 10.00: por debajo del monto del schedule (100.000)
    conn.commit()

    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.failed == 1 and summary.executed == 0
    assert _balances(conn) == before
    execs = _executions(conn, res.id)
    assert len(execs) == 1 and execs[0]["outcome"] == "failed"
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=1)


def test_A19_no_queda_atascado_siguiente_ocurrencia_ejecuta(conn):
    """A19: tras un fallo que avanza la fecha, la ocurrencia siguiente ejecuta con fondos.

    Verifica el núcleo de REC-10 end-to-end: el schedule NO se atasca en la ocurrencia fallida ni
    la reintenta; la siguiente ocurrencia (nuevo `due_at`) ejecuta exactamente una vez.
    """
    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due1 = iso(_NOW)
    _force_due(conn, res.id, due1)
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (5_000_000,))
    conn.commit()

    # Primera corrida: falla por fondos, sin débito, avanza al día siguiente.
    s1 = recurring_service.process_due(conn, _NOW)
    assert s1.failed == 1 and s1.executed == 0
    due2 = repository.get_schedule(conn, res.id).next_run_at
    assert parse_iso(due2) == parse_iso(due1) + timedelta(days=1)
    assert _balances(conn)["checking"] == 5_000_000  # intacto

    # Restaurar fondos y correr en el nuevo vencimiento: ejecuta con éxito.
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (20_000_000,))
    conn.commit()
    s2 = recurring_service.process_due(conn, parse_iso(due2))
    assert s2.executed == 1 and s2.failed == 0 and s2.skipped == 0

    outcomes = {e["due_at"]: e["outcome"] for e in _executions(conn, res.id)}
    assert outcomes == {due1: "failed", due2: "executed"}


# =============================================================================
# Exactamente-una-vez (DD-7, D07, ACH-08): doble tick / INSERT duplicado / crash
# =============================================================================

def test_exactamente_una_vez_doble_tick_del_scheduler(conn):
    """DD-7/D07: dos ticks del scheduler para el MISMO vencimiento ⇒ UN solo efecto.

    Usa `scheduler.run_tick(conn, now)` (el núcleo determinista del worker) dos veces en el mismo
    instante. El primer tick ejecuta; el segundo ya no vence (la fecha avanzó), de modo que no
    repite. Simula dos "despertares" del scheduler.
    """
    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    _force_due(conn, res.id, iso(_NOW))
    before = _balances(conn)

    first = scheduler.run_tick(conn, _NOW)
    assert first.executed == 1
    after_first = _balances(conn)
    assert after_first["checking"] == before["checking"] - 10_000_000

    # Segundo tick en el mismo `now`: la ocurrencia ya no vence (next_run_at avanzó) ⇒ sin efecto.
    second = scheduler.run_tick(conn, _NOW)
    assert second.executed == 0 and second.skipped == 0
    assert _balances(conn) == after_first
    assert len(_executions(conn, res.id)) == 1  # una sola fila de ejecución


def test_exactamente_una_vez_doble_tick_reencolado_mismo_due(conn):
    """DD-7/D07: si el mismo vencimiento se reencola (reintento), el 2.º tick se OMITE (UNIQUE).

    Tras ejecutar, restauramos `next_run_at` al vencimiento ORIGINAL (modela un tick solapado que
    vuelve a ver la misma ocurrencia vencida): el 2.º `process_due` choca con la UNIQUE y se marca
    `skipped`, sin repetir el efecto financiero.
    """
    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    before = _balances(conn)

    s1 = recurring_service.process_due(conn, _NOW)
    assert s1.executed == 1
    after_first = _balances(conn)

    _force_due(conn, res.id, due)  # reencolar la MISMA ocurrencia (due_at idéntico)
    s2 = recurring_service.process_due(conn, _NOW)

    assert s2.executed == 0 and s2.skipped == 1
    assert _balances(conn) == after_first          # sin doble efecto
    assert len(_executions(conn, res.id)) == 1     # una sola fila de ejecución


def test_exactamente_una_vez_insert_duplicado_viola_unique(conn):
    """DD-7: INSERT duplicado en `schedule_execution(schedule_id, due_at)` lanza IntegrityError.

    Verificación DIRECTA del mecanismo de idempotencia durable: la `UNIQUE(schedule_id, due_at)`
    rechaza a nivel de base de datos un segundo registro de la MISMA ocurrencia, que es lo que
    hace exactamente-una-vez robusto ante reintento/tick solapado/re-ejecución tras crash.
    """
    import sqlite3

    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due = iso(_NOW)

    repository.insert_schedule_execution_no_commit(
        conn, execution_id="exec-1", schedule_id=res.id, due_at=due,
        outcome="executed", transfer_id=None, created_at=iso(_NOW))

    # Segundo INSERT con la MISMA identidad (schedule_id, due_at) y un id distinto: debe fallar.
    with pytest.raises(sqlite3.IntegrityError):
        repository.insert_schedule_execution_no_commit(
            conn, execution_id="exec-2", schedule_id=res.id, due_at=due,
            outcome="executed", transfer_id=None, created_at=iso(_NOW))

    conn.rollback()  # deshacer la transacción fallida para no dejar la conexión a medias


def test_exactamente_una_vez_reintento_tras_crash_simulado(conn, monkeypatch):
    """DD-7/F10: crash ANTES del COMMIT ⇒ ROLLBACK total; el reintento ejecuta UNA sola vez.

    Simula un crash haciendo fallar la creación del movimiento tras insertar la fila de ejecución
    (dentro de la misma transacción): el context manager revierte TODO. El siguiente tick, ya sin
    el fallo, ejecuta la ocurrencia exactamente una vez.
    """
    res = _create_internal(conn, frequency="daily", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    _force_due(conn, res.id, due)
    before = _balances(conn)

    calls = {"n": 0}
    original = recurring_service._execute_internal_in_tx

    def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("crash simulado antes del COMMIT")
        return original(*args, **kwargs)

    monkeypatch.setattr(recurring_service, "_execute_internal_in_tx", _flaky)

    # Primer intento: crash ⇒ ROLLBACK total (sin fila de ejecución, sin débito, fecha intacta).
    with pytest.raises(RuntimeError):
        recurring_service.process_due(conn, _NOW)
    assert _executions(conn, res.id) == []
    assert _balances(conn) == before
    assert repository.get_schedule(conn, res.id).next_run_at == due

    # Reintento (mismo vencimiento aún vigente): ejecuta exactamente una vez.
    summary = recurring_service.process_due(conn, _NOW)
    assert summary.executed == 1
    assert _balances(conn)["checking"] == before["checking"] - 10_000_000
    assert len(_executions(conn, res.id)) == 1


# =============================================================================
# D06 — Reanudar sin catch-up: recalcula desde la reanudación, salta lo perdido
# =============================================================================

def test_D06_reanudar_sin_catch_up_recalcula_desde_reanudacion(conn):
    """D06 (Req. 9.6): reanudar recalcula `next_run_at` = reanudación + intervalo, no acumula.

    Aunque pasen varias ocurrencias durante una pausa larga, la reanudación fija UNA sola próxima
    fecha (reanudación + un intervalo), sin pagos duplicados ni débitos acumulados.
    """
    clock = ManualClock(_NOW)
    res = _create_internal(conn, frequency="weekly", now=clock.now_utc())
    assert parse_iso(res.next_run_at) == _NOW + timedelta(days=7)

    recurring_service.pause_schedule(conn, res.id)

    # Pausa larga: avanzan ~4 ocurrencias semanales perdidas.
    clock.advance(days=30)
    resume_instant = clock.now_utc()
    before = _balances(conn)
    lifecycle = recurring_service.resume_schedule(conn, res.id, now=resume_instant)

    assert lifecycle.status == "active"
    # Una sola próxima fecha: reanudación + 7 días (no acumula las semanas perdidas).
    assert parse_iso(lifecycle.next_run_at) == resume_instant + timedelta(days=7)
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        resume_instant + timedelta(days=7)
    # Reanudar no mueve saldos (sin débitos acumulados).
    assert _balances(conn) == before


def test_D06_reanudar_no_ejecuta_ocurrencias_perdidas(conn):
    """D06: al reanudar y correr `process_due`, SOLO ejecuta una ocurrencia (la recalculada).

    Verifica el efecto observable de "sin catch-up": las ocurrencias cuyo vencimiento cayó durante
    la pausa no se ejecutan retroactivamente (su `due_at` no se genera). Tras reanudar y alcanzar
    la nueva fecha, se ejecuta exactamente una vez.
    """
    clock = ManualClock(_NOW)
    res = _create_internal(conn, frequency="daily", now=clock.now_utc())
    recurring_service.pause_schedule(conn, res.id)

    # Pausa de 10 días (10 ocurrencias diarias perdidas) y reanudación.
    clock.advance(days=10)
    resume_instant = clock.now_utc()
    lifecycle = recurring_service.resume_schedule(conn, res.id, now=resume_instant)
    new_due = parse_iso(lifecycle.next_run_at)
    assert new_due == resume_instant + timedelta(days=1)

    # Correr en el nuevo vencimiento: exactamente UNA ocurrencia (no 10 retroactivas).
    before = _balances(conn)
    summary = recurring_service.process_due(conn, new_due)
    assert summary.executed == 1
    assert _balances(conn)["checking"] == before["checking"] - 10_000_000
    assert len(_executions(conn, res.id)) == 1

    # La única fila de ejecución corresponde a la ocurrencia recalculada, no a una pasada.
    execs = _executions(conn, res.id)
    assert execs[0]["due_at"] == iso(new_due)
