import sqlite3
from ..config import (
    DEFAULT_MOCK_CUSTOMER_ID,
    DEFAULT_MOCK_CUSTOMER_NAME,
    DEFAULT_MOCK_CUSTOMER_EMAIL,
)

def seed_database(conn: sqlite3.Connection) -> None:
    with conn:
        # Check if customer already exists
        cursor = conn.execute("SELECT id FROM customer WHERE id = ?", (DEFAULT_MOCK_CUSTOMER_ID,))
        if cursor.fetchone():
            return  # Idempotent skip if already seeded

        # Insert Mock Customer (Alex Morgan)
        conn.execute(
            "INSERT INTO customer (id, full_name, email) VALUES (?, ?, ?)",
            (DEFAULT_MOCK_CUSTOMER_ID, DEFAULT_MOCK_CUSTOMER_NAME, DEFAULT_MOCK_CUSTOMER_EMAIL),
        )

        # Insert 3 Accounts (AD-8)
        # Checking: $2,500.00 = 250000 cents
        # Savings: $12,450.75 = 1245075 cents
        # Reserve: $5,000.00 = 500000 cents
        accounts = [
            ("CHK-1001", DEFAULT_MOCK_CUSTOMER_ID, "Primary Checking", "CHECKING", 250000),
            ("SAV-2001", DEFAULT_MOCK_CUSTOMER_ID, "High-Yield Savings", "SAVINGS", 1245075),
            ("RSV-3001", DEFAULT_MOCK_CUSTOMER_ID, "Emergency Reserve", "RESERVE", 500000),
        ]

        conn.executemany(
            "INSERT INTO account (id, customer_id, nickname, account_type, balance_cents) VALUES (?, ?, ?, ?, ?)",
            accounts,
        )
