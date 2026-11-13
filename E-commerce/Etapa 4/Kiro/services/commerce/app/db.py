"""SQLite-backed public review projection owned by the commerce service.

This is the commerce service's private store (``commerce.db``). It holds the
public review projection (approved reviews only) and a ``processed_events``
table that makes the broker consumer idempotent (Stage 4 R4.2). Catalog data is
an immutable in-code fixture, so it is not stored here.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from contracts.events import ReviewProjectionData

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "commerce.db"


def _db_path() -> Path:
    return Path(os.environ.get("COMMERCE_DB_PATH", str(_DEFAULT_DB)))


class ProjectionStore:
    """Private SQLite store for the public review projection."""

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
                CREATE TABLE IF NOT EXISTS projection_reviews (
                    review_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    author_identity TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    title TEXT,
                    text TEXT NOT NULL,
                    images_json TEXT NOT NULL,
                    moderation_state TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL
                )
                """
            )

    def already_processed(self, event_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return row is not None

    def apply_approved(self, event_id: str, data: ReviewProjectionData) -> bool:
        """Upsert an approved review and record the event, atomically.

        Returns ``True`` if applied, ``False`` if the event was already
        processed (idempotent no-op). The event-id insert and the projection
        write share one transaction, so a crash cannot record the event without
        applying it.
        """
        with self._lock, self._connect() as conn:
            if self._is_processed(conn, event_id):
                return False
            conn.execute(
                """
                INSERT INTO projection_reviews
                    (review_id, product_id, author_identity, rating, title,
                     text, images_json, moderation_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'approved')
                ON CONFLICT(review_id) DO UPDATE SET
                    product_id=excluded.product_id,
                    author_identity=excluded.author_identity,
                    rating=excluded.rating,
                    title=excluded.title,
                    text=excluded.text,
                    images_json=excluded.images_json,
                    moderation_state='approved'
                """,
                (
                    data.review_id,
                    data.product_id,
                    data.author_identity,
                    data.rating,
                    data.title,
                    data.text,
                    json.dumps([img.model_dump(by_alias=True) for img in data.images]),
                ),
            )
            self._mark_processed(conn, event_id)
            return True

    def apply_rejected(self, event_id: str, review_id: str) -> bool:
        """Remove a review from the projection and record the event, atomically."""
        with self._lock, self._connect() as conn:
            if self._is_processed(conn, event_id):
                return False
            conn.execute(
                "DELETE FROM projection_reviews WHERE review_id = ?", (review_id,)
            )
            self._mark_processed(conn, event_id)
            return True

    @staticmethod
    def _is_processed(conn: sqlite3.Connection, event_id: str) -> bool:
        return (
            conn.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            is not None
        )

    @staticmethod
    def _mark_processed(conn: sqlite3.Connection, event_id: str) -> None:
        from datetime import datetime, timezone

        conn.execute(
            "INSERT OR IGNORE INTO processed_events (event_id, processed_at)"
            " VALUES (?, ?)",
            (event_id, datetime.now(timezone.utc).isoformat()),
        )

    def list_by_product(self, product_id: str) -> list[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projection_reviews WHERE product_id = ?"
                " ORDER BY review_id",
                (product_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["review_id"],
            "productId": row["product_id"],
            "authorIdentity": row["author_identity"],
            "rating": row["rating"],
            "title": row["title"],
            "text": row["text"],
            "images": json.loads(row["images_json"]),
            "moderationState": row["moderation_state"],
        }

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM projection_reviews")
            conn.execute("DELETE FROM processed_events")
