"""Identity domain logic: registration, sign-in, and moderator seeding.

Ports the Stage 3 registration/sign-in rules onto the identity service's own
SQLite store, preserving the exact validation outcomes and the uniform
authentication-failure message. The moderator demonstration account
(``moderator`` / ``moderator123``) is seeded idempotently at startup.
"""

from __future__ import annotations

import uuid

from app.db import Account, AccountStore, hash_password, verify_password

REQUIRED_FIELDS = ("identifier", "password")
AUTH_FAILURE_MESSAGE = (
    "Sign-in failed: the provided sign-in information is incomplete or invalid."
)

MODERATOR_IDENTIFIER = "moderator"
MODERATOR_PASSWORD = "moderator123"


class RegistrationError(Exception):
    def __init__(
        self, empty_fields: list[str], non_conforming_fields: list[str], message: str
    ) -> None:
        super().__init__(message)
        self.empty_fields = empty_fields
        self.non_conforming_fields = non_conforming_fields
        self.message = message


class IdentifierTakenError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthenticationError(Exception):
    pass


def _classify(value: object) -> str:
    """Classify a submitted field as ``ok``, ``empty``, or ``non_conforming``."""
    if value is None:
        return "empty"
    if not isinstance(value, str):
        return "non_conforming"
    if value.strip() == "":
        return "empty"
    return "ok"


def register(
    identifier: object, password: object, *, store: AccountStore
) -> Account:
    """Validate and create a customer account (Stage 3 parity)."""
    empty: list[str] = []
    non_conforming: list[str] = []
    values = {"identifier": identifier, "password": password}
    for field in REQUIRED_FIELDS:
        verdict = _classify(values[field])
        if verdict == "empty":
            empty.append(field)
        elif verdict == "non_conforming":
            non_conforming.append(field)

    if empty or non_conforming:
        offending = empty + non_conforming
        raise RegistrationError(
            empty_fields=empty,
            non_conforming_fields=non_conforming,
            message=(
                "Registration could not be completed. Please correct the "
                "following field(s): " + ", ".join(offending) + "."
            ),
        )

    assert isinstance(identifier, str) and isinstance(password, str)
    if store.get_by_identifier(identifier) is not None:
        raise IdentifierTakenError(
            f"The identifier '{identifier}' is already taken."
        )
    return store.create_account(identifier, hash_password(password))


def sign_in(identifier: str, password: str, *, store: AccountStore) -> Account:
    """Validate credentials and return the authenticated account.

    Raises :class:`AuthenticationError` with the uniform failure message for
    incomplete input, an unknown identifier, or a wrong password alike.
    """
    if not isinstance(identifier, str) or identifier.strip() == "":
        raise AuthenticationError(AUTH_FAILURE_MESSAGE)
    if not isinstance(password, str) or password.strip() == "":
        raise AuthenticationError(AUTH_FAILURE_MESSAGE)

    account = store.get_by_identifier(identifier)
    if account is None or not verify_password(password, account.password_hash):
        raise AuthenticationError(AUTH_FAILURE_MESSAGE)
    return account


def seed_moderator(store: AccountStore) -> Account:
    """Ensure the demonstration moderator account exists (idempotent)."""
    existing = store.get_by_identifier(MODERATOR_IDENTIFIER)
    if existing is not None:
        return existing
    moderator = Account(
        id=str(uuid.uuid4()),
        identifier=MODERATOR_IDENTIFIER,
        password_hash=hash_password(MODERATOR_PASSWORD),
        is_moderator=True,
    )
    return store.add_account(moderator)
