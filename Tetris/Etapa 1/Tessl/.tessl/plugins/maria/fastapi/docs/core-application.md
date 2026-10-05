# Core Application

The FastAPI class is the main application class that serves as the central instance for managing all routes, middleware, dependencies, and configuration. It provides decorators for all HTTP methods and handles the entire application lifecycle.

## Capabilities

### FastAPI Application Class

The main application class that creates a FastAPI instance with comprehensive configuration options for API metadata, documentation, middleware, and behavior customization.

```python { .api }
class FastAPI:
    def __init__(
        self,
        *,
        debug: bool = False,
        routes: List[BaseRoute] = None,
        title: str = "FastAPI",
        description: str = "",
        version: str = "0.1.0",
        openapi_url: str = "/openapi.json",
        openapi_tags: List[dict] = None,
        servers: List[dict] = None,
        dependencies: List[Depends] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        swagger_ui_oauth2_redirect_url: str = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: dict = None,
        middleware: List[Middleware] = None,
        exception_handlers: dict = None,
        on_startup: List[Callable] = None,
        on_shutdown: List[Callable] = None,
        lifespan: Lifespan = None,
        root_path: str = "",
        root_path_in_servers: bool = True,
        responses: dict = None,
        callbacks: List[BaseRoute] = None,
        webhooks: APIRouter = None,
        deprecated: bool = None,
        include_in_schema: bool = True,
        swagger_ui_parameters: dict = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
        **extra: Any,
    ) -> None:
        """
        Create a FastAPI application instance.

        Parameters:
        - debug: Enable debug mode
        - routes: List of routes to include in the application
        - title: API title for documentation
        - description: API description for documentation
        - version: API version
        - openapi_url: URL for the OpenAPI JSON schema
        - openapi_tags: List of tags for grouping operations
        - servers: List of servers for the API
        - dependencies: List of global dependencies
        - default_response_class: Default response class for routes
        - docs_url: URL for Swagger UI documentation
        - redoc_url: URL for ReDoc documentation
        - middleware: List of middleware to include
        - exception_handlers: Dictionary of exception handlers
        - on_startup: List of startup event handlers
        - on_shutdown: List of shutdown event handlers
        - lifespan: Application lifespan context manager
        """
```

### HTTP Method Decorators

Decorators for defining API endpoints that handle different HTTP methods with automatic OpenAPI documentation generation.

```python { .api }
def get(
    self,
    path: str,
    *,
    response_model: Any = Default(None),
    status_code: int = None,
    tags: List[str] = None,
    dependencies: List[Depends] = None,
    summary: str = None,
    description: str = None,
    response_description: str = "Successful Response",
    responses: dict = None,
    deprecated: bool = None,
    operation_id: str = None,
    response_model_include: IncEx = None,
    response_model_exclude: IncEx = None,
    response_model_by_alias: bool = True,
    response_model_exclude_unset: bool = False,
    response_model_exclude_defaults: bool = False,
    response_model_exclude_none: bool = False,
    include_in_schema: bool = True,
    response_class: Type[Response] = Default(JSONResponse),
    name: str = None,
    callbacks: List[BaseRoute] = None,
    openapi_extra: dict = None,
    generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """
    Decorator for GET endpoints.

    Parameters:
    - path: URL path for the endpoint
    - response_model: Pydantic model for response serialization
    - status_code: HTTP status code for successful responses
    - tags: List of tags for grouping in documentation
    - dependencies: List of dependencies for this endpoint
    - summary: Short summary for documentation
    - description: Detailed description for documentation
    - responses: Additional response models for different status codes
    - deprecated: Mark endpoint as deprecated
    - include_in_schema: Include endpoint in OpenAPI schema
    """

def post(
    self,
    path: str,
    *,
    response_model: Any = Default(None),
    status_code: int = None,
    tags: List[str] = None,
    dependencies: List[Depends] = None,
    summary: str = None,
    description: str = None,
    response_description: str = "Successful Response",
    responses: dict = None,
    deprecated: bool = None,
    operation_id: str = None,
    response_model_include: IncEx = None,
    response_model_exclude: IncEx = None,
    response_model_by_alias: bool = True,
    response_model_exclude_unset: bool = False,
    response_model_exclude_defaults: bool = False,
    response_model_exclude_none: bool = False,
    include_in_schema: bool = True,
    response_class: Type[Response] = Default(JSONResponse),
    name: str = None,
    callbacks: List[BaseRoute] = None,
    openapi_extra: dict = None,
    generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for POST endpoints."""

def put(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for PUT endpoints."""

def delete(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for DELETE endpoints."""

def patch(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for PATCH endpoints."""

def head(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for HEAD endpoints."""

def options(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for OPTIONS endpoints."""

def trace(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for TRACE endpoints."""
```

### WebSocket Decorator

Decorator for defining WebSocket endpoints for real-time bidirectional communication.

```python { .api }
def websocket(
    self,
    path: str,
    *,
    name: str = None,
    dependencies: List[Depends] = None,
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """
    Decorator for WebSocket endpoints.

    Parameters:
    - path: WebSocket URL path
    - name: Endpoint name for URL generation
    - dependencies: List of dependencies for this WebSocket
    """
```

### Router Integration

Methods for including APIRouter instances and adding routes programmatically.

```python { .api }
def include_router(
    self,
    router: APIRouter,
    *,
    prefix: str = "",
    tags: List[str] = None,
    dependencies: List[Depends] = None,
    default_response_class: Type[Response] = Default(JSONResponse),
    responses: dict = None,
    callbacks: List[BaseRoute] = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
) -> None:
    """
    Include an APIRouter in the application.

    Parameters:
    - router: APIRouter instance to include
    - prefix: URL prefix for all routes in the router
    - tags: List of tags to add to all routes
    - dependencies: List of dependencies to add to all routes
    - responses: Additional response models for all routes
    - deprecated: Mark all routes as deprecated
    - include_in_schema: Include router routes in OpenAPI schema
    """

def add_api_route(
    self,
    path: str,
    endpoint: Callable,
    *,
    methods: List[str] = None,
    name: str = None,
    response_model: Any = Default(None),
    status_code: int = None,
    tags: List[str] = None,
    dependencies: List[Depends] = None,
    summary: str = None,
    description: str = None,
    response_description: str = "Successful Response",
    responses: dict = None,
    deprecated: bool = None,
    operation_id: str = None,
    response_model_include: IncEx = None,
    response_model_exclude: IncEx = None,
    response_model_by_alias: bool = True,
    response_model_exclude_unset: bool = False,
    response_model_exclude_defaults: bool = False,
    response_model_exclude_none: bool = False,
    include_in_schema: bool = True,
    response_class: Type[Response] = Default(JSONResponse),
    callbacks: List[BaseRoute] = None,
    openapi_extra: dict = None,
    generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
) -> None:
    """
    Add an API route programmatically.

    Parameters:
    - path: URL path for the route
    - endpoint: Function to handle the route
    - methods: List of HTTP methods for the route
    - Additional parameters same as HTTP method decorators
    """

def add_api_websocket_route(
    self,
    path: str,
    endpoint: Callable,
    *,
    name: str = None,
    dependencies: List[Depends] = None,
) -> None:
    """
    Add a WebSocket route programmatically.

    Parameters:
    - path: WebSocket URL path
    - endpoint: Function to handle the WebSocket
    - name: Route name for URL generation
    - dependencies: List of dependencies for the WebSocket
    """
```

### Middleware and Exception Handling

Methods for adding middleware and exception handlers to the application.

```python { .api }
def middleware(self, middleware_type: str) -> Callable[[Callable], Callable]:
    """
    Decorator for adding middleware to the application.

    Parameters:
    - middleware_type: Type of middleware ("http" for HTTP middleware)
    """

def exception_handler(
    self,
    exc_class_or_status_code: Union[int, Exception]
) -> Callable[[Callable], Callable]:
    """
    Decorator for adding exception handlers.

    Parameters:
    - exc_class_or_status_code: Exception class or HTTP status code to handle
    """
```

### OpenAPI Generation

Method for generating and accessing the OpenAPI schema.

```python { .api }
def openapi(self) -> dict:
    """
    Generate and return the OpenAPI schema for the application.

    Returns:
    Dictionary containing the complete OpenAPI specification
    """
```

### Application Properties

Key properties available on FastAPI application instances.

```python { .api }
# Application properties
openapi_version: str  # OpenAPI specification version
openapi_schema: dict  # Generated OpenAPI schema (cached)
webhooks: APIRouter   # APIRouter for webhook endpoints
root_path: str        # Application root path
state: State          # Application state object for sharing data
dependency_overrides: dict  # Dependency override mapping
router: APIRouter     # Main APIRouter instance
```

## Usage Examples

### Basic Application Setup

```python
from fastapi import FastAPI

# Create application with custom configuration
app = FastAPI(
    title="My API",
    description="A comprehensive API for my application",
    version="1.0.0",
    docs_url="/documentation",
    redoc_url="/redoc-docs"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to my API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### Application with Global Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    if token.credentials != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# Global dependency applied to all routes
app = FastAPI(dependencies=[Depends(verify_token)])

@app.get("/protected")
def protected_endpoint():
    return {"message": "This is a protected endpoint"}
```

### Application with Custom Exception Handler

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": request.url.path}
    )

@app.get("/error")
def trigger_error():
    raise HTTPException(status_code=404, detail="Resource not found")
```