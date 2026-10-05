# FastAPI

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python based on standard Python type hints. It provides automatic API documentation, data validation, serialization, and authentication capabilities with exceptional performance on par with NodeJS and Go.

## Package Information

- **Package Name**: fastapi
- **Language**: Python
- **Installation**: `pip install "fastapi[standard]"`
- **Requirements**: Python 3.8+
- **Main Dependencies**: Starlette, Pydantic

## Core Imports

```python
from fastapi import FastAPI
```

Common imports for building APIs:

```python
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body, Header, Cookie, Form, File
from fastapi import Request, Response, BackgroundTasks
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import UploadFile, __version__, status
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder
```

## Basic Usage

```python
from fastapi import FastAPI, Query
from typing import Optional

# Create FastAPI application
app = FastAPI(
    title="My API",
    description="A simple API example",
    version="1.0.0"
)

# Simple GET endpoint
@app.get("/")
def read_root():
    return {"Hello": "World"}

# GET endpoint with path parameter
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = Query(None)):
    return {"item_id": item_id, "q": q}

# POST endpoint with request body
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None

@app.post("/items/")
def create_item(item: Item):
    return item

# Run with: fastapi dev main.py   (development, auto-reload)
# Run with: fastapi run main.py   (production)
```

## Architecture

FastAPI builds on the Starlette ASGI framework and uses Pydantic for data validation:

- **FastAPI Application**: Main application class that manages routes, middleware, and configuration
- **APIRouter**: Router for organizing and grouping related endpoints
- **Parameter Functions**: Type-safe parameter declaration (Query, Path, Body, etc.)
- **Pydantic Integration**: Automatic request/response validation and serialization
- **Starlette Foundation**: High-performance ASGI framework providing core web functionality
- **Automatic Documentation**: OpenAPI schema generation with interactive Swagger UI and ReDoc

This architecture enables rapid development of production-ready APIs with automatic validation, serialization, and documentation generation while maintaining high performance and type safety.

## Capabilities

### Core Application

Main FastAPI application class and basic routing functionality. The FastAPI class serves as the central application instance that manages all routes, middleware, dependencies, and configuration.

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
        **extra: Any,
    ) -> None: ...
    
    def get(self, path: str, **kwargs) -> Callable: ...
    def post(self, path: str, **kwargs) -> Callable: ...
    def put(self, path: str, **kwargs) -> Callable: ...
    def delete(self, path: str, **kwargs) -> Callable: ...
    def patch(self, path: str, **kwargs) -> Callable: ...
    def head(self, path: str, **kwargs) -> Callable: ...
    def options(self, path: str, **kwargs) -> Callable: ...
    def trace(self, path: str, **kwargs) -> Callable: ...
    def websocket(self, path: str, **kwargs) -> Callable: ...
    
    def include_router(self, router: APIRouter, **kwargs) -> None: ...
    def add_api_route(self, path: str, endpoint: Callable, **kwargs) -> None: ...
    def add_api_websocket_route(self, path: str, endpoint: Callable, **kwargs) -> None: ...
    def middleware(self, middleware_type: str) -> Callable: ...
    def exception_handler(self, exc_class_or_status_code: Union[int, Exception]) -> Callable: ...
```

[Core Application](./core-application.md)

### API Routing

Router for organizing and grouping related API endpoints with shared configuration, middleware, and dependencies.

```python { .api }
class APIRouter:
    def __init__(
        self,
        *,
        prefix: str = "",
        tags: List[str] = None,
        dependencies: List[Depends] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: dict = None,
        callbacks: List[BaseRoute] = None,
        routes: List[BaseRoute] = None,
        redirect_slashes: bool = True,
        default: ASGIApp = None,
        dependency_overrides_provider: Any = None,
        route_class: Type[APIRoute] = APIRoute,
        on_startup: List[Callable] = None,
        on_shutdown: List[Callable] = None,
        lifespan: Lifespan = None,
        deprecated: bool = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> None: ...
    
    def get(self, path: str, **kwargs) -> Callable: ...
    def post(self, path: str, **kwargs) -> Callable: ...
    def put(self, path: str, **kwargs) -> Callable: ...
    def delete(self, path: str, **kwargs) -> Callable: ...
    def patch(self, path: str, **kwargs) -> Callable: ...
    def head(self, path: str, **kwargs) -> Callable: ...
    def options(self, path: str, **kwargs) -> Callable: ...
    def trace(self, path: str, **kwargs) -> Callable: ...
    def websocket(self, path: str, **kwargs) -> Callable: ...
    
    def include_router(self, router: APIRouter, **kwargs) -> None: ...
    def add_api_route(self, path: str, endpoint: Callable, **kwargs) -> None: ...
```

[API Routing](./api-routing.md)

### Request Parameters

Type-safe parameter declaration functions for handling path parameters, query parameters, headers, cookies, request bodies, form data, and file uploads.

```python { .api }
def Path(
    default: Any = ...,
    *,
    alias: str = None,
    title: str = None,
    description: str = None,
    gt: float = None,
    ge: float = None,
    lt: float = None,
    le: float = None,
    min_length: int = None,
    max_length: int = None,
    regex: str = None,
    example: Any = None,
    examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any: ...

def Query(
    default: Any = Undefined,
    *,
    alias: str = None,
    title: str = None,
    description: str = None,
    gt: float = None,
    ge: float = None,
    lt: float = None,
    le: float = None,
    min_length: int = None,
    max_length: int = None,
    regex: str = None,
    example: Any = None,
    examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any: ...

def Body(
    default: Any = Undefined,
    *,
    embed: bool = None,
    media_type: str = "application/json",
    alias: str = None,
    title: str = None,
    description: str = None,
    example: Any = None,
    examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any: ...

def Form(
    default: Any = Undefined,
    *,
    media_type: str = "application/x-www-form-urlencoded",
    alias: str = None,
    title: str = None,
    description: str = None,
    example: Any = None,
    examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any: ...

def File(
    default: Any = Undefined,
    *,
    media_type: str = "multipart/form-data",
    alias: str = None,
    title: str = None,
    description: str = None,
    example: Any = None,
    examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any: ...
```

[Request Parameters](./request-parameters.md)

### Dependency Injection

Powerful dependency injection system for sharing code, database connections, authentication, and other common functionality across endpoints.

```python { .api }
def Depends(dependency: Callable = None, *, use_cache: bool = True) -> Any: ...

def Security(
    dependency: Callable = None,
    *,
    scopes: List[str] = None,
    use_cache: bool = True,
) -> Any: ...
```

[Dependency Injection](./dependency-injection.md)

### Request and Response Handling

Request and response objects for accessing HTTP data and customizing response behavior.

```python { .api }
class Request:
    # Starlette Request object with all HTTP request functionality
    pass

class Response:
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None: ...

class JSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None: ...

class UploadFile:
    filename: str
    content_type: str
    file: BinaryIO
    
    async def read(self, size: int = -1) -> bytes: ...
    async def readline(self, size: int = -1) -> bytes: ...
    async def readlines(self) -> List[bytes]: ...
    async def write(self, data: bytes) -> None: ...
    async def seek(self, offset: int) -> None: ...
    async def close(self) -> None: ...
```

[Request and Response](./request-response.md)

### WebSocket Support

WebSocket support for real-time bidirectional communication between client and server.

```python { .api }
class WebSocket:
    # Starlette WebSocket object with full WebSocket functionality
    async def accept(self, subprotocol: str = None, headers: dict = None) -> None: ...
    async def receive_text(self) -> str: ...
    async def receive_bytes(self) -> bytes: ...
    async def receive_json(self) -> Any: ...
    async def send_text(self, data: str) -> None: ...
    async def send_bytes(self, data: bytes) -> None: ...
    async def send_json(self, data: Any) -> None: ...
    async def close(self, code: int = 1000, reason: str = None) -> None: ...

class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000, reason: str = None) -> None: ...
```

[WebSocket Support](./websocket-support.md)

### Security and Authentication

Comprehensive security components for API key authentication, HTTP authentication (Basic, Bearer, Digest), and OAuth2 flows.

```python { .api }
class HTTPBearer:
    def __init__(
        self,
        *,
        bearerFormat: str = None,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True,
    ) -> None: ...

class OAuth2PasswordBearer:
    def __init__(
        self,
        tokenUrl: str,
        *,
        scheme_name: str = None,
        scopes: dict = None,
        description: str = None,
        auto_error: bool = True,
    ) -> None: ...

class APIKeyHeader:
    def __init__(
        self,
        *,
        name: str,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True,
    ) -> None: ...
```

[Security and Authentication](./security-authentication.md)

### Exception Handling

Exception classes for handling HTTP errors and WebSocket errors with proper status codes and error details.

```python { .api }
class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: dict = None,
    ) -> None: ...
    
    status_code: int
    detail: Any
    headers: dict

class WebSocketException(Exception):
    def __init__(self, code: int, reason: str = None) -> None: ...
    
    code: int
    reason: str
```

[Exception Handling](./exception-handling.md)

### Middleware

Middleware components for cross-cutting concerns like CORS, compression, security headers, and custom request/response processing.

```python { .api }
class CORSMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
    ) -> None: ...
```

[Middleware](./middleware.md)

### Background Tasks

Background task execution system for running tasks after sending the response to the client.

```python { .api }
class BackgroundTasks:
    def add_task(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
```

[Background Tasks](./background-tasks.md)

### Static Files and Templating

Static file serving and HTML template rendering capabilities for web applications that need to serve frontend content alongside API endpoints.

```python { .api }
class StaticFiles:
    def __init__(
        self,
        *,
        directory: str = None,
        packages: List[str] = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
    ) -> None: ...

class Jinja2Templates:
    def __init__(self, directory: str) -> None: ...
    def TemplateResponse(
        self,
        name: str,
        context: dict,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> TemplateResponse: ...
```

[Static Files and Templating](./static-templating.md)

### Testing Support

Test client for testing FastAPI applications with comprehensive HTTP request simulation capabilities.

```python { .api }
class TestClient:
    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: str = "asyncio",
        backend_options: dict = None,
        cookies: httpx.Cookies = None,
        headers: dict = None,
        follow_redirects: bool = False,
    ) -> None: ...
    
    def get(self, url: str, **kwargs) -> httpx.Response: ...
    def post(self, url: str, **kwargs) -> httpx.Response: ...
    def put(self, url: str, **kwargs) -> httpx.Response: ...
    def delete(self, url: str, **kwargs) -> httpx.Response: ...
    def patch(self, url: str, **kwargs) -> httpx.Response: ...
    def head(self, url: str, **kwargs) -> httpx.Response: ...
    def options(self, url: str, **kwargs) -> httpx.Response: ...
```

[Testing Support](./testing.md)

### Data Utilities

Utility functions for data encoding and serialization, particularly for converting Python objects to JSON-compatible formats.

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
) -> Any: ...
```

[Data Utilities](./data-utilities.md)

### Advanced Response Types

High-performance JSON response classes and additional response types for various content delivery needs.

```python { .api }
class UJSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None: ...

class ORJSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None: ...

class HTMLResponse(Response):
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/html",
        background: BackgroundTask = None,
    ) -> None: ...

class RedirectResponse(Response):
    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: dict = None,
        background: BackgroundTask = None,
    ) -> None: ...

class FileResponse(Response):
    def __init__(
        self,
        path: str,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        filename: str = None,
        background: BackgroundTask = None,
    ) -> None: ...

class StreamingResponse(Response):
    def __init__(
        self,
        content: Iterator[Any],
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None: ...
```

[Advanced Response Types](./advanced-responses.md)

### Pydantic v2 Patterns

Best practices for using Pydantic v2 with FastAPI: model separation (Create/Update/Response schemas), explicit response models, field validators, computed fields, serialization, and TypeAdapter.

[Pydantic v2 Patterns](./pydantic-patterns.md)

## Types

```python { .api }
# Core type definitions used across FastAPI

from typing import Any, Callable, Dict, List, Optional, Union, Set, Iterator
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import Response
from starlette.routing import BaseRoute
from starlette.middleware import Middleware
from starlette.background import BackgroundTask
from starlette.templating import _TemplateResponse as TemplateResponse
from starlette.datastructures import URL, Address, FormData, Headers, QueryParams, State
from pydantic import BaseModel
import httpx

# FastAPI specific types
DecoratedCallable = Callable[..., Any]
DependsCallable = Callable[..., Any]  
IncEx = Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any], None]
Lifespan = Callable[[Any], Any]

# Version information
__version__: str  # Current FastAPI version
```