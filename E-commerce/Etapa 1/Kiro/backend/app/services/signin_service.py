"""Sign-in / sign-out service (authentication business logic).

This service validates sign-in input, verifies the submitted credential
against the stored ``passwordHash``, and establishes or ends an in-process
``Session`` for the running service. It implements:

- Sign-in that accepts an ``identifier`` and ``password``, establishes an
  active ``Session`` on complete, valid input (Requirements 6.1, 6.9), and
  raises a uniform authentication failure on incomplete/invalid input without
  exposing internal detail, hashes, or submitted credential values
  (Requirements 6.3, 7.4).
- Sign-out that ends the active ``Session`` (Requirement 6.6).

The ``password`` is accepted only as transient input; it is never stored on
the session and never returned (Requirements 7.2, 7.3). The session itself
holds only ``active`` and ``customerId`` (no credential value).

Session state is kept as simple module-level state representing the single
active session of the running demonstration service, consistent with the
``Session`` model.
"""

from __future__ import annotations

from app.data.accounts import AccountStore, account_store
from app.models.session import Session
from app.services.password_verify import verify_password


class AuthenticationError(Exception):
    """Raised when sign-in input is incomplete or invalid.

    The message indicates the authentication failure without revealing
    internal system details, password hashes, or submitted credential values
    (Requirements 6.3, 7.4).
    """


# A single, generic failure message. It is deliberately uniform for every
# incomplete or invalid sign-in so the response never reveals whether the
# identifier exists or why verification failed (Requirements 6.3, 7.4).
AUTH_FAILURE_MESSAGE = "Sign-in failed: the provided sign-in information is incomplete or invalid."


# Module-level representation of the running service's single active session.
# Starts inactive (no Session). This mirrors the Session model's shape.
_current_session: Session = Session(active=False, customer_id=None)


def _is_blank(value: object) -> bool:
    """Return whether a credential input is missing or effectively empty."""
    return not isinstance(value, str) or value.strip() == ""


def sign_in(
    identifier: str,
    password: str,
    *,
    store: AccountStore | None = None,
) -> Session:
    """Validate credentials and establish an active ``Session``.

    Args:
        identifier: The submitted credential identifier.
        password: The submitted plain-text credential value (transient input;
            never stored or returned).
        store: Account store to look the account up in. Defaults to the shared
            in-process ``account_store``; injectable for tests.

    Returns:
        The active ``Session`` for the identified Customer. The returned
        session carries no password or credential value.

    Raises:
        AuthenticationError: If the input is incomplete (missing identifier or
            password) or invalid (unknown identifier or wrong password). The
            error carries only a uniform failure message.
    """
    account_lookup = store if store is not None else account_store

    # Reject incomplete input before any lookup (Requirement 6.3).
    if _is_blank(identifier) or _is_blank(password):
        raise AuthenticationError(AUTH_FAILURE_MESSAGE)

    account = account_lookup.get_by_identifier(identifier)

    # Unknown identifier or non-matching password both yield the same uniform
    # failure, so the response never distinguishes the two cases (R6.3, R7.4).
    if account is None or not verify_password(password, account.password_hash):
        raise AuthenticationError(AUTH_FAILURE_MESSAGE)

    global _current_session
    _current_session = Session(active=True, customer_id=account.id)
    # Return a copy so callers cannot mutate the stored session state.
    return _current_session.model_copy()


def sign_out() -> Session:
    """End the active ``Session``, returning the resulting inactive session.

    Signing out always results in a state in which no Session is active
    (Requirement 6.6), whether or not a Session was active beforehand.
    """
    global _current_session
    _current_session = Session(active=False, customer_id=None)
    return _current_session.model_copy()


def get_current_session() -> Session:
    """Return a copy of the current in-process session state."""
    return _current_session.model_copy()


def reset_session() -> None:
    """Reset session state to inactive. Provided so tests start from a known state."""
    global _current_session
    _current_session = Session(active=False, customer_id=None)
