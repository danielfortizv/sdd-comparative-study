# Advanced Response Types

FastAPI provides a comprehensive set of response classes for different content types and use cases, including high-performance JSON responses, HTML responses, file serving, streaming, and redirects. These response types enable efficient content delivery optimized for specific scenarios and client requirements.

## Capabilities

### High-Performance JSON Responses

Ultra-fast JSON response classes using optimized JSON libraries for maximum performance.

```python { .api }
class UJSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None:
        """
        JSON response using ujson for high performance.
        
        Parameters:
        - content: Data to serialize as JSON
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content type header
        - background: Background task to run after response
        """

class ORJSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "application/json",
        background: BackgroundTask = None,
    ) -> None:
        """
        JSON response using orjson for maximum performance.
        
        Parameters:
        - content: Data to serialize as JSON
        - status_code: HTTP status code
        - headers: Additional HTTP headers  
        - media_type: Content type header
        - background: Background task to run after response
        """
```

### HTML and Plain Text Responses

Response classes for serving HTML content and plain text.

```python { .api }
class HTMLResponse(Response):
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/html",
        background: BackgroundTask = None,
    ) -> None:
        """
        HTML response for serving HTML content.
        
        Parameters:
        - content: HTML content string
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content type header
        - background: Background task to run after response
        """

class PlainTextResponse(Response):
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/plain",
        background: BackgroundTask = None,
    ) -> None:
        """
        Plain text response.
        
        Parameters:
        - content: Plain text content string
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content type header
        - background: Background task to run after response
        """
```

### Redirect Responses

Response class for HTTP redirects with configurable status codes.

```python { .api }
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
        - url: Target URL for redirect
        - status_code: HTTP redirect status code (301, 302, 307, 308)
        - headers: Additional HTTP headers
        - background: Background task to run after response
        """
```

### File and Streaming Responses

Response classes for serving files and streaming large content.

```python { .api }
class FileResponse(Response):
    def __init__(
        self,
        path: str,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        filename: str = None,
        background: BackgroundTask = None,
    ) -> None:
        """
        File download response.
        
        Parameters:
        - path: File system path to the file
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content type (auto-detected if None)
        - filename: Download filename (Content-Disposition header)
        - background: Background task to run after response
        """

class StreamingResponse(Response):
    def __init__(
        self,
        content: Iterator[Any],
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None:
        """
        Streaming response for large content.
        
        Parameters:
        - content: Iterator yielding content chunks
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Content type header
        - background: Background task to run after response
        """
```

## Usage Examples

### High-Performance JSON Responses

```python
from fastapi import FastAPI
from fastapi.responses import UJSONResponse, ORJSONResponse
import time

app = FastAPI()

# Large dataset for performance comparison
large_data = {
    "users": [
        {"id": i, "name": f"User {i}", "score": i * 1.5} 
        for i in range(10000)
    ],
    "timestamp": time.time(),
    "metadata": {"total": 10000, "version": "1.0"}
}

@app.get("/data/ujson", response_class=UJSONResponse)
def get_data_ujson():
    """Return large dataset using ujson for faster serialization."""
    return large_data

@app.get("/data/orjson", response_class=ORJSONResponse)  
def get_data_orjson():
    """Return large dataset using orjson for maximum performance."""
    return large_data

# Set as default response class for entire app
app_with_orjson = FastAPI(default_response_class=ORJSONResponse)

@app_with_orjson.get("/fast")
def fast_endpoint():
    return {"message": "This uses ORJSONResponse by default"}
```

### HTML Responses

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI HTML Response</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { color: #2c3e50; }
        </style>
    </head>
    <body>
        <h1 class="header">Welcome to FastAPI</h1>
        <p>This is a direct HTML response.</p>
        <ul>
            <li><a href="/api/users">API Users</a></li>
            <li><a href="/api/docs">API Documentation</a></li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/dynamic/{name}", response_class=HTMLResponse)
def dynamic_page(name: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hello {name}</title>
    </head>
    <body>
        <h1>Hello, {name}!</h1>
        <p>This page was generated dynamically.</p>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/error-page", response_class=HTMLResponse)
def error_page():
    html_content = """
    <html>
    <body>
        <h1>Something went wrong</h1>
        <p>Please try again later.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=500)
```

### Redirect Responses

```python
from fastapi import FastAPI, Form
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/old-url")
def old_endpoint():
    # Permanent redirect (301)
    return RedirectResponse(url="/new-url", status_code=301)

@app.get("/new-url")
def new_endpoint():
    return {"message": "This is the new endpoint"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    # Simulate authentication
    if username == "admin" and password == "secret":
        # Temporary redirect after successful login (307)
        return RedirectResponse(url="/dashboard", status_code=307)
    else:
        # Redirect back to login with error
        return RedirectResponse(url="/login?error=invalid", status_code=303)

@app.get("/dashboard")
def dashboard():
    return {"message": "Welcome to the dashboard"}

@app.get("/external-redirect")
def external_redirect():
    # Redirect to external URL
    return RedirectResponse(url="https://fastapi.tiangolo.com/")

# Conditional redirects
@app.get("/redirect/{target}")
def conditional_redirect(target: str):
    redirect_map = {
        "docs": "/docs",
        "redoc": "/redoc", 
        "github": "https://github.com/tiangolo/fastapi",
        "home": "/"
    }
    
    if target in redirect_map:
        return RedirectResponse(url=redirect_map[target])
    else:
        return RedirectResponse(url="/404")
```

### File Responses

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path

app = FastAPI()

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = Path("files") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/image/{filename}")
def serve_image(filename: str):
    file_path = Path("images") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Auto-detect media type based on file extension
    return FileResponse(path=str(file_path))

@app.get("/report/pdf")
def download_report():
    return FileResponse(
        path="reports/monthly_report.pdf",
        filename="monthly_report.pdf",
        media_type="application/pdf"
    )

@app.get("/export/csv")
def export_data():
    # Assume CSV file is generated elsewhere
    return FileResponse(
        path="exports/data.csv",
        filename="exported_data.csv",
        media_type="text/csv",
        headers={"Custom-Header": "Export-Data"}
    )
```

### Streaming Responses

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import time
from typing import Iterator

app = FastAPI()

def generate_large_csv() -> Iterator[str]:
    """Generate large CSV data as iterator."""
    yield "id,name,email,created_at\n"
    for i in range(100000):
        yield f"{i},User{i},user{i}@example.com,2024-01-{(i % 30) + 1:02d}\n"

@app.get("/export/large-csv")
def export_large_csv():
    return StreamingResponse(
        generate_large_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=large_data.csv"}
    )

def generate_json_stream() -> Iterator[bytes]:
    """Generate streaming JSON response."""
    yield b'{"data": ['
    for i in range(1000):
        if i > 0:
            yield b','
        data = {"id": i, "value": f"item_{i}"}
        yield json.dumps(data).encode("utf-8")
    yield b']}'

@app.get("/stream/json")
def stream_json():
    return StreamingResponse(
        generate_json_stream(),
        media_type="application/json"
    )

def generate_server_sent_events() -> Iterator[str]:
    """Generate Server-Sent Events stream."""
    for i in range(10):
        yield f"data: Event {i} at {time.time()}\n\n"
        time.sleep(1)

@app.get("/events")
def server_sent_events():
    return StreamingResponse(
        generate_server_sent_events(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

async def generate_async_stream() -> Iterator[bytes]:
    """Generate async streaming response."""
    for chunk in range(100):
        # Simulate async processing
        await asyncio.sleep(0.01)
        yield f"Chunk {chunk}\n".encode("utf-8")

@app.get("/stream/async")
async def async_stream():
    return StreamingResponse(
        generate_async_stream(),
        media_type="text/plain"
    )
```

### Response Headers and Background Tasks

```python
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import logging

app = FastAPI()

def log_download(filename: str, user_ip: str):
    """Background task to log file downloads."""
    logging.info(f"File {filename} downloaded by {user_ip}")

@app.get("/secure-download/{filename}")
def secure_download(filename: str, background_tasks: BackgroundTasks, request: Request):
    file_path = f"secure_files/{filename}"
    
    # Add logging as background task
    background_tasks.add_task(log_download, filename, request.client.host)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        headers={
            "X-Custom-Header": "Secure-Download",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/api/data-with-headers")
def data_with_custom_headers():
    return JSONResponse(
        content={"data": "response"},
        headers={
            "X-API-Version": "1.0",
            "X-Response-Time": str(time.time()),
            "Access-Control-Allow-Origin": "*"
        }
    )
```

## Types

```python { .api }
from typing import Any, Dict, Iterator, Optional, Union
from starlette.responses import Response
from starlette.background import BackgroundTask

# Response content types
ResponseContent = Union[str, bytes, Iterator[Any]]

# Headers type
ResponseHeaders = Optional[Dict[str, str]]

# Background task type
BackgroundTaskType = Optional[BackgroundTask]

# HTTP status codes for redirects
RedirectStatusCode = Union[301, 302, 303, 307, 308]
```