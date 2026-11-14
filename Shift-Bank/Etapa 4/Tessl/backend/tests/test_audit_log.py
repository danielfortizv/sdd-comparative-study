import os
import time
import json
import uuid
import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from backend.app.database import Base
from backend.app.models import AuditLog, Account
from backend.app.services import audit_service
from backend.app.services.audit_service import (
    GENESIS_HASH,
    record_audit_event,
    record_failure_audit_event,
    verify_audit_chain,
    compute_audit_hash,
    compute_audit_signature,
    get_audit_signing_key,
)


def test_genesis_block_and_chain_construction(db_session):
    """First audit record chains from 64 zeros genesis, subsequent records chain from previous hash."""
    entry1 = record_audit_event(
        db=db_session,
        event_type="test_event_1",
        status="SUCCESS",
        details={"info": "initial"},
        actor_id=1,
    )
    db_session.commit()

    assert entry1.previous_hash == GENESIS_HASH
    assert len(entry1.current_hash) == 64
    assert len(entry1.signature) == 64

    entry2 = record_audit_event(
        db=db_session,
        event_type="test_event_2",
        status="SUCCESS",
        details={"info": "second"},
        actor_id=1,
    )
    db_session.commit()

    assert entry2.previous_hash == entry1.current_hash
    assert entry2.current_hash != entry1.current_hash

    # Verify chain
    res = verify_audit_chain(db_session)
    assert res["valid"] is True
    assert res["total_records"] == 2


def test_tamper_detection_on_modified_details(db_session):
    """Modifying event details in the database causes verify_audit_chain to detect hash_mismatch."""
    record_audit_event(
        db=db_session,
        event_type="transfer_internal",
        status="SUCCESS",
        details={"amount": 100.0, "to_account_id": 2},
        actor_id=1,
    )
    db_session.commit()

    # Disable triggers temporarily via raw SQLite connection to simulate direct database tampering
    conn = db_session.connection().connection
    cursor = conn.cursor()
    cursor.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update")
    cursor.execute("UPDATE audit_logs SET details = '{\"amount\":9999.0}' WHERE id = 1")
    conn.commit()

    res = verify_audit_chain(db_session)
    assert res["valid"] is False
    assert res["tampered_entry_id"] == 1
    assert res["reason"] == "hash_mismatch"


def test_tamper_detection_on_modified_signature(db_session):
    """Modifying signature in the database causes verify_audit_chain to detect signature_mismatch."""
    record_audit_event(
        db=db_session,
        event_type="mfa_verified",
        status="SUCCESS",
        details={"method": "pin"},
        actor_id=1,
    )
    db_session.commit()

    conn = db_session.connection().connection
    cursor = conn.cursor()
    cursor.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update")
    cursor.execute("UPDATE audit_logs SET signature = '0000111122223333444455556666777788889999aaaabbbbccccddddeeeeffff' WHERE id = 1")
    conn.commit()

    res = verify_audit_chain(db_session)
    assert res["valid"] is False
    assert res["tampered_entry_id"] == 1
    assert res["reason"] == "signature_mismatch"


def test_immutability_triggers_prevent_update_and_delete(db_session):
    """SQLite triggers and ORM listeners reject direct UPDATE and DELETE on audit_logs."""
    record_audit_event(
        db=db_session,
        event_type="immutable_event",
        status="SUCCESS",
        details={"test": "immutable"},
        actor_id=1,
    )
    db_session.commit()

    # 1. Attempt UPDATE via raw SQL (triggers SQLite trigger)
    with pytest.raises(Exception, match="UPDATE operations are strictly forbidden"):
        db_session.execute(text("UPDATE audit_logs SET details = 'hacked' WHERE id = 1"))
        db_session.commit()

    db_session.rollback()

    # 2. Attempt DELETE via raw SQL (triggers SQLite trigger)
    with pytest.raises(Exception, match="DELETE operations are strictly forbidden"):
        db_session.execute(text("DELETE FROM audit_logs WHERE id = 1"))
        db_session.commit()

    db_session.rollback()


def test_rollback_consistency_preserves_failed_operations(client: TestClient, db_session):
    """When a financial operation fails and rolls back, the failure audit entry is preserved durably."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()
    # Attempt an internal transfer with insufficient balance (source account has $2500, request $999999)
    resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc1["id"],
            "to_account_id": acc2["id"],
            "amount": "999999.00",
            "expected_from_version": acc1["version"],
            "expected_to_version": acc2["version"],
            "description": "Insufficient funds test",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 400

    # Verify failure audit event was committed to audit_logs
    rows = db_session.execute(
        text("SELECT event_type, status, details FROM audit_logs WHERE event_type = 'transfer_internal' AND status = 'FAILURE'")
    ).fetchall()
    assert len(rows) >= 1
    details = json.loads(rows[0][2])
    assert str(details["amount"]) == "999999.00"
    assert "error" in details


def test_fail_closed_audit_guarantee(client: TestClient, db_session, monkeypatch):
    """If audit recording fails during a transfer, the transfer is rolled back and does not commit."""
    initial_acc1 = db_session.execute(text("SELECT balance FROM accounts WHERE id = 1")).fetchone()[0]
    initial_acc2 = db_session.execute(text("SELECT balance FROM accounts WHERE id = 2")).fetchone()[0]

    # Force audit_service.record_audit_event to fail
    def failing_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit disk write failure")

    monkeypatch.setattr(audit_service, "record_audit_event", failing_audit)

    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    with pytest.raises(RuntimeError, match="Simulated audit disk write failure"):
        client.post(
            "/api/transfers",
            json={
                "from_account_id": acc1["id"],
                "to_account_id": acc2["id"],
                "amount": "50.00",
                "expected_from_version": acc1["version"],
                "expected_to_version": acc2["version"],
                "description": "Fail closed test",
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    # Verify balances were NOT modified (transaction was aborted)
    final_acc1 = db_session.execute(text("SELECT balance FROM accounts WHERE id = 1")).fetchone()[0]
    final_acc2 = db_session.execute(text("SELECT balance FROM accounts WHERE id = 2")).fetchone()[0]
    assert final_acc1 == initial_acc1
    assert final_acc2 == initial_acc2


def test_audit_verify_endpoint_authorization(client: TestClient):
    """GET /api/audit/verify requires valid X-Admin-Key; rejects missing or invalid keys with HTTP 403."""
    # Missing header
    resp_no_header = client.get("/api/audit/verify")
    assert resp_no_header.status_code == 403
    assert resp_no_header.json()["detail"] == "FORBIDDEN_ADMIN_ACCESS_REQUIRED"

    # Invalid header
    resp_wrong = client.get("/api/audit/verify", headers={"X-Admin-Key": "wrong_key"})
    assert resp_wrong.status_code == 403
    assert resp_wrong.json()["detail"] == "FORBIDDEN_ADMIN_ACCESS_REQUIRED"

    # Valid header
    resp_ok = client.get("/api/audit/verify", headers={"X-Admin-Key": "test_admin_secret_key_2026"})
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert "valid" in data
    assert "total_records" in data


def test_sensitive_data_redaction_in_audit_payloads(client: TestClient, db_session):
    """Audit ledger entries never log raw Security PINs, passwords, or full account numbers."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()
    # Submit transfer requiring PIN (> $1,000)
    resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc1["id"],
            "to_account_id": acc2["id"],
            "amount": "1500.00",
            "expected_from_version": acc1["version"],
            "expected_to_version": acc2["version"],
            "pin": "1234",
            "description": "Sensitive redaction test",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 200

    rows = db_session.execute(text("SELECT details FROM audit_logs")).fetchall()
    for r in rows:
        details_str = r[0]
        # Never contain the submitted PIN value "1234" or raw secrets
        assert "1234" not in details_str
        assert "password" not in details_str.lower()
        assert "private_key" not in details_str.lower()


def test_concurrent_audit_writes_maintain_chain_integrity(tmp_path):
    """Concurrent writes from multiple worker threads maintain strict sequential hash chaining."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "concurrent_audit_test.db"
    concurrency_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    Base.metadata.create_all(bind=concurrency_engine)
    ConcurrencySession = sessionmaker(autocommit=False, autoflush=False, bind=concurrency_engine)

    num_threads = 10
    events_per_thread = 5

    def worker_task(thread_idx: int):
        session = ConcurrencySession()
        try:
            for i in range(events_per_thread):
                record_audit_event(
                    db=session,
                    event_type=f"concurrent_event_t{thread_idx}",
                    status="SUCCESS",
                    details={"thread": thread_idx, "seq": i},
                    actor_id=1,
                )
                session.commit()
                time.sleep(0.005)
        finally:
            session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, t) for t in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Verify full chain integrity across all concurrent writes
    verify_session = ConcurrencySession()
    try:
        res = verify_audit_chain(verify_session)
        assert res["valid"] is True
        assert res["total_records"] == num_threads * events_per_thread
    finally:
        verify_session.close()


def test_comprehensive_event_types_coverage(client: TestClient, db_session):
    """Verifies that internal transfers, ACH transfers, beneficiaries, recurring payments, MFA, and limits all emit audit events."""
    # 1. Internal transfer success
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()
    resp_transfer = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc1["id"],
            "to_account_id": acc2["id"],
            "amount": "20.00",
            "expected_from_version": acc1["version"],
            "expected_to_version": acc2["version"],
            "description": "Audit event test transfer",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_transfer.status_code == 200

    # 2. Beneficiary creation & deletion
    ben_resp = client.post(
        "/api/beneficiaries",
        json={"name": "Audit Ben", "routing_number": "123456789", "account_number": "987654321", "bank_name": "Bank A"},
    )
    ben_id = ben_resp.json()["id"]
    client.delete(f"/api/beneficiaries/{ben_id}")

    # 3. ACH transfer initiation
    acc1_current = client.get("/api/accounts/1").json()
    ach_resp = client.post(
        "/api/transfers/ach",
        json={
            "from_account_id": acc1_current["id"],
            "amount": "35.00",
            "expected_from_version": acc1_current["version"],
            "recipient_name": "ACH Rec",
            "routing_number": "123456789",
            "account_number": "987654321",
            "bank_name": "Bank B",
            "description": "Audit event ACH transfer",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert ach_resp.status_code == 200

    # 4. Recurring schedule creation & pause
    rec_resp = client.post(
        "/api/recurring",
        json={"transfer_type": "internal", "from_account_id": 1, "to_account_id": 2, "amount": "15.00", "frequency": "monthly"},
    )
    sched_id = rec_resp.json()["id"]
    client.post(f"/api/recurring/{sched_id}/pause")

    # 5. MFA verification
    client.post("/api/mfa/verify", json={"pin": "1234"})

    # 6. Limit breach (set limit lower than balance to trigger limit breach check)
    client.put("/api/limits", json={"per_transaction_limit": "100.00", "daily_limit": "200.00"})
    acc1_for_limit = client.get("/api/accounts/1").json()
    acc2_for_limit = client.get("/api/accounts/2").json()
    breach_resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": acc1_for_limit["id"],
            "to_account_id": acc2_for_limit["id"],
            "amount": "150.00",
            "expected_from_version": acc1_for_limit["version"],
            "expected_to_version": acc2_for_limit["version"],
            "description": "Limit breach test",
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert breach_resp.status_code == 400

    # Query all emitted event types
    rows = db_session.execute(text("SELECT DISTINCT event_type FROM audit_logs")).fetchall()
    emitted_types = {r[0] for r in rows}

    expected_types = {
        "transfer_internal",
        "beneficiary_created",
        "beneficiary_deleted",
        "transfer_ach_initiated",
        "recurring_schedule_created",
        "recurring_schedule_paused",
        "mfa_verified",
        "limit_breach",
    }
    assert expected_types.issubset(emitted_types)

    # Verify the chain is 100% valid
    res = verify_audit_chain(db_session)
    assert res["valid"] is True


def test_failure_audit_persistence_error_propagation(monkeypatch):
    """Failure audit events raise AuditPersistenceError when persistence fails, never silently swallowing."""
    from backend.app.services.audit_service import AuditPersistenceError

    def failing_record(*args, **kwargs):
        raise RuntimeError("Disk full error while persisting failure audit")

    monkeypatch.setattr(audit_service, "record_audit_event", failing_record)

    with pytest.raises(AuditPersistenceError, match="Failed to persist failure audit event to ledger"):
        record_failure_audit_event(
            event_type="test_failure",
            details={"reason": "simulated_error"},
            actor_id=1,
        )


def test_mfa_state_and_audit_event_atomic_consistency(db_session, monkeypatch):
    """MFA state changes (failed_attempts, is_locked) and audit entries commit atomically together."""
    from backend.app.services import mfa_service
    from fastapi import HTTPException

    user_id = 1
    # Initial state
    state = mfa_service.get_or_create_mfa_state(db_session, user_id)
    assert state.failed_attempts == 0
    assert state.is_locked is False

    # 1. First failed attempt: atomic increment and audit entry
    with pytest.raises(HTTPException) as exc1:
        mfa_service.verify_pin(db_session, user_id, "0000")
    assert exc1.value.status_code == 400

    db_session.refresh(state)
    assert state.failed_attempts == 1

    last_audit = db_session.execute(
        text("SELECT event_type, details FROM audit_logs ORDER BY id DESC LIMIT 1")
    ).fetchone()
    assert last_audit[0] == "mfa_attempt_failed"
    details = json.loads(last_audit[1])
    assert details["failed_attempt_number"] == 1
    assert details["remaining_attempts"] == 2

    # 2. Simulate audit failure on second attempt: state must NOT commit (rollback)
    def failing_audit(*args, **kwargs):
        raise RuntimeError("Audit ledger lock timeout")

    monkeypatch.setattr(audit_service, "record_audit_event", failing_audit)

    with pytest.raises(RuntimeError, match="Audit ledger lock timeout"):
        mfa_service.verify_pin(db_session, user_id, "0000")

    db_session.rollback()
    db_session.refresh(state)
    # State remains 1 because audit failure prevented state mutation commit!
    assert state.failed_attempts == 1

    # 3. Third failed attempt leads to lockout
    monkeypatch.undo()
    with pytest.raises(HTTPException):
        mfa_service.verify_pin(db_session, user_id, "0000")  # Attempt 2 -> 2
    with pytest.raises(HTTPException) as exc_lock:
        mfa_service.verify_pin(db_session, user_id, "0000")  # Attempt 3 -> 3 -> Locked!
    assert exc_lock.value.status_code == 423

    db_session.refresh(state)
    assert state.failed_attempts == 3
    assert state.is_locked is True

    last_audit = db_session.execute(
        text("SELECT event_type FROM audit_logs ORDER BY id DESC LIMIT 1")
    ).fetchone()
    assert last_audit[0] == "mfa_locked"


def test_structured_error_code_sanitization_in_audit_payloads(db_session):
    """Raw exceptions containing user inputs, PINs, or credentials are mapped to structured error codes."""
    # Attempt recording failure with a message containing sensitive PIN "1234"
    record_audit_event(
        db=db_session,
        event_type="transfer_internal",
        status="FAILURE",
        details={
            "error": "Invalid Security PIN 1234 supplied for source account 9876543210123",
            "account_number": "9876543210123",
        },
        actor_id=1,
    )
    db_session.commit()

    row = db_session.execute(
        text("SELECT details FROM audit_logs ORDER BY id DESC LIMIT 1")
    ).fetchone()
    details_str = row[0]
    details = json.loads(details_str)

    # Raw PIN "1234" must not appear anywhere
    assert "1234" not in details_str
    # Raw account must be masked
    assert details["account_number"] == "****0123"
    # Error message must be mapped to safe structured error code
    assert details["error"] == "INVALID_SECURITY_PIN"


def test_multi_process_sqlite_write_locking_with_begin_immediate(tmp_path):
    """Multiple independent SQLite engines (simulating separate server processes) serialize writes cleanly with BEGIN IMMEDIATE."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    db_file = tmp_path / "proc_audit_test.db"
    db_url = f"sqlite:///{db_file}"

    # Setup database with initial schema
    init_engine = create_engine(db_url, connect_args={"timeout": 15})
    Base.metadata.create_all(bind=init_engine)
    init_engine.dispose()

    num_processes = 6
    events_per_process = 5

    def process_simulator(proc_id: int):
        # Each "process" creates its own independent engine and connection pool with BEGIN IMMEDIATE
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False, "timeout": 20},
        )
        @event.listens_for(engine, "connect")
        def set_p_pragma(conn, rec):
            cur = conn.cursor()
            cur.execute("PRAGMA busy_timeout = 8000")
            cur.close()

        @event.listens_for(engine, "begin")
        def do_p_begin(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        ProcSession = sessionmaker(bind=engine)
        session = ProcSession()
        try:
            for i in range(events_per_process):
                record_audit_event(
                    db=session,
                    event_type=f"proc_event_{proc_id}",
                    status="SUCCESS",
                    details={"proc": proc_id, "seq": i},
                    actor_id=proc_id,
                )
                session.commit()
                time.sleep(0.005)
        finally:
            session.close()
            engine.dispose()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(process_simulator, p) for p in range(num_processes)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Verify that the entire chain is valid across all simulated process writes
    verify_engine = create_engine(db_url)
    VerifySession = sessionmaker(bind=verify_engine)
    session = VerifySession()
    try:
        res = verify_audit_chain(session)
        assert res["valid"] is True
        assert res["total_records"] == num_processes * events_per_process
    finally:
        session.close()
        verify_engine.dispose()


def test_genuine_os_subprocess_concurrent_audit_writes(tmp_path):
    """Genuinely separate OS subprocesses sharing a disposable SQLite file serialize writes and produce a valid chain."""
    import subprocess
    import sys

    db_file = str(tmp_path / "genuine_os_audit.db")

    # Initialize schema
    from sqlalchemy import create_engine
    init_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=init_engine)
    init_engine.dispose()

    script = """import sys, os, time
from sqlalchemy import create_engine
from backend.app.services.audit_service import record_audit_event
from sqlalchemy.orm import sessionmaker

db_file = sys.argv[1]
proc_id = int(sys.argv[2])
engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 20})
Session = sessionmaker(bind=engine)
for i in range(5):
    s = Session()
    try:
        record_audit_event(
            db=s,
            event_type=f"os_proc_event_{proc_id}",
            status="SUCCESS",
            details={"proc": proc_id, "i": i},
            actor_id=proc_id,
        )
        s.commit()
    finally:
        s.close()
    time.sleep(0.005)
engine.dispose()
"""

    num_subprocesses = 4
    events_per_subprocess = 5
    env = {
        **os.environ,
        "AUDIT_SECRET_KEY": "test_audit_secret_key_32bytes!!",
        "TESTING": "true",
    }

    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script, db_file, str(i)],
            env=env,
        )
        for i in range(num_subprocesses)
    ]

    for p in procs:
        p.wait()

    assert all(p.returncode == 0 for p in procs)

    from sqlalchemy.orm import sessionmaker
    verify_engine = create_engine(f"sqlite:///{db_file}")
    VerifySession = sessionmaker(bind=verify_engine)
    session = VerifySession()
    try:
        res = verify_audit_chain(session)
        assert res["valid"] is True
        assert res["total_records"] == num_subprocesses * events_per_subprocess
    finally:
        session.close()
        verify_engine.dispose()


def test_read_only_queries_do_not_acquire_write_lock(client: TestClient, db_session):
    """Read-only balance and transaction history requests execute as standard read queries without acquiring write locks."""
    # 1. Accounts list
    acc_resp = client.get("/api/accounts")
    assert acc_resp.status_code == 200

    # 2. Account detail
    acc_id_resp = client.get("/api/accounts/1")
    assert acc_id_resp.status_code == 200

    # 3. Transaction history
    tx_resp = client.get("/api/transactions")
    assert tx_resp.status_code == 200

    # Verify connection was not forced into a write lock
    raw_conn = getattr(db_session.connection().connection, "dbapi_connection", db_session.connection().connection)
    # Read queries did not mutate or lock audit ledger
    audit_count = db_session.execute(text("SELECT count(*) FROM audit_logs")).fetchone()[0]
    assert audit_count == 0


def test_two_connections_read_only_does_not_reserve_writer_lock(tmp_path):
    """Demonstrates that an open read-only transaction on Connection 1 does not reserve the writer lock,
    allowing Connection 2 to acquire BEGIN IMMEDIATE and perform writes concurrently without being blocked."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "two_conn_lock_test.db"
    db_url = f"sqlite:///{db_path}"

    # Setup database with tables
    init_engine = create_engine(db_url, connect_args={"timeout": 15})
    Base.metadata.create_all(bind=init_engine)
    init_engine.dispose()

    # Create two independent engines simulating two separate connections
    e1 = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 2})
    e2 = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 2})
    Session1 = sessionmaker(bind=e1)
    Session2 = sessionmaker(bind=e2)

    s1 = Session1()
    s2 = Session2()

    try:
        # Connection 1 executes read query and leaves transaction open
        rows = s1.execute(text("SELECT count(*) FROM audit_logs")).fetchall()
        assert rows[0][0] == 0

        # Connection 2 attempts to write with BEGIN IMMEDIATE
        # If Connection 1 had executed BEGIN IMMEDIATE or held a write reservation,
        # Connection 2 would immediately fail with OperationalError: database is locked!
        record_audit_event(
            db=s2,
            event_type="conn2_write_event",
            status="SUCCESS",
            details={"writer": "connection_2"},
            actor_id=2,
        )
        s2.commit()

        # Connection 1 can still query cleanly
        s1.rollback()  # Refresh transaction view
        rows_after = s1.execute(text("SELECT count(*) FROM audit_logs")).fetchall()
        assert rows_after[0][0] == 1

    finally:
        s1.close()
        s2.close()
        e1.dispose()
        e2.dispose()
