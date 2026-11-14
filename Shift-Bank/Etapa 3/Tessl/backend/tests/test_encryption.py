import os
import base64
import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.app.services import crypto_service
from backend.app.services.crypto_service import (
    encrypt_at_rest,
    decrypt_at_rest,
    get_active_public_key,
    generate_server_rsa_key_pair,
    validate_encryption_key_at_startup,
    _key_registry,
)
from backend.app.services.migration_service import run_migration


def helper_encrypt_field_for_server(plaintext: str, public_key_pem: str, key_id: str) -> dict:
    """Helper to simulate client-side Web Crypto hybrid encryption."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
    session_key = os.urandom(32)  # 256-bit AES key
    iv = os.urandom(12)  # 96-bit nonce

    aesgcm = AESGCM(session_key)
    ct_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    ciphertext = ct_and_tag[:-16]
    tag = ct_and_tag[-16:]

    encrypted_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return {
        "__encrypted__": True,
        "key_id": key_id,
        "encrypted_key": base64.b64encode(encrypted_key).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def test_public_key_endpoint_success(client: TestClient):
    """GET /api/crypto/public-key returns active RSA public key, algorithm, key_id, and expiration."""
    resp = client.get("/api/crypto/public-key")
    assert resp.status_code == 200
    data = resp.json()
    assert "key_id" in data
    assert data["algorithm"] == "RSA-OAEP-256"
    assert "BEGIN PUBLIC KEY" in data["public_key"]
    assert "expires_at" in data
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    assert expires_at > datetime.now(timezone.utc)


def test_rejection_of_invalid_key_id(client: TestClient):
    """Rejects encryption payloads with HTTP 400 when key_id is unrecognized."""
    pub_info = client.get("/api/crypto/public-key").json()
    envelope = helper_encrypt_field_for_server("123456789", pub_info["public_key"], "invalid_nonexistent_key_id")

    resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Jane Doe",
            "routing_number": envelope,
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "INVALID_KEY_ID"


def test_rejection_of_expired_key(client: TestClient):
    """Rejects encryption payloads with HTTP 400 when key_id is expired."""
    # Generate an expired key pair in registry
    expired_key_id = "k_expired_test"
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    past_expiration = datetime.now(timezone.utc) - timedelta(hours=1)
    _key_registry[expired_key_id] = (priv, pub_pem, past_expiration)

    envelope = helper_encrypt_field_for_server("123456789", pub_pem, expired_key_id)

    resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Jane Doe",
            "routing_number": envelope,
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "KEY_EXPIRED"


def test_invalid_encrypted_payload_handling(client: TestClient):
    """Malformed ciphertext or corrupted tag returns HTTP 422 INVALID_ENCRYPTED_PAYLOAD."""
    pub_info = client.get("/api/crypto/public-key").json()
    envelope = helper_encrypt_field_for_server("123456789", pub_info["public_key"], pub_info["key_id"])

    # Corrupt ciphertext
    corrupted_envelope = dict(envelope)
    corrupted_envelope["ciphertext"] = base64.b64encode(b"corrupted_bytes_0000").decode("ascii")

    resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Jane Doe",
            "routing_number": corrupted_envelope,
            "account_number": "12345678",
            "bank_name": "Test Bank",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "INVALID_ENCRYPTED_PAYLOAD"


def test_end_to_end_encrypted_beneficiary_creation(client: TestClient, db_session):
    """Submitting encrypted routing and account numbers decrypts in memory and encrypts at rest in SQLite."""
    pub_info = client.get("/api/crypto/public-key").json()
    enc_routing = helper_encrypt_field_for_server("987654321", pub_info["public_key"], pub_info["key_id"])
    enc_account = helper_encrypt_field_for_server("4455667788", pub_info["public_key"], pub_info["key_id"])

    resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Encrypted Recipient",
            "routing_number": enc_routing,
            "account_number": enc_account,
            "bank_name": "Cipher National Bank",
        },
    )
    assert resp.status_code == 201
    ben = resp.json()
    assert ben["name"] == "Encrypted Recipient"
    assert ben["routing_number"] == "987654321"
    assert ben["account_number"] == "4455667788"

    # Verify directly in SQLite that values are stored as AES-256-GCM ciphertext
    raw_row = db_session.execute(
        text("SELECT routing_number, account_number FROM beneficiaries WHERE id = :id"),
        {"id": ben["id"]},
    ).fetchone()

    assert raw_row[0].startswith("enc:v1:")
    assert raw_row[1].startswith("enc:v1:")
    # Ensure raw plaintext does not exist on disk
    assert "987654321" not in raw_row[0]
    assert "4455667788" not in raw_row[1]


def test_tamper_detection_at_rest(db_session):
    """Altering ciphertext or authentication tag stored at rest triggers cryptographic integrity failure."""
    original = "123456789"
    encrypted_val = encrypt_at_rest(original)
    assert encrypted_val.startswith("enc:v1:")

    # Normal decryption works
    assert decrypt_at_rest(encrypted_val) == original

    # Tamper with tag
    parts = encrypted_val.split(":")
    tampered_tag = base64.b64encode(b"0" * 16).decode("ascii")
    tampered_val = f"enc:v1:{parts[2]}:{tampered_tag}:{parts[4]}"

    with pytest.raises(ValueError, match="Tamper detection"):
        decrypt_at_rest(tampered_val)


def test_strict_persistence_validation_on_unencrypted_read():
    """Attempting to decrypt unencrypted data at rest raises strict persistence validation error."""
    with pytest.raises(ValueError, match="Strict persistence validation error"):
        decrypt_at_rest("plaintext_account_12345")


def test_fail_fast_on_missing_or_invalid_encryption_key(monkeypatch):
    """Service safely fails fast during initialization if ENCRYPTION_KEY is missing or invalid."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("TESTING", "false")

    with pytest.raises(RuntimeError, match="Cryptographic initialization failure"):
        validate_encryption_key_at_startup()

    # Invalid length (e.g. 10 bytes instead of 32)
    monkeypatch.setenv("ENCRYPTION_KEY", "too_short_key")
    with pytest.raises(RuntimeError, match="Cryptographic initialization failure"):
        validate_encryption_key_at_startup()


def test_idempotent_database_migration(db_session):
    """Verifies that migration encrypts legacy plaintext records, verifies 100%, and is safe to re-run."""
    # 1. Insert legacy plaintext records directly bypassing ORM encryption
    db_session.execute(
        text("INSERT INTO beneficiaries (user_id, name, routing_number, account_number, bank_name) "
             "VALUES (1, 'Legacy Vendor', '111222333', '9988776655', 'Old Bank')")
    )
    db_session.execute(
        text("INSERT INTO transfers (transfer_type, from_account_id, amount, status, routing_number, account_number) "
             "VALUES ('ach', 1, 50.0, 'completed', '444555666', '1234567890')")
    )
    db_session.execute(
        text("INSERT INTO recurring_schedules (user_id, transfer_type, from_account_id, amount, frequency, status, next_execution_date, failure_count, routing_number, account_number) "
             "VALUES (1, 'ach', 1, 25.0, 'monthly', 'active', datetime('now'), 0, '777888999', '5544332211')")
    )
    db_session.commit()

    # 2. Run migration
    result = run_migration(db_session)
    assert result.success is True
    # 2 fields in beneficiary, 2 in transfer, 2 in schedule = 6 fields migrated
    assert result.migrated_records == 6
    assert result.verified_records == 6

    # 3. Check SQLite raw content
    ben_row = db_session.execute(
        text("SELECT routing_number, account_number FROM beneficiaries WHERE name = 'Legacy Vendor'")
    ).fetchone()
    assert ben_row[0].startswith("enc:v1:")
    assert ben_row[1].startswith("enc:v1:")
    assert decrypt_at_rest(ben_row[0]) == "111222333"
    assert decrypt_at_rest(ben_row[1]) == "9988776655"

    # 4. Re-run migration to test idempotency
    second_result = run_migration(db_session)
    assert second_result.success is True
    assert second_result.migrated_records == 0
    assert second_result.skipped_records >= 6
    assert second_result.verified_records >= 6


def test_backward_compatibility_with_plaintext_requests(client: TestClient):
    """Backend transparently accepts plaintext submissions for backward compatibility with Stage 1 and 2."""
    resp = client.post(
        "/api/beneficiaries",
        json={
            "name": "Plaintext Compatibility Recipient",
            "routing_number": "123456789",
            "account_number": "9876543210",
            "bank_name": "Standard Bank",
        },
    )
    assert resp.status_code == 201
    ben = resp.json()
    assert ben["routing_number"] == "123456789"
    assert ben["account_number"] == "9876543210"


def test_migration_failure_executes_atomic_rollback_without_data_loss(db_session, monkeypatch):
    """Migration failure triggers atomic rollback, leaving original records intact without data loss."""
    # Insert legacy plaintext record
    db_session.execute(
        text("INSERT INTO beneficiaries (user_id, name, routing_number, account_number, bank_name) "
             "VALUES (1, 'Uncorrupted Vendor', '987654321', '1122334455', 'Safety Bank')")
    )
    db_session.commit()

    # Simulate failure during verification phase by patching migration_service.decrypt_at_rest
    def fail_verification(stored_val):
        raise ValueError("Simulated verification check failure")

    monkeypatch.setattr("backend.app.services.migration_service.decrypt_at_rest", fail_verification)

    result = run_migration(db_session)
    assert result.success is False
    assert "Simulated verification check failure" in result.error_message

    # Undo patch and verify original data was rolled back and is NOT lost
    monkeypatch.undo()
    row = db_session.execute(
        text("SELECT routing_number, account_number FROM beneficiaries WHERE name = 'Uncorrupted Vendor'")
    ).fetchone()

    # Values must remain their original plaintext prior to failed migration
    assert row[0] == "987654321"
    assert row[1] == "1122334455"


def test_startup_halts_when_migration_fails(monkeypatch):
    """FastAPI lifespan startup fails fast and halts when encryption migration fails."""
    import backend.app.main as main_mod
    from backend.app.services.migration_service import MigrationResult

    def failing_migration(db):
        return MigrationResult(
            success=False,
            migrated_records=0,
            skipped_records=0,
            verified_records=0,
            error_message="Fatal corruption in legacy coordinates",
        )

    monkeypatch.setattr(main_mod, "run_migration", failing_migration)

    with pytest.raises(RuntimeError, match="Startup halted: encryption migration failed"):
        with TestClient(main_mod.app):
            pass



def test_migration_verification_detects_unencrypted_routing_and_rolls_back(db_session, monkeypatch):
    """Migration post-verification detects unencrypted beneficiary routing number and executes rollback."""
    import backend.app.services.migration_service as mig_mod
    db_session.execute(
        text("INSERT INTO beneficiaries (user_id, name, routing_number, account_number, bank_name) "
             "VALUES (1, 'Faulty Routing Vendor', '123123123', '9876543210', 'Faulty Bank')")
    )
    db_session.commit()

    def faulty_encrypt(val):
        return val

    monkeypatch.setattr(mig_mod, "encrypt_at_rest", faulty_encrypt)

    result = run_migration(db_session)
    assert result.success is False
    assert "routing_number not encrypted" in result.error_message


def test_migration_verification_detects_corrupt_account_length_and_rolls_back(db_session, monkeypatch):
    """Migration post-verification detects corrupt or short decrypted account number and executes rollback."""
    import backend.app.services.migration_service as mig_mod
    db_session.execute(
        text("INSERT INTO beneficiaries (user_id, name, routing_number, account_number, bank_name) "
             "VALUES (1, 'Short Account Vendor', '999888777', '11223344', 'Short Bank')")
    )
    db_session.commit()

    real_decrypt = mig_mod.decrypt_at_rest
    def corrupt_decrypt(val):
        res = real_decrypt(val)
        return "12" if res == "11223344" else res

    monkeypatch.setattr(mig_mod, "decrypt_at_rest", corrupt_decrypt)

    result = run_migration(db_session)
    assert result.success is False
    assert "account_number invalid or decrypt failed" in result.error_message


def test_migration_verification_detects_unencrypted_transfer_record(db_session, monkeypatch):
    """Migration post-verification detects unencrypted transfer coordinates and executes rollback."""
    import backend.app.services.migration_service as mig_mod
    db_session.execute(
        text("INSERT INTO transfers (transfer_type, from_account_id, to_account_id, amount, status, routing_number, account_number) "
             "VALUES ('ach', 1, 2, 50.0, 'completed', '444555666', '12345678')")
    )
    db_session.commit()

    real_encrypt = mig_mod.encrypt_at_rest
    def unencrypted_transfer_encrypt(val):
        if val == "444555666":
            return val
        return real_encrypt(val)

    monkeypatch.setattr(mig_mod, "encrypt_at_rest", unencrypted_transfer_encrypt)

    result = run_migration(db_session)
    assert result.success is False
    assert "Transfer" in result.error_message and "routing_number not encrypted" in result.error_message
