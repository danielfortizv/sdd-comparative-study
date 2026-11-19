"""Scheduler de fondo (único worker) y su ciclo de vida (Etapa 2, Tarea 32).

Diseño (DD-2/DD-3, D02, D07; Req. 10.1, 10.2, 10.6):
- **Una sola** tarea asyncio lanzada en el `lifespan` de FastAPI (startup) que cada
  `SCHEDULER_TICK_SECONDS` "despierta" y ejecuta un *tick*:
    1. `recurring_service.process_due(conn, now)` — ejecuta las ocurrencias recurrentes vencidas
       (durable e idempotente, Tarea 30).
    2. **Barrido de settlement ACH** — liquida las ACH `pending` cuyo retardo de simulación ya
       venció (`ach_service.settle_ach`, Tarea 23), de forma idempotente.
  Ambas operaciones comparten el mismo mecanismo de scheduler (D02): no hay un endpoint
  administrativo público cuyo único fin sea disparar los recurrentes/settlement (Req. 10.6).
- **Separación disparador/lógica (DD-3):** la lógica de negocio (qué ejecutar/liquidar y cuándo)
  vive en `recurring_service`/`ach_service` y es determinista dado `now`. El scheduler solo
  aporta el disparo temporal. `now` se toma del **reloj inyectable** (`clock.py`), de modo que
  la lógica del tick es verificable sin esperar en tiempo real (Req. 10.5).
- **Apagado limpio (Req. 10.2):** en el shutdown la tarea se cancela (`task.cancel()`) y se
  espera su término absorbiendo `CancelledError`; no inicia un nuevo ciclo tras la señal.
- **Recuperación tras reinicio (D07):** `next_run_at` y `schedule_execution` están persistidos,
  así que al reiniciar el scheduler reanuda procesando los vencidos pendientes; las ocurrencias
  ya registradas no se repiten (`UNIQUE(schedule_id, due_at)`). No hay estado en memoria que
  recuperar.
- **Un único worker (D07):** la Etapa 2 se opera con un solo proceso/worker de backend, por lo
  que existe exactamente una instancia del scheduler. La garantía de exactamente-una-vez no
  depende de ello (reside en la `UNIQUE` + transacción atómica).

Robustez: un fallo en un tick (p. ej. un error transitorio de BD) se registra y NO derriba el
bucle; el siguiente tick reintenta. Solo `CancelledError` detiene el worker (apagado).

Convenciones heredadas: sin ORM; SQLite vía `db.get_connection`; fechas/`now` con `clock`.

_Requisitos: 10.1, 10.2, 10.6_ · _Contrato: REC-05; §3/§7_ · _Decisión: D02, D07_
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from . import ach_service, clock, db, recurring_service
from .clock import Clock
from .config import SCHEDULER_TICK_SECONDS

logger = logging.getLogger("shift_bank.scheduler")


@dataclass
class TickResult:
    """Resumen de un tick del scheduler (útil para pruebas y trazas)."""

    executed: int = 0          # ocurrencias recurrentes ejecutadas
    failed: int = 0            # ocurrencias recurrentes con fallo de negocio (REC-10)
    skipped: int = 0           # ocurrencias omitidas por idempotencia (UNIQUE)
    settled: int = 0           # ACH liquidadas en el barrido de settlement


def _settlement_sweep(conn: sqlite3.Connection, now: datetime) -> int:
    """Barrido de settlement ACH: liquida cada ACH `pending` elegible (Tarea 23).

    Recorre las ACH `pending` y delega en `ach_service.settle_ach`, que decide la elegibilidad
    de forma determinista con `now` (reloj inyectable) y es idempotente. Devuelve cuántas
    transicionaron `pending → settled` en este barrido.
    """
    settled = 0
    from . import ach_repository

    for row in ach_repository.list_pending_ach(conn):
        if ach_service.settle_ach(conn, row["id"], now=now):
            settled += 1
    return settled


def run_tick(conn: sqlite3.Connection, now: datetime) -> TickResult:
    """Ejecuta un único tick del scheduler de forma determinista (núcleo testable).

    No usa el reloj de pared ni asincronía: recibe `(conn, now)` y hace exactamente lo que cada
    tick del worker hace, en orden:
      1. `recurring_service.process_due(conn, now)` (ejecución de recurrentes vencidos).
      2. Barrido de settlement ACH (`settle_ach` sobre las `pending` elegibles).

    Separado del bucle asyncio para poder verificarlo con un reloj simulado (Req. 10.5), sin
    esperar en tiempo real. Devuelve un `TickResult` con los contadores del tick.
    """
    summary = recurring_service.process_due(conn, now)
    settled = _settlement_sweep(conn, now)
    return TickResult(
        executed=summary.executed,
        failed=summary.failed,
        skipped=summary.skipped,
        settled=settled,
    )


async def _run_loop(clk: Clock, stop_event: asyncio.Event) -> None:
    """Bucle del worker de fondo (única tarea asyncio).

    Cada `SCHEDULER_TICK_SECONDS` abre una conexión propia, ejecuta `run_tick(conn, now)` con el
    `now` del reloj inyectado y la cierra. Entre ticks espera el intervalo; si `stop_event` se
    señala durante la espera, termina de inmediato sin iniciar un nuevo ciclo (apagado limpio,
    Req. 10.2). Un error en un tick se registra y NO rompe el bucle: el siguiente tick reintenta.
    """
    logger.info("Scheduler de fondo iniciado (tick=%ss)", SCHEDULER_TICK_SECONDS)
    try:
        while not stop_event.is_set():
            try:
                now = clk.now_utc()
                conn = db.get_connection()
                try:
                    run_tick(conn, now)
                finally:
                    conn.close()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - un tick con error no debe derribar el worker
                logger.exception("Fallo en un tick del scheduler; se reintentará en el siguiente")

            # Espera cancelable: si se señala el apagado durante la espera, salimos sin un
            # nuevo ciclo. `wait_for` sobre el evento con timeout evita un `sleep` no cancelable.
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=SCHEDULER_TICK_SECONDS)
            except asyncio.TimeoutError:
                pass  # expiró el intervalo: toca el siguiente tick
    except asyncio.CancelledError:
        logger.info("Scheduler de fondo cancelado; apagado limpio")
        raise
    finally:
        logger.info("Scheduler de fondo detenido")


class Scheduler:
    """Controlador del ciclo de vida del scheduler de fondo (una sola tarea asyncio).

    Lo instancia y referencia el `lifespan` de la app (startup lanza; shutdown detiene). Guarda
    la única `asyncio.Task` y un `asyncio.Event` para señalar el apagado de forma cooperativa.
    """

    def __init__(self, clk: Clock | None = None) -> None:
        self._clock: Clock = clk or clock.system_clock
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    def start(self) -> None:
        """Lanza la única tarea de fondo (idempotente mientras la tarea siga viva)."""
        if self._task is not None and not self._task.done():
            return  # ya hay exactamente un scheduler en marcha
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            _run_loop(self._clock, self._stop_event), name="shift-bank-scheduler")

    async def stop(self) -> None:
        """Detiene limpiamente la tarea de fondo (Req. 10.2).

        Señala el apagado, cancela la tarea y espera su término absorbiendo `CancelledError`.
        Seguro de llamar aunque la tarea nunca se haya lanzado o ya haya terminado.
        """
        if self._stop_event is not None:
            self._stop_event.set()
        task = self._task
        if task is None:
            return
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            # Solo absorbemos la cancelación de la **tarea worker** que acabamos de cancelar
            # (`task.cancelled()` es verdadero): es el apagado limpio esperado (Req. 10.2). Si en
            # cambio fue **este `stop()`** quien resultó cancelado por su llamador mientras
            # esperaba, `task` no está cancelada y la cancelación debe propagarse (S7497).
            if not task.cancelled():
                raise
        finally:
            self._task = None
            self._stop_event = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()
