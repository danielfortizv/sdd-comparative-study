import uuid
from typing import Any, Dict, List
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .security import hash_password, verify_password
from .storage import SESSIONS_DB, USERS_DB, load_catalog_products

app = FastAPI(title="Stage 1 E-Commerce Backend")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local demonstration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler middleware for non-sensitive error messages
@app.middleware("http")
async def non_sensitive_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # Return standard, non-sensitive 500 server error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An internal server error occurred. Please try again later."},
        )


# Pydantic Schemas for validation
class RegisterRequest(BaseModel):
    identifier: str
    password: str


class SignInRequest(BaseModel):
    identifier: str
    password: str


class CheckoutItem(BaseModel):
    product_id: str
    quantity: int


class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    demonstration_info: Dict[str, Any]


# Helper function to get token from Authorization Header
def get_token_from_header(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )
    return parts[1]


# 1. Product Catalog Retrieve Route
@app.get("/api/products")
def get_products():
    """Returns all products in the catalog list loaded from catalog.json."""
    products = load_catalog_products()
    return products


# 2. Account Registration Route
@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest):
    """
    Registers a new user account in-memory.
    Validates incomplete inputs. Passwords must never be saved in plain text.
    """
    identifier = payload.identifier.strip()
    password = payload.password

    # Validate empty input
    if not identifier or not password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Identifier and password cannot be empty."},
        )

    # Check if account already exists
    if identifier in USERS_DB:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "An account with this identifier already exists."},
        )

    # Secure hashing
    hashed = hash_password(password)
    USERS_DB[identifier] = hashed

    return {"message": "Account successfully registered."}


# 3. User Sign-In Route
@app.post("/api/signin")
def sign_in_user(payload: SignInRequest):
    """
    Validates credentials, activates session and returns session token.
    """
    identifier = payload.identifier.strip()
    password = payload.password

    # Validate inputs
    if not identifier or not password:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Identifier and password are required."},
        )

    # Find user account
    if identifier not in USERS_DB:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid identifier or password."},
        )

    # Verify password
    hashed_pwd = USERS_DB[identifier]
    if not verify_password(password, hashed_pwd):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid identifier or password."},
        )

    # Create active session
    session_token = str(uuid.uuid4())
    SESSIONS_DB[session_token] = identifier

    return {"session_token": session_token}


# 4. User Sign-Out Route
@app.post("/api/signout")
def sign_out_user(authorization: str = Header(None)):
    """
    Ends the active session on the backend.
    """
    try:
        token = get_token_from_header(authorization)
    except HTTPException as exc:
        # If token is invalid or missing, we can gracefully return success
        # to ensure local client sign-out is always completed.
        return {"message": "Session terminated or was already invalid."}

    if token in SESSIONS_DB:
        del SESSIONS_DB[token]

    return {"message": "Session successfully terminated."}


# 5. Simulated Checkout Route
@app.post("/api/checkout")
def simulated_checkout(payload: CheckoutRequest, authorization: str = Header(None)):
    """
    Performs simulated checkout validation.
    """
    # 1. Session verification
    try:
        token = get_token_from_header(authorization)
    except HTTPException:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Session inactive or invalid token. Please sign in."},
        )

    if token not in SESSIONS_DB:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Session inactive or invalid token. Please sign in."},
        )

    # 2. Cart verification
    if not payload.items:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Checkout blocked: shopping cart is empty."},
        )

    # 3. Catalog details resolution & quantity verification
    products = load_catalog_products()
    products_by_id = {p["product_id"]: p for p in products}

    summary_items = []
    accumulated_total = 0.0

    for item in payload.items:
        if item.quantity <= 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Invalid quantity '{item.quantity}' for product '{item.product_id}'."},
            )

        if item.product_id not in products_by_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Product '{item.product_id}' not found in catalog."},
            )

        prod_info = products_by_id[item.product_id]
        price = float(prod_info["price"])
        subtotal = round(price * item.quantity, 2)
        accumulated_total += subtotal

        summary_items.append({
            "product_id": item.product_id,
            "name": prod_info["name"],
            "quantity": item.quantity,
            "unit_price": price,
            "subtotal": subtotal
        })

    accumulated_total = round(accumulated_total, 2)

    # 4. Form Info validation (minimum opaque demo details)
    # The spec doesn't mandate specific fields, but let's make sure it contains at least one field
    if not payload.demonstration_info:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Checkout blocked: Please fill in the minimum demonstration details."},
        )

    # Simple check that the fields are not entirely empty
    for k, v in payload.demonstration_info.items():
        if not str(v).strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Checkout blocked: Demonstration field '{k}' cannot be empty."},
            )

    # 5. Build confirmation message with explicit disclaimers
    disclaimer_msg = (
        "Simulated purchase confirmed! No real payment gateway was contacted, "
        "no real inventory was reserved, and no actual charge has been made. "
        "This is an academic demonstration."
    )

    return {
        "message": disclaimer_msg,
        "purchase_summary": {
            "items": summary_items,
            "accumulated_total": accumulated_total
        }
    }
