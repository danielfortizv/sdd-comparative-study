from fastapi import status
from src.common.security import create_jwt


def test_checkout_unauthenticated(client_commerce):
    resp = client_commerce.post(
        "/api/checkout",
        json={
            "items": [{"product_id": "prod_004", "quantity": 1}],
            "demonstration_info": {"address": "123 Main St"},
        },
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_checkout_success(client_commerce):
    # Generate signed JWT token
    token = create_jwt({"sub": "alice", "role": "customer"})
    
    resp = client_commerce.post(
        "/api/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"product_id": "prod_004", "quantity": 1}],
            "demonstration_info": {
                "address": "123 Main St",
                "disclaimer": "I accept academic terms",
            },
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "Simulated purchase confirmed" in resp.json()["message"]
    assert resp.json()["purchase_summary"]["accumulated_total"] > 0


def test_checkout_empty_cart(client_commerce):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_commerce.post(
        "/api/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [],
            "demonstration_info": {"address": "123 Main St"},
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "shopping cart is empty" in resp.json()["detail"]


def test_checkout_missing_demo_info(client_commerce):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_commerce.post(
        "/api/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"product_id": "prod_004", "quantity": 1}],
            "demonstration_info": {},
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "demonstration details" in resp.json()["detail"]


def test_checkout_invalid_quantity(client_commerce):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_commerce.post(
        "/api/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"product_id": "prod_004", "quantity": -1}],
            "demonstration_info": {"address": "123 Main St"},
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
