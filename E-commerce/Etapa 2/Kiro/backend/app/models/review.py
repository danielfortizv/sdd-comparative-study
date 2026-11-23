"""Review data models (Stage 2: reviews with images and moderation).

These models describe product reviews, their attached images, the moderation
lifecycle, and the HTTP/JSON request/response contracts for the Stage 2
endpoints. They follow the Stage 1 convention of serializing camelCase to the
HTTP/JSON interface while keeping snake_case Python identifiers
(``ConfigDict(alias_generator=to_camel, populate_by_name=True)``).

Design references:
- ``Review`` carries a stable identity, its Product association, the authoring
  account identity (non-sensitive), the rating, optional title, required text,
  attached images, and the moderation state (Requirements 1.6, 1.7, 5.1, 5.4;
  Assumptions A2, A3, A4).
- Submitted images arrive base64-encoded with a declared media type and are
  validated and stored locally; the raw bytes are never part of a stored model
  (Assumption A3).
- No password or credential value is ever placed on a review (Requirement 5.4),
  and no editable/deletable surface is modeled (Requirements 5.2, 5.3).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# The moderation lifecycle states (Assumption A4). A review starts ``pending``
# and a moderator moves it to one terminal state (``approved`` or ``rejected``).
ModerationState = Literal["pending", "approved", "rejected"]


class _CamelModel(BaseModel):
    """Base model serializing fields in camelCase for the HTTP/JSON interface."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ReviewImage(_CamelModel):
    """A stored image attached to a review (metadata only).

    The raw bytes live on disk in the local demonstration image folder and are
    streamed by ``GET /reviews/images/{id}``; this model carries only the
    metadata needed to reference and serve them (Assumption A3).

    Attributes:
        id: Stable image identity used in the image-serving URL.
        media_type: One of the allowed image media types.
        filename: Generated local filename under the image folder.
    """

    id: str
    media_type: str
    filename: str


class Review(_CamelModel):
    """A customer-authored review of a Product.

    Attributes:
        id: Stable review identity.
        product_id: References ``Product.id`` (Stage 1 shared identity).
        author_identity: The authoring account's identifier; a non-sensitive
            value, never a password or credential (Requirements 5.1, 5.4).
        rating: Integer star rating from 1 to 5 (Assumption A2).
        title: Optional short title (<= 120 characters).
        text: Required review body (1..2000 characters after trimming).
        images: Zero to three attached images (Assumption A3).
        moderation_state: The current lifecycle state (Assumption A4).
    """

    id: str
    product_id: str
    author_identity: str
    rating: int
    title: str | None = None
    text: str
    images: list[ReviewImage] = []
    moderation_state: ModerationState = "pending"


class ReviewImageInput(_CamelModel):
    """A single image submitted as part of a review (request input only).

    Images are transferred base64-encoded with a declared media type to keep
    the local demo simple and dependency-free (Assumption A3). The declared
    media type is validated against the allow-list before any bytes are stored.

    Attributes:
        media_type: Declared media type (validated against the allow-list).
        data_base64: Base64-encoded image bytes.
    """

    media_type: str
    data_base64: str


class ReviewSubmission(_CamelModel):
    """The review a customer submits for a product (request input).

    Attributes:
        rating: Integer star rating (validated to 1..5).
        text: Required review body (validated non-empty, <= 2000 chars).
        title: Optional short title (validated <= 120 chars).
        images: Zero to three images to attach (validated count/type/size).
    """

    rating: int | None = None
    text: str | None = None
    title: str | None = None
    images: list[ReviewImageInput] = []


class ReviewImageResponse(_CamelModel):
    """An attached image as surfaced to the frontend.

    Attributes:
        id: Stable image identity.
        image_url: Relative URL to fetch the image bytes
            (``/reviews/images/{id}``) for direct use by an ``<img>`` element.
        media_type: The stored media type.
    """

    id: str
    image_url: str
    media_type: str


class ReviewResponse(_CamelModel):
    """A review as surfaced to the frontend.

    Carries only non-sensitive fields; the author identity is a display
    identifier and never a credential value (Requirement 5.4).
    """

    id: str
    product_id: str
    author_identity: str
    rating: int
    title: str | None = None
    text: str
    images: list[ReviewImageResponse] = []
    moderation_state: ModerationState


class RatingSummary(_CamelModel):
    """Aggregate rating for a product's visible (approved) reviews.

    Attributes:
        count: Number of approved reviews for the product.
        average: Mean rating across approved reviews (0 when there are none).
    """

    count: int = 0
    average: float = 0.0


class ProductReviewsResponse(_CamelModel):
    """Public reviews payload for a product.

    Attributes:
        reviews: The approved (visible) reviews for the product (Requirement
            4.1, 4.2).
        summary: The rating summary computed from approved reviews only
            (Requirements 4.3, 4.5).
        own_review: The requesting session's own non-approved review for this
            product, if any, so the author can see its state (Requirement 4.6).
            ``None`` when there is no active session or no such review.
    """

    reviews: list[ReviewResponse] = []
    summary: RatingSummary = RatingSummary()
    own_review: ReviewResponse | None = None
