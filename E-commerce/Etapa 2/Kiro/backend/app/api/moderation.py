"""Moderation API router (API layer, Stage 2).

Exposes the moderator-only review moderation endpoints over HTTP/JSON:

- ``GET /moderation/reviews`` - list the Moderation_Queue of pending reviews
  (Requirements 3.1, 3.2).
- ``POST /moderation/reviews/{review_id}/approve`` - approve a pending review
  (Requirements 3.3, 3.5, 3.7).
- ``POST /moderation/reviews/{review_id}/reject`` - reject a pending review
  (Requirements 3.4, 3.5, 3.7).

Every endpoint is guarded by an active moderator session: without one, the
request is denied and no state changes (Requirements 3.6, 6.4). The router
delegates all transitions to the review service and maps outcomes to
structured JSON. It never exposes internal detail (Requirement 6.1).
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.models.review import Review, ReviewResponse
from app.services import review_service
from app.services.review_service import ModerationError
from app.services.signin_service import get_current_session

router = APIRouter(prefix="/moderation", tags=["moderation"])


def _moderator_denied_response() -> JSONResponse:
    """Build the uniform denial for a request lacking a moderator session."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "moderator_required",
            "message": "Moderator access is required to perform this action.",
        },
    )


def _is_active_moderator() -> bool:
    """Return whether the current session is an active moderator session (A5)."""
    session = get_current_session()
    return session.active and session.is_moderator


def _to_response(review: Review) -> ReviewResponse:
    """Map a stored ``Review`` onto its HTTP/JSON response shape."""
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


@router.get("/reviews", response_model=list[ReviewResponse])
def list_moderation_queue():
    """Return the pending moderation queue (moderator session required)."""
    if not _is_active_moderator():
        return _moderator_denied_response()
    pending = review_service.list_pending_reviews()
    return [_to_response(review) for review in pending]


@router.post("/reviews/{review_id}/approve", response_model=ReviewResponse)
def approve_review(review_id: str):
    """Approve a pending review (moderator session required)."""
    if not _is_active_moderator():
        return _moderator_denied_response()
    try:
        review = review_service.approve_review(review_id)
    except ModerationError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": error.code, "message": error.message},
        )
    return _to_response(review)


@router.post("/reviews/{review_id}/reject", response_model=ReviewResponse)
def reject_review(review_id: str):
    """Reject a pending review (moderator session required)."""
    if not _is_active_moderator():
        return _moderator_denied_response()
    try:
        review = review_service.reject_review(review_id)
    except ModerationError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": error.code, "message": error.message},
        )
    return _to_response(review)
