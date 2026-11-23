"""Automated concurrency and financial invariant tests (Milestone 5, H5-02).

Verifies that:
1. High-concurrency internal transfers strictly conserve total funds without lost updates.
2. Concurrent transfer attempts cannot bypass daily limits through race conditions or stale pre-lock checks.
3. Every completed or rejected transfer is committed with an immutable HMAC-chained audit log record.
"""

import concurrent.futures
import os
import sys
from decimal import Decimal

import pytest

# Ensure backend/src is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from conftest import create_test_client_envelope
from database import get_connection, init_db
from fastapi.testclient import TestClient
from main import app
from models import LimitUpdate
from services import decrypt_val, get_limits, update_limits, verify_audit_ledger


@pytest.fixture
def client():
    return TestClient(app)


def test_concurrent_transfers_conserve_funds(client):
    """Verifies that concurrent transfers across multiple threads maintain 100% funds conservation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, balance FROM accounts WHERE id IN ('acc_checking_123', 'acc_savings_456');")
    initial_rows = cursor.fetchall()
    conn.close()

    initial_total = sum(Decimal(decrypt_val(r[1])) for r in initial_rows)

    def _execute_transfer(pair):
        src, dst, amt = pair
        envelope = create_test_client_envelope({
            "source_account_id": src,
            "destination_account_id": dst,
            "amount": amt,
        })
        resp = client.post("/api/transfers", json=envelope)
        return resp.status_code

    # 20 concurrent transfers back and forth
    tasks = [
        ("acc_checking_123", "acc_savings_456", "100.00") if i % 2 == 0
        else ("acc_savings_456", "acc_checking_123", "100.00")
        for i in range(20)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_execute_transfer, tasks))

    # D-14 rejects commands whose expected versions became stale while racing.
    assert all(code in (200, 201, 409) for code in results)
    assert any(code in (200, 201) for code in results)

    # Verify funds conservation
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, balance FROM accounts WHERE id IN ('acc_checking_123', 'acc_savings_456');")
    post_rows = cursor.fetchall()
    post_total = sum(Decimal(decrypt_val(r[1])) for r in post_rows)

    assert post_total == initial_total

    # Verify audit ledger integrity
    audit_report = verify_audit_ledger(conn)
    assert audit_report.is_valid is True
    conn.close()


def test_concurrent_transfers_cannot_bypass_limits(client):
    """
    Verifies that concurrent transfers cannot bypass daily limits via race conditions
    or stale pre-lock validation.
    """
    conn = get_connection()
    current_limits = get_limits(conn)
    current_cons = Decimal(current_limits.current_daily_consumption)
    # Set daily limit to allow exactly 500.00 COP of additional transfers today
    target_daily = current_cons + Decimal("500.00")
    update_limits(conn, LimitUpdate(per_transfer_limit="1000.00", daily_limit=f"{target_daily:.2f}"))
    conn.close()

    def _attempt_transfer():
        envelope = create_test_client_envelope({
            "source_account_id": "acc_checking_123",
            "destination_account_id": "acc_savings_456",
            "amount": "300.00",
        })
        resp = client.post("/api/transfers", json=envelope)
        return resp.status_code, resp.json()

    # Launch 5 concurrent attempts to transfer 300.00 COP each (300 * 5 = 1500 > 500 limit)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_attempt_transfer) for _ in range(5)]
        outcomes = [f.result() for f in futures]

    successes = [o for o in outcomes if o[0] in (200, 201)]
    rejections = [o for o in outcomes if o[0] in (400, 409)]

    # Exactly 1 transfer of 300.00 can succeed before the 500.00 daily limit is reached!
    # The remaining 4 MUST be rejected with HTTP 400!
    assert len(successes) == 1
    assert len(rejections) == 4

    # Verify remaining availability in limits
    conn = get_connection()
    limits = get_limits(conn)
    assert Decimal(limits.current_daily_consumption) == current_cons + Decimal("300.00")
    assert Decimal(limits.remaining_daily_availability) == Decimal("200.00")

    # Verify audit ledger integrity
    audit_report = verify_audit_ledger(conn)
    assert audit_report.is_valid is True
    conn.close()
