import uuid


def test_mfa_status_initial(client):
    """GET /api/mfa/status returns initial threshold '1000.00', unlocked, 3 attempts remaining."""
    response = client.get("/api/mfa/status")
    assert response.status_code == 200
    data = response.json()
    assert data["threshold"] == "1000.00"
    assert data["locked"] is False
    assert data["remaining_attempts"] == 3


def test_mfa_verify_correct_pin(client):
    """POST /api/mfa/verify with correct PIN '1234' returns valid=True."""
    response = client.post("/api/mfa/verify", json={"pin": "1234"})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["remaining_attempts"] == 3
    assert data["locked"] is False


def test_mfa_verify_incorrect_pin_decrements_attempts(client):
    """Incorrect PIN returns HTTP 400 with remaining attempts count."""
    response = client.post("/api/mfa/verify", json={"pin": "0000"})
    assert response.status_code == 400
    assert "2 attempt(s) remaining" in response.text

    # Verify status reflects 2 attempts left
    status_data = client.get("/api/mfa/status").json()
    assert status_data["remaining_attempts"] == 2
    assert status_data["locked"] is False


def test_mfa_three_failed_attempts_triggers_lockout(client):
    """Three consecutive failed attempts trigger account lockout and HTTP 423 Locked."""
    # Attempt 1
    res1 = client.post("/api/mfa/verify", json={"pin": "0000"})
    assert res1.status_code == 400

    # Attempt 2
    res2 = client.post("/api/mfa/verify", json={"pin": "1111"})
    assert res2.status_code == 400

    # Attempt 3: Triggers lockout (HTTP 423)
    res3 = client.post("/api/mfa/verify", json={"pin": "2222"})
    assert res3.status_code == 423
    assert "locked" in res3.text.lower()

    # Status shows locked
    status_data = client.get("/api/mfa/status").json()
    assert status_data["locked"] is True
    assert status_data["remaining_attempts"] == 0

    # Even with correct PIN, protected transfer is rejected with HTTP 423
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")
    initial_sav_bal = savings["balance"]
    initial_chk_bal = checking["balance"]

    transfer_res = client.post(
        "/api/transfers",
        json={
            "from_account_id": savings["id"],
            "to_account_id": checking["id"],
            "amount": "1500.00",
            "expected_from_version": savings["version"],
            "expected_to_version": checking["version"],
            "pin": "1234",
            "description": "Transfer while MFA locked",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert transfer_res.status_code == 423
    assert "locked" in transfer_res.text.lower()

    # Verify balances were not modified
    final_sav = client.get(f"/api/accounts/{savings['id']}").json()
    final_chk = client.get(f"/api/accounts/{checking['id']}").json()
    assert final_sav["balance"] == initial_sav_bal
    assert final_chk["balance"] == initial_chk_bal


def test_mfa_threshold_boundary_behavior(client):
    """Verifies that transfers <= $1,000.00 bypass MFA while transfers > $1,000.00 require PIN."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    # Boundary: exactly $1,000.00 does not require PIN
    resp_exact = client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": "1000.00",
            "expected_from_version": checking["version"],
            "expected_to_version": savings["version"],
            "description": "Exact $1000 transfer",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_exact.status_code == 200

    # Refresh versions
    checking = client.get(f"/api/accounts/{checking['id']}").json()
    savings = client.get(f"/api/accounts/{savings['id']}").json()

    # Boundary: $1,000.01 without PIN triggers HTTP 428
    resp_over = client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": "1000.01",
            "expected_from_version": checking["version"],
            "expected_to_version": savings["version"],
            "description": "Over threshold transfer without PIN",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_over.status_code == 428
    assert resp_over.json()["detail"] == "MFA_REQUIRED"

    # Boundary: $1,000.01 with valid PIN succeeds
    resp_with_pin = client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": "1000.01",
            "expected_from_version": checking["version"],
            "expected_to_version": savings["version"],
            "pin": "1234",
            "description": "Over threshold transfer with valid PIN",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_with_pin.status_code == 200
