import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db, seed_database, User, Product, Review
from app.auth import hash_password, verify_password, create_access_token, verify_access_token
from app.schemas import (
    UserAuth, UserOut, Token, ProductOut,
    ReviewCreate, ReviewOut, ProductDetailOut, ModerationAction
)
from app.cache import cache_instance

app = FastAPI(
    title="Stage 2 Academic Ecommerce API",
    description="English-only backend service for the academic e-commerce demonstration with reviews & moderation.",
    version="2.0.0"
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

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
        )
    return user_id

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
    cache_key = "products_list"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    products = db.query(Product).all()
    # Serialize to dictionary using schemas to avoid detached session issues when caching
    result = [ProductOut.model_validate(p).model_dump() for p in products]
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

@app.get("/api/products/{id}", response_model=ProductDetailOut)
def get_product_detail(id: int, db: Session = Depends(get_db)):
    """Fetch details of a single product with average rating."""
    cache_key = f"product_detail_{id}"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found."
        )
    # Calculate average rating
    approved_reviews = db.query(Review).filter(Review.product_id == id, Review.status == "approved").all()
    avg_rating = None
    if approved_reviews:
        avg_rating = sum(r.rating for r in approved_reviews) / len(approved_reviews)
        avg_rating = round(avg_rating, 2)
    
    result = {
        "id": product.id,
        "name": product.name,
        "image_url": product.image_url,
        "description": product.description,
        "price": product.price,
        "is_available": product.is_available,
        "average_rating": avg_rating
    }
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

@app.get("/api/products/{id}/reviews", response_model=List[ReviewOut])
def get_product_reviews(id: int, db: Session = Depends(get_db)):
    """Fetch approved reviews for a product."""
    cache_key = f"product_reviews_{id}"
    cached = cache_instance.get(cache_key)
    if cached is not None:
        return cached

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found."
        )
    reviews = db.query(Review).filter(Review.product_id == id, Review.status == "approved").order_by(Review.created_at.desc()).all()
    result = [ReviewOut.model_validate(r).model_dump() for r in reviews]
    cache_instance.set(cache_key, result, ttl_seconds=60)
    return result

@app.post("/api/products/{id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    id: int,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Submit a new product review (requires authentication)."""
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found."
        )
    
    # Create the review
    new_review = Review(
        product_id=id,
        user_id=current_user,
        rating=review_data.rating,
        comment=review_data.comment,
        image_data=review_data.image_data,
        status="pending"
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@app.get("/api/moderation/reviews", response_model=List[ReviewOut])
def list_pending_reviews(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """List all pending reviews (moderator only)."""
    if current_user != "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the moderator can access this resource."
        )
    pending_reviews = db.query(Review).filter(Review.status == "pending").order_by(Review.created_at.desc()).all()
    return pending_reviews

@app.post("/api/moderation/reviews/{review_id}/action", response_model=ReviewOut)
def moderate_review(
    review_id: int,
    action_data: ModerationAction,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Approve or reject a review (moderator only)."""
    if current_user != "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the moderator can moderate reviews."
        )
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found."
        )
    
    action = action_data.action.lower().strip()
    if action == "approve":
        review.status = "approved"
    elif action == "reject":
        review.status = "rejected"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'."
        )
    
    db.commit()
    db.refresh(review)

    # Invalidate cache for product detail, reviews list, and the overall catalog list
    cache_instance.invalidate_key("products_list")
    cache_instance.invalidate_key(f"product_detail_{review.product_id}")
    cache_instance.invalidate_key(f"product_reviews_{review.product_id}")

    return review

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
