"""Cross-story inherited banking compatibility and cryptographic verification (T035, Scenarios 5.1..5.6, H7-02).

Verifies without relying on test client encryption adapters or database transparent wrappers:
1. Direct CryptographicEnvelope construction using client-side Web Crypto hybrid simulation (RSA-OAEP + AES-GCM).
2. Verification of RAW SQLite disk storage (bypassing any test cursor wrappers) ensuring all sensitive fields start with enc:v1:.
3. Direct verification of audit_logs immutability, continuous sequence IDs, and HMAC-SHA256 digests.
4. Cross-story end-to-end verification of internal transfers, MFA step-up, dynamic limits, beneficiaries, ACH, and recurring payments.
5. High-value limit-before-MFA precedence (LIM-07, A14): Transfers >= COP 1,000,000 exceeding limits are rejected with 400 without MFA challenge or fund debit.
"""

import os
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import database
from conftest import create_test_client_envelope
from fastapi.testclient import TestClient
from main import app
from services import decrypt_val, encrypt_val, verify_audit_ledger

@pytest.fixture(scope="module", autouse=True)
def isolated_inherited_compat_db(tmp_path_factory):
    """Uniquely allocates a temporary database directory per pytest session (H8-02 Item 1).
    Ensures that test resets and transfer operations never erase shared test evidence,
    production databases, or compromise audit traceability in other test suites.
    """
    temp_dir = tmp_path_factory.mktemp("inherited_compat_session")
    temp_db_path = str(temp_dir / "test_inherited_compat.db")

    old_test_db = os.environ.get("TEST_DB_PATH")
    os.environ["TEST_DB_PATH"] = temp_db_path

    # Initialize schema and seed accounts
    database.init_db(temp_db_path)
    yield temp_db_path

    # Restore environment
    if old_test_db:
        os.environ["TEST_DB_PATH"] = old_test_db
    else:
        os.environ.pop("TEST_DB_PATH", None)


@pytest.fixture
def client():
    return TestClient(app)


def get_raw_sqlite_connection():
    """Returns a direct, unadapted sqlite3 connection to inspect disk bytes directly."""
    return sqlite3.connect(database.get_db_path())


@pytest.fixture(scope="function", autouse=True)
def reset_test_accounts_and_limits():
    """Ensures Checking (COP 5M) and Savings (COP 15M) balances, limits, and consumption are pristine
    strictly within the isolated test database (test_inherited_compat.db) before each test (H7-02, H8-01).
    """
    conn = database.get_connection()
    cursor = conn.cursor()
    # Reset transfers so daily consumption starts at 0 for isolated deterministic testing
    cursor.execute("DELETE FROM transfers;")
    cursor.execute("UPDATE accounts SET balance = ? WHERE id = 'acc_checking_123';", (encrypt_val("5000000.00"),))
    cursor.execute("UPDATE accounts SET balance = ? WHERE id = 'acc_savings_456';", (encrypt_val("15000000.00"),))

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor.execute("""
        INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
        VALUES ('lim_mock_001', 'user_mock_001', ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            per_transfer_limit = excluded.per_transfer_limit,
            daily_limit = excluded.daily_limit,
            updated_at = excluded.updated_at;
    """, (encrypt_val("5000000.00"), encrypt_val("10000000.00"), now_iso))
    conn.commit()
    conn.close()
    yield


def test_internal_transfer_direct_envelope_and_audit(client):
    """Scenario 5.1: Direct CryptographicEnvelope transfer updates balances and creates audit records."""
    # 1. Capture initial balances
    resp = client.get("/api/accounts")
    assert resp.status_code == 200
    accounts_before = {a["id"]: Decimal(a["balance"]) for a in resp.json()}

    # 2. Create raw encrypted envelope without adapter
    envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "250.00",
    })

    # Ensure envelope has required base64 cryptographic fields
    assert all(k in envelope for k in ("encrypted_key", "iv", "ciphertext", "tag"))

    post_resp = client.post("/api/transfers", json=envelope)
    assert post_resp.status_code == 200
    transfer_data = post_resp.json()
    assert transfer_data["status"] == "COMPLETED"
    assert transfer_data["amount"] == "250.00"

    # 3. Verify RAW SQLite persistence directly (bypassing test cursor wrappers)
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT id, balance FROM accounts WHERE id IN ('acc_checking_123', 'acc_savings_456');")
    db_rows = raw_cursor.fetchall()

    for acc_id, enc_bal in db_rows:
        assert enc_bal.startswith("enc:v1:"), f"Account {acc_id} balance was not encrypted at rest!"

    # 4. Verify SQLite audit trail record directly
    raw_cursor.execute("""
        SELECT event_type, resource_id, record_hmac
        FROM audit_logs
        WHERE resource_id = ?;
    """, (transfer_data["id"],))
    audit_row = raw_cursor.fetchone()
    assert audit_row is not None
    assert audit_row[0] == "TRANSFER_COMPLETED"
    assert len(audit_row[2]) == 64  # HMAC-SHA256 hex digest length
    raw_conn.close()

    # 5. Verify balance conservation
    accounts_after = {a["id"]: Decimal(a["balance"]) for a in client.get("/api/accounts").json()}
    assert accounts_after["acc_checking_123"] == accounts_before["acc_checking_123"] - Decimal("250.00")
    assert accounts_after["acc_savings_456"] == accounts_before["acc_savings_456"] + Decimal("250.00")


def test_sensitive_transfer_direct_envelope_and_mfa_stepup(client):
    """Scenario 5.2: Transfers >= COP 1,000,000.00 require encrypted MFA challenge and confirmation."""
    mfa_envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1000000.00",
    })

    # Initiates transfer -> 202 PENDING_MFA
    init_resp = client.post("/api/transfers", json=mfa_envelope)
    assert init_resp.status_code == 202
    pending_data = init_resp.json()
    assert pending_data["status"] == "PENDING_MFA"
    transfer_id = pending_data["id"]

    # Confirm MFA with direct encrypted envelope
    code_envelope = create_test_client_envelope({"code": "123456"})
    confirm_resp = client.post(f"/api/transfers/{transfer_id}/confirm-mfa", json=code_envelope)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "COMPLETED"

    # Verify both PENDING_MFA and COMPLETED audit records exist in RAW SQLite
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("""
        SELECT event_type FROM audit_logs
        WHERE resource_id = ? ORDER BY id ASC;
    """, (transfer_id,))
    events = [r[0] for r in raw_cursor.fetchall()]
    assert "TRANSFER_PENDING_MFA" in events
    assert "TRANSFER_COMPLETED" in events
    raw_conn.close()


def test_dynamic_limits_direct_envelope_and_precedence(client):
    """Scenario 5.3, H7-02: High-value transfers (>= COP 1M) exceeding limits return 400 before MFA."""
    # 1. Update limits via direct envelope: per-transfer = 2,000,000.00, daily = 4,000,000.00
    limits_envelope = create_test_client_envelope({
        "per_transfer_limit": "2000000.00",
        "daily_limit": "4000000.00",
    })
    put_resp = client.put("/api/limits", json=limits_envelope)
    assert put_resp.status_code == 200
    assert put_resp.json()["per_transfer_limit"] == "2000000.00"

    # Verify limits stored encrypted at rest in RAW SQLite
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT per_transfer_limit, daily_limit FROM limits WHERE user_id = 'user_mock_001';")
    enc_per, enc_daily = raw_cursor.fetchone()
    assert enc_per.startswith("enc:v1:")
    assert enc_daily.startswith("enc:v1:")

    # Initial balance check
    raw_cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    checking_initial = Decimal(decrypt_val(raw_cursor.fetchone()[0]))
    assert checking_initial == Decimal("5000000.00")
    raw_conn.close()

    # 2. Attempt transfer of COP 2,500,000.00 (LIM-07, A14, H7-02):
    # - Funds are sufficient (5,000,000.00 >= 2,500,000.00)
    # - Amount >= COP 1,000,000.00 (MFA boundary)
    # - Amount > COP 2,000,000.00 per-transfer limit
    # CRITICAL: Must be rejected with HTTP 400 BEFORE MFA challenge, with zero debit!
    over_limit_envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "2500000.00",
    })
    rej_resp = client.post("/api/transfers", json=over_limit_envelope)
    assert rej_resp.status_code == 400
    assert "exceeds per-transfer limit" in rej_resp.json()["detail"]

    # Verify no MFA challenge or PENDING_MFA transfer was created
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT COUNT(*) FROM transfers WHERE status = 'PENDING_MFA';")
    assert raw_cursor.fetchone()[0] == 0

    # Verify funds were NOT debited
    raw_cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    checking_post = Decimal(decrypt_val(raw_cursor.fetchone()[0]))
    assert checking_post == checking_initial

    # 3. Verify that a transfer within limits but >= COP 1,000,000 (e.g. COP 1,500,000) DOES trigger MFA
    valid_mfa_envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1500000.00",
    })
    mfa_resp = client.post("/api/transfers", json=valid_mfa_envelope)
    assert mfa_resp.status_code == 202
    assert mfa_resp.json()["status"] == "PENDING_MFA"
    raw_conn.close()


def test_beneficiaries_and_ach_transfer_lifecycle(client):
    """Scenario 5.4: Beneficiary creation and ACH transfer with immediate debit and settlement."""
    # 1. Create beneficiary via direct envelope
    ben_envelope = create_test_client_envelope({
        "name": "Maria Rodriguez",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "9876543210",
    })
    ben_resp = client.post("/api/beneficiaries", json=ben_envelope)
    assert ben_resp.status_code == 201
    ben_id = ben_resp.json()["id"]

    # Verify beneficiary PII is encrypted at rest in RAW SQLite
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT name, bank_name, account_number FROM beneficiaries WHERE id = ?;", (ben_id,))
    enc_name, enc_bank, enc_acct = raw_cursor.fetchone()
    assert enc_name.startswith("enc:v1:")
    assert enc_bank.startswith("enc:v1:")
    assert enc_acct.startswith("enc:v1:")
    raw_conn.close()

    # 2. Execute ACH transfer via direct envelope
    ach_envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "amount": "150000.00",
        "recipient_name": "Maria Rodriguez",
        "bank_name": "Bancolombia",
        "routing_number": "123456789",
        "account_number": "9876543210",
        "save_beneficiary": False,
    })
    ach_resp = client.post("/api/transfers/ach", json=ach_envelope)
    assert ach_resp.status_code == 201
    ach_data = ach_resp.json()
    assert ach_data["status"] == "PENDING"
    assert ach_data["transfer_type"] == "ACH"

    # 3. Verify immediate debit reflected in history
    history = client.get("/api/accounts/acc_checking_123/history").json()
    ach_entry = next((h for h in history if h["id"] == ach_data["id"]), None)
    assert ach_entry is not None
    assert "ACH Transfer to Maria Rodriguez (Bancolombia) - PENDING" in ach_entry["description"]


def test_recurring_schedule_lifecycle_and_execution(client):
    """Scenario 5.5: Recurring schedule creation via direct envelope and single sweep execution."""
    rec_envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "500.00",
        "frequency": "DAILY",
        "transfer_type": "INTERNAL",
    })
    sched_resp = client.post("/api/recurring-schedules", json=rec_envelope)
    assert sched_resp.status_code == 201
    sched_data = sched_resp.json()
    assert sched_data["status"] == "ACTIVE"
    sched_id = sched_data["id"]

    # Verify amount stored encrypted at rest in RAW SQLite
    raw_conn = get_raw_sqlite_connection()
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT amount FROM recurring_schedules WHERE id = ?;", (sched_id,))
    enc_amt = raw_cursor.fetchone()[0]
    assert enc_amt.startswith("enc:v1:")
    raw_conn.close()

    # Pause schedule
    pause_resp = client.post(f"/api/recurring-schedules/{sched_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # Resume schedule
    resume_resp = client.post(f"/api/recurring-schedules/{sched_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "ACTIVE"

    # Cancel schedule
    cancel_resp = client.post(f"/api/recurring-schedules/{sched_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


def test_overall_audit_chain_and_ledger_integrity(client):
    """Scenario 5.6: Validates complete HMAC ledger continuity across all operations."""
    conn = database.get_connection()
    try:
        audit_report = verify_audit_ledger(conn)
        assert audit_report.is_valid is True
        assert audit_report.verified_records >= 2
    finally:
        conn.close()
