def test_get_accounts_returns_all_seed_accounts(client):
    """GET /api/accounts returns HTTP 200 with all accounts belonging to the mock user."""
    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert isinstance(accounts, list)
    assert len(accounts) == 2

    # Check Checking account
    checking = next((a for a in accounts if a["account_number"] == "CHK-1001"), None)
    assert checking is not None
    assert checking["account_name"] == "Primary Checking"
    assert checking["account_type"] == "checking"
    assert checking["balance"] == 2500.00
    assert checking["currency"] == "USD"
    assert checking["user_id"] == 1

    # Check Savings account
    savings = next((a for a in accounts if a["account_number"] == "SAV-2001"), None)
    assert savings is not None
    assert savings["account_name"] == "Standard Savings"
    assert savings["account_type"] == "savings"
    assert savings["balance"] == 10000.00
    assert savings["currency"] == "USD"
    assert savings["user_id"] == 1


def test_get_account_by_id_success(client):
    """GET /api/accounts/{id} returns HTTP 200 for an existing account."""
    accounts_res = client.get("/api/accounts")
    account_id = accounts_res.json()[0]["id"]

    response = client.get(f"/api/accounts/{account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == account_id
    assert data["account_name"] == "Primary Checking"
    assert data["balance"] == 2500.00


def test_get_account_by_id_not_found(client):
    """GET /api/accounts/{id} returns HTTP 404 when account does not exist."""
    response = client.get("/api/accounts/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
