"""Finalization service: finalize a completed game at most once.

Finalization is wired at the controller/service boundary, NOT inside the pure
engine, so ``app/rules/engine.py`` stays framework- and I/O-free.

Locking model (single in-memory game worker):

- ``_LOCK`` is a module-level NON-REENTRANT ``threading.Lock``. It is the one
  consistent boundary that serializes mutation, finalization, AND response
  serialization for a request.
- The CONTROLLER acquires ``_LOCK`` exactly ONCE per request and holds it across
  the mutation, the finalization, and the response serialization.
- ``run_mutation`` and ``_finalize_if_needed`` assume the caller already holds
  the lock and MUST NOT acquire it again. Re-acquiring a non-reentrant Lock on
  the same thread would deadlock.

Write-once completion time:

- On the FIRST terminal transition only, ``completed_at`` is generated once
  (terminal time) and an immutable frozen ``HighScoreRecord`` is captured into
  ``game.finalization_record`` BEFORE any storage write is attempted.
- Every attempt and every retry reuses that SAME captured record, so a storage
  failure followed by a later successful retry persists the original
  ``completed_at`` and never re-mutates the terminal game.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable

from ..domain.models import Game
from ..persistence.store import HighScoreRecord, HighScoreStore, StorageError

# Non-reentrant lock; single in-memory game worker (Req 3.5, 4.5, 12.4).
# Acquired ONCE per request by the controller; the functions below never
# re-acquire it.
_LOCK = threading.Lock()


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(timezone.utc).isoformat()


def run_mutation(game: Game, mutate: Callable[[Game], None], store: HighScoreStore) -> None:
    """Run a pure engine mutation and finalize if the game is now terminal.

    Precondition: the caller already holds ``_LOCK``. This function does NOT
    acquire ``_LOCK``.
    """

    mutate(game)
    if game.status == "game_over":
        _finalize_if_needed(game, store)


def _finalize_if_needed(game: Game, store: HighScoreStore) -> None:
    """Persist the completed game's record exactly once; retry safely.

    Precondition: the caller already holds ``_LOCK``. This function does NOT
    acquire ``_LOCK``.

    On a non-duplicate storage failure, ``store.finalize`` raises
    :class:`StorageError`; this function marks the game pending, leaves the
    captured record and ``completed_at`` unchanged, preserves the terminal
    state, and re-raises so the controller returns a 503.
    """

    if game.finalized:
        return

    # (1) Capture the immutable pending record ONCE, at the first terminal
    #     transition, BEFORE any storage write. completed_at is generated here
    #     (terminal time) and never regenerated on retry.
    if game.finalization_record is None:
        game.completed_at = _utc_now_iso()
        game.finalization_record = HighScoreRecord(
            game_id=game.id,
            score=game.score,
            total_lines=game.total_lines,
            level=game.level,
            completed_at=game.completed_at,
        )

    record = game.finalization_record  # reuse the SAME record on every retry

    # (2) Attempt the write. A StorageError propagates to the controller; the
    #     captured record and terminal state are left intact for a later retry.
    try:
        store.finalize(record)
    except StorageError:
        game.pending_finalization = True
        raise

    # (3) On insert OR idempotent duplicate, mark finalized and clear pending.
    game.finalized = True
    game.pending_finalization = False
