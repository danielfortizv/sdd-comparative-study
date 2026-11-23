import sqlite3
import datetime
import json
import threading
import time
import uuid
import httpx
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
import pika
from app.models import ReviewCreateSchema, ReviewStatusUpdateSchema

import os

DB_FILE = os.getenv("REVIEWS_DB_FILE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reviews.db")))
AMQP_URL = os.getenv("AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_tessl")
IDENTITY_INTERNAL_URL = os.getenv("IDENTITY_INTERNAL_URL", "http://127.0.0.1:18401")
EXCHANGE = os.getenv("AMQP_EXCHANGE", "stage4.tessl.exchange")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "review.approved")
COMMERCE_QUEUE = os.getenv("AMQP_QUEUE", "commerce.review_projection_queue")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

app = FastAPI(title="Reviews Service", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REVIEWS_SEED = [
    {
        "id": 1,
        "product_id": 1,
        "rating": 5,
        "comment": "Absolutely love this keyboard! The split layout takes a few days to get used to, but my wrist pain has completely disappeared. Highly recommended!",
        "image_base64": None,
        "status": "approved",
        "username": "keyboard_enthusiast",
        "created_at": "2026-11-01 10:30:00"
    },
    {
        "id": 2,
        "product_id": 1,
        "rating": 4,
        "comment": "Very tactile and responsive. Build quality is solid. One star off because the spacebar was a bit squeaky out of the box.",
        "image_base64": None,
        "status": "approved",
        "username": "code_ninja",
        "created_at": "2026-11-03 14:15:00"
    },
    {
        "id": 3,
        "product_id": 2,
        "rating": 5,
        "comment": "Best travel mouse ever. Battery life is incredible and fits perfectly in my hand.",
        "image_base64": None,
        "status": "approved",
        "username": "digital_nomad",
        "created_at": "2026-11-05 09:00:00"
    },
    {
        "id": 4,
        "product_id": 3,
        "rating": 5,
        "comment": "Outstanding noise cancelling. I can finally work in peace at busy coffee shops.",
        "image_base64": None,
        "status": "pending",
        "username": "focus_seeker",
        "created_at": "2026-11-06 11:20:00"
    }
]

def outbox_publisher_loop():
    print("[Outbox Worker] Thread started.")
    while True:
        try:
            params = pika.URLParameters(AMQP_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            # Enable publisher confirmations
            channel.confirm_delivery()
            
            # 1. Declare exchange
            channel.exchange_declare(exchange=EXCHANGE, exchange_type='direct', durable=True)
            
            # 2. Declare and bind the commerce queue to guarantee event routing even if commerce starts late.
            # Configure exact matching Dead-Letter Queue (DLQ) topology arguments.
            dlx_name = EXCHANGE + ".dlx"
            dlq_name = COMMERCE_QUEUE + ".dlq"
            channel.exchange_declare(exchange=dlx_name, exchange_type='direct', durable=True)
            channel.queue_declare(queue=dlq_name, durable=True)
            channel.queue_bind(queue=dlq_name, exchange=dlx_name, routing_key="dlq")

            queue_args = {
                "x-dead-letter-exchange": dlx_name,
                "x-dead-letter-routing-key": "dlq"
            }
            channel.queue_declare(queue=COMMERCE_QUEUE, durable=True, arguments=queue_args)
            channel.queue_bind(queue=COMMERCE_QUEUE, exchange=EXCHANGE, routing_key="review.approved")
            channel.queue_bind(queue=COMMERCE_QUEUE, exchange=EXCHANGE, routing_key="review.rejected")
            
            print("[Outbox Worker] Connected to RabbitMQ with queue bind guarantees.")
            
            while True:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT id, event_type, payload FROM outbox WHERE processed = 0 ORDER BY id ASC")
                    rows = cur.fetchall()
                
                if not rows:
                    time.sleep(1)
                    continue
                
                for row in rows:
                    event_id = row["id"]
                    event_type = row["event_type"]
                    payload_str = row["payload"]
                    
                    try:
                        # Publish with mandatory=True and use event_type as routing key
                        channel.basic_publish(
                            exchange=EXCHANGE,
                            routing_key=event_type,
                            body=payload_str,
                            mandatory=True,
                            properties=pika.BasicProperties(
                                delivery_mode=2,  # persistent message
                                content_type='application/json'
                            )
                        )
                        with get_db() as conn:
                            conn.execute("UPDATE outbox SET processed = 1 WHERE id = ?", (event_id,))
                            conn.commit()
                        print(f"[Outbox Worker] Published event ID {event_id} of type {event_type} successfully.")
                    except pika.exceptions.UnroutableError:
                        print(f"[Outbox Worker] Event ID {event_id} was unroutable. Retaining in outbox.")
                        time.sleep(1)
                    except Exception as ex:
                        print(f"[Outbox Worker] Error publishing Event ID {event_id}: {ex}")
                        raise ex  # reconnect
                
                time.sleep(1)
                
        except Exception as e:
            print(f"[Outbox Worker] RabbitMQ connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

@app.on_event("startup")
def startup_event():
    # 1. Initialize SQLite Database
    with get_db() as conn:
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
        conn.commit()

    # 2. Seed default reviews
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reviews")
        if cur.fetchone()[0] == 0:
            for r in REVIEWS_SEED:
                conn.execute(
                    "INSERT INTO reviews (id, product_id, rating, comment, image_base64, status, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["product_id"], r["rating"], r["comment"], r["image_base64"], r["status"], r["username"], r["created_at"])
                )
            conn.commit()

    # 3. Start background publisher thread
    worker_thread = threading.Thread(target=outbox_publisher_loop, daemon=True)
    worker_thread.start()

async def verify_internal_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or missing authentication token"
        )
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{IDENTITY_INTERNAL_URL}/api/internal/verify-token", headers={"Authorization": authorization})
            if resp.status_code != 200:
                # Propagate exact unauthorized message
                detail_msg = resp.json().get("detail", "Session inactive or missing authentication token")
                raise HTTPException(status_code=resp.status_code, detail=detail_msg)
            return resp.json()
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth service unreachable"
            )

@app.post("/api/products/{id}/reviews")
async def create_product_review(id: int, payload: ReviewCreateSchema, authorization: str | None = Header(None)):
    user_info = await verify_internal_token(authorization)
    username = user_info["username"]

    # Image validation (size and format check)
    if payload.image_base64:
        # Simple local file check: check size
        # data:image/png;base64,iVBORw...
        if len(payload.image_base64) > 2 * 1024 * 1024 * 1.33: # Approx 2MB in base64
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attached image exceeds the maximum size limit of 2MB."
            )
        if not payload.image_base64.startswith("data:image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image format. Only JPEG, PNG, and GIF are allowed."
            )

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reviews (product_id, rating, comment, image_base64, status, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, payload.rating, payload.comment, payload.image_base64, "pending", username, created_at)
        )
        new_review_id = cur.lastrowid
        conn.commit()

        # Fetch the newly created review to return
        cur.execute("SELECT * FROM reviews WHERE id = ?", (new_review_id,))
        new_review = dict(cur.fetchone())

    return {
        "message": "Review submitted successfully and is currently pending moderation.",
        "review": new_review
    }

@app.get("/api/moderation/reviews")
async def get_all_reviews_for_moderation(authorization: str | None = Header(None)):
    user_info = await verify_internal_token(authorization)
    if not user_info.get("is_moderator", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the 'moderator' user can access moderation APIs."
        )

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reviews ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

@app.post("/api/moderation/reviews/{id}/status")
async def update_review_status(id: int, payload: ReviewStatusUpdateSchema, authorization: str | None = Header(None)):
    user_info = await verify_internal_token(authorization)
    if not user_info.get("is_moderator", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the 'moderator' user can access moderation APIs."
        )

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reviews WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {id} was not found"
            )
        
        # 1. Update review status
        conn.execute("UPDATE reviews SET status = ? WHERE id = ?", (payload.status, id))
        
        # 2. Transactionally append to outbox if approved or rejected
        if payload.status == "approved":
            event_payload = {
                "version": "1.0",
                "event_id": str(uuid.uuid4()),
                "correlation_id": str(uuid.uuid4()),
                "type": "review.approved",
                "event_type": "review.approved",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "payload": {
                    "review_id": id,
                    "product_id": row["product_id"],
                    "rating": row["rating"],
                    "comment": row["comment"],
                    "image_base64": row["image_base64"],
                    "username": row["username"],
                    "created_at": row["created_at"]
                }
            }
            conn.execute(
                "INSERT INTO outbox (event_type, payload, processed, created_at) VALUES (?, ?, ?, ?)",
                ("review.approved", json.dumps(event_payload), 0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        elif payload.status == "rejected":
            event_payload = {
                "version": "1.0",
                "event_id": str(uuid.uuid4()),
                "correlation_id": str(uuid.uuid4()),
                "type": "review.rejected",
                "event_type": "review.rejected",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "payload": {
                    "review_id": id,
                    "product_id": row["product_id"]
                }
            }
            conn.execute(
                "INSERT INTO outbox (event_type, payload, processed, created_at) VALUES (?, ?, ?, ?)",
                ("review.rejected", json.dumps(event_payload), 0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

        conn.commit()

        # Fetch updated review details
        cur.execute("SELECT * FROM reviews WHERE id = ?", (id,))
        updated_review = dict(cur.fetchone())

    return {
        "message": f"Review status updated to '{payload.status}' successfully.",
        "review": updated_review
    }
