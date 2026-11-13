import pytest
import time
from fastapi import status
from src.cache import response_cache
from src.storage import clear_storage

@pytest.fixture(autouse=True)
def run_around_tests():
    clear_storage()
    response_cache.clear()
    yield
    response_cache.clear()

def test_product_catalog_caching(client):
    # Initial request should load and cache
    res1 = client.get("/api/products")
    assert res1.status_code == status.HTTP_200_OK
    
    # We manipulate or check the cache to ensure it's hit
    cached = response_cache.get("products_catalog")
    assert cached is not None
    assert len(cached) > 0

    # If we subsequent call, it works too
    res2 = client.get("/api/products")
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json() == res1.json()

def test_reviews_caching_and_invalidation(client):
    # 1. Register and login a normal user
    reg_payload = {"identifier": "bob", "password": "bobpassword"}
    client.post("/api/register", json=reg_payload)

    signin_payload = {"identifier": "bob", "password": "bobpassword"}
    login_res = client.post("/api/signin", json=signin_payload)
    bob_token = login_res.json()["session_token"]

    # 2. Submit review
    rev_payload = {
        "product_id": "prod_001",
        "rating": 4,
        "comment": "Nice!",
        "image_base64": None
    }
    res = client.post("/api/reviews", json=rev_payload, headers={"Authorization": f"Bearer {bob_token}"})
    assert res.status_code == status.HTTP_201_CREATED
    review_id = res.json()["review"]["review_id"]

    # 3. Log in as moderator and approve it
    mod_signin = {"identifier": "moderator", "password": "moderator"}
    mod_login_res = client.post("/api/signin", json=mod_signin)
    mod_token = mod_login_res.json()["session_token"]

    client.post(
        f"/api/moderation/reviews/{review_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {mod_token}"}
    )

    # 4. Fetch approved reviews -> this should cache the response
    res_reviews = client.get("/api/products/prod_001/reviews")
    assert res_reviews.status_code == status.HTTP_200_OK
    assert len(res_reviews.json()) == 1

    # Check that it's in the cache
    cache_key = "reviews_prod_001"
    cached = response_cache.get(cache_key)
    assert cached is not None
    assert len(cached) == 1

    # 5. Approve another review or change state -> should invalidate reviews cache
    # First submit another review
    rev_payload2 = {
        "product_id": "prod_001",
        "rating": 5,
        "comment": "Awesome!",
        "image_base64": None
    }
    res2 = client.post("/api/reviews", json=rev_payload2, headers={"Authorization": f"Bearer {bob_token}"})
    review_id2 = res2.json()["review"]["review_id"]

    # Approving second review will trigger invalidation
    client.post(
        f"/api/moderation/reviews/{review_id2}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {mod_token}"}
    )

    # Cache should be invalidated now (None)
    cached_after = response_cache.get(cache_key)
    assert cached_after is None

    # Fetch approved reviews again -> should get both and re-cache
    res_reviews_after = client.get("/api/products/prod_001/reviews")
    assert len(res_reviews_after.json()) == 2
    assert response_cache.get(cache_key) is not None
