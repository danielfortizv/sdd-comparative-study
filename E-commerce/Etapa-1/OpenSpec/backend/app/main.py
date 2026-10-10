import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db, seed_database, User, Product
from app.auth import hash_password, verify_password, create_access_token
from app.schemas import UserAuth, UserOut, Token, ProductOut

app = FastAPI(
    title="Stage 1 Academic Ecommerce API",
    description="English-only backend service for the academic e-commerce demonstration.",
    version="1.0.0"
)

# Configure CORS explicitly to allow the frontend dev server on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Automatically create tables and seed demo product catalog
    seed_database()

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health-check route to verify backend status."""
    return {"status": "healthy"}

@app.get("/api/products", response_model=List[ProductOut])
def get_products(db: Session = Depends(get_db)):
    """Fetch the product catalog list."""
    products = db.query(Product).all()
    return products

@app.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserAuth, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Ensure inputs are not empty or purely whitespaces
    id_stripped = user_data.account_identifier.strip()
    pw_stripped = user_data.password.strip()

    if not id_stripped or not pw_stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier and password are required and cannot be empty."
        )

    # Check duplicate account identifier
    existing_user = db.query(User).filter(User.account_identifier == id_stripped).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier is already in use. Please select a unique identifier."
        )

    # Hash the password and save
    hashed_pw = hash_password(user_data.password)
    new_user = User(account_identifier=id_stripped, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=Token)
def login(user_data: UserAuth, db: Session = Depends(get_db)):
    """Login a user and return a session token."""
    id_stripped = user_data.account_identifier.strip()
    pw_stripped = user_data.password.strip()

    if not id_stripped or not pw_stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account identifier and password are required."
        )

    # Fetch user from DB
    user = db.query(User).filter(User.account_identifier == id_stripped).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account identifier or password. Please verify your credentials."
        )

    # Create session token
    token = create_access_token(account_identifier=user.account_identifier)
    return Token(access_token=token, account_identifier=user.account_identifier)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
