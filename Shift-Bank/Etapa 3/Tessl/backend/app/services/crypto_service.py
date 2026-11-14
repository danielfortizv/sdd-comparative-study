import os
import json
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union, Tuple
from fastapi import HTTPException, status
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Server key validity duration (24 hours)
KEY_EXPIRATION_HOURS = 24

# In-memory storage for active and previous RSA key pairs:
# key_id -> (private_key, public_key_pem, expires_at)
_key_registry: Dict[str, Tuple[rsa.RSAPrivateKey, str, datetime]] = {}
_active_key_id: Optional[str] = None


def _parse_storage_key(raw_key: Optional[str]) -> bytes:
    """Parse ENCRYPTION_KEY from hex, base64, or raw 32-byte string."""
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY environment variable is missing or empty")

    raw_key = raw_key.strip()

    # 1. Try 64-char hex string (32 bytes)
    if len(raw_key) == 64:
        try:
            key_bytes = bytes.fromhex(raw_key)
            if len(key_bytes) == 32:
                return key_bytes
        except ValueError:
            pass

    # 2. Try base64-encoded string
    try:
        decoded = base64.b64decode(raw_key, validate=True)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    # 3. Try raw 32-byte string
    raw_bytes = raw_key.encode("utf-8")
    if len(raw_bytes) == 32:
        return raw_bytes

    raise ValueError(
        f"ENCRYPTION_KEY must be exactly 32 bytes (256-bit). Received {len(raw_bytes)} bytes."
    )


def get_storage_key() -> bytes:
    """Retrieve and validate the AES-256 storage key from the environment."""
    raw_key = os.getenv("ENCRYPTION_KEY")
    if not raw_key:
        # Check if running in automated test mode
        if os.getenv("TESTING", "false").lower() == "true":
            return b"01234567890123456789012345678901"
        raise ValueError("ENCRYPTION_KEY environment variable is missing or empty")
    return _parse_storage_key(raw_key)


def validate_encryption_key_at_startup() -> None:
    """Fails fast during startup if ENCRYPTION_KEY is missing or invalid."""
    try:
        key = get_storage_key()
        # Verify AESGCM functionality
        aesgcm = AESGCM(key)
        test_nonce = os.urandom(12)
        ct = aesgcm.encrypt(test_nonce, b"test", None)
        aesgcm.decrypt(test_nonce, ct, None)
    except Exception as e:
        raise RuntimeError(f"Cryptographic initialization failure: {e}") from e


def generate_server_rsa_key_pair(expires_in_hours: int = KEY_EXPIRATION_HOURS) -> str:
    """Generate and register a new RSA-2048 key pair with a designated expiration."""
    global _active_key_id
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    now = datetime.now(timezone.utc)
    key_id = f"k_{int(now.timestamp())}_{os.urandom(4).hex()}"
    expires_at = now + timedelta(hours=expires_in_hours)

    _key_registry[key_id] = (private_key, public_pem, expires_at)
    _active_key_id = key_id
    return key_id


def get_active_public_key() -> Dict[str, Any]:
    """Retrieve the current active server public key and metadata."""
    global _active_key_id
    if not _active_key_id or _active_key_id not in _key_registry:
        generate_server_rsa_key_pair()

    assert _active_key_id is not None
    private_key, public_pem, expires_at = _key_registry[_active_key_id]

    # Rotate if expired
    if datetime.now(timezone.utc) >= expires_at:
        generate_server_rsa_key_pair()
        assert _active_key_id is not None
        private_key, public_pem, expires_at = _key_registry[_active_key_id]

    return {
        "key_id": _active_key_id,
        "algorithm": "RSA-OAEP-256",
        "public_key": public_pem,
        "expires_at": expires_at,
    }


def encrypt_at_rest(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a sensitive string at rest using AES-256-GCM (format: enc:v1:<iv>:<tag>:<ciphertext>)."""
    if plaintext is None:
        return None
    val_str = str(plaintext)
    if val_str.startswith("enc:v1:"):
        return val_str

    key = get_storage_key()
    iv = os.urandom(12)  # 96-bit nonce
    aesgcm = AESGCM(key)

    data = val_str.encode("utf-8")
    ct_and_tag = aesgcm.encrypt(iv, data, None)
    ciphertext = ct_and_tag[:-16]
    tag = ct_and_tag[-16:]

    iv_b64 = base64.b64encode(iv).decode("ascii")
    tag_b64 = base64.b64encode(tag).decode("ascii")
    ct_b64 = base64.b64encode(ciphertext).decode("ascii")
    return f"enc:v1:{iv_b64}:{tag_b64}:{ct_b64}"


def decrypt_at_rest(stored_val: Optional[str]) -> Optional[str]:
    """Decrypt an AES-256-GCM string stored at rest."""
    if stored_val is None:
        return None
    val_str = str(stored_val)
    if not val_str.startswith("enc:v1:"):
        raise ValueError(f"Strict persistence validation error: unencrypted data encountered at rest")

    parts = val_str.split(":")
    if len(parts) != 5 or parts[0] != "enc" or parts[1] != "v1":
        raise ValueError("Corrupted at-rest encryption envelope structure")

    try:
        iv = base64.b64decode(parts[2], validate=True)
        tag = base64.b64decode(parts[3], validate=True)
        ciphertext = base64.b64decode(parts[4], validate=True)
    except Exception as e:
        raise ValueError(f"Corrupted base64 in at-rest encryption envelope: {e}") from e

    if len(iv) != 12 or len(tag) != 16:
        raise ValueError("Invalid IV or authentication tag length in stored record")

    key = get_storage_key()
    aesgcm = AESGCM(key)
    try:
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext + tag, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Tamper detection: at-rest decryption failed or key mismatch: {e}") from e


def decrypt_envelope(payload: Dict[str, Any]) -> str:
    """Decrypt an application-layer encrypted field envelope using the server's private RSA key and AES-GCM session key."""
    key_id = payload.get("key_id")
    if not key_id or key_id not in _key_registry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_KEY_ID",
        )

    private_key, _, expires_at = _key_registry[key_id]
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KEY_EXPIRED",
        )

    try:
        encrypted_key_b64 = payload["encrypted_key"]
        iv_b64 = payload["iv"]
        tag_b64 = payload["tag"]
        ciphertext_b64 = payload["ciphertext"]

        encrypted_key = base64.b64decode(encrypted_key_b64, validate=True)
        iv = base64.b64decode(iv_b64, validate=True)
        tag = base64.b64decode(tag_b64, validate=True)
        ciphertext = base64.b64decode(ciphertext_b64, validate=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_ENCRYPTED_PAYLOAD",
        )

    if len(iv) != 12 or len(tag) != 16:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_ENCRYPTED_PAYLOAD",
        )

    # 1. Decrypt ephemeral AES session key with RSA-OAEP-256
    try:
        session_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_ENCRYPTED_PAYLOAD",
        )

    if len(session_key) != 32:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_ENCRYPTED_PAYLOAD",
        )

    # 2. Decrypt field ciphertext with AES-256-GCM
    try:
        aesgcm = AESGCM(session_key)
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext + tag, None)
        return plaintext_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_ENCRYPTED_PAYLOAD",
        )


def decrypt_field_if_needed(val: Any) -> Optional[str]:
    """Transparently decrypt an incoming value if it is an encrypted envelope; return string directly if plaintext."""
    if val is None:
        return None

    # Handle dictionary representation
    if isinstance(val, dict):
        if val.get("__encrypted__") or ("encrypted_key" in val and "ciphertext" in val):
            return decrypt_envelope(val)
        return str(val)

    # Handle string that may contain JSON-encoded envelope
    if isinstance(val, str):
        stripped = val.strip()
        if stripped.startswith("{") and ("encrypted_key" in stripped or "__encrypted__" in stripped):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict) and (parsed.get("__encrypted__") or "encrypted_key" in parsed):
                    return decrypt_envelope(parsed)
            except HTTPException:
                raise
            except Exception:
                pass
        return stripped

    # Handle Pydantic model
    if hasattr(val, "encrypted_key") and hasattr(val, "ciphertext"):
        dumped = val.model_dump() if hasattr(val, "model_dump") else val.__dict__
        return decrypt_envelope(dumped)

    return str(val)


def mask_account_number(acc: Optional[str]) -> Optional[str]:
    """Return a masked representation of an account number showing only the last 4 digits."""
    if not acc:
        return acc
    s = str(acc).strip()
    if len(s) <= 4:
        return "****"
    return f"****{s[-4:]}"
