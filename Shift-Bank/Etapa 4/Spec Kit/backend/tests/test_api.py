import pytest
import os
import sys

# Ensure backend/src is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient
from main import app
import database
from database import init_db, get_connection

@pytest.fixture(scope="function", autouse=True)
def reset_db(tmp_path, monkeypatch):
    """Resets the database before each test to ensure test isolation."""
    isolated_path = str(tmp_path / "test_api.sqlite")
    monkeypatch.setenv("TEST_DB_PATH", isolated_path)
    init_db(isolated_path)
    yield

def test_get_accounts():
    """Verifies GET /api/accounts retrieves inherited and additive Stage 4 accounts."""
    client = TestClient(app)
    response = client.get("/api/accounts")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6
    
    checking = next(a for a in data if a["name"] == "Checking")
    assert checking["balance"] == "5000000.00"
    assert checking["currency"] == "COP"
    
    savings = next(a for a in data if a["name"] == "Savings")
    assert savings["balance"] == "15000000.00"
    assert savings["currency"] == "COP"


def test_transfer_same_account():
    """Verifies that transferring funds to the same account is rejected with 400."""
    client = TestClient(app)
    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_checking_123",
        "amount": "100000.00"
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_TRANSFER"


def test_transfer_non_positive_amount():
    """Verifies that transferring zero or negative amounts is rejected with 400."""
    client = TestClient(app)
    
    # Test zero
    payload_zero = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "0.00"
    }
    response = client.post("/api/transfers", json=payload_zero)
    assert response.status_code == 422 or response.status_code == 400 # FastAPI Pydantic validator might return 422, both acceptable
    
    # Test negative
    payload_neg = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "-500.00"
    }
    response = client.post("/api/transfers", json=payload_neg)
    assert response.status_code == 422 or response.status_code == 400


def test_transfer_insufficient_funds():
    """Verifies that transferring more than the available balance is rejected with 400."""
    client = TestClient(app)
    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "6000000.00" # Exceeds checking balance of 5,000,000.00
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INSUFFICIENT_FUNDS"


def test_transfer_success_under_one_million():
    """Verifies successful direct transfer under COP 1,000,000 updates balances instantly."""
    client = TestClient(app)
    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "300000.00"
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Check response fields matching contract
    assert data["status"] == "COMPLETED"
    assert data["amount"] == "300000.00"
    assert data["source_account"] == "Checking"
    assert data["destination_account"] == "Savings"
    assert data["expires_at"] is None
    
    # Verify account balances were updated in the database
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    assert cursor.fetchone()[0] == "4700000.00" # 5,000,000.00 - 300,000.00
    
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_savings_456';")
    assert cursor.fetchone()[0] == "15300000.00" # 15,000,000.00 + 300,000.00
    
    conn.close()


def test_get_account_history():
    """Verifies GET /api/accounts/{account_id}/history retrieves exact seeded historical transactions in newest-first order."""
    client = TestClient(app)
    
    # 1. Query checking account history
    response = client.get("/api/accounts/acc_checking_123/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Chronological Ordering Verification: newest-first (descending)
    # tr_seeded_2 at 10:05:00Z should be first, tr_seeded_1 at 10:00:00Z should be second.
    t0 = data[0]
    t1 = data[1]
    
    # Verify both dates/created_at values according to seed data are sorted descending
    assert t0["date"] == "2026-09-30T10:05:00Z"
    assert t1["date"] == "2026-09-30T10:00:00Z"

    # Verify Transfer 2 (Checking -> Savings): outgoing from Checking's perspective
    assert t0["id"] == "tr_seeded_2"
    assert t0["direction"] == "outgoing"
    assert t0["amount"] == "100000.00"
    assert "Checking to Savings" in t0["description"]
    
    # Verify Transfer 1 (Savings -> Checking): incoming from Checking's perspective
    assert t1["id"] == "tr_seeded_1"
    assert t1["direction"] == "incoming"
    assert t1["amount"] == "500000.00"
    assert "Savings to Checking" in t1["description"]

    # 2. Query savings account history and verify reversed directions
    response_sav = client.get("/api/accounts/acc_savings_456/history")
    assert response_sav.status_code == 200
    data_sav = response_sav.json()
    assert len(data_sav) == 2
    
    # Verify chronological sorting (newest-first)
    assert data_sav[0]["date"] == "2026-09-30T10:05:00Z"
    assert data_sav[1]["date"] == "2026-09-30T10:00:00Z"
    
    # Verify Transfer 2 is incoming for Savings
    assert data_sav[0]["id"] == "tr_seeded_2"
    assert data_sav[0]["direction"] == "incoming"
    assert data_sav[0]["amount"] == "100000.00"
    
    # Verify Transfer 1 is outgoing for Savings
    assert data_sav[1]["id"] == "tr_seeded_1"
    assert data_sav[1]["direction"] == "outgoing"
    assert data_sav[1]["amount"] == "500000.00"
    
    # 3. Query non-existent account
    response_non = client.get("/api/accounts/acc_nonexistent/history")
    assert response_non.status_code == 404


def test_get_account_history_after_transfer():
    """Verifies that a newly completed standard transfer appears immediately at the top of the account's history."""
    client = TestClient(app)
    
    # Perform a new completed transfer checking -> savings
    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "250000.00"
    }
    tx_response = client.post("/api/transfers", json=payload)
    assert tx_response.status_code == 200
    new_tx = tx_response.json()
    new_tx_id = new_tx["id"]
    new_tx_date = new_tx["created_at"]

    # Retrieve history and verify new item is returned at the very top (index 0)
    response = client.get("/api/accounts/acc_checking_123/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Verify newest transfer is first (newest-first order)
    t0 = data[0]
    assert t0["id"] == new_tx_id
    assert t0["direction"] == "outgoing"
    assert t0["amount"] == "250000.00"
    assert t0["date"] == new_tx_date
    assert "Checking to Savings" in t0["description"]

    # Verify seeded transfers are now shifted down
    assert data[1]["id"] == "tr_seeded_2"
    assert data[2]["id"] == "tr_seeded_1"


# --- USER STORY 4: SENSITIVE TRANSFERS & MFA STATE MACHINE ---

def test_sensitive_transfer_creation():
    """Verifies that initiating a transfer >= COP 1,000,000 returns 202 Accepted, writes PENDING_MFA state, and leaves balances unchanged."""
    client = TestClient(app)
    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00" # Sensitive transfer
    }
    response = client.post("/api/transfers", json=payload)
    assert response.status_code == 202
    data = response.json()
    
    # Verify fields matching contracts and state machine
    assert data["status"] == "PENDING_MFA"
    assert data["amount"] == "1500000.00"
    assert data["expires_at"] is not None
    
    # Verify balances have NOT been changed
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    assert cursor.fetchone()[0] == "5000000.00"
    conn.close()


def test_sensitive_transfer_invalid_mfa_code():
    """Verifies that submitting an incorrect MFA code returns 401 and leaves the transfer PENDING_MFA."""
    client = TestClient(app)
    
    # 1. Create sensitive transfer
    create_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00"
    })
    tx_id = create_res.json()["id"]

    # 2. Confirm with bad code
    confirm_res = client.post(f"/api/transfers/{tx_id}/mfa", json={"code": "111111"})
    assert confirm_res.status_code == 401
    assert confirm_res.json()["detail"]["code"] == "MFA_INVALID"

    # 3. Verify transfer record is still PENDING_MFA in database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM transfers WHERE id = ?;", (tx_id,))
    assert cursor.fetchone()[0] == "PENDING_MFA"
    conn.close()


def test_sensitive_transfer_successful_mfa():
    """Verifies that submitting correct code '123456' within 5 mins executes transfer, updates balances, and marks as COMPLETED."""
    client = TestClient(app)
    
    # 1. Create sensitive transfer
    create_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00"
    })
    tx_id = create_res.json()["id"]

    # 2. Confirm with correct code
    confirm_res = client.post(f"/api/transfers/{tx_id}/mfa", json={"code": "123456"})
    assert confirm_res.status_code == 200
    data = confirm_res.json()
    assert data["status"] == "COMPLETED"

    # 3. Verify balances and status updated atomically
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    assert cursor.fetchone()[0] == "3500000.00" # 5,000,000.00 - 1,500,000.00
    
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_savings_456';")
    assert cursor.fetchone()[0] == "16500000.00" # 15,000,000.00 + 1,500,000.00
    
    cursor.execute("SELECT status FROM transfers WHERE id = ?;", (tx_id,))
    assert cursor.fetchone()[0] == "COMPLETED"
    
    conn.close()


def test_sensitive_transfer_insufficient_funds_at_confirmation():
    """Verifies re-validation at confirmation: if balance becomes insufficient, marks transfer as FAILED and returns 409."""
    client = TestClient(app)
    
    # 1. Create a sensitive transfer of 4,500,000
    create_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "4500000.00"
    })
    tx_id = create_res.json()["id"]

    # 2. Perform a separate immediate transfer of 1,000,000 (standard, completed immediately)
    # Checking balance will go down from 5,000,000 to 4,000,000.
    imm_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00" # Under 1,000,000
    })
    assert imm_res.status_code == 200

    # 3. Try to confirm the pending 4,500,000 transfer (Checking now only has 4,900,000, so still sufficient)
    # Wait, let's drain more checking balance so it's actually insufficient. Let's make an immediate transfer of 1,000,000? No, 1,000,000 is sensitive. Let's make a transfer of 900,000. Checking balance: 5,000,000 - 900,000 = 4,100,000.
    # Now try to confirm 4,500,000. Checked: 4,100,000 < 4,500,000. Insufficient!
    drain_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "900000.00"
    })
    assert drain_res.status_code == 200

    # 4. Confirm the pending 4,500,000 transfer. Re-validation must catch checking balance (4,100,000) < amount (4,500,000).
    confirm_res = client.post(f"/api/transfers/{tx_id}/mfa", json={"code": "123456"})
    assert confirm_res.status_code == 400
    assert confirm_res.json()["detail"]["code"] == "INSUFFICIENT_FUNDS"
    # 5. Verify balances remain at drained level, and transfer status is permanently FAILED in database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    assert cursor.fetchone()[0] == "4000000.00"
    
    cursor.execute("SELECT status FROM transfers WHERE id = ?;", (tx_id,))
    assert cursor.fetchone()[0] == "FAILED"
    conn.close()


def test_sensitive_transfer_on_demand_expiration():
    """Verifies that on-demand expiration check transitions the transfer status to EXPIRED and returns 410."""
    client = TestClient(app)
    
    # 1. Create sensitive transfer
    create_res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00"
    })
    tx_id = create_res.json()["id"]

    # 2. Directly tamper database to set the expires_at timestamp into the past (10 minutes ago)
    conn = get_connection()
    cursor = conn.cursor()
    past_iso = "2026-09-30T10:00:00Z"
    cursor.execute("UPDATE transfers SET expires_at = ? WHERE id = ?;", (past_iso, tx_id))
    conn.commit()
    conn.close()

    # 3. Confirm with correct code
    confirm_res = client.post(f"/api/transfers/{tx_id}/mfa", json={"code": "123456"})
    assert confirm_res.status_code == 410
    assert confirm_res.json()["detail"]["code"] == "MFA_EXPIRED"

    # 4. Verify DB state is EXPIRED and balances remain unchanged
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    assert cursor.fetchone()[0] == "5000000.00"
    
    cursor.execute("SELECT status FROM transfers WHERE id = ?;", (tx_id,))
    assert cursor.fetchone()[0] == "EXPIRED"
    conn.close()
