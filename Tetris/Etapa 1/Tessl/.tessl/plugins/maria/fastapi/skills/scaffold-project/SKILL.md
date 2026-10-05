---
name: scaffold-project
description: Scaffold a new FastAPI project with an opinionated directory layout, pydantic-settings config, and starter files. Use when creating a new FastAPI application from scratch.
---

# Scaffold FastAPI Project

Create a new FastAPI project with this layout:

```
<project>/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, router includes
│   ├── routers/             # APIRouter modules
│   │   └── __init__.py
│   ├── models/              # DB / ORM models
│   │   └── __init__.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   └── __init__.py
│   ├── dependencies/        # Shared Depends() callables
│   │   └── __init__.py
│   └── core/
│       ├── __init__.py
│       └── config.py        # pydantic-settings BaseSettings
├── tests/
│   ├── __init__.py
│   └── test_health.py
└── pyproject.toml
```

## Steps

1. **Ask** the user for a project name (default: `myapp`).

2. **Create directories** — all folders listed above, each with an `__init__.py`.

3. **Generate `app/core/config.py`**:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "<project-name>"
    debug: bool = False

settings = Settings()
```

4. **Generate `app/main.py`**:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

app = FastAPI(title=settings.app_name, lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}
```

5. **Generate `tests/test_health.py`**:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

6. **Generate `pyproject.toml`** with dependencies:
   - `fastapi[standard]`
   - `pydantic-settings`
   - `pytest`, `httpx` in dev group

7. **Verify** by running:

```bash
fastapi dev app/main.py &
sleep 2
curl -s http://127.0.0.1:8000/health
kill %1
```
