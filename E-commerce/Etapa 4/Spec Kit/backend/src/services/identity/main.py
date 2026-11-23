import os
import sqlite3
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ...common.security import hash_password, verify_password, create_jwt, decode_jwt

app = FastAPI(title="Identity Service", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get("IDENTITY_DB_PATH", "identity.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes identity.db table schemas and seeds the default moderator account."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                identifier TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        conn.commit()
        
        # Seed moderator if not exists
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE identifier = ?", ("moderator",))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (identifier, password_hash, role) VALUES (?, ?, ?)",
                ("moderator", hash_password("moderator"), "moderator"),
            )
            conn.commit()


init_db()


class RegisterRequest(BaseModel):
    identifier: str
    password: str


class SignInRequest(BaseModel):
    identifier: str
    password: str


@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    identifier = payload.identifier.strip()
    password = payload.password
    
    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier and password cannot be empty.",
        )
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE identifier = ?", (identifier,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this identifier already exists.",
            )
            
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (identifier, password_hash, role) VALUES (?, ?, ?)",
            (identifier, hashed, "customer"),
        )
        conn.commit()
        
    return {"message": "Account successfully registered."}


@app.post("/api/signin")
def signin(payload: SignInRequest):
    identifier = payload.identifier.strip()
    password = payload.password
    
    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifier and password are required.",
        )
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, role FROM users WHERE identifier = ?", (identifier,)
        )
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identifier or password.",
        )
        
    hashed_pwd = row["password_hash"]
    role = row["role"]
    
    if not verify_password(password, hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identifier or password.",
        )
        
    # Generate standard cryptographic JWT token
    token_payload = {"sub": identifier, "role": role}
    jwt_token = create_jwt(token_payload)
    
    return {"session_token": jwt_token}


@app.post("/api/signout")
def signout(authorization: str = Header(None)):
    """Handles logout statelessly on the server."""
    # Front-end has typo 'Bearer {token}', decode_jwt handles stripping curly braces gracefully.
    if not authorization:
        return {"message": "Session terminated or was already invalid."}
        
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"message": "Session terminated or was already invalid."}
        
    token = parts[1]
    # We decode it to check validity (optional, since it's stateless)
    payload = decode_jwt(token)
    if not payload:
        return {"message": "Session terminated or was already invalid."}
        
    return {"message": "Session successfully terminated."}


@app.get("/api/me")
def get_me(authorization: str = Header(None)):
    """A helper route for verifying token validity and retrieving current user metadata."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token format",
        )
    payload = decode_jwt(parts[1])
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or invalid token. Please sign in.",
        )
    return payload
