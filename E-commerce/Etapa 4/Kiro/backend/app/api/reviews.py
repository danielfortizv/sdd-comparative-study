"""Reviews API router (API layer, Stage 2).

Exposes the public and authoring review endpoints over HTTP/JSON:

- ``POST /products/{product_id}/reviews`` - submit a review. Requires an active
  non-moderator customer session (Requirements 1.1, 1.2). Validates the
  submission and creates a ``pending`` review (Requirements 1.3-1.8).
- ``GET /products/{product_id}/reviews`` - list the approved reviews and the
  rating summary for a product, plus the requester's own non-approved review
  when applicable (Requirements 4.1-4.6).
- ``GET /reviews/images/{image_id}`` - stream a stored review image's bytes
  (Requirements 2.6, 2.7).

The router validates request shape and session/authorization, delegates all
business rules to the review service, and maps outcomes to structured JSON
with appropriate status codes. It never exposes internal detail or credential
values (Requirement 6.1).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, Response

from app.data.accounts import account_store
from app.data.review_images import image_store
from app.data.reviews import review_store
from app.models.review import (
    ProductReviewsResponse,
    RatingSummary,
    Review,
    ReviewResponse,
    ReviewSubmission,
)
from app.services import review_service
from app.services.review_service import (
    DuplicateReviewError,
    ProductNotFoundError,
    ReviewValidationError,
)
from app.services.signin_service import get_current_session

router = APIRouter(tags=["reviews"])


def _resolve_customer_identity() -> str | None:
    """Return the active non-moderator customer's identifier, or ``None``.

    Resolves the module-level session's ``customer_id`` to the account's
    non-sensitive identifier used as a review's author identity. Returns
    ``None`` when there is no active session, when the account cannot be
    resolved, or when the active session is a moderator (a moderator is not a
    review-authoring customer in this demo).
    """
    session = get_current_session()
    if not session.active or session.customer_id is None or session.is_moderator:
        return None
    account = account_store.get_by_id(session.customer_id)
    return account.identifier if account is not None else None


def _to_response(review: Review) -> ReviewResponse:
    """Map a stored ``Review`` onto its safe HTTP/JSON response shape."""
    return ReviewResponse(
        id=review.id,
        product_id=review.product_id,
        author_identity=review.author_identity,
        rating=review.rating,
        title=review.title,
        text=review.text,
        images=[
            {
                "id": image.id,
                "imageUrl": f"/reviews/images/{image.id}",
                "mediaType": image.media_type,
            }
            for image in review.images
        ],
        moderation_state=review.moderation_state,
    )


@router.post(
    "/products/{product_id}/reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewResponse,
)
def submit_review(product_id: str, submission: ReviewSubmission):
    """Submit a review for a product (requires an active customer session)."""
    author_identity = _resolve_customer_identity()
    if author_identity is None:
        # Identification is required to submit a review (R1.2, R6.1).
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_required",
                "message": "You must be signed in as a customer to submit a review.",
            },
        )

    try:
        review = review_service.submit_review(
            product_id=product_id,
            author_identity=author_identity,
            rating=submission.rating,
            text=submission.text,
            title=submission.title,
            images=submission.images,
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
    except DuplicateReviewError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "duplicate_review", "message": error.message},
        )

    return _to_response(review)


@router.get(
    "/products/{product_id}/reviews",
    response_model=ProductReviewsResponse,
)
def list_product_reviews(product_id: str) -> ProductReviewsResponse:
    """Return approved reviews, the rating summary, and the requester's own review."""
    approved = review_service.list_approved_reviews(product_id)
    summary: RatingSummary = review_service.rating_summary(product_id)

    own: ReviewResponse | None = None
    author_identity = _resolve_customer_identity()
    if author_identity is not None:
        own_review = review_service.own_review(product_id, author_identity)
        if own_review is not None:
            own = _to_response(own_review)

    return ProductReviewsResponse(
        reviews=[_to_response(review) for review in approved],
        summary=summary,
        own_review=own,
    )


@router.get("/reviews/images/{image_id}")
def get_review_image(image_id: str) -> Response:
    """Stream a stored review image's bytes with its media type (R2.6, R2.7)."""
    # Resolve the image's stored filename from the review that references it.
    filename: str | None = None
    for review in review_store.list_all():
        for image in review.images:
            if image.id == image_id:
                filename = image.filename
                break
        if filename is not None:
            break

    if filename is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "image_not_found",
                "message": "No review image exists with that id.",
            },
        )

    try:
        data, media_type = image_store.read(image_id, filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "image_not_found",
                "message": "No review image exists with that id.",
            },
        )

    return Response(content=data, media_type=media_type)
