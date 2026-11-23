"""Reviews domain logic: submission validation and moderation decisions.

Preserves the Stage 2/3 rules: rating 1-5, text 1-2000 chars (trimmed), optional
title <= 120 chars, up to three validated images, one review per author per
product, and terminal moderation transitions. Approve/reject write the outgoing
projection event into the outbox transactionally with the state change.
"""

from __future__ import annotations

import uuid

import httpx

from contracts.envelope import EventEnvelope
from contracts.events import (
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    ProjectionImage,
    ReviewProjectionData,
    ReviewRejectedData,
)
from contracts.settings import get_settings

from app.db import DuplicateReviewError, Review, ReviewImage, ReviewStore
from app.images import ImageStore, ImageValidationError

MIN_RATING, MAX_RATING = 1, 5
MAX_TEXT_LENGTH = 2000
MAX_TITLE_LENGTH = 120
MAX_IMAGES = 3

settings = get_settings()


class ProductNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ReviewValidationError(Exception):
    def __init__(self, offending_fields: list[str], message: str) -> None:
        super().__init__(message)
        self.offending_fields = offending_fields
        self.message = message


class ModerationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _product_exists(product_id: str) -> bool:
    """Check product existence via the commerce service (catalog owner).

    This is an HTTP read, not a cross-service database read, so store ownership
    is respected.
    """
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.commerce_url}/products/{product_id}")
        return resp.status_code == 200
    except httpx.HTTPError:
        # If commerce is unreachable, fail closed on product existence.
        return False


def _validate(rating, text, title, images, image_store: ImageStore) -> list[str]:
    offending: list[str] = []
    if not isinstance(rating, int) or isinstance(rating, bool):
        offending.append("rating")
    elif rating < MIN_RATING or rating > MAX_RATING:
        offending.append("rating")

    if not isinstance(text, str) or text.strip() == "":
        offending.append("text")
    elif len(text) > MAX_TEXT_LENGTH:
        offending.append("text")

    if title is not None:
        if not isinstance(title, str) or len(title) > MAX_TITLE_LENGTH:
            offending.append("title")

    if len(images) > MAX_IMAGES:
        offending.append("images")
    else:
        for image in images:
            try:
                image_store.validate(image["mediaType"], image["dataBase64"])
            except (ImageValidationError, KeyError, TypeError):
                offending.append("images")
                break
    return offending


def submit_review(
    product_id: str,
    author_identity: str,
    rating,
    text,
    title,
    images: list[dict],
    *,
    store: ReviewStore,
    image_store: ImageStore,
) -> Review:
    if not _product_exists(product_id):
        raise ProductNotFoundError(f"No product exists with id '{product_id}'.")

    offending = _validate(rating, text, title, images, image_store)
    if offending:
        raise ReviewValidationError(
            offending_fields=offending,
            message=(
                "The review could not be submitted. Please correct the "
                "following field(s): " + ", ".join(offending) + "."
            ),
        )

    if store.find_by_author_and_product(author_identity, product_id) is not None:
        raise DuplicateReviewError()

    stored_images: list[ReviewImage] = []
    for image in images:
        image_id, filename = image_store.store(image["mediaType"], image["dataBase64"])
        stored_images.append(
            ReviewImage(id=image_id, media_type=image["mediaType"], filename=filename)
        )

    review = Review(
        id=str(uuid.uuid4()),
        product_id=product_id,
        author_identity=author_identity,
        rating=rating,
        title=title if isinstance(title, str) and title != "" else None,
        text=text,
        images=stored_images,
        moderation_state="pending",
    )
    return store.add(review)


def _projection_payload(review: Review) -> dict:
    data = ReviewProjectionData(
        review_id=review.id,
        product_id=review.product_id,
        author_identity=review.author_identity,
        rating=review.rating,
        title=review.title,
        text=review.text,
        images=[
            ProjectionImage(
                id=img.id,
                image_url=f"/reviews/images/{img.id}",
                media_type=img.media_type,
            )
            for img in review.images
        ],
    )
    return data.model_dump(by_alias=True)


def approve_review(review_id: str, *, store: ReviewStore) -> Review:
    return _decide(review_id, "approved", REVIEW_APPROVED, store=store)


def reject_review(review_id: str, *, store: ReviewStore) -> Review:
    return _decide(review_id, "rejected", REVIEW_REJECTED, store=store)


def _decide(
    review_id: str, new_state: str, event_type: str, *, store: ReviewStore
) -> Review:
    existing = store.get(review_id)
    if existing is None:
        raise ModerationError("review_not_found", "The review to moderate does not exist.")
    if existing.moderation_state != "pending":
        raise ModerationError(
            "already_decided",
            "This review has already been moderated and cannot be changed.",
        )

    # Build the event envelope for the decision.
    if new_state == "approved":
        # Reflect the approved state onto the projection payload.
        approved_review = Review(
            id=existing.id,
            product_id=existing.product_id,
            author_identity=existing.author_identity,
            rating=existing.rating,
            title=existing.title,
            text=existing.text,
            images=existing.images,
            moderation_state="approved",
        )
        data = _projection_payload(approved_review)
    else:
        data = ReviewRejectedData(
            review_id=existing.id, product_id=existing.product_id
        ).model_dump(by_alias=True)

    envelope = EventEnvelope.build(event_type, data)
    try:
        return store.decide_with_outbox(
            review_id,
            new_state,
            envelope.event_id,
            envelope.event_type,
            envelope.to_bytes().decode("utf-8"),
        )
    except KeyError:
        raise ModerationError("review_not_found", "The review to moderate does not exist.")
    except ValueError:
        raise ModerationError(
            "already_decided",
            "This review has already been moderated and cannot be changed.",
        )
