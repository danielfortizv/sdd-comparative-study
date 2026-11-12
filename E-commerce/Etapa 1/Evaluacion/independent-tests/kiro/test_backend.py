"""Independent Stage 1 backend checks for the frozen Kiro implementation."""

from fastapi.testclient import TestClient

from app.data.accounts import account_store
from app.main import app
from app.services.signin_service import reset_session


client = TestClient(app)


def setup_function() -> None:
    account_store.clear()
    reset_session()


def test_health_and_catalog_are_public_and_complete() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert products
    for product in products:
        assert set(product) == {
            "id", "name", "imageUrl", "description", "price", "available"
        }
        assert product["name"] and product["imageUrl"] and product["description"]
        assert isinstance(product["price"], (int, float))
        assert isinstance(product["available"], bool)


def test_product_detail_is_consistent_and_unknown_product_is_safe() -> None:
    product = client.get("/products").json()[0]
    assert client.get(f"/products/{product['id']}").json() == product
    missing = client.get("/products/not-a-product")
    assert missing.status_code == 404
    assert "traceback" not in missing.text.lower()


def test_registration_validation_and_password_storage_are_safe() -> None:
    incomplete = client.post("/auth/register", json={})
    assert incomplete.status_code == 422
    assert set(incomplete.json()["emptyFields"]) == {"identifier", "password"}

    # Pydantic rejects non-text values without leaking their values.
    invalid = client.post(
        "/auth/register", json={"identifier": ["secret-id"], "password": {"raw": "secret"}}
    )
    assert invalid.status_code == 422
    assert "secret-id" not in invalid.text and '"raw":"secret"' not in invalid.text

    created = client.post(
        "/auth/register", json={"identifier": "independent-user", "password": "plain-secret"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["identifier"] == "independent-user"
    assert "password" not in created.text.lower()

    stored = account_store.get_by_identifier("independent-user")
    assert stored is not None
    assert stored.password_hash != "plain-secret"
    assert "plain-secret" not in repr(stored)


def test_duplicate_registration_does_not_echo_credentials() -> None:
    payload = {"identifier": "duplicate-secret-id", "password": "duplicate-secret-password"}
    assert client.post("/auth/register", json=payload).status_code == 201
    duplicate = client.post("/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert payload["identifier"] not in duplicate.text
    assert payload["password"] not in duplicate.text


def test_login_session_and_logout_with_uniform_safe_failures() -> None:
    payload = {"identifier": "login-user", "password": "login-secret"}
    assert client.post("/auth/register", json=payload).status_code == 201

    incomplete = client.post("/auth/login", json={"identifier": "", "password": ""})
    wrong = client.post(
        "/auth/login", json={"identifier": payload["identifier"], "password": "wrong-secret"}
    )
    unknown = client.post(
        "/auth/login", json={"identifier": "unknown-secret-id", "password": "wrong-secret"}
    )
    assert incomplete.status_code == wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert "wrong-secret" not in wrong.text and "unknown-secret-id" not in unknown.text

    login = client.post("/auth/login", json=payload)
    assert login.status_code == 200
    assert login.json()["active"] is True
    assert "password" not in login.text.lower()

    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert logout.json() == {"active": False, "customerId": None}


def test_checkout_is_catalog_derived_simulated_and_non_persistent() -> None:
    product = client.get("/products").json()[0]
    payload = {"items": [{"productId": product["id"], "quantity": 2}]}
    response = client.post("/checkout/confirm", json=payload)
    assert response.status_code == 200
    confirmation = response.json()
    assert confirmation["simulated"] is True
    assert confirmation["items"][0]["name"] == product["name"]
    assert confirmation["items"][0]["unitPrice"] == product["price"]
    assert confirmation["items"][0]["lineTotal"] == product["price"] * 2
    assert confirmation["total"] == product["price"] * 2
    assert "order" not in response.text.lower()
    assert "timestamp" not in response.text.lower()

    # Repeating the request produces a confirmation but no durable order resource.
    assert client.post("/checkout/confirm", json=payload).json() == confirmation


def test_checkout_rejects_empty_unknown_and_invalid_items() -> None:
    empty = client.post("/checkout/confirm", json={"items": []})
    unknown = client.post(
        "/checkout/confirm", json={"items": [{"productId": "missing", "quantity": 1}]}
    )
    invalid = client.post(
        "/checkout/confirm", json={"items": [{"productId": "p-001", "quantity": 0}]}
    )
    assert empty.status_code == unknown.status_code == 400
    assert empty.json()["detail"]["code"] == "empty_cart"
    assert unknown.json()["detail"]["code"] == "unknown_product"
    assert invalid.status_code in {400, 422}

