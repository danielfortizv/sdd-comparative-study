"""In-process account storage (data-access layer).

This module keeps account data in in-process storage for the running service
(Requirement 14.6). It supports reading and writing Customer accounts and
nothing else: it stores no order records, because checkout confirmation is
non-persistent (Requirements 6.9, 7.3, and the non-persistent checkout).

The password is never handled here as plain text. Callers pass an already
hashed credential (``password_hash``); this layer only stores and reads it.
Account identities are generated here so each stored account has a stable id.
"""

from __future__ import annotations

import uuid

from app.models.customer import Customer


class AccountStore:
    """In-process read/write store for Customer accounts.

    Accounts are indexed by their credential ``identifier`` so sign-in can look
    an account up by the value the person provides. The store holds no order
    records and no plain-text passwords.
    """

    def __init__(self) -> None:
        self._accounts_by_identifier: dict[str, Customer] = {}

    def has_account(self, identifier: str) -> bool:
        """Return whether an account with the given identifier exists."""
        return identifier in self._accounts_by_identifier

    def get_by_identifier(self, identifier: str) -> Customer | None:
        """Return the account for the given identifier, or ``None``.

        Returns a copy so stored account data cannot be mutated by callers.
        """
        account = self._accounts_by_identifier.get(identifier)
        return account.model_copy() if account is not None else None

    def get_by_id(self, customer_id: str) -> Customer | None:
        """Return the account with the given account id, or ``None``.

        Added additively for Stage 2 so a session's ``customer_id`` can be
        resolved to the account's non-sensitive identifier for review
        authorship. Returns a copy so stored data cannot be mutated.
        """
        for account in self._accounts_by_identifier.values():
            if account.id == customer_id:
                return account.model_copy()
        return None

    def create_account(self, identifier: str, password_hash: str) -> Customer:
        """Create and store a new account, returning the stored Customer.

        Args:
            identifier: The credential identifier for the new account.
            password_hash: The already-hashed credential to store. This layer
                never receives or stores a readable plain-text password.

        Raises:
            ValueError: If an account with this identifier already exists.
        """
        if identifier in self._accounts_by_identifier:
            raise ValueError(f"An account already exists for identifier: {identifier}")

        customer = Customer(
            id=str(uuid.uuid4()),
            identifier=identifier,
            password_hash=password_hash,
        )
        self._accounts_by_identifier[identifier] = customer
        return customer.model_copy()

    def add_customer(self, customer: Customer) -> Customer:
        """Store a pre-built ``Customer`` account, returning a stored copy.

        Added additively for Stage 2 so a fully-formed account (for example a
        seeded moderator with ``is_moderator=True``) can be stored without the
        ``create_account`` helper's identity generation. Mirrors the copy-on-
        write behavior of the rest of this store.

        Raises:
            ValueError: If an account with this identifier already exists.
        """
        if customer.identifier in self._accounts_by_identifier:
            raise ValueError(
                f"An account already exists for identifier: {customer.identifier}"
            )
        self._accounts_by_identifier[customer.identifier] = customer.model_copy()
        return customer.model_copy()

    def clear(self) -> None:
        """Remove all stored accounts.

        Provided so tests can start from a known-empty in-process store.
        """
        self._accounts_by_identifier.clear()


# Shared in-process account store for the running service. Account data lives
# only for the lifetime of the process; nothing is persisted durably.
account_store = AccountStore()
