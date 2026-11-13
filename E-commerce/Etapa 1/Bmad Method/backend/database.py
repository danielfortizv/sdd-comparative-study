import os
import hashlib
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

def init_db():
    """Initializes the SQLite database and creates the users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 HMAC SHA-256 with a unique random salt."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Combine salt and hash as hex strings separated by '$'
    return f"{salt.hex()}${pwd_hash.hex()}"

def verify_password(stored_format: str, provided_password: str) -> bool:
    """Verifies a password against its stored hash and salt."""
    try:
        salt_hex, stored_hash_hex = stored_format.split('$')
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(stored_hash_hex)
        # Compute the hash with the same salt and iterations
        computed_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return computed_hash == stored_hash
    except Exception:
        return False

def register_user(username: str, password: str) -> bool:
    """Registers a user with a hashed password. Returns True on success, False if already exists."""
    username = username.strip()
    if not username or not password:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        password_hash = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> bool:
    """Authenticates a user. Returns True if valid credentials, otherwise False."""
    username = username.strip()
    if not username or not password:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return False
    
    stored_format = row[0]
    return verify_password(stored_format, password)
