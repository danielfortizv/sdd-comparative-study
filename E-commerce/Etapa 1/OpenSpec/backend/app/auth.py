import datetime
import jwt
import bcrypt

SECRET_KEY = "super-secret-academic-key-do-not-use-in-production"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(account_identifier: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode = {"sub": account_identifier, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_identifier: str = payload.get("sub")
        if account_identifier is None:
            return None
        return account_identifier
    except jwt.PyJWTError:
        return None
