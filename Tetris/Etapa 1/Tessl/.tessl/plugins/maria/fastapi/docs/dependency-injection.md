# Dependency Injection

FastAPI provides a powerful dependency injection system that allows sharing code, database connections, authentication, and other common functionality across endpoints. Dependencies are cached by default and can be overridden for testing.

## Capabilities

### Depends Function

Core dependency injection function that declares dependencies with optional caching control.

```python { .api }
def Depends(dependency: Callable = None, *, use_cache: bool = True) -> Any:
    """
    Declare a dependency for dependency injection.

    Parameters:
    - dependency: Callable that provides the dependency value
    - use_cache: Whether to cache the dependency result within a request

    Returns:
    Dependency declaration for use in function signatures

    The dependency callable can be:
    - A function that returns a value
    - A class constructor
    - Another dependency that uses Depends()
    - A callable with its own dependencies
    """
```

### Security Dependencies

Special dependency function for security-related dependencies with scope support for authorization.

```python { .api }
def Security(
    dependency: Callable = None,
    *,
    scopes: List[str] = None,
    use_cache: bool = True,
) -> Any:
    """
    Declare a security dependency with OAuth2 scopes support.

    Parameters:
    - dependency: Security scheme callable (e.g., OAuth2PasswordBearer)
    - scopes: List of required OAuth2 scopes for authorization
    - use_cache: Whether to cache the dependency result within a request

    Returns:
    Security dependency declaration for use in function signatures

    Used for endpoints that require specific permissions or scopes.
    """
```

## Usage Examples

### Basic Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

# Simple dependency function
def get_db():
    db = {"connection": "postgresql://..."}
    try:
        yield db
    finally:
        # Close connection
        pass

def get_current_user():
    return {"user_id": 1, "username": "john"}

@app.get("/items/")
def read_items(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    return {"db": db, "user": current_user}
```

### Class-based Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

class DatabaseService:
    def __init__(self):
        self.connection = "postgresql://..."
    
    def get_connection(self):
        return self.connection

class UserService:
    def __init__(self, db: DatabaseService = Depends(DatabaseService)):
        self.db = db
    
    def get_current_user(self):
        return {"user_id": 1, "username": "john"}

@app.get("/users/me")
def get_user_profile(user_service: UserService = Depends(UserService)):
    return user_service.get_current_user()
```

### Dependency with Parameters

```python
from fastapi import FastAPI, Depends, Query

app = FastAPI()

def common_parameters(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    return {"skip": skip, "limit": limit}

@app.get("/items/")
def read_items(commons: dict = Depends(common_parameters)):
    return {"params": commons}

@app.get("/users/")
def read_users(commons: dict = Depends(common_parameters)):
    return {"params": commons}
```

### Nested Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

def get_db():
    return {"connection": "active"}

def get_user_service(db=Depends(get_db)):
    return {"db": db, "service": "user_service"}

def get_current_user(user_service=Depends(get_user_service)):
    # Authentication logic using user_service
    return {"user_id": 1, "username": "john"}

def get_admin_user(current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user

@app.get("/admin/users")
def list_users(admin_user=Depends(get_admin_user)):
    return {"message": "Admin access granted", "admin": admin_user}
```

### Dependency Caching

```python
from fastapi import FastAPI, Depends
import time

app = FastAPI()

# Expensive operation that should be cached
def get_expensive_data():
    print("Computing expensive data...")
    time.sleep(1)  # Simulate expensive operation
    return {"data": "expensive_result", "timestamp": time.time()}

# Cached dependency (default behavior)
def cached_dependency():
    return get_expensive_data()

# Non-cached dependency
def non_cached_dependency():
    return get_expensive_data()

@app.get("/cached")
def endpoint_with_cached_deps(
    data1=Depends(cached_dependency),
    data2=Depends(cached_dependency)  # Same result, computed only once
):
    return {"data1": data1, "data2": data2}

@app.get("/non-cached")
def endpoint_with_non_cached_deps(
    data1=Depends(non_cached_dependency, use_cache=False),
    data2=Depends(non_cached_dependency, use_cache=False)  # Computed twice
):
    return {"data1": data1, "data2": data2}
```

### Global Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException

# Global authentication dependency
def verify_api_key(api_key: str = Header(...)):
    if api_key != "secret-api-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Apply dependency to entire application
app = FastAPI(dependencies=[Depends(verify_api_key)])

@app.get("/protected-endpoint")
def protected_endpoint():
    return {"message": "This endpoint requires API key"}

@app.get("/another-protected-endpoint")
def another_protected_endpoint():
    return {"message": "This endpoint also requires API key"}
```

### Router-level Dependencies

```python
from fastapi import FastAPI, APIRouter, Depends, HTTPException

app = FastAPI()

def admin_required():
    # Authentication logic
    return {"role": "admin"}

# Router with shared dependencies
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(admin_required)]
)

@admin_router.get("/users")
def admin_list_users():
    return {"users": ["admin", "user1", "user2"]}

@admin_router.delete("/users/{user_id}")
def admin_delete_user(user_id: int):
    return {"message": f"User {user_id} deleted"}

app.include_router(admin_router)
```

### Security Dependencies with Scopes

```python
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from typing import List

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access"
    }
)

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode token and return user
    return {"username": "john", "scopes": ["read", "write"]}

def check_scopes(required_scopes: List[str]):
    def scopes_checker(
        current_user=Security(oauth2_scheme, scopes=required_scopes)
    ):
        user_scopes = current_user.get("scopes", [])
        for scope in required_scopes:
            if scope not in user_scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Not enough permissions. Required: {required_scopes}"
                )
        return current_user
    return scopes_checker

@app.get("/read-data")
def read_data(
    current_user=Security(oauth2_scheme, scopes=["read"])
):
    return {"data": "sensitive data", "user": current_user}

@app.post("/write-data")
def write_data(
    current_user=Security(oauth2_scheme, scopes=["write"])
):
    return {"message": "Data written", "user": current_user}

@app.delete("/admin-action")
def admin_action(
    current_user=Security(oauth2_scheme, scopes=["admin"])
):
    return {"message": "Admin action performed", "user": current_user}
```

### Dependency Override for Testing

```python
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

app = FastAPI()

def get_db():
    return {"connection": "production_db"}

def get_current_user():
    return {"user_id": 1, "username": "john"}

@app.get("/items/")
def read_items(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    return {"db": db, "user": current_user}

# Test with dependency overrides
def test_read_items():
    def override_get_db():
        return {"connection": "test_db"}
    
    def override_get_current_user():
        return {"user_id": 999, "username": "test_user"}
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    client = TestClient(app)
    response = client.get("/items/")
    
    # Clean up overrides
    app.dependency_overrides = {}
    
    assert response.status_code == 200
    data = response.json()
    assert data["db"]["connection"] == "test_db"
    assert data["user"]["username"] == "test_user"
```

### Dependency with Cleanup

```python
from fastapi import FastAPI, Depends
import asyncio

app = FastAPI()

class DatabaseConnection:
    def __init__(self):
        self.connection = None
    
    async def connect(self):
        print("Connecting to database...")
        self.connection = "active_connection"
        return self
    
    async def disconnect(self):
        print("Disconnecting from database...")
        self.connection = None

async def get_database():
    db = DatabaseConnection()
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()

@app.get("/items/")
async def read_items(db: DatabaseConnection = Depends(get_database)):
    return {"connection_status": db.connection}
```