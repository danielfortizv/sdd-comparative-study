"""Pruebas de ejecución durable y atómica de ocurrencias recurrentes (Fase E, Tarea 30).

Cubren el alcance de la Tarea 30 (`recurring_service.process_due`): camino de éxito interno y
ACH, durabilidad/atomicidad e idempotencia durable; y el mínimo del fallo de negocio necesario
para la corrección (sin débito en el camino fallido; el registro completo `outcome='failed'`
pertenece a la Tarea 31, pero aquí se verifica que NO hay movimiento de dinero ni fila de
ejecución `executed`).

Garantías verificadas:
- Ocurrencia interna y ACH ejecutan al vencer: saldo actualizado, fila de movimiento creada,
  `schedule_execution` con `outcome='executed'`, `next_run_at` avanzado por el intervalo (A17).
- Idempotencia durable: llamar `process_due` dos veces para el mismo vencimiento produce UN
  solo efecto financiero y UNA sola fila de ejecución (el segundo INSERT choca con la UNIQUE y
  se omite). Se modela el "reinicio" invocando de nuevo `process_due`.
- Rollback atómico: si el movimiento falla tras el INSERT de la fila de ejecución pero antes del
  COMMIT, se revierte todo (sin fila de ejecución, sin cambio de saldo, `next_run_at` intacto).
- Nunca ejecuta schedules `paused`/`cancelled` ni sensibles no autorizados.
- Fondos/límite insuficientes al ejecutar: no hay débito parcial (REC-10, Req. 11.2).
- Verificación de reintento tras "crash" (dos llamadas secuenciales): la UNIQUE cubre el
  contrato de durabilidad sin necesitar dos conexiones concurrentes reales.

Reloj inyectable (`ManualClock`) y `now` explícito: ejecución determinista sin espera real.

_Requisitos: 10.3, 10.4, 11.1, 11.3_ · _Contrato: REC-05, ACH-08; A17, A19_ · _Diseño: DD-7, F10_
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.ach_repository as ach_repo
import app.db as db
import app.recurring_service as recurring_service
import app.repository as repository
from app.clock import ManualClock, iso, parse_iso

_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Instante base determinista.
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn(app_client, isolated_db_path):
    c = db.get_connection(isolated_db_path)
    try:
        yield c
    finally:
        c.close()


def _balances(conn):
    rows = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
    return {r["kind"]: r["balance_cents"] for r in rows}


def _executions(conn, schedule_id):
    return conn.execute(
        "SELECT * FROM schedule_execution WHERE schedule_id = ? ORDER BY created_at",
        (schedule_id,),
    ).fetchall()


def _make_internal_due(conn, *, frequency="daily", created_now):
    """Crea un schedule interno con `next_run_at` ya vencido respecto a la base de pruebas."""
    # Fecha de inicio: un instante pasado para que esté vencido en _NOW.
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency=frequency,
        from_kind="checking", to_kind="savings", description="ahorro",
        now=created_now)
    # Forzar un vencimiento en el pasado (equivalente a una ocurrencia ya debida).
    due = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    conn.commit()
    return res.id, due


# --- Éxito interno (A17) -------------------------------------------------------

def test_internal_ocurrencia_ejecuta_al_vencer(conn):
    """A17/REC-05: interno vencido ejecuta, mueve saldo, registra ejecución y avanza la fecha."""
    sid, due = _make_internal_due(conn, frequency="daily", created_now=_NOW - timedelta(days=1))
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.executed == 1 and summary.failed == 0 and summary.skipped == 0
    after = _balances(conn)
    assert after["checking"] == before["checking"] - 10_000_000
    assert after["savings"] == before["savings"] + 10_000_000

    # Fila de movimiento interna COMPLETED ligada al schedule.
    rows = conn.execute(
        "SELECT status, type, schedule_id FROM transfer WHERE schedule_id = ?", (sid,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "COMPLETED" and rows[0]["type"] == "internal"

    # Ejecución registrada con outcome='executed' y transfer_id poblado.
    execs = _executions(conn, sid)
    assert len(execs) == 1
    assert execs[0]["outcome"] == "executed"
    assert execs[0]["due_at"] == due
    assert execs[0]["transfer_id"] is not None

    # next_run_at avanzado UN intervalo desde el vencimiento (no desde `now`).
    stored = repository.get_schedule(conn, sid)
    assert parse_iso(stored.next_run_at) == parse_iso(due) + timedelta(days=1)


@pytest.mark.parametrize("frequency,days", [("daily", 1), ("weekly", 7), ("monthly", 30)])
def test_internal_avanza_por_intervalo(conn, frequency, days):
    sid, due = _make_internal_due(
        conn, frequency=frequency, created_now=_NOW - timedelta(days=1))
    recurring_service.process_due(conn, _NOW)
    stored = repository.get_schedule(conn, sid)
    assert parse_iso(stored.next_run_at) == parse_iso(due) + timedelta(days=days)


# --- Éxito ACH (A17, Req. 11.3) ------------------------------------------------

def test_ach_ocurrencia_ejecuta_pending_con_debito(conn):
    """Req. 11.3: ACH recurrente aplica el ciclo ACH (`pending` + débito inmediato)."""
    res = recurring_service.create_schedule(
        conn, type="ach", amount_raw="50000.00", frequency="monthly",
        from_kind="savings", adhoc=_VALID_BEN, description="renta",
        now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    conn.commit()
    before = _balances(conn)

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.executed == 1
    after = _balances(conn)
    assert after["savings"] == before["savings"] - 5_000_000  # débito inmediato
    assert after["checking"] == before["checking"]            # ACH no abona interno

    row = conn.execute(
        "SELECT status, type FROM transfer WHERE schedule_id = ?", (res.id,)).fetchone()
    assert row["status"] == "pending" and row["type"] == "ach"

    execs = _executions(conn, res.id)
    assert len(execs) == 1 and execs[0]["outcome"] == "executed"


# --- Idempotencia durable (ACH-08, D07) ----------------------------------------

def test_idempotencia_doble_process_due(conn):
    """Doble corrida para el mismo vencimiento: UN efecto, UNA fila de ejecución (UNIQUE)."""
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    before = _balances(conn)

    s1 = recurring_service.process_due(conn, _NOW)
    after_first = _balances(conn)
    # Segundo "tick" para EL MISMO vencimiento (simula reintento): restauramos la fecha.
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, sid))
    conn.commit()
    s2 = recurring_service.process_due(conn, _NOW)

    assert s1.executed == 1
    assert s2.executed == 0 and s2.skipped == 1    # segundo INSERT choca con la UNIQUE
    # Un solo efecto financiero.
    assert after_first["checking"] == before["checking"] - 10_000_000
    assert _balances(conn) == after_first          # el segundo no vuelve a mover
    assert len(_executions(conn, sid)) == 1        # una sola fila de ejecución


def test_idempotencia_reinicio_simulado(conn):
    """Modelado de 'reinicio': tras ejecutar y COMMIT, re-invocar no repite (UNIQUE durable)."""
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    recurring_service.process_due(conn, _NOW)
    stored = repository.get_schedule(conn, sid)
    advanced = stored.next_run_at

    # "Reinicio": una nueva conexión a la MISMA DB persistida, re-procesando el mismo instante.
    # La fecha ya avanzó, así que esa ocurrencia ni siquiera reentra; pero si forzamos la
    # reentrada con la fecha original, la UNIQUE la rechaza.
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, sid))
    conn.commit()
    balances_before_retry = _balances(conn)
    s = recurring_service.process_due(conn, _NOW)
    assert s.skipped == 1 and s.executed == 0
    assert _balances(conn) == balances_before_retry
    assert len(_executions(conn, sid)) == 1
    # La fecha sigue siendo la original (no se volvió a avanzar).
    assert repository.get_schedule(conn, sid).next_run_at == due
    assert advanced != due  # sanity: la primera corrida sí avanzó


# --- Rollback atómico (Req. 10.3, F10) -----------------------------------------

def test_rollback_atomico_si_falla_el_movimiento(conn, monkeypatch):
    """Fallo tras el INSERT de la ejecución y antes del COMMIT → ROLLBACK total."""
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    before = _balances(conn)

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado del movimiento (crash antes de COMMIT)")

    monkeypatch.setattr(recurring_service, "_execute_internal_in_tx", _boom)

    with pytest.raises(RuntimeError):
        recurring_service.process_due(conn, _NOW)

    # ROLLBACK total: sin fila de ejecución, sin cambio de saldo, next_run_at intacto.
    assert _executions(conn, sid) == []
    assert _balances(conn) == before
    assert repository.get_schedule(conn, sid).next_run_at == due


def test_rollback_reintentable_tras_crash(conn, monkeypatch):
    """Tras un 'crash' con ROLLBACK, el siguiente tick ejecuta limpiamente (exactamente una vez)."""
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    before = _balances(conn)

    calls = {"n": 0}
    original = recurring_service._execute_internal_in_tx

    def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("crash en el primer intento")
        return original(*args, **kwargs)

    monkeypatch.setattr(recurring_service, "_execute_internal_in_tx", _flaky)

    with pytest.raises(RuntimeError):
        recurring_service.process_due(conn, _NOW)
    assert _executions(conn, sid) == []            # nada persistido en el crash

    # Siguiente tick (misma fecha vencida): ahora ejecuta exactamente una vez.
    s = recurring_service.process_due(conn, _NOW)
    assert s.executed == 1
    assert _balances(conn)["checking"] == before["checking"] - 10_000_000
    assert len(_executions(conn, sid)) == 1


# --- Nunca ejecuta paused/cancelled/no-autorizado ------------------------------

def test_no_ejecuta_paused(conn):
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    recurring_service.pause_schedule(conn, sid)
    # pause_schedule no recalcula next_run_at: sigue vencido, pero no es `active`.
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, sid))
    conn.commit()
    before = _balances(conn)
    s = recurring_service.process_due(conn, _NOW)
    assert s.executed == 0 and s.outcomes == []
    assert _balances(conn) == before
    assert _executions(conn, sid) == []


def test_no_ejecuta_cancelled(conn):
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    recurring_service.cancel_schedule(conn, sid)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, sid))
    conn.commit()
    before = _balances(conn)
    s = recurring_service.process_due(conn, _NOW)
    assert s.executed == 0 and s.outcomes == []
    assert _balances(conn) == before


def test_no_ejecuta_sensible_no_autorizado(conn):
    """Un schedule `active` pero `authorized=0` (sensible sin MFA) nunca debe ejecutarse."""
    # Creamos uno no sensible y degradamos authorized a 0 para simular el estado prohibido.
    sid, due = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))
    conn.execute("UPDATE recurring_schedule SET authorized = 0 WHERE id = ?", (sid,))
    conn.commit()
    before = _balances(conn)
    s = recurring_service.process_due(conn, _NOW)
    assert s.outcomes == []
    assert _balances(conn) == before
    assert _executions(conn, sid) == []


# --- Fallo de negocio: sin débito parcial (Req. 11.2, REC-10, A19) -------------

def test_fondos_insuficientes_no_debita(conn):
    """Fondos insuficientes al ejecutar: NO hay débito; se registra failed y avanza la fecha."""
    # Schedule de monto modesto (no sensible) y luego se drena la cuenta de origen por debajo
    # del monto, de modo que la revalidación falle en el instante de ejecución.
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    # Dejar la cuenta de origen con menos que el monto del schedule (10.000.000 centavos).
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (5_000_000,))
    conn.commit()
    before = _balances(conn)

    s = recurring_service.process_due(conn, _NOW)

    assert s.failed == 1 and s.executed == 0
    assert _balances(conn) == before                       # SIN débito parcial
    # Sin movimiento financiero creado.
    assert conn.execute(
        "SELECT COUNT(*) AS n FROM transfer WHERE schedule_id = ?", (res.id,)).fetchone()["n"] == 0
    # Fila de ejecución registrada como failed, sin transfer_id, fecha avanzada (no atascado).
    execs = _executions(conn, res.id)
    assert len(execs) == 1 and execs[0]["outcome"] == "failed" and execs[0]["transfer_id"] is None
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=1)


def test_limite_excedido_no_debita(conn):
    """Límite por transferencia excedido al ejecutar: NO hay débito (REC-10)."""
    # Bajar el límite por transferencia por debajo del monto del schedule.
    from app import limit_service
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    conn.execute(
        "UPDATE transfer_limit SET per_transfer_cents = ? WHERE customer_id = ?",
        (1_000, cid))  # 10.00
    conn.commit()

    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    conn.commit()
    before = _balances(conn)

    s = recurring_service.process_due(conn, _NOW)

    assert s.failed == 1
    assert _balances(conn) == before
    execs = _executions(conn, res.id)
    assert len(execs) == 1 and execs[0]["outcome"] == "failed"


# --- Pureza / determinismo -----------------------------------------------------

def test_no_vencidos_no_hace_nada(conn):
    """Un schedule con `next_run_at` en el futuro no se procesa (determinista dado `now`)."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", now=_NOW)  # next_run = _NOW + 1 día
    before = _balances(conn)
    s = recurring_service.process_due(conn, _NOW)
    assert s.outcomes == []
    assert _balances(conn) == before
    assert _executions(conn, res.id) == []


def test_multiples_schedules_independientes(conn):
    """Cada ocurrencia corre en su propia transacción: el fallo de una no aborta las demás."""
    ok_id, _ = _make_internal_due(conn, created_now=_NOW - timedelta(days=1))

    # Un segundo schedule que FALLA por límite de negocio (no por excepción): bajamos el límite
    # por transferencia por debajo de su monto. El bueno (ok_id, 100.000) sigue bajo el límite.
    cid = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
    bad = recurring_service.create_schedule(
        conn, type="internal", amount_raw="200000.00", frequency="daily",
        from_kind="savings", to_kind="checking", now=_NOW - timedelta(days=1))
    conn.execute(
        "UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (iso(_NOW), bad.id))
    conn.execute(
        "UPDATE transfer_limit SET per_transfer_cents = ? WHERE customer_id = ?",
        (15_000_000, cid))  # 150.000: permite el bueno (100.000), rechaza el malo (200.000)
    conn.commit()

    s = recurring_service.process_due(conn, _NOW)
    assert s.executed == 1 and s.failed == 1       # el bueno corrió pese al fallo del otro
    assert len(_executions(conn, ok_id)) == 1
    assert _executions(conn, ok_id)[0]["outcome"] == "executed"
    assert _executions(conn, bad.id)[0]["outcome"] == "failed"


# --- Fallo de negocio: el schedule NO queda atascado (Tarea 31, REC-10, Req. 11.2, A19) --------

def test_failed_registra_outcome_failed_sin_transfer_y_avanza(conn):
    """REC-10/11.2: el fallo de negocio persiste `outcome='failed'`, `transfer_id=NULL` y avanza.

    Verifica explícitamente los tres efectos del contrato de la Tarea 31 sobre la MISMA fila de
    ejecución: (1) `outcome='failed'`, (2) `transfer_id IS NULL` (no hubo movimiento) y (3)
    `next_run_at` avanzado un intervalo (schedule no atascado).
    """
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="weekly",
        from_kind="checking", to_kind="savings", now=_NOW - timedelta(days=1))
    due = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due, res.id))
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (1,))
    conn.commit()

    summary = recurring_service.process_due(conn, _NOW)

    assert summary.failed == 1 and summary.executed == 0 and summary.skipped == 0
    # El resumen por ocurrencia también refleja el fallo sin transfer_id.
    assert summary.outcomes[0].status == "failed"
    assert summary.outcomes[0].transfer_id is None

    execs = _executions(conn, res.id)
    assert len(execs) == 1
    assert execs[0]["outcome"] == "failed"
    assert execs[0]["transfer_id"] is None
    assert execs[0]["due_at"] == due            # identidad = vencimiento original
    # Avanzó un intervalo semanal desde el vencimiento, no desde `now`.
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due) + timedelta(days=7)


def test_failed_no_queda_atascado_siguiente_ocurrencia_ejecuta(conn):
    """A19: tras un fallo que avanza la fecha, la ocurrencia siguiente ejecuta limpiamente.

    Prueba el núcleo de la Tarea 31 end-to-end: una ocurrencia falla por fondos (se registra
    `failed`, sin débito, y `next_run_at` avanza); al restaurar los fondos y correr `process_due`
    en el nuevo vencimiento, esa ocurrencia ejecuta con éxito. El schedule NO quedó atascado en
    la ocurrencia fallida ni la reintentó.
    """
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", now=_NOW - timedelta(days=1))
    due1 = iso(_NOW)
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?", (due1, res.id))
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (5_000_000,))
    conn.commit()

    # Primera corrida: falla por fondos, sin débito, avanza al día siguiente.
    s1 = recurring_service.process_due(conn, _NOW)
    assert s1.failed == 1 and s1.executed == 0
    schedule_after_fail = repository.get_schedule(conn, res.id)
    due2 = schedule_after_fail.next_run_at
    assert parse_iso(due2) == parse_iso(due1) + timedelta(days=1)
    balances_after_fail = _balances(conn)
    assert balances_after_fail["checking"] == 5_000_000      # intacto (sin débito)

    # Restaurar fondos suficientes y avanzar el reloj al nuevo vencimiento.
    conn.execute("UPDATE account SET balance_cents = ? WHERE kind = 'checking'", (20_000_000,))
    conn.commit()
    now2 = parse_iso(due2)

    # Segunda corrida: la ocurrencia del nuevo vencimiento ejecuta con éxito.
    s2 = recurring_service.process_due(conn, now2)
    assert s2.executed == 1 and s2.failed == 0 and s2.skipped == 0
    assert _balances(conn)["checking"] == 20_000_000 - 10_000_000

    # Dos filas de ejecución distintas: una failed (due1) y una executed (due2); sin reintento
    # de la fallida.
    execs = _executions(conn, res.id)
    outcomes = {e["due_at"]: e["outcome"] for e in execs}
    assert outcomes == {due1: "failed", due2: "executed"}
    # La fecha avanzó de nuevo tras el éxito: schedule sigue vivo, nunca atascado.
    assert parse_iso(repository.get_schedule(conn, res.id).next_run_at) == \
        parse_iso(due2) + timedelta(days=1)
