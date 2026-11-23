"""SQLite-backed review store and transactional outbox (reviews service).

This is the reviews service's private store (``reviews.db``). It holds reviews
(with their image metadata as JSON) and an **outbox** table. A moderation
decision updates the review row and inserts the outgoing event into the outbox
within the **same transaction**, so a broker outage cannot lose an accepted
change (Stage 4 R4.3, R4.4). A background relay later publishes outbox rows.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "reviews.db"


def _db_path() -> Path:
    return Path(os.environ.get("REVIEWS_DB_PATH", str(_DEFAULT_DB)))


@dataclass
class ReviewImage:
    id: str
    media_type: str
    filename: str


@dataclass
class Review:
    id: str
    product_id: str
    author_identity: str
    rating: int
    text: str
    moderation_state: str = "pending"
    title: str | None = None
    images: list[ReviewImage] = field(default_factory=list)


@dataclass
class OutboxRow:
    id: int
    event_id: str
    event_type: str
    payload: str


class DuplicateReviewError(Exception):
    pass


class ReviewStore:
    """Private SQLite store for reviews and the outbox."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else _db_path()
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    author_identity TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    title TEXT,
                    text TEXT NOT NULL,
                    images_json TEXT NOT NULL,
                    moderation_state TEXT NOT NULL,
                    UNIQUE(author_identity, product_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    # --- reviews -------------------------------------------------------------

    def add(self, review: Review) -> Review:
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO reviews
                        (id, product_id, author_identity, rating, title, text,
                         images_json, moderation_state)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review.id,
                        review.product_id,
                        review.author_identity,
                        review.rating,
                        review.title,
                        review.text,
                        _images_to_json(review.images),
                        review.moderation_state,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateReviewError() from error
        return review

    def get(self, review_id: str) -> Review | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
        return _row_to_review(row) if row is not None else None

    def find_by_author_and_product(
        self, author_identity: str, product_id: str
    ) -> Review | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE author_identity = ? AND product_id = ?",
                (author_identity, product_id),
            ).fetchone()
        return _row_to_review(row) if row is not None else None

    def list_by_state(self, state: str) -> list[Review]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE moderation_state = ? ORDER BY id",
                (state,),
            ).fetchall()
        return [_row_to_review(row) for row in rows]

    def image_filename(self, image_id: str) -> str | None:
        """Return the stored filename for an image id across all reviews."""
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT images_json FROM reviews").fetchall()
        for row in rows:
            for image in json.loads(row["images_json"]):
                if image["id"] == image_id:
                    return image["filename"]
        return None

    def decide_with_outbox(
        self, review_id: str, new_state: str, event_id: str, event_type: str,
        payload: str,
    ) -> Review:
        """Apply a terminal moderation decision AND enqueue its event atomically.

        The review-state update and the outbox insert share one transaction, so
        an accepted decision and its outgoing event are durably committed
        together even if the broker is unreachable (R4.3, R4.4).

        Raises:
            KeyError: unknown review.
            ValueError: review already decided (terminal).
        """
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
            if row is None:
                raise KeyError(review_id)
            if row["moderation_state"] != "pending":
                raise ValueError("already_decided")
            conn.execute(
                "UPDATE reviews SET moderation_state = ? WHERE id = ?",
                (new_state, review_id),
            )
            conn.execute(
                "INSERT INTO outbox (event_id, event_type, payload, created_at)"
                " VALUES (?, ?, ?, ?)",
                (event_id, event_type, payload, datetime.now(timezone.utc).isoformat()),
            )
            updated = conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
        return _row_to_review(updated)

    # --- outbox --------------------------------------------------------------

    def unsent_outbox(self, limit: int = 100) -> list[OutboxRow]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_id, event_type, payload FROM outbox"
                " WHERE sent_at IS NULL ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            OutboxRow(
                id=row["id"],
                event_id=row["event_id"],
                event_type=row["event_type"],
                payload=row["payload"],
            )
            for row in rows
        ]

    def mark_sent(self, outbox_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE outbox SET sent_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), outbox_id),
            )

    def increment_attempts(self, outbox_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE outbox SET attempts = attempts + 1 WHERE id = ?", (outbox_id,)
            )

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM reviews")
            conn.execute("DELETE FROM outbox")


def _images_to_json(images: list[ReviewImage]) -> str:
    return json.dumps(
        [
            {"id": img.id, "mediaType": img.media_type, "filename": img.filename}
            for img in images
        ]
    )


def _row_to_review(row: sqlite3.Row) -> Review:
    images = [
        ReviewImage(id=i["id"], media_type=i["mediaType"], filename=i["filename"])
        for i in json.loads(row["images_json"])
    ]
    return Review(
        id=row["id"],
        product_id=row["product_id"],
        author_identity=row["author_identity"],
        rating=row["rating"],
        title=row["title"],
        text=row["text"],
        images=images,
        moderation_state=row["moderation_state"],
    )
