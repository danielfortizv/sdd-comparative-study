"""Disposable E3-shaped SQLite fixtures for Stage 4 migration tests."""
import sqlite3


def create_e3_database(path: str, checking: str = "5000000.00", savings: str = "15000000.00"):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE accounts(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,balance TEXT NOT NULL,currency TEXT NOT NULL DEFAULT 'COP')")
    conn.execute("CREATE TABLE transfers(id TEXT PRIMARY KEY,source_account_id TEXT NOT NULL,destination_account_id TEXT,amount TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT,transfer_type TEXT NOT NULL DEFAULT 'INTERNAL',recipient_name TEXT,bank_name TEXT,routing_number TEXT,account_number TEXT,settled_at TEXT,failed_at TEXT,refunded_at TEXT)")
    conn.executemany("INSERT INTO accounts VALUES(?,?,?,'COP')", [
        ("acc_checking_123", "Checking", checking), ("acc_savings_456", "Savings", savings)])
    conn.execute("INSERT INTO transfers(id,source_account_id,destination_account_id,amount,status,created_at,expires_at,transfer_type) VALUES('legacy-1','acc_savings_456','acc_checking_123','500000.00','COMPLETED','2026-09-30T10:00:00Z',NULL,'INTERNAL')")
    conn.commit()
    conn.close()
    return path
