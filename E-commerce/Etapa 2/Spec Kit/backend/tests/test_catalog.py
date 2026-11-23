import pytest
from fastapi.testclient import TestClient


def test_get_products(client: TestClient):
    """
    Tests that GET /api/products returns 200 OK and retrieves a list of
    correctly structured demonstration products.
    """
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) > 0

    # Verify key fields on each product
    for product in products:
        assert "product_id" in product
        assert "name" in product
        assert "representative_image" in product
        assert "short_description" in product
        assert "price" in product
        assert "general_availability" in product

        assert isinstance(product["product_id"], str)
        assert isinstance(product["name"], str)
        assert isinstance(product["representative_image"], str)
        assert isinstance(product["short_description"], str)
        assert isinstance(product["price"], (int, float))
        assert isinstance(product["general_availability"], str)
