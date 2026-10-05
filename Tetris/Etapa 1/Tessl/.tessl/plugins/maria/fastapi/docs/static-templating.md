# Static Files and Templating

FastAPI provides built-in support for serving static files and rendering HTML templates, enabling the creation of full web applications that combine API endpoints with frontend content. This functionality is essential for applications that need to serve HTML pages, CSS, JavaScript, images, and other static assets alongside their API functionality.

## Capabilities

### Static Files Serving

Class for serving static files such as HTML, CSS, JavaScript, images, and other assets from the filesystem.

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
    ) -> None:
        """
        Create static files application for serving static content.
        
        Parameters:
        - directory: Directory path containing static files
        - packages: List of Python packages containing static files
        - html: Whether to serve HTML files for directory requests
        - check_dir: Whether to check if directory exists on startup
        - follow_symlink: Whether to follow symbolic links
        """
```

### Jinja2 Template Engine

Template engine integration for rendering dynamic HTML content with data from your API endpoints.

```python { .api }
class Jinja2Templates:
    def __init__(self, directory: str) -> None:
        """
        Create Jinja2 templates instance.
        
        Parameters:
        - directory: Directory containing template files
        """
    
    def TemplateResponse(
        self,
        name: str,
        context: dict,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> TemplateResponse:
        """
        Render template with context data and return as HTTP response.
        
        Parameters:
        - name: Template file name
        - context: Dictionary of template variables
        - status_code: HTTP status code
        - headers: Additional HTTP headers
        - media_type: Response content type
        - background: Background task to run after response
        
        Returns:
        TemplateResponse with rendered HTML content
        """

    def get_template(self, name: str) -> Template:
        """Get template object by name."""
```

## Usage Examples

### Serving Static Files

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount static files with HTML serving
app.mount("/public", StaticFiles(directory="public", html=True), name="public")

# Serve from Python package
app.mount("/assets", StaticFiles(packages=["mypackage"]), name="assets")
```

With this setup:
- Files in `./static/` are accessible at `/static/filename.ext`
- Files in `./public/` are accessible at `/public/filename.ext`
- Directory requests to `/public/` will serve `index.html` if `html=True`
- Package assets are served from installed Python packages

### HTML Template Rendering

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "Home Page"}
    )

@app.get("/user/{user_id}", response_class=HTMLResponse)
async def user_profile(request: Request, user_id: int):
    # Simulate user data retrieval
    user_data = {"id": user_id, "name": f"User {user_id}"}
    return templates.TemplateResponse(
        "profile.html", 
        {
            "request": request, 
            "user": user_data,
            "title": f"Profile - {user_data['name']}"
        }
    )
```

Template file `templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Welcome to FastAPI</h1>
    <p>This is a template-rendered page.</p>
    <script src="/static/script.js"></script>
</body>
</html>
```

Template file `templates/profile.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>User Profile</h1>
    <p>ID: {{ user.id }}</p>
    <p>Name: {{ user.name }}</p>
    <a href="/">Back to Home</a>
</body>
</html>
```

### Complete Web Application Example

```python
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

app = FastAPI()

# Mount static files for CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# In-memory storage for demo
items = []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", 
        {"request": request, "items": items}
    )

@app.get("/add", response_class=HTMLResponse)
async def add_item_form(request: Request):
    return templates.TemplateResponse(
        "add_item.html", 
        {"request": request}
    )

@app.post("/add")
async def add_item(
    request: Request,
    name: str = Form(...),
    description: str = Form(...)
):
    item = {"id": len(items) + 1, "name": name, "description": description}
    items.append(item)
    return RedirectResponse(url="/", status_code=303)

@app.get("/item/{item_id}", response_class=HTMLResponse)
async def item_detail(request: Request, item_id: int):
    item = next((item for item in items if item["id"] == item_id), None)
    if not item:
        return templates.TemplateResponse(
            "404.html", 
            {"request": request}, 
            status_code=404
        )
    return templates.TemplateResponse(
        "item_detail.html", 
        {"request": request, "item": item}
    )

# API endpoints for AJAX/SPA integration
@app.get("/api/items")
async def api_get_items():
    return {"items": items}

@app.post("/api/items")
async def api_add_item(item: dict):
    new_item = {"id": len(items) + 1, **item}
    items.append(new_item)
    return new_item
```

### Template with Custom Filters

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Add custom filter to templates
def format_datetime(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")

templates.env.filters["datetime"] = format_datetime

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request,
            "current_time": datetime.datetime.now(),
            "data": {"users": 150, "posts": 1240}
        }
    )
```

Template using custom filter:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <h1>Dashboard</h1>
    <p>Current time: {{ current_time | datetime }}</p>
    <p>Users: {{ data.users }}</p>
    <p>Posts: {{ data.posts }}</p>
</body>
</html>
```

### Error Page Templates

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "404.html", 
        {"request": request}, 
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "500.html", 
        {"request": request}, 
        status_code=500
    )
```

## Types

```python { .api }
from typing import Any, Dict, List, Optional
from starlette.responses import Response
from starlette.background import BackgroundTask
from starlette.templating import _TemplateResponse as TemplateResponse
from jinja2 import Template, Environment

# Template response type
TemplateResponse = _TemplateResponse

# Jinja2 environment type
Jinja2Environment = Environment

# Template context type
TemplateContext = Dict[str, Any]
```