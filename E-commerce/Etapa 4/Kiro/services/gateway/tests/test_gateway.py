"""Unit tests for the gateway (Stage 4 R7.1).

Upstream services are stubbed with an ``httpx.MockTransport`` so the gateway's
routing, session-cookie handling, token injection, and cache/no-store headers
are exercised without running the real services.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from contracts.tokens import issue_token, verify_token

import app.main as gw
from app.main import app, sessions

TOKEN = issue_token("cust-1", "alice", False)


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/auth/login"):
        return httpx.Response(
            200, json={"active": True, "customerId": "cust-1", "token": TOKEN}
        )
    if url.endswith("/auth/logout"):
        return httpx.Response(200, json={"active": False, "customerId": None})
    if url.endswith("/products"):
        return httpx.Response(200, json=[{"id": "p-001", "name": "Headphones"}])
    if url.endswith("/moderation/reviews"):
        # Echo back whether a bearer token reached the upstream.
        auth = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"authForwarded": auth})
    return httpx.Response(404, json={"error": "not_found"})


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    sessions.clear()
    gw.response_cache.clear()
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(gw, "_client", lambda: httpx.Client(transport=transport))
    yield
    sessions.clear()
    gw.response_cache.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_login_sets_cookie_and_hides_token(client):
    resp = client.post(
        "/auth/login", json={"identifier": "alice", "password": "pw12345"}
    )
    assert resp.status_code == 200
    body = resp.json()
    # The signed service token is never exposed to the browser.
    assert "token" not in body
    assert body["customerId"] == "cust-1"
    assert "stage4_session" in resp.cookies


def test_authenticated_request_forwards_bearer_token(client):
    client.post("/auth/login", json={"identifier": "alice", "password": "pw12345"})
    resp = client.get("/moderation/reviews")
    forwarded = resp.json()["authForwarded"]
    assert forwarded.startswith("Bearer ")
    # The forwarded token is the signed token, verifiable with the shared secret.
    claims = verify_token(forwarded.split(" ", 1)[1])
    assert claims is not None and claims.identifier == "alice"


def test_unauthenticated_request_forwards_no_token(client):
    resp = client.get("/moderation/reviews")
    assert resp.json()["authForwarded"] == ""


def test_catalog_is_cached_at_edge(client):
    first = client.get("/products")
    assert first.headers["X-Cache"] == "MISS"
    second = client.get("/products")
    assert second.headers["X-Cache"] == "HIT"


def test_logout_clears_cookie(client):
    client.post("/auth/login", json={"identifier": "alice", "password": "pw12345"})
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
    # Cookie is deleted (expired) on logout.
    assert resp.json() == {"active": False, "customerId": None}
