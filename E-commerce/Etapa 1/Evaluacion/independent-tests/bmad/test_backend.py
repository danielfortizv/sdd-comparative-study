import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND = Path(__file__).resolve().parents[3] / "Bmad Method" / "backend"
sys.path.insert(0, str(BACKEND))

import database  # noqa: E402
import main  # noqa: E402


def make_client(tmp_path: Path) -> TestClient:
    database.DB_PATH = str(tmp_path / "users.db")
    database.init_db()
    return TestClient(main.app)


def test_catalog_contract(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert products
    required = {"name", "image_svg", "description", "price", "availability"}
    assert all(required <= product.keys() for product in products)


def test_registration_login_and_non_plaintext_storage(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    credentials = {"username": "coverage-user", "password": "coverage-secret"}
    assert client.post("/api/register", json=credentials).status_code == 201
    assert client.post("/api/login", json=credentials).status_code == 200
    assert client.post(
        "/api/login",
        json={"username": "coverage-user", "password": "wrong"},
    ).status_code == 401

    with sqlite3.connect(database.DB_PATH) as connection:
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("coverage-user",),
        ).fetchone()[0]
    assert stored != "coverage-secret"
    assert "$" in stored


def test_incomplete_registration_is_rejected(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.post(
        "/api/register",
        json={"username": "", "password": ""},
    ).status_code in {400, 422}


def test_duplicate_registration_does_not_reveal_account_existence(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    credentials = {"username": "duplicate-user", "password": "secret"}
    assert client.post("/api/register", json=credentials).status_code == 201
    response = client.post("/api/register", json=credentials)
    assert response.status_code == 400
    assert "already registered" not in response.json()["detail"].lower()


def test_empty_checkout_is_rejected(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/checkout", json={"items": [], "summary_total": 0})
    assert response.status_code == 400


def test_checkout_uses_authoritative_catalog_values(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/api/checkout",
        json={
            "items": [{"id": 1, "quantity": 2, "price": 0.01}],
            "summary_total": 0.02,
        },
    )
    assert response.status_code == 200
    summary = response.json()["order_summary"]
    assert summary["items"][0]["price"] == 59.99
    assert summary["items"][0]["subtotal"] == 119.98
    assert summary["total"] == 119.98


def test_checkout_rejects_unknown_product(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/api/checkout",
        json={
            "items": [{"id": 999, "quantity": 1, "price": 500}],
            "summary_total": 500,
        },
    )
    assert response.status_code == 400


def test_checkout_rejects_unavailable_product(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/api/checkout",
        json={
            "items": [{"id": 4, "quantity": 1, "price": 120}],
            "summary_total": 120,
        },
    )
    assert response.status_code == 400

