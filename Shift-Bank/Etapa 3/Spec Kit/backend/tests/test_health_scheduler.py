"""Automated tests for health endpoint and single-instance scheduler guard (T030, T031, FR-034, FR-035).

Verifies that:
1. GET /api/health returns 200 OK with healthy status when keys and DB are available.
2. GET /api/health returns 503 Service Unavailable when keys or DB are corrupted/missing (fail-closed).
3. start_background_scheduler enforces single-instance execution and does not spawn duplicate loops.
"""

import asyncio
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient
from main import app
from scheduler import is_scheduler_active, start_background_scheduler, stop_background_scheduler


def test_health_endpoint_healthy_state():
    """FR-035: GET /api/health returns 200 with status=healthy when keys and database are functional."""
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["crypto_keys_loaded"] is True
    assert "environment" in data


def test_health_endpoint_fail_closed_missing_keys(monkeypatch):
    """FR-035: GET /api/health returns 503 Service Unavailable if keys are missing (fail-closed)."""
    monkeypatch.delenv("BANK_STORAGE_KEY", raising=False)
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"
    assert data["crypto_keys_loaded"] is False


def test_single_instance_scheduler_guard():
    """FR-034: start_background_scheduler prevents duplicate concurrent scheduler execution."""
    async def _run_test():
        assert is_scheduler_active() is False

        task = asyncio.create_task(start_background_scheduler(interval_seconds=1.0))
        await asyncio.sleep(0.1)

        assert is_scheduler_active() is True

        # Attempt to start a second duplicate instance concurrently
        duplicate_task = asyncio.create_task(start_background_scheduler(interval_seconds=1.0))
        await asyncio.sleep(0.1)

        # Should still be active and not cause duplicate processing loops
        assert is_scheduler_active() is True

        await stop_background_scheduler(task)
        await stop_background_scheduler(duplicate_task)
        assert is_scheduler_active() is False

    asyncio.run(_run_test())


def test_no_duplicate_recurring_execution_across_restarts():
    """FR-034, Scenario 4.6: Sweeps do not duplicate recurring payments across restarts."""
    from database import get_connection
    from models import RecurringScheduleCreate
    from scheduler import run_recurring_execution_sweep_sync
    from services import create_recurring_schedule

    conn = get_connection()
    # Create active schedule due right now
    create_req = RecurringScheduleCreate(
        source_account_id="acc_checking_123",
        destination_account_id="acc_savings_456",
        amount="100.00",
        frequency="DAILY",
        transfer_type="INTERNAL",
    )
    status_code, sched = create_recurring_schedule(conn, create_req)
    # Set next_due_date to now_iso so it is due for the first sweep
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()
    cursor.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (now_iso, sched.id))
    conn.commit()
    conn.close()
    assert status_code == 201

    # First sweep executes the schedule
    processed_1, failed_1 = run_recurring_execution_sweep_sync()
    assert processed_1 >= 1

    # Immediate second sweep (simulating restart recovery sweep) must NOT re-execute
    processed_2, failed_2 = run_recurring_execution_sweep_sync()
    assert processed_2 == 0
    assert failed_2 == 0
