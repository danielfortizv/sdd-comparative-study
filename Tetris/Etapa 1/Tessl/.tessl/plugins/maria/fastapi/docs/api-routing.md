# API Routing

APIRouter allows organizing and grouping related API endpoints with shared configuration, middleware, and dependencies. Routers enable modular API design and can be included in the main FastAPI application or nested within other routers.

## Capabilities

### APIRouter Class

Router for organizing related endpoints with shared configuration including URL prefixes, tags, dependencies, and response models.

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
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
        **kwargs: Any,
    ) -> None:
        """
        Create an APIRouter instance.

        Parameters:
        - prefix: Common URL prefix for all routes in this router
        - tags: List of tags for grouping routes in documentation
        - dependencies: List of dependencies applied to all routes
        - default_response_class: Default response class for all routes
        - responses: Additional response models for all routes
        - callbacks: List of callback routes
        - routes: List of routes to include in the router
        - deprecated: Mark all routes as deprecated
        - include_in_schema: Include router routes in OpenAPI schema
        """
```

### HTTP Method Decorators

Decorators for defining API endpoints on the router with the same functionality as FastAPI application decorators.

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
    Decorator for GET endpoints on this router.

    Parameters same as FastAPI.get() decorator.
    """

def post(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for POST endpoints on this router."""

def put(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for PUT endpoints on this router."""

def delete(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for DELETE endpoints on this router."""

def patch(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for PATCH endpoints on this router."""

def head(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for HEAD endpoints on this router."""

def options(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for OPTIONS endpoints on this router."""

def trace(self, path: str, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for TRACE endpoints on this router."""

def websocket(
    self,
    path: str,
    *,
    name: str = None,
    dependencies: List[Depends] = None,
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorator for WebSocket endpoints on this router."""
```

### Router Composition

Methods for including sub-routers and adding routes programmatically to create hierarchical API structures.

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
    Include another APIRouter in this router.

    Parameters:
    - router: APIRouter instance to include
    - prefix: Additional URL prefix for the included router
    - tags: Additional tags for all routes in the included router
    - dependencies: Additional dependencies for all routes
    - responses: Additional response models
    - deprecated: Mark all included routes as deprecated
    - include_in_schema: Include routes in OpenAPI schema
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
    Add an API route programmatically to this router.

    Parameters same as FastAPI.add_api_route() method.
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
    Add a WebSocket route programmatically to this router.

    Parameters same as FastAPI.add_api_websocket_route() method.
    """
```

### Route Mounting

Method for mounting ASGI applications and static file servers.

```python { .api }
def mount(
    self,
    path: str,
    app: ASGIApp,
    *,
    name: str = None,
) -> None:
    """
    Mount an ASGI application at the given path.

    Parameters:
    - path: URL path where the application should be mounted
    - app: ASGI application to mount
    - name: Name for the mount (for URL generation)
    """
```

### Route Classes

Individual route representation classes used internally by APIRouter.

```python { .api }
class APIRoute:
    """
    Individual API route representation with all route metadata,
    path parameters, dependencies, and response models.
    """
    def __init__(
        self,
        path: str,
        endpoint: Callable,
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
        name: str = None,
        methods: List[str] = None,
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
        generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
        openapi_extra: dict = None,
    ) -> None: ...

class APIWebSocketRoute:
    """
    WebSocket route representation for real-time communication endpoints.
    """
    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *,
        name: str = None,
        dependencies: List[Depends] = None,
    ) -> None: ...
```

## Usage Examples

### Basic Router Usage

```python
from fastapi import APIRouter, FastAPI

# Create router for user-related endpoints
users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

@users_router.get("/")
def get_users():
    return [{"username": "john"}, {"username": "jane"}]

@users_router.get("/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id, "username": "john"}

@users_router.post("/")
def create_user(user: dict):
    return {"message": "User created", "user": user}

# Include router in main application
app = FastAPI()
app.include_router(users_router)
```

### Router with Dependencies

```python
from fastapi import APIRouter, Depends, HTTPException

def get_current_user():
    # Authentication logic here
    return {"username": "current_user"}

def admin_required(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Router with shared dependencies
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(admin_required)]
)

@admin_router.get("/users")
def list_all_users():
    return {"users": ["admin", "user1", "user2"]}

@admin_router.delete("/users/{user_id}")
def delete_user(user_id: int):
    return {"message": f"User {user_id} deleted"}
```

### Nested Routers

```python
from fastapi import APIRouter, FastAPI

# Create nested router structure
api_v1_router = APIRouter(prefix="/api/v1")

users_router = APIRouter(prefix="/users", tags=["users"])
posts_router = APIRouter(prefix="/posts", tags=["posts"])

@users_router.get("/")
def get_users():
    return {"users": []}

@posts_router.get("/")
def get_posts():
    return {"posts": []}

# Include sub-routers in API v1 router
api_v1_router.include_router(users_router)
api_v1_router.include_router(posts_router)

# Include API v1 router in main application
app = FastAPI()
app.include_router(api_v1_router)

# This creates endpoints:
# GET /api/v1/users/
# GET /api/v1/posts/
```

### Router with Custom Response Models

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int
    username: str
    email: str

class UserCreate(BaseModel):
    username: str
    email: str

# Router with default response class
users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        404: {"description": "User not found"},
        422: {"description": "Validation error"}
    }
)

@users_router.get("/", response_model=List[User])
def get_users():
    return [
        {"id": 1, "username": "john", "email": "john@example.com"},
        {"id": 2, "username": "jane", "email": "jane@example.com"}
    ]

@users_router.post("/", response_model=User, status_code=201)
def create_user(user: UserCreate):
    return {"id": 3, **user.model_dump()}
```