"""Backend structural smoke checks for task 14.4.

These assert the backend's technology, architecture, and scope boundaries
rather than feature behavior, backing the structural requirements:

* R14.2/R14.5 — the backend is a Python + FastAPI app that runs independently
  and responds over HTTP (imported standalone, hit with ``TestClient``).
* R14.3/R14.4 — it exposes exactly the six fixed endpoints over HTTP/JSON, the
  clear interface between presentation and server-side logic.
* R10.1/R10.2 and the non-persistence scope — no order storage exists and the
  checkout confirmation carries no order id and no creation timestamp.

They complement ``tests/test_smoke.py`` (which checks ``/health``) and
``tests/test_checkout_nonpersistence.py`` (which checks a single confirmation)
by asserting the app-wide route surface and the storage-layer boundary.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import data
from app.data import accounts, catalog
from app.main import app

client = TestClient(app)


# The exact (method, path) contract for the six fixed endpoints (R14.3).
EXPECTED_ENDPOINTS = {
    ("GET", "/products"),
    ("GET", "/products/{product_id}"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/logout"),
    ("POST", "/checkout/confirm"),
}

# Infrastructure routes FastAPI/the app add that are not part of the feature
# contract and are excluded from the six-endpoint comparison.
_INFRA_PATHS = {"/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def _feature_routes() -> set[tuple[str, str]]:
    """Collect (method, path) pairs for the app's non-infrastructure routes."""
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        if path in _INFRA_PATHS:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.add((method, path))
    return routes


def test_backend_runs_independently_over_http() -> None:
    """The FastAPI app imports standalone and answers an HTTP request (R14.2, R14.5)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_exposes_exactly_the_six_fixed_endpoints() -> None:
    """The route surface is exactly the six fixed HTTP/JSON endpoints (R14.3)."""
    assert _feature_routes() == EXPECTED_ENDPOINTS


def test_endpoints_exchange_json() -> None:
    """The six endpoints communicate over JSON (R14.3, R14.4)."""
    # A representative GET returns a JSON array of products.
    listing = client.get("/products")
    assert listing.status_code == 200
    assert listing.headers["content-type"].startswith("application/json")
    assert isinstance(listing.json(), list)

    # A representative POST accepts and returns JSON.
    confirm = client.post(
        "/checkout/confirm",
        json={"items": [{"productId": "p-001", "quantity": 1}]},
    )
    assert confirm.status_code == 200
    assert confirm.headers["content-type"].startswith("application/json")


def test_data_layer_stores_catalog_and_accounts_only_no_orders() -> None:
    """The data-access layer exposes catalog/account access and no order storage."""
    order_like = ("order", "purchase", "checkout")

    for module in (data, accounts, catalog):
        for attribute_name in dir(module):
            if attribute_name.startswith("_"):
                continue
            lowered = attribute_name.lower()
            assert not any(token in lowered for token in order_like), (
                f"{module.__name__} unexpectedly exposes order-like member "
                f"{attribute_name!r}; checkout must store no order record"
            )

    # The account store supports accounts only (no order-writing surface).
    store_members = {
        name.lower() for name in dir(accounts.account_store) if not name.startswith("_")
    }
    for forbidden in order_like:
        assert not any(forbidden in name for name in store_members)


def test_checkout_response_has_no_order_id_or_timestamp() -> None:
    """The confirmation is simulated and carries no order id/timestamp (R10.1)."""
    response = client.post(
        "/checkout/confirm",
        json={"items": [{"productId": "p-001", "quantity": 2}]},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["simulated"] is True
    # The response contract is exactly the non-persistent summary shape.
    assert set(body.keys()) == {"items", "total", "simulated"}

    forbidden_keys = {
        "orderId",
        "order_id",
        "id",
        "createdAt",
        "created_at",
        "timestamp",
        "orderNumber",
    }
    assert forbidden_keys.isdisjoint(body.keys())
    for line in body["items"]:
        assert forbidden_keys.isdisjoint(line.keys())
        assert set(line.keys()) == {
            "productId",
            "name",
            "unitPrice",
            "quantity",
            "lineTotal",
        }
