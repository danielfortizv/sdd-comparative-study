"""SQLite persistence for the Stage 1 bank and additive Stage 2 records."""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("SHIFT_BANK_DB", Path(__file__).resolve().parent / "bank.db"))


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def _add_column(conn, table: str, name: str, definition: str) -> None:
    existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    if name not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, balance TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY, source_account_id TEXT NOT NULL, source_account_name TEXT NOT NULL,
            destination_account_id TEXT NOT NULL, destination_account_name TEXT NOT NULL,
            amount TEXT NOT NULL, timestamp TEXT NOT NULL, status TEXT NOT NULL)""")
        _add_column(conn, "transactions", "completed_at", "TEXT")
        _add_column(conn, "transactions", "failure_reason", "TEXT")
        _add_column(conn, "transactions", "occurrence_id", "TEXT")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS transfer_limits (
            user_id TEXT PRIMARY KEY, per_transfer TEXT NOT NULL, daily TEXT NOT NULL,
            updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, bank_name TEXT NOT NULL,
            routing_number TEXT NOT NULL, account_number TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ach_transfers (
            id TEXT PRIMARY KEY, source_account_id TEXT NOT NULL, source_account_name TEXT NOT NULL,
            amount TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            accepted_at TEXT, settled_at TEXT, failed_at TEXT, recipient_name TEXT NOT NULL,
            bank_name TEXT NOT NULL, routing_number TEXT NOT NULL, account_number TEXT NOT NULL,
            beneficiary_id TEXT, failure_code TEXT, failure_reason TEXT, refund_applied INTEGER NOT NULL DEFAULT 0,
            occurrence_id TEXT UNIQUE);
        CREATE INDEX IF NOT EXISTS idx_ach_status_acceptance ON ach_transfers(status, accepted_at);
        CREATE TABLE IF NOT EXISTS recurring_schedules (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, transfer_type TEXT NOT NULL,
            source_account_id TEXT NOT NULL, source_account_name TEXT NOT NULL,
            destination_account_id TEXT, destination_account_name TEXT,
            recipient_name TEXT, bank_name TEXT, routing_number TEXT, account_number TEXT,
            beneficiary_id TEXT, amount TEXT NOT NULL, frequency TEXT NOT NULL, interval_days INTEGER NOT NULL,
            cadence_anchor TEXT NOT NULL, next_execution_at TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, mfa_expires_at TEXT, authorized_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_schedule_due ON recurring_schedules(status, next_execution_at);
        CREATE TABLE IF NOT EXISTS recurring_occurrences (
            id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL, scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL, attempted_at TEXT NOT NULL, transaction_id TEXT, ach_transfer_id TEXT,
            failure_reason TEXT, UNIQUE(schedule_id, scheduled_at),
            FOREIGN KEY(schedule_id) REFERENCES recurring_schedules(id));
        CREATE INDEX IF NOT EXISTS idx_occurrence_schedule ON recurring_occurrences(schedule_id, scheduled_at);
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_occurrence ON transactions(occurrence_id) WHERE occurrence_id IS NOT NULL")
        count = conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"]
        if count == 0:
            conn.execute("INSERT INTO accounts VALUES (?, ?, ?)", ("acc_checking", "Cuenta Corriente", "5000000.00"))
            conn.execute("INSERT INTO accounts VALUES (?, ?, ?)", ("acc_savings", "Cuenta de Ahorros", "15000000.00"))
            conn.executemany("""INSERT INTO transactions
                (id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status,completed_at)
                VALUES(?,?,?,?,?,?,?,?,?)""", [
                ("tx_seed_1", "acc_savings", "Cuenta de Ahorros", "acc_checking", "Cuenta Corriente", "500000.00", "2026-09-28T10:00:00Z", "COMPLETED", "2026-09-28T10:00:00Z"),
                ("tx_seed_2", "acc_checking", "Cuenta Corriente", "acc_savings", "Cuenta de Ahorros", "100000.00", "2026-09-28T11:00:00Z", "COMPLETED", "2026-09-28T11:00:00Z")])
        conn.execute("INSERT OR IGNORE INTO transfer_limits VALUES (?, ?, ?, ?)",
                     ("usr_101", "5000000.00", "10000000.00", "2026-11-16T00:00:00Z"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
