"""HTTP controllers for game endpoints.

The controllers translate requests into pure rule calls and serialize the
resulting domain state. They contain no game logic themselves.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import store
from ..rules import engine
from .schemas import GameStateOut, MoveRequest, serialize

router = APIRouter(prefix="/api/games", tags=["games"])


def _get_or_404(game_id: str):
    """Return the game or raise HTTP 404 if it does not exist."""

    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("", response_model=GameStateOut)
def create_game() -> GameStateOut:
    """Create or restart a game and return its initial state."""

    game = store.create()
    return serialize(game)


@router.get("/{game_id}", response_model=GameStateOut)
def read_game(game_id: str) -> GameStateOut:
    """Return the current state of an existing game."""

    game = _get_or_404(game_id)
    return serialize(game)


@router.post("/{game_id}/tick", response_model=GameStateOut)
def tick_game(game_id: str) -> GameStateOut:
    """Advance one gravity tick and return the updated state."""

    game = _get_or_404(game_id)
    engine.tick(game)
    return serialize(game)


@router.post("/{game_id}/move", response_model=GameStateOut)
def move_game(game_id: str, body: MoveRequest) -> GameStateOut:
    """Apply a player move and return the updated state."""

    game = _get_or_404(game_id)
    engine.move(game, body.direction)
    return serialize(game)
