"""Verification tests for sign-in/sign-out service and endpoints.

Covers the Task 4.6 behavior:
- POST /auth/login establishes an active Session on complete, valid input and
  never returns the password (Requirements 6.1, 6.9, 7.2).
- POST /auth/login returns a uniform authentication error without internal
  detail, hashes, or submitted credential values on invalid/incomplete input
  (Requirements 6.3, 7.4).
- POST /auth/logout ends the active Session (Requirement 6.6).

Full property tests are separate tasks (4.7-4.10); these are minimal examples.
"""

from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.data.accounts import account_store
from app.main import app
from app.services.signin_service import (
    AuthenticationError,
    reset_session,
    sign_in,
    sign_out,
)

client = TestClient(app)


def _hash(password: str) -> str:
    """Produce a standard bcrypt hash for seeding stored accounts in tests."""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    """Start each test from an empty store and an inactive session."""
    account_store.clear()
    reset_session()
    yield
    account_store.clear()
    reset_session()


def _seed_account(identifier: str, password: str) -> str:
    """Create a stored account with a hashed credential; return its id."""
    account = account_store.create_account(identifier, _hash(password))
    return account.id


# --- Service-level behavior -------------------------------------------------


def test_sign_in_valid_input_establishes_active_session() -> None:
    customer_id = _seed_account("alice", "s3cret-pass")

    session = sign_in("alice", "s3cret-pass")

    assert session.active is True
    assert session.customer_id == customer_id


def test_sign_in_wrong_password_raises_authentication_error() -> None:
    _seed_account("alice", "s3cret-pass")

    with pytest.raises(AuthenticationError):
        sign_in("alice", "wrong-password")


def test_sign_in_unknown_identifier_raises_authentication_error() -> None:
    with pytest.raises(AuthenticationError):
        sign_in("nobody", "whatever")


@pytest.mark.parametrize(
    ("identifier", "password"),
    [("", "pass"), ("alice", ""), ("", ""), ("   ", "pass")],
)
def test_sign_in_incomplete_input_raises_authentication_error(
    identifier: str, password: str
) -> None:
    with pytest.raises(AuthenticationError):
        sign_in(identifier, password)


def test_sign_out_ends_active_session() -> None:
    _seed_account("alice", "s3cret-pass")
    sign_in("alice", "s3cret-pass")

    session = sign_out()

    assert session.active is False
    assert session.customer_id is None


# --- HTTP endpoint behavior -------------------------------------------------


def test_login_endpoint_returns_session_without_password() -> None:
    customer_id = _seed_account("bob", "hunter2-demo")

    response = client.post(
        "/auth/login", json={"identifier": "bob", "password": "hunter2-demo"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"active": True, "customerId": customer_id}
    # The submitted password must never appear anywhere in the response.
    assert "hunter2-demo" not in response.text
    assert "password" not in body


def test_login_endpoint_invalid_credentials_returns_safe_error() -> None:
    _seed_account("bob", "hunter2-demo")

    response = client.post(
        "/auth/login", json={"identifier": "bob", "password": "nope"}
    )

    assert response.status_code == 401
    body = response.json()
    # Error indicates failure but leaks no submitted value or stored hash.
    assert "error" in body
    assert "nope" not in response.text
    assert "hunter2-demo" not in response.text


def test_login_endpoint_incomplete_input_returns_safe_error() -> None:
    response = client.post("/auth/login", json={"identifier": "bob"})

    assert response.status_code == 401
    assert "error" in response.json()


def test_logout_endpoint_ends_session() -> None:
    _seed_account("bob", "hunter2-demo")
    client.post("/auth/login", json={"identifier": "bob", "password": "hunter2-demo"})

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"active": False, "customerId": None}
