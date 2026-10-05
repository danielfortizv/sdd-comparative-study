# Request and Response Handling

FastAPI provides comprehensive request and response handling through Starlette's Request and Response objects, along with FastAPI-specific enhancements like UploadFile for file handling and various response classes for different content types.

## Capabilities

### Request Object

HTTP request object providing access to all request data including headers, cookies, query parameters, form data, and JSON body.

```python { .api }
class Request:
    """
    Starlette Request object with all HTTP request functionality.
    
    Key attributes and methods for accessing request data:
    """
    
    # Request metadata
    method: str          # HTTP method (GET, POST, etc.)
    url: URL            # Complete URL object
    headers: Headers    # HTTP headers
    query_params: QueryParams  # Query string parameters
    path_params: dict   # Path parameters from URL
    cookies: dict       # HTTP cookies
    client: Address     # Client connection info
    
    # Request body access
    async def body(self) -> bytes:
        """Get raw request body as bytes."""
        pass
    
    async def json(self) -> Any:
        """Parse request body as JSON."""
        pass
    
    async def form(self) -> FormData:
        """Parse request body as form data."""
        pass
    
    # State and context
    state: State        # Request-scoped state storage
    scope: dict         # ASGI scope dictionary
    
    # Utility methods
    def url_for(self, name: str, **path_params) -> str:
        """Generate URL for named route."""
        pass
```

### Response Classes

Base response class and specialized response classes for different content types and use cases.

```python { .api }
class Response:
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None:
        """
        Base HTTP response class.

        Parameters:
        - content: Response content (string, bytes, or None)
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content-Type header value
        - background: Background task to run after response
        """
    
    # Response properties
    status_code: int    # HTTP status code
    headers: Headers    # Response headers
    media_type: str     # Content-Type
    body: bytes         # Response body
    background: BackgroundTask  # Background task

class JSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None:
        """
        JSON response with automatic serialization.

        Parameters:
        - content: Python object to serialize as JSON
        - Other parameters same as Response
        """

class HTMLResponse(Response):
    def __init__(
        self,
        content: str = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/html",
        background: BackgroundTask = None,
    ) -> None:
        """HTML response for returning HTML content."""

class PlainTextResponse(Response):
    def __init__(
        self,
        content: str = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/plain",
        background: BackgroundTask = None,
    ) -> None:
        """Plain text response."""

class RedirectResponse(Response):
    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: dict = None,
        background: BackgroundTask = None,
    ) -> None:
        """
        HTTP redirect response.

        Parameters:
        - url: Target URL for redirection
        - status_code: Redirect status code (307, 302, 301, etc.)
        """

class FileResponse(Response):
    def __init__(
        self,
        path: str = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
        filename: str = None,
        stat_result: os.stat_result = None,
        method: str = None,
    ) -> None:
        """
        File download response.

        Parameters:
        - path: File system path to serve
        - filename: Filename for Content-Disposition header
        - stat_result: Cached file stat result for performance
        - method: HTTP method for conditional logic
        """

class StreamingResponse(Response):
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None:
        """
        Streaming response for large data or real-time content.

        Parameters:
        - content: Iterable or async iterable of bytes/strings
        - Other parameters same as Response
        """
```

### FastAPI-Specific Response Classes

Enhanced JSON response classes using high-performance JSON libraries.

```python { .api }
class UJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        """
        Ultra-fast JSON response using ujson library.
        
        Requires: pip install ujson
        Provides faster JSON serialization than standard library.
        """

class ORJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        """
        Fast JSON response using orjson library.
        
        Requires: pip install orjson
        Fastest JSON serialization with additional features.
        """
```

### File Upload Handling

UploadFile class for handling multipart file uploads with async file operations.

```python { .api }
class UploadFile:
    def __init__(
        self,
        file: BinaryIO,
        *,
        size: int = None,
        filename: str = None,
        headers: Headers = None,
    ) -> None: ...
    
    # File metadata
    filename: Optional[str]      # Original filename
    content_type: Optional[str]  # MIME content type
    headers: Headers             # File-specific headers
    size: Optional[int]          # File size in bytes
    file: BinaryIO              # Underlying file object
    
    # Async file operations
    async def read(self, size: int = -1) -> bytes:
        """Read data from uploaded file."""
    
    async def readline(self, size: int = -1) -> bytes:
        """Read a line from uploaded file."""
    
    async def readlines(self) -> List[bytes]:
        """Read all lines from uploaded file."""
    
    async def write(self, data: bytes) -> None:
        """Write data to uploaded file."""
    
    async def seek(self, offset: int) -> None:
        """Seek to position in uploaded file."""
    
    async def close(self) -> None:
        """Close the uploaded file."""
```

## Usage Examples

### Accessing Request Data

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/analyze-request")
async def analyze_request(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "path_params": request.path_params,
        "cookies": request.cookies,
        "client": f"{request.client.host}:{request.client.port}",
        "body": (await request.body()).decode()
    }

@app.get("/items/{item_id}")
async def get_item(item_id: int, request: Request):
    # Access path parameters
    path_params = request.path_params
    
    # Access query parameters
    query_params = request.query_params
    
    # Access headers
    user_agent = request.headers.get("user-agent")
    
    return {
        "item_id": item_id,
        "path_params": path_params,
        "query_params": dict(query_params),
        "user_agent": user_agent
    }
```

### Custom Response Types

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

app = FastAPI()

@app.get("/html", response_class=HTMLResponse)
def get_html():
    html_content = """
    <html>
        <head><title>FastAPI HTML</title></head>
        <body><h1>Hello, HTML!</h1></body>
    </html>
    """
    return html_content

@app.get("/text", response_class=PlainTextResponse)
def get_text():
    return "Hello, plain text!"

@app.get("/redirect")
def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.get("/permanent-redirect")
def permanent_redirect():
    return RedirectResponse(url="/new-location", status_code=301)
```

### File Downloads

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse
import tempfile
import os

app = FastAPI()

@app.get("/download-file")
def download_file():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("This is a downloadable file content.")
        temp_file_path = f.name
    
    return FileResponse(
        path=temp_file_path,
        filename="download.txt",
        media_type="text/plain"
    )

@app.get("/download-image")
def download_image():
    # Serve an existing file
    file_path = "/path/to/image.jpg"
    return FileResponse(
        path=file_path,
        filename="image.jpg",
        media_type="image/jpeg"
    )
```

### Streaming Responses

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io
import json

app = FastAPI()

@app.get("/stream-data")
def stream_data():
    def generate_data():
        for i in range(1000):
            data = {"item": i, "value": f"data_{i}"}
            yield f"data: {json.dumps(data)}\n"
    
    return StreamingResponse(
        generate_data(),
        media_type="text/plain"
    )

@app.get("/stream-csv")
def stream_csv():
    def generate_csv():
        yield "id,name,email\n"
        for i in range(1000):
            yield f"{i},user_{i},user_{i}@example.com\n"
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )

@app.get("/stream-file")
def stream_large_file():
    def iterfile(file_path: str):
        with open(file_path, mode="rb") as file_like:
            while True:
                chunk = file_like.read(1024)
                if not chunk:
                    break
                yield chunk
    
    return StreamingResponse(
        iterfile("/path/to/large/file.bin"),
        media_type="application/octet-stream"
    )
```

### File Upload Handling

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List
import aiofiles
import os

app = FastAPI()

@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    # Read file content
    content = await file.read()
    
    # Save file
    file_path = f"uploads/{file.filename}"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "saved_to": file_path
    }

@app.post("/upload-multiple/")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        content = await file.read()
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content)
        }
        uploaded_files.append(file_info)
        
        # Reset file pointer if you need to read again
        await file.seek(0)
    
    return {"uploaded_files": uploaded_files}

@app.post("/process-file/")
async def process_file(file: UploadFile = File(...)):
    # Process file line by line for large files
    processed_lines = []
    
    # Read file line by line
    content = await file.read()
    lines = content.decode().split('\n')
    
    for i, line in enumerate(lines):
        if line.strip():  # Skip empty lines
            processed_lines.append(f"Line {i+1}: {line.strip()}")
    
    await file.close()
    
    return {
        "filename": file.filename,
        "total_lines": len(processed_lines),
        "processed_lines": processed_lines[:10]  # Return first 10 lines
    }
```

### Custom Response with Headers

```python
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/custom-headers")
def custom_headers():
    content = {"message": "Custom headers response"}
    headers = {
        "X-Custom-Header": "Custom Value",
        "X-Processing-Time": "0.123",
        "Cache-Control": "no-cache"
    }
    return JSONResponse(content=content, headers=headers)

@app.get("/set-cookie")
def set_cookie(response: Response):
    content = {"message": "Cookie set"}
    response.set_cookie(
        key="session_id",
        value="abc123",
        max_age=3600,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return content

@app.get("/custom-status")
def custom_status():
    return JSONResponse(
        content={"message": "Created successfully"},
        status_code=201,
        headers={"Location": "/items/123"}
    )
```

### Response Model with Custom Response Class

```python
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import List

app = FastAPI(default_response_class=ORJSONResponse)

class Item(BaseModel):
    id: int
    name: str
    price: float

@app.get("/items", response_model=List[Item])
def get_items():
    # FastAPI will use ORJSONResponse for serialization
    return [
        {"id": 1, "name": "Item 1", "price": 10.5},
        {"id": 2, "name": "Item 2", "price": 20.0}
    ]

@app.get("/custom-json", response_class=ORJSONResponse)
def get_custom_json():
    # Explicitly use ORJSONResponse
    return {"message": "Fast JSON response"}
```