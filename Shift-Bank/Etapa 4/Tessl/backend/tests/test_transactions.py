import uuid


def test_get_all_transactions_returns_seed_movements(client):
    """GET /api/transactions returns all transactions ordered newest first."""
    response = client.get("/api/transactions")
    assert response.status_code == 200
    transactions = response.json()
    assert isinstance(transactions, list)
    assert len(transactions) == 3  # 2 checking seed transactions + 1 savings seed transaction

    # Check fields present on transaction objects
    first = transactions[0]
    assert "id" in first
    assert "account_id" in first
    assert "transaction_type" in first
    assert "amount" in first
    assert "balance_after" in first
    assert "description" in first
    assert "created_at" in first
    assert "currency" in first
    assert isinstance(first["amount"], str)
    assert isinstance(first["balance_after"], str)


def test_get_transactions_filtered_by_account(client):
    """GET /api/transactions?account_id={id} returns movements strictly for that account."""
    accounts = client.get("/api/accounts").json()
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    response = client.get(f"/api/transactions?account_id={savings['id']}")
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["account_id"] == savings["id"]
    assert transactions[0]["amount"] == "10000.00"
    assert transactions[0]["balance_after"] == "10000.00"
    assert transactions[0]["currency"] == "USD"
    assert transactions[0]["transaction_type"] == "credit"


def test_transfer_creates_synchronized_transactions(client):
    """Executing a transfer produces a debit transaction for sender and credit for receiver."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    # Initial transaction count
    initial_count = len(client.get("/api/transactions").json())

    # Execute transfer with D-13 Idempotency-Key, D-14 versions, and D-03 exact amount
    idemp_key = str(uuid.uuid4())
    transfer_resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": "300.00",
            "expected_from_version": checking["version"],
            "expected_to_version": savings["version"],
            "description": "Monthly savings allotment",
        },
        headers={"Idempotency-Key": idemp_key},
    )
    assert transfer_resp.status_code == 200
    transfer_data = transfer_resp.json()
    assert transfer_data["status"] == "completed"

    # After transfer: 2 new movements recorded
    new_txs = client.get("/api/transactions").json()
    assert len(new_txs) == initial_count + 2

    # Verify debit on checking
    checking_txs = client.get(f"/api/transactions?account_id={checking['id']}").json()
    latest_checking = checking_txs[0]
    assert latest_checking["transaction_type"] == "debit"
    assert latest_checking["amount"] == "300.00"
    assert latest_checking["balance_after"] == "2200.00"  # 2500.00 - 300.00
    assert latest_checking["currency"] == "USD"
    assert latest_checking["transfer_id"] == transfer_data["id"]

    # Verify credit on savings
    savings_txs = client.get(f"/api/transactions?account_id={savings['id']}").json()
    latest_savings = savings_txs[0]
    assert latest_savings["transaction_type"] == "credit"
    assert latest_savings["amount"] == "300.00"
    assert latest_savings["balance_after"] == "10300.00"  # 10000.00 + 300.00
    assert latest_savings["currency"] == "USD"
    assert latest_savings["transfer_id"] == transfer_data["id"]


def test_get_transactions_invalid_account_fails(client):
    """GET /api/transactions?account_id=99999 returns HTTP 404."""
    response = client.get("/api/transactions?account_id=99999")
    assert response.status_code == 404
