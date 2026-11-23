from fastapi import status
from src.common.security import create_jwt


def test_submit_review_unauthenticated(client_reviews):
    resp = client_reviews.post(
        "/api/reviews",
        json={
            "product_id": "prod_004",
            "rating": 5,
            "comment": "Nice!",
        },
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_submit_review_success(client_reviews):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_reviews.post(
        "/api/reviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": "prod_004",
            "rating": 5,
            "comment": "Incredible keyboard!",
            "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["review"]["product_id"] == "prod_004"
    assert data["review"]["rating"] == 5
    assert data["review"]["status"] == "pending"


def test_submit_review_invalid_rating(client_reviews):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_reviews.post(
        "/api/reviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": "prod_004",
            "rating": 6,  # Invalid
            "comment": "Awesome!",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_submit_review_empty_comment(client_reviews):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_reviews.post(
        "/api/reviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": "prod_004",
            "rating": 4,
            "comment": "   ",  # Empty comment
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_moderation_queue_unauthorized_customer(client_reviews):
    token = create_jwt({"sub": "alice", "role": "customer"})
    resp = client_reviews.get(
        "/api/moderation/reviews", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_moderation_queue_moderator(client_reviews):
    token = create_jwt({"sub": "moderator", "role": "moderator"})
    resp = client_reviews.get(
        "/api/moderation/reviews", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == status.HTTP_200_OK


def test_update_review_status_success(client_reviews):
    # Create review first
    customer_token = create_jwt({"sub": "alice", "role": "customer"})
    sub_resp = client_reviews.post(
        "/api/reviews",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "product_id": "prod_004",
            "rating": 5,
            "comment": "Perfect!",
        },
    )
    review_id = sub_resp.json()["review"]["review_id"]
    
    # Approve review
    mod_token = create_jwt({"sub": "moderator", "role": "moderator"})
    resp = client_reviews.post(
        f"/api/moderation/reviews/{review_id}/status",
        headers={"Authorization": f"Bearer {mod_token}"},
        json={"status": "approved"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["review"]["status"] == "approved"
