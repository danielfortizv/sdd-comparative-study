import os
os.environ["RUN_WORKERS"] = "false"

import sqlite3
import subprocess
import time
import json
import httpx
import pika
import pytest

AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_speckit"
EVENT_NAMESPACE = "stage4.speckit"

# Dynamically resolve pathing depending on where pytest is executed from
if os.path.exists("backend"):
    CWD = "backend"
    DB_IDENTITY = "backend/test_identity_acceptance.db"
    DB_COMMERCE = "backend/test_commerce_acceptance.db"
    DB_REVIEWS = "backend/test_reviews_acceptance.db"
else:
    CWD = "."
    DB_IDENTITY = "test_identity_acceptance.db"
    DB_COMMERCE = "test_commerce_acceptance.db"
    DB_REVIEWS = "test_reviews_acceptance.db"

def kill_processes_on_ports(ports):
    import subprocess
    for port in ports:
        try:
            # Run netstat to find owning PID on Windows
            output = subprocess.check_output(f"netstat -ano | findstr LISTENING | findstr :{port}", shell=True).decode()
            pids = set()
            for line in output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 0:
                        pids.add(int(pid))
            for pid in pids:
                print(f"Killing process {pid} on port {port}...")
                subprocess.call(f"taskkill /F /PID {pid}", shell=True)
        except Exception:
            pass

@pytest.fixture(autouse=True, scope="module")
def cleanup_pre_and_post():
    # 1. Kill any stale processes first to release file locks
    kill_processes_on_ports([18600, 18601, 18602, 18603])
    time.sleep(1)

    # 2. Delete temporary databases if exist
    for f in [DB_IDENTITY, DB_COMMERCE, DB_REVIEWS]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Failed to remove {f}: {e}")
                
    yield
    
    # Post test cleanup: Kill any active subprocesses we started
    kill_processes_on_ports([18600, 18601, 18602, 18603])
    time.sleep(1)
    
    for f in [DB_IDENTITY, DB_COMMERCE, DB_REVIEWS]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Failed to remove {f} post-test: {e}")


def test_acceptance_suite():
    # 1. Purge the queues to ensure clean state
    try:
        connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
        channel = connection.channel()
        
        # Delete and recreate queues cleanly to avoid PreconditionFailed
        try:
            channel.queue_delete(queue=f"{EVENT_NAMESPACE}.commerce.reviews")
        except Exception:
            pass
        try:
            channel.queue_delete(queue=f"{EVENT_NAMESPACE}.commerce.reviews.dlq")
        except Exception:
            pass
            
        channel.exchange_declare(exchange=f"{EVENT_NAMESPACE}.reviews.dlx", exchange_type="direct", durable=True)
        channel.queue_declare(queue=f"{EVENT_NAMESPACE}.commerce.reviews.dlq", durable=True)
        channel.queue_bind(queue=f"{EVENT_NAMESPACE}.commerce.reviews.dlq", exchange=f"{EVENT_NAMESPACE}.reviews.dlx", routing_key="review.moderated.dlq")
        
        channel.exchange_declare(exchange=f"{EVENT_NAMESPACE}.reviews", exchange_type="direct", durable=True)
        channel.queue_declare(
            queue=f"{EVENT_NAMESPACE}.commerce.reviews",
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{EVENT_NAMESPACE}.reviews.dlx",
                "x-dead-letter-routing-key": "review.moderated.dlq"
            }
        )
        channel.queue_bind(queue=f"{EVENT_NAMESPACE}.commerce.reviews", exchange=f"{EVENT_NAMESPACE}.reviews", routing_key="review.moderated")
        
        connection.close()
        print("Pre-test RabbitMQ queue setup and purge successful.")
    except Exception as e:
        print(f"Failed to pre-purge queues: {e}")

    # Set up common env block for uvicorn subprocesses
    base_env = os.environ.copy()
    base_env["IDENTITY_DB_PATH"] = "test_identity_acceptance.db"
    base_env["COMMERCE_DB_PATH"] = "test_commerce_acceptance.db"
    base_env["REVIEWS_DB_PATH"] = "test_reviews_acceptance.db"
    base_env["JWT_SECRET"] = "stage4-super-secret-key-12345678"
    base_env["AMQP_URL"] = AMQP_URL
    base_env["EVENT_NAMESPACE"] = EVENT_NAMESPACE
    base_env["IDENTITY_SERVICE_URL"] = "http://127.0.0.1:18601"
    base_env["COMMERCE_SERVICE_URL"] = "http://127.0.0.1:18602"
    base_env["REVIEWS_SERVICE_URL"] = "http://127.0.0.1:18603"
    base_env["RUN_WORKERS"] = "true"  # Force sub-processes to run background workers!

    processes = {}

    def launch_service(name, module, port, custom_env=None):
        env = custom_env if custom_env else base_env
        p = subprocess.Popen(
            ["python", "-m", "uvicorn", module, "--port", str(port)],
            cwd=CWD,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes[name] = p
        return p

    print("Launching Gateway, Identity, Reviews, and Commerce...")
    launch_service("Identity", "src.services.identity.main:app", 18601)
    launch_service("Reviews", "src.services.reviews.main:app", 18603)
    launch_service("Gateway", "src.services.gateway.main:app", 18600)
    launch_service("Commerce", "src.services.commerce.main:app", 18602)

    # Wait for API gateway to become healthy
    gateway_url = "http://127.0.0.1:18600"
    healthy = False
    for _ in range(15):
        time.sleep(1)
        try:
            resp = httpx.get(f"{gateway_url}/api/products")
            if resp.status_code == 200:
                healthy = True
                break
        except Exception:
            pass

    assert healthy, "Gateway service failed to start or become healthy."
    print("All four services are ONLINE and healthy.")

    # 2. Register customer and sign in via gateway
    register_resp = httpx.post(f"{gateway_url}/api/register", json={"identifier": "alice_acc", "password": "password123"})
    assert register_resp.status_code == 201

    login_resp = httpx.post(f"{gateway_url}/api/signin", json={"identifier": "alice_acc", "password": "password123"})
    assert login_resp.status_code == 200
    alice_token = login_resp.json()["session_token"]

    # 3. Checkout via Gateway HTTP
    checkout_payload = {
        "items": [{"product_id": "prod_004", "quantity": 2}],
        "demonstration_info": {"address": "123 Acceptance Lane", "disclaimer": "Yes"}
    }
    checkout_resp = httpx.post(f"{gateway_url}/api/checkout", headers={"Authorization": f"Bearer {alice_token}"}, json=checkout_payload)
    assert checkout_resp.status_code == 200
    assert "Simulated purchase confirmed" in checkout_resp.json()["message"]
    print("Purchase journey verified.")

    # 4. Access Denial for Moderator endpoints
    # Submit review
    review_payload = {
        "product_id": "prod_004",
        "rating": 5,
        "comment": "Acceptance test review with image",
        "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
    sub_resp = httpx.post(f"{gateway_url}/api/reviews", headers={"Authorization": f"Bearer {alice_token}"}, json=review_payload)
    assert sub_resp.status_code == 201
    review_id = sub_resp.json()["review"]["review_id"]

    # Try to approve with Alice's token (should be 401/403)
    mod_resp = httpx.post(f"{gateway_url}/api/moderation/reviews/{review_id}/status", headers={"Authorization": f"Bearer {alice_token}"}, json={"status": "approved"})
    assert mod_resp.status_code in [401, 403]
    print("Access-denied journey verified.")

    # Get moderator token
    mod_login = httpx.post(f"{gateway_url}/api/signin", json={"identifier": "moderator", "password": "moderator"})
    assert mod_login.status_code == 200
    mod_token = mod_login.json()["session_token"]

    # 5. Stop Commerce service and approve review offline
    print("Stopping Commerce Service only...")
    processes["Commerce"].terminate()
    processes["Commerce"].wait()
    del processes["Commerce"]

    # Approve review while Commerce is offline
    app_resp = httpx.post(f"{gateway_url}/api/moderation/reviews/{review_id}/status", headers={"Authorization": f"Bearer {mod_token}"}, json={"status": "approved"})
    assert app_resp.status_code == 200
    print("Review approved offline.")

    # Verify event is queued in RabbitMQ
    time.sleep(2)
    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    channel = connection.channel()
    method = channel.queue_declare(queue=f"{EVENT_NAMESPACE}.commerce.reviews", passive=True)
    message_count = method.method.message_count
    connection.close()

    assert message_count >= 1, "Review status event was not queued in RabbitMQ."
    print(f"Verified event is queued. Message count: {message_count}")

    # 6. Restart Commerce and prove delivery
    print("Restarting Commerce Service...")
    launch_service("Commerce", "src.services.commerce.main:app", 18602)
    
    # Wait for reviews projection in commerce db to be updated
    delivered = False
    for _ in range(10):
        time.sleep(1)
        try:
            reviews_resp = httpx.get(f"{gateway_url}/api/products/prod_004/reviews")
            if reviews_resp.status_code == 200:
                revs = reviews_resp.json()
                if any(r["review_id"] == review_id for r in revs):
                    delivered = True
                    break
        except Exception:
            pass

    assert delivered, "Queued event was not delivered after Commerce restarted."
    print("Confirmed delivery to commerce projection.")

    # 7. Republish exact event envelope/ID (idempotency check)
    # Read DB to get processed event ID
    conn = sqlite3.connect(DB_COMMERCE)
    cursor = conn.cursor()
    cursor.execute("SELECT event_id FROM processed_events")
    rows = cursor.fetchall()
    conn.close()
    assert len(rows) >= 1
    processed_event_id = rows[0][0]

    # Manually publish duplicate event
    duplicate_envelope = {
        "event_id": processed_event_id,
        "correlation_id": "duplicate-corr-99999",
        "event_type": "review_moderated",
        "timestamp": "2026-11-07T12:00:00Z",
        "payload": {
            "review_id": review_id,
            "product_id": "prod_004",
            "user_id": "alice_acc",
            "rating": 5,
            "comment": "Acceptance test review with image (DUPLICATE EFFECT)",
            "image_base64": "data:image/png;base64,...",
            "status": "approved",
            "created_at": "2026-11-07T11:55:00Z",
        }
    }

    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    channel = connection.channel()
    channel.basic_publish(
        exchange=f"{EVENT_NAMESPACE}.reviews",
        routing_key="review.moderated",
        body=json.dumps(duplicate_envelope),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json"
        )
    )
    connection.close()

    time.sleep(3)
    # Check that comment did not change to the duplicate version
    reviews_resp = httpx.get(f"{gateway_url}/api/products/prod_004/reviews")
    revs = reviews_resp.json()
    matched_rev = [r for r in revs if r["review_id"] == review_id][0]
    assert matched_rev["comment"] == "Acceptance test review with image", "Duplicate event overwrote existing projection!"
    print("Idempotency successfully proven.")

    # 8. Outbox survival of restarts with unavailable AMQP
    print("Stopping Reviews Service to configure unavailable AMQP...")
    processes["Reviews"].terminate()
    processes["Reviews"].wait()
    del processes["Reviews"]

    # Start Reviews with invalid AMQP endpoint
    bad_env = base_env.copy()
    bad_env["AMQP_URL"] = "amqp://ecommerce:stage4-demo@127.0.0.1:9999/invalid_vhost"
    launch_service("Reviews", "src.services.reviews.main:app", 18603, custom_env=bad_env)
    time.sleep(3) # Wait for startup

    # Submit second review as Alice
    review_payload2 = {
        "product_id": "prod_004",
        "rating": 4,
        "comment": "Second review under network partition"
    }
    sub_resp2 = httpx.post(f"{gateway_url}/api/reviews", headers={"Authorization": f"Bearer {alice_token}"}, json=review_payload2)
    assert sub_resp2.status_code == 201
    review_id2 = sub_resp2.json()["review"]["review_id"]

    # Approve second review (fails to publish, but outbox write succeeds transactionally)
    app_resp2 = httpx.post(f"{gateway_url}/api/moderation/reviews/{review_id2}/status", headers={"Authorization": f"Bearer {mod_token}"}, json={"status": "approved"})
    assert app_resp2.status_code == 200

    time.sleep(2)
    # Kill the Reviews service to prove the outbox survives
    print("Killing Reviews Service...")
    processes["Reviews"].terminate()
    processes["Reviews"].wait()
    del processes["Reviews"]

    # Read the sqlite DB directly and assert the event is PENDING
    conn = sqlite3.connect(DB_REVIEWS)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM outbox WHERE payload_json LIKE ?", (f"%{review_id2}%",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "PENDING", f"Outbox event status is {row[0]}, expected PENDING."
    print("Outbox persistence and offline survival proven.")

    # Restart Reviews with standard AMQP URL
    print("Restarting Reviews Service with correct AMQP...")
    launch_service("Reviews", "src.services.reviews.main:app", 18603)

    # Wait and verify that the second review is delivered and shows up in commerce
    recovered = False
    for _ in range(15):
        time.sleep(1)
        try:
            reviews_resp = httpx.get(f"{gateway_url}/api/products/prod_004/reviews")
            if reviews_resp.status_code == 200:
                revs = reviews_resp.json()
                if any(r["review_id"] == review_id2 for r in revs):
                    recovered = True
                    break
        except Exception:
            pass

    assert recovered, "Reviews did not recover and publish outbox messages after AMQP restoration."
    print("AMQP recovery and outbox playback proven.")

    # 9. Poison message DLQ assertion
    print("Publishing poison message...")
    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    channel = connection.channel()
    channel.basic_publish(
        exchange=f"{EVENT_NAMESPACE}.reviews",
        routing_key="review.moderated",
        body=b"this is a poison message that is not valid JSON!",
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json"
        )
    )
    connection.close()

    # Wait for consumer to retry 3 times and move to DLQ
    print("Waiting for consumer to retry and move to DLQ...")
    time.sleep(6)

    # Verify message is in DLQ
    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    channel = connection.channel()
    method, properties, body = channel.basic_get(queue=f"{EVENT_NAMESPACE}.commerce.reviews.dlq", auto_ack=True)
    connection.close()

    assert body is not None, "Poison message was not found in DLQ."
    assert b"poison message" in body, f"Unexpected body in DLQ: {body}"
    print("Poison-message dead-lettering verified successfully.")

    # Terminate all uvicorn background processes
    print("Cleaning up processes...")
    for name, p in processes.items():
        try:
            p.terminate()
            p.wait()
            print(f"Service {name} stopped.")
        except Exception:
            pass
