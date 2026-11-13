import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


BACKEND = Path(__file__).resolve().parents[3] / "Spec Kit" / "backend"
sys.path.insert(0, str(BACKEND))

from src import main, security, storage  # noqa: E402


@pytest.fixture(autouse=True)
def reset_storage():
    storage.clear_storage()
    yield
    storage.clear_storage()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(main.app)


def register(client: TestClient, identifier="independent-user", password="secret"):
    return client.post("/api/register", json={"identifier": identifier, "password": password})


def signin(client: TestClient, identifier="independent-user", password="secret"):
    return client.post("/api/signin", json={"identifier": identifier, "password": password})


def test_catalog_contract_and_cache(client: TestClient):
    first = client.get("/api/products")
    assert first.status_code == 200
    products = first.json()
    assert products
    required = {"product_id", "name", "representative_image", "short_description", "price", "general_availability"}
    assert all(required <= product.keys() for product in products)
    assert storage.load_catalog_products() is storage.PRODUCTS_LIST


def test_registration_hashing_duplicate_and_validation(client: TestClient):
    assert register(client, "   ", "secret").status_code == 400
    assert register(client, "user", "").status_code == 400
    created = register(client)
    assert created.status_code == 201
    stored = storage.USERS_DB["independent-user"]
    assert stored != "secret"
    assert security.verify_password("secret", stored)
    assert not security.verify_password("wrong", stored)
    assert not security.verify_password("secret", "malformed")
    assert register(client).status_code == 400


def test_signin_success_and_failures(client: TestClient):
    assert signin(client, "", "").status_code == 401
    assert signin(client, "missing", "secret").status_code == 401
    register(client)
    assert signin(client, "independent-user", "wrong").status_code == 401
    ok = signin(client)
    assert ok.status_code == 200
    token = ok.json()["session_token"]
    assert storage.SESSIONS_DB[token] == "independent-user"


def test_token_parser_and_signout(client: TestClient):
    for value in (None, "Basic token", "Bearer", "Bearer one two"):
        with pytest.raises(HTTPException) as error:
            main.get_token_from_header(value)
        assert error.value.status_code == 401
    assert client.post("/api/signout").status_code == 200
    register(client)
    token = signin(client).json()["session_token"]
    assert client.post("/api/signout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert token not in storage.SESSIONS_DB
    assert client.post("/api/signout", headers={"Authorization": "Bearer expired"}).status_code == 200


def test_checkout_auth_cart_and_item_validation(client: TestClient):
    payload = {"items": [{"product_id": "prod-001", "quantity": 1}], "demonstration_info": {"reference": "x"}}
    assert client.post("/api/checkout", json=payload).status_code == 401
    register(client)
    token = signin(client).json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/checkout", json={"items": [], "demonstration_info": {"reference": "x"}}, headers=headers).status_code == 400
    bad_qty = {"items": [{"product_id": "prod-001", "quantity": 0}], "demonstration_info": {"reference": "x"}}
    assert client.post("/api/checkout", json=bad_qty, headers=headers).status_code == 400
    unknown = {"items": [{"product_id": "not-found", "quantity": 1}], "demonstration_info": {"reference": "x"}}
    assert client.post("/api/checkout", json=unknown, headers=headers).status_code == 400


def test_checkout_demo_validation_and_success(client: TestClient):
    products = client.get("/api/products").json()
    product = products[0]
    register(client)
    token = signin(client).json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    base_items = [{"product_id": product["product_id"], "quantity": 2}]
    assert client.post("/api/checkout", json={"items": base_items, "demonstration_info": {}}, headers=headers).status_code == 400
    assert client.post("/api/checkout", json={"items": base_items, "demonstration_info": {"reference": "  "}}, headers=headers).status_code == 400
    ok = client.post("/api/checkout", json={"items": base_items, "demonstration_info": {"reference": "demo"}}, headers=headers)
    assert ok.status_code == 200
    body = ok.json()
    assert "No real payment gateway" in body["message"]
    assert body["purchase_summary"]["items"][0]["quantity"] == 2
    assert body["purchase_summary"]["accumulated_total"] == round(float(product["price"]) * 2, 2)


def test_catalog_load_failure_is_handled(monkeypatch):
    storage.PRODUCTS_LIST.clear()
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable")))
    assert storage.load_catalog_products() == []


def test_global_middleware_returns_non_sensitive_error(client: TestClient, monkeypatch):
    monkeypatch.setattr(main, "load_catalog_products", lambda: (_ for _ in ()).throw(RuntimeError("secret detail")))
    response = client.get("/api/products")
    assert response.status_code == 500
    assert response.json() == {"error": "An internal server error occurred. Please try again later."}
    assert "secret detail" not in response.text
