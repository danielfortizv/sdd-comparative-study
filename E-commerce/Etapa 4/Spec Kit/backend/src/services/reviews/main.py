import datetime
import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pika

from ...common.security import get_user_from_header

app = FastAPI(title="Reviews Service", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get("REVIEWS_DB_PATH", "reviews.db")
AMQP_URL = os.environ.get(
    "AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_speckit"
)
EVENT_NAMESPACE = os.environ.get("EVENT_NAMESPACE", "stage4.speckit")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes sqlite database and outbox schemas."""
    with get_db() as conn:
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
        conn.commit()


init_db()


class ReviewSubmitRequest(BaseModel):
    product_id: str
    rating: int
    comment: str
    image_base64: Optional[str] = None


class ReviewStatusUpdateRequest(BaseModel):
    status: str


@app.post("/api/reviews", status_code=status.HTTP_201_CREATED)
def submit_review(payload: ReviewSubmitRequest, current_user: Dict[str, Any] = Depends(get_user_from_header)):
    user_id = current_user["sub"]
    
    # Validate rating
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be an integer between 1 and 5.",
        )
        
    # Validate comment
    comment = payload.comment.strip()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment cannot be empty.",
        )
        
    review_id = str(uuid.uuid4())
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reviews (review_id, product_id, user_id, rating, comment, image_base64, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                payload.product_id,
                user_id,
                payload.rating,
                comment,
                payload.image_base64,
                "pending",
                created_at,
            ),
        )
        conn.commit()
        
    return {
        "message": "Review submitted successfully and is pending moderation.",
        "review": {
            "review_id": review_id,
            "product_id": payload.product_id,
            "user_id": user_id,
            "rating": payload.rating,
            "comment": comment,
            "image_base64": payload.image_base64,
            "status": "pending",
            "created_at": created_at,
        },
    }


@app.get("/api/moderation/reviews")
def get_moderation_reviews(current_user: Dict[str, Any] = Depends(get_user_from_header)):
    if current_user.get("role") != "moderator":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied: Moderator permissions required.",
        )
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
    return [dict(row) for row in rows]


@app.post("/api/moderation/reviews/{review_id}/status")
def update_review_status(
    review_id: str,
    payload: ReviewStatusUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_user_from_header),
):
    if current_user.get("role") != "moderator":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied: Moderator permissions required.",
        )
        
    status_val = payload.status.strip().lower()
    if status_val not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'approved' or 'rejected'.",
        )
        
    with get_db() as conn:
        conn.execute("BEGIN TRANSACTION")
        cursor = conn.cursor()
        
        # Find review
        cursor.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with id '{review_id}' not found.",
            )
            
        review_data = dict(row)
        
        # Update status
        cursor.execute(
            "UPDATE reviews SET status = ? WHERE review_id = ?", (status_val, review_id)
        )
        
        # Build standard versioned JSON event contract
        event_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        event_payload = {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "event_type": "review_moderated",
            "timestamp": timestamp,
            "payload": {
                "review_id": review_data["review_id"],
                "product_id": review_data["product_id"],
                "user_id": review_data["user_id"],
                "rating": review_data["rating"],
                "comment": review_data["comment"],
                "image_base64": review_data["image_base64"],
                "status": status_val,
                "created_at": review_data["created_at"],
            },
        }
        
        # Insert event log to transactional outbox
        cursor.execute(
            """
            INSERT INTO outbox (event_id, event_type, payload_json, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                "review_moderated",
                json.dumps(event_payload),
                "PENDING",
                timestamp,
            ),
        )
        conn.commit()
        
    return {
        "message": f"Review status updated successfully to '{status_val}'.",
        "review": {"review_id": review_id, "status": status_val},
    }


# --- RESILIENT TRANSACTIONAL OUTBOX PUBLISHER THREAD ---

def outbox_publisher_worker():
    """Resilient background worker scanning and publishing outbox events with confirmations."""
    print("Outbox publisher thread started.")
    backoff = 1.0
    
    while True:
        try:
            # Connect to RabbitMQ
            parameters = pika.URLParameters(AMQP_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Enable publisher confirmations
            channel.confirm_delivery()
            
            # Declare direct exchange
            exchange_name = f"{EVENT_NAMESPACE}.reviews"
            channel.exchange_declare(
                exchange=exchange_name, exchange_type="direct", durable=True
            )
            
            # Setup unroutable callback
            unroutable_flag = [False]
            def on_return(ch, method, properties, body):
                print(f"WARNING: Message returned as unroutable! reply_code={method.reply_code}, reply_text={method.reply_text}")
                unroutable_flag[0] = True

            channel.add_on_return_callback(on_return)
            
            print("Successfully connected to RabbitMQ Broker in Outbox worker.")
            backoff = 1.0  # Reset backoff on successful connection
            
            while True:
                # Query pending outbox entries
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM outbox WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 10"
                    )
                    rows = cursor.fetchall()
                    
                if not rows:
                    time.sleep(0.5)
                    continue
                    
                for row in rows:
                    event_id = row["event_id"]
                    payload_json = row["payload_json"]
                    
                    try:
                        unroutable_flag[0] = False
                        # Publish with persistence (delivery_mode=2) and mandatory=True
                        channel.basic_publish(
                            exchange=exchange_name,
                            routing_key="review.moderated",
                            body=payload_json,
                            mandatory=True,
                            properties=pika.BasicProperties(
                                delivery_mode=2,  # make message durable
                                content_type="application/json",
                            ),
                        )
                        
                        if unroutable_flag[0]:
                            raise pika.exceptions.UnroutableError("Message returned as unroutable")
                        
                        # Mark event as SENT in database upon successful confirmation
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE outbox SET status = 'SENT' WHERE event_id = ?",
                                (event_id,),
                            )
                            conn.commit()
                            
                    except (pika.exceptions.UnroutableError, pika.exceptions.AMQPError) as publish_err:
                        print(f"Outbox worker failed to publish event {event_id}: {publish_err}")
                        raise publish_err  # Trigger outer reconnect loop
                        
                time.sleep(0.1)
                
        except Exception as conn_err:
            print(f"Outbox worker connection lost/failed: {conn_err}. Reconnecting in {backoff:.1f}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)


# Start outbox publisher thread
if os.environ.get("RUN_WORKERS", "true").lower() == "true":
    publisher_thread = threading.Thread(target=outbox_publisher_worker, daemon=True)
    publisher_thread.start()
