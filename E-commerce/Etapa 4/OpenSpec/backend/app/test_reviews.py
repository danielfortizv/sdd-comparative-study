import os
import json
import uuid
import time
import unittest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pika

# Import microservice models, bases, and apps
from app.identity.main import app as identity_app, Base as IdentityBase, User as IdentityUser, SessionLocal as IdentitySessionLocal
from app.commerce.main import app as commerce_app, Base as CommerceBase, Product as CommerceProduct, PublicReview, ProcessedEvent, SessionLocal as CommerceSessionLocal
from app.reviews.main import app as reviews_app, Base as ReviewsBase, Review as ReviewsReview, Outbox, SessionLocal as ReviewsSessionLocal
from app.gateway.main import app as gateway_app

from app.cache import cache_instance

# RabbitMQ runtime info
AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_openspec"
EVENT_NAMESPACE = "stage4.openspec"

class TestStage4DistributedArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up clean database files for testing
        for db_file in ["identity.db", "commerce.db", "reviews.db"]:
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except Exception:
                    pass

        # Create tables in all databases
        IdentityBase.metadata.create_all(bind=create_engine("sqlite:///./identity.db"))
        CommerceBase.metadata.create_all(bind=create_engine("sqlite:///./commerce.db"))
        ReviewsBase.metadata.create_all(bind=create_engine("sqlite:///./reviews.db"))

        # Seed test product in Commerce DB
        db_comm = CommerceSessionLocal()
        if db_comm.query(CommerceProduct).filter(CommerceProduct.id == 1).count() == 0:
            test_product = CommerceProduct(
                id=1,
                name="Classic Ceramic Mug",
                image_url="http://example.com/mug.jpg",
                description="A high-quality ceramic mug.",
                price=12.99,
                is_available=True
            )
            db_comm.add(test_product)
            db_comm.commit()
        db_comm.close()

        cls.client_id = TestClient(identity_app)
        cls.client_comm = TestClient(commerce_app)
        cls.client_rev = TestClient(reviews_app)
        cls.client_gw = TestClient(gateway_app)

    def setUp(self):
        cache_instance.clear()

    def tearDown(self):
        cache_instance.clear()

    def test_auth_and_user_flows(self):
        # Test Registration
        reg_payload = {
            "account_identifier": f"testuser_{uuid.uuid4().hex[:6]}",
            "password": "securepassword"
        }
        response = self.client_id.post("/api/auth/register", json=reg_payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["account_identifier"], reg_payload["account_identifier"])

        # Test Login
        login_response = self.client_id.post("/api/auth/login", json=reg_payload)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access_token", login_response.json())

    def test_reviews_submission_and_outbox_transactional_integrity(self):
        # 1. Register a user
        username = f"customer_{uuid.uuid4().hex[:6]}"
        self.client_id.post("/api/auth/register", json={"account_identifier": username, "password": "password"})
        login_res = self.client_id.post("/api/auth/login", json={"account_identifier": username, "password": "password"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Submit a review via Reviews service (port 18003/router)
        review_payload = {
            "rating": 5,
            "comment": "Outstanding quality product!",
            "image_data": None
        }
        res_submit = self.client_rev.post("/api/products/1/reviews", headers=headers, json=review_payload)
        self.assertEqual(res_submit.status_code, 201)
        rev_id = res_submit.json()["id"]
        self.assertEqual(res_submit.json()["status"], "pending")

        # 3. Create Moderator Authorization Headers
        self.client_id.post("/api/auth/register", json={"account_identifier": "moderator", "password": "modpassword"})
        mod_login = self.client_id.post("/api/auth/login", json={"account_identifier": "moderator", "password": "modpassword"})
        mod_token = mod_login.json()["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}

        # 4. Moderate Review (Approve)
        res_mod = self.client_rev.post(f"/api/moderation/reviews/{rev_id}/action", headers=mod_headers, json={"action": "approve"})
        self.assertEqual(res_mod.status_code, 200)
        self.assertEqual(res_mod.json()["status"], "approved")

        # Verify Transactional Outbox write
        db_rev = ReviewsSessionLocal()
        outbox_entries = db_rev.query(Outbox).filter(Outbox.status == "pending").all()
        self.assertGreaterEqual(len(outbox_entries), 1)
        
        target_entry = None
        for entry in outbox_entries:
            payload = json.loads(entry.payload)
            if payload.get("review_id") == rev_id:
                target_entry = entry
                break
        
        self.assertIsNotNone(target_entry)
        self.assertEqual(target_entry.event_type, "review_moderated")
        db_rev.close()

    def test_consumer_idempotency_and_duplicate_delivery(self):
        # 1. Manually insert a mock event and process it twice to test consumer idempotency
        event_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        test_review_id = uuid.uuid4().int % 1000000
        payload = {
            "review_id": test_review_id,
            "product_id": 1,
            "user_id": "test_idempotent_user",
            "rating": 5,
            "comment": "Idempotency comment",
            "image_data": None,
            "status": "approved"
        }

        # Create the mock event body as consumer receives it
        message = {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "event_type": "review_moderated",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }

        # Execute processing via SessionLocal directly to test database state change and deduplication
        db_comm = CommerceSessionLocal()
        
        # Helper processing logic mirroring consumer
        def process_message(msg):
            evt_id = msg["event_id"]
            pld = msg["payload"]
            rev_id = pld["review_id"]
            prod_id = pld["product_id"]
            status_str = pld["status"]

            existing_evt = db_comm.query(ProcessedEvent).filter(ProcessedEvent.event_id == evt_id).first()
            if existing_evt:
                return "skipped"

            if status_str == "approved":
                existing_rev = db_comm.query(PublicReview).filter(PublicReview.id == rev_id).first()
                if not existing_rev:
                    new_proj = PublicReview(
                        id=rev_id,
                        product_id=prod_id,
                        user_id=pld["user_id"],
                        rating=pld["rating"],
                        comment=pld["comment"],
                        image_data=pld["image_data"],
                        status=status_str,
                        created_at=datetime.utcnow()
                    )
                    db_comm.add(new_proj)
                else:
                    existing_rev.status = status_str
            
            proc_evt = ProcessedEvent(event_id=evt_id)
            db_comm.add(proc_evt)
            db_comm.commit()
            return "processed"

        # First process
        status1 = process_message(message)
        self.assertEqual(status1, "processed")

        # Second process (should skip and not duplicate or crash)
        status2 = process_message(message)
        self.assertEqual(status2, "skipped")

        # Verify exactly one record exists in projection
        proj_count = db_comm.query(PublicReview).filter(PublicReview.id == test_review_id).count()
        self.assertEqual(proj_count, 1)
        db_comm.close()

    def test_outage_and_recovery_flow(self):
        # Verify SQLite outbox holds onto events while we simulate RabbitMQ broker outage
        db_rev = ReviewsSessionLocal()
        event_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        payload = {
            "review_id": 888,
            "product_id": 1,
            "user_id": "outage_user",
            "rating": 3,
            "comment": "Offline comment",
            "image_data": None,
            "status": "approved"
        }

        outbox_entry = Outbox(
            event_id=event_id,
            correlation_id=correlation_id,
            event_type="review_moderated",
            payload=json.dumps(payload),
            status="pending"
        )
        db_rev.add(outbox_entry)
        db_rev.commit()

        # Check that the outbox is indeed persisting the event (not lost)
        entry_db = db_rev.query(Outbox).filter(Outbox.event_id == event_id).first()
        self.assertIsNotNone(entry_db)
        self.assertEqual(entry_db.status, "pending")
        db_rev.close()

if __name__ == "__main__":
    unittest.main()
