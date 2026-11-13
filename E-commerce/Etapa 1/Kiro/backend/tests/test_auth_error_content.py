"""Unit tests for authentication error message content (Task 4.10).

These example-based tests verify Requirement 7.4: an authentication error
response indicates the authentication failure without revealing unnecessary
internal system details. Concretely, for a wrong password, an unknown
identifier, and incomplete input, the ``POST /auth/login`` 401 response:

  (a) indicates failure (status 401 with a non-empty ``error`` message),
  (b) does NOT contain the submitted password,
  (c) does NOT contain the stored ``passwordHash``,
  (d) contains no stack trace / internal detail (e.g. no "Traceback").

A single uniform failure message is also asserted so the response never
distinguishes "unknown identifier" from "wrong password" (Requirements 6.3,
7.4). State is reset between tests so each case starts from a known store and
an inactive session.

_Requirements: 7.4_
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data.accounts import account_store
from app.main import app
from app.services.password import hash_password
from app.services.signin_service import AUTH_FAILURE_MESSAGE, reset_session

client = TestClient(app)

# A representative account whose credential value and stored hash must never
# surface in any authentication error response.
_IDENTIFIER = "alice"
_PASSWORD = "s3cret-demo-pass"

# Tokens that indicate internal implementation detail leaking into a response.
_INTERNAL_DETAIL_MARKERS = (
    "Traceback",
    "File \"",
    "line ",
    "bcrypt",
    "hashlib",
    "signin_service",
    "Exception",
)


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    """Start each test from an empty store and an inactive session."""
    account_store.clear()
    reset_session()
    yield
    account_store.clear()
    reset_session()


def _seed_account() -> str:
    """Create a stored account with a real hashed credential; return its hash."""
    password_hash = hash_password(_PASSWORD)
    account_store.create_account(_IDENTIFIER, password_hash)
    return password_hash


def _assert_safe_auth_error(response, *, submitted_password: str, stored_hash: str | None) -> None:
    """Assert a login response is a safe authentication failure (R7.4).

    Checks the four content guarantees: indicates failure, excludes the
    submitted password, excludes the stored hash, and exposes no internal
    detail or stack trace.
    """
    # (a) Indicates failure: 401 with a non-empty error message.
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    message = body["error"]
    assert isinstance(message, str)
    assert message.strip() != ""
    # The uniform message plainly indicates an authentication failure.
    assert "fail" in message.lower() or "invalid" in message.lower()

    raw = response.text

    # (b) Must not contain the submitted password anywhere in the response.
    assert submitted_password not in raw

    # (c) Must not contain the stored passwordHash.
    if stored_hash is not None:
        assert stored_hash not in raw

    # (d) Must not leak a stack trace or other internal implementation detail.
    for marker in _INTERNAL_DETAIL_MARKERS:
        assert marker not in raw


def test_wrong_password_error_hides_internal_detail_and_values() -> None:
    stored_hash = _seed_account()

    response = client.post(
        "/auth/login",
        json={"identifier": _IDENTIFIER, "password": "totally-wrong-pass"},
    )

    _assert_safe_auth_error(
        response, submitted_password="totally-wrong-pass", stored_hash=stored_hash
    )


def test_unknown_identifier_error_hides_internal_detail_and_values() -> None:
    # No account seeded: the identifier does not exist in the store.
    response = client.post(
        "/auth/login",
        json={"identifier": "nobody-here", "password": "any-password-value"},
    )

    _assert_safe_auth_error(
        response, submitted_password="any-password-value", stored_hash=None
    )


@pytest.mark.parametrize(
    ("payload", "submitted_password"),
    [
        ({"identifier": _IDENTIFIER}, None),
        ({"password": "lonely-pass"}, "lonely-pass"),
        ({"identifier": "", "password": ""}, None),
        ({"identifier": _IDENTIFIER, "password": ""}, None),
        ({}, None),
    ],
)
def test_incomplete_input_error_hides_internal_detail_and_values(
    payload: dict[str, str], submitted_password: str | None
) -> None:
    stored_hash = _seed_account()

    response = client.post("/auth/login", json=payload)

    _assert_safe_auth_error(
        response,
        submitted_password=submitted_password if submitted_password else _PASSWORD,
        stored_hash=stored_hash,
    )
    # When a password value was submitted, it must not be echoed either.
    if submitted_password:
        assert submitted_password not in response.text


def test_authentication_error_message_is_uniform_across_failure_modes() -> None:
    """Wrong password and unknown identifier yield the same uniform message.

    A uniform message is what keeps the response from revealing which part of
    the credential was wrong, i.e. no unnecessary internal detail (R7.4).
    """
    _seed_account()

    wrong_password = client.post(
        "/auth/login", json={"identifier": _IDENTIFIER, "password": "nope-nope"}
    )
    unknown_identifier = client.post(
        "/auth/login", json={"identifier": "ghost", "password": "nope-nope"}
    )

    assert wrong_password.json()["error"] == AUTH_FAILURE_MESSAGE
    assert unknown_identifier.json()["error"] == AUTH_FAILURE_MESSAGE
