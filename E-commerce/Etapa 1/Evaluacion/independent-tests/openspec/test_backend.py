import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "frozen-first-implementation" / "backend"
sys.path.insert(0, str(BACKEND))

from app import database, main  # noqa: E402


def reset_database() -> None:
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    database.seed_database()


def test_health_and_catalog_contract() -> None:
    reset_database()
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "healthy"}
        response = client.get("/api/products")
        assert response.status_code == 200
        products = response.json()
        assert products
        required = {"id", "name", "description", "price", "is_available", "image_url"}
        assert all(required <= product.keys() for product in products)


def test_registration_login_and_failures() -> None:
    reset_database()
    credentials = {"account_identifier": "coverage-user", "password": "coverage-secret"}
    with TestClient(main.app) as client:
        registered = client.post("/api/auth/register", json=credentials)
        assert registered.status_code == 201
        assert client.post("/api/auth/register", json=credentials).status_code == 400
        assert client.post("/api/auth/register", json={"account_identifier": " ", "password": " "}).status_code == 400
        logged_in = client.post("/api/auth/login", json=credentials)
        assert logged_in.status_code == 200
        assert logged_in.json()["access_token"]
        assert client.post("/api/auth/login", json={**credentials, "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"account_identifier": " ", "password": " "}).status_code == 400

    with database.SessionLocal() as session:
        stored = session.query(database.User).filter_by(account_identifier="coverage-user").one()
        assert stored.password_hash != credentials["password"]
