"""Background Autonomous Scheduler & Concurrency Engine (F-03, F-07)

This module manages:
1. In-process asyncio.Lock() to serialize HTTP request writes and background sweeps.
2. Context manager for SQLite `BEGIN IMMEDIATE` transactions to guarantee cross-thread database locking.
3. Autonomous background processing loop running every 5 seconds under FastAPI lifespan.
4. Single-process execution mandate: Uvicorn MUST be run with `--workers 1` to prevent duplicate schedulers.
"""

import asyncio
import logging
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger("scheduler")

# Shared concurrency lock between HTTP request handlers and background tasks (F-07)
scheduler_lock = asyncio.Lock()

# Shutdown signal for graceful lifespan termination
_shutdown_event = asyncio.Event()


@contextmanager
def immediate_transaction(conn: sqlite3.Connection):
    """Context manager executing under SQLite BEGIN IMMEDIATE transaction lock.
    Guarantees that write locks are acquired immediately, preventing deadlock and
    concurrency collisions across concurrent worker tasks or threads.
    """
    conn.execute("BEGIN IMMEDIATE;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


async def scheduler_tick():
    """Single execution cycle of autonomous background tasks:
    1. Executes due active recurring payment schedules and advances intervals (REC-05, D-04, D-09).
    2. Settles eligible ACH transfers pending >= 10 seconds (ACH-06, F-03).
    """
    async with scheduler_lock:
        conn = None
        try:
            from database import get_connection
            from services import execute_due_recurring_schedules, settle_eligible_ach_transfers

            conn = get_connection()
            # 1. Recurring schedules sweep
            processed, failed = execute_due_recurring_schedules(conn)
            if processed > 0 or failed > 0:
                logger.info(f"Autonomous recurring sweep: processed {processed}, failed {failed} due schedules.")

            # 2. ACH auto-settlement sweep
            settled = settle_eligible_ach_transfers(conn, delay_seconds=10)
            if settled > 0:
                logger.info(f"Autonomous background settlement: settled {settled} ACH transfers.")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error during scheduler tick: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()


def run_ach_settlement_sweep_sync(delay_seconds: int = 0) -> int:
    """Synchronous trigger for settlement sweep used by test endpoint POST /api/test/ach/settle-pending (D-04, D-06)."""
    from database import get_connection
    from services import settle_eligible_ach_transfers

    conn = get_connection()
    try:
        return settle_eligible_ach_transfers(conn, delay_seconds=delay_seconds)
    finally:
        conn.close()


def run_recurring_execution_sweep_sync() -> tuple[int, int]:
    """Synchronous trigger for recurring execution sweep used by test endpoint POST /api/test/recurring/run-due (D-04)."""
    from database import get_connection
    from services import execute_due_recurring_schedules

    conn = get_connection()
    try:
        return execute_due_recurring_schedules(conn)
    finally:
        conn.close()


async def start_background_scheduler(interval_seconds: float = 5.0):
    """Runs the autonomous background loop every interval_seconds until shutdown."""
    _shutdown_event.clear()
    logger.info("Starting autonomous background scheduler loop (single-process mode).")
    while not _shutdown_event.is_set():
        try:
            await scheduler_tick()
            await asyncio.wait_for(_shutdown_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            # Expected interval timeout, continue loop
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001
            logger.error(f"Unexpected error in background scheduler: {e}", exc_info=True)
            await asyncio.sleep(1.0)
    logger.info("Autonomous background scheduler loop stopped.")


async def stop_background_scheduler(task: asyncio.Task | None = None):
    """Signals the background scheduler to stop and awaits completion."""
    _shutdown_event.set()
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
