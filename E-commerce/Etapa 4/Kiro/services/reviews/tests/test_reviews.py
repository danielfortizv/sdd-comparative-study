"""Unit tests for the reviews service (Stage 4 R7.1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contracts.tokens import issue_token

from app import service
from app.main import app, store


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    store.clear()
    # Products are owned by commerce; stub existence so submission logic can run
    # without a live commerce service (the real check is covered by E2E).
    monkeypatch.setattr(service, "_product_exists", lambda product_id: True)
    yield
    store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _customer_header(identifier="alice"):
    token = issue_token("cust-" + identifier, identifier, False)
    return {"Authorization": f"Bearer {token}"}


def _moderator_header():
    token = issue_token("mod-1", "moderator", True)
    return {"Authorization": f"Bearer {token}"}


def test_submit_requires_customer_session(client):
    resp = client.post("/products/p-001/reviews", json={"rating": 5, "text": "ok"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "authentication_required"


def test_submit_creates_pending_review(client):
    resp = client.post(
        "/products/p-001/reviews",
        json={"rating": 5, "text": "Great product"},
        headers=_customer_header(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["moderationState"] == "pending"
    assert body["authorIdentity"] == "alice"


def test_submit_validation_reports_offending_fields(client):
    resp = client.post(
        "/products/p-001/reviews",
        json={"rating": 9, "text": ""},
        headers=_customer_header(),
    )
    assert resp.status_code == 422
    assert set(resp.json()["offendingFields"]) >= {"rating", "text"}


def test_duplicate_review_conflict(client):
    client.post(
        "/products/p-001/reviews",
        json={"rating": 4, "text": "first"},
        headers=_customer_header(),
    )
    resp = client.post(
        "/products/p-001/reviews",
        json={"rating": 3, "text": "second"},
        headers=_customer_header(),
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "duplicate_review"


def test_moderation_requires_moderator(client):
    resp = client.get("/moderation/reviews", headers=_customer_header())
    assert resp.status_code == 403
    assert resp.json()["error"] == "moderator_required"


def test_approve_writes_outbox_and_is_terminal(client):
    created = client.post(
        "/products/p-002/reviews",
        json={"rating": 5, "text": "Nice"},
        headers=_customer_header("bob"),
    ).json()
    review_id = created["id"]

    approve = client.post(
        f"/moderation/reviews/{review_id}/approve", headers=_moderator_header()
    )
    assert approve.status_code == 200
    assert approve.json()["moderationState"] == "approved"

    # An outbox row was written transactionally with the decision.
    assert len(store.unsent_outbox()) == 1

    # Second decision is rejected as already decided (terminal).
    again = client.post(
        f"/moderation/reviews/{review_id}/reject", headers=_moderator_header()
    )
    assert again.status_code == 409
    assert again.json()["error"] == "already_decided"


def test_approve_unknown_review_conflict(client):
    resp = client.post(
        "/moderation/reviews/does-not-exist/approve", headers=_moderator_header()
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "review_not_found"


def test_own_review_only_for_matching_caller(client):
    created = client.post(
        "/products/p-003/reviews",
        json={"rating": 2, "text": "meh"},
        headers=_customer_header("carol"),
    ).json()
    # Matching caller sees their own pending review.
    mine = client.get(
        "/internal/own-review",
        params={"productId": "p-003", "author": "carol"},
        headers=_customer_header("carol"),
    )
    assert mine.json()["id"] == created["id"]
    # A different caller cannot read it.
    other = client.get(
        "/internal/own-review",
        params={"productId": "p-003", "author": "carol"},
        headers=_customer_header("mallory"),
    )
    assert other.json() is None
