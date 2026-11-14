import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from backend.app.models import RecurringSchedule
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
            "amount": "200.00",
            "frequency": "weekly",
            "description": "Weekly savings contribution",
        },
    )
    assert resp.status_code == 201
    sched = resp.json()
    assert sched["status"] == "active"
    assert sched["frequency"] == "weekly"
    assert sched["amount"] == "200.00"
    assert sched["from_account_id"] == 1
    assert sched["to_account_id"] == 2

    # 2. ACH schedule > $1,000 without PIN -> 428
    resp_428 = client.post(
        "/api/recurring",
        json={
            "transfer_type": "ach",
            "from_account_id": 2,
            "amount": "1200.00",
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
            "amount": "1200.00",
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
            "amount": "50.00",
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
            "amount": "100.00",
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
            "amount": "150.00",
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
    assert Decimal(chk_after) == Decimal(chk_before) - Decimal("150.00")
    assert Decimal(sav_after) == Decimal(sav_before) + Decimal("150.00")

    # Schedule advanced
    sched_after = client.get("/api/recurring").json()
    target = next(s for s in sched_after if s["id"] == sched_id)
    assert target["last_executed_at"] is not None
    assert target["next_execution_date"] > initial_next_date


def test_recurring_execution_failure_on_insufficient_funds(client, db_session):
    """Test that recurring execution failure records a failure and advances date without failing silently."""
    past_date = datetime.now(timezone.utc) - timedelta(hours=1)
    # Checking has $2,500.00, schedule $2,400.00
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": "2400.00",
            "frequency": "weekly",
            "start_date": past_date.isoformat(),
            "pin": "1234",
        },
    )
    sched_id = create_resp.json()["id"]

    chk = client.get("/api/accounts/1").json()
    sav = client.get("/api/accounts/2").json()

    # Spend from checking with D-13 Idempotency-Key and D-14 versions so funds become insufficient ($2,000 < $2,400)
    spend_resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": "500.00",
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
            "description": "Spend checking balance",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert spend_resp.status_code == 200

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
            "amount": "50.00",
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
            "amount": "75.00",
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
            "amount": "100.00",
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
        json={"transfer_type": "internal", "from_account_id": 1, "to_account_id": 2, "amount": "0.00", "frequency": "daily"},
    )
    assert resp_zero.status_code == 422

    # Amount > 2 decimals
    resp_dec = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 1, "to_account_id": 2, "amount": "50.123", "frequency": "daily"},
    )
    assert resp_dec.status_code == 422

    # Non-existent from_account_id
    resp_acc = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 99999, "to_account_id": 2, "amount": "50.00", "frequency": "daily"},
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
            "amount": "30.00",
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
            "amount": "80.00",
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
    assert Decimal(new_balance) == Decimal(initial_balance) - Decimal("80.00")


def test_concurrent_scheduler_execution_does_not_duplicate_transfer(tmp_path):
    """
    Concurrency regression test for D-09/D-12/D-13:
    When two scheduler worker sessions select due schedules concurrently before either commits,
    only one execution must succeed, debiting the account exactly once and creating exactly one transfer and event.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from backend.app.database import Base
    from backend.app.models import Account, RecurringSchedule, Transfer, DomainEvent
    from backend.app.services.account_service import seed_initial_data
    from backend.app.services.migration_service import run_stage4_event_sourcing_migration
    from backend.app.services import audit_service
    import threading

    db_path = tmp_path / "concurrent_sched_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    audit_service.set_session_factory(Session)

    # 1. Seed data and run migration
    init_db = Session()
    try:
        seed_initial_data(init_db)
        run_stage4_event_sourcing_migration(init_db)

        # Create an active due schedule ($100.00)
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)
        sched = RecurringSchedule(
            user_id=1,
            transfer_type="internal",
            from_account_id=1,
            to_account_id=2,
            amount=Decimal("100.00"),
            currency="USD",
            frequency="monthly",
            next_execution_date=past_date,
            status="active",
        )
        init_db.add(sched)
        init_db.commit()
        sched_id = sched.id
    finally:
        init_db.close()

    # 2. Launch two concurrent worker threads synchronized by a barrier
    barrier = threading.Barrier(2)
    worker_results = []
    worker_errors = []

    def worker():
        session = Session()
        try:
            barrier.wait()
            res = execute_due_recurring_schedules(session, datetime.now(timezone.utc))
            worker_results.append(res)
        except Exception as e:
            worker_errors.append(e)
        finally:
            session.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # 3. Verify exactly-once financial effects
    verify_session = Session()
    try:
        from_acc = verify_session.query(Account).filter(Account.id == 1).first()
        to_acc = verify_session.query(Account).filter(Account.id == 2).first()

        transfers = verify_session.query(Transfer).filter(Transfer.transfer_type == "internal").all()
        events = verify_session.query(DomainEvent).filter(DomainEvent.event_type == "InternalTransferCompleted").all()

        # Balance should be debited exactly once: 2500 - 100 = 2400
        assert from_acc.balance == Decimal("2400.00"), f"Balance was debited multiple times: {from_acc.balance}"
        assert to_acc.balance == Decimal("10100.00"), f"Destination balance was credited multiple times: {to_acc.balance}"
        assert len(transfers) == 1, f"Expected 1 transfer, but found {len(transfers)}"
        assert len(events) == 1, f"Expected 1 domain event, but found {len(events)}"
    finally:
        verify_session.close()
        engine.dispose()


def test_scheduler_repeated_ticks_and_recovery_after_failure(client, db_session):
    """
    Verifies that:
    1. Repeated scheduler ticks do not re-execute or duplicate transfers.
    2. A schedule that fails due to insufficient funds advances its due date and failure count.
    3. When funds become available on the next due date, the scheduler successfully recovers and executes.
    4. Schedules never become permanently stuck.
    """
    now = datetime.now(timezone.utc)
    past_date = now - timedelta(hours=2)

    # 1. Create a schedule of $2,400.00
    create_resp = client.post(
        "/api/recurring",
        json={
            "transfer_type": "internal",
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": "2400.00",
            "frequency": "daily",
            "start_date": past_date.isoformat(),
            "pin": "1234",
        },
    )
    assert create_resp.status_code == 201
    sched_id = create_resp.json()["id"]

    # Reduce balance so funds are insufficient ($2,000 < $2,400)
    chk = client.get("/api/accounts/1").json()
    sav = client.get("/api/accounts/2").json()
    client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": "500.00",
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
            "description": "Spend funds for recovery test",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    # 2. First tick: fails with insufficient funds
    tick1_res = execute_due_recurring_schedules(db_session, now)
    assert len(tick1_res) == 1
    assert tick1_res[0]["status"] == "failed"

    sched_state = client.get(f"/api/recurring").json()
    sched = next(s for s in sched_state if s["id"] == sched_id)
    assert sched["status"] == "active"
    sched_db = db_session.query(RecurringSchedule).filter(RecurringSchedule.id == sched_id).first()
    assert sched_db.failure_count == 1
    next_due_1 = datetime.fromisoformat(sched["next_execution_date"])
    if next_due_1.tzinfo is None:
        next_due_1 = next_due_1.replace(tzinfo=timezone.utc)
    assert next_due_1 > now

    # 3. Repeated tick immediately runs: 0 due schedules, no duplicate failure
    tick_repeat = execute_due_recurring_schedules(db_session, now)
    assert len(tick_repeat) == 0

    # 4. Deposit funds back so balance is sufficient ($2,000 + $1,000 = $3,000 >= $2,400)
    chk_cur = client.get("/api/accounts/1").json()
    sav_cur = client.get("/api/accounts/2").json()
    client.post(
        "/api/transfers",
        json={
            "from_account_id": sav_cur["id"],
            "to_account_id": chk_cur["id"],
            "amount": "1000.00",
            "expected_from_version": sav_cur["version"],
            "expected_to_version": chk_cur["version"],
            "description": "Refund balance for recovery",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    # 5. Advance time to next_due_1 and run scheduler: schedule recovers and executes successfully!
    target_time_recovered = next_due_1 + timedelta(seconds=10)
    tick2_res = execute_due_recurring_schedules(db_session, target_time_recovered)
    assert len(tick2_res) == 1
    assert tick2_res[0]["status"] == "success"

    # Schedule is healthy, next date advanced, failure count not stuck
    sched_recovered = client.get(f"/api/recurring").json()
    sched_obj = next(s for s in sched_recovered if s["id"] == sched_id)
    assert sched_obj["status"] == "active"
    next_due_2 = datetime.fromisoformat(sched_obj["next_execution_date"])
    if next_due_2.tzinfo is None:
        next_due_2 = next_due_2.replace(tzinfo=timezone.utc)
    assert next_due_2 > next_due_1

    # 6. Immediate repeat tick at same target time: 0 executions, no duplicate
    tick2_repeat = execute_due_recurring_schedules(db_session, target_time_recovered)
    assert len(tick2_repeat) == 0


