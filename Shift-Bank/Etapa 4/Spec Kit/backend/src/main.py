import asyncio
import os
from contextlib import asynccontextmanager

from api import router as api_router
from database import init_db
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scheduler import start_background_scheduler, stop_background_scheduler


def is_test_endpoints_enabled() -> bool:
    """Returns True only when ENABLE_TEST_ENDPOINTS is explicitly enabled (F-03).
    In normal application environments, test simulation endpoints remain strictly disabled.
    """
    return os.environ.get("ENABLE_TEST_ENDPOINTS", "false").lower() in ("true", "1", "yes")


def require_test_endpoints():
    """FastAPI dependency to guard non-public test simulation endpoints (F-03).
    Returns 404 Not Found when test endpoints are disabled.
    """
    if not is_test_endpoints_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test simulation endpoints are disabled in this environment."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager (F-07).
    Initializes database schema and starts single-process autonomous scheduler on startup,
    and cleanly stops the scheduler task upon application shutdown.
    """
    # 1. Startup: Initialize database schema & seeds idempotently
    init_db()

    # 2. Startup: Launch autonomous background scheduler task
    scheduler_task = asyncio.create_task(start_background_scheduler())
    yield

    # 3. Shutdown: Gracefully stop background scheduler task
    await stop_background_scheduler(scheduler_task)


app = FastAPI(
    title="Shift Bank Stage 2 API",
    description="Shift Bank Stage 2 — Functional Complexity and State REST API",
    lifespan=lifespan,
)

# Configure CORS Middleware to allow requests from local frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API endpoints router under /api prefix
app.include_router(api_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Maps Pydantic validation errors to HTTP 400 Bad Request with consistent JSON detail."""
    errors = exc.errors()
    msg = errors[0].get("msg", "Validation error.") if errors else "Validation error."
    # Strip any internal prefixes like "Value error, " if present
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": msg}
    )


@app.get("/")
def read_root():
    return {"message": "Welcome to Shift Bank Stage 2 REST API"}
