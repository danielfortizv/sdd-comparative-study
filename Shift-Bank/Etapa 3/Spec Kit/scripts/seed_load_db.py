"""Synthetic test database generator for reproducible high-concurrency load testing (E3-LOAD-01, FR-028, T024).

Seeds dedicated test_load_bank.db with high-value synthetic accounts
(COP 100,000,000.00 balances, COP 50,000,000.00 limits) to isolate load tests
and prevent business limit exhaustion or unintended MFA triggers.
"""

import argparse
import os
import secrets
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Ensure backend/src is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_SRC = os.path.join(PROJECT_ROOT, "backend", "src")
if BACKEND_SRC not in sys.path:
    sys.path.insert(0, BACKEND_SRC)

DEFAULT_LOAD_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "test_load_bank.db")

# Ensure required encryption keys exist in environment or set deterministic fallbacks for load seeding
if not os.environ.get("BANK_STORAGE_KEY"):
    os.environ["BANK_STORAGE_KEY"] = secrets.token_hex(32)
if not os.environ.get("AUDIT_SIGNING_KEY"):
    os.environ["AUDIT_SIGNING_KEY"] = secrets.token_urlsafe(32)
if not os.environ.get("AUDIT_ADMIN_KEY"):
    os.environ["AUDIT_ADMIN_KEY"] = secrets.token_urlsafe(32)

import database
from services import decrypt_val, encrypt_val

SYNTHETIC_ACCOUNTS = [
    ("acc_checking_123", "Checking", "100000000.00", "COP"),
    ("acc_savings_456", "Savings", "100000000.00", "COP"),
    ("acc_synth_001", "Synthetic Account 1", "100000000.00", "COP"),
    ("acc_synth_002", "Synthetic Account 2", "100000000.00", "COP"),
    ("acc_synth_003", "Synthetic Account 3", "100000000.00", "COP"),
    ("acc_synth_004", "Synthetic Account 4", "100000000.00", "COP"),
]

SYNTHETIC_LIMITS = {
    "user_id": "user_mock_001",
    "per_transfer_limit": "50000000.00",
    "daily_limit": "50000000.00",
}


def seed_load_database(db_path: str = DEFAULT_LOAD_DB_PATH, clean: bool = True) -> dict:
    """Creates and populates the synthetic load testing database.

    Args:
        db_path: Path to target SQLite database file.
        clean: If True, removes existing database file before seeding.

    Returns:
        dict: Seeding summary with account count, total initial funds, and limits.
    """
    target_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    if clean and os.path.exists(target_path):
        # Clean existing database and any WAL/SHM companion files
        for ext in ("", "-wal", "-shm"):
            p = target_path + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError as e:
                    print(f"Warning: could not remove {p}: {e}")

    # 1. Initialize schema and run at-rest migration
    database.init_db(target_path)

    conn = database.get_connection(target_path)
    cursor = conn.cursor()

    total_funds = Decimal("0.00")

    # 2. Seed synthetic accounts with COP 100,000,000.00
    for acc_id, name, balance_str, currency in SYNTHETIC_ACCOUNTS:
        enc_bal = encrypt_val(balance_str)
        cursor.execute("""
            INSERT INTO accounts (id, name, balance, currency)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                balance = excluded.balance,
                currency = excluded.currency;
        """, (acc_id, name, enc_bal, currency))
        total_funds += Decimal(balance_str)

    # 3. Seed dynamic limits with COP 50,000,000.00
    enc_per_tr = encrypt_val(SYNTHETIC_LIMITS["per_transfer_limit"])
    enc_daily = encrypt_val(SYNTHETIC_LIMITS["daily_limit"])
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor.execute("""
        INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
        VALUES ('lim_mock_001', ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            per_transfer_limit = excluded.per_transfer_limit,
            daily_limit = excluded.daily_limit,
            updated_at = excluded.updated_at;
    """, (SYNTHETIC_LIMITS["user_id"], enc_per_tr, enc_daily, now_iso))

    conn.commit()

    # 4. Verify integrity and consistency
    cursor.execute("SELECT COUNT(*) FROM accounts;")
    account_count = cursor.fetchone()[0]

    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchone()[0]
    if integrity != "ok":
        conn.close()
        raise RuntimeError(f"Database integrity check failed: {integrity}")

    conn.close()

    summary = {
        "db_path": target_path,
        "account_count": account_count,
        "accounts": [acc[0] for acc in SYNTHETIC_ACCOUNTS],
        "initial_total_funds": str(total_funds),
        "per_transfer_limit": SYNTHETIC_LIMITS["per_transfer_limit"],
        "daily_limit": SYNTHETIC_LIMITS["daily_limit"],
        "integrity": integrity,
    }
    return summary


def verify_funds_conservation(db_path: str = DEFAULT_LOAD_DB_PATH, expected_total: Decimal | None = None) -> tuple[bool, Decimal, dict]:
    """Verifies that the sum of all account balances equals expected initial funds.

    Returns:
        tuple: (is_conserved, current_total, account_balances)
    """
    target_path = os.path.abspath(db_path)
    conn = database.get_connection(target_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, balance FROM accounts;")
    rows = cursor.fetchall()
    conn.close()

    current_total = Decimal("0.00")
    balances = {}
    for acc_id, name, enc_bal in rows:
        dec_bal = Decimal(decrypt_val(enc_bal))
        balances[acc_id] = {"name": name, "balance": str(dec_bal)}
        current_total += dec_bal

    target_expected = expected_total
    if target_expected is None:
        target_expected = Decimal(str(len(SYNTHETIC_ACCOUNTS) * 100000000))

    is_conserved = (current_total == target_expected)
    return is_conserved, current_total, balances


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic database for Locust load testing")
    parser.add_argument("--db-path", default=DEFAULT_LOAD_DB_PATH, help="Target SQLite DB path")
    parser.add_argument("--no-clean", action="store_true", help="Do not wipe existing DB before seeding")
    args = parser.parse_args()

    result = seed_load_database(db_path=args.db_path, clean=not args.no_clean)
    print("Synthetic load testing database seeded successfully:")
    print(f"  Path: {result['db_path']}")
    print(f"  Accounts: {result['account_count']}")
    print(f"  Total Funds: COP {Decimal(result['initial_total_funds']):,.2f}")
    print(f"  Per-Transfer Limit: COP {Decimal(result['per_transfer_limit']):,.2f}")
    print(f"  Daily Limit: COP {Decimal(result['daily_limit']):,.2f}")
    print(f"  Integrity: {result['integrity']}")
