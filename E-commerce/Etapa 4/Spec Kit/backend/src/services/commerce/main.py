import copy
import datetime
import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime as dt, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pika

from ...common.security import get_user_from_header

app = FastAPI(title="Commerce Service", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get("COMMERCE_DB_PATH", "commerce.db")
AMQP_URL = os.environ.get(
    "AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_speckit"
)
EVENT_NAMESPACE = os.environ.get("EVENT_NAMESPACE", "stage4.speckit")


# --- THREAD-SAFE RESPONSE CACHE IMPLEMENTATION ---

class ResponseCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if dt.now(timezone.utc) > entry["expires_at"]:
                del self._cache[key]
                return None
            return entry["content"]

    def set(self, key: str, content: Any, ttl_seconds: int = 60) -> dt:
        expires_at = dt.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        cached_content = copy.deepcopy(content)
        with self._lock:
            self._cache[key] = {
                "content": cached_content,
                "expires_at": expires_at
            }
        return expires_at

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


response_cache = ResponseCache()


# --- DATABASE SETUP ---

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes commerce tables and seeds products from catalog.json."""
    with get_db() as conn:
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
        conn.commit()
        
        # Seed catalog products if not exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            catalog_path = os.path.join(current_dir, "..", "..", "data", "catalog.json")
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    products_list = json.load(f)
                for p in products_list:
                    cursor.execute(
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
                print(f"Successfully seeded {len(products_list)} products into commerce database.")
            except Exception as e:
                print(f"Error seeding products from catalog.json: {e}")


init_db()


# --- REQUEST SCHEMAS ---

class CheckoutItem(BaseModel):
    product_id: str
    quantity: int


class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    demonstration_info: Dict[str, Any]


# --- ROUTES ---

@app.get("/api/products")
def get_products():
    cache_key = "products_catalog"
    cached = response_cache.get(cache_key)
    if cached is not None:
        return cached
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        
    products = [dict(row) for row in rows]
    response_cache.set(cache_key, products, ttl_seconds=60)
    return products


@app.get("/api/products/{product_id}/reviews")
def get_product_reviews(product_id: str):
    cache_key = f"reviews_{product_id}"
    cached = response_cache.get(cache_key)
    if cached is not None:
        return cached
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM product_reviews WHERE product_id = ? ORDER BY created_at DESC",
            (product_id,),
        )
        rows = cursor.fetchall()
        
    reviews = [dict(row) for row in rows]
    response_cache.set(cache_key, reviews, ttl_seconds=60)
    return reviews


@app.post("/api/checkout")
def checkout(payload: CheckoutRequest, current_user: Dict[str, Any] = Depends(get_user_from_header)):
    user_id = current_user["sub"]
    
    # Cart validation
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout blocked: shopping cart is empty.",
        )
        
    # Load products for validation
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        products_by_id = {row["product_id"]: dict(row) for row in cursor.fetchall()}
        
    summary_items = []
    accumulated_total = 0.0
    
    for item in payload.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quantity '{item.quantity}' for product '{item.product_id}'.",
            )
            
        if item.product_id not in products_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{item.product_id}' not found in catalog.",
            )
            
        prod_info = products_by_id[item.product_id]
        price = float(prod_info["price"])
        subtotal = round(price * item.quantity, 2)
        accumulated_total += subtotal
        
        summary_items.append(
            {
                "product_id": item.product_id,
                "name": prod_info["name"],
                "quantity": item.quantity,
                "unit_price": price,
                "subtotal": subtotal,
            }
        )
        
    accumulated_total = round(accumulated_total, 2)
    
    # Info validation
    if not payload.demonstration_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout blocked: Please fill in the minimum demonstration details.",
        )
        
    for k, v in payload.demonstration_info.items():
        if not str(v).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Checkout blocked: Demonstration field '{k}' cannot be empty.",
            )
            
    order_id = str(uuid.uuid4())
    created_at = dt.now(timezone.utc).isoformat()
    
    # Persist order log
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO orders (order_id, user_id, items_json, accumulated_total, demonstration_info_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                user_id,
                json.dumps([item.dict() for item in payload.items]),
                accumulated_total,
                json.dumps(payload.demonstration_info),
                created_at,
            ),
        )
        conn.commit()
        
    disclaimer_msg = (
        "Simulated purchase confirmed! No real payment gateway was contacted, "
        "no real inventory was reserved, and no actual charge has been made. "
        "This is an academic demonstration."
    )
    
    return {
        "message": disclaimer_msg,
        "purchase_summary": {
            "items": summary_items,
            "accumulated_total": accumulated_total,
        },
    }


# --- RESILIENT EVENT CONSUMER BACKGROUND THREAD ---

def events_consumer_worker():
    """Resilient background consumer subscribing to reviews exchange and executing manual ACKs."""
    print("Events consumer thread started.")
    backoff = 1.0
    
    while True:
        try:
            parameters = pika.URLParameters(AMQP_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Declare exchange
            exchange_name = f"{EVENT_NAMESPACE}.reviews"
            channel.exchange_declare(
                exchange=exchange_name, exchange_type="direct", durable=True
            )
            
            # Declare DLX
            dlx_name = f"{EVENT_NAMESPACE}.reviews.dlx"
            channel.exchange_declare(
                exchange=dlx_name, exchange_type="direct", durable=True
            )
            
            # Declare DLQ
            dlq_name = f"{EVENT_NAMESPACE}.commerce.reviews.dlq"
            channel.queue_declare(queue=dlq_name, durable=True)
            channel.queue_bind(
                queue=dlq_name, exchange=dlx_name, routing_key="review.moderated.dlq"
            )
            
            # Declare queue with DLX args
            queue_name = f"{EVENT_NAMESPACE}.commerce.reviews"
            queue_args = {
                "x-dead-letter-exchange": dlx_name,
                "x-dead-letter-routing-key": "review.moderated.dlq"
            }
            
            try:
                channel.queue_declare(queue=queue_name, durable=True, arguments=queue_args)
            except pika.exceptions.ChannelClosedByBroker as e:
                if e.reply_code == 406:  # PRECONDITION_FAILED
                    # Recreate channel, delete the queue, and redeclare it
                    channel = connection.channel()
                    print(f"Queue {queue_name} has different arguments. Deleting and recreating for DLQ support.")
                    channel.queue_delete(queue=queue_name)
                    channel.queue_declare(queue=queue_name, durable=True, arguments=queue_args)
                else:
                    raise e
            
            # Bind queue
            channel.queue_bind(
                queue=queue_name, exchange=exchange_name, routing_key="review.moderated"
            )
            
            print(f"Successfully connected to RabbitMQ Broker and subscribed to queue {queue_name}.")
            backoff = 1.0  # Reset backoff on successful connection
            
            def callback(ch, method, properties, body):
                try:
                    event = json.loads(body.decode("utf-8"))
                    event_id = event["event_id"]
                    event_type = event["event_type"]
                    payload = event["payload"]
                    
                    print(f"Consumer received event {event_id} ({event_type})")
                    
                    with get_db() as conn:
                        conn.execute("BEGIN TRANSACTION")
                        cursor = conn.cursor()
                        
                        # Idempotency check
                        cursor.execute(
                            "SELECT 1 FROM processed_events WHERE event_id = ?",
                            (event_id,),
                        )
                        if cursor.fetchone():
                            print(f"Event {event_id} already processed. Skipping (Idempotency).")
                            conn.rollback()
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            return
                            
                        review_id = payload["review_id"]
                        product_id = payload["product_id"]
                        status_val = payload["status"]
                        
                        if status_val == "approved":
                            # Projection: Insert or replace approved review
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO product_reviews (review_id, product_id, user_id, rating, comment, image_base64, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    review_id,
                                    product_id,
                                    payload["user_id"],
                                    payload["rating"],
                                    payload["comment"],
                                    payload["image_base64"],
                                    payload["created_at"],
                                ),
                            )
                        elif status_val == "rejected":
                            # Projection: Delete review if rejected (or previously approved and now changed to rejected)
                            cursor.execute(
                                "DELETE FROM product_reviews WHERE review_id = ?",
                                (review_id,),
                            )
                            
                        # Record processed event ID
                        cursor.execute(
                            "INSERT INTO processed_events (event_id, processed_at) VALUES (?, ?)",
                            (event_id, dt.now(timezone.utc).isoformat()),
                        )
                        conn.commit()
                        
                        # Invalidate public reviews cache for this specific product
                        response_cache.invalidate(f"reviews_{product_id}")
                        print(f"Projection updated and cache invalidated for product {product_id}.")
                        
                    # Manual Ack
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
                except Exception as err:
                    print(f"Error processing review moderation event: {err}.")
                    # Bounded retry policy: up to 3 retries, then move to DLQ
                    headers = properties.headers if properties and properties.headers else {}
                    retry_count = headers.get("x-retry-count", 0)
                    
                    if retry_count < 3:
                        new_retry_count = retry_count + 1
                        print(f"Retrying message (attempt {new_retry_count}/3)...")
                        headers["x-retry-count"] = new_retry_count
                        
                        try:
                            ch.basic_publish(
                                exchange=exchange_name,
                                routing_key="review.moderated",
                                body=body,
                                properties=pika.BasicProperties(
                                    delivery_mode=2,
                                    content_type="application/json",
                                    headers=headers
                                )
                            )
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception as repub_err:
                            print(f"Failed to republish for retry: {repub_err}. Requeueing natively.")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    else:
                        print(f"Max retries reached ({retry_count}). Moving to DLQ...")
                        try:
                            ch.basic_publish(
                                exchange=dlx_name,
                                routing_key="review.moderated.dlq",
                                body=body,
                                properties=pika.BasicProperties(
                                    delivery_mode=2,
                                    content_type="application/json",
                                    headers=headers
                                )
                            )
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception as dlq_err:
                            print(f"Failed to move to DLQ: {dlq_err}. Requeueing natively.")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    
            # Set prefetch count to 1 for fair dispatch
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=False
            )
            
            # Block and consume
            channel.start_consuming()
            
        except Exception as conn_err:
            print(f"Consumer worker connection lost/failed: {conn_err}. Reconnecting in {backoff:.1f}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)


# Start consumer thread
if os.environ.get("RUN_WORKERS", "true").lower() == "true":
    consumer_thread = threading.Thread(target=events_consumer_worker, daemon=True)
    consumer_thread.start()
