"""Gateway FastAPI app (Stage 4, port 18200): thin HTTP compatibility layer.

Preserves the nine Stage 1-3 endpoints and their request/response bodies while
delegating every call over HTTP to the owning service. It contains **no
business logic**: it only routes, manages the browser session cookie <-> service
token binding, injects the token downstream as a Bearer header, and applies the
Stage 3 bounded catalog cache / no-store semantics at the edge.

Routing:
- ``/auth/*``                         -> identity
- ``/products``, ``/products/{id}``   -> commerce (cacheable)
- ``/checkout/confirm``               -> commerce
- ``GET /products/{id}/reviews``      -> commerce (public projection, no-store)
- ``POST /products/{id}/reviews``     -> reviews
- ``/reviews/images/{id}``            -> reviews
- ``/moderation/*``                   -> reviews

Run with: ``uvicorn app.main:app --port 18200``.
"""

from __future__ import annotations

import json

import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from contracts.settings import get_settings

from app.cache import response_cache
from app.session import SessionBindingStore

settings = get_settings()
sessions = SessionBindingStore()
app = FastAPI(title="Stage 4 Gateway", version="1.0.0")

COOKIE_NAME = "stage4_session"

_FRONTEND_ORIGINS = [
    f"http://localhost:{settings.frontend_port}",
    f"http://127.0.0.1:{settings.frontend_port}",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client() -> httpx.Client:
    return httpx.Client(timeout=10.0)


def _bearer(request: Request) -> dict[str, str]:
    token = sessions.token_for(request.cookies.get(COOKIE_NAME))
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- auth (-> identity) ------------------------------------------------------


@app.post("/auth/register")
async def register(request: Request) -> Response:
    body = await request.body()
    with _client() as client:
        upstream = client.post(
            f"{settings.identity_url}/auth/register",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    return _passthrough(upstream, no_store=True)


@app.post("/auth/login")
async def login(request: Request) -> Response:
    body = await request.body()
    with _client() as client:
        upstream = client.post(
            f"{settings.identity_url}/auth/login",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    if upstream.status_code != 200:
        return _passthrough(upstream, no_store=True)

    payload = upstream.json()
    token = payload.pop("token", None)  # never expose the token to the browser
    resp = JSONResponse(status_code=200, content=payload)
    resp.headers["Cache-Control"] = "no-store"
    if token:
        cookie_id = sessions.create(token)
        resp.set_cookie(
            COOKIE_NAME,
            cookie_id,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return resp


@app.post("/auth/logout")
async def logout(request: Request) -> Response:
    cookie_id = request.cookies.get(COOKIE_NAME)
    sessions.drop(cookie_id)
    with _client() as client:
        upstream = client.post(f"{settings.identity_url}/auth/logout")
    resp = JSONResponse(status_code=upstream.status_code, content=upstream.json())
    resp.headers["Cache-Control"] = "no-store"
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


# --- catalog (-> commerce, cacheable) ----------------------------------------


@app.get("/products")
def list_products() -> Response:
    return _cached_catalog_get("/products")


@app.get("/products/{product_id}")
def get_product(product_id: str) -> Response:
    return _cached_catalog_get(f"/products/{product_id}")


def _cached_catalog_get(path: str) -> Response:
    key = f"GET {path}"
    cached = response_cache.get(key)
    if cached is not None:
        resp = Response(content=cached.body, media_type=cached.media_type)
        resp.headers["X-Cache"] = "HIT"
        resp.headers["Cache-Control"] = f"public, max-age={response_cache.ttl_seconds}"
        return resp
    with _client() as client:
        upstream = client.get(f"{settings.commerce_url}{path}")
    if upstream.status_code == 200:
        response_cache.set(key, upstream.content, "application/json")
    resp = Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type="application/json",
    )
    if upstream.status_code == 200:
        resp.headers["X-Cache"] = "MISS"
        resp.headers["Cache-Control"] = f"public, max-age={response_cache.ttl_seconds}"
    return resp


# --- checkout (-> commerce) --------------------------------------------------


@app.post("/checkout/confirm")
async def checkout(request: Request) -> Response:
    body = await request.body()
    with _client() as client:
        upstream = client.post(
            f"{settings.commerce_url}/checkout/confirm",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    return _passthrough(upstream)


# --- reviews -----------------------------------------------------------------


@app.get("/products/{product_id}/reviews")
def public_reviews(product_id: str, request: Request) -> Response:
    with _client() as client:
        upstream = client.get(
            f"{settings.commerce_url}/products/{product_id}/reviews",
            headers=_bearer(request),
        )
    return _passthrough(upstream, no_store=True)


@app.post("/products/{product_id}/reviews")
async def submit_review(product_id: str, request: Request) -> Response:
    body = await request.body()
    with _client() as client:
        upstream = client.post(
            f"{settings.reviews_url}/products/{product_id}/reviews",
            content=body,
            headers={"Content-Type": "application/json", **_bearer(request)},
        )
    return _passthrough(upstream, no_store=True)


@app.get("/reviews/images/{image_id}")
def review_image(image_id: str) -> Response:
    with _client() as client:
        upstream = client.get(f"{settings.reviews_url}/reviews/images/{image_id}")
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
    )


# --- moderation (-> reviews) -------------------------------------------------


@app.get("/moderation/reviews")
def moderation_queue(request: Request) -> Response:
    with _client() as client:
        upstream = client.get(
            f"{settings.reviews_url}/moderation/reviews", headers=_bearer(request)
        )
    return _passthrough(upstream, no_store=True)


@app.post("/moderation/reviews/{review_id}/approve")
def approve(review_id: str, request: Request) -> Response:
    return _moderate(review_id, "approve", request)


@app.post("/moderation/reviews/{review_id}/reject")
def reject(review_id: str, request: Request) -> Response:
    return _moderate(review_id, "reject", request)


def _moderate(review_id: str, action: str, request: Request) -> Response:
    with _client() as client:
        upstream = client.post(
            f"{settings.reviews_url}/moderation/reviews/{review_id}/{action}",
            headers=_bearer(request),
        )
    return _passthrough(upstream, no_store=True)


# --- helpers -----------------------------------------------------------------


def _passthrough(upstream: httpx.Response, *, no_store: bool = False) -> Response:
    """Return an upstream JSON response unchanged (same body + status)."""
    try:
        content = upstream.json()
        resp = JSONResponse(status_code=upstream.status_code, content=content)
    except json.JSONDecodeError:
        resp = Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "application/json"),
        )
    if no_store:
        resp.headers["Cache-Control"] = "no-store"
    return resp
