import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_connection, init_db
from app.core.seed import seed_database
from app.config import (
    DEFAULT_MOCK_CUSTOMER_ID,
    DEFAULT_MOCK_CUSTOMER_NAME,
    DEFAULT_MOCK_CUSTOMER_EMAIL,
)

@pytest.fixture
def test_db(tmp_path: Path):
    db_file = tmp_path / "test_shift_bank.db"
    conn = get_connection(db_file)
    init_db(conn)
    yield conn
    conn.close()

def test_database_initialization_and_seeder(test_db: sqlite3.Connection):
    # Run seeder
    seed_database(test_db)

    # 1. Verify Customer
    cursor = test_db.execute("SELECT id, full_name, email FROM customer WHERE id = ?", (DEFAULT_MOCK_CUSTOMER_ID,))
    customer = cursor.fetchone()
    assert customer is not None
    assert customer["id"] == DEFAULT_MOCK_CUSTOMER_ID
    assert customer["full_name"] == DEFAULT_MOCK_CUSTOMER_NAME
    assert customer["email"] == DEFAULT_MOCK_CUSTOMER_EMAIL

    # 2. Verify Exactly 3 Accounts
    cursor = test_db.execute(
        "SELECT id, nickname, account_type, balance_cents FROM account WHERE customer_id = ? ORDER BY id",
        (DEFAULT_MOCK_CUSTOMER_ID,)
    )
    accounts = cursor.fetchall()
    assert len(accounts) == 3

    # Primary Checking
    assert accounts[0]["id"] == "CHK-1001"
    assert accounts[0]["nickname"] == "Primary Checking"
    assert accounts[0]["account_type"] == "CHECKING"
    assert accounts[0]["balance_cents"] == 250000  # $2,500.00 exact

    # High-Yield Savings
    assert accounts[1]["id"] == "RSV-3001" or accounts[1]["id"] == "SAV-2001"
    sav = next(a for a in accounts if a["id"] == "SAV-2001")
    assert sav["nickname"] == "High-Yield Savings"
    assert sav["account_type"] == "SAVINGS"
    assert sav["balance_cents"] == 1245075  # $12,450.75 exact

    # Emergency Reserve
    rsv = next(a for a in accounts if a["id"] == "RSV-3001")
    assert rsv["nickname"] == "Emergency Reserve"
    assert rsv["account_type"] == "RESERVE"
    assert rsv["balance_cents"] == 500000  # $5,000.00 exact

def test_seeder_idempotency(test_db: sqlite3.Connection):
    # Seed twice
    seed_database(test_db)
    seed_database(test_db)

    cursor = test_db.execute("SELECT COUNT(*) as count FROM customer")
    assert cursor.fetchone()["count"] == 1

    cursor = test_db.execute("SELECT COUNT(*) as count FROM account")
    assert cursor.fetchone()["count"] == 3

def test_balance_non_negative_constraint(test_db: sqlite3.Connection):
    seed_database(test_db)
    # Attempting to insert or update negative balance must violate check constraint
    with pytest.raises(sqlite3.IntegrityError):
        with test_db:
            test_db.execute(
                "INSERT INTO account (id, customer_id, nickname, account_type, balance_cents) VALUES (?, ?, ?, ?, ?)",
                ("NEG-001", DEFAULT_MOCK_CUSTOMER_ID, "Negative Account", "CHECKING", -500)
            )

def test_api_healthcheck():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["stage"] == 1
    assert data["currency"] == "USD"
