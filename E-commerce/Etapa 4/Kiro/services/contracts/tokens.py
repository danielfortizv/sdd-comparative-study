"""Signed opaque bearer tokens for internal authorization (Stage 4 R5.1).

The monolith kept a single in-process session and trusted nothing from the
client. Stage 4 replaces that with a stateless, HMAC-signed token issued by the
identity service on login. Any service can verify the signature with the shared
secret and read the embedded claims, so the **role lives inside the signed
token** and a client cannot forge a moderator role by sending a header.

Format: ``<base64url(payload_json)>.<base64url(hmac_sha256(payload_json))>``.
Tokens are compact and self-validating; identity remains the only issuer.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from contracts.settings import get_settings


@dataclass(frozen=True)
class TokenClaims:
    """Verified claims carried by a session token."""

    customer_id: str
    identifier: str
    is_moderator: bool
    issued_at: int


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(payload: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()


def issue_token(
    customer_id: str,
    identifier: str,
    is_moderator: bool,
    *,
    secret: str | None = None,
) -> str:
    """Issue a signed token embedding the account's identity and role."""
    signing_secret = secret if secret is not None else get_settings().token_secret
    payload = {
        "customerId": customer_id,
        "identifier": identifier,
        "isModerator": bool(is_moderator),
        "iat": int(time.time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    signature = _sign(payload_bytes, signing_secret)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def verify_token(token: str, *, secret: str | None = None) -> TokenClaims | None:
    """Return the token's claims if the signature is valid, else ``None``.

    A tampered payload or signature, a malformed token, or a wrong secret all
    yield ``None`` so callers treat the request as unauthenticated.
    """
    signing_secret = secret if secret is not None else get_settings().token_secret
    if not token or token.count(".") != 1:
        return None
    payload_part, signature_part = token.split(".", 1)
    try:
        payload_bytes = _b64url_decode(payload_part)
        provided_signature = _b64url_decode(signature_part)
    except (ValueError, TypeError):
        return None

    expected_signature = _sign(payload_bytes, signing_secret)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    try:
        return TokenClaims(
            customer_id=str(payload["customerId"]),
            identifier=str(payload["identifier"]),
            is_moderator=bool(payload["isModerator"]),
            issued_at=int(payload["iat"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
