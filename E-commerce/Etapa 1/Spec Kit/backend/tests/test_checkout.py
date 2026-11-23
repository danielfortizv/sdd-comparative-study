import pytest
from fastapi import status

def test_simulated_checkout(client):
    # 1. Register and sign in to get session token
    client.post("/api/register", json={"identifier": "bob", "password": "password123"})
    signin_res = client.post("/api/signin", json={"identifier": "bob", "password": "password123"})
    token = signin_res.json()["session_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test checkout with empty cart (must fail)
    empty_payload = {
        "items": [],
        "demonstration_info": {"field_a": "Bob Test", "field_b": "bob@example.com"}
    }
    response = client.post("/api/checkout", json=empty_payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in response.json()["error"]

    # 3. Get catalog products to construct a valid cart
    products_res = client.get("/api/products")
    products = products_res.json()
    assert len(products) > 0
    p_id = products[0]["product_id"]

    # 4. Test checkout with valid cart and incomplete demonstration info (must fail)
    bad_info_payload = {
        "items": [{"product_id": p_id, "quantity": 2}],
        "demonstration_info": {}
    }
    response = client.post("/api/checkout", json=bad_info_payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "details" in response.json()["error"]

    # 5. Test valid simulated checkout
    valid_payload = {
        "items": [{"product_id": p_id, "quantity": 3}],
        "demonstration_info": {"field_a": "Bob Test", "field_b": "bob@example.com"}
    }
    response = client.post("/api/checkout", json=valid_payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "Simulated purchase confirmed" in data["message"]
    assert "purchase_summary" in data
    assert len(data["purchase_summary"]["items"]) == 1
    assert data["purchase_summary"]["items"][0]["product_id"] == p_id
    assert data["purchase_summary"]["items"][0]["quantity"] == 3
