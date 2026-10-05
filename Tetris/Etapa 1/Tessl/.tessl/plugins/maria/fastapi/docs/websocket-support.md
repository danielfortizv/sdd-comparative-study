# WebSocket Support

FastAPI provides comprehensive WebSocket support for real-time bidirectional communication between clients and servers. This enables applications to push data to clients instantly and receive real-time updates from clients.

## Capabilities

### WebSocket Connection Class

The WebSocket class handles real-time bidirectional communication with clients, providing methods for sending and receiving data in various formats.

```python { .api }
class WebSocket:
    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Initialize WebSocket connection.
        
        Parameters:
        - scope: ASGI scope dictionary
        - receive: ASGI receive callable
        - send: ASGI send callable
        """

    async def accept(
        self,
        subprotocol: str = None,
        headers: List[Tuple[bytes, bytes]] = None
    ) -> None:
        """
        Accept the WebSocket connection.
        
        Parameters:
        - subprotocol: WebSocket subprotocol to use
        - headers: Additional headers to send
        """

    async def receive_text(self) -> str:
        """
        Receive text data from the WebSocket.
        
        Returns:
        String containing the received text message
        """

    async def receive_bytes(self) -> bytes:
        """
        Receive binary data from the WebSocket.
        
        Returns:
        Bytes containing the received binary message
        """

    async def receive_json(self, mode: str = "text") -> Any:
        """
        Receive JSON data from the WebSocket.
        
        Parameters:
        - mode: Receive mode ("text" or "binary")
        
        Returns:
        Parsed JSON data as Python object
        """

    async def send_text(self, data: str) -> None:
        """
        Send text data to the WebSocket.
        
        Parameters:
        - data: Text message to send
        """

    async def send_bytes(self, data: bytes) -> None:
        """
        Send binary data to the WebSocket.
        
        Parameters:
        - data: Binary message to send
        """

    async def send_json(self, data: Any, mode: str = "text") -> None:
        """
        Send JSON data to the WebSocket.
        
        Parameters:
        - data: Python object to serialize and send as JSON
        - mode: Send mode ("text" or "binary")
        """

    async def close(self, code: int = 1000, reason: str = None) -> None:
        """
        Close the WebSocket connection.
        
        Parameters:
        - code: WebSocket close code
        - reason: Close reason string
        """

    @property
    def client(self) -> Address:
        """Client address information."""

    @property
    def url(self) -> URL:
        """WebSocket URL information."""

    @property
    def headers(self) -> Headers:
        """WebSocket headers."""

    @property
    def query_params(self) -> QueryParams:
        """WebSocket query parameters."""

    @property
    def path_params(self) -> dict:
        """WebSocket path parameters."""

    @property
    def cookies(self) -> dict:
        """WebSocket cookies."""

    @property
    def state(self) -> State:
        """WebSocket connection state."""
```

### WebSocket State Enumeration

Enumeration defining the possible states of a WebSocket connection.

```python { .api }
class WebSocketState(enum.Enum):
    """WebSocket connection state constants."""
    
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 3
```

### WebSocket Disconnect Exception

Exception raised when a WebSocket connection is unexpectedly disconnected.

```python { .api }
class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000, reason: str = None) -> None:
        """
        WebSocket disconnect exception.
        
        Parameters:
        - code: WebSocket close code
        - reason: Disconnect reason
        """
        self.code = code
        self.reason = reason
```

### WebSocket Route Decorator

Decorator method on FastAPI and APIRouter instances for defining WebSocket endpoints.

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

### WebSocket Route Class

Class representing individual WebSocket routes in the application.

```python { .api }
class APIWebSocketRoute:
    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *,
        name: str = None,
        dependencies: List[Depends] = None,
    ) -> None:
        """
        WebSocket route representation.
        
        Parameters:
        - path: WebSocket URL path
        - endpoint: WebSocket handler function
        - name: Route name for URL generation
        - dependencies: List of dependencies for the WebSocket
        """

    def matches(self, scope: Scope) -> Tuple[Match, Scope]:
        """Check if route matches the given scope."""

    def url_path_for(self, name: str, **path_params: Any) -> URLPath:
        """Generate URL path for the named route."""
```

## Usage Examples

### Basic WebSocket Endpoint

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")
```

### WebSocket with Path Parameters

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Client {client_id}: {data}")
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
```

### WebSocket with Dependencies

```python
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

def verify_websocket_token(token: str = Depends(security)):
    if token.credentials != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return token.credentials

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Depends(verify_websocket_token)
):
    await websocket.accept()
    await websocket.send_text(f"Authenticated with token: {token}")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("Authenticated client disconnected")
```

### WebSocket JSON Communication

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Any

app = FastAPI()

@app.websocket("/ws/json")
async def websocket_json_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive JSON data
            data: Dict[str, Any] = await websocket.receive_json()
            
            # Process the data
            response = {
                "type": "response",
                "original_message": data,
                "timestamp": "2023-01-01T00:00:00Z"
            }
            
            # Send JSON response
            await websocket.send_json(response)
    except WebSocketDisconnect:
        print("JSON WebSocket client disconnected")
```

### WebSocket Connection Manager

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
```

### WebSocket with Query Parameters

```python
from fastapi import FastAPI, WebSocket, Query

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str = Query(..., description="Chat room name"),
    user_id: int = Query(..., description="User ID")
):
    await websocket.accept()
    await websocket.send_text(f"Welcome to room {room}, user {user_id}!")
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"[{room}] User {user_id}: {message}")
    except WebSocketDisconnect:
        print(f"User {user_id} left room {room}")
```

### WebSocket Error Handling

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

@app.websocket("/ws/safe")
async def safe_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            try:
                # Receive and validate JSON
                data = await websocket.receive_text()
                parsed_data = json.loads(data)
                
                if "action" not in parsed_data:
                    await websocket.send_json({
                        "error": "Missing 'action' field"
                    })
                    continue
                
                # Process valid messages
                response = {
                    "success": True,
                    "action": parsed_data["action"],
                    "data": parsed_data.get("data")
                }
                await websocket.send_json(response)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid JSON format"
                })
            except Exception as e:
                await websocket.send_json({
                    "error": f"Processing error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        print("Client disconnected from safe WebSocket")
```

### WebSocket with Custom Close Handling

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.websocket("/ws/custom-close")
async def websocket_with_custom_close(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "close":
                await websocket.close(code=1000, reason="Client requested close")
                break
            elif data == "error":
                await websocket.close(code=1011, reason="Server error occurred")
                break
            else:
                await websocket.send_text(f"Received: {data}")
                
    except WebSocketDisconnect as disconnect:
        print(f"WebSocket disconnected with code: {disconnect.code}, reason: {disconnect.reason}")
```