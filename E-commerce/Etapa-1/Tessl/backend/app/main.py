from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from app.database import PRODUCTS, USERS, SESSIONS
from app.auth import hash_password, verify_password, create_session, delete_session, get_username_by_token
from app.models import UserAuthSchema, CheckoutRequest, CartItemSchema

app = FastAPI(title="Stage 1 E-Commerce Backend", version="1.0.0")

# Configure CORS so the React frontend can safely interact with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits requests from localhost:3000 or any dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_user(authorization: str | None = Header(None)) -> str:
    """
    Dependency helper to resolve Bearer tokens.
    Returns the username if active session exists, else raises 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session inactive or missing authentication token"
        )
    token = authorization.split(" ")[1]
    username = get_username_by_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or token is invalid"
        )
    return username

@app.get("/api/products")
def get_products():
    """
    Retrieve all product details from the catalog. Accessible by visitors.
    """
    return PRODUCTS

@app.post("/api/register")
def register_user(payload: UserAuthSchema):
    """
    Registers a new user and automatically establishes an active session,
    returning the bearer token and username.
    """
    username = payload.username
    password = payload.password

    if username in USERS:
        # Standard useful conflict response without leaking internal systems
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The username is already taken. Please choose another username."
        )

    # Securely hash password and save
    hashed_pwd, salt = hash_password(password)
    USERS[username] = {
        "username": username,
        "hashed_password": hashed_pwd,
        "salt": salt
    }

    # Automatically create session upon successful registration as approved
    token = create_session(username)
    return {
        "token": token,
        "username": username,
        "message": "User registered successfully"
    }

@app.post("/api/login")
def login_user(payload: UserAuthSchema):
    """
    Authenticates an existing user and returns a session token.
    """
    username = payload.username
    password = payload.password

    user = USERS.get(username)
    if not user or not verify_password(password, user["hashed_password"], user["salt"]):
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
    """
    Logs out the user and invalidates their current session token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bearer token missing or malformed"
        )
    token = authorization.split(" ")[1]
    success = delete_session(token)
    if not success:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or session already terminated"
        )
    return {"message": "Logged out successfully"}

@app.post("/api/checkout")
def simulated_checkout(payload: CheckoutRequest, authorization: str | None = Header(None)):
    """
    Executes a simulated checkout using the active cart contents and authenticated user only.
    Rejects unauthorized and empty-cart requests. Returns fictitious success and order details.
    """
    # 1. Enforce authentication
    username = get_current_user(authorization)

    # 2. Extract items and build summary matching mock catalog
    summary_items = []
    total_amount = 0.0

    product_map = {p["id"]: p for p in PRODUCTS}

    for cart_item in payload.items:
        prod_id = cart_item.product_id
        qty = cart_item.quantity

        product = product_map.get(prod_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {prod_id} was not found in the catalog"
            )

        # Enforce that products added to checkout must be available
        if not product["availability"]:
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

    # 3. Formulate response without an order ID
    return {
        "message": "Fictitious checkout completed successfully. No real charge has been made, and no payment gateway was contacted.",
        "summary": {
            "items": summary_items,
            "total_amount": total_amount,
            "buyer": username
        }
    }
