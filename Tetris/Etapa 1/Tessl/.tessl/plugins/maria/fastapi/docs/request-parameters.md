# Request Parameters

FastAPI provides type-safe parameter declaration functions for handling different types of request data including path parameters, query parameters, headers, cookies, request bodies, form data, and file uploads. These functions enable automatic validation, serialization, and OpenAPI documentation generation.

## Capabilities

### Path Parameters

Declare path parameters extracted from the URL path with automatic type conversion and validation.

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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare a path parameter with validation constraints.

    Parameters:
    - default: Default value (use ... for required parameters)
    - alias: Alternative name for the parameter in OpenAPI
    - title: Title for documentation
    - description: Description for documentation
    - gt: Greater than validation for numbers
    - ge: Greater than or equal validation for numbers
    - lt: Less than validation for numbers
    - le: Less than or equal validation for numbers
    - min_length: Minimum length for strings
    - max_length: Maximum length for strings
    - regex: Regular expression pattern for string validation
    - example: Example value for documentation
    - examples: Multiple examples for documentation
    - deprecated: Mark parameter as deprecated
    - include_in_schema: Include in OpenAPI schema

    Returns:
    Parameter declaration for use in function signatures
    """
```

### Query Parameters

Declare query parameters from URL query strings with optional defaults and validation.

```python { .api }
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare a query parameter with validation constraints.

    Parameters:
    Same as Path() but with optional default values.
    Use default=Undefined for required query parameters.

    Returns:
    Parameter declaration for use in function signatures
    """
```

### Header Parameters

Declare HTTP header parameters with automatic conversion and validation.

```python { .api }
def Header(
    default: Any = Undefined,
    *,
    alias: str = None,
    convert_underscores: bool = True,
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare an HTTP header parameter with validation constraints.

    Parameters:
    - convert_underscores: Convert underscores to hyphens in header names
    - Other parameters same as Path() and Query()

    Returns:
    Parameter declaration for use in function signatures
    """
```

### Cookie Parameters

Declare HTTP cookie parameters with validation and type conversion.

```python { .api }
def Cookie(
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare an HTTP cookie parameter with validation constraints.

    Parameters:
    Same as Query() and Header() without convert_underscores.

    Returns:
    Parameter declaration for use in function signatures
    """
```

### Request Body

Declare request body parameters with JSON serialization and validation via Pydantic models.

```python { .api }
def Body(
    default: Any = Undefined,
    *,
    embed: bool = None,
    media_type: str = "application/json",
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare a request body parameter with validation constraints.

    Parameters:
    - embed: Embed single values in a JSON object
    - media_type: Media type for the request body
    - Other parameters same as other parameter functions

    Returns:
    Parameter declaration for use in function signatures
    """
```

### Form Data

Declare form data parameters for application/x-www-form-urlencoded content.

```python { .api }
def Form(
    default: Any = Undefined,
    *,
    media_type: str = "application/x-www-form-urlencoded",
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare a form data parameter with validation constraints.

    Parameters:
    - media_type: Media type for form data (default: application/x-www-form-urlencoded)
    - Other parameters same as other parameter functions

    Returns:
    Parameter declaration for use in function signatures
    """
```

### File Upload

Declare file upload parameters for multipart/form-data content with UploadFile objects.

```python { .api }
def File(
    default: Any = Undefined,
    *,
    media_type: str = "multipart/form-data",
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
    openapi_examples: dict = None,
    deprecated: bool = None,
    include_in_schema: bool = True,
    **extra: Any,
) -> Any:
    """
    Declare a file upload parameter with validation constraints.

    Parameters:
    - media_type: Media type for file uploads (default: multipart/form-data)
    - Other parameters same as other parameter functions

    Returns:
    Parameter declaration for use in function signatures
    """
```

## Usage Examples

### Path Parameters

```python
from fastapi import FastAPI, Path

app = FastAPI()

@app.get("/items/{item_id}")
def get_item(
    item_id: int = Path(..., title="Item ID", description="The ID of the item", ge=1)
):
    return {"item_id": item_id}

@app.get("/users/{user_id}/posts/{post_id}")
def get_user_post(
    user_id: int = Path(..., ge=1),
    post_id: int = Path(..., ge=1, le=1000)
):
    return {"user_id": user_id, "post_id": post_id}
```

### Query Parameters

```python
from fastapi import FastAPI, Query
from typing import Optional, List

app = FastAPI()

@app.get("/items/")
def read_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    q: Optional[str] = Query(None, min_length=3, max_length=50, description="Search query"),
    tags: List[str] = Query([], description="Filter by tags")
):
    return {"skip": skip, "limit": limit, "q": q, "tags": tags}

# Multiple query parameters with the same name
@app.get("/items/search")
def search_items(category: List[str] = Query(..., description="Categories to search")):
    return {"categories": category}
```

### Header Parameters

```python
from fastapi import FastAPI, Header
from typing import Optional

app = FastAPI()

@app.get("/items/")
def read_items(
    user_agent: Optional[str] = Header(None),
    x_token: str = Header(..., description="Authentication token"),
    accept_language: Optional[str] = Header(None, convert_underscores=True)
):
    return {
        "User-Agent": user_agent,
        "X-Token": x_token,
        "Accept-Language": accept_language
    }
```

### Cookie Parameters

```python
from fastapi import FastAPI, Cookie
from typing import Optional

app = FastAPI()

@app.get("/items/")
def read_items(
    session_id: Optional[str] = Cookie(None),
    ads_id: Optional[str] = Cookie(None)
):
    return {"session_id": session_id, "ads_id": ads_id}
```

### Request Body with Pydantic Models

```python
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class User(BaseModel):
    username: str
    email: str

@app.post("/items/")
def create_item(item: Item):
    return item

@app.put("/items/{item_id}")
def update_item(
    item_id: int,
    item: Item,
    user: User,
    importance: int = Body(..., gt=0, description="Item importance level")
):
    return {"item_id": item_id, "item": item, "user": user, "importance": importance}

# Single value in body
@app.post("/items/{item_id}/priority")
def set_priority(
    item_id: int,
    priority: int = Body(..., embed=True, ge=1, le=5)
):
    return {"item_id": item_id, "priority": priority}
```

### Form Data

```python
from fastapi import FastAPI, Form

app = FastAPI()

@app.post("/login/")
def login(
    username: str = Form(..., min_length=3),
    password: str = Form(..., min_length=8)
):
    return {"username": username}

@app.post("/contact/")
def contact(
    name: str = Form(...),
    email: str = Form(..., regex=r'^[^@]+@[^@]+\.[^@]+$'),
    message: str = Form(..., min_length=10, max_length=1000)
):
    return {"name": name, "email": email, "message": message}
```

### File Upload

```python
from fastapi import FastAPI, File, UploadFile, Form
from typing import List

app = FastAPI()

@app.post("/upload/")
def upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}

@app.post("/upload-multiple/")
def upload_multiple_files(files: List[UploadFile] = File(...)):
    return {"filenames": [file.filename for file in files]}

@app.post("/upload-with-form/")
def upload_with_form_data(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...)
):
    return {
        "filename": file.filename,
        "name": name,
        "description": description
    }

# File as bytes
@app.post("/upload-bytes/")
def upload_file_bytes(file: bytes = File(...)):
    return {"file_size": len(file)}
```

### Combined Parameters

```python
from fastapi import FastAPI, Path, Query, Header, Cookie, Body, Form, File, UploadFile
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Metadata(BaseModel):
    title: str
    description: Optional[str] = None

@app.post("/items/{item_id}/process")
def process_item(
    # Path parameter
    item_id: int = Path(..., ge=1),
    
    # Query parameters
    force: bool = Query(False),
    notify_users: bool = Query(True),
    
    # Headers
    user_agent: Optional[str] = Header(None),
    x_api_key: str = Header(...),
    
    # Cookies
    session_id: Optional[str] = Cookie(None),
    
    # Request body
    metadata: Metadata,
    priority: int = Body(..., ge=1, le=5),
    
    # Form data and file
    notes: str = Form(...),
    attachment: Optional[UploadFile] = File(None)
):
    return {
        "item_id": item_id,
        "force": force,
        "notify_users": notify_users,
        "user_agent": user_agent,
        "session_id": session_id,
        "metadata": metadata,
        "priority": priority,
        "notes": notes,
        "attachment": attachment.filename if attachment else None
    }
```