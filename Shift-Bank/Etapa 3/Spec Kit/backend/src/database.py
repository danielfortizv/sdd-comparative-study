import os
import sqlite3
import sys
from datetime import datetime, timezone

# Define default database file path in the backend directory
DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shift_bank.db"))


def is_in_test_environment() -> bool:
    """Detects if execution is running in an automated test context."""
    return bool(
        os.environ.get("TEST_DB_PATH")
        or os.environ.get("PYTEST_CURRENT_TEST")
        or "pytest" in sys.modules
    )


def get_db_path() -> str:
    """Returns the effective database path.
    If in test mode (TEST_DB_PATH is set or pytest is running), returns the isolated test database path.
    Strictly protects DEFAULT_DB_PATH (shift_bank.db) from test runs (D-02, F-10).
    """
    if os.environ.get("TEST_DB_PATH"):
        return os.environ["TEST_DB_PATH"]
    if is_in_test_environment():
        fallback_test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests", "test_shift_bank.db"))
        os.environ["TEST_DB_PATH"] = fallback_test_db
        return fallback_test_db
    return os.environ.get("SHIFT_BANK_DB_PATH") or DEFAULT_DB_PATH


def __getattr__(name: str):
    """Dynamically resolves DB_PATH to guarantee that test isolation is never bypassed."""
    if name == "DB_PATH":
        return get_db_path()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite database with foreign keys, WAL mode, and busy timeout enabled."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    return conn


def get_next_audit_sequence(cursor: sqlite3.Cursor) -> tuple[int, str]:
    """
    Computes the next contiguous monotonic sequence number and predecessor hash
    under an active write transaction (BEGIN IMMEDIATE).
    Guarantees gap-free contiguous sequence numbers (1, 2, 3...) regardless of rollbacks.
    """
    cursor.execute("""
        SELECT COALESCE(MAX(id), 0) + 1,
               COALESCE((SELECT record_hmac FROM audit_logs WHERE id = (SELECT MAX(id) FROM audit_logs)),
                        '0000000000000000000000000000000000000000000000000000000000000000')
        FROM audit_logs;
    """)
    row = cursor.fetchone()
    return row[0], row[1]


def _validate_or_encrypt_field(val: str | None, field_name: str, row_id: str, storage_key: bytes) -> tuple[str | None, bool]:
    """
    Helper for legacy data migration:
    - If None: returns (None, False).
    - If already encrypted ('enc:v1:...'): validates format; raises ValueError if corrupted.
    - If plaintext: encrypts using storage_key and returns (ciphertext, True).
    """
    if val is None:
        return None, False

    if val.startswith("enc:v1:"):
        parts = val.split(":")
        if len(parts) != 4 or not parts[2] or not parts[3]:
            raise ValueError(f"Corrupted ciphertext envelope in {field_name} for row {row_id}")
        return val, False

    # Plaintext value; encrypt using storage_key
    from crypto import encrypt_at_rest
    encrypted = encrypt_at_rest(val, storage_key)
    return encrypted, True


def migrate_legacy_plaintext_records(conn: sqlite3.Connection, storage_key: bytes | None = None) -> int:
    """
    Safely and idempotently converts legacy Stage 2 plaintext records to encrypted storage.
    Performs complete entity scanning and validation across:
    accounts, limits, beneficiaries, transfers, and recurring_schedules.
    Executes inside an atomic transaction (BEGIN IMMEDIATE).
    Rolls back completely on any error, leaving original state untouched.
    """
    from crypto import get_storage_key
    key = storage_key or get_storage_key()

    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE;")
    try:
        migrated_fields = 0

        # 1. Accounts (balance)
        cursor.execute("SELECT id, balance FROM accounts;")
        for acc_id, balance in cursor.fetchall():
            new_val, changed = _validate_or_encrypt_field(balance, "accounts.balance", acc_id, key)
            if changed:
                cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (new_val, acc_id))
                migrated_fields += 1

        # 2. Dynamic Limits (per_transfer_limit, daily_limit)
        cursor.execute("SELECT id, per_transfer_limit, daily_limit FROM limits;")
        for lim_id, per_tr, daily in cursor.fetchall():
            new_per, ch_per = _validate_or_encrypt_field(per_tr, "limits.per_transfer_limit", lim_id, key)
            new_day, ch_day = _validate_or_encrypt_field(daily, "limits.daily_limit", lim_id, key)
            if ch_per or ch_day:
                cursor.execute("UPDATE limits SET per_transfer_limit = ?, daily_limit = ? WHERE id = ?;",
                               (new_per, new_day, lim_id))
                migrated_fields += int(ch_per) + int(ch_day)

        # 3. Beneficiaries (name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, name, bank_name, routing_number, account_number FROM beneficiaries;")
        for ben_id, name, bank_name, routing, acc_num in cursor.fetchall():
            new_name, ch_name = _validate_or_encrypt_field(name, "beneficiaries.name", ben_id, key)
            new_bank, ch_bank = _validate_or_encrypt_field(bank_name, "beneficiaries.bank_name", ben_id, key)
            new_rout, ch_rout = _validate_or_encrypt_field(routing, "beneficiaries.routing_number", ben_id, key)
            new_acc, ch_acc = _validate_or_encrypt_field(acc_num, "beneficiaries.account_number", ben_id, key)
            if any([ch_name, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE beneficiaries SET name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_name, new_bank, new_rout, new_acc, ben_id)
                )
                migrated_fields += sum([ch_name, ch_bank, ch_rout, ch_acc])

        # 4. Transfers (amount, recipient_name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, amount, recipient_name, bank_name, routing_number, account_number FROM transfers;")
        for tr_id, amount, rec_name, bank_name, routing, acc_num in cursor.fetchall():
            new_amt, ch_amt = _validate_or_encrypt_field(amount, "transfers.amount", tr_id, key)
            new_rec, ch_rec = _validate_or_encrypt_field(rec_name, "transfers.recipient_name", tr_id, key)
            new_bank, ch_bank = _validate_or_encrypt_field(bank_name, "transfers.bank_name", tr_id, key)
            new_rout, ch_rout = _validate_or_encrypt_field(routing, "transfers.routing_number", tr_id, key)
            new_acc, ch_acc = _validate_or_encrypt_field(acc_num, "transfers.account_number", tr_id, key)
            if any([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE transfers SET amount = ?, recipient_name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_amt, new_rec, new_bank, new_rout, new_acc, tr_id)
                )
                migrated_fields += sum([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc])

        # 5. Recurring Schedules (amount, recipient_name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, amount, recipient_name, bank_name, routing_number, account_number FROM recurring_schedules;")
        for sch_id, amount, rec_name, bank_name, routing, acc_num in cursor.fetchall():
            new_amt, ch_amt = _validate_or_encrypt_field(amount, "recurring_schedules.amount", sch_id, key)
            new_rec, ch_rec = _validate_or_encrypt_field(rec_name, "recurring_schedules.recipient_name", sch_id, key)
            new_bank, ch_bank = _validate_or_encrypt_field(bank_name, "recurring_schedules.bank_name", sch_id, key)
            new_rout, ch_rout = _validate_or_encrypt_field(routing, "recurring_schedules.routing_number", sch_id, key)
            new_acc, ch_acc = _validate_or_encrypt_field(acc_num, "recurring_schedules.account_number", sch_id, key)
            if any([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE recurring_schedules SET amount = ?, recipient_name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_amt, new_rec, new_bank, new_rout, new_acc, sch_id)
                )
                migrated_fields += sum([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc])

        conn.commit()
        return migrated_fields
    except Exception:
        conn.rollback()
        raise


def init_db(db_path: str | None = None):
    """Initializes the database schema, executes safe atomic table-rebuild migration if needed (F-01),
    creates Stage 3 audit trail table and immutability triggers (E3-AUD-01),
    and executes safe legacy plaintext migration (FR-013).
    """
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Create accounts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        balance TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'COP'
    );
    """)
    conn.commit()

    # 2. Check if transfers table exists and inspect its schema for Stage 2 evolution (F-01)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transfers';")
    transfers_exists = cursor.fetchone() is not None

    if not transfers_exists:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id TEXT PRIMARY KEY,
            source_account_id TEXT NOT NULL,
            destination_account_id TEXT,
            amount TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            transfer_type TEXT NOT NULL DEFAULT 'INTERNAL',
            recipient_name TEXT,
            bank_name TEXT,
            routing_number TEXT,
            account_number TEXT,
            settled_at TEXT,
            failed_at TEXT,
            refunded_at TEXT,
            FOREIGN KEY (source_account_id) REFERENCES accounts(id),
            FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
        );
        """)
        conn.commit()
    else:
        cursor.execute("PRAGMA table_info(transfers);")
        columns = cursor.fetchall()
        dest_col = next((c for c in columns if c[1] == "destination_account_id"), None)
        transfer_type_col = next((c for c in columns if c[1] == "transfer_type"), None)

        if dest_col and dest_col[3] == 1:
            conn.execute("PRAGMA foreign_keys = OFF;")
            conn.execute("BEGIN TRANSACTION;")
            try:
                cursor.execute("DROP TABLE IF EXISTS transfers_v2;")
                cursor.execute("""
                CREATE TABLE transfers_v2 (
                    id TEXT PRIMARY KEY,
                    source_account_id TEXT NOT NULL,
                    destination_account_id TEXT,
                    amount TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    transfer_type TEXT NOT NULL DEFAULT 'INTERNAL',
                    recipient_name TEXT,
                    bank_name TEXT,
                    routing_number TEXT,
                    account_number TEXT,
                    settled_at TEXT,
                    failed_at TEXT,
                    refunded_at TEXT,
                    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
                    FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
                );
                """)

                cursor.execute("""
                INSERT INTO transfers_v2 (
                    id, source_account_id, destination_account_id, amount, status, created_at, expires_at, transfer_type
                )
                SELECT id, source_account_id, destination_account_id, amount, status, created_at, expires_at, 'INTERNAL'
                FROM transfers;
                """)

                cursor.execute("DROP TABLE transfers;")
                cursor.execute("ALTER TABLE transfers_v2 RENAME TO transfers;")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.execute("PRAGMA foreign_keys = ON;")
        elif not transfer_type_col:
            stage2_cols = [
                ("transfer_type", "TEXT NOT NULL DEFAULT 'INTERNAL'"),
                ("recipient_name", "TEXT"),
                ("bank_name", "TEXT"),
                ("routing_number", "TEXT"),
                ("account_number", "TEXT"),
                ("settled_at", "TEXT"),
                ("failed_at", "TEXT"),
                ("refunded_at", "TEXT"),
            ]
            existing_col_names = {c[1] for c in columns}
            conn.execute("BEGIN TRANSACTION;")
            try:
                for col_name, col_def in stage2_cols:
                    if col_name not in existing_col_names:
                        cursor.execute(f"ALTER TABLE transfers ADD COLUMN {col_name} {col_def};")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # 3. Create Stage 2 tables: beneficiaries, limits, recurring_schedules
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS beneficiaries (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'user_mock_001',
        name TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        routing_number TEXT NOT NULL,
        account_number TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS limits (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL DEFAULT 'user_mock_001',
        per_transfer_limit TEXT NOT NULL,
        daily_limit TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recurring_schedules (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'user_mock_001',
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
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_account_id) REFERENCES accounts(id),
        FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
    );
    """)
    conn.commit()

    # 4. Stage 3: Create audit_logs table and immutability triggers (E3-AUD-01, T007)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        resource_id TEXT,
        payload_digest TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        record_hmac TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_update
    BEFORE UPDATE ON audit_logs BEGIN
        SELECT RAISE(ABORT, 'Audit log is append-only: updates prohibited');
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_delete
    BEFORE DELETE ON audit_logs BEGIN
        SELECT RAISE(ABORT, 'Audit log is append-only: deletions prohibited');
    END;
    """)
    conn.commit()

    # 5. Seed accounts table if empty (Stage 1 reproducible baseline)
    cursor.execute("SELECT COUNT(*) FROM accounts;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO accounts (id, name, balance, currency) VALUES
        ('acc_checking_123', 'Checking', '5000000.00', 'COP'),
        ('acc_savings_456', 'Savings', '15000000.00', 'COP');
        """)
        conn.commit()

    # 6. Seed transfers table if empty (Stage 1 reproducible historical transfers)
    cursor.execute("SELECT COUNT(*) FROM transfers;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at, transfer_type) VALUES
        ('tr_seeded_1', 'acc_savings_456', 'acc_checking_123', '500000.00', 'COMPLETED', '2026-09-30T10:00:00Z', NULL, 'INTERNAL'),
        ('tr_seeded_2', 'acc_checking_123', 'acc_savings_456', '100000.00', 'COMPLETED', '2026-09-30T10:05:00Z', NULL, 'INTERNAL');
        """)
        conn.commit()

    # 7. Seed limits table if empty (D-01, T005)
    cursor.execute("SELECT COUNT(*) FROM limits WHERE user_id = 'user_mock_001';")
    if cursor.fetchone()[0] == 0:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor.execute("""
        INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at) VALUES
        ('lim_mock_001', 'user_mock_001', '5000000.00', '10000000.00', ?);
        """, (now_iso,))
        conn.commit()

    # 8. Stage 3: Safe, idempotent legacy plaintext migration (FR-013, T008)
    if os.environ.get("BANK_STORAGE_KEY"):
        try:
            migrate_legacy_plaintext_records(conn)
        except Exception as e:
            conn.close()
            raise RuntimeError(f"Database startup migration failed: {e}")

    # Verify integrity and foreign key constraints
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchone()
    if integrity and integrity[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity[0]}")

    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()
    if fk_errors:
        raise RuntimeError(f"SQLite foreign key check failed: {fk_errors}")

    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", get_db_path())
