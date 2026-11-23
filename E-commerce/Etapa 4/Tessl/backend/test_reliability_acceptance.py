import subprocess
import time
import socket
import json
import uuid
import sys
import os
import sqlite3
import pika
import httpx

# Real RabbitMQ configuration from stage4-runtime.json
AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_tessl"

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

def terminate_process_tree(proc):
    """Cleanly terminate a subprocess using OS signals."""
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

def run_acceptance_suite():
    print("==================================================")
    print("   STAGE 4 RELIABILITY & PERSISTENCE ACCEPTANCE   ")
    print("==================================================")

    # 0. Generate unique names for isolation
    unique_id = str(uuid.uuid4())[:8]
    AMQP_EXCHANGE = f"test_exchange_{unique_id}"
    AMQP_QUEUE = f"test_queue_{unique_id}"
    AMQP_ROUTING_KEY = f"test_routing_{unique_id}"

    # Temp DB Paths (absolute paths)
    IDENTITY_DB_FILE = os.path.abspath(f"backend/test_identity_{unique_id}.db")
    COMMERCE_DB_FILE = os.path.abspath(f"backend/test_commerce_{unique_id}.db")
    REVIEWS_DB_FILE = os.path.abspath(f"backend/test_reviews_{unique_id}.db")

    print(f"Isolated Exchange: {AMQP_EXCHANGE}")
    print(f"Isolated Queue: {AMQP_QUEUE}")
    print(f"Isolated Identity DB: {IDENTITY_DB_FILE}")
    print(f"Isolated Commerce DB: {COMMERCE_DB_FILE}")
    print(f"Isolated Reviews DB: {REVIEWS_DB_FILE}")

    # Remove any pre-existing temp databases
    for db in [IDENTITY_DB_FILE, COMMERCE_DB_FILE, REVIEWS_DB_FILE]:
        if os.path.exists(db):
            os.remove(db)

    # Dictionary representing env vars for the services
    common_env = os.environ.copy()
    common_env["IDENTITY_DB_FILE"] = IDENTITY_DB_FILE
    common_env["COMMERCE_DB_FILE"] = COMMERCE_DB_FILE
    common_env["REVIEWS_DB_FILE"] = REVIEWS_DB_FILE
    common_env["AMQP_EXCHANGE"] = AMQP_EXCHANGE
    common_env["AMQP_QUEUE"] = AMQP_QUEUE
    common_env["AMQP_ROUTING_KEY"] = AMQP_ROUTING_KEY

    # Ports
    ports = {
        "identity": 18401,
        "commerce": 18402,
        "reviews": 18403,
        "gateway": 18400
    }

    # Helper to start a microservice
    def start_service(name, port, extra_env=None):
        cmd = [sys.executable, "-m", "uvicorn", f"app.{name}:app", "--port", str(port), "--host", "127.0.0.1"]
        env = common_env.copy()
        if extra_env:
            env.update(extra_env)
        print(f"Starting {name} on port {port}...")
        return subprocess.Popen(cmd, cwd="backend", env=env)

    # Start all services initially
    procs = {}
    procs["identity"] = start_service("identity", ports["identity"])
    procs["commerce"] = start_service("commerce", ports["commerce"])
    procs["reviews"] = start_service("reviews", ports["reviews"])
    procs["gateway"] = start_service("gateway", ports["gateway"])

    # Wait for all to be listening
    if not wait_for_ports(list(ports.values())):
        print("ERROR: Services failed to start.")
        for p in procs.values():
            terminate_process_tree(p)
        sys.exit(1)

    print("[SUCCESS] All services started and listening.")
    client = httpx.Client()

    try:
        # Prerequisites: Register & Login standard user, and moderator
        print("\n--- Registering standard user and moderator ---")
        reg_resp = client.post(f"http://127.0.0.1:{ports['gateway']}/api/register", json={"username": "acc_buyer", "password": "buyerpass123"})
        assert reg_resp.status_code == 200, reg_resp.text
        buyer_token = reg_resp.json()["token"]
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

        mod_login = client.post(f"http://127.0.0.1:{ports['gateway']}/api/login", json={"username": "moderator", "password": "moderator"})
        assert mod_login.status_code == 200
        mod_token = mod_login.json()["token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}
        print("User credentials established successfully.")

        # =====================================================================
        # TEST CASE 1: Stop Commerce only, Approve review while offline, Recovery
        # =====================================================================
        print("\n--- [TEST CASE 1] Stop Commerce only, Approve review while offline, Recovery ---")
        
        # Submit a review for product 1
        review_comment_1 = f"Excellent quality mechanical keycaps - {uuid.uuid4().hex[:6]}"
        rev_payload = {
            "rating": 5,
            "comment": review_comment_1,
            "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        submit_resp = client.post(f"http://127.0.0.1:{ports['gateway']}/api/products/1/reviews", json=rev_payload, headers=buyer_headers)
        assert submit_resp.status_code == 200, submit_resp.text
        review_id_1 = submit_resp.json()["review"]["id"]
        print(f"Review 1 submitted (ID: {review_id_1}) and is pending.")

        # Confirm review is not public yet
        check_pub = client.get(f"http://127.0.0.1:{ports['gateway']}/api/products/1/reviews")
        assert review_comment_1 not in [r["comment"] for r in check_pub.json()]
        print("Confirmed pending review is hidden.")

        # Stop Commerce Service ONLY
        print("Stopping Commerce microservice process tree...")
        terminate_process_tree(procs["commerce"])
        del procs["commerce"]
        time.sleep(1)
        assert not is_port_listening(ports["commerce"]), "Commerce port should be closed!"
        print("Commerce is offline.")

        # Approve review via Gateway while Commerce is offline
        approve_resp = client.post(f"http://127.0.0.1:{ports['gateway']}/api/moderation/reviews/{review_id_1}/status", json={"status": "approved"}, headers=mod_headers)
        assert approve_resp.status_code == 200
        print("Moderator approved review while Commerce was offline.")

        # Verify Outbox row is marked processed = 1 inside reviews.db (meaning reviews successfully published it)
        time.sleep(2)  # Give publisher a moment to publish
        conn = sqlite3.connect(REVIEWS_DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT processed, payload FROM outbox ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        assert row is not None, "No outbox row staged!"
        assert row["processed"] == 1, "Outbox should have marked event processed!"
        print("Verified that Reviews successfully published the event to RabbitMQ.")

        # Inspect RabbitMQ message count (it should be queued in the durable queue)
        params = pika.URLParameters(AMQP_URL)
        mq_conn = pika.BlockingConnection(params)
        mq_channel = mq_conn.channel()
        queue_args = {
            "x-dead-letter-exchange": f"{AMQP_EXCHANGE}.dlx",
            "x-dead-letter-routing-key": "dlq"
        }
        q_declare = mq_channel.queue_declare(queue=AMQP_QUEUE, durable=True, arguments=queue_args)
        msg_count = q_declare.method.message_count
        print(f"RabbitMQ Queue {AMQP_QUEUE} contains {msg_count} queued message(s).")
        mq_conn.close()
        assert msg_count >= 1, "Expected at least 1 message queued in RabbitMQ!"

        # Restart Commerce Service
        print("Restarting Commerce service...")
        procs["commerce"] = start_service("commerce", ports["commerce"])
        assert wait_for_ports([ports["commerce"]]), "Commerce failed to start on recovery!"
        print("Commerce restored.")

        # Wait a moment for the subscriber to process the queued event (Eventual Consistency Recovery)
        print("Waiting for eventual consistency recovery...")
        recovered = False
        for _ in range(10):
            time.sleep(0.5)
            check_pub = client.get(f"http://127.0.0.1:{ports['gateway']}/api/products/1/reviews")
            assert check_pub.status_code == 200
            public_comments = [r["comment"] for r in check_pub.json()]
            if review_comment_1 in public_comments:
                recovered = True
                break

        assert recovered, "Recovery failed: Approved review did not propagate to public projection!"
        print("[SUCCESS] Test Case 1 Passed: Offline recovery succeeded perfectly.")

        # =====================================================================
        # TEST CASE 2: Idempotency (Republish exact event ID)
        # =====================================================================
        print("\n--- [TEST CASE 2] Idempotency (Duplicate message ingestion) ---")
        # Extract the exact payload we processed
        event_payload = json.loads(row["payload"])
        
        # Publish it again directly to AMQP
        print("Directly republishing identical event payload to exchange...")
        mq_conn = pika.BlockingConnection(params)
        mq_channel = mq_conn.channel()
        mq_channel.basic_publish(
            exchange=AMQP_EXCHANGE,
            routing_key="review.approved",
            body=json.dumps(event_payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        mq_conn.close()

        # Wait
        time.sleep(1)

        # Assert no duplicate review in public_reviews database
        comm_conn = sqlite3.connect(COMMERCE_DB_FILE)
        cur = comm_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM public_reviews WHERE id = ?", (review_id_1,))
        count = cur.fetchone()[0]
        comm_conn.close()
        assert count == 1, f"Idempotency violated! Found {count} rows instead of 1."
        print("[SUCCESS] Test Case 2 Passed: Duplicate message discarded safely, idempotence retained.")

        # =====================================================================
        # TEST CASE 3: Unavailable AMQP Endpoint outbox durability & restart survival
        # =====================================================================
        print("\n--- [TEST CASE 3] Outbox durability with unavailable AMQP & Service Restart ---")
        
        # Submit another review
        review_comment_2 = f"Stunning water bottle - {uuid.uuid4().hex[:6]}"
        submit_resp_2 = client.post(f"http://127.0.0.1:{ports['gateway']}/api/products/2/reviews", json={"rating": 5, "comment": review_comment_2}, headers=buyer_headers)
        assert submit_resp_2.status_code == 200
        review_id_2 = submit_resp_2.json()["review"]["id"]
        print(f"Review 2 submitted (ID: {review_id_2}).")

        # Stop Reviews Service
        print("Stopping Reviews service to restart with unavailable AMQP URL...")
        terminate_process_tree(procs["reviews"])
        del procs["reviews"]
        time.sleep(1)

        # Restart Reviews Service with unreachable AMQP endpoint
        bad_amqp_env = {"AMQP_URL": "amqp://ecommerce:stage4-demo@127.0.0.1:9999/stage4_tessl"} # bad port
        procs["reviews"] = start_service("reviews", ports["reviews"], extra_env=bad_amqp_env)
        assert wait_for_ports([ports["reviews"]]), "Reviews failed to restart!"
        print("Reviews restarted with an unreachable AMQP broker.")

        # Moderator approves the review via Gateway
        approve_resp_2 = client.post(f"http://127.0.0.1:{ports['gateway']}/api/moderation/reviews/{review_id_2}/status", json={"status": "approved"}, headers=mod_headers)
        assert approve_resp_2.status_code == 200
        print("Moderator approved review while Reviews was pointing to unreachable AMQP broker.")

        # Verify that in reviews DB, outbox row is staged but remains unprocessed (processed = 0)
        time.sleep(2)
        conn = sqlite3.connect(REVIEWS_DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT processed FROM outbox ORDER BY id DESC LIMIT 1")
        row2 = cur.fetchone()
        conn.close()
        assert row2 is not None
        assert row2["processed"] == 0, "Event should NOT be processed when AMQP is unreachable!"
        print("Confirmed outbox event remains pending (processed = 0).")

        # Simulate service restart: Stop Reviews and restart still with bad AMQP to prove survival
        print("Simulating service restart: Stopping Reviews service...")
        terminate_process_tree(procs["reviews"])
        del procs["reviews"]
        time.sleep(1)

        print("Restarting Reviews service with bad AMQP to prove survival...")
        procs["reviews"] = start_service("reviews", ports["reviews"], extra_env=bad_amqp_env)
        assert wait_for_ports([ports["reviews"]]), "Reviews failed to restart!"

        # Verify event still exists and is unprocessed (durability!)
        conn = sqlite3.connect(REVIEWS_DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT processed FROM outbox WHERE id = (SELECT max(id) FROM outbox)")
        row2_check = cur.fetchone()
        conn.close()
        assert row2_check is not None
        assert row2_check[0] == 0, "Staged outbox event must survive service restart!"
        print("Confirmed pending outbox survived restart and remains unprocessed.")

        # Restore real AMQP! Stop Reviews and start with REAL AMQP_URL
        print("Stopping Reviews and restoring connection to real AMQP broker...")
        terminate_process_tree(procs["reviews"])
        del procs["reviews"]
        time.sleep(1)

        procs["reviews"] = start_service("reviews", ports["reviews"])
        assert wait_for_ports([ports["reviews"]]), "Reviews failed to start with real AMQP!"
        print("Reviews restored with real AMQP.")

        # Wait for eventual consistency propagation
        print("Waiting for outbox to publish and commerce to ingest...")
        delivered = False
        for _ in range(10):
            time.sleep(0.5)
            check_pub = client.get(f"http://127.0.0.1:{ports['gateway']}/api/products/2/reviews")
            assert check_pub.status_code == 200
            public_comments = [r["comment"] for r in check_pub.json()]
            if review_comment_2 in public_comments:
                delivered = True
                break

        assert delivered, "Pending event failed to publish and deliver once AMQP was restored!"
        print("Verified review successfully propagated to Commerce projection.")

        # Verify outbox is now marked processed = 1
        conn = sqlite3.connect(REVIEWS_DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT processed FROM outbox WHERE id = (SELECT max(id) FROM outbox)")
        row2_final = cur.fetchone()
        conn.close()
        assert row2_final is not None
        assert row2_final[0] == 1, "Outbox event should now be marked processed = 1!"
        print("Confirmed outbox row is now processed = 1 in Reviews DB.")
        print("[SUCCESS] Test Case 3 Passed: Pending outbox survived restarts and delivered successfully.")

        # =====================================================================
        # TEST CASE 4: Poison-message DLQ assertion
        # =====================================================================
        print("\n--- [TEST CASE 4] Poison-message DLQ assertion ---")
        
        # Publish a poison message directly to the commerce queue
        # This has event_type = review.approved but lacks required fields in payload (it's completely malformed)
        poison_msg = {
            "type": "review.approved",
            "payload": {
                "review_id": "NOT_AN_INT", # bad types / malformed payload
                "product_id": 1,
                "rating": "poison"
            }
        }
        
        print(f"Publishing poison message directly to queue {AMQP_QUEUE}...")
        mq_conn = pika.BlockingConnection(params)
        mq_channel = mq_conn.channel()
        mq_channel.basic_publish(
            exchange=AMQP_EXCHANGE,
            routing_key="review.approved",
            body=json.dumps(poison_msg),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        mq_conn.close()

        # Wait for bounded retries to execute and fail
        print("Waiting for consumer callback to run bounded retries (3 attempts) and DLQ the message...")
        time.sleep(5)  # Max 3 attempts, with 1s sleep in between

        # Check DLQ to assert message is present
        print("Consuming from DLQ to assert poison message arrived...")
        mq_conn = pika.BlockingConnection(params)
        mq_channel = mq_conn.channel()
        dlq_name = f"{AMQP_QUEUE}.dlq"
        method_frame, header_frame, body = mq_channel.basic_get(queue=dlq_name, auto_ack=True)
        mq_conn.close()

        assert method_frame is not None, "Poison message was not dead-lettered!"
        dlq_msg = json.loads(body.decode('utf-8'))
        print(f"DLQ Message received: {dlq_msg}")
        assert dlq_msg["type"] == "review.approved"
        assert dlq_msg["payload"]["review_id"] == "NOT_AN_INT"
        print("[SUCCESS] Test Case 4 Passed: Poison-message DLQ assertion succeeded.")

        # =====================================================================
        # TEST CASE 5: Terminal-state Contract (Moderator Rejections)
        # =====================================================================
        print("\n--- [TEST CASE 5] Terminal-state contract (moderation rejection) ---")
        
        # 1. Create a review, approve it, verify public visibility
        review_comment_5 = f"Cool headphones - {uuid.uuid4().hex[:6]}"
        submit_resp_5 = client.post(f"http://127.0.0.1:{ports['gateway']}/api/products/3/reviews", json={"rating": 5, "comment": review_comment_5}, headers=buyer_headers)
        assert submit_resp_5.status_code == 200
        review_id_5 = submit_resp_5.json()["review"]["id"]
        
        # Moderator approves it
        approve_resp_5 = client.post(f"http://127.0.0.1:{ports['gateway']}/api/moderation/reviews/{review_id_5}/status", json={"status": "approved"}, headers=mod_headers)
        assert approve_resp_5.status_code == 200

        # Wait for propagation
        time.sleep(2)
        check_pub_5 = client.get(f"http://127.0.0.1:{ports['gateway']}/api/products/3/reviews")
        assert review_comment_5 in [r["comment"] for r in check_pub_5.json()], "Should be in public projection!"
        print("Confirmed approved review is visible in public projection.")

        # 2. Moderator rejects the already approved review!
        reject_resp_5 = client.post(f"http://127.0.0.1:{ports['gateway']}/api/moderation/reviews/{review_id_5}/status", json={"status": "rejected"}, headers=mod_headers)
        assert reject_resp_5.status_code == 200
        print("Moderator successfully rejected the already approved review.")

        # Wait for propagation of the rejection event (terminal-state contract)
        print("Waiting for rejection event to propagate...")
        time.sleep(2)
        check_pub_5_after = client.get(f"http://127.0.0.1:{ports['gateway']}/api/products/3/reviews")
        assert review_comment_5 not in [r["comment"] for r in check_pub_5_after.json()], "Rejected review is still visible in public projection!"
        print("Confirmed rejected review was successfully removed from public projection!")
        print("[SUCCESS] Test Case 5 Passed: Terminal-state contract verified successfully.")

        # =====================================================================
        # TEST CASE 6: Normal launcher stop/start persistence check
        # =====================================================================
        print("\n--- [TEST CASE 6] Normal launcher stop/start persistence check ---")
        
        # Shut down current test microservices so they don't block ports
        print("Stopping temp acceptance services...")
        for p in procs.values():
            terminate_process_tree(p)
        procs.clear()
        time.sleep(2)

        # Clear standard databases if they exist to start fresh
        for db in ["backend/identity.db", "backend/commerce.db", "backend/reviews.db"]:
            if os.path.exists(db):
                try:
                    os.remove(db)
                except:
                    pass

        # Run Start-Services.ps1
        print("Running Start-Services.ps1...")
        p_start = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ".\\Start-Services.ps1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = p_start.communicate()
        print("Start-Services Output:")
        print(stdout)
        assert p_start.returncode == 0, f"Start-Services failed! {stderr}"

        # Confirm services started
        assert wait_for_ports([18400, 18401, 18402, 18403, 18500]), "Normal launcher ports failed to start!"

        # Register a unique user under this normal stack
        print("Registering a user 'persist_user' in the normal running stack...")
        reg_normal = client.post("http://127.0.0.1:18400/api/register", json={"username": "persist_user", "password": "persistpass123"})
        assert reg_normal.status_code == 200, reg_normal.text
        print("User registered successfully in normal running stack.")

        # Run Stop-Services.ps1
        print("Running Stop-Services.ps1...")
        p_stop = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ".\\Stop-Services.ps1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout_stop, stderr_stop = p_stop.communicate()
        print("Stop-Services Output:")
        print(stdout_stop)
        assert p_stop.returncode == 0, f"Stop-Services failed! {stderr_stop}"
        time.sleep(2)

        # Confirm services stopped and ports closed
        for port in [18400, 18401, 18402, 18403, 18500]:
            assert not is_port_listening(port), f"Port {port} should have stopped!"
        print("All microservices are verified offline.")

        # Run Start-Services.ps1 again
        print("Running Start-Services.ps1 again...")
        p_start_2 = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ".\\Start-Services.ps1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout_2, stderr_2 = p_start_2.communicate()
        assert p_start_2.returncode == 0, f"Start-Services 2 failed! {stderr_2}"
        
        assert wait_for_ports([18400, 18401, 18402, 18403, 18500]), "Services failed to start on second launch!"

        # Attempt to login 'persist_user'. If DBs are preserved, login should succeed!
        print("Attempting login of 'persist_user' to prove store persistence...")
        login_normal = client.post("http://127.0.0.1:18400/api/login", json={"username": "persist_user", "password": "persistpass123"})
        
        # Stop services first so we don't leave them running before assertion check
        print("Stopping standard microservices stack...")
        p_stop_final = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ".\\Stop-Services.ps1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p_stop_final.communicate()
        
        assert login_normal.status_code == 200, f"Store was destroyed! Login failed: {login_normal.text}"
        print("[SUCCESS] Test Case 6 Passed: Stores correctly preserved across start/stop cycles!")

        print("\n==================================================")
        print("  ALL RELIABILITY ACCEPTANCE TESTS PASSED PERFECTLY!")
        print("==================================================")

    except Exception as ex:
        print(f"\n[FAILURE] Acceptance suite encountered error: {ex}")
        import traceback
        traceback.print_exc()
        # Clean shutdown of all running subprocesses
        for p in procs.values():
            terminate_process_tree(p)
        # Attempt standard stop
        p_stop = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ".\\Stop-Services.ps1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p_stop.communicate()
        sys.exit(1)
    finally:
        # Clean temp DB files
        print("\nCleaning up temporary database files...")
        for db in [IDENTITY_DB_FILE, COMMERCE_DB_FILE, REVIEWS_DB_FILE]:
            if os.path.exists(db):
                try:
                    os.remove(db)
                    print(f"Deleted {db}")
                except Exception as e:
                    print(f"Warning: Could not delete {db}: {e}")

if __name__ == "__main__":
    run_acceptance_suite()
