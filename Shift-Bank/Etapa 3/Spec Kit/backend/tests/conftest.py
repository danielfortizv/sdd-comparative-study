import os
import sys
import json
import base64
import secrets
import shutil
import pytest
from starlette.testclient import TestClient as StarletteTestClient
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Ensure backend/src is in sys.path
backend_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

# Configure isolated test database path to strictly prevent modifying backend/shift_bank.db (D-02, F-10)
TEST_DB_PATH = None
os.environ["ENABLE_TEST_ENDPOINTS"] = "true"

# Cryptographic test keys configuration (T002)
TEST_CERTS_DIR = None
TEST_PRIV_KEY_PATH = None
TEST_PUB_KEY_PATH = None

# Generate secure random test keys dynamically
TEST_STORAGE_KEY = secrets.token_hex(32)  # 256-bit AES storage key
TEST_AUDIT_SIGNING_KEY = secrets.token_urlsafe(32)
TEST_AUDIT_ADMIN_KEY = secrets.token_urlsafe(32)

os.environ["BANK_STORAGE_KEY"] = TEST_STORAGE_KEY
os.environ["AUDIT_SIGNING_KEY"] = TEST_AUDIT_SIGNING_KEY
os.environ["AUDIT_ADMIN_KEY"] = TEST_AUDIT_ADMIN_KEY
def _setup_test_crypto_keys():
    """Generates an ephemeral RSA-2048 keypair for testing if not already generated."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
    pub_pem = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(TEST_PRIV_KEY_PATH, "wb") as f:
        f.write(priv_pem)
    with open(TEST_PUB_KEY_PATH, "wb") as f:
        f.write(pub_pem)


import database
import crypto


def create_test_client_envelope(payload_dict: dict) -> dict:
    """Shared test helper that wraps a payload dict into a valid CryptographicEnvelope."""
    pub_pem = crypto.load_public_key_pem()
    pub_key = serialization.load_pem_public_key(pub_pem.encode("utf-8"))

    aes_key = os.urandom(32)
    iv = os.urandom(12)

    data_bytes = json.dumps(payload_dict).encode("utf-8")
    aesgcm = AESGCM(aes_key)
    ct_with_tag = aesgcm.encrypt(iv, data_bytes, None)

    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]

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


# ==============================================================================
# Test-Only Encryption Transport Adapter for Inherited Test Compatibility
# ==============================================================================

_orig_request = StarletteTestClient.request

ENCRYPTED_TARGET_PREFIXES = (
    "/api/transfers",
    "/api/ach/transfers",
    "/api/beneficiaries",
    "/api/limits",
    "/api/recurring-schedules",
    "/api/recurring-transfers",
)


def _is_encrypted_target(url_str: str) -> bool:
    for target in ENCRYPTED_TARGET_PREFIXES:
        if target in url_str:
            return True
    if "/confirm-mfa" in url_str or "/mfa" in url_str:
        return True
    return False


def _test_client_request(self, method: str, url, *args, **kwargs):
    headers = kwargs.get("headers")
    # Negative security test escape hatch: explicitly allow raw plaintext
    if headers and headers.get("X-Test-Plaintext") == "true":
        clean_headers = {k: v for k, v in headers.items() if k != "X-Test-Plaintext"}
        kwargs["headers"] = clean_headers
        return _orig_request(self, method, url, *args, **kwargs)

    # Automatically adapt transport for sensitive mutation endpoints
    if method.upper() in ("POST", "PUT") and "json" in kwargs:
        payload = kwargs["json"]
        url_str = str(url)
        if _is_encrypted_target(url_str):
            # If payload is already a CryptographicEnvelope, preserve it as-is
            if isinstance(payload, dict) and all(k in payload for k in ("encrypted_key", "iv", "ciphertext", "tag")):
                pass
            elif isinstance(payload, dict):
                # Wrap plaintext dict in an encrypted envelope through test transport
                kwargs["json"] = create_test_client_envelope(payload)

    return _orig_request(self, method, url, *args, **kwargs)


StarletteTestClient.request = _test_client_request


# ==============================================================================
# Test Connection Wrapper for Inherited Direct DB Assertions
# ==============================================================================

_orig_get_connection = database.get_connection


class TestCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, *args, **kwargs):
        self._cursor.execute(*args, **kwargs)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return tuple(self._decrypt_if_needed(v) for v in row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [tuple(self._decrypt_if_needed(v) for v in row) for row in rows]

    def _decrypt_if_needed(self, val):
        if isinstance(val, str) and val.startswith("enc:v1:"):
            try:
                return crypto.decrypt_at_rest(val)
            except Exception:
                return val
        return val

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class TestConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return TestCursorWrapper(self._conn.cursor())

    def execute(self, *args, **kwargs):
        cursor = self._conn.execute(*args, **kwargs)
        return TestCursorWrapper(cursor)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _test_get_connection(db_path: str | None = None):
    raw_conn = _orig_get_connection(db_path)
    return TestConnectionWrapper(raw_conn)


database.get_connection = _test_get_connection


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database(tmp_path_factory):
    """Session fixture ensuring tests run strictly against an isolated database and clean up afterward."""
    global TEST_DB_PATH, TEST_CERTS_DIR, TEST_PRIV_KEY_PATH, TEST_PUB_KEY_PATH
    session_root = tmp_path_factory.mktemp("shift_bank_pytest")
    TEST_DB_PATH = str(session_root / "test_shift_bank.db")
    TEST_CERTS_DIR = str(session_root / "certs")
    TEST_PRIV_KEY_PATH = os.path.join(TEST_CERTS_DIR, "test_bank_private.pem")
    TEST_PUB_KEY_PATH = os.path.join(TEST_CERTS_DIR, "test_bank_public.pem")
    os.environ["TEST_DB_PATH"] = TEST_DB_PATH
    os.environ["BANK_PRIVATE_KEY_PATH"] = TEST_PRIV_KEY_PATH
    os.environ["BANK_PUBLIC_KEY_PATH"] = TEST_PUB_KEY_PATH
    os.environ["ENABLE_TEST_ENDPOINTS"] = "true"
    os.makedirs(TEST_CERTS_DIR, exist_ok=False)
    _setup_test_crypto_keys()
    database.init_db(TEST_DB_PATH)
    yield
    # pytest owns session_root and removes only this uniquely created directory.


@pytest.fixture(autouse=True)
def reset_limits_to_defaults():
    """Resets user_mock_001 limits to default COP 5M / COP 10M before every test function (D-01).
    Ensures complete isolation between test modules.
    """
    conn = _orig_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT per_transfer_limit FROM limits WHERE user_id = 'user_mock_001';")
        row = cursor.fetchone()
        if row:
            from services import encrypt_if_configured
            per_tr = encrypt_if_configured("5000000.00")
            daily = encrypt_if_configured("10000000.00")
            cursor.execute("""
                UPDATE limits
                SET per_transfer_limit = ?, daily_limit = ?
                WHERE user_id = 'user_mock_001';
            """, (per_tr, daily))
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
    yield


# ==============================================================================
# Synthetic Load Testing Database Generator (T024, FR-028)
# ==============================================================================

LOAD_TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_load_bank.db"))


def seed_synthetic_load_db(db_path: str = LOAD_TEST_DB_PATH) -> dict:
    """Pre-seeds an isolated database with high-value synthetic accounts and limits for load testing (FR-028, T024)."""
    scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from seed_load_db import seed_load_database
    return seed_load_database(db_path=db_path, clean=True)


@pytest.fixture
def synthetic_load_db(tmp_path):
    """Pytest fixture providing a dedicated synthetic load test database for tests."""
    temp_db = str(tmp_path / "test_load_bank.db")
    summary = seed_synthetic_load_db(temp_db)
    yield temp_db, summary
    for ext in ("", "-wal", "-shm"):
        p = temp_db + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

