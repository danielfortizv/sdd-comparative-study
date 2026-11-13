# E-Commerce Stage 1 — Backend (Python + FastAPI)

Independently runnable and reviewable backend service for the Stage 1
demonstration e-commerce journey. It serves catalog data, account data,
authentication, and a non-persistent checkout confirmation over HTTP/JSON.

## Layering

The code separates presentation, business logic, and data access
(Requirement 14.4):

```
app/
  api/        API layer  — FastAPI routers (request/response handling)
  services/   Service layer — business logic (catalog, auth, checkout)
  data/       Data-access layer — in-process demonstration data store
  models/     Shared Pydantic data models
  main.py     Application entry point
tests/        Unit, property-based, and smoke tests
```

The frontend never reaches the data store directly; it always goes through
the API over HTTP/JSON.

## Prerequisites

- Python 3.11+

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

The service is then available at `http://localhost:8000`
(health check: `http://localhost:8000/health`, interactive docs: `/docs`).

## Test

```bash
pytest
```
