"""Password verification helper (sign-in side).

This module provides a single ``verify_password`` helper used by the sign-in
service to check a submitted plain-text ``password`` against a stored
``passwordHash`` (Requirements 6.9, 7.3). The plain-text password is accepted
only as transient input here; it is never stored or returned, and only the
boolean result of the comparison leaves this module.

Verification uses the ``bcrypt`` library directly so the stored credential is
never readable plain text and so verification works against any standard
bcrypt hash (``$2a$``/``$2b$``/``$2y$``) regardless of which component produced
it. If the registration side introduces a shared ``app.services.password``
module exposing a ``verify_password`` function, this helper transparently
delegates to it so a single scheme is used across registration and sign-in;
otherwise it verifies locally.
"""

from __future__ import annotations

import bcrypt

# bcrypt only considers the first 72 bytes of a secret. Truncate consistently
# so verification agrees with any hashing side that follows the same rule.
_BCRYPT_MAX_BYTES = 72


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches the stored ``password_hash``.

    Args:
        password: The submitted plain-text credential value (transient input;
            never stored or returned).
        password_hash: The stored hashed credential to compare against.

    Returns:
        ``True`` when the password matches the hash, ``False`` otherwise. A
        missing, malformed, or non-string stored hash yields ``False`` rather
        than raising, so sign-in surfaces a uniform authentication failure
        without leaking internal detail (Requirement 7.4).
    """
    # Prefer a shared registration-owned helper when present so registration
    # and sign-in agree on a single scheme. Imported lazily to avoid a hard
    # dependency on a module another task may own.
    try:  # pragma: no cover - exercised only once the shared module exists
        from app.services.password import verify_password as shared_verify

        return bool(shared_verify(password, password_hash))
    except Exception:
        pass

    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    if not password_hash:
        return False

    secret = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(secret, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # An unrecognized/corrupt hash must not raise through to the client.
        return False
