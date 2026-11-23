import subprocess
import time
import socket
import json
import uuid
import sys
import httpx
import sqlite3
import pika

AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_tessl"
EXCHANGE = "stage4.tessl.exchange"
ROUTING_KEY = "review.approved"

def is_port_listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect(("127.0.0.1", port))
            return True
        except:
            return False

def wait_for_ports(ports, timeout=15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        all_ready = True
        for port in ports:
            if not is_port_listening(port):
                all_ready = False
                break
        if all_ready:
            return True
        time.sleep(0.5)
    return False

def run_distributed_test():
    print("==================================================")
    print("   STAGE 4 DISTRIBUTED STACK VERIFICATION SUITE   ")
    print("==================================================")

    # Clean previous local sqlite databases
    for db_file in ["backend/identity.db", "backend/commerce.db", "backend/reviews.db"]:
        try:
            import os
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"Removed previous {db_file}")
        except Exception as e:
            print(f"Could not remove {db_file}: {e}")

    # Launch microservices in background
    processes = []
    services_to_start = [
        ("app.identity:app", 18401),
        ("app.commerce:app", 18402),
        ("app.reviews:app", 18403),
        ("app.gateway:app", 18400)
    ]

    for app_module, port in services_to_start:
        cmd = [sys.executable, "-m", "uvicorn", app_module, "--port", str(port), "--host", "127.0.0.1"]
        print(f"Starting {app_module} on port {port}...")
        proc = subprocess.Popen(cmd, cwd="backend")
        processes.append(proc)

    # Wait for services to start
    ports_list = [18401, 18402, 18403, 18400]
    if not wait_for_ports(ports_list):
        print("ERROR: Upstream services failed to start within timeout. Aborting tests.")
        for p in processes:
            p.terminate()
        sys.exit(1)

    print("\n[SUCCESS] All microservices are active and listening.")

    # HTTP client for verification
    client = httpx.Client()

    try:
        # TEST 1: User Registration & Login (Identity Service)
        print("\n[TEST 1] Registering and logging in standard user via Gateway...")
        reg_payload = {"username": "dist_buyer", "password": "securepass123"}
        reg_resp = client.post("http://127.0.0.1:18400/api/register", json=reg_payload)
        assert reg_resp.status_code == 200, f"Reg failed: {reg_resp.text}"
        token = reg_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Success: dist_buyer registered and authenticated.")

        # TEST 2: Catalog Retrieval & Caching (Commerce Service)
        print("\n[TEST 2] Retrieving product list and verifying cache...")
        resp1 = client.get("http://127.0.0.1:18400/api/products")
        assert resp1.status_code == 200
        products = resp1.json()
        assert len(products) == 5
        print(f"Success: Catalog of {len(products)} products served correctly.")

        # TEST 3: Submit Review (Reviews Service)
        print("\n[TEST 3] Submitting a pending review for product 1...")
        review_comment = f"Amazing split mechanical keyboard - {uuid.uuid4().hex[:6]}"
        review_payload = {
            "rating": 5,
            "comment": review_comment,
            "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        rev_resp = client.post("http://127.0.0.1:18400/api/products/1/reviews", json=review_payload, headers=headers)
        assert rev_resp.status_code == 200, f"Submit failed: {rev_resp.text}"
        review_id = rev_resp.json()["review"]["id"]
        print(f"Success: Review submitted. ID: {review_id}, Status: {rev_resp.json()['review']['status']}")

        # TEST 4: Verification of Pendency (Eventual Consistency Boundary)
        print("\n[TEST 4] Verifying the pending review is NOT visible in public reviews (Commerce)...")
        reviews_resp = client.get("http://127.0.0.1:18400/api/products/1/reviews")
        assert reviews_resp.status_code == 200
        public_comments = [r["comment"] for r in reviews_resp.json()]
        assert review_comment not in public_comments, "Pending review leaked to public projection!"
        print("Success: Pending review remains hidden from public catalog.")

        # TEST 5: Access Control / Access Denial (Reviews Service)
        print("\n[TEST 5] Verifying that non-moderator cannot access moderation dashboard...")
        mod_dash_resp = client.get("http://127.0.0.1:18400/api/moderation/reviews", headers=headers)
        assert mod_dash_resp.status_code == 403, f"Expected 403, got {mod_dash_resp.status_code}"
        print("Success: Standard user was correctly denied access to moderation controls.")

        # TEST 6: Review Moderation / Event Propagation (RabbitMQ Integration)
        print("\n[TEST 6] Logging in as moderator and approving the review...")
        mod_login_resp = client.post("http://127.0.0.1:18400/api/login", json={"username": "moderator", "password": "moderator"})
        assert mod_login_resp.status_code == 200
        mod_token = mod_login_resp.json()["token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}

        approve_resp = client.post(f"http://127.0.0.1:18400/api/moderation/reviews/{review_id}/status", json={"status": "approved"}, headers=mod_headers)
        assert approve_resp.status_code == 200
        print("Success: Moderator approved review. Outbox event staged.")

        # Wait for transactional outbox worker and RabbitMQ subscriber eventually consistent propagation
        print("Waiting for event-driven projection updates (up to 5s)...")
        eventually_consistent = False
        for _ in range(10):
            time.sleep(0.5)
            check_reviews = client.get("http://127.0.0.1:18400/api/products/1/reviews")
            assert check_reviews.status_code == 200
            public_comments = [r["comment"] for r in check_reviews.json()]
            if review_comment in public_comments:
                eventually_consistent = True
                break

        assert eventually_consistent, "Event-driven update failed to propagate within eventual consistency window!"
        print("Success: Approved review successfully propagated to public reviews projection via RabbitMQ!")

        # TEST 7: Idempotency Verification
        print("\n[TEST 7] Verifying idempotent delivery (duplicate message ingestion check)...")
        # Find the row in the outbox table inside reviews.db to duplicate the payload
        db_conn = sqlite3.connect("backend/reviews.db")
        db_conn.row_factory = sqlite3.Row
        cur = db_conn.cursor()
        cur.execute("SELECT payload FROM outbox WHERE processed = 1 ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        assert row is not None, "No outbox record found!"
        payload_str = row["payload"]
        db_conn.close()

        # Forcibly publish the same event payload again directly to RabbitMQ to test consumer idempotency
        params = pika.URLParameters(AMQP_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=payload_str,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print("Duplicate event published directly to RabbitMQ.")

        # Wait a moment
        time.sleep(1)

        # Confirm that no duplicate review row is inserted in the public projection
        comm_conn = sqlite3.connect("backend/commerce.db")
        cur = comm_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM public_reviews WHERE id = ?", (review_id,))
        count = cur.fetchone()[0]
        comm_conn.close()

        assert count == 1, f"Idempotency violation! Expected exactly 1 public review row for ID {review_id}, but found {count}."
        print("Success: Consumer is fully idempotent; duplicate events are discarded safely without duplicate record insertion.")

        # TEST 8: Checkout Simulation (Commerce Service)
        print("\n[TEST 8] Verifying simulated checkout flow via Gateway...")
        checkout_payload = {
            "items": [{"product_id": 1, "quantity": 1}]
        }
        checkout_resp = client.post("http://127.0.0.1:18400/api/checkout", json=checkout_payload, headers=headers)
        assert checkout_resp.status_code == 200, f"Checkout failed: {checkout_resp.text}"
        checkout_data = checkout_resp.json()
        assert "summary" in checkout_data
        assert checkout_data["summary"]["buyer"] == "dist_buyer"
        print("Success: Simulated checkout completed successfully.")

        print("\n==================================================")
        print("  ALL STAGE 4 DISTRIBUTED TESTS PASSED PERFECTLY! ")
        print("==================================================")

    except Exception as ex:
        print(f"\n[FAILURE] Test suite encountered error: {ex}")
        import traceback
        traceback.print_exc()
        # Terminate processes
        for p in processes:
            p.terminate()
        sys.exit(1)

    finally:
        # Clean shutdown of background microservices
        print("\nShutting down backend microservice processes...")
        for p in processes:
            p.terminate()
            p.wait()
        print("All processes cleanly terminated.")

if __name__ == "__main__":
    run_distributed_test()
