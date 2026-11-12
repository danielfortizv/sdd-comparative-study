"""Registration service (service layer).

Implements account registration for the credential contract: an ``identifier``
and a ``password`` (Requirement 5.1). The service validates that every required
item is present and conforms to its expected format; on success it creates a
``Customer`` account, storing the password only as ``passwordHash`` and never
returning it (Requirements 5.6, 7.3).

On failure it raises a structured error that names the exact set of offending
items — each empty required item (Requirement 5.3) and each non-conforming item
(Requirement 5.4) — and that never echoes the submitted credential values
(Requirement 5.5). An already-taken identifier is reported as a conflict
without exposing internal detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.data.accounts import AccountStore, account_store
from app.models.customer import Customer

# The required items of the credential contract. The contract is intentionally
# the minimum (identifier + password); no additional fields are invented
# (Requirement 5.1 and the design's Customer model).
REQUIRED_FIELDS: tuple[str, ...] = ("identifier", "password")


@dataclass
class RegistrationError(Exception):
    """Structured registration failure that identifies offending items.

    The error carries machine-usable sets of offending field names so the API
    layer can build a safe JSON error. It never carries any submitted
    credential value, so error output cannot echo credentials (Requirement
    5.5).

    Attributes:
        empty_fields: Required items that were missing or empty (R5.3).
        non_conforming_fields: Items present but not conforming to their
            expected format (R5.4).
        message: A short, safe summary that contains no credential values.
    """

    empty_fields: list[str] = field(default_factory=list)
    non_conforming_fields: list[str] = field(default_factory=list)
    message: str = "Registration input is invalid."

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass
class IdentifierTakenError(Exception):
    """An account already exists for the submitted identifier.

    Reported without echoing the submitted identifier value or any other
    credential value (Requirements 5.5, 7.4).
    """

    message: str = "An account with the provided identifier already exists."

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def _is_present_and_conforming(value: object) -> tuple[bool, bool]:
    """Classify a single submitted item.

    Returns ``(is_empty, is_non_conforming)``:
        - ``is_empty`` is True when the item is missing or, after trimming
          surrounding whitespace, has no characters (Requirement 5.3).
        - ``is_non_conforming`` is True when the item is present and non-empty
          but does not conform to its expected format: for this credential
          contract the expected format is a text value, so a non-string
          present value is non-conforming (Requirement 5.4).

    An item is never reported as both empty and non-conforming.
    """
    if value is None:
        return True, False
    if isinstance(value, str):
        # Empty or whitespace-only text is treated as an empty required item.
        if value.strip() == "":
            return True, False
        # A non-empty text value conforms to the expected text format.
        return False, False
    # Present but not text: it does not conform to the expected format.
    return False, True


def register(
    identifier: object,
    password: object,
    store: AccountStore | None = None,
) -> Customer:
    """Register a new ``Customer`` account from registration input.

    Args:
        identifier: The submitted credential identifier.
        password: The submitted plain-text password (used only to compute the
            stored hash; never retained or returned).
        store: Account store to use; defaults to the shared in-process store.

    Returns:
        The created ``Customer``. Its ``password_hash`` is a one-way hash, and
        no readable plain-text password is present on it (Requirement 7.3).

    Raises:
        RegistrationError: If any required item is empty or any item does not
            conform to its expected format. The error names the exact offending
            items and contains no submitted credential values (R5.3, R5.4,
            R5.5).
        IdentifierTakenError: If an account already exists for the identifier.
    """
    active_store = store if store is not None else account_store

    submitted: dict[str, object] = {
        "identifier": identifier,
        "password": password,
    }

    empty_fields: list[str] = []
    non_conforming_fields: list[str] = []
    for name in REQUIRED_FIELDS:
        is_empty, is_non_conforming = _is_present_and_conforming(submitted[name])
        if is_empty:
            empty_fields.append(name)
        elif is_non_conforming:
            non_conforming_fields.append(name)

    if empty_fields or non_conforming_fields:
        # Build a safe message that lists only field names, never values.
        parts: list[str] = []
        if empty_fields:
            parts.append(
                "Required field(s) missing: " + ", ".join(empty_fields)
            )
        if non_conforming_fields:
            parts.append(
                "Field(s) with invalid format: "
                + ", ".join(non_conforming_fields)
            )
        raise RegistrationError(
            empty_fields=empty_fields,
            non_conforming_fields=non_conforming_fields,
            message="; ".join(parts) + ".",
        )

    # Both items are present and conforming: safe to narrow to text.
    assert isinstance(identifier, str)
    assert isinstance(password, str)

    if active_store.has_account(identifier):
        raise IdentifierTakenError()

    # Lazy import keeps the hashing dependency out of the import path for
    # callers (such as validation-only tests) that never create an account.
    from app.services.password import hash_password

    password_hash = hash_password(password)
    return active_store.create_account(identifier, password_hash)
