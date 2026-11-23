import threading
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.services import transfer_service, recurring_service

_scheduler_running = False
_scheduler_thread = None


def run_scheduler_tick(db: Session):
    """
    Executes a single scheduler cycle:
    1. Settles in-flight pending ACH transfers.
    2. Executes due recurring payments.
    """
    try:
        transfer_service.process_pending_ach_transfers(db)
        recurring_service.execute_due_recurring_schedules(db)
    except Exception as e:
        # In background tasks, log exception without crashing thread
        print(f"[Scheduler] Error during scheduler cycle: {e}")


def _scheduler_loop(interval_seconds: float = 5.0):
    global _scheduler_running
    while _scheduler_running:
        db = SessionLocal()
        try:
            run_scheduler_tick(db)
        finally:
            db.close()
        time.sleep(interval_seconds)


def start_background_scheduler(interval_seconds: float = 5.0):
    """Starts the background scheduler thread if not already running."""
    global _scheduler_running, _scheduler_thread
    if not _scheduler_running:
        _scheduler_running = True
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(interval_seconds,),
            daemon=True,
            name="ShiftBankScheduler",
        )
        _scheduler_thread.start()


def stop_background_scheduler():
    """Stops the background scheduler thread."""
    global _scheduler_running
    _scheduler_running = False
