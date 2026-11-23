"""SQLite-backed high-score persistence (Stage 3, Option A).

A thin wrapper over the Python standard-library ``sqlite3`` module. It stores a
one-row summary (:class:`HighScoreRecord`) per completed game and exposes a
read-only top-ten leaderboard query.

Design invariants (see ``.kiro/specs/tetris-stage3-option-a/design.md``):

- The schema enforces ``UNIQUE(game_id)`` so at most one record exists per game.
- ``finalize`` is an all-or-nothing parameterized ``INSERT ... ON CONFLICT`` that
  returns ``True`` on insert and ``False`` only when the specific ``game_id``
  UNIQUE conflict fires (an idempotent duplicate, not an error). Any other
  failure raises :class:`StorageError` and leaves no partial row.
- Every operation opens a short-lived connection with ``closing(...)`` so the
  connection is always explicitly closed, and wraps the write in ``with conn:``
  so the transaction commits or rolls back.
- ``top_ten`` only issues a ``SELECT`` and never writes.
- Error messages surfaced to clients never contain a filesystem path, SQL text,
  an exception/class name, or a stack trace; the controller maps
  :class:`StorageError` to a single generic message.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass

DEFAULT_DB_PATH = "./data/high-scores.sqlite3"

# Column order used by every INSERT/SELECT in this module.
_COLUMNS = ("game_id", "score", "total_lines", "level", "completed_at")

# Shared internal StorageError text (Sonar python:S1192). Carries no path, SQL,
# exception/class name, or stack trace; the controller maps StorageError to a
# single generic client-facing message independent of this value.
_STORAGE_UNAVAILABLE = "high-score storage is unavailable"


@dataclass(frozen=True)
class HighScoreRecord:
    """An immutable persisted summary of one completed game.

    Exactly the five fields of the Stage 3 ``High_Score_Record`` contract. The
    frozen dataclass guarantees a captured record cannot be mutated between a
    failed finalization attempt and a later successful retry.
    """

    game_id: str
    score: int
    total_lines: int
    level: int
    completed_at: str


class StorageError(Exception):
    """Raised for any storage failure that must surface as a controlled 503.

    Its string representation intentionally carries no sensitive detail (no
    path, SQL, exception/class name, or stack trace) that could be forwarded to
    a client. The controller maps it to a single generic message.
    """


class HighScoreStore:
    """SQLite high-score store using the standard-library ``sqlite3`` module."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @property
    def db_path(self) -> str:
        """Return the resolved SQLite database file path."""

        return self._db_path

    @classmethod
    def from_env(cls) -> "HighScoreStore":
        """Build a store from ``TETRIS_DB_PATH`` (default ``./data/high-scores.sqlite3``).

        An unset or empty/whitespace-only value falls back to the default.
        """

        value = os.environ.get("TETRIS_DB_PATH")
        if value is None or value.strip() == "":
            value = DEFAULT_DB_PATH
        return cls(value)

    def initialize(self) -> None:
        """Create the parent directory (if needed) and the schema (if needed).

        Existing rows are never deleted or reinitialized: ``CREATE TABLE IF NOT
        EXISTS`` leaves a populated table untouched, so opening an existing
        database file reads prior rows as-is.
        """

        parent = os.path.dirname(os.path.abspath(self._db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            with closing(sqlite3.connect(self._db_path)) as conn:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS high_scores (
                            game_id      TEXT    NOT NULL UNIQUE,
                            score        INTEGER NOT NULL,
                            total_lines  INTEGER NOT NULL,
                            level        INTEGER NOT NULL,
                            completed_at TEXT    NOT NULL
                        )
                        """
                    )
        except sqlite3.Error as exc:
            raise StorageError(_STORAGE_UNAVAILABLE) from exc

    def finalize(self, record: HighScoreRecord) -> bool:
        """Persist one record atomically; return True on insert, False on duplicate.

        Uses a single parameterized ``INSERT ... ON CONFLICT(game_id) DO
        NOTHING`` inside one transaction. A zero-row result means the row for
        this ``game_id`` already existed (idempotent duplicate) and returns
        ``False``; it is never reclassified as an error. Any other sqlite
        failure rolls back (no partial row) and raises :class:`StorageError`.
        """

        try:
            with closing(sqlite3.connect(self._db_path)) as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO high_scores
                            (game_id, score, total_lines, level, completed_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(game_id) DO NOTHING
                        """,
                        (
                            record.game_id,
                            record.score,
                            record.total_lines,
                            record.level,
                            record.completed_at,
                        ),
                    )
                    return cursor.rowcount == 1
        except sqlite3.Error as exc:
            raise StorageError(_STORAGE_UNAVAILABLE) from exc

    def top_ten(self) -> list[HighScoreRecord]:
        """Return up to ten records ordered by the leaderboard sort.

        Order: ``score`` DESC, then ``completed_at`` ASC, then ``game_id`` ASC.
        Read-only; never writes. Any sqlite failure raises :class:`StorageError`.
        """

        try:
            with closing(sqlite3.connect(self._db_path)) as conn:
                rows = conn.execute(
                    """
                    SELECT game_id, score, total_lines, level, completed_at
                    FROM high_scores
                    ORDER BY score DESC, completed_at ASC, game_id ASC
                    LIMIT 10
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(_STORAGE_UNAVAILABLE) from exc

        return [
            HighScoreRecord(
                game_id=row[0],
                score=row[1],
                total_lines=row[2],
                level=row[3],
                completed_at=row[4],
            )
            for row in rows
        ]
