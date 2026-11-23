"""FastAPI application entry point for the Stage 1 e-commerce backend.

This module wires the API layer into a runnable FastAPI application. Feature
routers (catalog, authentication, checkout) are added in later tasks; this
scaffold exposes a health endpoint so the service is independently runnable
and reviewable (Requirements 14.2, 14.5).

Run locally with:

    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth_register

from app.api import checkout

from app.api import auth_signin

from app.api import catalog

# Default origin for the separately-run frontend development server. The two
# parts communicate exclusively over HTTP/JSON (Requirements 14.3, 14.4).
FRONTEND_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(
    title="E-Commerce Stage 1 Backend",
    version="0.1.0",
    description=(
        "Demonstration backend for the Stage 1 e-commerce journey. Serves "
        "catalog data, account data, authentication, and a non-persistent "
        "checkout confirmation over HTTP/JSON."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the service is running. Used by smoke/structural checks."""
    return {"status": "ok"}


# Registration endpoint (POST /auth/register). Added additively; other auth
# routes (sign-in/sign-out) are registered by their own task.
app.include_router(auth_register.router)

# Sign-in/sign-out endpoints (POST /auth/login, POST /auth/logout).
app.include_router(auth_signin.router)

# Non-persistent simulated-purchase confirmation (POST /checkout/confirm,
# Requirements 10.1, 10.2). Added additively by task 5.1.
app.include_router(checkout.router)


# Feature routers are registered here as later tasks implement them.
app.include_router(catalog.router)
# Additional routers (auth, checkout) are registered by their respective tasks:
#   from app.api import auth, checkout
#   app.include_router(auth.router)
#   app.include_router(checkout.router)
