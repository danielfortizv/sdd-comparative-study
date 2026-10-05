import uuid
from typing import Dict, Optional, Literal
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import GameState, MoveRequest, ErrorResponse
from app.rules import init_new_game, move_piece, process_gravity_tick

app = FastAPI(
    title="Tetris Study API",
    description="Authoritative game state backend for Tetris Stage 1 Option A",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage of game sessions
games: Dict[str, GameState] = {}

@app.post(
    "/api/games",
    response_model=GameState,
    status_code=status.HTTP_201_CREATED,
    summary="Create or restart a game session"
)
def create_game(test_piece: Optional[str] = None):
    """
    Creates a new game session with a unique UUID.
    If 'test_piece' is provided, the first spawned piece will be forced to that type.
    """
    game_id = str(uuid.uuid4())
    state = init_new_game(game_id, fixed_first_piece=test_piece)
    games[game_id] = state
    return state

@app.get(
    "/api/games/{game_id}",
    response_model=GameState,
    summary="Get current game state"
)
def get_game(game_id: str):
    """
    Retrieves the current state of an active game session.
    Throws a 404 error if the session ID is invalid.
    """
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game session {game_id} not found"
        )
    return games[game_id]

@app.post(
    "/api/games/{game_id}/tick",
    response_model=GameState,
    summary="Advance game state by one gravity tick"
)
def tick_game(game_id: str, test_next_piece: Optional[str] = None):
    """
    Advances gravity by one row. If the piece locks, a new one is spawned.
    If 'test_next_piece' is provided, the subsequent spawned piece will be forced to that type.
    Throws 404 if the session ID is invalid.
    """
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game session {game_id} not found"
        )
    
    state = games[game_id]
    updated_state = process_gravity_tick(state, fixed_next_piece=test_next_piece)
    games[game_id] = updated_state
    return updated_state

@app.post(
    "/api/games/{game_id}/move",
    response_model=GameState,
    summary="Move the active piece"
)
def move_game_piece(game_id: str, request: MoveRequest):
    """
    Shifts the active falling tetromino left, right, or down by 1 cell.
    If the requested move results in a collision, the command is ignored and state remains unchanged.
    Throws 404 if the session ID is invalid.
    """
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game session {game_id} not found"
        )
    
    state = games[game_id]
    updated_state = move_piece(state, request.direction)
    games[game_id] = updated_state
    return updated_state
