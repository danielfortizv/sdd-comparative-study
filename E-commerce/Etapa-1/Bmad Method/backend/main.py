from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import database

# Initialize application and database
app = FastAPI(title="Stage 1 E-Commerce Backend", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows communication from any local origin (e.g. Vite dev server)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    database.init_db()

# Request and Response schemas
class UserAuthSchema(BaseModel):
    username: str = Field(..., min_length=1, description="Minimum customer identifier")
    password: str = Field(..., min_length=1, description="Password secret")

class CartItemSchema(BaseModel):
    id: int
    quantity: int = Field(..., gt=0)
    price: float

class CheckoutSchema(BaseModel):
    items: List[CartItemSchema]
    summary_total: float

# Static Demonstration Catalog Data
# Includes clean, inline SVG vectors representing each product to ensure flawless standalone loading.
PRODUCTS_CATALOG = [
    {
        "id": 1,
        "name": "Wireless Stereo Headphones",
        "description": "High-fidelity wireless audio headphones with adaptive sound and comfortable over-ear design.",
        "price": 59.99,
        "availability": "In Stock",
        "image_svg": '<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2" class="product-icon"><rect x="15" y="45" rx="5" width="12" height="30" fill="currentColor"/><rect x="73" y="45" rx="5" width="12" height="30" fill="currentColor"/><path d="M21 45 C 21 10, 79 10, 79 45" stroke-linecap="round"/><path d="M21 55 L 21 65" stroke-linecap="round"/><path d="M79 55 L 79 65" stroke-linecap="round"/></svg>'
    },
    {
        "id": 2,
        "name": "Ergonomic Office Chair",
        "description": "Premium lumbar support mesh chair with adjustable height and padded armrests.",
        "price": 149.50,
        "availability": "In Stock",
        "image_svg": '<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2" class="product-icon"><path d="M30 45 L70 45 M35 45 L35 20 L65 20 L65 45 M30 55 L70 55 L50 55 L50 80 M50 80 L35 90 M50 80 L65 90" stroke-linecap="round"/><path d="M40 55 L40 45 M60 55 L60 45" stroke-linecap="round"/></svg>'
    },
    {
        "id": 3,
        "name": "Mechanical Gaming Keyboard",
        "description": "Tactile mechanical switches with responsive backlight and durable layout.",
        "price": 89.00,
        "availability": "In Stock",
        "image_svg": '<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2" class="product-icon"><rect x="10" y="30" width="80" height="40" rx="4"/><rect x="18" y="38" width="8" height="8" rx="1"/><rect x="32" y="38" width="8" height="8" rx="1"/><rect x="46" y="38" width="8" height="8" rx="1"/><rect x="60" y="38" width="8" height="8" rx="1"/><rect x="74" y="38" width="8" height="8" rx="1"/><rect x="18" y="52" width="8" height="8" rx="1"/><rect x="32" y="52" width="36" height="8" rx="1"/><rect x="74" y="52" width="8" height="8" rx="1"/></svg>'
    },
    {
        "id": 4,
        "name": "Classic Smart Watch",
        "description": "Elegant smart wrist wearable with fitness tracking, notifications, and long battery life.",
        "price": 120.00,
        "availability": "Out of Stock",
        "image_svg": '<svg viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="2" class="product-icon"><circle cx="50" cy="50" r="22" fill="none"/><rect x="42" y="10" width="16" height="18" rx="2"/><rect x="42" y="72" width="16" height="18" rx="2"/><path d="M50 35 L50 50 L60 50" stroke-linecap="round"/></svg>'
    }
]

# API Endpoints

@app.get("/api/products")
def get_products():
    """Returns the static demonstration catalog of products."""
    return PRODUCTS_CATALOG

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(credentials: UserAuthSchema):
    """Registers a new user with minimum identifying credentials."""
    username = credentials.username.strip()
    password = credentials.password
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required and cannot be empty."
        )
    
    success = database.register_user(username, password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The username is already registered."
        )
    
    return {"success": True, "message": "Registration successful."}

@app.post("/api/login")
def login(credentials: UserAuthSchema):
    """Authenticates user credentials and starts an active session."""
    username = credentials.username.strip()
    password = credentials.password
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required."
        )
    
    is_valid = database.authenticate_user(username, password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )
    
    return {
        "success": True,
        "message": "Login successful.",
        "username": username
    }

@app.post("/api/checkout")
def checkout(order: CheckoutSchema):
    """Processes a simulated checkout, validating that the order is not empty."""
    if not order.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout with an empty shopping cart."
        )
    
    # Resolve items details to present an unambiguous confirmation summary
    summary_items = []
    catalog_dict = {p["id"]: p for p in PRODUCTS_CATALOG}
    
    for item in order.items:
        product_info = catalog_dict.get(item.id)
        if product_info:
            summary_items.append({
                "id": item.id,
                "name": product_info["name"],
                "quantity": item.quantity,
                "price": item.price,
                "subtotal": round(item.quantity * item.price, 2)
            })
    
    return {
        "success": True,
        "message": "Simulated purchase completed successfully.",
        "order_summary": {
            "items": summary_items,
            "total": round(order.summary_total, 2)
        }
    }
