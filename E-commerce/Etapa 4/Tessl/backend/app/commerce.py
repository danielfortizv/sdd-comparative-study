import sqlite3
import json
import threading
import time
import httpx
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
import pika
from app.models import CheckoutRequest
from app.cache import response_cache

import os

DB_FILE = os.getenv("COMMERCE_DB_FILE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "commerce.db")))
AMQP_URL = os.getenv("AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_tessl")
IDENTITY_INTERNAL_URL = os.getenv("IDENTITY_INTERNAL_URL", "http://127.0.0.1:18401")
EXCHANGE = os.getenv("AMQP_EXCHANGE", "stage4.tessl.exchange")
QUEUE = os.getenv("AMQP_QUEUE", "commerce.review_projection_queue")
ROUTING_KEY = os.getenv("AMQP_ROUTING_KEY", "review.approved")

PRODUCTS_SEED = [
    {
        "id": 1,
        "name": "Premium Ergonomic Keyboard",
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        "description": "Tactile mechanical switches with an ergonomic split layout for comfortable typing.",
        "price": 129.99,
        "availability": True
    },
    {
        "id": 2,
        "name": "Wireless Optical Mouse",
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&q=80",
        "description": "High-precision optical tracking with an ultra-long battery life and comfortable grip.",
        "price": 49.99,
        "availability": True
    },
    {
        "id": 3,
        "name": "Noise-Cancelling Headphones",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
        "description": "Active noise cancellation with rich studio sound and soft ear cushions for long listening sessions.",
        "price": 199.99,
        "availability": True
    },
    {
        "id": 4,
        "name": "Stainless Steel Water Bottle",
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=600&q=80",
        "description": "Double-wall vacuum insulation keeps your beverages cold for 24 hours or hot for 12 hours.",
        "price": 24.99,
        "availability": True
    },
    {
        "id": 5,
        "name": "Travel Canvas Backpack",
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "description": "Vintage canvas backpack with spacious compartments, padded laptop sleeve, and water-resistant finish.",
        "price": 59.99,
        "availability": False
    }
]

PUBLIC_REVIEWS_SEED = [
    {
        "id": 1,
        "product_id": 1,
        "rating": 5,
        "comment": "Absolutely love this keyboard! The split layout takes a few days to get used to, but my wrist pain has completely disappeared. Highly recommended!",
        "image_base64": None,
        "username": "keyboard_enthusiast",
        "created_at": "2026-11-01 10:30:00"
    },
    {
        "id": 2,
        "product_id": 1,
        "rating": 4,
        "comment": "Very tactile and responsive. Build quality is solid. One star off because the spacebar was a bit squeaky out of the box.",
        "image_base64": None,
        "username": "code_ninja",
        "created_at": "2026-11-03 14:15:00"
    },
    {
        "id": 3,
        "product_id": 2,
        "rating": 5,
        "comment": "Best travel mouse ever. Battery life is incredible and fits perfectly in my hand.",
        "image_base64": None,
        "username": "digital_nomad",
        "created_at": "2026-11-05 09:00:00"
    }
]

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

app = FastAPI(title="Commerce Service", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def rabbitmq_subscriber_loop():
    print("[Subscriber Worker] Thread started.")
    while True:
        try:
            params = pika.URLParameters(AMQP_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            
            # 1. Declare Main Exchange (direct)
            channel.exchange_declare(exchange=EXCHANGE, exchange_type='direct', durable=True)
            
            # 2. Configure Dead-Letter Queue (DLQ) topology
            dlx_name = EXCHANGE + ".dlx"
            dlq_name = QUEUE + ".dlq"
            
            # Declare DLX
            channel.exchange_declare(exchange=dlx_name, exchange_type='direct', durable=True)
            # Declare DLQ
            channel.queue_declare(queue=dlq_name, durable=True)
            # Bind DLQ to DLX
            channel.queue_bind(queue=dlq_name, exchange=dlx_name, routing_key="dlq")
            
            # 3. Declare Main Queue with x-dead-letter arguments (with 406 migration fallback)
            queue_args = {
                "x-dead-letter-exchange": dlx_name,
                "x-dead-letter-routing-key": "dlq"
            }
            try:
                channel.queue_declare(queue=QUEUE, durable=True, arguments=queue_args)
            except pika.exceptions.ChannelClosedByBroker as cb:
                if cb.reply_code == 406:
                    print(f"[Subscriber Worker] Queue {QUEUE} has mismatched arguments. Recreating queue...")
                    channel = connection.channel()
                    channel.queue_delete(queue=QUEUE)
                    channel.queue_declare(queue=QUEUE, durable=True, arguments=queue_args)
                else:
                    raise cb
            
            # 4. Bind Main Queue to BOTH routing keys to listen to approvals and rejections
            channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key="review.approved")
            channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key="review.rejected")
            
            print("[Subscriber Worker] Connected to RabbitMQ with DLQ and terminal-state routing.")
            
            def callback(ch, method, properties, body):
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        event = json.loads(body.decode('utf-8'))
                        event_type = event.get("event_type") or event.get("type")
                        payload = event["payload"]
                        
                        if event_type == "review.approved":
                            review_id = payload["review_id"]
                            product_id = payload["product_id"]
                            rating = payload["rating"]
                            comment = payload["comment"]
                            image_base64 = payload["image_base64"]
                            username = payload["username"]
                            created_at = payload["created_at"]
                            
                            print(f"[Subscriber Worker] (Attempt {attempt}/{max_retries}) Received approved review event ID {review_id} for product {product_id}")
                            
                            # Idempotently insert into public_reviews table
                            with get_db() as conn:
                                cur = conn.cursor()
                                cur.execute("SELECT 1 FROM public_reviews WHERE id = ?", (review_id,))
                                if not cur.fetchone():
                                    conn.execute(
                                        "INSERT INTO public_reviews (id, product_id, rating, comment, image_base64, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                        (review_id, product_id, rating, comment, image_base64, username, created_at)
                                    )
                                    conn.commit()
                                    print(f"[Subscriber Worker] Inserted review ID {review_id} into public projection.")
                                else:
                                    print(f"[Subscriber Worker] Review ID {review_id} already exists in projection. Skipping insert.")
                            
                            # Invalidate reviews cache
                            response_cache.invalidate(f"reviews:{product_id}")
                            print(f"[Subscriber Worker] Invalidated cache for key 'reviews:{product_id}'")
                            
                        elif event_type == "review.rejected":
                            review_id = payload["review_id"]
                            product_id = payload["product_id"]
                            
                            print(f"[Subscriber Worker] (Attempt {attempt}/{max_retries}) Received rejected review event ID {review_id} for product {product_id}")
                            
                            # Idempotently delete from public_reviews table
                            with get_db() as conn:
                                conn.execute("DELETE FROM public_reviews WHERE id = ?", (review_id,))
                                conn.commit()
                                print(f"[Subscriber Worker] Deleted review ID {review_id} from public projection.")
                            
                            # Invalidate reviews cache
                            response_cache.invalidate(f"reviews:{product_id}")
                            print(f"[Subscriber Worker] Invalidated cache for key 'reviews:{product_id}'")
                        
                        else:
                            # Unexpected event type, throw to trigger retries/DLQ
                            raise ValueError(f"Unknown event type: {event_type}")

                        # Succeeded! Manual ack and return from loop
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                        
                    except Exception as ex:
                        print(f"[Subscriber Worker] Error processing message (attempt {attempt}/{max_retries}): {ex}")
                        if attempt < max_retries:
                            time.sleep(1)
                        else:
                            print(f"[Subscriber Worker] Max retries reached. Dead-lettering message.")
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE, on_message_callback=callback)
            channel.start_consuming()
            
        except Exception as e:
            print(f"[Subscriber Worker] RabbitMQ consumer error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

@app.on_event("startup")
def startup_event():
    # 1. Initialize DB
    with get_db() as conn:
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
        conn.commit()

    # 2. Seed products
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            for p in PRODUCTS_SEED:
                conn.execute(
                    "INSERT INTO products (id, name, image_url, description, price, availability) VALUES (?, ?, ?, ?, ?, ?)",
                    (p["id"], p["name"], p["image_url"], p["description"], p["price"], 1 if p["availability"] else 0)
                )
            conn.commit()

    # 3. Seed public reviews
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM public_reviews")
        if cur.fetchone()[0] == 0:
            for r in PUBLIC_REVIEWS_SEED:
                conn.execute(
                    "INSERT INTO public_reviews (id, product_id, rating, comment, image_base64, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["product_id"], r["rating"], r["comment"], r["image_base64"], r["username"], r["created_at"])
                )
            conn.commit()

    # 4. Start RabbitMQ subscriber thread
    sub_thread = threading.Thread(target=rabbitmq_subscriber_loop, daemon=True)
    sub_thread.start()

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
                detail_msg = resp.json().get("detail", "Session inactive or missing authentication token")
                raise HTTPException(status_code=resp.status_code, detail=detail_msg)
            return resp.json()
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Auth service unreachable"
            )

@app.get("/api/products")
def get_products():
    cached = response_cache.get("products")
    if cached is not None:
        return cached

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products ORDER BY id ASC")
        rows = cur.fetchall()
        products_list = []
        for r in rows:
            products_list.append({
                "id": r["id"],
                "name": r["name"],
                "image_url": r["image_url"],
                "description": r["description"],
                "price": r["price"],
                "availability": bool(r["availability"])
            })
        
    response_cache.set("products", products_list)
    return products_list

@app.get("/api/products/{id}/reviews")
def get_product_reviews(id: int):
    # Verify product exists in catalog
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM products WHERE id = ?", (id,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {id} was not found in the catalog"
            )
    
    cache_key = f"reviews:{id}"
    cached = response_cache.get(cache_key)
    if cached is not None:
        return cached

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM public_reviews WHERE product_id = ? ORDER BY id ASC", (id,))
        rows = cur.fetchall()
        reviews_list = [dict(r) for r in rows]

    response_cache.set(cache_key, reviews_list)
    return reviews_list

@app.post("/api/checkout")
async def simulated_checkout(payload: CheckoutRequest, authorization: str | None = Header(None)):
    user_info = await verify_internal_token(authorization)
    username = user_info["username"]

    summary_items = []
    total_amount = 0.0

    # Read products from DB
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products")
        db_products = {r["id"]: dict(r) for r in cur.fetchall()}

    for cart_item in payload.items:
        prod_id = cart_item.product_id
        qty = cart_item.quantity

        product = db_products.get(prod_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {prod_id} was not found in the catalog"
            )

        if not bool(product["availability"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product['name']}' is currently out of stock"
            )

        item_total = round(product["price"] * qty, 2)
        summary_items.append({
            "product_id": prod_id,
            "name": product["name"],
            "price": product["price"],
            "quantity": qty,
            "item_total": item_total
        })
        total_amount += item_total

    total_amount = round(total_amount, 2)

    return {
        "message": "Fictitious checkout completed successfully. No real charge has been made, and no payment gateway was contacted.",
        "summary": {
            "items": summary_items,
            "total_amount": total_amount,
            "buyer": username
        }
    }
