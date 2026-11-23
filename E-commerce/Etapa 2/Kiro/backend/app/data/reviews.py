"""In-process review storage (data-access layer, Stage 2).

This module keeps review records in in-process storage for the running service,
mirroring the Stage 1 ``AccountStore`` style: an in-memory dict that returns
copies so callers cannot mutate stored state (Requirement 9.6, Assumption A6).
It stores no credential values and nothing durable; review records live only
for the lifetime of the backend process. Review image bytes are stored
separately on disk by ``review_images.py``.
"""

from __future__ import annotations

from app.models.review import ModerationState, Review


class ReviewStore:
    """In-process read/write store for reviews.

    Reviews are indexed by their ``id``. All reads return copies so the stored
    data stays immutable to callers. State transitions are performed by
    replacing the stored review with an updated copy.
    """

    def __init__(self) -> None:
        self._reviews_by_id: dict[str, Review] = {}

    def add(self, review: Review) -> Review:
        """Store a new review, returning a copy of the stored record.

        Raises:
            ValueError: If a review with the same id already exists.
        """
        if review.id in self._reviews_by_id:
            raise ValueError(f"A review already exists with id: {review.id}")
        self._reviews_by_id[review.id] = review.model_copy(deep=True)
        return review.model_copy(deep=True)

    def get(self, review_id: str) -> Review | None:
        """Return the review with the given id, or ``None``."""
        review = self._reviews_by_id.get(review_id)
        return review.model_copy(deep=True) if review is not None else None

    def list_all(self) -> list[Review]:
        """Return copies of all stored reviews."""
        return [review.model_copy(deep=True) for review in self._reviews_by_id.values()]

    def list_by_product(self, product_id: str) -> list[Review]:
        """Return all reviews associated with the given product."""
        return [
            review.model_copy(deep=True)
            for review in self._reviews_by_id.values()
            if review.product_id == product_id
        ]

    def list_by_state(self, state: ModerationState) -> list[Review]:
        """Return all reviews currently in the given moderation state."""
        return [
            review.model_copy(deep=True)
            for review in self._reviews_by_id.values()
            if review.moderation_state == state
        ]

    def find_by_author_and_product(
        self, author_identity: str, product_id: str
    ) -> Review | None:
        """Return the given author's review for the product, or ``None``.

        Supports the one-review-per-author-per-product rule (Assumption A1).
        """
        for review in self._reviews_by_id.values():
            if (
                review.author_identity == author_identity
                and review.product_id == product_id
            ):
                return review.model_copy(deep=True)
        return None

    def replace(self, review: Review) -> Review:
        """Replace an existing review with an updated copy (used for transitions).

        Raises:
            KeyError: If no review with this id exists.
        """
        if review.id not in self._reviews_by_id:
            raise KeyError(f"No review exists with id: {review.id}")
        self._reviews_by_id[review.id] = review.model_copy(deep=True)
        return review.model_copy(deep=True)

    def clear(self) -> None:
        """Remove all stored reviews. Provided so tests start from empty."""
        self._reviews_by_id.clear()


# Shared in-process review store for the running service. Review data lives only
# for the lifetime of the process; nothing is persisted durably.
review_store = ReviewStore()
