import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    GameSessionSchema,
    MoveRequest,
    CreateGameRequest,
    LeaderboardResponseSchema
)
from app.services.game_engine import (
    create_session,
    get_session_snapshot,
    move_session_piece,
    tick_session,
    hold_session_piece
)

logger = logging.getLogger("tetris.endpoints")

STORAGE_UNAVAILABLE_MESSAGE = "Storage service temporarily unavailable. State preserved. Please retry."

# Router for active game sessions
router = APIRouter(prefix="/api/games")

# Separate Router for leaderboards mounted outside the inherited prefix
scores_router = APIRouter(prefix="/api/high-scores")

@router.post(
    "",
    response_model=GameSessionSchema,
    status_code=201,
    responses={500: {"description": "Internal server error"}}
)
def create_game(request: Optional[CreateGameRequest] = None):
    """
    Initializes a new game session.
    Rejects request bodies containing extraneous properties with a 4xx.
    """
    try:
        return create_session()
    except Exception as e:
        logger.exception(f"Unexpected error creating game session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{id}", response_model=GameSessionSchema, responses={404: {"description": "Game not found"}})
def get_game(id: str):
    """
    Thread-safe retrieval of game session state snapshot.
    Does NOT mutate state or trigger any database write/retry.
    """
    session = get_session_snapshot(id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    return session

@router.post("/{id}/tick", response_model=GameSessionSchema, responses={
    404: {"description": "Game not found"},
    503: {"description": "Storage service unavailable"}
})
def tick_game(id: str):
    """
    Ticks the gravity on the game session.
    Triggers DB finalization on game over. Gracefully handles persistence failures with 503.
    """
    session = get_session_snapshot(id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    try:
        return tick_session(id)
    except Exception as e:
        logger.exception(f"Database or execution failure in tick_session for {id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=STORAGE_UNAVAILABLE_MESSAGE
        )

@router.post("/{id}/move", response_model=GameSessionSchema, responses={
    404: {"description": "Game not found"},
    422: {"description": "Validation error"},
    503: {"description": "Storage service unavailable"}
})
def move_game(id: str, request: MoveRequest):
    """
    Moves the active piece on the game session.
    Rejects bodies with extra fields. Gracefully handles persistence failures with 503.
    """
    session = get_session_snapshot(id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    try:
        return move_session_piece(id, request.direction)
    except Exception as e:
        logger.exception(f"Database or execution failure in move_session_piece for {id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=STORAGE_UNAVAILABLE_MESSAGE
        )

@router.post("/{id}/hold", response_model=GameSessionSchema, responses={
    404: {"description": "Game not found"},
    503: {"description": "Storage service unavailable"}
})
def hold_game(id: str):
    """
    Swaps or holds the active piece on the game session.
    Gracefully handles persistence failures with 503.
    """
    session = get_session_snapshot(id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    try:
        return hold_session_piece(id)
    except Exception as e:
        logger.exception(f"Database or execution failure in hold_session_piece for {id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=STORAGE_UNAVAILABLE_MESSAGE
        )

@scores_router.get("", response_model=LeaderboardResponseSchema, responses={
    503: {"description": "Storage service unavailable"}
})
def get_high_scores():
    """
    Retrieves the global leaderboard containing up to 10 sorted entries.
    Gracefully handles database failures with a controlled 503 response.
    """
    try:
        from app.services.database import fetch_leaderboard
        scores = fetch_leaderboard()
        return {"scores": scores}
    except Exception as e:
        logger.exception(f"Failed to fetch leaderboard from SQLite: {e}")
        raise HTTPException(
            status_code=503,
            detail="Leaderboard service temporarily unavailable. Please try again later."
        )
