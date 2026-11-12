"""Verification tests for registration (service + POST /auth/register).

These example tests confirm the registration behavior required by Task 4.1:
all required items validated for presence and format, the exact set of
offending items reported, submitted credential values never echoed, and the
password stored only as a hash and never returned (Requirements 5.1, 5.3, 5.4,
5.5, 5.6, 7.3). Dedicated property-based tests are separate tasks.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data.accounts import AccountStore, account_store
from app.main import app
from app.services.registration_service import (
    IdentifierTakenError,
    RegistrationError,
    register,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_store() -> None:
    """Start every test from an empty in-process account store."""
    account_store.clear()
    yield
    account_store.clear()


def test_valid_registration_creates_account_and_hides_password() -> None:
    store = AccountStore()

    customer = register("alice", "s3cret-pass", store=store)

    # Account created and retrievable (R5.6).
    assert store.has_account("alice")
    # Password is stored only as a hash, never as readable plain text (R7.3).
    assert customer.password_hash != "s3cret-pass"
    assert "s3cret-pass" not in customer.password_hash


def test_empty_required_items_reported_exactly() -> None:
    with pytest.raises(RegistrationError) as excinfo:
        register("", "", store=AccountStore())

    error = excinfo.value
    assert set(error.empty_fields) == {"identifier", "password"}
    assert error.non_conforming_fields == []


def test_non_conforming_item_reported_separately() -> None:
    # A present but non-text password does not conform to the expected format.
    with pytest.raises(RegistrationError) as excinfo:
        register("alice", 12345, store=AccountStore())

    error = excinfo.value
    assert error.empty_fields == []
    assert error.non_conforming_fields == ["password"]


def test_duplicate_identifier_rejected() -> None:
    store = AccountStore()
    register("alice", "pw-one", store=store)

    with pytest.raises(IdentifierTakenError):
        register("alice", "pw-two", store=store)


def test_endpoint_success_returns_identity_without_credentials() -> None:
    response = client.post(
        "/auth/register",
        json={"identifier": "bob", "password": "top-secret-9"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["identifier"] == "bob"
    assert "id" in body
    # No password or hash is ever returned (R7.2, R7.3).
    assert "password" not in body
    assert "passwordHash" not in body
    assert "top-secret-9" not in response.text


def test_endpoint_validation_error_names_fields_without_echoing_values() -> None:
    response = client.post(
        "/auth/register",
        json={"identifier": "", "password": "   "},
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body["emptyFields"]) == {"identifier", "password"}
    # The submitted password value is never echoed back (R5.5).
    assert "   " not in body["message"]


def test_endpoint_duplicate_identifier_conflict() -> None:
    first = client.post(
        "/auth/register",
        json={"identifier": "carol", "password": "pw-one"},
    )
    assert first.status_code == 201

    second = client.post(
        "/auth/register",
        json={"identifier": "carol", "password": "pw-two"},
    )
    assert second.status_code == 409
    # No submitted credential value appears in the conflict message (R5.5).
    assert "pw-two" not in second.text
