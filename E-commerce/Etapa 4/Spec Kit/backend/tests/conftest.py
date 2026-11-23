import os
os.environ["RUN_WORKERS"] = "false"

import sqlite3
import pytest
from fastapi.testclient import TestClient

TEST_IDENTITY_DB = "test_identity.db"
TEST_COMMERCE_DB = "test_commerce.db"
TEST_REVIEWS_DB = "test_reviews.db"

# Configure environment database paths before imports
os.environ["IDENTITY_DB_PATH"] = TEST_IDENTITY_DB
os.environ["COMMERCE_DB_PATH"] = TEST_COMMERCE_DB
os.environ["REVIEWS_DB_PATH"] = TEST_REVIEWS_DB
os.environ["JWT_SECRET"] = "test-secret-key-123456"

from src.common.security import hash_password
from src.services.identity.main import app as identity_app
from src.services.commerce.main import app as commerce_app, response_cache as commerce_cache
from src.services.reviews.main import app as reviews_app
from src.services.gateway.main import app as gateway_app


def reset_test_databases():
    """Truncates tables and re-seeds databases to ensure complete test isolation without breaking connections."""
    
    # 1. Reset Identity DB
    with sqlite3.connect(TEST_IDENTITY_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                identifier TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        conn.execute("DELETE FROM users")
        conn.execute(
            "INSERT INTO users (identifier, password_hash, role) VALUES (?, ?, ?)",
            ("moderator", hash_password("moderator"), "moderator"),
        )
        conn.commit()
        
    # 2. Reset Commerce DB
    with sqlite3.connect(TEST_COMMERCE_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                representative_image TEXT NOT NULL,
                short_description TEXT NOT NULL,
                price REAL NOT NULL,
                general_availability TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_reviews (
                review_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                image_base64 TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                items_json TEXT NOT NULL,
                accumulated_total REAL NOT NULL,
                demonstration_info_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM product_reviews")
        conn.execute("DELETE FROM processed_events")
        conn.execute("DELETE FROM orders")
        
        # Seed catalog products
        import json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        catalog_path = os.path.join(current_dir, "..", "src", "data", "catalog.json")
        with open(catalog_path, "r", encoding="utf-8") as f:
            products_list = json.load(f)
        for p in products_list:
            conn.execute(
                """
                INSERT INTO products (product_id, name, representative_image, short_description, price, general_availability)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    p["product_id"],
                    p["name"],
                    p["representative_image"],
                    p["short_description"],
                    p["price"],
                    p["general_availability"],
                ),
            )
        conn.commit()
        
    # 3. Reset Reviews DB
    with sqlite3.connect(TEST_REVIEWS_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                image_base64 TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("DELETE FROM reviews")
        conn.execute("DELETE FROM outbox")
        conn.commit()


@pytest.fixture(autouse=True)
def run_around_tests():
    # Reset databases and cache before each test
    reset_test_databases()
    commerce_cache.clear()
    
    yield
    
    # Clear cache after test
    commerce_cache.clear()


@pytest.fixture
def client_identity():
    with TestClient(identity_app) as c:
        yield c


@pytest.fixture
def client_commerce():
    with TestClient(commerce_app) as c:
        yield c


@pytest.fixture
def client_reviews():
    with TestClient(reviews_app) as c:
        yield c


@pytest.fixture
def client_gateway():
    with TestClient(gateway_app) as c:
        yield c


@pytest.fixture
def client():
    with TestClient(gateway_app) as c:
        yield c
