def test_limits_query_and_defaults(client):
    """Test retrieving default transfer limits."""
    resp = client.get("/api/limits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_transaction_limit"] == 5000.00
    assert data["daily_limit"] == 10000.00
    assert data["current_daily_total"] == 0.00
    assert data["remaining_daily_limit"] == 10000.00


def test_limits_update_validation(client):
    """Test updating limits with validation rules."""
    # Update valid limits
    update_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": 3000.00, "daily_limit": 6000.00},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["per_transaction_limit"] == 3000.00
    assert data["daily_limit"] == 6000.00

    # per_transaction_limit > daily_limit -> 400
    bad_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": 7000.00, "daily_limit": 5000.00},
    )
    assert bad_resp.status_code == 400
    assert "cannot exceed" in bad_resp.json()["detail"].lower()

    # negative limit -> 422
    neg_resp = client.put(
        "/api/limits",
        json={"per_transaction_limit": -100.00, "daily_limit": 5000.00},
    )
    assert neg_resp.status_code == 422


def test_limits_enforcement_per_transaction_and_daily(client):
    """Test that transfer limits act as a hard cap on internal and ACH transfers."""
    # Configure per-transaction limit $1,500 and daily limit $2,000
    client.put(
        "/api/limits",
        json={"per_transaction_limit": 1500.00, "daily_limit": 2000.00},
    )

    # 1. Single transfer > $1,500 should fail with HTTP 400 even if PIN is provided
    single_over = client.post(
        "/api/transfers",
        json={
            "from_account_id": 2,  # Savings has $10,000
            "to_account_id": 1,
            "amount": 1600.00,
            "pin": "1234",
        },
    )
    assert single_over.status_code == 400
    assert "exceeds per-transaction limit" in single_over.json()["detail"]

    # 2. Transfer $1,200 (<= $1,500, requires PIN because > $1,000)
    tx1 = client.post(
        "/api/transfers",
        json={
            "from_account_id": 2,
            "to_account_id": 1,
            "amount": 1200.00,
            "pin": "1234",
        },
    )
    assert tx1.status_code == 200

    # Check updated daily consumption: 1,200 used, 800 remaining
    limits_info = client.get("/api/limits").json()
    assert limits_info["current_daily_total"] == 1200.00
    assert limits_info["remaining_daily_limit"] == 800.00

    # 3. Second transfer of $900 would exceed daily limit ($1200 + $900 = $2100 > $2000)
    tx2 = client.post(
        "/api/transfers",
        json={
            "from_account_id": 2,
            "to_account_id": 1,
            "amount": 900.00,
        },
    )
    assert tx2.status_code == 400
    assert "would exceed daily limit" in tx2.json()["detail"]

    # 4. Transfer of $800 succeeds (fills daily limit exactly)
    tx3 = client.post(
        "/api/transfers",
        json={
            "from_account_id": 2,
            "to_account_id": 1,
            "amount": 800.00,
        },
    )
    assert tx3.status_code == 200

    limits_final = client.get("/api/limits").json()
    assert limits_final["current_daily_total"] == 2000.00
    assert limits_final["remaining_daily_limit"] == 0.00
