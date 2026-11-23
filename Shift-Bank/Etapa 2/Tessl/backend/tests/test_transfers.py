def test_transfer_under_threshold_executes_without_pin(client):
    """Transfers <= $1,000 execute immediately without requiring MFA PIN."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 250.00,
        "description": "Savings boost",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 250.00
    assert data["status"] == "completed"

    # Verify balances updated atomically
    updated_checking = client.get(f"/api/accounts/{checking['id']}").json()
    updated_savings = client.get(f"/api/accounts/{savings['id']}").json()
    assert updated_checking["balance"] == 2250.00  # 2500 - 250
    assert updated_savings["balance"] == 10250.00  # 10000 + 250


def test_transfer_over_threshold_requires_pin(client):
    """Transfers > $1,000 without PIN return HTTP 428 Precondition Required with MFA_REQUIRED and message."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1500.00,
        "description": "Large transfer without PIN",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 428
    assert response.json() == {
        "detail": "MFA_REQUIRED",
        "message": "Security PIN required for transfers over $1,000",
    }

    # Verify balances NOT modified
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == 10000.00


def test_transfer_exact_boundary_1000_executes_without_pin(client):
    """Transfers of exactly $1,000.00 execute immediately without requiring MFA PIN."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 1000.00,
        "description": "Exact boundary transfer of $1,000.00",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["amount"] == 1000.00

    # Verify balances updated
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == 1500.00
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == 11000.00


def test_transfer_exact_boundary_1000_01_without_pin_returns_http_428(client):
    """Transfers of boundary amount $1,000.01 without PIN return HTTP 428 with full contract."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    initial_tx_count = len(client.get("/api/transactions").json())

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1000.01,
        "description": "Boundary amount exceeding threshold by $0.01",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 428
    assert response.json() == {
        "detail": "MFA_REQUIRED",
        "message": "Security PIN required for transfers over $1,000",
    }

    # Verify rejected transfer does not alter balances or transaction history
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == 10000.00
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == 2500.00
    assert len(client.get("/api/transactions").json()) == initial_tx_count


def test_transfer_exact_boundary_1000_01_with_valid_pin_succeeds(client):
    """Transfers of boundary amount $1,000.01 with valid PIN execute successfully."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    initial_tx_count = len(client.get("/api/transactions").json())

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1000.01,
        "description": "Authorized boundary transfer of $1,000.01",
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["amount"] == 1000.01

    # Verify balances updated atomically
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == 8999.99
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == 3500.01

    # Verify synchronized transactions appended (+2)
    new_txs = client.get("/api/transactions").json()
    assert len(new_txs) == initial_tx_count + 2


def test_transfer_over_threshold_with_valid_pin_succeeds(client):
    """Transfers > $1,000 with valid Security PIN ('1234') execute successfully."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 2000.00,
        "description": "Large authorized transfer",
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Verify balances updated
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == 8000.00
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == 4500.00


def test_transfer_to_same_account_fails(client):
    """Transfer fails with HTTP 400 when from_account_id equals to_account_id."""
    accounts = client.get("/api/accounts").json()
    checking_id = accounts[0]["id"]

    payload = {
        "from_account_id": checking_id,
        "to_account_id": checking_id,
        "amount": 100.00,
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 400
    assert "same account" in response.json()["detail"].lower()


def test_transfer_insufficient_funds_fails(client):
    """Transfer fails with HTTP 400 when amount exceeds source account balance."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],  # Balance: 2500
        "to_account_id": savings["id"],
        "amount": 3000.00,  # Exceeds balance
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 400
    assert "insufficient funds" in response.json()["detail"].lower()


def test_transfer_non_positive_amount_fails(client):
    """Transfer fails with HTTP 422 if amount is <= 0."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": accounts[1]["id"],
        "amount": 0.0,
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 422


def test_transfer_more_than_two_decimals_fails(client):
    """Transfer fails with HTTP 422 if amount has more than 2 decimal places."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": accounts[1]["id"],
        "amount": 50.123,
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 422


def test_transfer_non_existent_account_fails(client):
    """Transfer fails with HTTP 404 if source or destination does not exist."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": 99999,
        "amount": 50.00,
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 404
