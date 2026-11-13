import pytest
from fastapi import status

def test_continuous_purchasing_journey(client):
    # 1. Browse catalog (FR-001 - FR-008)
    catalog_res = client.get("/api/products")
    assert catalog_res.status_code == status.HTTP_200_OK
    products = catalog_res.json()
    assert len(products) > 0
    p_id = products[0]["product_id"]

    # 2. Add product to cart (simulate preparing payload for checkout)
    cart_items = [{"product_id": p_id, "quantity": 2}]

    # 3. Register user (FR-022 - FR-024)
    reg_payload = {"identifier": "carol", "password": "securepwd456"}
    reg_res = client.post("/api/register", json=reg_payload)
    assert reg_res.status_code == status.HTTP_201_CREATED

    # 4. Sign in user (FR-025 - FR-027)
    signin_res = client.post("/api/signin", json=reg_payload)
    assert signin_res.status_code == status.HTTP_200_OK
    token = signin_res.json()["session_token"]

    # 5. Complete simulated checkout (FR-041 - FR-053)
    headers = {"Authorization": f"Bearer {token}"}
    checkout_payload = {
        "items": cart_items,
        "demonstration_info": {"name": "Carol Demonstration", "contact": "carol@example.com"}
    }
    checkout_res = client.post("/api/checkout", json=checkout_payload, headers=headers)
    assert checkout_res.status_code == status.HTTP_200_OK
    
    data = checkout_res.json()
    assert "Simulated purchase confirmed" in data["message"]
    assert data["purchase_summary"]["accumulated_total"] == round(float(products[0]["price"]) * 2, 2)
