"""Reviews service FastAPI app (Stage 4, port 18203).

Owns review submission, image storage, moderation, and the transactional
outbox. A background relay publishes outbox events to RabbitMQ. Endpoints:

- ``POST /products/{id}/reviews`` — submit a review (customer token required).
- ``GET /moderation/reviews`` — pending queue (moderator token required).
- ``POST /moderation/reviews/{id}/approve`` / ``/reject`` — terminal decisions.
- ``GET /reviews/images/{id}`` — serve stored image bytes.
- ``GET /internal/own-review`` — caller's own non-approved review (for commerce).
- ``GET /health`` — readiness.

Authorization is derived from the signed Bearer token only; no client-supplied
role header is trusted (Stage 4 R5.1).

Run with: ``uvicorn app.main:app --port 18203``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from contracts.tokens import TokenClaims, verify_token

from app.db import DuplicateReviewError, Review, ReviewStore
from app.images import ImageStore
from app.relay import OutboxRelay
from app.service import (
    ModerationError,
    ProductNotFoundError,
    ReviewValidationError,
    approve_review,
    reject_review,
    submit_review,
)

store = ReviewStore()
image_store = ImageStore()
relay = OutboxRelay(store)
app = FastAPI(title="Stage 4 Reviews Service", version="1.0.0")


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ReviewSubmission(_CamelModel):
    rating: int | None = None
    text: str | None = None
    title: str | None = None
    images: list[dict] = []


@app.on_event("startup")
def _start_relay() -> None:
    if os.environ.get("REVIEWS_DISABLE_RELAY") != "1":
        relay.start()


@app.on_event("shutdown")
def _stop_relay() -> None:
    relay.stop()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- auth helpers ------------------------------------------------------------


def _claims(authorization: str | None) -> TokenClaims | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return verify_token(authorization.split(" ", 1)[1].strip())


def _review_to_response(review: Review) -> dict:
    return {
        "id": review.id,
        "productId": review.product_id,
        "authorIdentity": review.author_identity,
        "rating": review.rating,
        "title": review.title,
        "text": review.text,
        "images": [
            {
                "id": img.id,
                "imageUrl": f"/reviews/images/{img.id}",
                "mediaType": img.media_type,
            }
            for img in review.images
        ],
        "moderationState": review.moderation_state,
    }


def _moderator_denied() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "moderator_required",
            "message": "Moderator access is required to perform this action.",
        },
    )


# --- submission --------------------------------------------------------------


@app.post("/products/{product_id}/reviews", status_code=status.HTTP_201_CREATED)
def submit(
    product_id: str,
    submission: ReviewSubmission,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    claims = _claims(authorization)
    if claims is None or claims.is_moderator:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_required",
                "message": "You must be signed in as a customer to submit a review.",
            },
        )
    try:
        review = submit_review(
            product_id,
            claims.identifier,
            submission.rating,
            submission.text,
            submission.title,
            submission.images,
            store=store,
            image_store=image_store,
        )
    except ProductNotFoundError as error:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "product_not_found", "message": error.message},
        )
    except ReviewValidationError as error:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": error.message,
                "offendingFields": error.offending_fields,
            },
        )
    except DuplicateReviewError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "duplicate_review",
                "message": "You have already reviewed this product.",
            },
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED, content=_review_to_response(review)
    )


# --- moderation --------------------------------------------------------------


@app.get("/moderation/reviews")
def moderation_queue(authorization: str | None = Header(default=None)) -> JSONResponse:
    claims = _claims(authorization)
    if claims is None or not claims.is_moderator:
        return _moderator_denied()
    pending = store.list_by_state("pending")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=[_review_to_response(r) for r in pending],
    )


@app.post("/moderation/reviews/{review_id}/approve")
def approve(
    review_id: str, authorization: str | None = Header(default=None)
) -> JSONResponse:
    return _moderate(review_id, approve_review, authorization)


@app.post("/moderation/reviews/{review_id}/reject")
def reject(
    review_id: str, authorization: str | None = Header(default=None)
) -> JSONResponse:
    return _moderate(review_id, reject_review, authorization)


def _moderate(review_id: str, action, authorization: str | None) -> JSONResponse:
    claims = _claims(authorization)
    if claims is None or not claims.is_moderator:
        return _moderator_denied()
    try:
        review = action(review_id, store=store)
    except ModerationError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": error.code, "message": error.message},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=_review_to_response(review)
    )


# --- images ------------------------------------------------------------------


@app.get("/reviews/images/{image_id}")
def get_image(image_id: str) -> Response:
    filename = store.image_filename(image_id)
    if filename is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": {
                    "error": "image_not_found",
                    "message": "No review image exists with that id.",
                }
            },
        )
    try:
        data, media_type = image_store.read(filename)
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": {
                    "error": "image_not_found",
                    "message": "No review image exists with that id.",
                }
            },
        )
    return Response(content=data, media_type=media_type)


# --- internal ----------------------------------------------------------------


@app.get("/internal/own-review")
def own_review(
    productId: str,  # noqa: N803 - query param name matches the wire contract
    author: str,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Return the caller's own non-approved review for a product, or null.

    Only the authenticated caller may read their own review: the token's
    identifier must match the requested author.
    """
    claims = _claims(authorization)
    if claims is None or claims.identifier != author:
        return JSONResponse(status_code=status.HTTP_200_OK, content=None)
    review = store.find_by_author_and_product(author, productId)
    if review is None or review.moderation_state == "approved":
        return JSONResponse(status_code=status.HTTP_200_OK, content=None)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=_review_to_response(review)
    )
