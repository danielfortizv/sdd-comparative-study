"""Event type constants and payload models for the Stage 4 broker flow.

Only the moderation->public-projection flow is carried over the broker in this
stage. Type strings are namespaced by ``EVENT_NAMESPACE`` (default
``stage4.kiro``) so they are unique to this tool-isolated deployment.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from contracts.settings import get_settings

_NS = get_settings().event_namespace

# Routing keys / event types.
REVIEW_APPROVED = f"{_NS}.review.approved"
REVIEW_REJECTED = f"{_NS}.review.rejected"


class ProjectionImage(BaseModel):
    """An approved review's image reference as surfaced publicly."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    image_url: str
    media_type: str


class ReviewProjectionData(BaseModel):
    """Payload for ``review.approved``: everything commerce needs publicly."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    review_id: str
    product_id: str
    author_identity: str
    rating: int
    title: str | None = None
    text: str
    images: list[ProjectionImage] = Field(default_factory=list)
    moderation_state: str = "approved"


class ReviewRejectedData(BaseModel):
    """Payload for ``review.rejected``: identifies the review to remove."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    review_id: str
    product_id: str
    moderation_state: str = "rejected"
