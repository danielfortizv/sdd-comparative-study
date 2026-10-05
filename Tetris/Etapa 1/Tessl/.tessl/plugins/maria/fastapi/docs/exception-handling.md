# Exception Handling

FastAPI provides comprehensive exception handling capabilities that integrate with HTTP status codes, automatic error responses, and custom exception handlers. The framework includes built-in exceptions for common scenarios and allows for custom exception handling patterns.

## Capabilities

### HTTP Exception

The primary exception class for handling HTTP errors with proper status codes and response formatting.

```python { .api }
class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Dict[str, str] = None
    ) -> None:
        """
        HTTP exception with status code and detail message.
        
        Parameters:
        - status_code: HTTP status code (400, 401, 404, 500, etc.)
        - detail: Error detail message or structured data
        - headers: Additional HTTP headers to include in error response
        """
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
```

### WebSocket Exception

Exception class specifically for WebSocket connection errors.

```python { .api }
class WebSocketException(Exception):
    def __init__(
        self,
        code: int,
        reason: str = None
    ) -> None:
        """
        WebSocket error exception.
        
        Parameters:
        - code: WebSocket close code (1000-4999)
        - reason: Human-readable close reason
        """
        self.code = code
        self.reason = reason
```

### FastAPI Error

Generic runtime error exception for FastAPI framework issues.

```python { .api }
class FastAPIError(Exception):
    def __init__(self, message: str = None) -> None:
        """
        Generic FastAPI runtime error.
        
        Parameters:
        - message: Error message describing the issue
        """
        self.message = message
```

### Validation Exceptions

Exception classes for handling request and response validation errors with detailed error information.

```python { .api }
class ValidationException(Exception):
    def __init__(self, errors: List[dict]) -> None:
        """
        Base validation error exception.
        
        Parameters:
        - errors: List of validation error dictionaries
        """
        self.errors = errors

class RequestValidationError(ValidationException):
    def __init__(self, errors: List[ErrorWrapper]) -> None:
        """
        Request validation error with detailed error information.
        
        Parameters:
        - errors: List of Pydantic ErrorWrapper objects containing
                 field-specific validation error details
        """
        self.errors = errors
        self.body = getattr(errors, "body", None)

class WebSocketRequestValidationError(ValidationException):
    def __init__(self, errors: List[ErrorWrapper]) -> None:
        """
        WebSocket request validation error.
        
        Parameters:
        - errors: List of Pydantic ErrorWrapper objects for WebSocket
                 parameter validation failures
        """
        self.errors = errors

class ResponseValidationError(ValidationException):
    def __init__(self, errors: List[ErrorWrapper]) -> None:
        """
        Response validation error for response model validation failures.
        
        Parameters:
        - errors: List of Pydantic ErrorWrapper objects containing
                 response validation error details
        """
        self.errors = errors
```

### Exception Handler Decorator

Decorator method for registering custom exception handlers on FastAPI and APIRouter instances.

```python { .api }
def exception_handler(
    self,
    exc_class_or_status_code: Union[int, Type[Exception]]
) -> Callable[[Callable], Callable]:
    """
    Decorator for adding exception handlers.

    Parameters:
    - exc_class_or_status_code: Exception class or HTTP status code to handle

    Returns:
    Decorator function for exception handler registration
    """
```

### Exception Handler Function Type

Type signature for custom exception handler functions.

```python { .api }
async def exception_handler_function(
    request: Request,
    exc: Exception
) -> Response:
    """
    Exception handler function signature.
    
    Parameters:
    - request: HTTP request object
    - exc: Exception instance that was raised
    
    Returns:
    Response object to send to client
    """
```

## Usage Examples

### Basic HTTP Exception Handling

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    if item_id < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item ID must be positive",
            headers={"X-Error": "Invalid item ID"}
        )
    return {"item_id": item_id, "name": f"Item {item_id}"}
```

### Custom Exception Handler

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "body": exc.body
        }
    )

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id == 42:
        raise HTTPException(status_code=418, detail="I'm a teapot")
    return {"item_id": item_id}
```

### Custom Exception Classes

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# Custom exception classes
class ItemNotFoundError(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id
        self.message = f"Item with ID {item_id} not found"
        super().__init__(self.message)

class InsufficientPermissionsError(Exception):
    def __init__(self, required_role: str, user_role: str):
        self.required_role = required_role
        self.user_role = user_role
        self.message = f"Required role: {required_role}, user role: {user_role}"
        super().__init__(self.message)

class BusinessLogicError(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

# Exception handlers
@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Item Not Found",
            "message": exc.message,
            "item_id": exc.item_id
        }
    )

@app.exception_handler(InsufficientPermissionsError)
async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissionsError):
    return JSONResponse(
        status_code=403,
        content={
            "error": "Insufficient Permissions",
            "message": exc.message,
            "required_role": exc.required_role,
            "user_role": exc.user_role
        }
    )

@app.exception_handler(BusinessLogicError)
async def business_logic_handler(request: Request, exc: BusinessLogicError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Business Logic Error",
            "message": exc.message,
            "error_code": exc.error_code
        }
    )

# Routes using custom exceptions
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id == 999:
        raise ItemNotFoundError(item_id)
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int, user_role: str = "user"):
    if user_role != "admin":
        raise InsufficientPermissionsError("admin", user_role)
    if item_id <= 0:
        raise BusinessLogicError("Cannot delete items with non-positive IDs", "INVALID_ID")
    return {"message": f"Item {item_id} deleted"}
```

### Exception Handling with Logging

```python
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the exception
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Return generic error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log HTTP exceptions
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        },
        headers=exc.headers
    )

@app.get("/error-demo/{error_type}")
async def error_demo(error_type: str):
    if error_type == "404":
        raise HTTPException(status_code=404, detail="Resource not found")
    elif error_type == "500":
        raise Exception("Simulated internal server error")
    elif error_type == "400":
        raise HTTPException(status_code=400, detail="Bad request")
    return {"message": "No error"}
```

### Validation Error Customization

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI()

class ItemModel(BaseModel):
    name: str
    price: float
    description: str = None

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Failed",
            "message": "The request contains invalid data",
            "errors": errors,
            "total_errors": len(errors)
        }
    )

@app.post("/items/")
async def create_item(item: ItemModel):
    return {"message": "Item created", "item": item}
```

### WebSocket Exception Handling

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import WebSocketException

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            
            # Validate WebSocket data
            if not data.strip():
                raise WebSocketException(
                    code=1003,
                    reason="Empty message not allowed"
                )
            
            if len(data) > 1000:
                raise WebSocketException(
                    code=1009,
                    reason="Message too large"
                )
            
            # Echo the message back
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except WebSocketException as e:
        print(f"WebSocket error {e.code}: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)
    except Exception as e:
        print(f"Unexpected WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
```

### Exception Handling in Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException, Header

app = FastAPI()

def verify_auth_header(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.replace("Bearer ", "")
    if token != "valid-token":
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token

def get_user_role(token: str = Depends(verify_auth_header)):
    # Simulate role extraction from token
    if token == "valid-token":
        return "admin"
    return "user"

def require_admin_role(role: str = Depends(get_user_role)):
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin role required"
        )
    return role

@app.get("/admin/users")
async def list_users(role: str = Depends(require_admin_role)):
    return {"users": ["user1", "user2"], "requesting_role": role}

@app.get("/profile")
async def get_profile(token: str = Depends(verify_auth_header)):
    return {"message": "Profile data", "token": token}
```

### Context Manager for Exception Handling

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import asyncio

app = FastAPI()

@asynccontextmanager
async def handle_database_errors():
    try:
        yield
    except ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Database operation timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    async with handle_database_errors():
        # Simulate database operations
        if user_id == 1:
            raise ConnectionError("DB connection lost")
        elif user_id == 2:
            await asyncio.sleep(10)  # Simulate timeout
            raise TimeoutError("Operation timed out")
        elif user_id == 3:
            raise Exception("Unknown database error")
        
        return {"user_id": user_id, "name": f"User {user_id}"}
```