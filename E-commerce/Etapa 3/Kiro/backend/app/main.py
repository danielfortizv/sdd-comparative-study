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

# Stage 3: bounded response caching for public catalog reads (additive).
from app.api.cache_middleware import CatalogCacheMiddleware

from app.api import auth_register

from app.api import checkout

from app.api import auth_signin

from app.api import catalog

# Stage 2 routers (reviews with images and moderation). Added additively.
from app.api import reviews

from app.api import moderation

from app.services.moderator_seed import seed_moderator

# Default origin for the separately-run frontend development server. The two
# parts communicate exclusively over HTTP/JSON (Requirements 14.3, 14.4).
# Stage 3 additively allows the Vite *preview* origin (port 4173) used by the
# production build and the Playwright E2E suite, and the Docker-published
# frontend origin (host port 8080). These are local-demo origins only.
FRONTEND_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
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

# Stage 3: bounded, TTL-based caching for the two session-independent public
# catalog reads (GET /products, GET /products/{id}); session-varying and
# moderation responses are marked no-store. Added additively; it does not
# change any endpoint's request/response body (Requirements 5.1, 5.4, 7.1).
#
# Ordering matters: FastAPI/Starlette applies the LAST-added middleware as the
# OUTERMOST layer. The cache is added FIRST (so it is the inner layer) and CORS
# is added AFTER it (so CORS is the outer layer). This guarantees CORS headers
# are applied to every response — including cached HITs that this middleware
# constructs itself — so the browser is never blocked on a cached catalog read.
app.add_middleware(CatalogCacheMiddleware)

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

# Stage 2: reviews (submission, public reviews, image serving) and moderation
# (moderator-only queue + approve/reject). Added additively; the six Stage 1
# endpoints are unchanged (Requirement 9.5).
app.include_router(reviews.router)
app.include_router(moderation.router)


@app.on_event("startup")
def _seed_demo_moderator() -> None:
    """Seed the demonstration moderator account at startup (Assumption A5).

    Idempotent: safe to run on every startup. The moderator credentials are
    documented in the project README so the moderation workflow can be
    demonstrated immediately.
    """
    seed_moderator()
