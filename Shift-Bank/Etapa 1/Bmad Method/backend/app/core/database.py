import sqlite3
from pathlib import Path
from typing import Generator
from ..config import DATABASE_PATH

def get_connection(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                nickname TEXT NOT NULL,
                account_type TEXT NOT NULL,
                balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                FOREIGN KEY (customer_id) REFERENCES customer(id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfer (
                id TEXT PRIMARY KEY,
                source_account_id TEXT NOT NULL,
                destination_account_id TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                status TEXT NOT NULL,
                idempotency_key TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_account_id) REFERENCES account(id),
                FOREIGN KEY (destination_account_id) REFERENCES account(id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mfa_challenge (
                id TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL,
                mock_code TEXT NOT NULL,
                remaining_attempts INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (transfer_id) REFERENCES transfer(id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                running_balance_cents INTEGER NOT NULL CHECK (running_balance_cents >= 0),
                counterparty_account_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (transfer_id) REFERENCES transfer(id),
                FOREIGN KEY (account_id) REFERENCES account(id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_cache (
                key TEXT PRIMARY KEY,
                response_status INTEGER NOT NULL,
                response_body TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
        """)

def db_dependency() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
