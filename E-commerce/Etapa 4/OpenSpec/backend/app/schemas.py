from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class UserAuth(BaseModel):
    account_identifier: str = Field(..., description="The unique customer identifier, e.g. email or username")
    password: str = Field(..., description="The user's secret password")

class UserOut(BaseModel):
    id: int
    account_identifier: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    account_identifier: str

class ProductOut(BaseModel):
    id: int
    name: str
    image_url: str
    description: str
    price: float
    is_available: bool

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating between 1 and 5")
    comment: str = Field(..., min_length=1, description="Text comment for the review")
    image_data: Optional[str] = Field(None, description="Optional Base64 encoded image string")

class ReviewOut(BaseModel):
    id: int
    product_id: int
    user_id: str
    rating: int
    comment: str
    image_data: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProductDetailOut(BaseModel):
    id: int
    name: str
    image_url: str
    description: str
    price: float
    is_available: bool
    average_rating: Optional[float] = None

    class Config:
        from_attributes = True

class ModerationAction(BaseModel):
    action: str = Field(..., description="Must be either 'approve' or 'reject'")
