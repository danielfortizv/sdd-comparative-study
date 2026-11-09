import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_connection, init_db, db_dependency
from app.core.seed import seed_database
from app.config import DEFAULT_MOCK_CUSTOMER_ID
from app.schemas.account import format_cents_to_usd

@pytest.fixture
def seeded_db(tmp_path: Path):
    db_file = tmp_path / "test_accounts.db"
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

def test_get_accounts_success(client: TestClient):
    headers = {"X-Customer-Id": DEFAULT_MOCK_CUSTOMER_ID}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Primary Checking
    chk = next(a for a in data if a["id"] == "CHK-1001")
    assert chk["nickname"] == "Primary Checking"
    assert chk["type"] == "CHECKING"
    assert chk["account_type"] == "CHECKING"
    assert chk["balance_cents"] == 250000
    assert chk["balance_formatted"] == "$2,500.00"

    # High-Yield Savings
    sav = next(a for a in data if a["id"] == "SAV-2001")
    assert sav["nickname"] == "High-Yield Savings"
    assert sav["type"] == "SAVINGS"
    assert sav["account_type"] == "SAVINGS"
    assert sav["balance_cents"] == 1245075
    assert sav["balance_formatted"] == "$12,450.75"

    # Emergency Reserve
    rsv = next(a for a in data if a["id"] == "RSV-3001")
    assert rsv["nickname"] == "Emergency Reserve"
    assert rsv["type"] == "RESERVE"
    assert rsv["account_type"] == "RESERVE"
    assert rsv["balance_cents"] == 500000
    assert rsv["balance_formatted"] == "$5,000.00"

def test_get_accounts_missing_customer_header(client: TestClient):
    # Request without X-Customer-Id header must return 403 Forbidden with standard error envelope
    response = client.get("/api/accounts")
    assert response.status_code == 403

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "MISSING_CUSTOMER_CONTEXT"
    assert "X-Customer-Id header is required" in body["error"]["message"]

def test_get_accounts_unauthorized_customer_id(client: TestClient):
    # Request with an unknown customer ID must return 403 Forbidden with standard error envelope
    headers = {"X-Customer-Id": "unknown_user_999"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 403

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED_CUSTOMER"
    assert "unauthorized" in body["error"]["message"].lower()

def test_format_cents_to_usd():
    assert format_cents_to_usd(0) == "$0.00"
    assert format_cents_to_usd(5) == "$0.05"
    assert format_cents_to_usd(50) == "$0.50"
    assert format_cents_to_usd(100) == "$1.00"
    assert format_cents_to_usd(250000) == "$2,500.00"
    assert format_cents_to_usd(1245075) == "$12,450.75"
    assert format_cents_to_usd(100000000) == "$1,000,000.00"
