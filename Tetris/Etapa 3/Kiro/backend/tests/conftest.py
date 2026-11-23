"""Shared pytest fixtures for the backend test suite.

Keeps the High_Score_Store database out of the source tree by pointing
``TETRIS_DB_PATH`` at a fresh per-test temporary file, and resets the in-memory
game store and the shared store accessor between tests so cases stay isolated.
This support file adds fixtures only; it changes no inherited assertion.
"""

from __future__ import annotations

import os

import pytest

from app import store as game_store


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path):
    """Give each test a fresh temp DB path and a clean in-memory + store state."""

    os.environ["TETRIS_DB_PATH"] = str(tmp_path / "high-scores.sqlite3")
    game_store.reset()
    try:
        from app.api import deps

        deps.reset_high_score_store()
    except Exception:
        pass

    yield

    game_store.reset()
    try:
        from app.api import deps

        deps.reset_high_score_store()
    except Exception:
        pass
    os.environ.pop("TETRIS_DB_PATH", None)
