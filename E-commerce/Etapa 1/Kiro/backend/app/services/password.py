"""Shared password hashing helper (service layer).

Authentication accepts a password only as request input. It is never kept or
returned as readable plain text; it is stored solely as a one-way hash
(Requirements 7.2, 7.3). This module centralizes the hashing/verification so
registration and sign-in share one consistent credential-handling policy.

The hashing uses the established ``bcrypt`` library, a standard one-way
password hashing scheme appropriate for the demonstration scope. No raw
password value is logged, stored, or returned by anything here.
"""

from __future__ import annotations

import bcrypt

# bcrypt operates on a 72-byte secret limit. Longer inputs are reduced to a
# fixed-size digest first so any length of password can be hashed consistently,
# while the stored value remains a one-way hash and never the plain text.
import hashlib


def _to_secret(password: str) -> bytes:
    """Return the bytes bcrypt should hash for the given password.

    bcrypt silently truncates anything beyond 72 bytes, so passwords longer
    than that are pre-hashed to a fixed-length digest. This keeps the full
    password material contributing to the stored hash without ever retaining
    the readable plain text.
    """
    raw = password.encode("utf-8")
    if len(raw) > 72:
        # Pre-hash to a 64-char hex digest (<= 72 bytes) before bcrypt.
        return hashlib.sha256(raw).hexdigest().encode("ascii")
    return raw


def hash_password(password: str) -> str:
    """Return a one-way hash of the given plain-text password.

    The returned value is a bcrypt hash, never the readable plain-text
    password, so it is safe to store as ``passwordHash`` (Requirement 7.3). The
    plain-text ``password`` argument is only read to compute the hash and is
    not retained.
    """
    hashed = bcrypt.hashpw(_to_secret(password), bcrypt.gensalt())
    return hashed.decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches the stored ``password_hash``.

    Used by sign-in to check a submitted credential against the stored hash
    without ever reconstructing the plain-text password.
    """
    try:
        return bcrypt.checkpw(_to_secret(password), password_hash.encode("ascii"))
    except ValueError:
        # A malformed stored hash never matches.
        return False
