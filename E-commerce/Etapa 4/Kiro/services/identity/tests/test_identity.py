"""Unit tests for the identity service (Stage 4 R7.1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, store
from contracts.tokens import verify_token


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    # Re-seed the moderator so moderator tests have the demo account.
    from app.service import seed_moderator

    seed_moderator(store)
    yield
    store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_register_success_returns_public_identity(client):
    resp = client.post(
        "/auth/register", json={"identifier": "alice", "password": "pw12345"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["identifier"] == "alice"
    assert "id" in body
    assert "password" not in body and "passwordHash" not in body


def test_register_validation_reports_empty_fields(client):
    resp = client.post("/auth/register", json={"identifier": "", "password": ""})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation_error"
    assert set(body["emptyFields"]) == {"identifier", "password"}


def test_register_duplicate_identifier_conflicts(client):
    client.post("/auth/register", json={"identifier": "bob", "password": "pw12345"})
    resp = client.post(
        "/auth/register", json={"identifier": "bob", "password": "pw12345"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "identifier_taken"


def test_login_success_issues_valid_token(client):
    client.post("/auth/register", json={"identifier": "carol", "password": "pw12345"})
    resp = client.post(
        "/auth/login", json={"identifier": "carol", "password": "pw12345"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    claims = verify_token(body["token"])
    assert claims is not None
    assert claims.identifier == "carol"
    assert claims.is_moderator is False
    assert "isModerator" not in body


def test_login_failure_is_uniform_401(client):
    resp = client.post(
        "/auth/login", json={"identifier": "ghost", "password": "nope123"}
    )
    assert resp.status_code == 401
    assert "incomplete or invalid" in resp.json()["error"]


def test_moderator_login_flags_role_in_token(client):
    resp = client.post(
        "/auth/login", json={"identifier": "moderator", "password": "moderator123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isModerator"] is True
    claims = verify_token(body["token"])
    assert claims is not None and claims.is_moderator is True


def test_internal_verify(client):
    client.post("/auth/register", json={"identifier": "dave", "password": "pw12345"})
    login = client.post(
        "/auth/login", json={"identifier": "dave", "password": "pw12345"}
    ).json()
    resp = client.get(
        "/internal/verify", headers={"Authorization": f"Bearer {login['token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "dave"
    bad = client.get("/internal/verify", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401
