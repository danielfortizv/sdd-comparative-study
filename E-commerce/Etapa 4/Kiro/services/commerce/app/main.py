"""Commerce service FastAPI app (Stage 4, port 18202).

Owns the catalog, simulated checkout, and the public review projection. The
projection is kept coherent by a background RabbitMQ consumer of review
moderation events. Endpoints:

- ``GET /products`` / ``GET /products/{id}`` — catalog (cacheable).
- ``POST /checkout/confirm`` — simulated purchase.
- ``GET /products/{id}/reviews`` — approved reviews + rating summary from the
  projection, plus the caller's own non-approved review (resolved from the
  reviews service using the caller's token).
- ``GET /health`` — readiness.

Run with: ``uvicorn app.main:app --port 18202``.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header, Request, status
from fastapi.responses import JSONResponse, Response

from contracts.settings import get_settings
from contracts.tokens import verify_token

from app import catalog
from app.cache import response_cache
from app.checkout import CheckoutError, CheckoutRequest, confirm_checkout
from app.consumer import ProjectionConsumer
from app.db import ProjectionStore

settings = get_settings()
store = ProjectionStore()
consumer = ProjectionConsumer(store)
app = FastAPI(title="Stage 4 Commerce Service", version="1.0.0")

_CACHEABLE_PATHS = {"/products"}


@app.on_event("startup")
def _start_consumer() -> None:
    # Allow disabling the live consumer in unit tests that only exercise HTTP.
    if os.environ.get("COMMERCE_DISABLE_CONSUMER") != "1":
        consumer.start()


@app.on_event("shutdown")
def _stop_consumer() -> None:
    consumer.stop()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Catalog (cacheable) -----------------------------------------------------


@app.get("/products")
def list_products(request: Request) -> Response:
    key = "GET /products"
    cached = response_cache.get(key)
    if cached is not None:
        return _hit(cached.body, cached.media_type)
    products = [p.model_dump(by_alias=True) for p in catalog.list_products()]
    return _store_and_miss(key, products)


@app.get("/products/{product_id}")
def get_product(product_id: str) -> Response:
    key = f"GET /products/{product_id}"
    cached = response_cache.get(key)
    if cached is not None:
        return _hit(cached.body, cached.media_type)
    product = catalog.get_product(product_id)
    if product is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "product_not_found",
                "message": f"No product exists with id '{product_id}'.",
                "productId": product_id,
            },
        )
    return _store_and_miss(key, product.model_dump(by_alias=True))


# --- Checkout ----------------------------------------------------------------


@app.post("/checkout/confirm")
def checkout(request: CheckoutRequest) -> JSONResponse:
    try:
        confirmation = confirm_checkout(request)
    except CheckoutError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": {"code": error.code, "message": error.message}},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=confirmation.model_dump(by_alias=True),
    )


# --- Public reviews (projection + own review) --------------------------------


@app.get("/products/{product_id}/reviews")
def product_reviews(
    product_id: str, authorization: str | None = Header(default=None)
) -> JSONResponse:
    approved = store.list_by_product(product_id)
    count = len(approved)
    average = (
        round(sum(r["rating"] for r in approved) / count, 2) if count else 0.0
    )
    summary = {"count": count, "average": average}

    own_review = _resolve_own_review(product_id, authorization)

    body = {"reviews": approved, "summary": summary, "ownReview": own_review}
    resp = JSONResponse(status_code=status.HTTP_200_OK, content=body)
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _resolve_own_review(product_id: str, authorization: str | None):
    """Fetch the caller's own non-approved review from the reviews service.

    The caller's identity comes from the signed token (never a client role
    header). Commerce does not read the reviews database; it asks the reviews
    service over HTTP, honoring store ownership.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_token(token)
    if claims is None or claims.is_moderator:
        return None
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{settings.reviews_url}/internal/own-review",
                params={"productId": product_id, "author": claims.identifier},
                headers={"Authorization": authorization},
            )
        if resp.status_code == 200:
            return resp.json()
    except httpx.HTTPError:
        return None
    return None


# --- cache helpers -----------------------------------------------------------


def _hit(body: bytes, media_type: str) -> Response:
    resp = Response(content=body, media_type=media_type)
    resp.headers["X-Cache"] = "HIT"
    resp.headers["Cache-Control"] = f"public, max-age={response_cache.ttl_seconds}"
    return resp


def _store_and_miss(key: str, payload) -> Response:
    import json

    body = json.dumps(payload).encode("utf-8")
    response_cache.set(key, body, "application/json")
    resp = Response(content=body, media_type="application/json")
    resp.headers["X-Cache"] = "MISS"
    resp.headers["Cache-Control"] = f"public, max-age={response_cache.ttl_seconds}"
    return resp
