"""Minimal verification tests for the checkout confirmation (task 5.1).

These confirm the non-persistent simulated-purchase confirmation behaves as the
design requires (Requirements 10.1, 10.2, 9.5): the summary and total are built
from the submitted cart and catalog data, the response is marked simulated and
carries no order ID or creation timestamp, and an empty submission is rejected
by the server-side empty-cart guard. Full property/unit coverage lives in
separate tasks; this is a focused smoke check.

The checkout router is mounted on a standalone app so the test is independent
of other feature routers that are wired into ``app.main`` by concurrent tasks.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import checkout
from app.data import catalog


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(checkout.router)
    return TestClient(app)


def test_confirm_builds_summary_and_total_from_catalog() -> None:
    client = _client()
    headphones = catalog.get_product("p-001")
    hub = catalog.get_product("p-003")
    assert headphones is not None and hub is not None

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
    body = response.json()

    # Simulated flag present; no order identity or timestamp returned (R10.1).
    assert body["simulated"] is True
    assert "orderId" not in body and "id" not in body
    assert "createdAt" not in body and "timestamp" not in body

    # Each line resolves name/unitPrice from the catalog; lineTotal is derived.
    by_id = {line["productId"]: line for line in body["items"]}
    assert by_id["p-001"]["name"] == headphones.name
    assert by_id["p-001"]["unitPrice"] == headphones.price
    assert by_id["p-001"]["lineTotal"] == headphones.price * 2
    assert by_id["p-003"]["lineTotal"] == hub.price * 1

    # Total equals the sum of line totals (R10.2, R11.5).
    expected_total = headphones.price * 2 + hub.price * 1
    assert body["total"] == expected_total


def test_confirm_rejects_empty_submission() -> None:
    client = _client()

    response = client.post("/checkout/confirm", json={"items": []})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_cart"
