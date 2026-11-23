"""HTTP controllers for game endpoints.

The controllers translate requests into pure rule calls and serialize the
resulting domain state. Game logic lives in the pure engine; the Stage 3
finalization side effect lives in the finalization service.

Single-boundary locking (Stage 3): each mutating request acquires the
finalization service lock exactly ONCE and holds it across the mutation, the
finalization, AND the response serialization, so the serialized response is a
coherent immutable snapshot. The read endpoint takes the same lock once and
serializes a read-only snapshot without mutating or finalizing.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import store
from ..rules import engine
from ..service import finalization
from ..persistence.store import StorageError
from .deps import get_high_score_store
from .errors import STORAGE_UNAVAILABLE_MESSAGE
from .schemas import CreateGameRequest, GameStateOut, MoveRequest, serialize

router = APIRouter(prefix="/api/games", tags=["games"])

# Documents the controlled 503 that each MUTATING route can return when
# finalization hits a storage failure (Sonar python:S8415). Documentation-only:
# it does not change behavior or the response body.
_STORAGE_503_RESPONSES = {
    503: {"description": "High-score storage is temporarily unavailable."}
}


def _get_or_404(game_id: str):
    """Return the game or raise HTTP 404 if it does not exist."""

    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("", response_model=GameStateOut)
def create_game(body: Optional[CreateGameRequest] = None) -> GameStateOut:
    """Create or restart a game and return its initial state.

    A bodyless request is valid and returns HTTP 200 (Req 6.4). A supplied body
    is validated with ``extra="forbid"``, rejecting any client-supplied score
    metadata or arbitrary game id (Req 6.2).
    """

    game = store.create()
    return serialize(game)


@router.get("/{game_id}", response_model=GameStateOut)
def read_game(game_id: str) -> GameStateOut:
    """Return the current state of an existing game.

    Takes the shared lock once and serializes a coherent read-only snapshot. A
    GET never mutates state, never finalizes, and never retries a pending
    finalization (Req 3.3, 7.9).
    """

    with finalization._LOCK:
        game = _get_or_404(game_id)
        return serialize(game)


def _mutate(game_id: str, mutate) -> GameStateOut:
    """Run a mutation under the single lock, finalize if terminal, serialize."""

    with finalization._LOCK:
        game = _get_or_404(game_id)
        try:
            finalization.run_mutation(game, mutate, get_high_score_store())
        except StorageError:
            raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_MESSAGE)
        return serialize(game)


@router.post("/{game_id}/tick", responses=_STORAGE_503_RESPONSES)
def tick_game(game_id: str) -> GameStateOut:
    """Advance one gravity tick and return the updated state."""

    return _mutate(game_id, engine.tick)


@router.post("/{game_id}/move", responses=_STORAGE_503_RESPONSES)
def move_game(game_id: str, body: MoveRequest) -> GameStateOut:
    """Apply a player move and return the updated state."""

    return _mutate(game_id, lambda g: engine.move(g, body.direction))


@router.post("/{game_id}/hold", responses=_STORAGE_503_RESPONSES)
def hold_game(game_id: str) -> GameStateOut:
    """Hold or swap the active piece and return the updated state."""

    return _mutate(game_id, engine.hold)
