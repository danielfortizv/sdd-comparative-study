import os
import json
import base64
import pytest
from decimal import Decimal
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import crypto
from fastapi.testclient import TestClient
from main import app


def create_client_envelope(payload_dict: dict, public_pem: str) -> dict:
    """Helper simulating browser Web Crypto hybrid encryption."""
    from cryptography.hazmat.primitives import serialization
    pub_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))

    # 1. Ephemeral 256-bit AES key
    aes_key = os.urandom(32)

    # 2. Random 12-byte IV
    iv = os.urandom(12)

    # 3. Encrypt payload with AES-GCM
    data_bytes = json.dumps(payload_dict).encode("utf-8")
    aesgcm = AESGCM(aes_key)
    ct_with_tag = aesgcm.encrypt(iv, data_bytes, None)

    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]

    # 4. Wrap AES key with backend RSA-OAEP (SHA-256)
    wrapped_key = pub_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return {
        "encrypted_key": base64.b64encode(wrapped_key).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def test_rsa_key_loading():
    """Verifies that private and public keys can be loaded from external configuration."""
    priv = crypto.load_private_key()
    assert isinstance(priv, rsa.RSAPrivateKey)
    pub_pem = crypto.load_public_key_pem()
    assert "-----BEGIN PUBLIC KEY-----" in pub_pem
    assert "-----END PUBLIC KEY-----" in pub_pem


def test_public_key_endpoint():
    """Verifies GET /api/crypto/public-key returns the active RSA public key."""
    client = TestClient(app)
    res = client.get("/api/crypto/public-key")
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "RSA-OAEP-256"
    assert data["format"] == "PEM"
    assert "-----BEGIN PUBLIC KEY-----" in data["public_key"]


def test_hybrid_envelope_encryption_decryption():
    """Verifies client envelope unwrapping and AES-GCM payload decryption in memory."""
    pub_pem = crypto.load_public_key_pem()
    test_payload = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "150000.00",
    }
    envelope = create_client_envelope(test_payload, pub_pem)
    decrypted_bytes = crypto.unwrap_and_decrypt_payload(envelope)
    decrypted_dict = json.loads(decrypted_bytes.decode("utf-8"))
    assert decrypted_dict == test_payload


def test_rejection_of_corrupted_ciphertext():
    """Verifies that tampering with ciphertext fails securely without plaintext fallback."""
    pub_pem = crypto.load_public_key_pem()
    envelope = create_client_envelope({"amount": "500.00"}, pub_pem)

    # Tamper with ciphertext
    raw_ct = base64.b64decode(envelope["ciphertext"])
    tampered_ct = bytes([b ^ 0x01 for b in raw_ct])
    envelope["ciphertext"] = base64.b64encode(tampered_ct).decode("ascii")

    with pytest.raises(crypto.DecryptionError):
        crypto.unwrap_and_decrypt_payload(envelope)


def test_rejection_of_corrupted_tag():
    """Verifies that an invalid authentication tag is immediately rejected."""
    pub_pem = crypto.load_public_key_pem()
    envelope = create_client_envelope({"amount": "500.00"}, pub_pem)

    # Corrupt authentication tag
    raw_tag = base64.b64decode(envelope["tag"])
    tampered_tag = bytes([b ^ 0xFF for b in raw_tag])
    envelope["tag"] = base64.b64encode(tampered_tag).decode("ascii")

    with pytest.raises(crypto.DecryptionError):
        crypto.unwrap_and_decrypt_payload(envelope)


def test_rejection_of_missing_envelope_fields():
    """Verifies that missing envelope attributes fail immediately."""
    with pytest.raises(crypto.DecryptionError):
        crypto.unwrap_and_decrypt_payload({"encrypted_key": "abc"})


def test_at_rest_encryption_and_decryption():
    """Verifies AES-256-GCM field encryption and decryption at rest with 'enc:v1:' prefix."""
    plaintext = "5000000.00"
    encrypted = crypto.encrypt_at_rest(plaintext)
    assert encrypted.startswith("enc:v1:")
    assert crypto.is_encrypted(encrypted) is True

    decrypted = crypto.decrypt_at_rest(encrypted)
    assert decrypted == plaintext


def test_at_rest_exact_decimal_preservation():
    """Verifies that financial amounts at rest preserve exact monetary decimal precision."""
    test_amounts = ["0.01", "1000.50", "5000000.00", "999999999.99"]
    for amt_str in test_amounts:
        enc = crypto.encrypt_at_rest(amt_str)
        dec = crypto.decrypt_at_rest(enc)
        d_val = Decimal(dec)
        assert f"{d_val:.2f}" == amt_str
        assert str(d_val) == amt_str


def test_corrupted_at_rest_envelope_fails():
    """Verifies that corrupted at-rest ciphertext raises ValueError."""
    corrupted = "enc:v1:not_valid_iv:not_valid_ct"
    with pytest.raises(Exception):
        crypto.decrypt_at_rest(corrupted)


def test_api_transfer_with_encrypted_envelope():
    """Verifies that POST /api/transfers accepts CryptographicEnvelope and executes transfer."""
    client = TestClient(app)
    pub_pem = crypto.load_public_key_pem()

    transfer_data = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "200000.00",
    }
    envelope = create_client_envelope(transfer_data, pub_pem)

    res = client.post("/api/transfers", json=envelope)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["amount"] == "200000.00"


def test_api_transfer_rejection_of_plaintext():
    """Verifies that POST /api/transfers rejects plaintext request lacking CryptographicEnvelope fields (FR-005, FR-006)."""
    client = TestClient(app)
    plaintext_data = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "200000.00",
    }
    res = client.post("/api/transfers", json=plaintext_data, headers={"X-Test-Plaintext": "true"})
    # FR-005 permits client error status codes 400 or 422
    assert res.status_code in (400, 422)


def test_api_transfer_rejection_of_corrupted_envelope():
    """Verifies that POST /api/transfers returns HTTP 400 when envelope tag or ciphertext is corrupted."""
    client = TestClient(app)
    pub_pem = crypto.load_public_key_pem()

    transfer_data = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "200000.00",
    }
    envelope = create_client_envelope(transfer_data, pub_pem)
    # Corrupt ciphertext
    envelope["ciphertext"] = base64.b64encode(b"corrupted_ciphertext_data").decode("ascii")

    res = client.post("/api/transfers", json=envelope)
    assert res.status_code == 400
    assert "Invalid cryptographic envelope" in res.json()["detail"]


def test_api_sensitive_transfer_and_encrypted_mfa():
    """Verifies sensitive transfer (>= COP 1M) triggers PENDING_MFA and encrypted MFA confirmation succeeds."""
    client = TestClient(app)
    pub_pem = crypto.load_public_key_pem()

    # 1. Initiate sensitive transfer
    transfer_data = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "1200000.00",
    }
    envelope = create_client_envelope(transfer_data, pub_pem)

    res = client.post("/api/transfers", json=envelope)
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "PENDING_MFA"
    tx_id = data["id"]

    # 2. Confirm MFA with encrypted PIN
    mfa_data = {"code": "123456"}
    mfa_envelope = create_client_envelope(mfa_data, pub_pem)

    confirm_res = client.post(f"/api/transfers/{tx_id}/confirm-mfa", json=mfa_envelope)
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "COMPLETED"


def test_raw_sqlite_persistence_is_actually_encrypted():
    """Preliminary Verification: Directly connects via raw sqlite3.connect() to verify at-rest ciphertext."""
    import sqlite3
    db_path = os.environ.get("TEST_DB_PATH")
    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.cursor()
    cursor.execute("SELECT balance FROM accounts;")
    rows = cursor.fetchall()
    raw_conn.close()
    assert len(rows) > 0
    for (bal,) in rows:
        assert bal.startswith("enc:v1:")


def test_mfa_code_conflict_rejected():
    """Preliminary Verification: Rejects conflicting code and mfa_code values in MFACodeConfirm."""
    from models import MFACodeConfirm
    from pydantic import ValidationError

    # Valid with code only
    m1 = MFACodeConfirm(code="123456")
    assert m1.code == "123456"

    # Valid with mfa_code only
    m2 = MFACodeConfirm(mfa_code="123456")
    assert m2.code == "123456"

    # Valid with matching code and mfa_code
    m3 = MFACodeConfirm(code="123456", mfa_code="123456")
    assert m3.code == "123456"

    # Invalid with conflicting code and mfa_code
    with pytest.raises(ValidationError):
        MFACodeConfirm(code="123456", mfa_code="654321")

    # Invalid with empty code
    with pytest.raises(ValidationError):
        MFACodeConfirm(code="")


def test_fail_closed_encryption_failure_injection(monkeypatch):
    """Negative Security Test: Verifies that if encryption fails, the financial mutation rolls back completely
    and zero newly persisted plaintext appears in raw SQLite (H4-02).
    """
    import sqlite3
    import services
    import api

    # Record baseline state directly from raw SQLite
    db_path = os.environ.get("TEST_DB_PATH")
    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id, balance FROM accounts WHERE id = 'acc_checking_123';")
    before_row = cursor.fetchone()
    raw_conn.close()

    # Inject failure into encryption
    def broken_encrypt(*args, **kwargs):
        raise RuntimeError("Simulated at-rest encryption engine failure")

    monkeypatch.setattr(crypto, "encrypt_at_rest", broken_encrypt)
    monkeypatch.setattr(services, "encrypt_at_rest", broken_encrypt)
    monkeypatch.setattr(services, "encrypt_val", broken_encrypt)
    monkeypatch.setattr(api, "encrypt_val", broken_encrypt)

    client = TestClient(app)
    pub_pem = crypto.load_public_key_pem()
    transfer_data = {
        "source_account_id": "acc_checking_123",
        "destination_account_id": "acc_savings_456",
        "amount": "100000.00",
    }
    envelope = create_client_envelope(transfer_data, pub_pem)

    res = client.post("/api/transfers", json=envelope)
    # Must fail securely with server error (500)
    assert res.status_code == 500

    # Inspect raw SQLite directly
    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.cursor()
    cursor.execute("SELECT id, balance FROM accounts WHERE id = 'acc_checking_123';")
    after_row = cursor.fetchone()

    # Verify no newly persisted plaintext and exact balance rollback
    cursor.execute("SELECT balance FROM accounts;")
    all_balances = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT amount FROM transfers;")
    all_transfers = [r[0] for r in cursor.fetchall()]
    raw_conn.close()

    assert after_row == before_row
    for bal in all_balances:
        assert bal.startswith("enc:v1:"), f"Found plaintext balance in raw SQLite: {bal}"
    for amt in all_transfers:
        assert amt.startswith("enc:v1:"), f"Found plaintext transfer amount in raw SQLite: {amt}"


def test_corrupted_authenticated_ciphertext_fails_closed():
    """Negative Security Test: Verifies that corrupted authenticated ciphertext raises an exception
    and never silently falls back to plaintext (H4-02).
    """
    corrupted_envelope = "enc:v1:YWJjZGVmZ2hpamts:Y29ycnVwdGVkX2NpcGhlcnRleHRfdGFn"
    with pytest.raises(Exception):
        crypto.decrypt_at_rest(corrupted_envelope)

    with pytest.raises(Exception):
        from services import decrypt_val
        decrypt_val(corrupted_envelope)


