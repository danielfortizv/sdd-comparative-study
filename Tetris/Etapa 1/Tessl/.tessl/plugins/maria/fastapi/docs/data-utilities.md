# Data Utilities

FastAPI provides utility functions for data encoding and serialization, particularly useful for converting Python objects to JSON-compatible formats. These utilities are essential for handling complex data types that aren't natively JSON serializable, such as datetime objects, Pydantic models, and database models.

## Capabilities

### JSON Encodable Converter

Primary utility function for converting Python objects to JSON-compatible formats with extensive customization options.

```python { .api }
def jsonable_encoder(
    obj: Any,
    include: Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any]] = None,
    exclude: Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any]] = None,
    by_alias: bool = True,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    round_trip: bool = True,
    timedelta_isoformat: str = "iso8601",
    sqlalchemy_safe: bool = True,
    fallback: Callable[[Any], Any] = None,
) -> Any:
    """
    Convert any object to a JSON-compatible format.
    
    Parameters:
    - obj: The object to encode
    - include: Fields to include (set of field names or dict with nested structure)
    - exclude: Fields to exclude (set of field names or dict with nested structure)
    - by_alias: Use field aliases if available (Pydantic models)
    - exclude_unset: Exclude fields that weren't explicitly set
    - exclude_defaults: Exclude fields that contain their default value
    - exclude_none: Exclude fields with None values
    - round_trip: Enable round-trip serialization compatibility
    - timedelta_isoformat: Format for timedelta objects ("iso8601" or "float")
    - sqlalchemy_safe: Safe handling of SQLAlchemy models
    - fallback: Custom fallback function for unsupported types
    
    Returns:
    JSON-compatible object (dict, list, str, int, float, bool, None)
    """
```

## Usage Examples

### Basic Object Encoding

```python
from fastapi.encoders import jsonable_encoder
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

# Basic Python types
data = {
    "string": "hello",
    "integer": 42,
    "float": 3.14,
    "boolean": True,
    "none": None,
    "list": [1, 2, 3],
    "dict": {"nested": "value"}
}

encoded = jsonable_encoder(data)
print(encoded)  # Already JSON-compatible, returned as-is

# Complex types that need encoding
complex_data = {
    "datetime": datetime.now(),
    "date": date.today(),
    "timedelta": timedelta(hours=2, minutes=30),
    "decimal": Decimal("10.50"),
    "uuid": uuid4(),
    "bytes": b"binary data",
    "set": {1, 2, 3}
}

encoded_complex = jsonable_encoder(complex_data)
print(encoded_complex)
# {
#     "datetime": "2024-01-15T10:30:00.123456",
#     "date": "2024-01-15",
#     "timedelta": "PT2H30M",
#     "decimal": 10.5,
#     "uuid": "123e4567-e89b-12d3-a456-426614174000",
#     "bytes": "YmluYXJ5IGRhdGE=",  # base64 encoded
#     "set": [1, 2, 3]
# }
```

### Pydantic Model Encoding

```python
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: int
    name: str
    email: str
    full_name: Optional[str] = Field(None, alias="fullName")
    created_at: datetime
    is_active: bool = True

class UserProfile(BaseModel):
    user: User
    preferences: dict
    login_count: int = 0

# Create model instances
user = User(
    id=1,
    name="john_doe",
    email="john@example.com",
    fullName="John Doe",
    created_at=datetime.now()
)

profile = UserProfile(
    user=user,
    preferences={"theme": "dark", "notifications": True}
)

# Encode with default settings
encoded = jsonable_encoder(profile)
print(encoded)

# Encode using aliases
encoded_with_aliases = jsonable_encoder(profile, by_alias=True)
print(encoded_with_aliases["user"]["fullName"])  # Uses alias

# Exclude certain fields
encoded_minimal = jsonable_encoder(
    profile, 
    exclude={"user": {"created_at"}, "login_count"}
)

# Include only specific fields
encoded_specific = jsonable_encoder(
    profile,
    include={"user": {"id", "name"}, "preferences"}
)

# Exclude unset fields
user_partial = User(id=2, name="jane", email="jane@example.com")
encoded_no_unset = jsonable_encoder(user_partial, exclude_unset=True)
# Won't include created_at if it wasn't explicitly set

# Exclude None values
user_with_none = User(
    id=3, 
    name="bob", 
    email="bob@example.com",
    full_name=None,  # Explicitly set to None
    created_at=datetime.now()
)
encoded_no_none = jsonable_encoder(user_with_none, exclude_none=True)
```

### Database Model Integration

```python
from fastapi import FastAPI, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
# Assuming SQLAlchemy models

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert SQLAlchemy model to JSON-compatible dict
    user_data = jsonable_encoder(user, sqlalchemy_safe=True)
    return user_data

@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Include related data, exclude sensitive fields
    profile_data = jsonable_encoder(
        user,
        include={
            "id", "name", "email", "created_at", "last_login",
            "profile": {"bio", "location", "website"},
            "posts": {"id", "title", "created_at"}
        },
        exclude={"password_hash", "email_verified_token"}
    )
    return profile_data
```

### Custom Fallback Function

```python
from fastapi.encoders import jsonable_encoder
import numpy as np
from typing import Any

# Custom fallback for handling NumPy arrays
def numpy_fallback(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    else:
        # Re-raise the TypeError to use default handling
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Data with NumPy objects
data_with_numpy = {
    "array": np.array([1, 2, 3, 4]),
    "matrix": np.array([[1, 2], [3, 4]]),
    "int64": np.int64(42),
    "float64": np.float64(3.14159)
}

encoded_numpy = jsonable_encoder(data_with_numpy, fallback=numpy_fallback)
print(encoded_numpy)
# {
#     "array": [1, 2, 3, 4],
#     "matrix": [[1, 2], [3, 4]],
#     "int64": 42,
#     "float64": 3.14159
# }
```

### Response Encoding in Endpoints

```python
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/complex-data")
def get_complex_data():
    complex_response = {
        "timestamp": datetime.now(),
        "data": {
            "measurements": [
                {"value": Decimal("123.456"), "unit": "kg"},
                {"value": Decimal("789.012"), "unit": "kg"}
            ],
            "metadata": {
                "id": uuid4(),
                "processed": True
            }
        }
    }
    
    # Encode the complex data structure
    encoded_response = jsonable_encoder(complex_response)
    return JSONResponse(content=encoded_response)

@app.post("/process-data")
def process_data(raw_data: dict):
    # Process and potentially modify data
    processed = {
        "original": raw_data,
        "processed_at": datetime.now(),
        "result": calculate_result(raw_data),
        "metadata": {
            "version": "1.0",
            "processor_id": uuid4()
        }
    }
    
    # Use jsonable_encoder to ensure everything is JSON-compatible
    return jsonable_encoder(processed, exclude_none=True)
```

### Time Delta Formatting Options

```python
from fastapi.encoders import jsonable_encoder
from datetime import timedelta

duration_data = {
    "short": timedelta(minutes=30),
    "medium": timedelta(hours=2, minutes=45),
    "long": timedelta(days=5, hours=3, minutes=20)
}

# ISO 8601 format (default)
iso_encoded = jsonable_encoder(duration_data, timedelta_isoformat="iso8601")
print(iso_encoded)
# {
#     "short": "PT30M",
#     "medium": "PT2H45M", 
#     "long": "P5DT3H20M"
# }

# Float format (total seconds)
float_encoded = jsonable_encoder(duration_data, timedelta_isoformat="float")
print(float_encoded)
# {
#     "short": 1800.0,
#     "medium": 9900.0,
#     "long": 443400.0
# }
```

## Types

```python { .api }
from typing import Any, Callable, Dict, List, Optional, Set, Union

# Include/exclude type for field selection
IncEx = Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any], None]

# Fallback function type
FallbackFunc = Callable[[Any], Any]

# Supported timedelta formats
TimedeltaIsoFormat = Union["iso8601", "float"]
```