import sqlite3
import datetime
import secrets
import os
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from app.auth import hash_password, verify_password
from app.models import UserAuthSchema

DB_FILE = os.getenv("IDENTITY_DB_FILE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "identity.db")))

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

app = FastAPI(title="Identity & Authentication Service", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    with get_db() as conn:
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

def create_session(username: str) -> str:
    token = secrets.token_hex(24)
    # Session valid for 24 hours
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).timestamp()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
            (token, username, expires_at)
        )
        conn.commit()
    return token

@app.post("/api/register")
def register_user(payload: UserAuthSchema):
    username = payload.username
    password = payload.password

    with get_db() as conn:
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

    token = create_session(username)
    return {
        "token": token,
        "username": username,
        "message": "User registered successfully"
    }

@app.post("/api/login")
def login_user(payload: UserAuthSchema):
    username = payload.username
    password = payload.password

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT hashed_password, salt FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row or not verify_password(password, row["hashed_password"], row["salt"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

    token = create_session(username)
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

    with get_db() as conn:
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

@app.get("/api/internal/verify-token")
def verify_token(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or missing authentication token"
        )
    token = authorization.split(" ")[1]

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, expires_at FROM sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired or token is invalid"
            )
        
        # Check expiration
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
