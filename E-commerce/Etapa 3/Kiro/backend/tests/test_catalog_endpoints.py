"""Unit tests for the catalog endpoints (Task 3.2).

Exercises ``GET /products`` and ``GET /products/{id}`` through a
``fastapi.testclient.TestClient`` against ``app.main:app``. These tests cover:

* the product list response — every product is returned with the full
  commercial field set in camelCase (Requirement 1.3);
* the single-product response — the expanded view returns the same name,
  image, description, price, and availability shown in the list (Requirements
  1.3, 1.4);
* the not-found error shape — an unknown id yields a structured 404 whose
  ``detail`` carries ``error``, ``message``, and ``productId`` with no internal
  diagnostics leaked (Requirement 1.4, design Error Handling).

Requirements: 1.3, 1.4.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data import catalog as catalog_data
from app.main import app

client = TestClient(app)

# Field set the HTTP/JSON interface serializes for a Product (camelCase).
EXPECTED_PRODUCT_FIELDS = {
    "id",
    "name",
    "imageUrl",
    "description",
    "price",
    "available",
}


def _expected_json(product) -> dict:
    """Serialize a Product the way the API does (by alias / camelCase)."""
    return product.model_dump(by_alias=True)


# --------------------------------------------------------------------------- #
# GET /products  -- product list response (R1.3)
# --------------------------------------------------------------------------- #


def test_list_products_returns_ok_and_all_products() -> None:
    response = client.get("/products")

    assert response.status_code == 200
    body = response.json()

    expected = catalog_data.list_products()
    assert isinstance(body, list)
    assert len(body) == len(expected)
    assert [item["id"] for item in body] == [p.id for p in expected]


def test_list_products_each_entry_has_full_commercial_fields() -> None:
    # R1.3: each product shows name, image, short description, price, and the
    # general availability indication. Verify the camelCase field set exactly.
    response = client.get("/products")
    assert response.status_code == 200

    for item in response.json():
        assert set(item.keys()) == EXPECTED_PRODUCT_FIELDS
        assert isinstance(item["name"], str) and item["name"]
        assert isinstance(item["imageUrl"], str) and item["imageUrl"]
        assert isinstance(item["description"], str) and item["description"]
        assert isinstance(item["price"], (int, float))
        assert isinstance(item["available"], bool)


def test_list_products_matches_shared_demonstration_data_exactly() -> None:
    # The list serves the same demonstration data used across the flow.
    response = client.get("/products")
    assert response.status_code == 200

    expected = [_expected_json(p) for p in catalog_data.list_products()]
    assert response.json() == expected


# --------------------------------------------------------------------------- #
# GET /products/{id}  -- single-product response (R1.3, R1.4)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "product", catalog_data.list_products(), ids=lambda p: p.id
)
def test_get_product_returns_expanded_view_matching_list(product) -> None:
    # R1.4: the expanded single-product view shows the same name, image,
    # description, price, and availability as the catalog list entry.
    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    assert response.json() == _expected_json(product)


def test_get_product_serializes_image_url_in_camel_case() -> None:
    response = client.get("/products/p-001")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == EXPECTED_PRODUCT_FIELDS
    assert "imageUrl" in body
    assert "image_url" not in body


def test_get_unavailable_product_reports_availability_false() -> None:
    # p-005 is marked unavailable in the demonstration data; the availability
    # indication must survive the round trip (R1.3).
    response = client.get("/products/p-005")

    assert response.status_code == 200
    assert response.json()["available"] is False


# --------------------------------------------------------------------------- #
# GET /products/{id}  -- not-found error shape (R1.4)
# --------------------------------------------------------------------------- #


def test_get_unknown_product_returns_404_structured_error() -> None:
    unknown_id = "does-not-exist"
    response = client.get(f"/products/{unknown_id}")

    assert response.status_code == 404

    detail = response.json()["detail"]
    assert detail["error"] == "product_not_found"
    assert detail["productId"] == unknown_id
    assert isinstance(detail["message"], str) and detail["message"]
    assert unknown_id in detail["message"]


def test_get_unknown_product_error_leaks_no_internal_detail() -> None:
    response = client.get("/products/does-not-exist")

    assert response.status_code == 404
    # No stack trace / internal diagnostics in the client-facing response.
    assert "Traceback" not in response.text
    assert "Exception" not in response.text
