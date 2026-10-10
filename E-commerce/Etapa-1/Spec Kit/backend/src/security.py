import hashlib
import os

# Secure PBKDF2 parameters
ITERATIONS = 100000
HASH_NAME = "sha256"


def hash_password(password: str) -> str:
    """
    Derives a secure PBKDF2 hash using salt and a fixed iteration count.
    Returns the string formatted as 'salt_hex:hash_hex' to be stored.
    """
    salt = os.urandom(16)
    pwd_bytes = password.encode("utf-8")
    derived_hash = hashlib.pbkdf2_hmac(HASH_NAME, pwd_bytes, salt, ITERATIONS)
    return f"{salt.hex()}:{derived_hash.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies if the provided plain text password matches the stored hashed_password.
    The hashed_password format is expected to be 'salt_hex:hash_hex'.
    """
    try:
        salt_hex, original_hash_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pwd_bytes = password.encode("utf-8")
        derived_hash = hashlib.pbkdf2_hmac(HASH_NAME, pwd_bytes, salt, ITERATIONS)
        return derived_hash.hex() == original_hash_hex
    except Exception:
        return False
