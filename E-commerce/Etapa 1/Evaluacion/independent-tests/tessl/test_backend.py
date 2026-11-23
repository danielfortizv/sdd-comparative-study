import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


BACKEND = Path(__file__).resolve().parents[3] / "Tessl" / "backend"
sys.path.insert(0, str(BACKEND))

from app import auth, database, main  # noqa: E402


@pytest.fixture(autouse=True)
def reset_memory_database():
    database.USERS.clear()
    database.SESSIONS.clear()
    yield
    database.USERS.clear()
    database.SESSIONS.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(main.app)


def register(client: TestClient, username: str = "independent-user", password: str = "secret"):
    return client.post("/api/register", json={"username": username, "password": password})


def test_catalog_contract(client: TestClient) -> None:
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 5
    required = {"id", "name", "image_url", "description", "price", "availability"}
    assert all(required <= product.keys() for product in products)
    assert any(not product["availability"] for product in products)


def test_registration_hashes_password_and_creates_session(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "independent-user"
    assert body["token"] in database.SESSIONS
    stored = database.USERS["independent-user"]
    assert stored["hashed_password"] != "secret"
    assert auth.verify_password("secret", stored["hashed_password"], stored["salt"])
    assert not auth.verify_password("wrong", stored["hashed_password"], stored["salt"])


def test_registration_validation_and_duplicate(client: TestClient) -> None:
    assert client.post("/api/register", json={"username": "   ", "password": "secret"}).status_code == 422
    assert client.post("/api/register", json={"username": "user", "password": ""}).status_code == 422
    assert register(client, "duplicate", "secret").status_code == 200
    duplicate = register(client, "duplicate", "different")
    assert duplicate.status_code == 409
    assert "already taken" in duplicate.json()["detail"]


def test_login_success_and_failures(client: TestClient) -> None:
    register(client, "login-user", "correct")
    ok = client.post("/api/login", json={"username": "login-user", "password": "correct"})
    assert ok.status_code == 200
    assert database.SESSIONS[ok.json()["token"]] == "login-user"
    assert client.post("/api/login", json={"username": "login-user", "password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"username": "missing", "password": "wrong"}).status_code == 401


def test_logout_success_and_rejections(client: TestClient) -> None:
    token = register(client, "logout-user", "secret").json()["token"]
    assert client.post("/api/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert token not in database.SESSIONS
    assert client.post("/api/logout").status_code == 400
    assert client.post("/api/logout", headers={"Authorization": "Basic invalid"}).status_code == 400
    assert client.post("/api/logout", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_auth_helpers_cover_missing_and_expired_sessions() -> None:
    with pytest.raises(HTTPException) as missing:
        main.get_current_user(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as malformed:
        main.get_current_user("Basic value")
    assert malformed.value.status_code == 401
    with pytest.raises(HTTPException) as expired:
        main.get_current_user("Bearer expired")
    assert expired.value.status_code == 401
    assert auth.delete_session("missing") is False


def test_checkout_requires_authentication_and_non_empty_items(client: TestClient) -> None:
    assert client.post("/api/checkout", json={"items": [{"product_id": 1, "quantity": 1}]}).status_code == 401
    token = register(client).json()["token"]
    assert client.post(
        "/api/checkout",
        json={"items": []},
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 422


def test_checkout_returns_authoritative_summary(client: TestClient) -> None:
    token = register(client, "buyer", "secret").json()["token"]
    response = client.post(
        "/api/checkout",
        json={"items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["buyer"] == "buyer"
    assert summary["items"][0]["price"] == 129.99
    assert summary["items"][0]["item_total"] == 259.98
    assert summary["total_amount"] == 309.97


def test_checkout_rejects_unknown_and_unavailable_products(client: TestClient) -> None:
    token = register(client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    unknown = client.post("/api/checkout", json={"items": [{"product_id": 999, "quantity": 1}]}, headers=headers)
    assert unknown.status_code == 404
    unavailable = client.post("/api/checkout", json={"items": [{"product_id": 5, "quantity": 1}]}, headers=headers)
    assert unavailable.status_code == 400

