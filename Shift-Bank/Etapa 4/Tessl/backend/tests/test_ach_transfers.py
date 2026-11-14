import pytest
from backend.app.services.transfer_service import process_pending_ach_transfers, fail_ach_transfer


def test_beneficiary_lifecycle(client):
    """Test creating, listing, and deleting external beneficiaries."""
    # List initially empty
    resp = client.get("/api/beneficiaries")
    assert resp.status_code == 200
    assert resp.json() == []

    # Validation errors
    bad_resp = client.post(
        "/api/beneficiaries",
        json={"name": "Alice", "routing_number": "123", "account_number": "123456", "bank_name": "Test Bank"},
    )
    assert bad_resp.status_code == 422

    bad_resp2 = client.post(
        "/api/beneficiaries",
        json={"name": "   ", "routing_number": "123456789", "account_number": "123456", "bank_name": "Test Bank"},
    )
    assert bad_resp2.status_code == 422

    # Create valid beneficiary
    create_resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Jane Doe",
            "routing_number": "123456789",
            "account_number": "9876543210",
            "bank_name": "Chase Bank",
        },
    )
    assert create_resp.status_code == 201
    ben = create_resp.json()
    assert ben["name"] == "Jane Doe"
    assert ben["routing_number"] == "123456789"
    ben_id = ben["id"]

    # List now contains beneficiary
    list_resp = client.get("/api/beneficiaries")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Delete beneficiary
    del_resp = client.delete(f"/api/beneficiaries/{ben_id}")
    assert del_resp.status_code == 200

    # Delete non-existent
    del_404 = client.delete(f"/api/beneficiaries/{ben_id}")
    assert del_404.status_code == 404


def test_ach_transfer_with_saved_beneficiary_under_threshold(client):
    """Test initiating an ACH transfer using saved beneficiary for amount <= $1,000."""
    # Create beneficiary
    ben_resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Robert Smith",
            "routing_number": "111222333",
            "account_number": "555444333222",
            "bank_name": "Wells Fargo",
        },
    )
    ben_id = ben_resp.json()["id"]

    # Source checking balance is $2,500.00
    acc_before = client.get("/api/accounts/1").json()
    assert acc_before["balance"] == "2500.00"

    # Execute ACH transfer of $500.00 (no PIN required)
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "beneficiary_id": ben_id,
            "amount": 500.00,
            "expected_from_version": acc_before["version"],
            "description": "Monthly rent payment",
        },
    )
    assert ach_resp.status_code == 200
    data = ach_resp.json()
    assert data["status"] == "pending"
    assert data["amount"] == "500.00"
    assert data["recipient_name"] == "Robert Smith"
    assert data["routing_number"] == "111222333"
    assert data["bank_name"] == "Wells Fargo"

    # Balance debited immediately and version incremented
    acc_after = client.get("/api/accounts/1").json()
    assert acc_after["balance"] == "2000.00"
    assert acc_after["version"] == acc_before["version"] + 1

    # Pending transaction recorded
    tx_resp = client.get("/api/transactions?account_id=1")
    latest_tx = tx_resp.json()[0]
    assert latest_tx["amount"] == "500.00"
    assert latest_tx["transaction_type"] == "debit"
    assert latest_tx["status"] == "pending"
    assert "ACH-" in latest_tx["reference"]


def test_ach_transfer_ad_hoc_with_save_beneficiary(client):
    """Test ad-hoc ACH transfer and verify save_beneficiary=True creates a new beneficiary."""
    acc_before = client.get("/api/accounts/1").json()
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 250.00,
            "expected_from_version": acc_before["version"],
            "recipient_name": "Acme Electric Co",
            "routing_number": "987654321",
            "account_number": "1122334455",
            "bank_name": "CitiBank",
            "save_beneficiary": True,
        },
    )
    assert ach_resp.status_code == 200
    data = ach_resp.json()
    assert data["status"] == "pending"
    assert data["beneficiary_id"] is not None

    # Check that beneficiary is now saved
    bens = client.get("/api/beneficiaries").json()
    saved = [b for b in bens if b["name"] == "Acme Electric Co"]
    assert len(saved) == 1
    assert saved[0]["routing_number"] == "987654321"


def test_ach_transfer_mfa_pin_required(client):
    """Test that ACH transfers > $1,000 require Security PIN."""
    acc = client.get("/api/accounts/2").json()
    # Transfer without PIN -> 428
    resp_428 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,  # Savings has $10,000
            "amount": 1500.00,
            "expected_from_version": acc["version"],
            "recipient_name": "Landlord LLC",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Chase Bank",
        },
    )
    assert resp_428.status_code == 428
    assert resp_428.json()["detail"] == "MFA_REQUIRED"

    # Transfer with invalid PIN -> 400
    bad_pin = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 1500.00,
            "expected_from_version": acc["version"],
            "recipient_name": "Landlord LLC",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Chase Bank",
            "pin": "0000",
        },
    )
    assert bad_pin.status_code == 400

    # Transfer with correct PIN ('1234') -> 200
    ok_pin = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 1500.00,
            "expected_from_version": acc["version"],
            "recipient_name": "Landlord LLC",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Chase Bank",
            "pin": "1234",
        },
    )
    assert ok_pin.status_code == 200
    assert ok_pin.json()["status"] == "pending"


def test_ach_transfer_with_save_beneficiary_and_incorrect_pin_does_not_save_beneficiary(client, db_session):
    """When an ACH transfer > $1,000 with save_beneficiary=True fails MFA, no beneficiary or transfer is created,
    and source account balance is unchanged, while failed attempt is recorded."""
    from sqlalchemy import text

    # Initial balance and version of account 2 (Savings has $10,000)
    init_balance = db_session.execute(text("SELECT balance FROM accounts WHERE id = 2")).fetchone()[0]
    acc2 = client.get("/api/accounts/2").json()

    resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 1500.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Unsaved Vendor",
            "routing_number": "123456789",
            "account_number": "9876543210",
            "bank_name": "Test Bank",
            "save_beneficiary": True,
            "pin": "0000",  # Incorrect PIN
        },
    )
    assert resp.status_code == 400
    assert "Invalid Security PIN" in resp.json()["detail"]

    # 1. Beneficiary must NOT exist in the database
    bens = db_session.execute(
        text("SELECT count(*) FROM beneficiaries WHERE name = 'Unsaved Vendor'")
    ).fetchone()[0]
    assert bens == 0

    # 2. Transfer must NOT exist in the database
    transfers = db_session.execute(
        text("SELECT count(*) FROM transfers WHERE recipient_name = 'Unsaved Vendor'")
    ).fetchone()[0]
    assert transfers == 0

    # 3. Source account balance must NOT be debited
    final_balance = db_session.execute(text("SELECT balance FROM accounts WHERE id = 2")).fetchone()[0]
    assert final_balance == init_balance

    # 4. MFA failure must be durably committed with remaining attempts = 2
    mfa_state = db_session.execute(text("SELECT failed_attempts FROM mfa_states WHERE user_id = 1")).fetchone()
    assert mfa_state is not None
    assert mfa_state[0] == 1

    # 5. Audit log must contain mfa_attempt_failed and transfer_ach_initiated (FAILURE), but NO beneficiary_created
    mfa_audit = db_session.execute(
        text("SELECT count(*) FROM audit_logs WHERE event_type = 'mfa_attempt_failed' AND status = 'FAILURE'")
    ).fetchone()[0]
    assert mfa_audit >= 1

    ben_audit = db_session.execute(
        text("SELECT count(*) FROM audit_logs WHERE event_type = 'beneficiary_created'")
    ).fetchone()[0]
    assert ben_audit == 0


def test_ach_transfer_validation_errors(client):
    """Test validation errors for insufficient funds, bad routing numbers, and missing beneficiaries."""
    acc = client.get("/api/accounts/1").json()
    # Insufficient funds
    insuf = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,  # Checking has $2,500
            "amount": 9999.00,
            "expected_from_version": acc["version"],
            "recipient_name": "Someone",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Bank",
        },
    )
    assert insuf.status_code == 400
    assert "Insufficient funds" in insuf.json()["detail"]

    # Invalid routing number (8 digits)
    bad_route = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 100.00,
            "expected_from_version": acc["version"],
            "recipient_name": "Someone",
            "routing_number": "12345678",
            "account_number": "12345678",
            "bank_name": "Bank",
        },
    )
    assert bad_route.status_code == 422

    # Non-existent beneficiary ID
    bad_ben = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 100.00,
            "expected_from_version": acc["version"],
            "beneficiary_id": 99999,
        },
    )
    assert bad_ben.status_code == 404


def test_ach_settlement_and_failure_refund(client, db_session):
    """Test settling pending ACH transfers and simulated failure with refund."""
    acc1 = client.get("/api/accounts/1").json()
    # 1. Create ACH transfer
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 300.00,
            "expected_from_version": acc1["version"],
            "recipient_name": "Vendor Corp",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Bank of America",
        },
    )
    trf_id = ach_resp.json()["id"]
    assert client.get("/api/accounts/1").json()["balance"] == "2200.00"

    # Settle transfer
    settled = process_pending_ach_transfers(db_session)
    assert any(t.id == trf_id and t.status == "settled" for t in settled)

    # 2. Create another ACH transfer and simulate failure/refund
    acc1_v2 = client.get("/api/accounts/1").json()
    ach_resp2 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 200.00,
            "expected_from_version": acc1_v2["version"],
            "recipient_name": "Failing Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Fake Bank",
        },
    )
    trf_id2 = ach_resp2.json()["id"]
    assert client.get("/api/accounts/1").json()["balance"] == "2000.00"

    # Fail the transfer
    failed_trf = fail_ach_transfer(db_session, trf_id2, reason="Invalid account at recipient bank")
    assert failed_trf.status == "failed"

    # Balance refunded back to 2200.00
    assert client.get("/api/accounts/1").json()["balance"] == "2200.00"


def test_ach_transfer_limits_enforcement(client):
    """Test that dynamic per-transaction and daily limits apply to ACH transfers."""
    # Configure per-transaction $500.00, daily $1,000.00
    limits_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": 500.00, "daily_limit": 1000.00},
    )
    assert limits_resp.status_code == 200
    assert limits_resp.json()["per_transaction_limit"] == "500.00"
    assert limits_resp.json()["daily_limit"] == "1000.00"

    # 1. ACH transfer exceeding per-transaction limit ($600 > $500) fails with HTTP 400
    acc2 = client.get("/api/accounts/2").json()
    resp_over_tx = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 600.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_over_tx.status_code == 400
    assert "exceeds per-transaction limit" in resp_over_tx.json()["detail"].lower()

    # 2. First successful ACH transfer within cumulative limit ($400 <= $500 per-tx, cumulative $400 <= $1,000)
    acc2 = client.get("/api/accounts/2").json()
    resp_tx1 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 400.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx1.status_code == 200
    assert resp_tx1.json()["status"] == "pending"

    limits_after_tx1 = client.get("/api/limits").json()
    assert limits_after_tx1["current_daily_total"] == "400.00"
    assert limits_after_tx1["remaining_daily_limit"] == "600.00"

    # 3. Second successful ACH transfer within cumulative limit ($300 <= $500 per-tx, cumulative $700 <= $1,000)
    acc2 = client.get("/api/accounts/2").json()
    resp_tx2 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 300.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx2.status_code == 200
    assert resp_tx2.json()["status"] == "pending"

    limits_after_tx2 = client.get("/api/limits").json()
    assert limits_after_tx2["current_daily_total"] == "700.00"
    assert limits_after_tx2["remaining_daily_limit"] == "300.00"

    # 4. ACH transfer that exceeds daily limit ($400 <= $500 per-tx, but $700 + $400 = $1,100 > $1,000) fails with HTTP 400
    acc2 = client.get("/api/accounts/2").json()
    resp_over_daily = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 400.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_over_daily.status_code == 400
    assert "would exceed daily limit" in resp_over_daily.json()["detail"].lower()

    # Verify cumulative total is unchanged after rejection
    limits_after_rejection = client.get("/api/limits").json()
    assert limits_after_rejection["current_daily_total"] == "700.00"
    assert limits_after_rejection["remaining_daily_limit"] == "300.00"

    # 5. ACH transfer that reaches daily limit exactly ($300 fills remaining $300 to reach $1,000)
    acc2 = client.get("/api/accounts/2").json()
    resp_tx3 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 300.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx3.status_code == 200
    assert resp_tx3.json()["status"] == "pending"

    limits_final = client.get("/api/limits").json()
    assert limits_final["current_daily_total"] == "1000.00"
    assert limits_final["remaining_daily_limit"] == "0.00"

    # 6. Any further transfer when daily limit is exhausted fails with HTTP 400
    acc2 = client.get("/api/accounts/2").json()
    resp_exhausted = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 10.00,
            "expected_from_version": acc2["version"],
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_exhausted.status_code == 400
    assert "would exceed daily limit" in resp_exhausted.json()["detail"].lower()


def test_ach_transfer_additional_validation_errors(client):
    """Test validation errors for ACH transfers and beneficiaries."""
    # Amount <= 0
    resp_zero = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 0.00, "expected_from_version": 1, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_zero.status_code == 422

    # Amount > 2 decimals
    resp_dec = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.555, "expected_from_version": 1, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_dec.status_code == 422

    # Non-existent from_account_id
    resp_acc = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 99999, "amount": 10.00, "expected_from_version": 1, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_acc.status_code == 404

    # Missing expected_from_version -> 422 (D-14)
    resp_missing_ver = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.00, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_missing_ver.status_code == 422

    # Negative expected_from_version -> 422 (D-14)
    resp_neg_ver = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.00, "expected_from_version": -1, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_neg_ver.status_code == 422

    # Missing ad-hoc details
    resp_missing = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.00, "expected_from_version": 1},
    )
    assert resp_missing.status_code == 422

    # Account number too short (< 4 digits)
    resp_short = client.post(
        "/api/beneficiaries",
        json={"name": "Alice", "routing_number": "123456789", "account_number": "123", "bank_name": "Test Bank"},
    )
    assert resp_short.status_code == 422


def test_ach_transfer_optimistic_concurrency_conflict(client):
    """Test that stale source account version in ACH transfer fails with HTTP 409 ACCOUNT_VERSION_CONFLICT (D-14)."""
    import uuid
    acc = client.get("/api/accounts/1").json()
    stale_payload = {
        "from_account_id": 1,
        "amount": 50.00,
        "expected_from_version": acc["version"] + 99,
        "recipient_name": "Vendor LLC",
        "routing_number": "123456789",
        "account_number": "12345678",
        "bank_name": "Test Bank",
    }
    response = client.post(
        "/api/transfers/ach",
        json=stale_payload,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert "ACCOUNT_VERSION_CONFLICT" in response.text


def test_ach_transfer_idempotency_before_version_check(client):
    """Test that idempotent replay returns original committed response even after account version has advanced (D-14)."""
    import uuid
    acc_before = client.get("/api/accounts/1").json()
    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": 1,
        "amount": 25.00,
        "expected_from_version": acc_before["version"],
        "recipient_name": "Vendor LLC",
        "routing_number": "123456789",
        "account_number": "12345678",
        "bank_name": "Test Bank",
    }
    # Initial execution
    resp1 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert resp1.status_code == 200
    orig_data = resp1.json()

    # Replay with same key and same payload (which has the older expected_from_version):
    # Idempotency check happens BEFORE version validation, so it returns 200 with the original data
    resp2 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == orig_data["id"]


def test_ach_failure_refund_single_version_increment_and_projection_consistency(client, db_session):
    """
    Regression test for D-09/D-06/D-14:
    fail_ach_transfer must:
    1. Refund the debited amount exactly once.
    2. Increment the source account version by exactly +1 (not +2).
    3. Maintain exact agreement between the persisted account version and the CQRS event fold.
    4. Emit exactly one AchTransferFailed domain event with matching from_account_version.
    5. Be idempotent: repeated fail_ach_transfer calls must not produce duplicate refunds or extra version increments.
    """
    import json
    import uuid
    from decimal import Decimal
    from backend.app.models import DomainEvent, Account
    from backend.app.services.projection_service import verify_projections_integrity, rebuild_projections

    # 1. Create a valid pending ACH transfer
    acc_initial = client.get("/api/accounts/1").json()
    init_version = acc_initial["version"]
    init_balance = Decimal(acc_initial["balance"])
    transfer_amount = Decimal("200.00")

    resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": str(transfer_amount),
            "expected_from_version": init_version,
            "recipient_name": "Supplier Inc",
            "routing_number": "123456789",
            "account_number": "987654321",
            "bank_name": "Supplier Bank",
            "description": "Invoice 101",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 200
    transfer_id = resp.json()["id"]

    # Account state after pending initiation:
    # Version should have incremented by +1 (init_version + 1), balance should be debited
    acc_pending = client.get("/api/accounts/1").json()
    version_before_fail = acc_pending["version"]
    balance_before_fail = Decimal(acc_pending["balance"])
    assert version_before_fail == init_version + 1
    assert balance_before_fail == init_balance - transfer_amount

    # Capture event count before failure
    events_before = db_session.query(DomainEvent).filter(DomainEvent.event_type == "AchTransferFailed").count()

    # 2. Execute fail_ach_transfer
    failed_trf = fail_ach_transfer(db_session, transfer_id, reason="Simulated network rejection")
    assert failed_trf is not None
    assert failed_trf.status == "failed"

    # 3. Assert exactly one refund and one version increment
    acc_post_fail = client.get("/api/accounts/1").json()
    version_after_fail = acc_post_fail["version"]
    balance_after_fail = Decimal(acc_post_fail["balance"])

    # Balance must be refunded exactly once (restoring to init_balance)
    assert balance_after_fail == init_balance
    assert balance_after_fail == balance_before_fail + transfer_amount

    # Version must increment by exactly +1 from version_before_fail (NOT +2)
    assert version_after_fail == version_before_fail + 1

    # 4. Confirm exactly one AchTransferFailed domain event was recorded
    fail_events = (
        db_session.query(DomainEvent)
        .filter(DomainEvent.event_type == "AchTransferFailed")
        .all()
    )
    assert len(fail_events) == events_before + 1
    event_payload = json.loads(fail_events[-1].payload)
    assert int(event_payload["from_account_version"]) == version_after_fail

    # 5. Verify persisted account matches event-derived CQRS projection fold
    assert verify_projections_integrity(db_session) is True

    # Rebuild projections from scratch to confirm deterministic replay matches
    rebuild_res = rebuild_projections(db_session)
    db_session.commit()
    assert rebuild_res["status"] == "success"
    assert verify_projections_integrity(db_session) is True

    acc_rebuilt = client.get("/api/accounts/1").json()
    assert acc_rebuilt["version"] == version_after_fail
    assert Decimal(acc_rebuilt["balance"]) == balance_after_fail

    # 6. Idempotency of terminal state: repeated fail_ach_transfer has no effect
    second_fail = fail_ach_transfer(db_session, transfer_id, reason="Repeated failure call")
    assert second_fail.status == "failed"

    acc_terminal = client.get("/api/accounts/1").json()
    assert acc_terminal["version"] == version_after_fail
    assert Decimal(acc_terminal["balance"]) == balance_after_fail

    events_after_second = db_session.query(DomainEvent).filter(DomainEvent.event_type == "AchTransferFailed").count()
    assert events_after_second == events_before + 1


def test_concurrent_ach_transfers_same_version_conflict_d14(tmp_path, monkeypatch):
    """
    D-14 Concurrency Test for ACH Transfers:
    When two simultaneous ACH transfer requests compete using the same expected account version,
    exactly one succeeds (200), and the competing request is rejected with HTTP 409 ACCOUNT_VERSION_CONFLICT.
    """
    import uuid
    import threading
    from decimal import Decimal
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app.database import Base
    from backend.app.models import Account, Transfer, DomainEvent
    from backend.app.schemas import AchTransferRequest
    from backend.app.services.account_service import seed_initial_data
    from backend.app.services.migration_service import run_stage4_event_sourcing_migration
    from backend.app.services import transfer_service, audit_service, event_store
    from backend.app.services.projection_service import verify_projections_integrity

    db_path = tmp_path / "concurrent_ach_d14.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    audit_service.set_session_factory(Session)

    init_db = Session()
    try:
        seed_initial_data(init_db)
        run_stage4_event_sourcing_migration(init_db)
    finally:
        init_db.close()

    barrier = threading.Barrier(2)
    original_append = transfer_service.append_domain_event

    def synchronized_append(*args, **kwargs):
        barrier.wait()
        return original_append(*args, **kwargs)

    monkeypatch.setattr(transfer_service, "append_domain_event", synchronized_append)

    results = []
    errors = []

    def worker_ach(amt_str: str, key_str: str):
        db = Session()
        try:
            req = AchTransferRequest(
                from_account_id=1,
                amount=amt_str,
                expected_from_version=1,
                recipient_name="Vendor X",
                routing_number="123456789",
                account_number="987654321",
                bank_name="Vendor Bank",
                description=f"Concurrent ACH of {amt_str}",
            )
            res = transfer_service.execute_ach_transfer(
                db=db,
                user_id=1,
                request=req,
                idempotency_key=key_str,
            )
            results.append({"status": 200, "transfer_id": res.id})
        except Exception as e:
            errors.append(e)
        finally:
            db.close()

    t1 = threading.Thread(target=worker_ach, args=("15.00", str(uuid.uuid4())))
    t2 = threading.Thread(target=worker_ach, args=("25.00", str(uuid.uuid4())))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 1, f"Expected exactly 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected exactly 1 error, got {len(errors)}"
    err = errors[0]
    from fastapi import HTTPException
    assert isinstance(err, HTTPException)
    assert err.status_code == 409
    err_code = err.detail.get("code") if isinstance(err.detail, dict) else str(err.detail)
    assert err_code == "ACCOUNT_VERSION_CONFLICT"

    verify_db = Session()
    try:
        assert verify_projections_integrity(verify_db) is True
    finally:
        verify_db.close()
        engine.dispose()



