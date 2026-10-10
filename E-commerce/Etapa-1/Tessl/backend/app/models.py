from pydantic import BaseModel, Field, field_validator

class UserAuthSchema(BaseModel):
    """
    Standard schema for user registration and sign-in.
    Contains strictly 'username' and 'password'.
    """
    username: str = Field(..., min_length=1, description="Username is required")
    password: str = Field(..., min_length=1, description="Password is required")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Username cannot be empty or whitespace only")
        return stripped

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Simple non-empty validation as approved. No invented complexity rules.
        if not v:
            raise ValueError("Password cannot be empty")
        return v

class CartItemSchema(BaseModel):
    """
    Represents an item in the shopping cart.
    """
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1, description="Quantity must be at least 1")

class CheckoutRequest(BaseModel):
    """
    Represents a simulated checkout request containing the shopping cart items.
    """
    items: list[CartItemSchema] = Field(..., description="Items list is required")

    @field_validator('items')
    @classmethod
    def validate_items_non_empty(cls, v: list[CartItemSchema]) -> list[CartItemSchema]:
        if not v:
            raise ValueError("Shopping cart is empty. Checkout rejected.")
        return v
