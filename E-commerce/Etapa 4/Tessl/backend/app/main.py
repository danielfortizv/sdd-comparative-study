import sqlite3
import datetime
import secrets
import uuid
import json
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from app.auth import hash_password, verify_password
from app.models import UserAuthSchema, CheckoutRequest, ReviewCreateSchema, ReviewStatusUpdateSchema
from app.cache import response_cache

DB_IDENTITY = "identity.db"
DB_COMMERCE = "commerce.db"
DB_REVIEWS = "reviews.db"

@contextmanager
def get_db(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

app = FastAPI(title="Stage 4 Facade & Test Service", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Ensure all three databases are initialized for testing/compatibility runs
    with get_db(DB_IDENTITY) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT,
                salt TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT,
                expires_at REAL
            )
        """)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = 'moderator'")
        if not cur.fetchone():
            m_hashed, m_salt = hash_password("moderator")
            conn.execute(
                "INSERT INTO users (username, hashed_password, salt) VALUES (?, ?, ?)",
                ("moderator", m_hashed, m_salt)
            )
        conn.commit()

    with get_db(DB_COMMERCE) as conn:
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

    with get_db(DB_REVIEWS) as conn:
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

def verify_token_direct(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or missing authentication token"
        )
    token = authorization.split(" ")[1]
    with get_db(DB_IDENTITY) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, expires_at FROM sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired or token is invalid"
            )
        if datetime.datetime.now().timestamp() > row["expires_at"]:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired or token is invalid"
            )
        username = row["username"]
        is_moderator = (username == "moderator")
        return {"username": username, "is_moderator": is_moderator}

@app.post("/api/register")
def register_user(payload: UserAuthSchema):
    username = payload.username
    password = payload.password

    with get_db(DB_IDENTITY) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The username is already taken. Please choose another username."
            )
        hashed_pwd, salt = hash_password(password)
        conn.execute(
            "INSERT INTO users (username, hashed_password, salt) VALUES (?, ?, ?)",
            (username, hashed_pwd, salt)
        )
        conn.commit()

    # Create session
    token = secrets.token_hex(24)
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).timestamp()
    with get_db(DB_IDENTITY) as conn:
        conn.execute(
            "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
            (token, username, expires_at)
        )
        conn.commit()

    return {
        "token": token,
        "username": username,
        "message": "User registered successfully"
    }

@app.post("/api/login")
def login_user(payload: UserAuthSchema):
    username = payload.username
    password = payload.password

    with get_db(DB_IDENTITY) as conn:
        cur = conn.cursor()
        cur.execute("SELECT hashed_password, salt FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row or not verify_password(password, row["hashed_password"], row["salt"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

    token = secrets.token_hex(24)
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).timestamp()
    with get_db(DB_IDENTITY) as conn:
        conn.execute(
            "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
            (token, username, expires_at)
        )
        conn.commit()

    return {
        "token": token,
        "username": username,
        "message": "Logged in successfully"
    }

@app.post("/api/logout")
def logout_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bearer token missing or malformed"
        )
    token = authorization.split(" ")[1]
    with get_db(DB_IDENTITY) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sessions WHERE token = ?", (token,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or session already terminated"
            )
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    return {"message": "Logged out successfully"}

@app.get("/api/products")
def get_products():
    cached = response_cache.get("products")
    if cached is not None:
        return cached

    with get_db(DB_COMMERCE) as conn:
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
    # Verify product exists
    with get_db(DB_COMMERCE) as conn:
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

    with get_db(DB_COMMERCE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM public_reviews WHERE product_id = ? ORDER BY id ASC", (id,))
        rows = cur.fetchall()
        reviews_list = [dict(r) for r in rows]

    response_cache.set(cache_key, reviews_list)
    return reviews_list

@app.post("/api/products/{id}/reviews")
def create_product_review(id: int, payload: ReviewCreateSchema, authorization: str | None = Header(None)):
    user_info = verify_token_direct(authorization)
    username = user_info["username"]

    with get_db(DB_COMMERCE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM products WHERE id = ?", (id,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {id} was not found in the catalog"
            )

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db(DB_REVIEWS) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reviews (product_id, rating, comment, image_base64, status, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, payload.rating, payload.comment, payload.image_base64, "pending", username, created_at)
        )
        new_review_id = cur.lastrowid
        conn.commit()

        cur.execute("SELECT * FROM reviews WHERE id = ?", (new_review_id,))
        new_review = dict(cur.fetchone())

    # Invalidate reviews cache for test verification
    response_cache.invalidate(f"reviews:{id}")

    return {
        "message": "Review submitted successfully and is currently pending moderation.",
        "review": new_review
    }

@app.get("/api/moderation/reviews")
def get_all_reviews_for_moderation(authorization: str | None = Header(None)):
    user_info = verify_token_direct(authorization)
    if not user_info.get("is_moderator", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the 'moderator' user can access moderation APIs."
        )

    with get_db(DB_REVIEWS) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reviews ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

@app.post("/api/moderation/reviews/{id}/status")
def update_review_status(id: int, payload: ReviewStatusUpdateSchema, authorization: str | None = Header(None)):
    user_info = verify_token_direct(authorization)
    if not user_info.get("is_moderator", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the 'moderator' user can access moderation APIs."
        )

    with get_db(DB_REVIEWS) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reviews WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {id} was not found"
            )
        
        conn.execute("UPDATE reviews SET status = ? WHERE id = ?", (payload.status, id))
        
        if payload.status == "approved":
            event_payload = {
                "event_id": str(uuid.uuid4()),
                "correlation_id": str(uuid.uuid4()),
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
            
            # For monolithic/facade testing compatibility, we also update DB_COMMERCE immediately
            with get_db(DB_COMMERCE) as comm_conn:
                comm_conn.execute("INSERT OR REPLACE INTO public_reviews (id, product_id, rating, comment, image_base64, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (id, row["product_id"], row["rating"], row["comment"], row["image_base64"], row["username"], row["created_at"]))
                comm_conn.commit()

        conn.commit()

        cur.execute("SELECT * FROM reviews WHERE id = ?", (id,))
        updated_review = dict(cur.fetchone())

    # Invalidate reviews cache
    response_cache.invalidate(f"reviews:{updated_review['product_id']}")

    return {
        "message": f"Review status updated to '{payload.status}' successfully.",
        "review": updated_review
    }

@app.post("/api/checkout")
def simulated_checkout(payload: CheckoutRequest, authorization: str | None = Header(None)):
    user_info = verify_token_direct(authorization)
    username = user_info["username"]

    summary_items = []
    total_amount = 0.0

    with get_db(DB_COMMERCE) as conn:
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
