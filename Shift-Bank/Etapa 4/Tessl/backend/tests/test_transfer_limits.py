import uuid


def test_limits_query_and_defaults(client):
    """Test retrieving default transfer limits."""
    resp = client.get("/api/limits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_transaction_limit"] == "5000.00"
    assert data["daily_limit"] == "10000.00"
    assert data["current_daily_total"] == "0.00"
    assert data["remaining_daily_limit"] == "10000.00"
    assert data["reference_currency"] == "USD"


def test_limits_update_validation(client):
    """Test updating limits with validation rules."""
    # Update valid limits
    update_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": "3000.00", "daily_limit": "6000.00"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["per_transaction_limit"] == "3000.00"
    assert data["daily_limit"] == "6000.00"
    assert data["reference_currency"] == "USD"

    # per_transaction_limit > daily_limit -> 400
    bad_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": "7000.00", "daily_limit": "5000.00"},
    )
    assert bad_resp.status_code == 400
    assert "cannot exceed" in bad_resp.text.lower()

    # negative limit -> 422
    neg_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": "-100.00", "daily_limit": "5000.00"},
    )
    assert neg_resp.status_code == 422


def test_limits_enforcement_per_transaction_and_daily(client):
    """Test that transfer limits act as a hard cap on internal and ACH transfers."""
    # Configure per-transaction limit $1,500 and daily limit $2,000
    limit_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": "1500.00", "daily_limit": "2000.00"},
    )
    assert limit_resp.status_code == 200

    acc_sav = client.get("/api/accounts/2").json()  # Savings has $10,000.00
    acc_chk = client.get("/api/accounts/1").json()

    # 1. Single transfer > $1,500 should fail with HTTP 400 even if PIN is provided
    single_over = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc_sav["id"],
            "to_account_id": acc_chk["id"],
            "amount": "1600.00",
            "expected_from_version": acc_sav["version"],
            "expected_to_version": acc_chk["version"],
            "pin": "1234",
            "description": "Exceed single limit",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert single_over.status_code == 400
    assert "exceeds per-transaction limit" in single_over.text

    # 2. Transfer $1,200 (<= $1,500, requires PIN because > $1,000)
    tx1 = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc_sav["id"],
            "to_account_id": acc_chk["id"],
            "amount": "1200.00",
            "expected_from_version": acc_sav["version"],
            "expected_to_version": acc_chk["version"],
            "pin": "1234",
            "description": "Transfer 1200 within limits",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert tx1.status_code == 200

    # Check updated daily consumption: 1,200 used, 800 remaining
    limits_info = client.get("/api/limits").json()
    assert limits_info["current_daily_total"] == "1200.00"
    assert limits_info["remaining_daily_limit"] == "800.00"

    # Refresh versions after tx1
    acc_sav = client.get("/api/accounts/2").json()
    acc_chk = client.get("/api/accounts/1").json()

    # 3. Second transfer of $900 would exceed daily limit ($1200 + $900 = $2100 > $2000)
    tx2 = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc_sav["id"],
            "to_account_id": acc_chk["id"],
            "amount": "900.00",
            "expected_from_version": acc_sav["version"],
            "expected_to_version": acc_chk["version"],
            "description": "Transfer 900 exceeding daily",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert tx2.status_code == 400
    assert "would exceed daily limit" in tx2.text

    # 4. Transfer of $800 succeeds (fills daily limit exactly: 1200 + 800 = 2000)
    tx3 = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc_sav["id"],
            "to_account_id": acc_chk["id"],
            "amount": "800.00",
            "expected_from_version": acc_sav["version"],
            "expected_to_version": acc_chk["version"],
            "description": "Transfer 800 filling daily",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert tx3.status_code == 200

    limits_final = client.get("/api/limits").json()
    assert limits_final["current_daily_total"] == "2000.00"
    assert limits_final["remaining_daily_limit"] == "0.00"
