import os
import sqlite3
import pytest
from decimal import Decimal

import crypto
import database


@pytest.fixture
def temp_legacy_db(tmp_path):
    """Creates a temporary isolated SQLite database with pre-existing Stage 2 plaintext records."""
    db_file = str(tmp_path / "legacy_test.db")
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = OFF;")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE accounts (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        balance TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'COP'
    );
    """)

    cursor.execute("""
    CREATE TABLE limits (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        per_transfer_limit TEXT NOT NULL,
        daily_limit TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE beneficiaries (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        routing_number TEXT NOT NULL,
        account_number TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE transfers (
        id TEXT PRIMARY KEY,
        source_account_id TEXT NOT NULL,
        destination_account_id TEXT,
        amount TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        transfer_type TEXT NOT NULL,
        recipient_name TEXT,
        bank_name TEXT,
        routing_number TEXT,
        account_number TEXT,
        settled_at TEXT,
        failed_at TEXT,
        refunded_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE recurring_schedules (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        transfer_type TEXT NOT NULL,
        source_account_id TEXT NOT NULL,
        destination_account_id TEXT,
        recipient_name TEXT,
        bank_name TEXT,
        routing_number TEXT,
        account_number TEXT,
        amount TEXT NOT NULL,
        frequency TEXT NOT NULL,
        status TEXT NOT NULL,
        start_date TEXT,
        next_due_date TEXT NOT NULL,
        last_executed_at TEXT,
        mfa_expires_at TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Seed plaintext records across all 5 tables
    cursor.execute("INSERT INTO accounts VALUES ('acc_1', 'Checking', '5000000.00', 'COP');")
    cursor.execute("INSERT INTO accounts VALUES ('acc_2', 'Savings', '15000000.00', 'COP');")
    cursor.execute("INSERT INTO limits VALUES ('lim_1', 'user_mock_001', '5000000.00', '10000000.00', '2026-09-30T10:00:00Z');")
    cursor.execute("INSERT INTO beneficiaries VALUES ('ben_1', 'user_mock_001', 'Carlos Gomez', 'Banco Bogota', '123456789', '987654321', '2026-09-30T10:00:00Z');")
    cursor.execute("INSERT INTO transfers VALUES ('tr_1', 'acc_1', 'acc_2', '250000.00', 'COMPLETED', '2026-09-30T10:00:00Z', NULL, 'INTERNAL', NULL, NULL, NULL, NULL, NULL, NULL, NULL);")
    cursor.execute("INSERT INTO transfers VALUES ('tr_2', 'acc_1', NULL, '350000.00', 'SETTLED', '2026-09-30T10:00:00Z', NULL, 'ACH', 'Carlos Gomez', 'Banco Bogota', '123456789', '987654321', '2026-09-30T10:01:00Z', NULL, NULL);")
    cursor.execute("INSERT INTO recurring_schedules VALUES ('sch_1', 'user_mock_001', 'INTERNAL', 'acc_1', 'acc_2', NULL, NULL, NULL, NULL, '100000.00', 'MONTHLY', 'ACTIVE', NULL, '2026-10-30', NULL, NULL, '2026-09-30T10:00:00Z');")

    conn.commit()
    conn.close()
    return db_file


def test_full_legacy_migration_across_all_entities(temp_legacy_db):
    """Verifies that all 5 entities with plaintext records are migrated to encrypted storage."""
    conn = sqlite3.connect(temp_legacy_db)
    storage_key = crypto.get_storage_key()

    migrated_count = database.migrate_legacy_plaintext_records(conn, storage_key)
    assert migrated_count > 0

    cursor = conn.cursor()

    # 1. Accounts
    cursor.execute("SELECT balance FROM accounts;")
    for (bal,) in cursor.fetchall():
        assert bal.startswith("enc:v1:")
        dec = crypto.decrypt_at_rest(bal, storage_key)
        assert dec in ("5000000.00", "15000000.00")

    # 2. Limits
    cursor.execute("SELECT per_transfer_limit, daily_limit FROM limits;")
    per_tr, daily = cursor.fetchone()
    assert per_tr.startswith("enc:v1:")
    assert daily.startswith("enc:v1:")
    assert crypto.decrypt_at_rest(per_tr, storage_key) == "5000000.00"
    assert crypto.decrypt_at_rest(daily, storage_key) == "10000000.00"

    # 3. Beneficiaries
    cursor.execute("SELECT name, bank_name, routing_number, account_number FROM beneficiaries;")
    name, bank, routing, acc_num = cursor.fetchone()
    assert name.startswith("enc:v1:")
    assert bank.startswith("enc:v1:")
    assert routing.startswith("enc:v1:")
    assert acc_num.startswith("enc:v1:")
    assert crypto.decrypt_at_rest(name, storage_key) == "Carlos Gomez"
    assert crypto.decrypt_at_rest(routing, storage_key) == "123456789"

    # 4. Transfers (internal has NULL recipient fields; ACH has non-null)
    cursor.execute("SELECT amount, recipient_name, routing_number FROM transfers WHERE id = 'tr_1';")
    tr1_amt, tr1_rec, tr1_rout = cursor.fetchone()
    assert tr1_amt.startswith("enc:v1:")
    assert tr1_rec is None
    assert tr1_rout is None
    assert crypto.decrypt_at_rest(tr1_amt, storage_key) == "250000.00"

    cursor.execute("SELECT amount, recipient_name, routing_number FROM transfers WHERE id = 'tr_2';")
    tr2_amt, tr2_rec, tr2_rout = cursor.fetchone()
    assert tr2_amt.startswith("enc:v1:")
    assert tr2_rec.startswith("enc:v1:")
    assert tr2_rout.startswith("enc:v1:")
    assert crypto.decrypt_at_rest(tr2_rec, storage_key) == "Carlos Gomez"

    # 5. Recurring Schedules
    cursor.execute("SELECT amount FROM recurring_schedules WHERE id = 'sch_1';")
    (sch_amt,) = cursor.fetchone()
    assert sch_amt.startswith("enc:v1:")
    assert crypto.decrypt_at_rest(sch_amt, storage_key) == "100000.00"

    conn.close()


def test_migration_atomic_rollback_on_corrupted_record(temp_legacy_db):
    """Verifies that encountering a corrupted ciphertext envelope causes an atomic rollback."""
    conn = sqlite3.connect(temp_legacy_db)
    cursor = conn.cursor()

    # Intentionally corrupt one record with invalid envelope format
    cursor.execute("UPDATE accounts SET balance = 'enc:v1:corrupted' WHERE id = 'acc_2';")
    conn.commit()

    storage_key = crypto.get_storage_key()

    with pytest.raises(Exception):
        database.migrate_legacy_plaintext_records(conn, storage_key)

    # Verify rollback: acc_1 should still be plaintext
    cursor.execute("SELECT balance FROM accounts WHERE id = 'acc_1';")
    acc1_bal = cursor.fetchone()[0]
    assert acc1_bal == "5000000.00"  # Rolled back, not encrypted

    conn.close()


def test_migration_idempotency_on_subsequent_runs(temp_legacy_db):
    """Verifies that running migration repeatedly produces zero changes and modifies nothing."""
    conn = sqlite3.connect(temp_legacy_db)
    storage_key = crypto.get_storage_key()

    # First run
    count1 = database.migrate_legacy_plaintext_records(conn, storage_key)
    assert count1 > 0

    # Second run immediately after
    count2 = database.migrate_legacy_plaintext_records(conn, storage_key)
    assert count2 == 0

    conn.close()
