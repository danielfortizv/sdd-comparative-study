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
    """Returns a connection to the SQLite database with foreign keys enabled."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | None = None):
    """Initializes the database schema, executes safe atomic table-rebuild migration if needed (F-01),
    and seeds initial records (accounts, pre-seeded historical transfers, default limits).
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
        # Create transfers table with full Stage 2 schema (destination_account_id nullable for ACH)
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
        # Table exists: inspect PRAGMA table_info(transfers)
        cursor.execute("PRAGMA table_info(transfers);")
        columns = cursor.fetchall()
        # columns: (cid, name, type, notnull, dflt_value, pk)
        dest_col = next((c for c in columns if c[1] == "destination_account_id"), None)
        transfer_type_col = next((c for c in columns if c[1] == "transfer_type"), None)

        # If destination_account_id is NOT NULL (Stage 1 schema: notnull == 1),
        # execute safe, atomic, idempotent table rebuild (Remediating F-01)
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
            # Destination is already nullable but Stage 2 columns might be missing
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

    # 4. Seed accounts table if empty (Stage 1 reproducible baseline)
    cursor.execute("SELECT COUNT(*) FROM accounts;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO accounts (id, name, balance, currency) VALUES
        ('acc_checking_123', 'Checking', '5000000.00', 'COP'),
        ('acc_savings_456', 'Savings', '15000000.00', 'COP');
        """)
        conn.commit()

    # 5. Seed transfers table if empty (Stage 1 reproducible historical transfers)
    cursor.execute("SELECT COUNT(*) FROM transfers;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at, transfer_type) VALUES
        ('tr_seeded_1', 'acc_savings_456', 'acc_checking_123', '500000.00', 'COMPLETED', '2026-09-30T10:00:00Z', NULL, 'INTERNAL'),
        ('tr_seeded_2', 'acc_checking_123', 'acc_savings_456', '100000.00', 'COMPLETED', '2026-09-30T10:05:00Z', NULL, 'INTERNAL');
        """)
        conn.commit()

    # 6. Seed limits table if empty (D-01, T005)
    cursor.execute("SELECT COUNT(*) FROM limits WHERE user_id = 'user_mock_001';")
    if cursor.fetchone()[0] == 0:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor.execute("""
        INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at) VALUES
        ('lim_mock_001', 'user_mock_001', '5000000.00', '10000000.00', ?);
        """, (now_iso,))
        conn.commit()

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
