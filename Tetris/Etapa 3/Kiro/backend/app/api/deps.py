"""Shared dependency accessors for the API layer (Stage 3, Option A).

Holds the process-wide High_Score_Store instance. ``main.py`` constructs and
initializes the store once on startup (via the FastAPI lifespan handler) and
sets it here; the game and leaderboard controllers read it through
``get_high_score_store``.

Lazy fallback (inherited-test correction): if the lifespan never ran -- for
example when a test uses a module-level ``TestClient(app)`` without a ``with``
block, so Starlette does not run startup -- ``get_high_score_store`` lazily
self-initializes a default store from the environment on first use. This keeps
the store available everywhere without changing any inherited assertion. The
fallback resolves the same ``TETRIS_DB_PATH`` and schema as the lifespan path,
is idempotent, and never clears or reinitializes existing rows.
"""

from __future__ import annotations

import threading
from typing import Optional

from ..persistence.store import HighScoreStore

_high_score_store: Optional[HighScoreStore] = None
_lock = threading.Lock()


def set_high_score_store(store: HighScoreStore) -> None:
    """Install the process-wide High_Score_Store (called once on startup)."""

    global _high_score_store
    with _lock:
        _high_score_store = store


def get_high_score_store() -> HighScoreStore:
    """Return the installed store, lazily creating a default one if needed."""

    global _high_score_store
    if _high_score_store is not None:
        return _high_score_store
    with _lock:
        if _high_score_store is None:
            store = HighScoreStore.from_env()
            store.initialize()
            _high_score_store = store
        return _high_score_store


def reset_high_score_store() -> None:
    """Clear the installed store (used by tests for isolation)."""

    global _high_score_store
    with _lock:
        _high_score_store = None
