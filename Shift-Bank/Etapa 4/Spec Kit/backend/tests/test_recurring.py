import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from database import DB_PATH, get_connection, init_db
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="function", autouse=True)
def reset_db():
    """Resets the isolated test database before each test."""
    conn = get_connection()
    cursor = conn.cursor()
    for table in ("recurring_occurrences", "history_projection", "domain_events", "idempotency_records", "projection_checkpoints", "stage4_migration_markers"):
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    cursor.execute("DROP TABLE IF EXISTS recurring_schedules;")
    cursor.execute("DROP TABLE IF EXISTS limits;")
    cursor.execute("DROP TABLE IF EXISTS beneficiaries;")
    cursor.execute("DROP TABLE IF EXISTS transfers;")
    cursor.execute("DROP TABLE IF EXISTS accounts;")
    conn.commit()
    conn.close()

    init_db()
    yield


# ==============================================================================
# T028: Recurring Schedule Creation & Intervals (A15, A16, D-08, D-09, F-06)
# ==============================================================================

def test_recurring_default_first_due_date():
    """Verifies daily schedule without start_date runs after +24h, not immediately, with no debit at creation (A15, D-09)."""
    client = TestClient(app)

    payload = {
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00",
        "frequency": "DAILY"
    }
    resp = client.post("/api/recurring-schedules", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "ACTIVE"
    assert data["frequency"] == "DAILY"
    assert data["transfer_type"] == "INTERNAL"
    assert data["amount"] == "100000.00"

    # Verify no debit at creation (A15, D-03)
    checking = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking["balance"] == "5000000.00"

    # Verify first due date is scheduled for approx +24 hours (+1 day) from creation
    created_dt = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    due_dt = datetime.fromisoformat(data["next_due_date"].replace("Z", "+00:00"))
    diff_seconds = (due_dt - created_dt).total_seconds()
    assert abs(diff_seconds - 86400) <= 5  # Exactly 24 hours +/- 5s tolerance


def test_recurring_frequency_intervals():
    """Verifies weekly (+7d) and monthly (strictly +30d) frequency intervals (A16, D-09)."""
    client = TestClient(app)

    # Weekly (+7d)
    w_resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "50000.00",
        "frequency": "WEEKLY"
    })
    assert w_resp.status_code == 201
    w_data = w_resp.json()
    w_created = datetime.fromisoformat(w_data["created_at"].replace("Z", "+00:00"))
    w_due = datetime.fromisoformat(w_data["next_due_date"].replace("Z", "+00:00"))
    assert abs((w_due - w_created).total_seconds() - 7 * 86400) <= 5

    # Monthly (strictly +30d per D-09, REC-02)
    m_resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "75000.00",
        "frequency": "MONTHLY"
    })
    assert m_resp.status_code == 201
    m_data = m_resp.json()
    m_created = datetime.fromisoformat(m_data["created_at"].replace("Z", "+00:00"))
    m_due = datetime.fromisoformat(m_data["next_due_date"].replace("Z", "+00:00"))
    assert abs((m_due - m_created).total_seconds() - 30 * 86400) <= 5


def test_recurring_explicit_start_date_validation():
    """Verifies explicit future start date YYYY-MM-DD at 00:00:00 UTC and rejection of current/past dates (D-09)."""
    client = TestClient(app)

    now_utc = datetime.now(timezone.utc)
    future_date = (now_utc + timedelta(days=5)).strftime("%Y-%m-%d")
    past_date = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    today_date = now_utc.strftime("%Y-%m-%d")

    base_payload = {
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00",
        "frequency": "MONTHLY"
    }

    # 1. Past date -> 400 Bad Request
    r_past = client.post("/api/recurring-schedules", json={**base_payload, "start_date": past_date})
    assert r_past.status_code == 400

    # 2. Today's date (not strictly future) -> 400 Bad Request
    r_today = client.post("/api/recurring-schedules", json={**base_payload, "start_date": today_date})
    assert r_today.status_code == 400

    # 3. Strictly future date -> Accepted with 00:00:00 UTC
    r_future = client.post("/api/recurring-schedules", json={**base_payload, "start_date": future_date})
    assert r_future.status_code == 201
    data = r_future.json()
    assert data["next_due_date"] == f"{future_date}T00:00:00Z"


# ==============================================================================
# T029: Sensitive Recurring Schedule MFA Lifecycle (D-03, D-05, F-08)
# ==============================================================================

def test_sensitive_recurring_mfa_flow_and_expiration():
    """Verifies sensitive schedule (>= COP 1M) enters PENDING_MFA, activates on code 123456, or expires (D-03, D-05, F-08)."""
    client = TestClient(app)

    # 1. Create sensitive schedule: COP 1,500,000.00
    payload = {
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00",
        "frequency": "MONTHLY"
    }
    resp = client.post("/api/recurring-schedules", json=payload)
    assert resp.status_code == 202
    data = resp.json()

    assert data["status"] == "PENDING_MFA"
    assert data["mfa_expires_at"] is not None
    sched_id = data["id"]

    # Verify no funds debited
    checking = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking["balance"] == "5000000.00"

    # 2. PENDING_MFA schedule is NOT executable by scheduler
    conn = get_connection()
    past_due = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (past_due, sched_id))
    conn.commit()
    conn.close()

    sweep = client.post("/api/test/recurring/run-due")
    assert sweep.status_code == 200
    assert sweep.json()["processed_count"] == 0

    # 3. Invalid code retry returns 401
    bad_confirm = client.post(f"/api/recurring-schedules/{sched_id}/confirm-mfa", json={"code": "000000"})
    assert bad_confirm.status_code == 401

    # 4. Valid code 123456 confirms and activates schedule
    good_confirm = client.post(f"/api/recurring-schedules/{sched_id}/confirm-mfa", json={"code": "123456"})
    assert good_confirm.status_code == 200

    # Verify schedule is now ACTIVE and mfa_expires_at is cleared
    schedules = client.get("/api/recurring-schedules").json()
    active_sched = next(s for s in schedules if s["id"] == sched_id)
    assert active_sched["status"] == "ACTIVE"
    assert active_sched["mfa_expires_at"] is None


def test_sensitive_recurring_mfa_expiration_sweep():
    """Verifies PENDING_MFA schedule past 300s window automatically sweeps to EXPIRED (F-08)."""
    client = TestClient(app)

    # Create sensitive schedule
    resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1200000.00",
        "frequency": "MONTHLY"
    })
    assert resp.status_code == 202
    sched_id = resp.json()["id"]

    # Backdate mfa_expires_at in database to simulate expiration
    conn = get_connection()
    past_expiry = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET mfa_expires_at = ? WHERE id = ?;", (past_expiry, sched_id))
    conn.commit()
    conn.close()

    # Query GET /api/recurring-schedules -> automatically sweeps expired challenges (F-08)
    schedules = client.get("/api/recurring-schedules").json()
    expired_sched = next(s for s in schedules if s["id"] == sched_id)
    assert expired_sched["status"] == "EXPIRED"

    # Confirming expired schedule returns 410 Gone
    confirm_resp = client.post(f"/api/recurring-schedules/{sched_id}/confirm-mfa", json={"code": "123456"})
    assert confirm_resp.status_code == 410


# ==============================================================================
# T030: Lifecycle Controls & Autonomous Execution (A17, A18, A19, D-04)
# ==============================================================================

def test_recurring_pause_resume_cancel():
    """Verifies pause, resume, and terminal cancel behavior (REC-06, REC-07, A18)."""
    client = TestClient(app)

    # 1. Create active schedule
    resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "50000.00",
        "frequency": "DAILY"
    })
    sched_id = resp.json()["id"]

    # 2. Pause
    pause_resp = client.post(f"/api/recurring-schedules/{sched_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # Pausing again returns 400
    assert client.post(f"/api/recurring-schedules/{sched_id}/pause").status_code == 400

    # 3. Resume
    resume_resp = client.post(f"/api/recurring-schedules/{sched_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "ACTIVE"

    # Resuming active returns 400
    assert client.post(f"/api/recurring-schedules/{sched_id}/resume").status_code == 400

    # 4. Cancel
    cancel_resp = client.post(f"/api/recurring-schedules/{sched_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Terminal state: Cannot pause or resume cancelled schedule
    assert client.post(f"/api/recurring-schedules/{sched_id}/pause").status_code == 400
    assert client.post(f"/api/recurring-schedules/{sched_id}/resume").status_code == 400


def test_recurring_due_execution_advances_interval():
    """Verifies that active due schedules execute, debit funds, log history, and advance next_due_date (A17, D-04)."""
    client = TestClient(app)

    # 1. Create active daily schedule
    resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00",
        "frequency": "DAILY"
    })
    sched_id = resp.json()["id"]

    # 2. Simulate schedule becoming due by setting next_due_date to past
    conn = get_connection()
    due_time = (datetime.now(timezone.utc) - timedelta(minutes=5))
    due_iso = due_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (due_iso, sched_id))
    conn.commit()
    conn.close()

    # 3. Trigger execution sweep
    sweep_resp = client.post("/api/test/recurring/run-due")
    assert sweep_resp.status_code == 200
    assert sweep_resp.json()["processed_count"] == 1

    # 4. Verify balances updated: Checking 5M - 100k = 4.9M; Savings 15M + 100k = 15.1M
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["id"] == "acc_checking_123")
    savings = next(a for a in accounts if a["id"] == "acc_savings_456")
    assert checking["balance"] == "4900000.00"
    assert savings["balance"] == "15100000.00"

    # 5. Verify next_due_date advanced by interval (24 hours from previous due time)
    sched = next(s for s in client.get("/api/recurring-schedules").json() if s["id"] == sched_id)
    new_due_dt = datetime.fromisoformat(sched["next_due_date"].replace("Z", "+00:00"))
    expected_due_dt = due_time + timedelta(days=1)
    assert abs((new_due_dt - expected_due_dt).total_seconds()) <= 2


def test_recurring_insufficient_funds_advances_without_debit():
    """Verifies that an active due schedule with insufficient funds logs failure and advances next_due_date without debiting (REC-10, A19)."""
    client = TestClient(app)

    # 1. Create schedule for COP 6,000,000.00 (checking has only 5M)
    # First set per-transfer limit high enough
    client.put("/api/limits", json={"per_transfer_limit": "10000000.00", "daily_limit": "10000000.00"})

    resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "6000000.00",
        "frequency": "DAILY"
    })
    sched_id = resp.json()["id"]

    # Confirm MFA to make it ACTIVE
    client.post(f"/api/recurring-schedules/{sched_id}/confirm-mfa", json={"code": "123456"})

    # Make it due
    conn = get_connection()
    due_time = (datetime.now(timezone.utc) - timedelta(minutes=5))
    due_iso = due_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (due_iso, sched_id))
    conn.commit()
    conn.close()

    # Trigger execution sweep
    sweep = client.post("/api/test/recurring/run-due")
    assert sweep.status_code == 200
    assert sweep.json()["failed_count"] == 1

    # Verify funds were NOT debited (checking remains 5,000,000.00)
    checking = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking["balance"] == "5000000.00"

    # Verify next_due_date was advanced by 24h so it does not get stuck
    sched = next(s for s in client.get("/api/recurring-schedules").json() if s["id"] == sched_id)
    new_due_dt = datetime.fromisoformat(sched["next_due_date"].replace("Z", "+00:00"))
    expected_due_dt = due_time + timedelta(days=1)
    assert abs((new_due_dt - expected_due_dt).total_seconds()) <= 2


# ==============================================================================
# T039: Beneficiary Deletion Snapshot Retention (REC-11, D-08)
# ==============================================================================

def test_recurring_beneficiary_deletion_preserves_snapshot():
    """Verifies that deleting a saved beneficiary preserves active recurring schedules referencing it (REC-11, D-08)."""
    client = TestClient(app)

    # 1. Create beneficiary
    ben = client.post("/api/beneficiaries", json={
        "name": "Servicios Publicos",
        "bank_name": "Banco Davivienda",
        "routing_number": "123456789",
        "account_number": "77665544"
    }).json()

    # 2. Create recurring ACH schedule referencing beneficiary
    sched = client.post("/api/recurring-schedules", json={
        "transfer_type": "ACH",
        "source_account_id": "acc_checking_123",
        "recipient_name": ben["name"],
        "bank_name": ben["bank_name"],
        "routing_number": ben["routing_number"],
        "account_number": ben["account_number"],
        "amount": "120000.00",
        "frequency": "MONTHLY"
    }).json()

    # 3. Delete beneficiary
    del_resp = client.delete(f"/api/beneficiaries/{ben['id']}")
    assert del_resp.status_code == 204

    # 4. Verify schedule still exists and retains recipient snapshot
    schedules = client.get("/api/recurring-schedules").json()
    active_sched = next(s for s in schedules if s["id"] == sched["id"])
    assert "Servicios Publicos" in active_sched["destination_display"]
    assert "Davivienda" in active_sched["destination_display"]
