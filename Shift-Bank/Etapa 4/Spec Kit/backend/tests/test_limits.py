from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from database import DB_PATH, get_connection, init_db
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="function", autouse=True)
def reset_db():
    """Resets the isolated test database before each test."""
    conn = get_connection()
    cursor = conn.cursor()
    for table in ("recurring_occurrences", "history_projection", "domain_events", "idempotency_records", "projection_checkpoints", "stage4_migration_markers"):
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    cursor.execute("DROP TABLE IF EXISTS recurring_schedules;")
    cursor.execute("DROP TABLE IF EXISTS limits;")
    cursor.execute("DROP TABLE IF EXISTS beneficiaries;")
    cursor.execute("DROP TABLE IF EXISTS transfers;")
    cursor.execute("DROP TABLE IF EXISTS accounts;")
    conn.commit()
    conn.close()

    init_db()
    yield


def test_get_default_limits():
    """Verifies GET /api/limits retrieves default limits (COP 5M per-transfer, COP 10M daily)."""
    client = TestClient(app)
    response = client.get("/api/limits")
    assert response.status_code == 200
    data = response.json()

    assert data["per_transfer_limit"] == "5000000.00"
    assert data["daily_limit"] == "10000000.00"
    assert data["current_daily_consumption"] == "0.00"
    assert data["remaining_daily_availability"] == "10000000.00"
    assert "updated_at" in data


def test_update_dynamic_limits():
    """Verifies PUT /api/limits updates limits and takes immediate effect (A10)."""
    client = TestClient(app)
    payload = {
        "per_transfer_limit": "2000000.00",
        "daily_limit": "4000000.00"
    }
    response = client.put("/api/limits", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["per_transfer_limit"] == "2000000.00"
    assert data["daily_limit"] == "4000000.00"
    assert data["current_daily_consumption"] == "0.00"
    assert data["remaining_daily_availability"] == "4000000.00"

    # Verify subsequent GET reflects the updated limits
    get_resp = client.get("/api/limits")
    assert get_resp.status_code == 200
    assert get_resp.json()["per_transfer_limit"] == "2000000.00"
    assert get_resp.json()["daily_limit"] == "4000000.00"


def test_update_limits_invalid_inputs():
    """Verifies PUT /api/limits rejects non-positive, > 2 decimals, or invalid formats (A09)."""
    client = TestClient(app)

    # 1. Zero amount
    r = client.put("/api/limits", json={"per_transfer_limit": "0.00", "daily_limit": "1000000.00"})
    assert r.status_code == 400

    # 2. Negative amount
    r = client.put("/api/limits", json={"per_transfer_limit": "-500.00", "daily_limit": "1000000.00"})
    assert r.status_code == 400

    # 3. More than 2 decimal places
    r = client.put("/api/limits", json={"per_transfer_limit": "500000.123", "daily_limit": "1000000.00"})
    assert r.status_code == 400

    # 4. Non-numeric
    r = client.put("/api/limits", json={"per_transfer_limit": "invalid", "daily_limit": "1000000.00"})
    assert r.status_code == 400


def test_per_transfer_limit_boundaries():
    """Verifies rejection of amounts exceeding per-transfer limit and acceptance of exact equal amount (A11)."""
    client = TestClient(app)

    # Set per-transfer limit to COP 500,000.00
    client.put("/api/limits", json={"per_transfer_limit": "500000.00", "daily_limit": "10000000.00"})

    # 1. Transfer above limit: COP 500,000.01 -> Must be rejected with 400
    r = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "500000.01"
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "per-transfer limit" in r.json()["detail"]["message"].lower()

    # 2. Transfer exactly equal to limit: COP 500,000.00 -> Must succeed
    r2 = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "500000.00"
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "COMPLETED"


def test_mfa_cannot_bypass_limits():
    """Verifies that dynamic limits are evaluated BEFORE MFA, so MFA PIN cannot bypass limits (A14)."""
    client = TestClient(app)

    # Set per-transfer limit to COP 500,000.00
    client.put("/api/limits", json={"per_transfer_limit": "500000.00", "daily_limit": "10000000.00"})

    # Attempt transfer of COP 1,500,000.00 (which would normally trigger MFA)
    r = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00"
    })
    # Must fail with 400 Bad Request immediately, never return 202 PENDING_MFA
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "per-transfer limit" in r.json()["detail"]["message"].lower()


def test_daily_limit_accumulation_scenario():
    """Scenario A12: Daily limit accumulation (400 + 300 + 300 ok; next 10 fails)."""
    client = TestClient(app)

    # Configure daily limit = 1000.00, per-transfer limit = 1000.00
    client.put("/api/limits", json={"per_transfer_limit": "1000.00", "daily_limit": "1000.00"})

    # Transfer 1: 400.00
    r1 = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "400.00"
    })
    assert r1.status_code == 200

    # Transfer 2: 300.00
    r2 = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "300.00"
    })
    assert r2.status_code == 200

    # Transfer 3: 300.00 (reaching exactly 1000.00 total)
    r3 = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "300.00"
    })
    assert r3.status_code == 200

    # Check limits status
    limits_resp = client.get("/api/limits")
    assert limits_resp.json()["current_daily_consumption"] == "1000.00"
    assert limits_resp.json()["remaining_daily_availability"] == "0.00"

    # Transfer 4: 10.00 -> Must be rejected for exceeding daily limit
    r4 = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "10.00"
    })
    assert r4.status_code == 400
    assert r4.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "daily limit" in r4.json()["detail"]["message"].lower()


def test_daily_limit_immediate_reduction_clamping():
    """Verifies that reducing daily limit below current consumption clamps availability to 0.00 (D-07)."""
    client = TestClient(app)

    # Initial transfer of COP 500,000.00
    r = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "500000.00"
    })
    assert r.status_code == 200

    # Reduce daily limit to COP 300,000.00 (below current 500,000.00 consumption)
    r_update = client.put("/api/limits", json={
        "per_transfer_limit": "5000000.00",
        "daily_limit": "300000.00"
    })
    assert r_update.status_code == 200
    data = r_update.json()

    assert data["daily_limit"] == "300000.00"
    assert data["current_daily_consumption"] == "500000.00"
    assert data["remaining_daily_availability"] == "0.00"  # Clamped to 0, never negative!

    # Any subsequent transfer is immediately blocked
    r_blocked = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100.00"
    })
    assert r_blocked.status_code == 400
    assert r_blocked.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "daily limit" in r_blocked.json()["detail"]["message"].lower()


def test_utc_midnight_windowing():
    """Verifies that daily limit consumption strictly aggregates movements within the current UTC day (F-04)."""
    client = TestClient(app)
    conn = get_connection()
    cursor = conn.cursor()

    now_utc = datetime.now(timezone.utc)
    yesterday_iso = (now_utc - timedelta(days=1, hours=1)).strftime("%Y-%m-%dT12:00:00Z")
    today_fractional_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%S.500000Z")

    # Insert transfer from yesterday (should NOT be counted today)
    cursor.execute("""
        INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, transfer_type)
        VALUES ('tr_yesterday', 'acc_checking_123', 'acc_savings_456', '200000.00', 'COMPLETED', ?, 'INTERNAL');
    """, (yesterday_iso,))

    # Insert transfer from today with fractional seconds (MUST be counted today)
    cursor.execute("""
        INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, transfer_type)
        VALUES ('tr_today', 'acc_checking_123', 'acc_savings_456', '150000.00', 'COMPLETED', ?, 'INTERNAL');
    """, (today_fractional_iso,))
    conn.commit()
    conn.close()

    # Query limits
    resp = client.get("/api/limits")
    assert resp.status_code == 200
    data = resp.json()

    # Exactly 150000.00 counted, not 350000.00
    assert data["current_daily_consumption"] == "150000.00"
    assert data["remaining_daily_availability"] == "9850000.00"


def test_mfa_confirmation_revalidates_limits():
    """Verifies that confirming an MFA challenge re-validates dynamic limits and balance (HER-05)."""
    client = TestClient(app)

    # 1. Create sensitive transfer of COP 1,500,000.00 -> returns 202 PENDING_MFA
    r = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00"
    })
    assert r.status_code == 202
    transfer_id = r.json()["id"]

    # 2. Before confirming, reduce daily limit to COP 1,000,000.00
    client.put("/api/limits", json={
        "per_transfer_limit": "5000000.00",
        "daily_limit": "1000000.00"
    })

    # 3. Attempt to confirm MFA with valid code 123456
    r_confirm = client.post(f"/api/transfers/{transfer_id}/confirm-mfa", json={"code": "123456"})
    # Must fail because transfer amount 1,500,000.00 exceeds the updated daily limit 1,000,000.00
    assert r_confirm.status_code == 400
    assert r_confirm.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "daily limit" in r_confirm.json()["detail"]["message"].lower()
