"""Cryptographic services for Shift Bank Stage 3.

Implements:
1. RSA-OAEP asymmetric keypair loading and ephemeral AES key unwrapping.
2. AES-256-GCM client-to-server authenticated payload decryption.
3. AES-256-GCM authenticated field-level encryption/decryption at rest (enc:v1:...).
4. Keyed HMAC-SHA256 calculation for immutable audit chaining.
5. Canonical JSON digest computation for audit payload snapshots.
"""

import os
import json
import base64
import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class DecryptionError(Exception):
    """Raised when envelope unwrapping, tag validation, or decryption fails."""
    pass


def get_storage_key() -> bytes:
    """Retrieves and parses the 256-bit symmetric storage key from environment."""
    key_hex = os.environ.get("BANK_STORAGE_KEY", "")
    if not key_hex:
        raise RuntimeError("BANK_STORAGE_KEY environment variable is missing.")
    try:
        # Support 64 hex characters (32 bytes) or base64 32 bytes
        if len(key_hex) == 64:
            return bytes.fromhex(key_hex)
        key_bytes = base64.b64decode(key_hex)
        if len(key_bytes) == 32:
            return key_bytes
    except Exception as e:
        raise RuntimeError(f"Invalid BANK_STORAGE_KEY format: {e}")
    raise RuntimeError("BANK_STORAGE_KEY must be exactly 32 bytes (64 hex characters or 32-byte base64).")


def get_audit_signing_key() -> bytes:
    """Retrieves the HMAC secret key for audit ledger chaining from environment."""
    key_str = os.environ.get("AUDIT_SIGNING_KEY", "")
    if not key_str:
        raise RuntimeError("AUDIT_SIGNING_KEY environment variable is missing.")
    return key_str.encode("utf-8")


def get_audit_admin_key() -> str:
    """Retrieves the administrative verification secret token from environment."""
    key_str = os.environ.get("AUDIT_ADMIN_KEY", "")
    if not key_str:
        raise RuntimeError("AUDIT_ADMIN_KEY environment variable is missing.")
    return key_str


def load_private_key() -> rsa.RSAPrivateKey:
    """Loads backend RSA private key from BANK_PRIVATE_KEY_PATH."""
    key_path = os.environ.get("BANK_PRIVATE_KEY_PATH", "")
    if not key_path or not os.path.exists(key_path):
        raise RuntimeError(f"BANK_PRIVATE_KEY_PATH not found or invalid: {key_path}")
    with open(key_path, "rb") as f:
        pem_data = f.read()
    return serialization.load_pem_private_key(pem_data, password=None)


def load_public_key_pem() -> str:
    """Returns PEM representation of the backend RSA public key."""
    pub_path = os.environ.get("BANK_PUBLIC_KEY_PATH", "")
    if pub_path and os.path.exists(pub_path):
        with open(pub_path, "r", encoding="utf-8") as f:
            return f.read()
    # Alternatively derive from private key
    priv_key = load_private_key()
    pub_key = priv_key.public_key()
    pem_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_bytes.decode("utf-8")


def unwrap_and_decrypt_payload(envelope_data: dict) -> bytes:
    """
    Unwraps ephemeral AES key via RSA-OAEP (SHA-256) and decrypts AES-256-GCM payload.
    Expected envelope structure:
    {
        "encrypted_key": "<base64>",
        "iv": "<base64>",
        "ciphertext": "<base64>",
        "tag": "<base64>"
    }
    Raises DecryptionError on any failure. Plaintext fallback is strictly prohibited.
    """
    try:
        encrypted_key_b64 = envelope_data.get("encrypted_key", "")
        iv_b64 = envelope_data.get("iv", "")
        ciphertext_b64 = envelope_data.get("ciphertext", "")
        tag_b64 = envelope_data.get("tag", "")

        if not all([encrypted_key_b64, iv_b64, ciphertext_b64, tag_b64]):
            raise DecryptionError("Missing required cryptographic envelope fields.")

        wrapped_key = base64.b64decode(encrypted_key_b64)
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        tag = base64.b64decode(tag_b64)

        if len(iv) != 12:
            raise DecryptionError("Initialization vector must be exactly 12 bytes.")
        if len(tag) != 16:
            raise DecryptionError("Authentication tag must be exactly 16 bytes.")

        priv_key = load_private_key()
        aes_key = priv_key.decrypt(
            wrapped_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        if len(aes_key) != 32:
            raise DecryptionError("Unwrapped AES key must be exactly 32 bytes.")

        aesgcm = AESGCM(aes_key)
        # AESGCM.decrypt expects ciphertext + tag concatenated
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext + tag, None)
        return plaintext_bytes

    except (InvalidTag, ValueError, TypeError, KeyError) as e:
        raise DecryptionError(f"Decryption or tag verification failed: {e}")
    except Exception as e:
        if isinstance(e, DecryptionError):
            raise
        raise DecryptionError(f"Cryptographic processing error: {e}")


def encrypt_at_rest(plaintext: str, storage_key: bytes | None = None) -> str:
    """
    Encrypts a sensitive plaintext string for SQLite persistence using AES-256-GCM.
    Returns: enc:v1:<base64_iv>:<base64_ciphertext_and_tag>
    """
    key = storage_key or get_storage_key()
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    iv_b64 = base64.b64encode(iv).decode("ascii")
    ct_b64 = base64.b64encode(ciphertext_and_tag).decode("ascii")
    return f"enc:v1:{iv_b64}:{ct_b64}"


def decrypt_at_rest(envelope_str: str, storage_key: bytes | None = None) -> str:
    """
    Decrypts an authenticated ciphertext string from SQLite persistence.
    If the value does not have the 'enc:v1:' prefix, raises ValueError.
    """
    if not is_encrypted(envelope_str):
        raise ValueError(f"Value is not an authenticated ciphertext envelope: {envelope_str[:15]}...")

    parts = envelope_str.split(":")
    if len(parts) != 4 or parts[0] != "enc" or parts[1] != "v1":
        raise ValueError("Invalid ciphertext envelope format.")

    key = storage_key or get_storage_key()
    iv = base64.b64decode(parts[2])
    ciphertext_and_tag = base64.b64decode(parts[3])

    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext_and_tag, None)
    return plaintext_bytes.decode("utf-8")


def is_encrypted(value: str | None) -> bool:
    """Checks whether a string value is an authenticated ciphertext envelope."""
    if not value or not isinstance(value, str):
        return False
    return value.startswith("enc:v1:")


def compute_hmac(key: bytes, message: bytes) -> str:
    """Computes HMAC-SHA256 hex digest for audit chaining."""
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def compute_payload_digest(data: dict | str) -> str:
    """Computes SHA-256 hex digest of canonical JSON metadata for audit records."""
    if isinstance(data, dict):
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    else:
        canonical_str = str(data)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
