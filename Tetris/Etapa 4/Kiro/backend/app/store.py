"""In-memory game repository.

State exists only for the lifetime of the process; there is no database.
"""

from __future__ import annotations

import uuid
from typing import Dict, Optional

from .domain.models import Game
from .rules import engine

# Fixed default seed keeps the piece sequence reproducible across runs.
DEFAULT_SEED = 20260929

_games: Dict[str, Game] = {}


def create(seed: int = DEFAULT_SEED) -> Game:
    """Create and store a new game, returning it."""

    game_id = uuid.uuid4().hex
    game = engine.new_game(game_id, seed)
    _games[game.id] = game
    return game


def get(game_id: str) -> Optional[Game]:
    """Return the stored game for an id, or None if it does not exist."""

    return _games.get(game_id)


def reset() -> None:
    """Remove all stored games (used by tests)."""

    _games.clear()
