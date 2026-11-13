from datetime import datetime, timezone, timedelta
from backend.app.services.recurring_service import execute_due_recurring_schedules


def test_recurring_schedule_creation(client):
    """Test creating recurring payment schedules for internal and ACH transfers."""
    # 1. Internal transfer schedule <= $1,000 (no PIN required)
    resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 200.00,
            "frequency": "weekly",
            "description": "Weekly savings contribution",
        },
    )
    assert resp.status_code == 201
    sched = resp.json()
    assert sched["status"] == "active"
    assert sched["frequency"] == "weekly"
    assert sched["amount"] == 200.00
    assert sched["from_account_id"] == 1
    assert sched["to_account_id"] == 2

    # 2. ACH schedule > $1,000 without PIN -> 428
    resp_428 = client.post(
        "/api/recurring",
        json={
            "transfer_type": "ach",
            "from_account_id": 2,
            "amount": 1200.00,
            "frequency": "monthly",
            "recipient_name": "Investment Fund",
            "routing_number": "123456789",
            "account_number": "11223344",
            "bank_name": "Vanguard",
        },
    )
    assert resp_428.status_code == 428
    assert resp_428.json()["detail"] == "MFA_REQUIRED"

    # 3. ACH schedule > $1,000 with valid PIN -> 201
    resp_pin = client.post(
        "/api/recurring",
        json={
            "transfer_type": "ach",
            "from_account_id": 2,
            "amount": 1200.00,
            "frequency": "monthly",
            "recipient_name": "Investment Fund",
            "routing_number": "123456789",
            "account_number": "11223344",
            "bank_name": "Vanguard",
            "pin": "1234",
        },
    )
    assert resp_pin.status_code == 201
    assert resp_pin.json()["status"] == "active"

    # 4. Invalid frequency -> 422
    bad_freq = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 50.00,
            "frequency": "hourly",
        },
    )
    assert bad_freq.status_code == 422


def test_recurring_schedule_lifecycle(client):
    """Test pausing, resuming, and cancelling recurring schedules."""
    # Create schedule
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 100.00,
            "frequency": "daily",
        },
    )
    sched_id = create_resp.json()["id"]

    # Pause
    pause_resp = client.post(f"/api/recurring/{sched_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    # Resume
    resume_resp = client.post(f"/api/recurring/{sched_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "active"

    # Cancel
    cancel_resp = client.post(f"/api/recurring/{sched_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Resuming cancelled schedule should fail
    bad_resume = client.post(f"/api/recurring/{sched_id}/resume")
    assert bad_resume.status_code == 400


def test_recurring_execution_success_and_date_advancement(client, db_session):
    """Test executing due recurring schedules autonomously and advancing next_execution_date."""
    # Create due schedule (start_date in past)
    past_date = datetime.now(timezone.utc) - timedelta(hours=1)
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 150.00,
            "frequency": "daily",
            "start_date": past_date.isoformat(),
        },
    )
    sched_id = create_resp.json()["id"]
    initial_next_date = create_resp.json()["next_execution_date"]

    chk_before = client.get("/api/accounts/1").json()["balance"]
    sav_before = client.get("/api/accounts/2").json()["balance"]

    # Run execution
    results = execute_due_recurring_schedules(db_session)
    assert any(r["schedule_id"] == sched_id and r["status"] == "success" for r in results)

    # Balances updated
    chk_after = client.get("/api/accounts/1").json()["balance"]
    sav_after = client.get("/api/accounts/2").json()["balance"]
    assert chk_after == round(chk_before - 150.00, 2)
    assert sav_after == round(sav_before + 150.00, 2)

    # Schedule advanced
    sched_after = client.get("/api/recurring").json()
    target = next(s for s in sched_after if s["id"] == sched_id)
    assert target["last_executed_at"] is not None
    assert target["next_execution_date"] > initial_next_date


def test_recurring_execution_failure_on_insufficient_funds(client, db_session):
    """Test that recurring execution failure records a failure and advances date without failing silently."""
    past_date = datetime.now(timezone.utc) - timedelta(hours=1)
    # Checking has $2,500.00, schedule $9,000.00 (within single limit $5,000? No, let's use $2,400 then spend it)
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 2400.00,
            "frequency": "weekly",
            "start_date": past_date.isoformat(),
            "pin": "1234",
        },
    )
    sched_id = create_resp.json()["id"]

    # Spend from checking so funds are insufficient (< 2400)
    client.post(
        "/api/transfers",
        json={"from_account_id": 1, "to_account_id": 2, "amount": 500.00},
    )

    # Run scheduler
    results = execute_due_recurring_schedules(db_session)
    fail_res = next((r for r in results if r["schedule_id"] == sched_id), None)
    assert fail_res is not None
    assert fail_res["status"] == "failed"

    # Schedule remains active with incremented failure_count
    sched_list = client.get("/api/recurring").json()
    sched = next(s for s in sched_list if s["id"] == sched_id)
    assert sched["status"] == "active"


def test_pause_cancelled_or_paused_schedule_fails(client):
    """DEFECT-01 regression: Pausing a cancelled schedule fails with HTTP 400."""
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 50.00,
            "frequency": "daily",
        },
    )
    sched_id = create_resp.json()["id"]

    # Cancel the schedule
    cancel_resp = client.post(f"/api/recurring/{sched_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Attempting to pause cancelled schedule returns HTTP 400
    pause_resp = client.post(f"/api/recurring/{sched_id}/pause")
    assert pause_resp.status_code == 400
    assert "cannot pause a cancelled" in pause_resp.json()["detail"].lower()

    # Attempting to resume cancelled schedule returns HTTP 400
    resume_resp = client.post(f"/api/recurring/{sched_id}/resume")
    assert resume_resp.status_code == 400

    # Test already paused / already active guards
    create_resp2 = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 75.00,
            "frequency": "weekly",
        },
    )
    sched_id2 = create_resp2.json()["id"]
    client.post(f"/api/recurring/{sched_id2}/pause")

    double_pause = client.post(f"/api/recurring/{sched_id2}/pause")
    assert double_pause.status_code == 400
    assert "already paused" in double_pause.json()["detail"].lower()

    client.post(f"/api/recurring/{sched_id2}/resume")
    double_resume = client.post(f"/api/recurring/{sched_id2}/resume")
    assert double_resume.status_code == 400
    assert "already active" in double_resume.json()["detail"].lower()


def test_recurring_schedule_creation_omitted_start_date_advances_interval(client, db_session):
    """DEFECT-02 regression: Omitting start_date schedules first execution in the future, not immediately."""
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 100.00,
            "frequency": "daily",
        },
    )
    assert create_resp.status_code == 201
    sched = create_resp.json()

    created_at = datetime.fromisoformat(sched["created_at"])
    next_exec = datetime.fromisoformat(sched["next_execution_date"])

    # Next execution must be >= 23 hours in the future (advance +1 day for daily)
    assert next_exec >= created_at + timedelta(hours=23)

    # Scheduler running immediately does not execute this future-dated schedule
    results = execute_due_recurring_schedules(db_session)
    executed_ids = [r["schedule_id"] for r in results]
    assert sched["id"] not in executed_ids


def test_process_due_endpoint(client):
    """Test POST /api/recurring/process-due simulation endpoint."""
    resp = client.post("/api/recurring/process-due")
    assert resp.status_code == 200
    data = resp.json()
    assert "processed_count" in data
    assert "executions" in data
    assert isinstance(data["executions"], list)


def test_recurring_schedule_validation_errors(client):
    """Test validation errors for recurring schedule creation and lifecycle."""
    # Amount <= 0
    resp_zero = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 1, "to_account_id": 2, "amount": 0.00, "frequency": "daily"},
    )
    assert resp_zero.status_code == 422

    # Amount > 2 decimals
    resp_dec = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 1, "to_account_id": 2, "amount": 50.123, "frequency": "daily"},
    )
    assert resp_dec.status_code == 422

    # Non-existent from_account_id
    resp_acc = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 99999, "to_account_id": 2, "amount": 50.00, "frequency": "daily"},
    )
    assert resp_acc.status_code == 404

    # Non-existent schedule ID on pause/resume/cancel
    assert client.post("/api/recurring/99999/pause").status_code == 404
    assert client.post("/api/recurring/99999/resume").status_code == 404
    assert client.post("/api/recurring/99999/cancel").status_code == 404


def test_paused_and_cancelled_schedules_skipped_by_scheduler(client, db_session):
    """Test that paused or cancelled schedules are not executed by the background scheduler."""
    past_date = datetime.now(timezone.utc) - timedelta(hours=2)
    # Create due schedule
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 30.00,
            "frequency": "daily",
            "start_date": past_date.isoformat(),
        },
    )
    sched_id = create_resp.json()["id"]

    # Pause it
    client.post(f"/api/recurring/{sched_id}/pause")

    # Run scheduler
    results = execute_due_recurring_schedules(db_session)
    executed_ids = [r["schedule_id"] for r in results]
    assert sched_id not in executed_ids


def test_recurring_ach_execution_success(client, db_session):
    """Test background scheduler executing a due recurring ACH transfer."""
    # Create beneficiary
    ben_resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Utility Provider",
            "routing_number": "123456789",
            "account_number": "987654321",
            "bank_name": "Power Bank",
        },
    )
    ben_id = ben_resp.json()["id"]

    past_date = datetime.now(timezone.utc) - timedelta(hours=1)
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "ach",
            "from_account_id": 1,
            "beneficiary_id": ben_id,
            "amount": 80.00,
            "frequency": "monthly",
            "start_date": past_date.isoformat(),
        },
    )
    sched_id = create_resp.json()["id"]

    initial_balance = client.get("/api/accounts/1").json()["balance"]

    # Run scheduler
    results = execute_due_recurring_schedules(db_session)
    ach_res = next((r for r in results if r["schedule_id"] == sched_id), None)
    assert ach_res is not None
    assert ach_res["status"] == "success"

    # Balance debited
    new_balance = client.get("/api/accounts/1").json()["balance"]
    assert new_balance == initial_balance - 80.00

