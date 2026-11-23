import os
import sys
import json
import time
import uuid
import sqlite3
import subprocess
import unittest
import httpx
import pika
from datetime import datetime

class TestStage4Reliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        cls.EVENT_NAMESPACE = f"test_namespace_{cls.unique_id}"
        cls.QUEUE_NAME = f"test_queue_{cls.unique_id}"
        
        # Load AMQP URL
        cls.workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        runtime_path = os.path.join(cls.workspace_dir, "stage4-runtime.json")
        if os.path.exists(runtime_path):
            with open(runtime_path, "r") as f:
                runtime_data = json.load(f)
                cls.AMQP_URL = runtime_data.get("amqp_url")
        else:
            cls.AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_openspec"
            
        print(f"Using AMQP_URL: {cls.AMQP_URL}")
        print(f"Using isolated Event Namespace: {cls.EVENT_NAMESPACE}")
        print(f"Using isolated Queue Name: {cls.QUEUE_NAME}")

        # SQLite database files
        cls.db_identity = "test_identity.db"
        cls.db_commerce = "test_commerce.db"
        cls.db_reviews = "test_reviews.db"
        
        # Clean databases before starting
        for db in [cls.db_identity, cls.db_commerce, cls.db_reviews]:
            if os.path.exists(db):
                try:
                    os.remove(db)
                except Exception:
                    pass

    def setUp(self):
        self.procs = {}
        self.log_files = []
        self.start_counts = {}

    def tearDown(self):
        # Stop all running subprocesses
        for name, proc in list(self.procs.items()):
            if proc and proc.poll() is None:
                print(f"Stopping subprocess {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        # Close log files
        for f in self.log_files:
            try:
                f.close()
            except Exception:
                pass

        # Clean databases
        for db in [self.db_identity, self.db_commerce, self.db_reviews]:
            if os.path.exists(db):
                try:
                    os.remove(db)
                except Exception:
                    pass

    def start_process(self, name, script_path, extra_env=None):
        self.start_counts[name] = self.start_counts.get(name, 0) + 1
        count = self.start_counts[name]
        
        env = os.environ.copy()
        env["IDENTITY_DATABASE_URL"] = f"sqlite:///./{self.db_identity}"
        env["COMMERCE_DATABASE_URL"] = f"sqlite:///./{self.db_commerce}"
        env["REVIEWS_DATABASE_URL"] = f"sqlite:///./{self.db_reviews}"
        
        env["IDENTITY_PORT"] = "19001"
        env["COMMERCE_PORT"] = "19002"
        env["REVIEWS_PORT"] = "19003"
        env["GATEWAY_PORT"] = "19000"
        
        env["IDENTITY_HOST"] = "127.0.0.1"
        env["COMMERCE_HOST"] = "127.0.0.1"
        env["REVIEWS_HOST"] = "127.0.0.1"
        env["GATEWAY_HOST"] = "127.0.0.1"
        
        env["IDENTITY_SERVICE_URL"] = "http://127.0.0.1:19001"
        env["COMMERCE_SERVICE_URL"] = "http://127.0.0.1:19002"
        env["REVIEWS_SERVICE_URL"] = "http://127.0.0.1:19003"
        
        env["AMQP_URL"] = self.AMQP_URL
        env["EVENT_NAMESPACE"] = self.EVENT_NAMESPACE
        env["QUEUE_NAME"] = self.QUEUE_NAME
        
        if extra_env:
            env.update(extra_env)
            
        print(f"Starting {name} (run {count}) as subprocess...")
        
        log_dir = os.path.join(self.workspace_dir, "test_logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        stdout_file = open(os.path.join(log_dir, f"{name}_{count}_{self.unique_id}.log"), "w")
        stderr_file = open(os.path.join(log_dir, f"{name}_{count}_{self.unique_id}_err.log"), "w")
        self.log_files.extend([stdout_file, stderr_file])
        
        p = subprocess.Popen(
            [sys.executable, "-u", script_path],
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True
        )
        self.procs[name] = p
        return p

    def wait_for_service(self, url, timeout=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res = httpx.get(url, timeout=1.0)
                if res.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def test_end_to_end_reliability_and_outbox_recovery(self):
        # 1. Start actual identity, commerce, reviews, and gateway
        self.start_process("identity", "app/identity/main.py")
        self.start_process("commerce", "app/commerce/main.py")
        self.start_process("reviews", "app/reviews/main.py")
        time.sleep(2.0) # wait for them to bind
        self.start_process("gateway", "app/gateway/main.py")
        
        print("Waiting for API Gateway and services to become healthy...")
        self.assertTrue(self.wait_for_service("http://127.0.0.1:19000/health", timeout=15))
        
        # Verify and seed products in commerce DB
        # To bypass seed waiting or ensure DB exists, we wait a moment
        time.sleep(2.0)
        
        # Connect client to Gateway
        client = httpx.Client(base_url="http://127.0.0.1:19000")
        
        # 2. Register a normal user and a moderator
        username = f"user_{uuid.uuid4().hex[:6]}"
        reg_res = client.post("/api/auth/register", json={"account_identifier": username, "password": "password"})
        self.assertEqual(reg_res.status_code, 201)
        
        login_res = client.post("/api/auth/login", json={"account_identifier": username, "password": "password"})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}
        
        # Moderator
        reg_mod = client.post("/api/auth/register", json={"account_identifier": "moderator", "password": "modpassword"})
        login_mod = client.post("/api/auth/login", json={"account_identifier": "moderator", "password": "modpassword"})
        mod_token = login_mod.json()["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}
        
        # 3. Create and moderate an actual review through HTTP
        review_payload = {
            "rating": 5,
            "comment": "Exceptional reliable item!",
            "image_data": None
        }
        submit_res = client.post("/api/products/1/reviews", headers=user_headers, json=review_payload)
        self.assertEqual(submit_res.status_code, 201)
        review_id = submit_res.json()["id"]
        
        mod_res = client.post(f"/api/moderation/reviews/{review_id}/action", headers=mod_headers, json={"action": "approve"})
        self.assertEqual(mod_res.status_code, 200)
        self.assertEqual(mod_res.json()["status"], "approved")
        
        # Assert private cache headers
        self.assertEqual(mod_res.headers.get("Cache-Control"), "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(mod_res.headers.get("Pragma"), "no-cache")
        self.assertEqual(mod_res.headers.get("Expires"), "0")
        
        # Verify the approved review is asynchronously propagated and public on commerce public projection
        review_public = False
        for _ in range(20):
            res_pub = client.get("/api/products/1/reviews")
            if res_pub.status_code == 200:
                reviews = res_pub.json()
                if any(r["id"] == review_id for r in reviews):
                    review_public = True
                    break
            time.sleep(0.5)
        self.assertTrue(review_public, "Review was not asynchronously propagated to public projection.")
        
        # 4. Stop only commerce
        print("Stopping commerce subprocess...")
        comm_proc = self.procs["commerce"]
        comm_proc.terminate()
        comm_proc.wait()
        del self.procs["commerce"]
        
        # Prove gateway reports commerce unhealthy or unreachable
        health_res = client.get("/health")
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(health_res.json()["services"]["commerce"], "unreachable")
        
        # 5. Submit and approve another review while commerce is offline
        review_payload2 = {
            "rating": 4,
            "comment": "Offline accepted review!",
            "image_data": None
        }
        submit_res2 = client.post("/api/products/1/reviews", headers=user_headers, json=review_payload2)
        self.assertEqual(submit_res2.status_code, 201)
        review_id2 = submit_res2.json()["id"]
        
        mod_res2 = client.post(f"/api/moderation/reviews/{review_id2}/action", headers=mod_headers, json={"action": "approve"})
        self.assertEqual(mod_res2.status_code, 200)
        self.assertEqual(mod_res2.json()["status"], "approved")
        
        # 6. Wait for publisher confirmation and verify durable queued message in RabbitMQ
        print("Waiting for publisher confirmation and verifying durable queue message count...")
        conn = pika.BlockingConnection(pika.URLParameters(self.AMQP_URL))
        ch = conn.channel()
        
        # Poll queue message count passive declare
        queue_has_message = False
        for _ in range(20):
            res_decl = ch.queue_declare(queue=self.QUEUE_NAME, passive=True)
            if res_decl.method.message_count >= 1:
                queue_has_message = True
                break
            time.sleep(0.5)
        conn.close()
        
        self.assertTrue(queue_has_message, "No durable message found in the queue while Commerce was offline.")
        
        # 7. Restart commerce and prove the offline accepted review becomes public
        print("Restarting commerce subprocess...")
        self.start_process("commerce", "app/commerce/main.py")
        
        review2_public = False
        for _ in range(20):
            try:
                res_pub2 = client.get("/api/products/1/reviews")
                if res_pub2.status_code == 200:
                    reviews = res_pub2.json()
                    if any(r["id"] == review_id2 for r in reviews):
                        review2_public = True
                        break
            except Exception:
                pass
            time.sleep(0.5)
        self.assertTrue(review2_public, "Offline accepted review did not become public after Commerce restarted.")
        
        # 8. Republish the exact envelope with the same event ID and prove no second effect (idempotency)
        # Fetch the outbox event from database
        db_conn = sqlite3.connect(self.db_reviews)
        cursor = db_conn.cursor()
        cursor.execute("SELECT event_id, correlation_id, payload FROM outbox ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        db_conn.close()
        
        self.assertIsNotNone(row)
        evt_id, corr_id, payload_str = row
        
        # Construct exact envelope
        republish_message = {
            "event_id": evt_id,
            "correlation_id": corr_id,
            "event_type": "review_moderated",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": json.loads(payload_str)
        }
        
        # Re-publish to the exchange manually using pika
        print(f"Republishing exact duplicate event {evt_id}...")
        conn = pika.BlockingConnection(pika.URLParameters(self.AMQP_URL))
        ch = conn.channel()
        ch.basic_publish(
            exchange=self.EVENT_NAMESPACE,
            routing_key='',
            body=json.dumps(republish_message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json',
                message_id=evt_id
            )
        )
        conn.close()
        
        # Wait a moment and check that there are still exactly 2 reviews (no duplicate projection)
        time.sleep(2.0)
        res_pub3 = client.get("/api/products/1/reviews")
        self.assertEqual(res_pub3.status_code, 200)
        reviews_after = res_pub3.json()
        self.assertEqual(len(reviews_after), 2, "Duplicate event caused duplicate projection or unexpected behavior.")
        
        # 9. Prove publisher outbox recovery with only this test's AMQP connection disabled/unavailable
        print("Stopping reviews subprocess...")
        rev_proc = self.procs["reviews"]
        rev_proc.terminate()
        rev_proc.wait()
        del self.procs["reviews"]
        
        # Start reviews with an INVALID AMQP_URL to simulate connection unavailable
        bad_amqp = "amqp://ecommerce:stage4-demo@127.0.0.1:9999/stage4_openspec"
        print("Starting reviews with invalid AMQP_URL...")
        self.start_process("reviews", "app/reviews/main.py", extra_env={"AMQP_URL": bad_amqp})
        time.sleep(2.0)
        
        # Submit and approve third review
        review_payload3 = {
            "rating": 3,
            "comment": "Review accepted during outbox outage!",
            "image_data": None
        }
        submit_res3 = client.post("/api/products/1/reviews", headers=user_headers, json=review_payload3)
        self.assertEqual(submit_res3.status_code, 201)
        review_id3 = submit_res3.json()["id"]
        
        mod_res3 = client.post(f"/api/moderation/reviews/{review_id3}/action", headers=mod_headers, json={"action": "approve"})
        self.assertEqual(mod_res3.status_code, 200)
        
        # Query test_reviews.db and verify outbox entry status is stuck at "pending"
        time.sleep(2.0) # give background worker a moment to attempt and fail
        db_conn = sqlite3.connect(self.db_reviews)
        cursor = db_conn.cursor()
        cursor.execute("SELECT status FROM outbox WHERE event_id IN (SELECT event_id FROM outbox ORDER BY id DESC LIMIT 1)")
        last_status = cursor.fetchone()[0]
        db_conn.close()
        
        self.assertEqual(last_status, "pending", "Outbox message should be stuck in pending status during network outage.")
        
        # Restart reviews with the CORRECT AMQP_URL
        print("Restarting reviews with correct AMQP_URL...")
        rev_proc2 = self.procs["reviews"]
        rev_proc2.terminate()
        rev_proc2.wait()
        del self.procs["reviews"]
        
        self.start_process("reviews", "app/reviews/main.py")
        
        # Verify outbox transitions to "published" and the review becomes public on commerce public projection
        outbox_recovered = False
        for _ in range(30):
            try:
                db_conn = sqlite3.connect(self.db_reviews)
                cursor = db_conn.cursor()
                cursor.execute("SELECT status FROM outbox ORDER BY id DESC LIMIT 1")
                row_status = cursor.fetchone()
                db_conn.close()
                if row_status and row_status[0] == "published":
                    outbox_recovered = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
            
        self.assertTrue(outbox_recovered, "Outbox did not recover and publish pending messages after AMQP URL restored.")
        
        # Verify third review becomes public on commerce
        review3_public = False
        for _ in range(20):
            try:
                res_pub4 = client.get("/api/products/1/reviews")
                if res_pub4.status_code == 200:
                    reviews = res_pub4.json()
                    if any(r["id"] == review_id3 for r in reviews):
                        review3_public = True
                        break
            except Exception:
                pass
            time.sleep(0.5)
        self.assertTrue(review3_public, "Third review did not become public after publisher recovery.")
        
        print("All reliability and recovery integration assertions passed beautifully!")

if __name__ == "__main__":
    unittest.main()
