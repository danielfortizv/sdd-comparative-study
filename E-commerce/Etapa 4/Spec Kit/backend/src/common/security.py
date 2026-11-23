import base64
import hmac
import hashlib
import json
import os
import time
from typing import Dict, Any, Optional
from fastapi import Header, HTTPException, status

# Secure PBKDF2 parameters for password hashing
ITERATIONS = 100000
HASH_NAME = "sha256"

# Cryptographic secret key for JWT signing (can be overridden via env)
JWT_SECRET = os.environ.get("JWT_SECRET", "stage4-super-secret-key-12345678")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 3600 * 24  # 24 hours


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


def base64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    """Decodes base64url string to bytes, adding back any missing padding."""
    padding = "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt(payload: Dict[str, Any], secret: str = JWT_SECRET) -> str:
    """
    Creates and signs a JSON Web Token (HS256) with standard headers and an expiration.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Ensure payload contains 'exp'
    jwt_payload = payload.copy()
    if "exp" not in jwt_payload:
        jwt_payload["exp"] = int(time.time()) + TOKEN_EXPIRE_SECONDS
        
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(jwt_payload, separators=(",", ":")).encode("utf-8"))
    
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str, secret: str = JWT_SECRET) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies an HS256-signed JWT token.
    Gracefully cleans up literal curly braces (e.g. '{token}') from frontend signout typo.
    Returns the payload if verified, or None if invalid or expired.
    """
    token = token.strip()
    # Safe regex-free stripping of curly braces
    if token.startswith("{") and token.endswith("}"):
        token = token[1:-1].strip()
        
    parts = token.split(".")
    if len(parts) != 3:
        return None
        
    header_b64, payload_b64, signature_b64 = parts
    try:
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        
        # Prevent timing attacks
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
        
        # Expiration validation
        if "exp" in payload and payload["exp"] < time.time():
            return None
            
        return payload
    except Exception:
        return None


def get_user_from_header(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and verify the user from the Authorization bearer header.
    Throws a 401 Unauthenticated exception if invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )
        
    token = parts[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or invalid token. Please sign in.",
        )
        
    return payload
