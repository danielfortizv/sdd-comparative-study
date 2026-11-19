"""Pruebas del scheduler de fondo (único worker) y su ciclo de vida (Etapa 2, Tarea 32).

Cubren:
- **Núcleo determinista del tick** (`scheduler.run_tick`): con un reloj simulado procesa los
  recurrentes vencidos (`process_due`) Y barre el settlement ACH (`settle_ach`) en una sola
  pasada (Req. 10.1, 10.4; REC-05). Sin esperar en tiempo real (Req. 10.5).
- **Settlement no elegible aún:** una ACH `pending` cuyo retardo de simulación no venció NO se
  liquida (determinismo por `now`, Tarea 23).
- **Idempotencia entre ticks (D07/ACH-08):** repetir el tick para el mismo `now` no duplica
  efectos (ni ocurrencias recurrentes ni liquidaciones).
- **Ciclo de vida asyncio (Req. 10.2):** el worker arranca una **única** tarea, ejecuta ticks
  reales contra una BD aislada y se **cancela limpiamente** en el apagado.
- **Recuperación tras reinicio (D07):** un `Scheduler` nuevo (simulando reinicio) procesa los
  vencidos pendientes vía `next_run_at`/`schedule_execution`, sin repetir lo ya registrado.
- **Sin endpoint admin público (Req. 10.6):** no existe ninguna ruta pública para disparar los
  recurrentes/settlement.

Reloj inyectable (`ManualClock`) para determinismo; la BD se aísla con el fixture del arnés.

_Requisitos: 10.1, 10.2, 10.6_ · _Contrato: REC-05; §3/§7_ · _Decisión: D02, D07_
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.ach_service as ach_service
import app.db as db
import app.recurring_service as recurring_service
import app.repository as repository
import app.scheduler as scheduler
from app.clock import ManualClock, iso, parse_iso

# El arnés no incluye `pytest-asyncio` (sin dependencias nuevas, Req. 16.1). Las pruebas del
# ciclo de vida asyncio se ejecutan como pruebas síncronas que conducen las corrutinas con un
# bucle de eventos propio, de forma determinista.
import asyncio


def _run(coro):
    """Ejecuta una corrutina en un bucle de eventos efímero y devuelve su resultado."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

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


def _make_internal_due(conn, *, due_at):
    """Crea un schedule interno y fuerza su vencimiento en `due_at`."""
    res = recurring_service.create_schedule(
        conn, type="internal", amount_raw="100000.00", frequency="daily",
        from_kind="checking", to_kind="savings", description="ahorro",
        now=_NOW - timedelta(days=1))
    conn.execute("UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?",
                 (iso(due_at), res.id))
    conn.commit()
    return res.id


def _make_pending_ach(conn, *, created_at):
    """Crea una ACH `pending` interactiva con `created_at` dado (para el barrido)."""
    res = ach_service.create_ach(
        conn, amount_raw="50000.00", description="pago", from_kind="savings",
        adhoc=_VALID_BEN)
    assert res.status == "pending"
    row = ach_service.ach_repository.get_ach_by_reference(conn, res.reference)
    conn.execute("UPDATE transfer SET created_at = ? WHERE id = ?", (iso(created_at), row["id"]))
    conn.commit()
    return row["id"]


# --- Núcleo determinista del tick ---------------------------------------------

def test_run_tick_procesa_recurrentes_y_barre_settlement(conn):
    """Un tick ejecuta el recurrente vencido Y liquida la ACH elegible, de forma determinista."""
    sid = _make_internal_due(conn, due_at=_NOW)
    delay = ach_service.ACH_SETTLEMENT_DELAY_SECONDS
    ach_id = _make_pending_ach(conn, created_at=_NOW - timedelta(seconds=delay + 1))
    before = _balances(conn)

    result = scheduler.run_tick(conn, _NOW)

    # Recurrente: una ocurrencia ejecutada; saldo movido checking → savings.
    assert result.executed == 1 and result.failed == 0
    after = _balances(conn)
    assert after["checking"] == before["checking"] - 10_000_000

    # Settlement: la ACH elegible pasó a `settled`.
    assert result.settled == 1
    settled = conn.execute("SELECT status FROM transfer WHERE id = ?", (ach_id,)).fetchone()
    assert settled["status"] == "settled"

    # El recurrente avanzó su próxima fecha.
    stored = repository.get_schedule(conn, sid)
    assert parse_iso(stored.next_run_at) == _NOW + timedelta(days=1)


def test_run_tick_no_liquida_ach_no_elegible(conn):
    """Una ACH `pending` cuyo retardo de settlement no venció NO se liquida (determinismo)."""
    delay = ach_service.ACH_SETTLEMENT_DELAY_SECONDS
    ach_id = _make_pending_ach(conn, created_at=_NOW - timedelta(seconds=delay - 1))

    result = scheduler.run_tick(conn, _NOW)

    assert result.settled == 0
    row = conn.execute("SELECT status FROM transfer WHERE id = ?", (ach_id,)).fetchone()
    assert row["status"] == "pending"


def test_run_tick_idempotente_para_mismo_now(conn):
    """Repetir el tick con el mismo `now` no duplica efectos (D07/ACH-08)."""
    _make_internal_due(conn, due_at=_NOW)
    delay = ach_service.ACH_SETTLEMENT_DELAY_SECONDS
    _make_pending_ach(conn, created_at=_NOW - timedelta(seconds=delay + 1))

    first = scheduler.run_tick(conn, _NOW)
    assert first.executed == 1 and first.settled == 1
    balances_after_first = _balances(conn)

    second = scheduler.run_tick(conn, _NOW)
    # La ocurrencia recurrente ya no vence (next_run_at avanzó) y la ACH ya está settled.
    assert second.executed == 0 and second.settled == 0
    assert _balances(conn) == balances_after_first


def test_run_tick_recupera_tras_reinicio(conn):
    """Recuperación tras reinicio (D07): el estado persistido basta; nada se repite."""
    sid = _make_internal_due(conn, due_at=_NOW)

    # Primer "arranque": procesa el vencido.
    first = scheduler.run_tick(conn, _NOW)
    assert first.executed == 1
    execs_1 = conn.execute(
        "SELECT COUNT(*) AS n FROM schedule_execution WHERE schedule_id = ?", (sid,)).fetchone()
    assert execs_1["n"] == 1

    # "Reinicio": un tick nuevo con el mismo `now` no reejecuta la ocurrencia ya registrada.
    second = scheduler.run_tick(conn, _NOW)
    assert second.executed == 0
    execs_2 = conn.execute(
        "SELECT COUNT(*) AS n FROM schedule_execution WHERE schedule_id = ?", (sid,)).fetchone()
    assert execs_2["n"] == 1


# --- Ciclo de vida asyncio (arranque/apagado limpios, Req. 10.2) --------------

def test_scheduler_worker_arranca_ejecuta_y_para_limpio(conn, monkeypatch, isolated_db_path):
    """El worker lanza UNA tarea, ejecuta ticks reales contra la BD aislada y para limpio."""
    # Tick rápido para no esperar en la prueba.
    monkeypatch.setattr(scheduler, "SCHEDULER_TICK_SECONDS", 0.01, raising=True)
    # El worker abre conexiones vía db.get_connection(); el fixture ya parchea DB_PATH a la BD
    # aislada, así que sus ticks operan sobre la misma base que este test.
    sid = _make_internal_due(conn, due_at=_NOW)

    async def _exercise():
        clk = ManualClock(_NOW)
        sched = scheduler.Scheduler(clk=clk)
        sched.start()
        assert sched.running
        # Esperar activamente a que un tick procese la ocurrencia vencida.
        for _ in range(200):
            await asyncio.sleep(0.01)
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM schedule_execution WHERE schedule_id = ?",
                (sid,)).fetchone()
            if row["n"] >= 1:
                break
        await sched.stop()
        assert not sched.running

    _run(_exercise())

    # La ocurrencia se ejecutó exactamente una vez pese a múltiples ticks (mismo `now`).
    final = conn.execute(
        "SELECT COUNT(*) AS n FROM schedule_execution WHERE schedule_id = ?", (sid,)).fetchone()
    assert final["n"] == 1


def test_scheduler_start_es_idempotente_un_solo_worker(monkeypatch):
    """`start()` no crea más de una tarea (un único scheduler, D07)."""
    monkeypatch.setattr(scheduler, "SCHEDULER_TICK_SECONDS", 0.01, raising=True)

    async def _exercise():
        sched = scheduler.Scheduler(clk=ManualClock(_NOW))
        sched.start()
        task1 = sched._task
        sched.start()  # segunda llamada: no debe reemplazar la tarea viva
        assert sched._task is task1
        await sched.stop()

    _run(_exercise())


def test_scheduler_stop_sin_start_es_seguro():
    """Detener un scheduler nunca arrancado no lanza ni cuelga."""
    async def _exercise():
        sched = scheduler.Scheduler(clk=ManualClock(_NOW))
        await sched.stop()  # no-op seguro
        assert not sched.running

    _run(_exercise())


# --- Sin endpoint administrativo público (Req. 10.6) --------------------------

def test_no_hay_endpoint_admin_para_disparar_scheduler(app_client):
    """No existe ninguna ruta pública cuyo único fin sea disparar recurrentes/settlement."""
    paths = {route.path for route in app_client.app.routes}
    forbidden_fragments = ("scheduler", "process-due", "process_due", "settle", "admin/run")
    offending = [p for p in paths if any(frag in p.lower() for frag in forbidden_fragments)]
    assert offending == [], f"Endpoints de disparo prohibidos expuestos: {offending}"
