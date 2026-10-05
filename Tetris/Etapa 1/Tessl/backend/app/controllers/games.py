import uuid
from typing import Dict, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.game import GameStateModel, ActivePieceModel
from app.domain.pieces import get_random_piece_type, get_relative_cells
from app.domain.rules import is_legal_position, tick_game, move_game

router = APIRouter(prefix="/api/games", tags=["games"])

# In-memory store
GAMES: Dict[str, GameStateModel] = {}

class MovePayload(BaseModel):
    direction: Literal['left', 'right', 'down']

@router.post("", response_model=GameStateModel)
def create_game():
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
    
    state = GameStateModel(
        id=game_id,
        board=board,
        active_piece=active_piece,
        status="playing"
    )
    
    GAMES[game_id] = state
    return state

@router.get("/{id}", response_model=GameStateModel)
def get_game(id: str):
    if id not in GAMES:
        raise HTTPException(status_code=404, detail="Game session not found")
    return GAMES[id]

@router.post("/{id}/tick", response_model=GameStateModel)
def tick_game_endpoint(id: str):
    if id not in GAMES:
        raise HTTPException(status_code=404, detail="Game session not found")
    state = GAMES[id]
    updated_state = tick_game(state)
    GAMES[id] = updated_state
    return updated_state

@router.post("/{id}/move", response_model=GameStateModel)
def move_game_endpoint(id: str, payload: MovePayload):
    if id not in GAMES:
        raise HTTPException(status_code=404, detail="Game session not found")
    state = GAMES[id]
    updated_state = move_game(state, payload.direction)
    GAMES[id] = updated_state
    return updated_state
