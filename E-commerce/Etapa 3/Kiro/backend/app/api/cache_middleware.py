"""Catalog response-cache middleware (API layer, Stage 3).

This Starlette middleware adds bounded, TTL-based caching to the two
*session-independent* public catalog reads and marks session-varying or
moderation responses as non-cacheable. It is additive: request and response
bodies of every existing endpoint are unchanged; only cache/freshness response
headers are added (Stage 3 Requirements 5.1, 5.4, 7.1; Assumptions A3, A5).

Cached endpoints (safe to share across all callers):

- ``GET /products``
- ``GET /products/{id}`` (any single-segment product id)

Never cached and explicitly marked ``no-store`` (would vary per user or carry
authenticated data):

- ``/products/{id}/reviews`` — body includes the caller's own non-approved
  review, so it is session-dependent.
- ``/auth/*`` — authentication responses.
- ``/moderation/*`` — moderator-only queue and decisions.

Only ``200`` responses are stored, so errors are never cached. On a hit the
stored body is replayed with ``X-Cache: HIT``; on a miss the downstream body is
returned and stored with ``X-Cache: MISS``. Both carry
``Cache-Control: public, max-age=<ttl>``.
"""

from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.response_cache import response_cache

# Exact catalog list, and a single product by id (one path segment, so the
# ``/reviews`` sub-resource is NOT matched).
_PRODUCTS_LIST = re.compile(r"^/products/?$")
_PRODUCT_DETAIL = re.compile(r"^/products/[^/]+/?$")

# Route groups whose responses must never be cached by us or an intermediary.
_NO_STORE_PREFIXES = ("/auth", "/moderation")


def _is_cacheable_path(path: str) -> bool:
    """Return whether ``path`` is one of the two cacheable catalog reads."""
    return bool(_PRODUCTS_LIST.match(path) or _PRODUCT_DETAIL.match(path))


def _is_sensitive_path(path: str) -> bool:
    """Return whether ``path`` is session-varying or authenticated.

    These must be marked ``no-store`` so no shared cache (ours or an
    intermediary's) can leak per-user data between callers (Requirement 5.4).
    """
    if path.startswith(_NO_STORE_PREFIXES):
        return True
    # /products/{id}/reviews depends on the caller's session (ownReview).
    return bool(re.match(r"^/products/[^/]+/reviews/?$", path))


class CatalogCacheMiddleware(BaseHTTPMiddleware):
    """Cache the public catalog GETs; mark sensitive responses non-cacheable."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        method = request.method

        cacheable = method == "GET" and _is_cacheable_path(path)

        # Serve a live cache hit without touching downstream.
        if cacheable and response_cache.enabled:
            key = f"GET {path}"
            entry = response_cache.get(key)
            if entry is not None:
                hit = Response(content=entry.body, media_type=entry.media_type)
                hit.headers["X-Cache"] = "HIT"
                hit.headers["Cache-Control"] = (
                    f"public, max-age={response_cache.ttl_seconds}"
                )
                return hit

        response = await call_next(request)

        # Mark session-varying / authenticated responses non-cacheable.
        if _is_sensitive_path(path):
            response.headers["Cache-Control"] = "no-store"
            return response

        if not cacheable:
            return response

        if not response_cache.enabled:
            # Caching disabled (TTL=0): still advertise freshness semantics.
            response.headers["X-Cache"] = "MISS"
            return response

        # Store only successful responses, so errors are never cached.
        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body += chunk if isinstance(chunk, bytes) else chunk.encode()
            media_type = response.media_type or "application/json"
            response_cache.set(f"GET {path}", body, media_type)

            fresh = Response(
                content=body,
                status_code=response.status_code,
                media_type=media_type,
            )
            # Preserve any non-cache headers the downstream set.
            for header, value in response.headers.items():
                if header.lower() not in {"content-length", "x-cache", "cache-control"}:
                    fresh.headers[header] = value
            fresh.headers["X-Cache"] = "MISS"
            fresh.headers["Cache-Control"] = (
                f"public, max-age={response_cache.ttl_seconds}"
            )
            return fresh

        response.headers["X-Cache"] = "MISS"
        return response
