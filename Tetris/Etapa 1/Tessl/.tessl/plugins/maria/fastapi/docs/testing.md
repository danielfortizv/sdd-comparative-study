# Testing Support

FastAPI provides comprehensive testing capabilities through the TestClient class, which enables testing of FastAPI applications with full HTTP request simulation. The TestClient is built on top of HTTPX and provides a convenient interface for testing API endpoints without needing to run a live server.

## Capabilities

### TestClient Class

A test client for testing FastAPI applications with comprehensive HTTP request simulation capabilities.

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
    ) -> None:
        """
        Create a test client for a FastAPI application.
        
        Parameters:
        - app: The FastAPI application to test
        - base_url: Base URL for requests (default: http://testserver)
        - raise_server_exceptions: Whether to raise server exceptions during tests
        - root_path: Root path for the application
        - backend: Async backend to use (asyncio or trio)
        - backend_options: Options for the async backend
        - cookies: Default cookies for requests
        - headers: Default headers for requests
        - follow_redirects: Whether to automatically follow redirects
        """
```

### HTTP Methods

Standard HTTP methods for testing API endpoints with full request and response handling.

```python { .api }
def get(self, url: str, **kwargs) -> httpx.Response:
    """Send GET request to the specified URL."""

def post(self, url: str, **kwargs) -> httpx.Response:
    """Send POST request with optional data/json body."""

def put(self, url: str, **kwargs) -> httpx.Response:
    """Send PUT request with optional data/json body."""

def delete(self, url: str, **kwargs) -> httpx.Response:
    """Send DELETE request to the specified URL."""

def patch(self, url: str, **kwargs) -> httpx.Response:
    """Send PATCH request with optional data/json body."""

def head(self, url: str, **kwargs) -> httpx.Response:
    """Send HEAD request to the specified URL."""

def options(self, url: str, **kwargs) -> httpx.Response:
    """Send OPTIONS request to the specified URL."""

def request(
    self, 
    method: str, 
    url: str, 
    **kwargs
) -> httpx.Response:
    """Send request with specified HTTP method."""
```

### Context Manager Support

TestClient supports context manager protocol for proper resource cleanup.

```python { .api }
def __enter__(self) -> TestClient:
    """Enter context manager."""

def __exit__(self, *args) -> None:
    """Exit context manager and cleanup resources."""
```

### WebSocket Testing

Support for testing WebSocket connections.

```python { .api }
def websocket_connect(
    self, 
    url: str, 
    subprotocols: List[str] = None, 
    **kwargs
) -> WebSocketTestSession:
    """Create WebSocket connection for testing."""
```

## Usage Examples

### Basic API Testing

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

@app.post("/items/")
def create_item(item: dict):
    return item

# Create test client
client = TestClient(app)

def test_read_item():
    response = client.get("/items/1?q=test")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "q": "test"}

def test_create_item():
    item_data = {"name": "Test Item", "price": 10.50}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 200
    assert response.json() == item_data
```

### Testing with Authentication

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.testclient import TestClient

app = FastAPI()
security = HTTPBearer()

@app.get("/protected")
def protected_endpoint(token: str = Depends(security)):
    if token.credentials != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": "Protected data"}

client = TestClient(app)

def test_protected_endpoint():
    # Test without token
    response = client.get("/protected")
    assert response.status_code == 403
    
    # Test with invalid token
    response = client.get(
        "/protected", 
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
    
    # Test with valid token
    response = client.get(
        "/protected", 
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Protected data"}
```

### Testing File Uploads

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient
import io

app = FastAPI()

@app.post("/upload/")
def upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename, "size": len(file.file.read())}

client = TestClient(app)

def test_file_upload():
    test_file = io.BytesIO(b"test file content")
    response = client.post(
        "/upload/", 
        files={"file": ("test.txt", test_file, "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["size"] > 0
```

### Testing with Context Manager

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

def test_with_context_manager():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Hello": "World"}
```

### WebSocket Testing

```python
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello WebSocket!")
    await websocket.close()

client = TestClient(app)

def test_websocket():
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_text()
        assert data == "Hello WebSocket!"
```

## Types

```python { .api }
from typing import Any, Dict, List, Optional, Union
import httpx
from starlette.types import ASGIApp

# Test client response type
TestResponse = httpx.Response

# WebSocket test session
class WebSocketTestSession:
    def send_text(self, data: str) -> None: ...
    def send_bytes(self, data: bytes) -> None: ...
    def send_json(self, data: Any) -> None: ...
    def receive_text(self) -> str: ...
    def receive_bytes(self) -> bytes: ...
    def receive_json(self) -> Any: ...
    def close(self, code: int = 1000) -> None: ...
```