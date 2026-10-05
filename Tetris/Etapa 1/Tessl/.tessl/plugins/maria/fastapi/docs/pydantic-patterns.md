# Pydantic v2 Patterns

Best practices for using Pydantic v2 with FastAPI. All examples use Pydantic v2 syntax exclusively.

## Model Separation Pattern

Separate schemas by purpose — never reuse one model for input, update, and output.

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Input schema — fields the client sends when creating
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Update schema — all fields optional for partial updates
class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None

# Response schema — what the API returns (no password, includes server fields)
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    created_at: datetime
```

Use in endpoints:

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate):
    user = save_to_db(payload)
    return user

@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate):
    user = patch_in_db(user_id, payload.model_dump(exclude_unset=True))
    return user
```

## Explicit Response Models

Always declare `response_model=` on every endpoint. This acts as an allowlist — only fields defined in the response model are serialised, preventing accidental PII leakage.

```python
# Good — response_model controls what gets returned
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return db.get(user_id)  # extra fields like password are stripped

# Bad — no response_model, raw dict/ORM object goes straight to client
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return db.get(user_id)  # may leak internal fields
```

## Field Configuration

Use `Field()` for constraints and metadata. Use `ConfigDict` (not inner `class Config`).

```python
from pydantic import BaseModel, Field, ConfigDict

class Product(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0, description="Price in USD")
    sku: str = Field(pattern=r"^[A-Z]{2}-\d{4}$")
    tags: list[str] = Field(default_factory=list, max_length=10)
```

## Validators

Use `@field_validator` for single-field validation and `@model_validator` for cross-field logic.

```python
from pydantic import BaseModel, field_validator, model_validator

class Order(BaseModel):
    quantity: int
    unit_price: float
    discount: float = 0.0

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v

    @model_validator(mode="after")
    def discount_within_total(self):
        total = self.quantity * self.unit_price
        if self.discount > total:
            raise ValueError("discount exceeds order total")
        return self
```

**Pre-validation** (operate on raw input before field parsing):

```python
class NormalisedEmail(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v):
        if isinstance(v, str):
            return v.lower().strip()
        return v
```

## Computed Fields

Use `@computed_field` with `@property` for derived values included in serialisation.

```python
from pydantic import BaseModel, computed_field

class CartItem(BaseModel):
    name: str
    quantity: int
    unit_price: float

    @computed_field
    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price
```

## Serialization

Use `model_dump()` and `model_dump_json()` — never `.dict()` or `.json()`.

```python
user = UserResponse(id=1, username="alice", email="a@b.com", created_at=datetime.now())

# Dict output
data = user.model_dump()                          # all fields
data = user.model_dump(exclude_unset=True)         # only explicitly set fields
data = user.model_dump(exclude={"email"})          # drop specific fields
data = user.model_dump(include={"id", "username"}) # keep only these fields

# JSON string
json_str = user.model_dump_json(indent=2)
```

Custom serialisation with `@field_serializer`:

```python
from pydantic import BaseModel, field_serializer
from datetime import datetime

class Event(BaseModel):
    name: str
    starts_at: datetime

    @field_serializer("starts_at")
    def serialize_starts_at(self, v: datetime, _info):
        return v.strftime("%Y-%m-%d %H:%M")
```

## Nested Models

Pydantic models compose naturally as FastAPI request/response types.

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class CompanyResponse(BaseModel):
    name: str
    headquarters: Address
    offices: list[Address] = []

@app.get("/company/{id}", response_model=CompanyResponse)
def get_company(id: int):
    return db.get_company(id)
```

## TypeAdapter

Validate non-model types (lists, unions, primitives) without wrapping in a model.

```python
from pydantic import TypeAdapter

# Validate a list of integers
int_list_adapter = TypeAdapter(list[int])
result = int_list_adapter.validate_python(["1", "2", "3"])  # [1, 2, 3]

# Validate a union type
from typing import Union
adapter = TypeAdapter(Union[int, str])
adapter.validate_python(42)    # 42
adapter.validate_python("hi")  # "hi"

# Generate JSON schema for non-model types
schema = int_list_adapter.json_schema()
```

Use with FastAPI for validating query parameters or complex types outside of Pydantic models.
