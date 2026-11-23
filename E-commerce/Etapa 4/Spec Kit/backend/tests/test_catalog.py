from fastapi import status


def test_get_catalog_products(client_commerce):
    resp = client_commerce.get("/api/products")
    assert resp.status_code == status.HTTP_200_OK
    products = resp.json()
    assert len(products) > 0
    # Check that keys match requirements
    assert "product_id" in products[0]
    assert "name" in products[0]
    assert "price" in products[0]
