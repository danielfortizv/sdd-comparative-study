"""Unit tests for the commerce service (Stage 4 R7.1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contracts.envelope import EventEnvelope
from contracts.events import (
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    ReviewProjectionData,
    ReviewRejectedData,
)

from app import cache
from app.db import ProjectionStore
from app.main import app, store
from app.projection import apply_event


@pytest.fixture(autouse=True)
def _clean():
    store.clear()
    cache.response_cache.clear()
    yield
    store.clear()
    cache.response_cache.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_products_listing_is_cacheable(client):
    first = client.get("/products")
    assert first.status_code == 200
    assert first.headers["X-Cache"] == "MISS"
    assert "public" in first.headers["Cache-Control"]
    second = client.get("/products")
    assert second.headers["X-Cache"] == "HIT"
    assert len(first.json()) == 6


def test_unknown_product_404(client):
    resp = client.get("/products/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "product_not_found"


def test_checkout_confirmation(client):
    resp = client.post(
        "/checkout/confirm",
        json={"items": [{"productId": "p-001", "quantity": 2}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["simulated"] is True
    assert body["total"] == round(79.99 * 2, 2)
    assert body["items"][0]["lineTotal"] == round(79.99 * 2, 2)


def test_checkout_empty_cart(client):
    resp = client.post("/checkout/confirm", json={"items": []})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "empty_cart"


def _approved_envelope(review_id="r1", product_id="p-002", event_id=None):
    data = ReviewProjectionData(
        review_id=review_id,
        product_id=product_id,
        author_identity="alice",
        rating=5,
        text="Great",
    ).model_dump(by_alias=True)
    return EventEnvelope.build(REVIEW_APPROVED, data, event_id=event_id)


def test_projection_apply_approved_then_public(client):
    direct = ProjectionStore()  # same temp DB via env
    changed = apply_event(_approved_envelope(), direct)
    assert changed is True
    resp = client.get("/products/p-002/reviews")
    body = resp.json()
    assert resp.headers["Cache-Control"] == "no-store"
    assert body["summary"]["count"] == 1
    assert body["summary"]["average"] == 5.0
    assert body["reviews"][0]["text"] == "Great"


def test_duplicate_event_is_idempotent():
    direct = ProjectionStore()
    env = _approved_envelope(event_id="dup-1")
    assert apply_event(env, direct) is True
    # Same event id delivered again: no additional effect.
    assert apply_event(env, direct) is False
    assert len(direct.list_by_product("p-002")) == 1


def test_rejected_event_removes_from_projection():
    direct = ProjectionStore()
    apply_event(_approved_envelope(review_id="r9", event_id="a9"), direct)
    assert len(direct.list_by_product("p-002")) == 1
    rejected = EventEnvelope.build(
        REVIEW_REJECTED,
        ReviewRejectedData(review_id="r9", product_id="p-002").model_dump(
            by_alias=True
        ),
    )
    assert apply_event(rejected, direct) is True
    assert direct.list_by_product("p-002") == []


def test_projection_change_invalidates_cache(client):
    # Prime the catalog cache.
    client.get("/products")
    direct = ProjectionStore()
    before = cache.response_cache.get("GET /products")
    assert before is not None
    apply_event(_approved_envelope(event_id="inv-1"), direct)
    assert cache.response_cache.get("GET /products") is None
