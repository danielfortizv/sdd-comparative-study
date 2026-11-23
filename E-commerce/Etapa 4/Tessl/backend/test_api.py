import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.cache import response_cache
from app.auth import hash_password

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    """
    Fixture to reset the database and cache state before each test.
    """
    # Reset cache
    response_cache.clear_all()
    
    # 1. Reset DB_IDENTITY
    with sqlite3.connect("identity.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT,
                salt TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT,
                expires_at REAL
            )
        """)
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM sessions")
        # Seed moderator
        m_hashed, m_salt = hash_password("moderator")
        conn.execute("INSERT INTO users (username, hashed_password, salt) VALUES (?, ?, ?)", ("moderator", m_hashed, m_salt))
        conn.commit()

    # 2. Reset DB_COMMERCE
    with sqlite3.connect("commerce.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                image_url TEXT,
                description TEXT,
                price REAL,
                availability INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public_reviews (
                id INTEGER PRIMARY KEY,
                product_id INTEGER,
                rating INTEGER,
                comment TEXT,
                image_base64 TEXT,
                username TEXT,
                created_at TEXT
            )
        """)
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM public_reviews")
        # Seed products
        from app.commerce import PRODUCTS_SEED
        for p in PRODUCTS_SEED:
            conn.execute(
                "INSERT INTO products (id, name, image_url, description, price, availability) VALUES (?, ?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["image_url"], p["description"], p["price"], 1 if p["availability"] else 0)
            )
        # Seed public reviews
        reviews_seed = [
            {
                "id": 1,
                "product_id": 1,
                "rating": 5,
                "comment": "Incredible durability and comfort! Recommended for programmers.",
                "image_base64": None,
                "status": "approved",
                "username": "keyboard_fanatic",
                "created_at": "2026-02-15 14:30:22"
            },
            {
                "id": 2,
                "product_id": 1,
                "rating": 4,
                "comment": "Excellent keyboard, although the keys are a bit loud.",
                "image_base64": None,
                "status": "approved",
                "username": "alice_dev",
                "created_at": "2026-02-18 09:12:05"
            },
            {
                "id": 3,
                "product_id": 2,
                "rating": 5,
                "comment": "Super precise, the battery lasts forever. Love it!",
                "image_base64": None,
                "status": "approved",
                "username": "mouse_guru",
                "created_at": "2026-02-10 18:45:00"
            }
        ]
        for r in reviews_seed:
            conn.execute(
                "INSERT INTO public_reviews (id, product_id, rating, comment, image_base64, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["product_id"], r["rating"], r["comment"], r["image_base64"], r["username"], r["created_at"])
            )
        conn.commit()

    # 3. Reset DB_REVIEWS
    with sqlite3.connect("reviews.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                rating INTEGER,
                comment TEXT,
                image_base64 TEXT,
                status TEXT,
                username TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                payload TEXT,
                processed INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        conn.execute("DELETE FROM reviews")
        conn.execute("DELETE FROM outbox")
        # Seed reviews
        reviews_seed = [
            {
                "id": 1,
                "product_id": 1,
                "rating": 5,
                "comment": "Incredible durability and comfort! Recommended for programmers.",
                "image_base64": None,
                "status": "approved",
                "username": "keyboard_fanatic",
                "created_at": "2026-02-15 14:30:22"
            },
            {
                "id": 2,
                "product_id": 1,
                "rating": 4,
                "comment": "Excellent keyboard, although the keys are a bit loud.",
                "image_base64": None,
                "status": "approved",
                "username": "alice_dev",
                "created_at": "2026-02-18 09:12:05"
            },
            {
                "id": 3,
                "product_id": 2,
                "rating": 5,
                "comment": "Super precise, the battery lasts forever. Love it!",
                "image_base64": None,
                "status": "approved",
                "username": "mouse_guru",
                "created_at": "2026-02-10 18:45:00"
            }
        ]
        for r in reviews_seed:
            conn.execute(
                "INSERT INTO reviews (id, product_id, rating, comment, image_base64, status, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["product_id"], r["rating"], r["comment"], r["image_base64"], r["status"], r["username"], r["created_at"])
            )
        conn.commit()


def test_get_products_and_caching():
    """
    Verify GET /api/products serves products and stores response in cache.
    """
    # First request - cache miss
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["name"] == "Premium Ergonomic Keyboard"

    # Modify availability in SQLite products table
    with sqlite3.connect("commerce.db") as conn:
        conn.execute("UPDATE products SET availability = 0 WHERE id = 1")
        conn.commit()

    try:
        # Second request - cache hit (should return cached data where availability is True)
        response_cached = client.get("/api/products")
        assert response_cached.status_code == 200
        data_cached = response_cached.json()
        assert data_cached[0]["availability"] is True
        
        # Clear cache and check - cache miss (should return modified data where availability is False)
        response_cache.clear_all()
        response_fresh = client.get("/api/products")
        assert response_fresh.status_code == 200
        assert response_fresh.json()[0]["availability"] is False
    finally:
        # Restore availability in DB
        with sqlite3.connect("commerce.db") as conn:
            conn.execute("UPDATE products SET availability = 1 WHERE id = 1")
            conn.commit()


def test_user_registration_and_login():
    """
    Verify user registration, login, duplicate username prevention, and logout.
    """
    # 1. Register a new user
    reg_payload = {"username": "john_doe", "password": "securepassword123"}
    response = client.post("/api/register", json=reg_payload)
    assert response.status_code == 200
    reg_data = response.json()
    assert "token" in reg_data
    assert reg_data["username"] == "john_doe"
    token = reg_data["token"]

    # 2. Attempt duplicate registration
    response_dup = client.post("/api/register", json=reg_payload)
    assert response_dup.status_code == 409
    assert "already taken" in response_dup.json()["detail"]

    # 3. Login with correct password
    login_payload = {"username": "john_doe", "password": "securepassword123"}
    response_login = client.post("/api/login", json=login_payload)
    assert response_login.status_code == 200
    assert response_login.json()["token"] is not None

    # 4. Login with incorrect password
    bad_login_payload = {"username": "john_doe", "password": "wrongpassword"}
    response_bad = client.post("/api/login", json=bad_login_payload)
    assert response_bad.status_code == 401

    # 5. Logout
    headers = {"Authorization": f"Bearer {token}"}
    response_logout = client.post("/api/logout", headers=headers)
    assert response_logout.status_code == 200
    assert response_logout.json()["message"] == "Logged out successfully"

    # 6. Verify token is invalidated
    response_checkout = client.post("/api/checkout", headers=headers, json={"items": [{"product_id": 1, "quantity": 1}]})
    assert response_checkout.status_code == 401


def test_checkout_validation_and_simulation():
    """
    Verify simulated checkout rules (auth required, non-empty, items availability, no order ID returned).
    """
    # 1. Unauthenticated checkout rejection
    checkout_payload = {"items": [{"product_id": 1, "quantity": 2}]}
    response = client.post("/api/checkout", json=checkout_payload)
    assert response.status_code == 401

    # Register user
    reg_payload = {"username": "buyer1", "password": "password1"}
    reg_resp = client.post("/api/register", json=reg_payload)
    token = reg_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Empty cart rejection
    response_empty = client.post("/api/checkout", headers=headers, json={"items": []})
    assert response_empty.status_code in (400, 422)

    # 3. Successful simulated checkout
    response_ok = client.post("/api/checkout", headers=headers, json=checkout_payload)
    assert response_ok.status_code == 200
    ok_data = response_ok.json()
    assert "summary" in ok_data
    assert ok_data["summary"]["total_amount"] == round(129.99 * 2, 2)
    assert ok_data["summary"]["buyer"] == "buyer1"
    # Ensure NO order ID is leaked or returned
    assert "order_id" not in ok_data
    assert "order_id" not in ok_data["summary"]

    # 4. Out of stock item checkout rejection
    with sqlite3.connect("commerce.db") as conn:
        conn.execute("UPDATE products SET availability = 0 WHERE id = 3")
        conn.commit()
    try:
        response_oos = client.post("/api/checkout", headers=headers, json={"items": [{"product_id": 3, "quantity": 1}]})
        assert response_oos.status_code == 400
        assert "out of stock" in response_oos.json()["detail"]
    finally:
        with sqlite3.connect("commerce.db") as conn:
            conn.execute("UPDATE products SET availability = 1 WHERE id = 3")
            conn.commit()


def test_reviews_submission_and_moderation_flow():
    """
    Verify submission, pending visibility, access control, moderation, and public visibility with cache invalidation.
    """
    # 1. Submit review (visitor) -> should fail (auth required)
    review_payload = {"rating": 5, "comment": "Amazing item!", "image_base64": None}
    response = client.post("/api/products/1/reviews", json=review_payload)
    assert response.status_code == 401

    # Register/login user
    reg_resp = client.post("/api/register", json={"username": "reviewer1", "password": "password123"})
    token = reg_resp.json()["token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Get initial approved reviews for Product 1 (forces reviews:1 to be cached)
    get_init = client.get("/api/products/1/reviews")
    assert get_init.status_code == 200
    assert len(get_init.json()) == 2
    assert response_cache.get("reviews:1") is not None

    # 3. Submit review (authenticated user)
    response_sub = client.post("/api/products/1/reviews", headers=user_headers, json=review_payload)
    assert response_sub.status_code == 200
    new_review = response_sub.json()["review"]
    assert new_review["status"] == "pending"
    assert new_review["username"] == "reviewer1"
    review_id = new_review["id"]

    # Verify cache for reviews:1 was invalidated upon review submission
    assert response_cache.get("reviews:1") is None

    # 4. Fetch reviews list (visitor) -> should still be 2 (pending review is hidden)
    get_vis = client.get("/api/products/1/reviews")
    assert get_vis.status_code == 200
    assert len(get_vis.json()) == 2
    assert response_cache.get("reviews:1") is not None  # cached again

    # 5. Non-moderator attempts moderation access -> 403 Forbidden
    response_mod_fail = client.get("/api/moderation/reviews", headers=user_headers)
    assert response_mod_fail.status_code == 403

    # 6. Moderator logs in and views moderation reviews list
    mod_login = client.post("/api/login", json={"username": "moderator", "password": "moderator"})
    mod_token = mod_login.json()["token"]
    mod_headers = {"Authorization": f"Bearer {mod_token}"}

    response_mod_list = client.get("/api/moderation/reviews", headers=mod_headers)
    assert response_mod_list.status_code == 200
    mod_reviews = response_mod_list.json()
    assert len(mod_reviews) >= 4
    pending_found = any(r["id"] == review_id and r["status"] == "pending" for r in mod_reviews)
    assert pending_found is True

    # 7. Moderator approves review
    response_approve = client.post(f"/api/moderation/reviews/{review_id}/status", headers=mod_headers, json={"status": "approved"})
    assert response_approve.status_code == 200
    assert response_approve.json()["review"]["status"] == "approved"

    # Verify cache for reviews:1 was invalidated upon review approval
    assert response_cache.get("reviews:1") is None

    # 8. Fetch reviews list (visitor) -> should now be 3 (approved review is now visible)
    get_vis_after = client.get("/api/products/1/reviews")
    assert get_vis_after.status_code == 200
    assert len(get_vis_after.json()) == 3
    approved_found = any(r["id"] == review_id and r["username"] == "reviewer1" for r in get_vis_after.json())
    assert approved_found is True
