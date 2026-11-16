"""Automated tests for granular fail-closed behavior when individual secrets are missing (H6-02 Item 5).

Verifies that with a valid database and valid remaining configuration:
1. Omitting ONLY BANK_STORAGE_KEY causes /api/health to return 503 and blocks account/transfer operations.
2. Omitting ONLY AUDIT_SIGNING_KEY causes /api/health to return 503 and blocks sensitive mutations.
3. Omitting ONLY AUDIT_ADMIN_KEY causes /api/health to return 503 and rejects administrative audit verification.
4. Omitting ONLY BANK_PRIVATE_KEY_PATH causes /api/health to return 503 and blocks encrypted payload processing.
"""

import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from conftest import create_test_client_envelope
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_fail_closed_missing_only_storage_key(client, monkeypatch):
    """With valid DB and other keys, removing ONLY BANK_STORAGE_KEY must return 503 and block balance decryption."""
    monkeypatch.delenv("BANK_STORAGE_KEY", raising=False)

    # 1. Healthcheck reports 503 unhealthy
    health = client.get("/api/health")
    assert health.status_code == 503
    assert health.json()["status"] == "unhealthy"
    assert health.json()["crypto_keys_loaded"] is False

    # 2. Account balance decryption fails closed
    acc_resp = client.get("/api/accounts")
    assert acc_resp.status_code in (500, 503)


def test_fail_closed_missing_only_audit_signing_key(client, monkeypatch):
    """With valid DB and other keys, removing ONLY AUDIT_SIGNING_KEY must return 503 and block mutations."""
    monkeypatch.delenv("AUDIT_SIGNING_KEY", raising=False)

    # 1. Healthcheck reports 503 unhealthy
    health = client.get("/api/health")
    assert health.status_code == 503
    assert health.json()["status"] == "unhealthy"
    assert health.json()["crypto_keys_loaded"] is False

    # 2. Attempting a mutation requiring audit signing fails closed
    envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100.00",
    })
    tx_resp = client.post("/api/transfers", json=envelope)
    assert tx_resp.status_code in (500, 503)


def test_fail_closed_missing_only_audit_admin_key(client, monkeypatch):
    """With valid DB and other keys, removing ONLY AUDIT_ADMIN_KEY must return 503 and block audit verification."""
    monkeypatch.delenv("AUDIT_ADMIN_KEY", raising=False)

    # 1. Healthcheck reports 503 unhealthy
    health = client.get("/api/health")
    assert health.status_code == 503
    assert health.json()["status"] == "unhealthy"
    assert health.json()["crypto_keys_loaded"] is False

    # 2. Administrative verification rejects requests
    audit_resp = client.get("/api/audit/verify", headers={"X-Audit-Admin-Key": "some_token"})
    assert audit_resp.status_code in (401, 500, 503)


def test_fail_closed_missing_only_private_key(client, monkeypatch):
    """With valid DB and other keys, removing ONLY BANK_PRIVATE_KEY_PATH must return 503 and block envelope decryption."""
    monkeypatch.delenv("BANK_PRIVATE_KEY_PATH", raising=False)

    # 1. Healthcheck reports 503 unhealthy
    health = client.get("/api/health")
    assert health.status_code == 503
    assert health.json()["status"] == "unhealthy"
    assert health.json()["crypto_keys_loaded"] is False

    # 2. Encrypted payload processing fails closed (cannot unwrap AES key)
    envelope = create_test_client_envelope({
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100.00",
    })
    tx_resp = client.post("/api/transfers", json=envelope)
    assert tx_resp.status_code in (400, 500, 503)
