import sqlite3
import os
from pathlib import Path

# Resolve database path relative to this file
DB_PATH = Path(__file__).resolve().parent / "bank.db"

def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database tables and seeds them if they are empty."""
    db_existed = DB_PATH.exists()
    
    # Ensure parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            balance TEXT NOT NULL
        )
    """)
    
    # Create transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            source_account_id TEXT NOT NULL,
            source_account_name TEXT NOT NULL,
            destination_account_id TEXT NOT NULL,
            destination_account_name TEXT NOT NULL,
            amount TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    conn.commit()
    
    # Check if accounts table is empty to seed initial data
    cursor.execute("SELECT COUNT(*) as count FROM accounts")
    row = cursor.fetchone()
    if row["count"] == 0:
        print("Database is empty. Seeding initial accounts and transactions...")
        try:
            # Seed accounts
            cursor.execute(
                "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
                ("acc_checking", "Cuenta Corriente", "5000000.00")
            )
            cursor.execute(
                "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
                ("acc_savings", "Cuenta de Ahorros", "15000000.00")
            )
            
            # Seed transactions
            # Transaction 1: Savings -> Checking, 500,000.00 COP, 2026-09-28T10:00:00Z
            cursor.execute("""
                INSERT INTO transactions (
                    id, source_account_id, source_account_name, 
                    destination_account_id, destination_account_name, 
                    amount, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "tx_seed_1", "acc_savings", "Cuenta de Ahorros",
                "acc_checking", "Cuenta Corriente",
                "500000.00", "2026-09-28T10:00:00Z", "COMPLETED"
            ))
            
            # Transaction 2: Checking -> Savings, 100,000.00 COP, 2026-09-28T11:00:00Z
            cursor.execute("""
                INSERT INTO transactions (
                    id, source_account_id, source_account_name, 
                    destination_account_id, destination_account_name, 
                    amount, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "tx_seed_2", "acc_checking", "Cuenta Corriente",
                "acc_savings", "Cuenta de Ahorros",
                "100000.00", "2026-09-28T11:00:00Z", "COMPLETED"
            ))
            
            conn.commit()
            print("Database seeded successfully.")
        except Exception as e:
            conn.rollback()
            print(f"Error seeding database: {e}")
            raise e
    else:
        print("Database already contains records. Seeding skipped.")
        
    conn.close()

if __name__ == "__main__":
    init_db()
