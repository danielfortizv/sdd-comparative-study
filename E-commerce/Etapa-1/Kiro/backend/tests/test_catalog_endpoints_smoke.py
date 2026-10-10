"""Minimal verification tests for the catalog endpoints (Task 3.1).

These are smoke-level checks confirming the catalog router is wired and
returns the shared demonstration data, that a single product is retrievable,
and that an unknown id yields a structured 404 error. Comprehensive endpoint
unit tests are covered by Task 3.2.

Requirements exercised: 1.1, 1.3, 1.4, 1.5, 11.1.
"""

from fastapi.testclient import TestClient

from app.data import catalog as catalog_data
from app.main import app

client = TestClient(app)


def test_list_products_returns_shared_catalog_data() -> None:
    response = client.get("/products")
    assert response.status_code == 200

    body = response.json()
    expected = catalog_data.list_products()
    assert len(body) == len(expected)
    assert {item["id"] for item in body} == {p.id for p in expected}
    # camelCase serialization is used over the HTTP/JSON interface.
    assert "imageUrl" in body[0]


def test_get_product_returns_single_product() -> None:
    response = client.get("/products/p-001")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == "p-001"
    assert body["name"] == "Wireless Headphones"


def test_get_unknown_product_returns_structured_404() -> None:
    response = client.get("/products/does-not-exist")
    assert response.status_code == 404

    detail = response.json()["detail"]
    assert detail["error"] == "product_not_found"
    assert detail["productId"] == "does-not-exist"
    # No stack trace / internal diagnostics leak into the client response.
    assert "Traceback" not in response.text
