import uuid
import threading
from typing import Dict, Literal, List, Set, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.game import GameStateModel, ActivePieceModel
from app.domain.pieces import get_random_piece_type, get_relative_cells
from app.domain.rules import tick_game, move_game, hold_game, rotate_game
from app.core.db import save_high_score, get_high_scores

# Separate APIRouters to handle prefixing correctly
router = APIRouter(prefix="/api/games", tags=["games"])
high_scores_router = APIRouter(prefix="/api/high-scores", tags=["high-scores"])

# Thread lock for single-process synchronization
STATE_LOCK = threading.RLock()

# In-memory transient stores
GAMES: Dict[str, GameStateModel] = {}
COMPLETED_AT_STORE: Dict[str, str] = {}
PERSISTED_GAMES: Set[str] = set()

class CreateGamePayload(BaseModel):
    model_config = {"extra": "forbid"}

class MovePayload(BaseModel):
    direction: Literal['left', 'right', 'down']
    model_config = {"extra": "forbid"}

class RotatePayload(BaseModel):
    direction: Literal['cw', 'ccw']
    model_config = {"extra": "forbid"}

# Leaderboard Response Models
class HighScoreEntryModel(BaseModel):
    game_id: str
    score: int
    total_lines: int
    level: int
    completed_at: str

class HighScoresResponseModel(BaseModel):
    scores: List[HighScoreEntryModel]

def finalize_and_save_game_state(state: GameStateModel):
    """
    Serializes and retries saving the game score to the database safely.
    Reuses the original completed_at timestamp if it was already generated.
    """
    game_id = state.id
    if game_id not in COMPLETED_AT_STORE:
        # Generate the original completed_at UTC ISO-8601 string timestamp
        completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        COMPLETED_AT_STORE[game_id] = completed_at
    else:
        completed_at = COMPLETED_AT_STORE[game_id]

    if game_id not in PERSISTED_GAMES:
        save_high_score(
            game_id=game_id,
            score=state.score,
            total_lines=state.total_lines,
            level=state.level,
            completed_at=completed_at
        )
        PERSISTED_GAMES.add(game_id)

@router.post("", response_model=GameStateModel)
def create_game(payload: Optional[CreateGamePayload] = None):
    with STATE_LOCK:
        game_id = str(uuid.uuid4())
        # Initialize an empty 20x10 board
        board = [[None] * 10 for _ in range(20)]
        
        # Spawn first random piece
        piece_type = get_random_piece_type()
        relative_cells = get_relative_cells(piece_type)
        origin = (0, 3)
        
        # Initial position should be legal since board is empty, but calculate standard absolute cells
        cells = [(origin[0] + r, origin[1] + c) for r, c in relative_cells]
        
        active_piece = ActivePieceModel(
            type=piece_type,
            origin=origin,
            cells=cells
        )
        
        # Independently generate random preview next piece
        next_piece = get_random_piece_type()
        
        state = GameStateModel(
            id=game_id,
            board=board,
            active_piece=active_piece,
            status="playing",
            score=0,
            total_lines=0,
            level=1,
            gravity_interval_ms=500,
            next_piece=next_piece,
            hold_piece=None,
            can_hold=True
        )
        
        GAMES[game_id] = state
        return state.model_copy(deep=True)

GAME_NOT_FOUND = "Game session not found"

@router.get("/{id}", response_model=GameStateModel, responses={404: {"description": GAME_NOT_FOUND}})
def get_game(id: str):
    with STATE_LOCK:
        if id not in GAMES:
            raise HTTPException(status_code=404, detail=GAME_NOT_FOUND)
        # GET request is strictly read-only and never triggers database finalization or writes.
        return GAMES[id].model_copy(deep=True)

@router.post("/{id}/tick", response_model=GameStateModel, responses={404: {"description": GAME_NOT_FOUND}})
def tick_game_endpoint(id: str):
    with STATE_LOCK:
        if id not in GAMES:
            raise HTTPException(status_code=404, detail=GAME_NOT_FOUND)
        
        state = GAMES[id]
        if state.status == "game_over":
            # If already game over, attempt database retry safely (preserving original completed_at)
            finalize_and_save_game_state(state)
            return state.model_copy(deep=True)
            
        updated_state = tick_game(state)
        if updated_state.status == "game_over":
            finalize_and_save_game_state(updated_state)
            
        GAMES[id] = updated_state
        return updated_state.model_copy(deep=True)

@router.post("/{id}/move", response_model=GameStateModel, responses={404: {"description": GAME_NOT_FOUND}})
def move_game_endpoint(id: str, payload: MovePayload):
    with STATE_LOCK:
        if id not in GAMES:
            raise HTTPException(status_code=404, detail=GAME_NOT_FOUND)
        
        state = GAMES[id]
        if state.status == "game_over":
            # If already game over, attempt database retry safely (preserving original completed_at)
            finalize_and_save_game_state(state)
            return state.model_copy(deep=True)
            
        updated_state = move_game(state, payload.direction)
        if updated_state.status == "game_over":
            finalize_and_save_game_state(updated_state)
            
        GAMES[id] = updated_state
        return updated_state.model_copy(deep=True)

@router.post("/{id}/hold", response_model=GameStateModel, responses={404: {"description": GAME_NOT_FOUND}})
def hold_game_endpoint(id: str):
    with STATE_LOCK:
        if id not in GAMES:
            raise HTTPException(status_code=404, detail=GAME_NOT_FOUND)
        
        state = GAMES[id]
        if state.status == "game_over":
            # If already game over, attempt database retry safely (preserving original completed_at)
            finalize_and_save_game_state(state)
            return state.model_copy(deep=True)
            
        updated_state = hold_game(state)
        if updated_state.status == "game_over":
            finalize_and_save_game_state(updated_state)
            
        GAMES[id] = updated_state
        return updated_state.model_copy(deep=True)

@router.post("/{id}/rotate", response_model=GameStateModel, responses={404: {"description": GAME_NOT_FOUND}})
def rotate_game_endpoint(id: str, payload: RotatePayload):
    with STATE_LOCK:
        if id not in GAMES:
            raise HTTPException(status_code=404, detail=GAME_NOT_FOUND)
        
        state = GAMES[id]
        if state.status == "game_over":
            # If already game over, attempt database retry safely (preserving original completed_at)
            finalize_and_save_game_state(state)
            return state.model_copy(deep=True)
            
        updated_state = rotate_game(state, payload.direction)
        if updated_state.status == "game_over":
            finalize_and_save_game_state(updated_state)
            
        GAMES[id] = updated_state
        return updated_state.model_copy(deep=True)

@high_scores_router.get("", response_model=HighScoresResponseModel)
def get_high_scores_endpoint():
    # Leaderboard read does not mutate any game state or create rows
    scores = get_high_scores()
    return HighScoresResponseModel(scores=scores)
