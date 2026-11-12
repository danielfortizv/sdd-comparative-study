"""Apply moderation events to the commerce public review projection.

Pure application logic shared by the live broker consumer and the focused unit
tests, so the idempotency and upsert/remove behavior can be tested without a
broker (the adapter does not replace the real-broker acceptance run).
"""

from __future__ import annotations

from contracts.envelope import EventEnvelope
from contracts.events import (
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    ReviewProjectionData,
    ReviewRejectedData,
)

from app import cache
from app.db import ProjectionStore


class UnknownEventError(Exception):
    """Raised for an event type this consumer does not handle (poison)."""


def apply_event(envelope: EventEnvelope, store: ProjectionStore) -> bool:
    """Apply one moderation event to the projection, idempotently.

    Returns ``True`` when the projection changed, ``False`` when the event was
    a duplicate (already processed). Invalidates the cache on a real change so
    the next public read is coherent (R3.5). Raises :class:`UnknownEventError`
    for an unhandled type so the consumer can dead-letter it.
    """
    if envelope.event_type == REVIEW_APPROVED:
        data = ReviewProjectionData.model_validate(envelope.data)
        changed = store.apply_approved(envelope.event_id, data)
    elif envelope.event_type == REVIEW_REJECTED:
        data = ReviewRejectedData.model_validate(envelope.data)
        changed = store.apply_rejected(envelope.event_id, data.review_id)
    else:
        raise UnknownEventError(envelope.event_type)

    if changed:
        cache.invalidate()
    return changed
