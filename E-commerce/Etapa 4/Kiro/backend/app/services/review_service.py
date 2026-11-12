"""Review and moderation service (business logic, Stage 2).

This service owns the Stage 2 business rules:

- Submission validation and review creation (Requirements 1.3-1.8, 2.1-2.5;
  Assumptions A1, A2, A3): rating range, text/title length, image count/type/
  size, one-review-per-author-per-product, and creation in ``pending`` state
  with the author identity recorded.
- Moderation transitions (Requirements 3.1, 3.3-3.5, 3.7; Assumption A4): the
  pending queue, and terminal approve/reject from ``pending``.
- Public visibility and aggregation (Requirements 4.1-4.5; Assumption A8): the
  approved reviews for a product and a rating summary derived from approved
  ratings only.

The service never handles credential values and builds only safe,
client-facing error messages (Requirement 6.1). Image validation and storage
are delegated to the local on-disk image store; a rejected attachment is never
stored (Requirements 2.3, 2.4, 6.3).
"""

from __future__ import annotations

import uuid

from app.data import catalog
from app.data.review_images import ImageStore, ImageValidationError, image_store
from app.data.reviews import ReviewStore, review_store
from app.models.review import (
    RatingSummary,
    Review,
    ReviewImage,
    ReviewImageInput,
)

# Field bounds (Assumption A2, A3). These are demonstration conveniences.
MIN_RATING = 1
MAX_RATING = 5
MAX_TEXT_LENGTH = 2000
MAX_TITLE_LENGTH = 120
MAX_IMAGES = 3


class ReviewValidationError(Exception):
    """A review submission failed field validation.

    Carries the exact set of offending field names so the API layer can build
    a structured error. It never carries any submitted credential value
    (Requirement 6.1). ``offending_fields`` is the authoritative set used by
    Property 1; ``message`` is a safe human-readable summary.
    """

    def __init__(self, offending_fields: list[str], message: str) -> None:
        super().__init__(message)
        # Preserve order but keep it a plain list of unique field names.
        seen: dict[str, None] = {}
        for name in offending_fields:
            seen.setdefault(name, None)
        self.offending_fields = list(seen.keys())
        self.message = message


class DuplicateReviewError(Exception):
    """The author already has a review for this product (Assumption A1)."""

    def __init__(self) -> None:
        self.message = "You have already reviewed this product. Only one review per product is allowed."
        super().__init__(self.message)


class ProductNotFoundError(Exception):
    """The product being reviewed does not exist in the catalog."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        self.message = "The product being reviewed does not exist."
        super().__init__(self.message)


class ModerationError(Exception):
    """A moderation action could not be performed.

    Raised for an unknown review or for an attempt to decide a review that is
    not ``pending`` (a decision is terminal, Assumption A4).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _validate_submission_fields(
    rating: object,
    text: object,
    title: object,
    images: list[ReviewImageInput],
) -> list[str]:
    """Return the set of offending field names for a submission.

    Classifies rating, text, title, and the image set against their rules. The
    returned list is exactly the fields that violate a rule (Property 1).
    Image validation here covers only the count and each image's declared type
    and decoded size, without storing anything.
    """
    offending: list[str] = []

    # Rating: required integer in [MIN_RATING, MAX_RATING] (R1.3).
    if not isinstance(rating, int) or isinstance(rating, bool):
        offending.append("rating")
    elif rating < MIN_RATING or rating > MAX_RATING:
        offending.append("rating")

    # Text: required, non-empty after trimming, <= MAX_TEXT_LENGTH (R1.4, R1.5).
    if not isinstance(text, str) or text.strip() == "":
        offending.append("text")
    elif len(text) > MAX_TEXT_LENGTH:
        offending.append("text")

    # Title: optional; when present must be <= MAX_TITLE_LENGTH (R1.5).
    if title is not None:
        if not isinstance(title, str) or len(title) > MAX_TITLE_LENGTH:
            offending.append("title")

    # Images: count <= MAX_IMAGES (R2.2), then each image's type/size (R2.3,
    # R2.4). The whole image set is reported under the single "images" field.
    if len(images) > MAX_IMAGES:
        offending.append("images")
    else:
        for image in images:
            try:
                image_store.validate(image.media_type, image.data_base64)
            except ImageValidationError:
                offending.append("images")
                break

    return offending


def submit_review(
    product_id: str,
    author_identity: str,
    rating: object,
    text: object,
    title: object = None,
    images: list[ReviewImageInput] | None = None,
    *,
    store: ReviewStore | None = None,
    images_store: ImageStore | None = None,
) -> Review:
    """Validate and create a ``pending`` review for a product.

    Args:
        product_id: The product being reviewed (must exist in the catalog).
        author_identity: The authoring account's non-sensitive identity.
        rating: Submitted integer rating.
        text: Submitted review body.
        title: Optional submitted title.
        images: Submitted image inputs (0..3).
        store: Review store to use; defaults to the shared in-process store.
        images_store: Image store to use; defaults to the shared local store.

    Returns:
        The created ``Review`` with ``moderation_state == "pending"``.

    Raises:
        ProductNotFoundError: If the product does not exist.
        DuplicateReviewError: If the author already reviewed this product.
        ReviewValidationError: If any field violates its rule; the error names
            the exact offending fields and contains no credential values.
    """
    active_store = store if store is not None else review_store
    active_images = images_store if images_store is not None else image_store
    submitted_images = images if images is not None else []

    # The product must exist so the review associates with a real catalog item.
    if catalog.get_product(product_id) is None:
        raise ProductNotFoundError(product_id)

    offending = _validate_submission_fields(rating, text, title, submitted_images)
    if offending:
        raise ReviewValidationError(
            offending_fields=offending,
            message=(
                "The review could not be submitted. Please correct the "
                "following field(s): " + ", ".join(offending) + "."
            ),
        )

    # One review per author per product (Assumption A1).
    if active_store.find_by_author_and_product(author_identity, product_id) is not None:
        raise DuplicateReviewError()

    # All fields valid: store images (validated again inside the store) and
    # build the pending review. Narrow types now that validation has passed.
    assert isinstance(rating, int)
    assert isinstance(text, str)
    stored_images: list[ReviewImage] = []
    for image in submitted_images:
        image_id, filename = active_images.store(image.media_type, image.data_base64)
        stored_images.append(
            ReviewImage(id=image_id, media_type=image.media_type, filename=filename)
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
    return active_store.add(review)


def list_pending_reviews(*, store: ReviewStore | None = None) -> list[Review]:
    """Return the Moderation_Queue: all reviews in ``pending`` (R3.1, R3.5)."""
    active_store = store if store is not None else review_store
    return active_store.list_by_state("pending")


def approve_review(review_id: str, *, store: ReviewStore | None = None) -> Review:
    """Approve a pending review, a terminal transition (R3.3, R3.7)."""
    return _decide_review(review_id, "approved", store=store)


def reject_review(review_id: str, *, store: ReviewStore | None = None) -> Review:
    """Reject a pending review, a terminal transition (R3.4, R3.7)."""
    return _decide_review(review_id, "rejected", store=store)


def _decide_review(
    review_id: str,
    new_state: str,
    *,
    store: ReviewStore | None = None,
) -> Review:
    """Apply a terminal moderation decision to a pending review.

    Raises:
        ModerationError: If the review is unknown, or if it is not ``pending``
            (a decided review cannot be moved again; Assumption A4).
    """
    active_store = store if store is not None else review_store

    review = active_store.get(review_id)
    if review is None:
        raise ModerationError(
            code="review_not_found",
            message="The review to moderate does not exist.",
        )
    if review.moderation_state != "pending":
        raise ModerationError(
            code="already_decided",
            message="This review has already been moderated and cannot be changed.",
        )

    updated = review.model_copy(update={"moderation_state": new_state})
    stored = active_store.replace(updated)

    # Stage 3 (Requirement 5.5): a moderation decision changes public review
    # visibility. The review-listing endpoint is intentionally uncached, so an
    # approval is already immediately visible; we additionally invalidate the
    # shared response cache here so freshness is enforced from a single,
    # obvious point even if review responses were cached in a future
    # extension. The import is local to avoid any import cycle at module load.
    from app.services import response_cache

    response_cache.invalidate()
    return stored


def list_approved_reviews(
    product_id: str, *, store: ReviewStore | None = None
) -> list[Review]:
    """Return the Visible_Reviews (approved) for a product (R4.1, R4.2)."""
    active_store = store if store is not None else review_store
    return [
        review
        for review in active_store.list_by_product(product_id)
        if review.moderation_state == "approved"
    ]


def rating_summary(
    product_id: str, *, store: ReviewStore | None = None
) -> RatingSummary:
    """Return the rating summary from approved reviews only (R4.3, R4.5).

    The count is the number of approved reviews; the average is the mean of
    their ratings (0 when there are none). The average is rounded to two
    decimal places for a stable display value.
    """
    approved = list_approved_reviews(product_id, store=store)
    count = len(approved)
    if count == 0:
        return RatingSummary(count=0, average=0.0)
    average = sum(review.rating for review in approved) / count
    return RatingSummary(count=count, average=round(average, 2))


def own_review(
    product_id: str,
    author_identity: str,
    *,
    store: ReviewStore | None = None,
) -> Review | None:
    """Return the author's own review for a product if it is not approved.

    Supports showing an author the state of their own non-approved submission
    (Requirement 4.6). An already-approved own review appears in the public
    list, so it is not returned here to avoid duplication.
    """
    active_store = store if store is not None else review_store
    review = active_store.find_by_author_and_product(author_identity, product_id)
    if review is None or review.moderation_state == "approved":
        return None
    return review
