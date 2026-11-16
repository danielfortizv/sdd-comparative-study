import os
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


# ==============================================================================
# T017: Beneficiary Management Integration Tests (A03, D-08, F-06)
# ==============================================================================

def test_create_and_list_beneficiary():
    """Verifies creating a saved beneficiary and retrieving it via GET /api/beneficiaries (A03)."""
    client = TestClient(app)

    payload = {
        "name": "Empresa de Energia",
        "bank_name": "Banco Davivienda",
        "routing_number": "123456789",
        "account_number": "9876543210"
    }
    create_resp = client.post("/api/beneficiaries", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()

    assert created_data["name"] == "Empresa de Energia"
    assert created_data["bank_name"] == "Banco Davivienda"
    assert created_data["routing_number"] == "123456789"
    assert created_data["account_number"] == "9876543210"
    assert "id" in created_data
    assert "created_at" in created_data

    # List beneficiaries
    list_resp = client.get("/api/beneficiaries")
    assert list_resp.status_code == 200
    beneficiaries = list_resp.json()
    assert len(beneficiaries) == 1
    assert beneficiaries[0]["id"] == created_data["id"]


def test_delete_beneficiary():
    """Verifies deleting a saved beneficiary (A03, D-08)."""
    client = TestClient(app)

    payload = {
        "name": "Arrendatario",
        "bank_name": "Bancolombia",
        "routing_number": "987654321",
        "account_number": "1122334455"
    }
    create_resp = client.post("/api/beneficiaries", json=payload)
    ben_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/beneficiaries/{ben_id}")
    assert del_resp.status_code == 204

    # Verify no longer returned
    list_resp = client.get("/api/beneficiaries")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0

    # Delete non-existent returns 404
    del_again = client.delete(f"/api/beneficiaries/{ben_id}")
    assert del_again.status_code == 404


def test_beneficiary_validation_rules():
    """Verifies strict routing (9 digits) and account (4-17 digits) validation (A05, A06)."""
    client = TestClient(app)

    base = {
        "name": "Maria Rodriguez",
        "bank_name": "Banco de Bogota",
        "routing_number": "123456789",
        "account_number": "123456"
    }

    # 1. Routing number < 9 digits
    p1 = {**base, "routing_number": "12345678"}
    assert client.post("/api/beneficiaries", json=p1).status_code == 400

    # 2. Routing number > 9 digits
    p2 = {**base, "routing_number": "1234567890"}
    assert client.post("/api/beneficiaries", json=p2).status_code == 400

    # 3. Routing number non-numeric
    p3 = {**base, "routing_number": "12345678A"}
    assert client.post("/api/beneficiaries", json=p3).status_code == 400

    # 4. Account number < 4 digits
    p4 = {**base, "account_number": "123"}
    assert client.post("/api/beneficiaries", json=p4).status_code == 400

    # 5. Account number > 17 digits
    p5 = {**base, "account_number": "123456789012345678"}
    assert client.post("/api/beneficiaries", json=p5).status_code == 400

    # 6. Account number non-numeric
    p6 = {**base, "account_number": "1234ABCD"}
    assert client.post("/api/beneficiaries", json=p6).status_code == 400

    # 7. Empty name
    p7 = {**base, "name": "   "}
    assert client.post("/api/beneficiaries", json=p7).status_code == 400


# ==============================================================================
# T018: ACH Transfers Integration Tests (A04, A05, A06, A07, D-06)
# ==============================================================================

def test_adhoc_ach_transfer_with_save_beneficiary():
    """Verifies initiating an ad hoc ACH transfer with save_beneficiary=True (A04, A07)."""
    client = TestClient(app)

    payload = {
        "source_account_id": "acc_checking_123",
        "amount": "250000.00",
        "recipient_name": "Empresa de Gas",
        "bank_name": "Banco Davivienda",
        "routing_number": "123456789",
        "account_number": "456789123",
        "save_beneficiary": True
    }
    resp = client.post("/api/transfers/ach", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "PENDING"
    assert data["transfer_type"] == "ACH"
    assert data["amount"] == "250000.00"
    assert data["recipient_name"] == "Empresa de Gas"

    # Verify source balance debited immediately (5,000,000 - 250,000 = 4,750,000) (A07)
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["id"] == "acc_checking_123")
    assert checking["balance"] == "4750000.00"

    # Verify beneficiary was saved (A04)
    beneficiaries = client.get("/api/beneficiaries").json()
    assert len(beneficiaries) == 1
    assert beneficiaries[0]["name"] == "Empresa de Gas"

    # Verify ACH movement visible in account history with LEFT JOIN (F-02, A07)
    history = client.get("/api/accounts/acc_checking_123/history").json()
    assert len(history) >= 1
    ach_entry = next(h for h in history if h["id"] == data["id"])
    assert ach_entry["direction"] == "outgoing"
    assert ach_entry["amount"] == "250000.00"
    assert "Empresa de Gas" in ach_entry["description"]
    assert "PENDING" in ach_entry["description"]


def test_ach_transfer_routing_and_account_validation():
    """Verifies ACH transfer rejects invalid routing or account numbers with 400 (A05, A06)."""
    client = TestClient(app)

    base = {
        "source_account_id": "acc_checking_123",
        "amount": "100000.00",
        "recipient_name": "Proveedor",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "12345678",
        "save_beneficiary": False
    }

    # Invalid routing (8 digits)
    r1 = client.post("/api/transfers/ach", json={**base, "routing_number": "12345678"})
    assert r1.status_code == 400

    # Invalid account (3 digits)
    r2 = client.post("/api/transfers/ach", json={**base, "account_number": "123"})
    assert r2.status_code == 400

    # Invalid amount (0)
    r3 = client.post("/api/transfers/ach", json={**base, "amount": "0.00"})
    assert r3.status_code == 400


def test_ach_limits_evaluated_before_mfa():
    """Verifies dynamic limits are checked strictly before MFA for ACH transfers (LIM-07, A14, F-09)."""
    client = TestClient(app)

    # Set per-transfer limit to COP 500,000.00
    client.put("/api/limits", json={"per_transfer_limit": "500000.00", "daily_limit": "10000000.00"})

    # Submit ACH transfer of COP 1,500,000.00
    payload = {
        "source_account_id": "acc_checking_123",
        "amount": "1500000.00",
        "recipient_name": "Inmobiliaria",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "12345678",
        "save_beneficiary": False
    }
    resp = client.post("/api/transfers/ach", json=payload)
    # Must fail immediately with 400, never enter PENDING_MFA (A14)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "LIMIT_EXCEEDED"
    assert "limit" in resp.json()["detail"]["message"].lower()


def test_sensitive_ach_transfer_and_mfa_confirmation():
    """Verifies sensitive ACH transfer (>= COP 1M) enters PENDING_MFA and debits upon PIN confirmation (D-03)."""
    client = TestClient(app)

    payload = {
        "source_account_id": "acc_checking_123",
        "amount": "1500000.00",
        "recipient_name": "Inmobiliaria",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "12345678",
        "save_beneficiary": False
    }
    resp = client.post("/api/transfers/ach", json=payload)
    assert resp.status_code == 202
    tx_data = resp.json()
    assert tx_data["status"] == "PENDING_MFA"
    tx_id = tx_data["id"]

    # Source balance untouched while in PENDING_MFA
    checking_before = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking_before["balance"] == "5000000.00"

    # Confirm with code 123456
    confirm_resp = client.post(f"/api/transfers/{tx_id}/confirm-mfa", json={"code": "123456"})
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "PENDING"

    # Now balance is debited
    checking_after = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking_after["balance"] == "3500000.00"


def test_autonomous_ach_settlement():
    """Verifies autonomous background settlement transitions PENDING to SETTLED without second debit (A07, F-03)."""
    client = TestClient(app)

    # Initiate standard ACH transfer
    resp = client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "100000.00",
        "recipient_name": "Colegio",
        "bank_name": "Banco de Bogota",
        "routing_number": "123456789",
        "account_number": "99887766",
        "save_beneficiary": False
    })
    assert resp.status_code == 201
    tx_id = resp.json()["id"]

    # Balance debited once
    checking_mid = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking_mid["balance"] == "4900000.00"

    # Simulate 11 seconds elapsing by backdating created_at in database
    conn = get_connection()
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE transfers SET created_at = ? WHERE id = ?;", (past_iso, tx_id))
    conn.commit()
    conn.close()

    # Trigger test settlement sweep
    settle_resp = client.post("/api/test/ach/settle-pending")
    assert settle_resp.status_code == 200
    assert settle_resp.json()["settled_count"] >= 1

    # Verify status is now SETTLED and balance was NOT debited a second time
    checking_final = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking_final["balance"] == "4900000.00"

    # Verify movement description in history shows SETTLED
    history = client.get("/api/accounts/acc_checking_123/history").json()
    entry = next(h for h in history if h["id"] == tx_id)
    assert "SETTLED" in entry["description"]


# ==============================================================================
# T019: Deterministic Test-Only Failure & Atomic Refund (A08, D-06, F-03, F-05)
# ==============================================================================

def test_ach_failure_single_refund_and_idempotency():
    """Verifies simulated ACH failure executes exactly one refund and is idempotent (A08, F-05)."""
    client = TestClient(app)

    # 1. Create standard ACH transfer of COP 200,000.00
    resp = client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "200000.00",
        "recipient_name": "Taller Mecanico",
        "bank_name": "Banco Popular",
        "routing_number": "123456789",
        "account_number": "55443322",
        "save_beneficiary": False
    })
    assert resp.status_code == 201
    tx_id = resp.json()["id"]

    # Verify debited: 5M - 200k = 4.8M
    c1 = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert c1["balance"] == "4800000.00"

    # 2. Trigger simulated failure on PENDING transfer
    fail_resp = client.post(f"/api/test/ach/{tx_id}/fail")
    assert fail_resp.status_code == 200
    fail_data = fail_resp.json()
    assert fail_data["status"] == "FAILED"
    assert fail_data["refunded_amount"] == "200000.00"

    # Verify balance refunded once: 4.8M + 200k = 5.0M
    c2 = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert c2["balance"] == "5000000.00"

    # 3. Verify failed transfer is excluded from daily limit consumption (A08, LIM-06)
    limits = client.get("/api/limits").json()
    assert limits["current_daily_consumption"] == "0.00"
    assert limits["remaining_daily_availability"] == "10000000.00"

    # 4. Trigger failure a second time -> Must return 409 Conflict without duplicate refund (F-05)
    fail_again = client.post(f"/api/test/ach/{tx_id}/fail")
    assert fail_again.status_code == 409

    # Balance remains 5.0M
    c3 = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert c3["balance"] == "5000000.00"


def test_test_endpoints_disabled_by_default():
    """Verifies test endpoints return 404 when ENABLE_TEST_ENDPOINTS is not enabled (F-03)."""
    old_env = os.environ.get("ENABLE_TEST_ENDPOINTS")
    try:
        os.environ["ENABLE_TEST_ENDPOINTS"] = "false"
        client = TestClient(app)

        r1 = client.post("/api/test/ach/settle-pending")
        assert r1.status_code == 404

        r2 = client.post("/api/test/ach/nonexistent/fail")
        assert r2.status_code == 404
    finally:
        if old_env is not None:
            os.environ["ENABLE_TEST_ENDPOINTS"] = old_env
        else:
            os.environ.pop("ENABLE_TEST_ENDPOINTS", None)


def test_beneficiary_deletion_preserves_transfer_snapshots():
    """Verifies deleting a saved beneficiary preserves past transfer records intact (REC-11, D-08)."""
    client = TestClient(app)

    # 1. Create beneficiary
    ben_resp = client.post("/api/beneficiaries", json={
        "name": "Arrendatario Snapshot",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "88776655"
    })
    ben_id = ben_resp.json()["id"]

    # 2. Execute ACH transfer referencing recipient
    ach_resp = client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "100000.00",
        "recipient_name": "Arrendatario Snapshot",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "88776655",
        "save_beneficiary": False
    })
    tx_id = ach_resp.json()["id"]

    # 3. Delete the beneficiary
    client.delete(f"/api/beneficiaries/{ben_id}")

    # 4. Verify the transfer history still retains recipient name and bank name intact
    history = client.get("/api/accounts/acc_checking_123/history").json()
    entry = next(h for h in history if h["id"] == tx_id)
    assert "Arrendatario Snapshot" in entry["description"]
    assert "Bancolombia" in entry["description"]
