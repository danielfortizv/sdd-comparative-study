def test_mfa_status_initial(client):
    """GET /api/mfa/status returns initial threshold 1000.0, unlocked, 3 attempts remaining."""
    response = client.get("/api/mfa/status")
    assert response.status_code == 200
    data = response.json()
    assert data["threshold"] == 1000.00
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
    assert "2 attempt(s) remaining" in response.json()["detail"]

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
    assert "locked" in res3.json()["detail"].lower()

    # Status shows locked
    status_data = client.get("/api/mfa/status").json()
    assert status_data["locked"] is True
    assert status_data["remaining_attempts"] == 0

    # Even with correct PIN, operation is rejected with 423
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    transfer_res = client.post(
        "/api/transfers",
        json={
            "from_account_id": savings["id"],
            "to_account_id": checking["id"],
            "amount": 1500.00,
            "pin": "1234",
        },
    )
    assert transfer_res.status_code == 423
    assert "locked" in transfer_res.json()["detail"].lower()
