from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os

import pytest
from database import get_connection, init_db
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="function", autouse=True)
def reset_db(tmp_path, monkeypatch):
    """Resets the isolated test database before each test."""
    isolated_path = str(tmp_path / "test_stage2_regression.sqlite")
    monkeypatch.setenv("TEST_DB_PATH", isolated_path)
    init_db(isolated_path)
    yield


# ==============================================================================
# T042: Stage 1 Regression & Multi-State History Visibility (HER-01..05, F-02)
# ==============================================================================

def test_inherited_account_balances_and_seeds():
    """Verifies inherited Stage 1 accounts, COP currency, and pre-seeded movements (HER-01, A01)."""
    client = TestClient(app)

    resp = client.get("/api/accounts")
    assert resp.status_code == 200
    accounts = resp.json()

    assert len(accounts) == 6
    checking = next(a for a in accounts if a["id"] == "acc_checking_123")
    savings = next(a for a in accounts if a["id"] == "acc_savings_456")

    assert checking["name"] == "Checking"
    assert checking["balance"] == "5000000.00"
    assert checking["currency"] == "COP"

    assert savings["name"] == "Savings"
    assert savings["balance"] == "15000000.00"
    assert savings["currency"] == "COP"

    # Verify pre-seeded historical transfers appear in Checking history
    history = client.get("/api/accounts/acc_checking_123/history").json()
    assert len(history) == 2
    # Newest first: tr_seeded_2 at 10:05, tr_seeded_1 at 10:00
    assert history[0]["id"] == "tr_seeded_2"
    assert all(item["currency"] == "COP" for item in history)
    assert history[0]["direction"] == "outgoing"
    assert history[0]["amount"] == "100000.00"
    assert history[0]["description"] == "Transfer from Checking to Savings"

    assert history[1]["id"] == "tr_seeded_1"
    assert history[1]["direction"] == "incoming"
    assert history[1]["amount"] == "500000.00"
    assert history[1]["description"] == "Transfer from Savings to Checking"


def test_stage4_public_contracts_health_audit_and_guarded_simulators(monkeypatch):
    client = TestClient(app)
    accounts = client.get("/api/accounts")
    assert accounts.status_code == 200 and len(accounts.json()) == 6
    checking = next(row for row in accounts.json() if row["id"] == "acc_checking_123")
    assert checking["currency"] == "COP" and checking["version"] == 0
    history = client.get("/api/accounts/acc_checking_123/history")
    assert history.status_code == 200 and all(row["currency"] == "COP" for row in history.json())
    limits = client.get("/api/limits")
    assert limits.status_code == 200
    assert limits.json()["per_transfer_limit"] == "5000000.00"
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/audit/verify").status_code == 401
    assert client.get("/api/audit/verify", headers={"X-Audit-Admin-Key": os.environ["AUDIT_ADMIN_KEY"]}).status_code == 200

    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "false")
    assert client.post("/api/test/recurring/run-due").status_code == 404
    monkeypatch.setenv("ENABLE_TEST_ENDPOINTS", "true")
    guarded = client.post("/api/test/recurring/run-due")
    assert guarded.status_code == 200 and guarded.json()["processed_count"] == 0


def test_stage4_cutover_marker_and_history_import_do_not_double_apply_balances():
    conn = get_connection()
    try:
        marker = conn.cursor().execute("SELECT account_count,history_count FROM stage4_migration_markers WHERE migration_key='e4-cutover-v1'").fetchone()
        assert marker == (6, 2)
        events = conn.cursor().execute("SELECT COUNT(*) FROM domain_events WHERE event_type='LegacyHistoryImported'").fetchone()[0]
        assert events == 2
        checking = conn.cursor().execute("SELECT balance,currency FROM accounts WHERE id='acc_checking_123'").fetchone()
        assert checking == ("5000000.00", "COP")
    finally:
        conn.close()


def test_stage4_cutover_marker_and_history_import_do_not_double_apply_balances():
    conn = get_connection()
    try:
        marker = conn.cursor().execute("SELECT account_count,history_count FROM stage4_migration_markers WHERE migration_key='e4-cutover-v1'").fetchone()
        assert marker == (6, 2)
        events = conn.cursor().execute("SELECT COUNT(*) FROM domain_events WHERE event_type='LegacyHistoryImported'").fetchone()[0]
        assert events == 2
        checking = conn.cursor().execute("SELECT balance,currency FROM accounts WHERE id='acc_checking_123'").fetchone()
        assert checking == ("5000000.00", "COP")
    finally:
        conn.close()


def test_multi_state_left_join_account_history():
    """Verifies that GET /api/accounts/{id}/history uses LEFT JOIN and includes multi-state
    movements (COMPLETED, PENDING, SETTLED, FAILED) without exposing raw DB IDs (HER-01, F-02).
    """
    client = TestClient(app)

    # 1. Execute an internal transfer (COMPLETED)
    client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "200000.00"
    })

    # 2. Execute an ACH transfer that enters PENDING
    ach_resp = client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "300000.00",
        "recipient_name": "Empresa Electrica",
        "bank_name": "Banco Davivienda",
        "routing_number": "123456789",
        "account_number": "987654321",
        "save_beneficiary": False
    })
    ach_id = ach_resp.json()["id"]

    # 3. Simulate failure on an ACH transfer (FAILED)
    ach_fail_resp = client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "150000.00",
        "recipient_name": "Gas Natural",
        "bank_name": "Bancolombia",
        "routing_number": "987654321",
        "account_number": "11223344",
        "save_beneficiary": False
    })
    fail_id = ach_fail_resp.json()["id"]
    client.post(f"/api/test/ach/{fail_id}/fail")

    # 4. Query account history for checking account
    history = client.get("/api/accounts/acc_checking_123/history").json()

    # All movements must appear in history
    entry_ids = [h["id"] for h in history]
    assert ach_id in entry_ids
    assert fail_id in entry_ids

    # Verify formatting and ID hiding
    for entry in history:
        desc = entry["description"]
        # Raw database IDs must never leak into description
        assert "acc_checking_123" not in desc
        assert "acc_savings_456" not in desc
        assert "user_mock_001" not in desc

        if entry["id"] == ach_id:
            assert entry["direction"] == "outgoing"
            assert "ACH Transfer to Empresa Electrica (Banco Davivienda) - PENDING" == desc

        if entry["id"] == fail_id:
            assert entry["direction"] == "outgoing"
            assert "ACH Transfer to Gas Natural (Bancolombia) - FAILED" == desc


def test_internal_transfer_contract_compatibility():
    """Verifies that internal transfer contracts match Stage 1 schema exactly (HER-02, A02)."""
    client = TestClient(app)

    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "250000.00"
    }
    resp = client.post("/api/transfers", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Verify exact Stage 1 response structure
    assert "id" in data
    assert data["source_account"] == "Checking"
    assert data["destination_account"] == "Savings"
    assert data["amount"] == "250000.00"
    assert data["status"] == "COMPLETED"
    assert "created_at" in data
    assert data["expires_at"] is None

    # Balances updated atomically: Checking 5M - 250k = 4.75M; Savings 15M + 250k = 15.25M
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["id"] == "acc_checking_123")
    savings = next(a for a in accounts if a["id"] == "acc_savings_456")
    assert checking["balance"] == "4750000.00"
    assert savings["balance"] == "15250000.00"


def test_sensitive_transfer_mfa_compatibility():
    """Verifies sensitive internal transfer MFA step-up and code verification (HER-03, A13)."""
    client = TestClient(app)

    payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1200000.00"
    }
    # Sensitive transfer returns 202 Accepted and PENDING_MFA
    resp = client.post("/api/transfers", json=payload)
    assert resp.status_code == 202
    data = resp.json()

    assert data["status"] == "PENDING_MFA"
    assert data["expires_at"] is not None
    tx_id = data["id"]

    # Balance untouched while pending
    checking = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking["balance"] == "5000000.00"

    # Wrong PIN returns 401
    bad_resp = client.post(f"/api/transfers/{tx_id}/confirm-mfa", json={"code": "999999"})
    assert bad_resp.status_code == 401

    # Valid PIN 123456 confirms transfer
    good_resp = client.post(f"/api/transfers/{tx_id}/confirm-mfa", json={"code": "123456"})
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] == "COMPLETED"

    # Now balance is debited
    checking_after = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking_after["balance"] == "3800000.00"


def test_balance_and_history_across_internal_ach_recurring():
    """Verifies unified balance tracking and history across internal, ACH, and recurring transactions."""
    client = TestClient(app)

    # 1. Internal transfer: 100,000.00 (Checking -> Savings)
    client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00"
    })

    # 2. ACH transfer: 200,000.00
    client.post("/api/transfers/ach", json={
        "source_account_id": "acc_checking_123",
        "amount": "200000.00",
        "recipient_name": "Seguros del Estado",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "55667788",
        "save_beneficiary": False
    })

    # 3. Create due recurring schedule and execute it
    sched_resp = client.post("/api/recurring-schedules", json={
        "transfer_type": "INTERNAL",
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "50000.00",
        "frequency": "MONTHLY"
    })
    sched_id = sched_resp.json()["id"]

    # Make schedule due now
    conn = get_connection()
    past_due = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (past_due, sched_id))
    conn.commit()
    conn.close()

    # Trigger scheduler sweep
    sweep = client.post("/api/test/recurring/run-due")
    assert sweep.status_code == 200
    assert sweep.json()["processed_count"] == 1

    # Total debited from Checking: 100k + 200k + 50k = 350k -> 5,000,000 - 350,000 = 4,650,000.00
    checking = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_checking_123")
    assert checking["balance"] == "4650000.00"

    # Savings credited: 100k + 50k = 150k -> 15,000,000 + 150,000 = 15,150,000.00
    savings = next(a for a in client.get("/api/accounts").json() if a["id"] == "acc_savings_456")
    assert savings["balance"] == "15150000.00"

    # Account history contains all movements
    history = client.get("/api/accounts/acc_checking_123/history").json()
    # 2 seeded + 1 internal + 1 ACH + 1 recurring = 5 total movements
    assert len(history) == 5


def test_autonomous_lifespan_scheduler_ach_and_recurring():
    """Verifies that the autonomous background scheduler running inside FastAPI lifespan
    settles ACH transfers and processes due recurring schedules automatically without
    invoking test endpoints (ACH-06, REC-05, F-03, F-07).
    """
    import time

    with TestClient(app) as client:
        # 1. Create an ACH transfer
        ach_resp = client.post("/api/transfers/ach", json={
            "source_account_id": "acc_checking_123",
            "amount": "80000.00",
            "recipient_name": "Servicios Publicos",
            "bank_name": "Banco Davivienda",
            "routing_number": "123456789",
            "account_number": "11223344",
            "save_beneficiary": False
        })
        assert ach_resp.status_code == 201
        ach_id = ach_resp.json()["id"]

        # 2. Create a recurring schedule
        sched_resp = client.post("/api/recurring-schedules", json={
            "transfer_type": "INTERNAL",
            "source_account_id": "acc_checking_123",
            "destination_account_id": "acc_savings_456",
            "amount": "40000.00",
            "frequency": "WEEKLY"
        })
        assert sched_resp.status_code == 201
        sched_id = sched_resp.json()["id"]

        # 3. Fast-forward time for ACH (>= 10s old) and schedule (due in past) in database
        conn = get_connection()
        past_12s = (datetime.now(timezone.utc) - timedelta(seconds=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
        past_due = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("UPDATE transfers SET created_at = ? WHERE id = ?;", (past_12s, ach_id))
        conn.execute("UPDATE recurring_schedules SET next_due_date = ? WHERE id = ?;", (past_due, sched_id))
        conn.commit()
        conn.close()

        # 4. Wait for background scheduler autonomous loop to tick (interval is 5.0s)
        settled = False
        recurring_processed = False
        for _ in range(14):  # poll up to 7 seconds
            time.sleep(0.5)
            conn = get_connection()
            ach_status = conn.execute("SELECT status FROM transfers WHERE id = ?;", (ach_id,)).fetchone()[0]
            sched_next = conn.execute("SELECT next_due_date FROM recurring_schedules WHERE id = ?;", (sched_id,)).fetchone()[0]
            conn.close()

            if ach_status == "SETTLED":
                settled = True
            if sched_next > past_due:
                recurring_processed = True

            if settled and recurring_processed:
                break

        assert settled, "ACH transfer was not settled autonomously by the background scheduler"
        assert recurring_processed, "Due recurring schedule was not processed autonomously by the background scheduler"

        # Verify balance and history updated by background execution
        accounts = client.get("/api/accounts").json()
        checking = next(a for a in accounts if a["id"] == "acc_checking_123")
        # 5,000,000 - 80,000 (ACH) - 40,000 (Recurring) = 4,880,000.00
        assert checking["balance"] == "4880000.00"

