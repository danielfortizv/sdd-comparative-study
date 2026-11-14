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
    assert acc_before["balance"] == 2500.00

    # Execute ACH transfer of $500.00 (no PIN required)
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "beneficiary_id": ben_id,
            "amount": 500.00,
            "description": "Monthly rent payment",
        },
    )
    assert ach_resp.status_code == 200
    data = ach_resp.json()
    assert data["status"] == "pending"
    assert data["amount"] == 500.00
    assert data["recipient_name"] == "Robert Smith"
    assert data["routing_number"] == "111222333"
    assert data["bank_name"] == "Wells Fargo"

    # Balance debited immediately
    acc_after = client.get("/api/accounts/1").json()
    assert acc_after["balance"] == 2000.00

    # Pending transaction recorded
    tx_resp = client.get("/api/transactions?account_id=1")
    latest_tx = tx_resp.json()[0]
    assert latest_tx["amount"] == 500.00
    assert latest_tx["transaction_type"] == "debit"
    assert latest_tx["status"] == "pending"
    assert "ACH-" in latest_tx["reference"]


def test_ach_transfer_ad_hoc_with_save_beneficiary(client):
    """Test ad-hoc ACH transfer and verify save_beneficiary=True creates a new beneficiary."""
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 250.00,
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
    # Transfer without PIN -> 428
    resp_428 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,  # Savings has $10,000
            "amount": 1500.00,
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
            "recipient_name": "Landlord LLC",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Chase Bank",
            "pin": "1234",
        },
    )
    assert ok_pin.status_code == 200
    assert ok_pin.json()["status"] == "pending"


def test_ach_transfer_validation_errors(client):
    """Test validation errors for insufficient funds, bad routing numbers, and missing beneficiaries."""
    # Insufficient funds
    insuf = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,  # Checking has $2,500
            "amount": 9999.00,
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
            "beneficiary_id": 99999,
        },
    )
    assert bad_ben.status_code == 404


def test_ach_settlement_and_failure_refund(client, db_session):
    """Test settling pending ACH transfers and simulated failure with refund."""
    # 1. Create ACH transfer
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 300.00,
            "recipient_name": "Vendor Corp",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Bank of America",
        },
    )
    trf_id = ach_resp.json()["id"]
    assert client.get("/api/accounts/1").json()["balance"] == 2200.00

    # Settle transfer
    settled = process_pending_ach_transfers(db_session)
    assert any(t.id == trf_id and t.status == "settled" for t in settled)

    # 2. Create another ACH transfer and simulate failure/refund
    ach_resp2 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 1,
            "amount": 200.00,
            "recipient_name": "Failing Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Fake Bank",
        },
    )
    trf_id2 = ach_resp2.json()["id"]
    assert client.get("/api/accounts/1").json()["balance"] == 2000.00

    # Fail the transfer
    failed_trf = fail_ach_transfer(db_session, trf_id2, reason="Invalid account at recipient bank")
    assert failed_trf.status == "failed"

    # Balance refunded back to 2200.00
    assert client.get("/api/accounts/1").json()["balance"] == 2200.00


def test_ach_transfer_limits_enforcement(client):
    """Test that dynamic per-transaction and daily limits apply to ACH transfers."""
    # Configure per-transaction $500.00, daily $1,000.00
    limits_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": 500.00, "daily_limit": 1000.00},
    )
    assert limits_resp.status_code == 200
    assert limits_resp.json()["per_transaction_limit"] == 500.00
    assert limits_resp.json()["daily_limit"] == 1000.00

    # 1. ACH transfer exceeding per-transaction limit ($600 > $500) fails with HTTP 400
    resp_over_tx = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 600.00,
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_over_tx.status_code == 400
    assert "exceeds per-transaction limit" in resp_over_tx.json()["detail"].lower()

    # 2. First successful ACH transfer within cumulative limit ($400 <= $500 per-tx, cumulative $400 <= $1,000)
    resp_tx1 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 400.00,
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx1.status_code == 200
    assert resp_tx1.json()["status"] == "pending"

    limits_after_tx1 = client.get("/api/limits").json()
    assert limits_after_tx1["current_daily_total"] == 400.00
    assert limits_after_tx1["remaining_daily_limit"] == 600.00

    # 3. Second successful ACH transfer within cumulative limit ($300 <= $500 per-tx, cumulative $700 <= $1,000)
    resp_tx2 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 300.00,
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx2.status_code == 200
    assert resp_tx2.json()["status"] == "pending"

    limits_after_tx2 = client.get("/api/limits").json()
    assert limits_after_tx2["current_daily_total"] == 700.00
    assert limits_after_tx2["remaining_daily_limit"] == 300.00

    # 4. ACH transfer that exceeds daily limit ($400 <= $500 per-tx, but $700 + $400 = $1,100 > $1,000) fails with HTTP 400
    resp_over_daily = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 400.00,
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
    assert limits_after_rejection["current_daily_total"] == 700.00
    assert limits_after_rejection["remaining_daily_limit"] == 300.00

    # 5. ACH transfer that reaches daily limit exactly ($300 fills remaining $300 to reach $1,000)
    resp_tx3 = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 300.00,
            "recipient_name": "Test Payee",
            "routing_number": "123456789",
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp_tx3.status_code == 200
    assert resp_tx3.json()["status"] == "pending"

    limits_final = client.get("/api/limits").json()
    assert limits_final["current_daily_total"] == 1000.00
    assert limits_final["remaining_daily_limit"] == 0.00

    # 6. Any further transfer when daily limit is exhausted fails with HTTP 400
    resp_exhausted = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": 2,
            "amount": 10.00,
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
        json={"from_account_id": 1, "amount": 0.00, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_zero.status_code == 422

    # Amount > 2 decimals
    resp_dec = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.555, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_dec.status_code == 422

    # Non-existent from_account_id
    resp_acc = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 99999, "amount": 10.00, "recipient_name": "A", "routing_number": "123456789", "account_number": "123456", "bank_name": "B"},
    )
    assert resp_acc.status_code == 404

    # Missing ad-hoc details
    resp_missing = client.post(
        "/api/transfers/ach",
        json={"from_account_id": 1, "amount": 10.00},
    )
    assert resp_missing.status_code == 422

    # Account number too short (< 4 digits)
    resp_short = client.post(
        "/api/beneficiaries",
        json={"name": "Alice", "routing_number": "123456789", "account_number": "123", "bank_name": "Test Bank"},
    )
    assert resp_short.status_code == 422

