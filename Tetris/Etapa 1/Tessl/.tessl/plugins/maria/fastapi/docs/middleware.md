# Middleware

FastAPI provides comprehensive middleware support for processing HTTP requests and responses. Middleware components can modify requests before they reach route handlers and modify responses before they're sent to clients. FastAPI includes built-in middleware classes and supports custom middleware development.

## Capabilities

### Base Middleware Class

Base class for creating custom middleware components that process requests and responses.

```python { .api }
class Middleware:
    def __init__(self, cls: type, **options: Any) -> None:
        """
        Base middleware class for custom middleware.
        
        Parameters:
        - cls: Middleware class to instantiate
        - options: Configuration options for the middleware
        """
        self.cls = cls
        self.options = options
```

### Middleware Decorator

Decorator method on FastAPI and APIRouter instances for adding middleware functions.

```python { .api }
def middleware(self, middleware_type: str) -> Callable[[Callable], Callable]:
    """
    Decorator for adding middleware to the application.

    Parameters:
    - middleware_type: Type of middleware ("http" for HTTP middleware)
    
    Returns:
    Decorator function for middleware registration
    """
```

### CORS Middleware

Cross-Origin Resource Sharing middleware for handling cross-domain requests.

```python { .api }
class CORSMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers: List[str] = None,
        max_age: int = 600
    ) -> None:
        """
        Cross-Origin Resource Sharing middleware.
        
        Parameters:
        - app: ASGI application to wrap
        - allow_origins: List of allowed origin URLs
        - allow_methods: List of allowed HTTP methods
        - allow_headers: List of allowed request headers
        - allow_credentials: Allow credentials in cross-origin requests
        - allow_origin_regex: Regex pattern for allowed origins
        - expose_headers: List of headers to expose to the browser
        - max_age: Maximum age for preflight cache
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with CORS handling."""
```

### GZip Middleware

Middleware for compressing HTTP responses using GZip compression.

```python { .api }
class GZipMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 9
    ) -> None:
        """
        GZip compression middleware.
        
        Parameters:
        - app: ASGI application to wrap
        - minimum_size: Minimum response size to compress (bytes)
        - compresslevel: GZip compression level (1-9)
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with GZip compression."""
```

### HTTPS Redirect Middleware

Middleware for enforcing HTTPS connections by redirecting HTTP requests.

```python { .api }
class HTTPSRedirectMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        """
        HTTPS redirect enforcement middleware.
        
        Parameters:
        - app: ASGI application to wrap
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with HTTPS redirect."""
```

### Trusted Host Middleware

Middleware for validating Host headers to prevent Host header attacks.

```python { .api }
class TrustedHostMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True
    ) -> None:
        """
        Trusted host validation middleware.
        
        Parameters:
        - app: ASGI application to wrap
        - allowed_hosts: List of allowed host patterns
        - www_redirect: Redirect www subdomain to non-www
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with host validation."""
```

### WSGI Middleware

Middleware for mounting WSGI applications within ASGI applications.

```python { .api }
class WSGIMiddleware:
    def __init__(self, app: ASGIApp, wsgi_app: WSGIApp) -> None:
        """
        WSGI application mounting middleware.
        
        Parameters:
        - app: ASGI application to wrap
        - wsgi_app: WSGI application to mount
        """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request with WSGI app mounting."""
```

### Custom Middleware Interface

Interface for creating custom HTTP middleware functions.

```python { .api }
async def custom_middleware_function(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Custom middleware function signature.
    
    Parameters:
    - request: HTTP request object
    - call_next: Function to call next middleware/route handler
    
    Returns:
    Response object (potentially modified)
    """
```

## Usage Examples

### Basic Custom Middleware

```python
import time
from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### CORS Middleware Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://myapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Custom-Header"],
    max_age=600
)

@app.get("/api/data")
async def get_data():
    return {"data": "This endpoint supports CORS"}
```

### GZip Compression Middleware

```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable GZip compression for responses larger than 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/large-data")
async def get_large_data():
    # Return large response that will be compressed
    return {"data": "x" * 2000, "message": "This response will be compressed"}
```

### HTTPS Redirect Middleware

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Redirect all HTTP requests to HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

@app.get("/secure-endpoint")
async def secure_endpoint():
    return {"message": "This endpoint requires HTTPS"}
```

### Trusted Host Middleware

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# Only allow requests from specific hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com", "localhost"]
)

@app.get("/")
async def read_main():
    return {"message": "Request from trusted host"}
```

### Authentication Middleware

```python
import jwt
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    # Skip authentication for certain paths
    if request.url.path in ["/login", "/docs", "/openapi.json"]:
        response = await call_next(request)
        return response
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "Missing or invalid authorization header"}
        )
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Verify JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        request.state.user = payload
    except jwt.InvalidTokenError:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid token"}
        )
    
    response = await call_next(request)
    return response

@app.get("/protected")
async def protected_route(request: Request):
    return {"message": f"Hello {request.state.user['sub']}"}
```

### Logging Middleware

```python
import logging
import time
from fastapi import FastAPI, Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client": request.client.host if request.client else None
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} in {process_time:.4f}s",
        extra={
            "status_code": response.status_code,
            "process_time": process_time,
            "path": request.url.path
        }
    )
    
    return response

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### Rate Limiting Middleware

```python
import time
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# Simple in-memory rate limiter
rate_limiter = defaultdict(list)
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Clean old requests
    rate_limiter[client_ip] = [
        req_time for req_time in rate_limiter[client_ip]
        if current_time - req_time < RATE_WINDOW
    ]
    
    # Check rate limit
    if len(rate_limiter[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(RATE_WINDOW)}
        )
    
    # Add current request
    rate_limiter[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### Error Handling Middleware

```python
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Re-raise HTTPExceptions to be handled by FastAPI
        raise
    except Exception as e:
        # Handle unexpected exceptions
        error_id = str(hash(str(e) + str(time.time())))
        
        # Log the full traceback
        logger.error(
            f"Unhandled exception {error_id}: {str(e)}",
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "error_id": error_id,
                "message": "An unexpected error occurred"
            }
        )

@app.get("/error")
async def trigger_error():
    raise ValueError("This is a test error")

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### Multiple Middleware Stack

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import time

app = FastAPI()

# Add multiple middleware in order
# Note: Middleware is executed in reverse order of addition

# 1. GZip (executed last - compresses final response)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS (executed second to last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Custom timing middleware (executed first)
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def read_main():
    return {"message": "Hello World", "data": "x" * 1500}  # Large response for GZip
```

### Conditional Middleware

```python
from fastapi import FastAPI, Request
import os

app = FastAPI()

# Only add CORS middleware in development
if os.getenv("ENVIRONMENT") == "development":
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Security middleware for production
if os.getenv("ENVIRONMENT") == "production":
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["myapp.com", "*.myapp.com"]
    )

@app.middleware("http")
async def environment_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Environment"] = os.getenv("ENVIRONMENT", "unknown")
    return response

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### Custom Middleware Class

```python
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

app = FastAPI()

# Add custom middleware class
app.add_middleware(RequestIDMiddleware)

@app.get("/")
async def read_main(request: Request):
    return {
        "message": "Hello World",
        "request_id": request.state.request_id
    }
```