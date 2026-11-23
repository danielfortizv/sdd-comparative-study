import pytest
from fastapi import status
from src.storage import clear_storage

@pytest.fixture(autouse=True)
def run_around_tests():
    clear_storage()
    yield

def test_review_lifecycle(client):
    # 1. Register and login a normal user
    reg_payload = {"identifier": "alice", "password": "alicepassword"}
    client.post("/api/register", json=reg_payload)

    signin_payload = {"identifier": "alice", "password": "alicepassword"}
    login_res = client.post("/api/signin", json=signin_payload)
    assert login_res.status_code == status.HTTP_200_OK
    alice_token = login_res.json()["session_token"]

    # 2. Try to submit a review with invalid product
    rev_payload = {
        "product_id": "invalid_prod",
        "rating": 5,
        "comment": "Nice product",
        "image_base64": None
    }
    res = client.post("/api/reviews", json=rev_payload, headers={"Authorization": f"Bearer {alice_token}"})
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in res.json()["error"]

    # 3. Submit a valid review for prod_001
    rev_payload["product_id"] = "prod_001"
    res = client.post("/api/reviews", json=rev_payload, headers={"Authorization": f"Bearer {alice_token}"})
    assert res.status_code == status.HTTP_201_CREATED
    assert "pending" in res.json()["message"]
    review_id = res.json()["review"]["review_id"]

    # 4. Verify review is not visible publicly (not approved yet)
    res = client.get("/api/products/prod_001/reviews")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) == 0

    # 5. Non-moderator tries to access moderation queue
    res = client.get("/api/moderation/reviews", headers={"Authorization": f"Bearer {alice_token}"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    # 6. Moderator login (moderator:moderator is pre-seeded)
    mod_signin = {"identifier": "moderator", "password": "moderator"}
    mod_login_res = client.post("/api/signin", json=mod_signin)
    assert mod_login_res.status_code == status.HTTP_200_OK
    mod_token = mod_login_res.json()["session_token"]

    # 7. Moderator fetches moderation queue
    res = client.get("/api/moderation/reviews", headers={"Authorization": f"Bearer {mod_token}"})
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) == 1
    assert res.json()[0]["review_id"] == review_id
    assert res.json()[0]["status"] == "pending"

    # 8. Moderator approves review
    res = client.post(
        f"/api/moderation/reviews/{review_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {mod_token}"}
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["review"]["status"] == "approved"

    # 9. Verify review is now publicly visible
    res = client.get("/api/products/prod_001/reviews")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) == 1
    assert res.json()[0]["review_id"] == review_id
    assert res.json()[0]["comment"] == "Nice product"
