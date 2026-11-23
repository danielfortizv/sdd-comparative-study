import os
import sqlite3
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

import database
import crypto
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers():
    admin_key = os.environ.get("AUDIT_ADMIN_KEY", "test_admin_key")
    return {"X-Audit-Admin-Key": admin_key}


def get_raw_test_db():
    conn = sqlite3.connect(database.get_db_path(), timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def test_audit_record_created_atomically_with_internal_transfer(client):
    """Verifies that an internal transfer atomically writes a chained audit log entry (FR-014..FR-017)."""
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audit_logs;")
    initial_count = cursor.fetchone()[0]
    raw_conn.close()

    res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "150000.00",
    })
    assert res.status_code == 200

    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac FROM audit_logs ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    raw_conn.close()

    assert row is not None
    seq_id, event_type, actor_id, resource_id, digest, prev_hash, record_hmac = row
    assert seq_id > initial_count
    assert event_type in ("TRANSFER_COMPLETED", "TRANSFER_CREATED")
    assert actor_id == "user_mock_001"
    assert resource_id.startswith("tr_")
    assert len(digest) == 64
    assert len(record_hmac) == 64


def test_audit_fail_closed_rollback_on_audit_failure(client, monkeypatch):
    """Verifies that if the audit log write fails, the entire financial operation rolls back (FR-017)."""
    import services
    import api

    def broken_audit_write(*args, **kwargs):
        raise RuntimeError("Simulated audit storage failure")

    monkeypatch.setattr(services, "append_audit_record", broken_audit_write)
    monkeypatch.setattr(api, "append_audit_record", broken_audit_write)

    # Check checking balance before attempt
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    bal_before = cursor.fetchone()[0]
    raw_conn.close()

    res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "250000.00",
    })
    assert res.status_code == 500

    # Verify checking balance was rolled back completely (fail-closed)
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_checking_123';")
    bal_after = cursor.fetchone()[0]
    raw_conn.close()

    assert bal_after == bal_before


def test_audit_rejected_operation_logged_in_separate_transaction(client):
    """Verifies that rejected operations (e.g. limit exceeded or insufficient funds) are recorded in audit logs (FR-018)."""
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audit_logs;")
    count_before = cursor.fetchone()[0]
    raw_conn.close()

    # Attempt transfer exceeding balance
    res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "99000000.00",
    })
    assert res.status_code == 400

    # Verify an audit record for rejection exists
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id, event_type, actor_id FROM audit_logs ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    raw_conn.close()

    assert row is not None
    seq_id, event_type, actor_id = row
    assert seq_id > count_before
    assert "REJECTED" in event_type or "FAILED" in event_type or "LIMIT" in event_type


def test_audit_privacy_no_plaintext_pins_or_secrets(client):
    """Verifies that plaintext MFA PINs or raw secrets never appear in audit payloads or columns (FR-008, E3-AUD-01)."""
    # 1. Initiate sensitive transfer
    res = client.post("/api/transfers", json={
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1200000.00",
    })
    assert res.status_code == 202
    tx_id = res.json()["id"]

    # 2. Confirm MFA with code 123456
    confirm_res = client.post(f"/api/transfers/{tx_id}/confirm-mfa", json={"code": "123456"})
    assert confirm_res.status_code == 200

    # 3. Inspect audit_logs
    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id, event_type, payload_digest, record_hmac FROM audit_logs;")
    rows = cursor.fetchall()
    raw_conn.close()

    for r in rows:
        row_str = " ".join(str(item) for item in r)
        assert "123456" not in row_str
        assert os.environ["BANK_STORAGE_KEY"] not in row_str
        assert os.environ["AUDIT_SIGNING_KEY"] not in row_str


def test_audit_immutability_triggers_prevent_update_and_delete(tmp_path):
    """Verifies that SQLite triggers prevent ordinary UPDATE and DELETE operations on audit_logs (FR-020)."""
    isolated_db = str(tmp_path / "trigger_test.db")
    database.init_db(isolated_db)

    raw_conn = sqlite3.connect(isolated_db, timeout=30.0)
    cursor = raw_conn.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (id, timestamp, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac)
        VALUES (1, '2026-11-15T20:00:00Z', 'TEST_EVENT', 'user_mock_001', 'test_res', 'digest', 'prev', 'hmac');
    """)
    raw_conn.commit()

    # Attempt UPDATE
    with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError)) as exc_update:
        cursor.execute("UPDATE audit_logs SET event_type = 'MODIFIED' WHERE id = 1;")
    assert "Audit log is append-only" in str(exc_update.value) or "immutable" in str(exc_update.value).lower()

    # Attempt DELETE
    with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError)) as exc_delete:
        cursor.execute("DELETE FROM audit_logs WHERE id = 1;")
    assert "Audit log is append-only" in str(exc_delete.value) or "immutable" in str(exc_delete.value).lower()

    raw_conn.close()


def test_audit_verification_endpoint_authorized_success(client, admin_headers):
    """Verifies that GET /api/audit/verify returns 200 with is_valid=True for an authorized request (FR-021, FR-022)."""
    res = client.get("/api/audit/verify", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["verified_records"] >= 0
    assert data["broken_sequence"] is None


def test_audit_verification_endpoint_unauthorized_rejection(client):
    """Verifies that GET /api/audit/verify rejects requests lacking valid administrative credentials (FR-022)."""
    # 1. No credentials provided
    res1 = client.get("/api/audit/verify")
    assert res1.status_code in (401, 403)

    # 2. Invalid credentials provided
    res2 = client.get("/api/audit/verify", headers={"X-Audit-Admin-Key": "invalid_wrong_token"})
    assert res2.status_code in (401, 403)


def test_audit_verification_detects_record_tampering(tmp_path):
    """Verifies that modifying an audit record's payload digest or link is detected by verification (FR-021)."""
    isolated_db = str(tmp_path / "tamper_test.db")
    database.init_db(isolated_db)

    conn = database.get_connection(isolated_db)
    cursor = conn.cursor()

    # Add 2 valid records
    from services import append_audit_record, verify_audit_ledger
    append_audit_record(cursor, "EVENT_1", "user_mock_001", "res_1", {"key": "val1"})
    append_audit_record(cursor, "EVENT_2", "user_mock_001", "res_2", {"key": "val2"})
    conn.commit()

    # Verify baseline is valid
    res_clean = verify_audit_ledger(conn)
    assert res_clean.is_valid is True

    # Tamper with record 1 digest out-of-band (disabling trigger temporarily)
    cursor.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update;")
    cursor.execute("UPDATE audit_logs SET payload_digest = 'tampered_bad_digest' WHERE id = 1;")
    conn.commit()

    # Verify tamper is detected
    res_tampered = verify_audit_ledger(conn)
    assert res_tampered.is_valid is False
    assert res_tampered.broken_sequence == 1
    conn.close()


def test_audit_tail_truncation_detected_with_external_checkpoint(tmp_path):
    """Verifies that tail truncation is detected when verified against an external trusted checkpoint (FR-023)."""
    isolated_db = str(tmp_path / "truncation_test.db")
    database.init_db(isolated_db)

    conn = database.get_connection(isolated_db)
    cursor = conn.cursor()

    from services import append_audit_record, verify_audit_ledger
    append_audit_record(cursor, "EVENT_1", "user_mock_001", "res_1")
    append_audit_record(cursor, "EVENT_2", "user_mock_001", "res_2")
    conn.commit()

    # Capture checkpoint of current head (seq=2)
    cursor.execute("SELECT id, record_hmac FROM audit_logs WHERE id = 2;")
    head_seq, head_hmac = cursor.fetchone()

    # Truncate record 2 out-of-band
    cursor.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete;")
    cursor.execute("DELETE FROM audit_logs WHERE id = 2;")
    conn.commit()

    # Verify against external checkpoint (expected_count=head_seq, expected_head_hash=head_hmac)
    res = verify_audit_ledger(conn, expected_head_hash=head_hmac, expected_count=head_seq)
    assert res.is_valid is False
    assert res.tail_truncation_detected is True
    conn.close()


def test_concurrent_audit_writes_no_duplicate_or_missing_sequences(client):
    """Verifies that sequential/concurrent transactions allocate strictly contiguous gap-free sequence numbers (FR-015, T007)."""
    for i in range(5):
        r = client.post("/api/transfers", json={
            "source_account_id": "acc_checking_123",
            "destination_account_id": "acc_savings_456",
            "amount": f"100{i}.00",
        })
        assert r.status_code == 200

    raw_conn = get_raw_test_db()
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id FROM audit_logs ORDER BY id ASC;")
    ids = [r[0] for r in cursor.fetchall()]
    raw_conn.close()

    assert len(ids) >= 5
    for i in range(len(ids) - 1):
        assert ids[i + 1] == ids[i] + 1, f"Sequence gap found between {ids[i]} and {ids[i+1]}"
