"""Tests for the catalog cache middleware (Stage 3, Task 4).

Verifies the middleware's visible contract through FastAPI's ``TestClient``:

- Catalog reads report ``X-Cache: MISS`` then ``HIT`` and carry a public
  ``Cache-Control`` (Requirements 5.1, 5.2).
- Session-varying (``/products/{id}/reviews``) and moderation responses are
  marked ``no-store`` and are never served from the shared cache
  (Requirement 5.4).
- Error responses (404) are not cached (design: Error Handling).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.response_cache import response_cache

client = TestClient(app)


def setup_function() -> None:
    """Start each test from an empty cache for deterministic HIT/MISS."""
    response_cache.clear()


def test_products_list_reports_miss_then_hit() -> None:
    first = client.get("/products")
    assert first.status_code == 200
    assert first.headers.get("X-Cache") == "MISS"
    assert "max-age=" in first.headers.get("Cache-Control", "")

    second = client.get("/products")
    assert second.status_code == 200
    assert second.headers.get("X-Cache") == "HIT"
    # The cached body is byte-for-byte identical to the fresh one.
    assert second.json() == first.json()


def test_product_detail_is_cached() -> None:
    first = client.get("/products/p-001")
    assert first.status_code == 200
    assert first.headers.get("X-Cache") == "MISS"

    second = client.get("/products/p-001")
    assert second.headers.get("X-Cache") == "HIT"
    assert second.json()["id"] == "p-001"


def test_unknown_product_404_is_not_cached() -> None:
    first = client.get("/products/missing")
    assert first.status_code == 404
    # A non-200 is never stored, so it carries no HIT on repeat.
    second = client.get("/products/missing")
    assert second.status_code == 404
    assert second.headers.get("X-Cache") != "HIT"


def test_reviews_endpoint_is_not_shared_cached() -> None:
    # The review listing varies by session (ownReview); it must be no-store
    # and must never report a cache HIT.
    response = client.get("/products/p-001/reviews")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("X-Cache") != "HIT"


def test_moderation_queue_is_no_store() -> None:
    # Without a moderator session this is denied, but the response must still
    # carry no-store so no intermediary caches per-user/authenticated data.
    response = client.get("/moderation/reviews")
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("X-Cache") != "HIT"
