from pydantic import BaseModel, Field

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
