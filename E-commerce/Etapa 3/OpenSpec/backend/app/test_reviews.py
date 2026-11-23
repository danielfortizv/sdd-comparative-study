import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set a different database for testing or just use a local memory/file DB
# To avoid messing up the main db, we can mock get_db
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_ecommerce.db"

from app.main import app
from app.database import Base, get_db, Product

# Setup a clean test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ecommerce.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestReviewsWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Remove old test DB if it exists
        if os.path.exists("test_ecommerce.db"):
            try:
                os.remove("test_ecommerce.db")
            except Exception:
                pass

        # Create tables and seed test product
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()
        # Seed a test product
        cls.test_product = Product(
            id=1,
            name="Test Coffee Cup",
            image_url="http://example.com/cup.jpg",
            description="Perfect for testing reviews.",
            price=9.99,
            is_available=True
        )
        cls.db.add(cls.test_product)
        cls.db.commit()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        # Dispose of engine to release any open connections
        engine.dispose()
        # Clean up database file if possible, ignoring errors on Windows
        if os.path.exists("test_ecommerce.db"):
            try:
                os.remove("test_ecommerce.db")
            except Exception:
                pass

    def setUp(self):
        from app.cache import cache_instance
        cache_instance.clear()
        
        # Drop and recreate tables to ensure total isolation
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Seed test product
        db = TestingSessionLocal()
        test_product = Product(
            id=1,
            name="Test Coffee Cup",
            image_url="http://example.com/cup.jpg",
            description="Perfect for testing reviews.",
            price=9.99,
            is_available=True
        )
        db.add(test_product)
        db.commit()
        db.close()

    def tearDown(self):
        from app.cache import cache_instance
        cache_instance.clear()

    def test_complete_reviews_and_moderation_flow(self):
        # 1. Fetch product detail, verify average_rating is None initially
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test Coffee Cup")
        self.assertIsNone(data["average_rating"])

        # 2. Try to submit review without auth (should fail)
        response = self.client.post("/api/products/1/reviews", json={
            "rating": 5,
            "comment": "Unauthenticated review comment"
        })
        self.assertEqual(response.status_code, 401)

        # 3. Register and login normal user
        response = self.client.post("/api/auth/register", json={
            "account_identifier": "testuser",
            "password": "testpassword"
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.post("/api/auth/login", json={
            "account_identifier": "testuser",
            "password": "testpassword"
        })
        self.assertEqual(response.status_code, 200)
        user_token = response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 4. Register and login moderator
        response = self.client.post("/api/auth/register", json={
            "account_identifier": "moderator",
            "password": "modpassword"
        })
        self.assertEqual(response.status_code, 201)

        response = self.client.post("/api/auth/login", json={
            "account_identifier": "moderator",
            "password": "modpassword"
        })
        self.assertEqual(response.status_code, 200)
        mod_token = response.json()["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}

        # 5. Submit valid review (should succeed, start as pending)
        response = self.client.post("/api/products/1/reviews", headers=user_headers, json={
            "rating": 4,
            "comment": "Excellent mug! Loved it.",
            "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        })
        self.assertEqual(response.status_code, 201)
        review_data = response.json()
        self.assertEqual(review_data["rating"], 4)
        self.assertEqual(review_data["comment"], "Excellent mug! Loved it.")
        self.assertEqual(review_data["status"], "pending")
        review_id = review_data["id"]

        # 6. Verify product detail still shows average_rating as None (pending reviews are hidden)
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["average_rating"])

        # 7. Verify product reviews page returns empty list of approved reviews
        response = self.client.get("/api/products/1/reviews")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

        # 8. Try to list reviews for moderation as normal user (should be forbidden)
        response = self.client.get("/api/moderation/reviews", headers=user_headers)
        self.assertEqual(response.status_code, 403)

        # 9. List reviews for moderation as moderator (should see our pending review)
        response = self.client.get("/api/moderation/reviews", headers=mod_headers)
        self.assertEqual(response.status_code, 200)
        pending_list = response.json()
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0]["id"], review_id)

        # 10. Approve review as moderator
        response = self.client.post(f"/api/moderation/reviews/{review_id}/action", headers=mod_headers, json={
            "action": "approve"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")

        # 11. Verify product detail now shows average_rating as 4.0
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["average_rating"], 4.0)

        # 12. Verify product reviews page returns the approved review
        response = self.client.get("/api/products/1/reviews")
        self.assertEqual(response.status_code, 200)
        reviews_list = response.json()
        self.assertEqual(len(reviews_list), 1)
        self.assertEqual(reviews_list[0]["comment"], "Excellent mug! Loved it.")
        self.assertEqual(reviews_list[0]["user_id"], "testuser")

    def test_caching_and_invalidation_flow(self):
        from app.cache import cache_instance
        # Clear cache first
        cache_instance.clear()

        # Register users if not already registered (ignore 400 if they exist)
        self.client.post("/api/auth/register", json={
            "account_identifier": "testuser",
            "password": "testpassword"
        })
        self.client.post("/api/auth/register", json={
            "account_identifier": "moderator",
            "password": "modpassword"
        })

        # 1. Fetch product detail (will be cached)
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        
        # Verify it exists in cache
        cached_product = cache_instance.get("product_detail_1")
        self.assertIsNotNone(cached_product)
        self.assertEqual(cached_product["id"], 1)

        # 2. Fetch product reviews (will be cached)
        response = self.client.get("/api/products/1/reviews")
        self.assertEqual(response.status_code, 200)
        
        # Verify it exists in cache
        cached_reviews = cache_instance.get("product_reviews_1")
        self.assertIsNotNone(cached_reviews)

        # 3. Manually put some dummy data in cache to check hit
        cache_instance.set("product_detail_1", {
            "id": 1,
            "name": "Cached Mug",
            "image_url": "http://example.com/cup.jpg",
            "description": "Perfect for testing reviews.",
            "price": 9.99,
            "is_available": True,
            "average_rating": 5.0
        })
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Cached Mug") # Proves it hit the cache!

        # 4. Perform moderator action to approve/reject a review, which should invalidate the cache
        response = self.client.post("/api/auth/login", json={
            "account_identifier": "moderator",
            "password": "modpassword"
        })
        self.assertEqual(response.status_code, 200)
        mod_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        # Login standard user to submit review
        response = self.client.post("/api/auth/login", json={
            "account_identifier": "testuser",
            "password": "testpassword"
        })
        user_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        
        response = self.client.post("/api/products/1/reviews", headers=user_headers, json={
            "rating": 5,
            "comment": "Super caching test!"
        })
        new_rev_id = response.json()["id"]

        # Moderate it (approve)
        response = self.client.post(f"/api/moderation/reviews/{new_rev_id}/action", headers=mod_headers, json={
            "action": "approve"
        })
        self.assertEqual(response.status_code, 200)

        # Verify that cache is invalidated (should be None)
        self.assertIsNone(cache_instance.get("product_detail_1"))
        self.assertIsNone(cache_instance.get("product_reviews_1"))
        self.assertIsNone(cache_instance.get("products_list"))

        # Fetch product detail again (should get real from DB, name is back to "Test Coffee Cup")
        response = self.client.get("/api/products/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Test Coffee Cup")

if __name__ == "__main__":
    unittest.main()
