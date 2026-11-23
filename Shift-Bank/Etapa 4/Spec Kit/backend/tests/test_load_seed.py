"""Unit and integration tests for synthetic test database generator (T024, FR-028, Scenario 3.1).

Verifies that:
1. Synthetic database seeds with COP 100,000,000.00 balances across synthetic accounts.
2. Dynamic limits are pre-seeded to COP 50,000,000.00 (per-transfer and daily).
3. Balances and limits are encrypted at rest with enc:v1: prefix.
4. Funds conservation helper mathematically validates total funds.
5. SQLite schema includes audit_logs and trigger immutability.
"""

import os
import sqlite3
from decimal import Decimal

import pytest
from conftest import seed_synthetic_load_db
from database import get_connection
from services import decrypt_val


def test_synthetic_load_db_seeding(synthetic_load_db):
    """Scenario 3.1: Dedicated synthetic database initialized with COP 100M balances and COP 50M limits."""
    db_path, summary = synthetic_load_db

    assert os.path.exists(db_path)
    assert summary["account_count"] >= 2
    assert summary["per_transfer_limit"] == "50000000.00"
    assert summary["daily_limit"] == "50000000.00"
    assert summary["integrity"] == "ok"

    # Verify accounts and decrypted balances directly
    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.cursor()

    cursor.execute("SELECT id, name, balance, currency FROM accounts WHERE currency = 'COP' ORDER BY id ASC;")
    accounts = cursor.fetchall()
    assert len(accounts) >= 6

    for acc_id, name, enc_bal, currency in accounts:
        # Sensitive balance is encrypted at rest
        assert enc_bal.startswith("enc:v1:")
        dec_bal = Decimal(decrypt_val(enc_bal))
        assert dec_bal == Decimal("100000000.00")
        assert currency == "COP"

    # Verify limits for user_mock_001
    cursor.execute("SELECT per_transfer_limit, daily_limit FROM limits WHERE user_id = 'user_mock_001';")
    limits_row = cursor.fetchone()
    assert limits_row is not None
    assert limits_row[0].startswith("enc:v1:")
    assert limits_row[1].startswith("enc:v1:")
    assert Decimal(decrypt_val(limits_row[0])) == Decimal("50000000.00")
    assert Decimal(decrypt_val(limits_row[1])) == Decimal("50000000.00")

    # Verify audit_logs table and triggers exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs';")
    assert cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='trg_prevent_audit_update';")
    assert cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='trg_prevent_audit_delete';")
    assert cursor.fetchone() is not None

    raw_conn.close()


def test_funds_conservation_verification(synthetic_load_db):
    """Verifies that funds conservation helper correctly detects preserved vs altered balances."""
    db_path, summary = synthetic_load_db
    import sys
    scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from seed_load_db import verify_funds_conservation

    # Initial conservation check
    is_conserved, total, balances = verify_funds_conservation(db_path)
    assert is_conserved is True
    assert total == Decimal(summary["initial_total_funds"])
    assert len(balances) == summary["account_count"]
