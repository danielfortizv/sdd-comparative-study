import hashlib
import os
import secrets
from app.database import USERS, SESSIONS

ITERATIONS = 100000
HASH_NAME = 'sha256'

def hash_password(password: str) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-SHA256 with a unique salt.
    Returns (hex_hashed_password, hex_salt).
    """
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac(HASH_NAME, password.encode('utf-8'), salt, ITERATIONS)
    return hashed.hex(), salt.hex()

def verify_password(password: str, hashed_password: str, salt_hex: str) -> bool:
    """
    Verifies a password against its PBKDF2-SHA256 hash using the provided salt.
    """
    salt = bytes.fromhex(salt_hex)
    hashed_attempt = hashlib.pbkdf2_hmac(HASH_NAME, password.encode('utf-8'), salt, ITERATIONS)
    return hashed_attempt.hex() == hashed_password

def create_session(username: str) -> str:
    """
    Creates an active token-based session for a user.
    Returns a secure unique token.
    """
    token = secrets.token_hex(24)
    SESSIONS[token] = username
    return token

def delete_session(token: str) -> bool:
    """
    Invalidates a user session token.
    Returns True if successfully deleted, False otherwise.
    """
    if token in SESSIONS:
        del SESSIONS[token]
        return True
    return False

def get_username_by_token(token: str) -> str | None:
    """
    Returns the username associated with the token if active, else None.
    """
    return SESSIONS.get(token)
