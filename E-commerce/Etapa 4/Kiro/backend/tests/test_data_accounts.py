"""Unit tests for the account storage data-access layer.

These tests exercise ``app.data.accounts.AccountStore`` (in-process account
storage) and confirm that creating an account makes it readable, that reads
return the stored data, and that duplicate identifiers are rejected. Creating
a valid account and then reading it back is the data-layer behavior behind a
valid, conforming registration producing an account (Requirement 5.6).
"""

from __future__ import annotations

import pytest

from app.data.accounts import AccountStore
from app.models.customer import Customer


def make_store() -> AccountStore:
    """Return a fresh, empty in-process store for an isolated test."""
    store = AccountStore()
    store.clear()
    return store


def test_new_store_has_no_account() -> None:
    store = make_store()

    assert store.has_account("alice@example.com") is False
    assert store.get_by_identifier("alice@example.com") is None


def test_create_account_returns_stored_customer() -> None:
    store = make_store()

    customer = store.create_account("alice@example.com", "hashed-secret")

    assert isinstance(customer, Customer)
    assert customer.identifier == "alice@example.com"
    assert customer.password_hash == "hashed-secret"
    assert customer.id


def test_create_account_makes_it_readable() -> None:
    """Create-then-read: a created account is present and retrievable.

    This is the data-layer behavior behind a valid registration creating an
    account (Requirement 5.6).
    """
    store = make_store()

    created = store.create_account("bob@example.com", "hash-123")

    assert store.has_account("bob@example.com") is True

    read_back = store.get_by_identifier("bob@example.com")
    assert read_back is not None
    assert read_back.id == created.id
    assert read_back.identifier == "bob@example.com"
    assert read_back.password_hash == "hash-123"


def test_create_account_generates_unique_ids() -> None:
    store = make_store()

    first = store.create_account("one@example.com", "h1")
    second = store.create_account("two@example.com", "h2")

    assert first.id != second.id


def test_create_duplicate_identifier_raises() -> None:
    store = make_store()
    store.create_account("dup@example.com", "hash-a")

    with pytest.raises(ValueError):
        store.create_account("dup@example.com", "hash-b")


def test_duplicate_create_does_not_overwrite_existing_account() -> None:
    store = make_store()
    original = store.create_account("dup@example.com", "hash-a")

    with pytest.raises(ValueError):
        store.create_account("dup@example.com", "hash-b")

    stored = store.get_by_identifier("dup@example.com")
    assert stored is not None
    assert stored.id == original.id
    assert stored.password_hash == "hash-a"


def test_get_by_identifier_returns_copy_not_shared_reference() -> None:
    """Reads return copies, so stored account data cannot be mutated."""
    store = make_store()
    store.create_account("carol@example.com", "hash-c")

    read_one = store.get_by_identifier("carol@example.com")
    assert read_one is not None
    read_one.password_hash = "tampered"

    read_two = store.get_by_identifier("carol@example.com")
    assert read_two is not None
    assert read_two.password_hash == "hash-c"


def test_clear_removes_all_accounts() -> None:
    store = make_store()
    store.create_account("a@example.com", "ha")
    store.create_account("b@example.com", "hb")

    store.clear()

    assert store.has_account("a@example.com") is False
    assert store.has_account("b@example.com") is False
    assert store.get_by_identifier("a@example.com") is None
