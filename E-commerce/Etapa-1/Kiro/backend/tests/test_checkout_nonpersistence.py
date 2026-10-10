"""Unit tests for checkout non-persistence and the empty-cart guard (task 5.3).

The fictitious-payment NOTICE text itself (R10.1) is rendered on the frontend;
on the backend side these tests verify the non-persistence aspects that back
that behavior:

* The ``POST /checkout/confirm`` response carries no order identity and no
  creation timestamp (no ``orderId``/``id``/``createdAt``/``timestamp`` keys)
  and is marked ``simulated: true`` (R10.1).
* No order record is stored: the data-access layer exposes no order-storage
  API and confirming a purchase leaves the account store unchanged (R10.1,
  with the non-persistent checkout design).
* An empty submission is rejected by the server-side empty-cart guard with a
  ``400`` and the ``empty_cart`` code (R9.5).

The checkout router is mounted on a standalone FastAPI app so these tests are
independent of other feature routers wired into ``app.main`` by concurrent
tasks.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import data
from app.api import checkout
from app.data import accounts, catalog


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(checkout.router)
    return TestClient(app)


# Keys that would indicate a persisted order identity or creation time. The
# non-persistent confirmation must contain none of these (R10.1).
_FORBIDDEN_KEYS = {
    "orderId",
    "order_id",
    "id",
    "createdAt",
    "created_at",
    "timestamp",
    "createdOn",
    "created_on",
    "orderNumber",
    "order_number",
}


def test_confirmation_response_has_no_order_id_or_timestamp() -> None:
    """The confirmation body is marked simulated and carries no order id/time."""
    client = _client()

    response = client.post(
        "/checkout/confirm",
        json={"items": [{"productId": "p-001", "quantity": 1}]},
    )

    assert response.status_code == 200
    body = response.json()

    # The purchase is explicitly fictitious (R10.1).
    assert body["simulated"] is True

    # No order identity and no creation timestamp at the top level (R10.1).
    for key in _FORBIDDEN_KEYS:
        assert key not in body, f"confirmation unexpectedly contains top-level key {key!r}"

    # The confirmation exposes only the summary contract: items, total, flag.
    assert set(body.keys()) == {"items", "total", "simulated"}

    # Per-line summaries also carry no order identity or timestamp (R10.1).
    for line in body["items"]:
        for key in _FORBIDDEN_KEYS - {"id"}:
            # ``id`` is excluded here only because a line never has one either;
            # assert it explicitly below for clarity.
            assert key not in line, f"line unexpectedly contains key {key!r}"
        assert "orderId" not in line and "id" not in line
        assert "createdAt" not in line and "timestamp" not in line
        assert set(line.keys()) == {
            "productId",
            "name",
            "unitPrice",
            "quantity",
            "lineTotal",
        }


def test_data_layer_exposes_no_order_storage_api() -> None:
    """No order record is stored: the data layer offers no order-storage API."""
    # The data package and its modules expose catalog and account access only;
    # nothing order-shaped exists to persist a purchase (R10.1).
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

    # The account store supports accounts only; it has no order-writing method.
    store = accounts.account_store
    store_members = {name.lower() for name in dir(store) if not name.startswith("_")}
    for forbidden in ("order", "purchase", "checkout"):
        assert not any(forbidden in name for name in store_members), (
            f"account store unexpectedly exposes an order-like member containing "
            f"{forbidden!r}"
        )


def test_confirming_a_purchase_stores_no_order_record() -> None:
    """Confirming a simulated purchase leaves the account store unchanged (R10.1)."""
    store = accounts.account_store
    store.clear()
    # Seed one account so we can detect any unexpected write during checkout.
    store.create_account(identifier="buyer@example.com", password_hash="hashed")
    accounts_before = {
        store.has_account("buyer@example.com"),
    }

    client = _client()
    response = client.post(
        "/checkout/confirm",
        json={
            "items": [
                {"productId": "p-001", "quantity": 2},
                {"productId": "p-003", "quantity": 1},
            ]
        },
    )
    assert response.status_code == 200

    # The only stored state (accounts) is unchanged: no order record was added,
    # and the single seeded account is still the only thing present (R10.1).
    assert store.has_account("buyer@example.com")
    assert accounts_before == {True}
    # A fresh, unrelated identifier is still absent — checkout wrote nothing.
    assert store.has_account("someone-else@example.com") is False

    store.clear()


def test_empty_submission_is_rejected() -> None:
    """An empty cart submission is rejected by the server-side guard (R9.5)."""
    client = _client()

    response = client.post("/checkout/confirm", json={"items": []})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_cart"
