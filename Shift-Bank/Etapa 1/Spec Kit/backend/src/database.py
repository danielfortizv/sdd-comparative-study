import os
import sqlite3

# Define database file path in the backend directory
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shift_bank.db"))

def get_connection():
    """Returns a connection to the SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema and seeds initial records if the tables are empty."""
    conn = get_connection()
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

    # 2. Create transfers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transfers (
        id TEXT PRIMARY KEY,
        source_account_id TEXT NOT NULL,
        destination_account_id TEXT NOT NULL,
        amount TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        FOREIGN KEY (source_account_id) REFERENCES accounts(id),
        FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
    );
    """)

    conn.commit()

    # 3. Seed accounts table if empty
    cursor.execute("SELECT COUNT(*) FROM accounts;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO accounts (id, name, balance, currency) VALUES
        ('acc_checking_123', 'Checking', '5000000.00', 'COP'),
        ('acc_savings_456', 'Savings', '15000000.00', 'COP');
        """)
        conn.commit()

    # 4. Seed transfers table if empty
    # These pre-seeded transfers are strictly historical records and DO NOT modify initial balances.
    cursor.execute("SELECT COUNT(*) FROM transfers;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at) VALUES
        ('tr_seeded_1', 'acc_savings_456', 'acc_checking_123', '500000.00', 'COMPLETED', '2026-09-30T10:00:00Z', NULL),
        ('tr_seeded_2', 'acc_checking_123', 'acc_savings_456', '100000.00', 'COMPLETED', '2026-09-30T10:05:00Z', NULL);
        """)
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
