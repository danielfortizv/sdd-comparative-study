import sqlite3
import pytest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_connection, init_db, db_dependency
from app.core.seed import seed_database
from app.config import DEFAULT_MOCK_CUSTOMER_ID

@pytest.fixture
def seeded_db(tmp_path: Path):
    db_file = tmp_path / "test_transfers.db"
    conn = get_connection(db_file)
    init_db(conn)
    seed_database(conn)
    yield conn
    conn.close()

@pytest.fixture
def client(seeded_db: sqlite3.Connection):
    def override_db():
        yield seeded_db

    app.dependency_overrides[db_dependency] = override_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

def test_atomic_standard_transfer_success(client: TestClient, seeded_db: sqlite3.Connection):
    # Total customer balance before: 250000 + 1245075 + 500000 = 1995075 cents ($19,950.75)
    headers = {
        "X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID,
        "Idempotency-Key": str(uuid.uuid4()),
    }
    payload = {
        "from_account_id": "CHK-1001",
        "to_account_id": "SAV-2001",
        "amount_cents": 25000,  # $250.00
    }

    response = client.post("/api/transfers", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["transfer"]["source_account_id"] == "CHK-1001"
    assert data["transfer"]["destination_account_id"] == "SAV-2001"
    assert data["transfer"]["amount_cents"] == 25000
    assert data["transfer"]["amount_formatted"] == "$250.00"

    # Verify updated balances in response
    assert data["source_account"]["id"] == "CHK-1001"
    assert data["source_account"]["balance_cents"] == 225000
    assert data["source_account"]["balance_formatted"] == "$2,250.00"

    assert data["destination_account"]["id"] == "SAV-2001"
    assert data["destination_account"]["balance_cents"] == 1270075
    assert data["destination_account"]["balance_formatted"] == "$12,700.75"

    # Verify persistence directly in database
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    sav = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'SAV-2001'").fetchone()
    rsv = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'RSV-3001'").fetchone()

    assert chk["balance_cents"] == 225000
    assert sav["balance_cents"] == 1270075
    assert rsv["balance_cents"] == 500000

    # Balance Conservation Invariant: sum after equals sum before
    total_after = chk["balance_cents"] + sav["balance_cents"] + rsv["balance_cents"]
    assert total_after == 1995075

    # Verify Transfer record
    transfer_id = data["transfer"]["id"]
    trf = seeded_db.execute("SELECT * FROM transfer WHERE id = ?", (transfer_id,)).fetchone()
    assert trf is not None
    assert trf["status"] == "COMPLETED"
    assert trf["amount_cents"] == 25000

    # Verify Dual-Entry Movements (AD-7, FR-13)
    movements = seeded_db.execute(
        "SELECT * FROM movement WHERE transfer_id = ? ORDER BY id ASC", (transfer_id,)
    ).fetchall()
    assert len(movements) == 2

    # Debit on source
    debit = next(m for m in movements if m["direction"] == "DEBIT")
    assert debit["account_id"] == "CHK-1001"
    assert debit["amount_cents"] == 25000
    assert debit["running_balance_cents"] == 225000
    assert debit["counterparty_account_id"] == "SAV-2001"

    # Credit on destination
    credit = next(m for m in movements if m["direction"] == "CREDIT")
    assert credit["account_id"] == "SAV-2001"
    assert credit["amount_cents"] == 25000
    assert credit["running_balance_cents"] == 1270075
    assert credit["counterparty_account_id"] == "CHK-1001"

def test_same_account_transfer_rejection(client: TestClient, seeded_db: sqlite3.Connection):
    headers = {"X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID}
    payload = {
        "from_account_id": "CHK-1001",
        "to_account_id": "CHK-1001",
        "amount_cents": 25000,
    }

    response = client.post("/api/transfers", json=payload, headers=headers)
    assert response.status_code == 400

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "SAME_ACCOUNT_TRANSFER_NOT_ALLOWED"

    # Balances must be untouched
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    assert chk["balance_cents"] == 250000

def test_zero_and_negative_amount_rejection(client: TestClient, seeded_db: sqlite3.Connection):
    headers = {"X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID}

    # 1. Zero amount
    resp_zero = client.post(
        "/api/transfers",
        json={"from_account_id": "CHK-1001", "to_account_id": "SAV-2001", "amount_cents": 0},
        headers=headers,
    )
    assert resp_zero.status_code == 422
    assert resp_zero.json()["error"]["code"] == "INVALID_TRANSFER_AMOUNT"

    # 2. Negative amount
    resp_neg = client.post(
        "/api/transfers",
        json={"from_account_id": "CHK-1001", "to_account_id": "SAV-2001", "amount_cents": -5000},
        headers=headers,
    )
    assert resp_neg.status_code == 422
    assert resp_neg.json()["error"]["code"] == "INVALID_TRANSFER_AMOUNT"

    # Balances must be untouched
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    assert chk["balance_cents"] == 250000

def test_insufficient_funds_rejection(client: TestClient, seeded_db: sqlite3.Connection):
    headers = {"X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID}
    # Primary Checking has $2,500.00 (250000 cents). Attempt $3,500.00 (350000 cents)
    payload = {
        "from_account_id": "CHK-1001",
        "to_account_id": "SAV-2001",
        "amount_cents": 350000,
    }

    response = client.post("/api/transfers", json=payload, headers=headers)
    assert response.status_code == 422

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "INSUFFICIENT_FUNDS"

    # Balances must be untouched
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    assert chk["balance_cents"] == 250000

def test_idempotency_duplicate_submission_protection(client: TestClient, seeded_db: sqlite3.Connection):
    idempotency_key = str(uuid.uuid4())
    headers = {
        "X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID,
        "Idempotency-Key": idempotency_key,
    }
    payload = {
        "from_account_id": "CHK-1001",
        "to_account_id": "SAV-2001",
        "amount_cents": 25000,
    }

    # First request
    resp1 = client.post("/api/transfers", json=payload, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second identical request with same Idempotency-Key
    resp2 = client.post("/api/transfers", json=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Cached transfer ID must match
    assert data1["transfer"]["id"] == data2["transfer"]["id"]

    # Balance must only have decremented ONCE ($250.00)
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    assert chk["balance_cents"] == 225000  # Not 200000!

def test_atomic_rollback_on_transaction_failure(client: TestClient, seeded_db: sqlite3.Connection):
    # Simulate integrity error or lock failure by pointing destination to an account that will trigger an exception
    headers = {"X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID}
    payload = {
        "from_account_id": "CHK-1001",
        "to_account_id": "NON_EXISTENT_ACC",
        "amount_cents": 25000,
    }

    response = client.post("/api/transfers", json=payload, headers=headers)
    assert response.status_code == 403

    # Ensure source balance was not decremented
    chk = seeded_db.execute("SELECT balance_cents FROM account WHERE id = 'CHK-1001'").fetchone()
    assert chk["balance_cents"] == 250000

    # Ensure no orphan transfer or movements were created
    cursor = seeded_db.execute("SELECT COUNT(*) as count FROM transfer")
    assert cursor.fetchone()["count"] == 0
    cursor = seeded_db.execute("SELECT COUNT(*) as count FROM movement")
    assert cursor.fetchone()["count"] == 0
