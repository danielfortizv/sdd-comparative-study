import uuid
from typing import Dict, Literal
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.domain import (
    GameState,
    create_new_game,
    move_piece,
    tick_game
)

app = FastAPI(title="Stage 1 Tetris Study API", version="1.0.0")

# CORS setup for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ephemeral in-memory sessions mapping UUID -> GameState
sessions: Dict[str, GameState] = {}

class MoveRequest(BaseModel):
    direction: Literal["left", "right", "down"]

@app.post("/api/games", status_code=status.HTTP_201_CREATED, response_model=GameState)
def create_game():
    """Initializes a brand new game session in memory and spawns the first piece."""
    game_id = str(uuid.uuid4())
    state = create_new_game(game_id)
    sessions[game_id] = state
    return state

@app.get("/api/games/{id}", response_model=GameState)
def get_game(id: str):
    """Retrieves the current game state of the given game session ID."""
    if id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found"
        )
    return sessions[id]

@app.post("/api/games/{id}/tick", response_model=GameState)
def tick_game_session(id: str):
    """Advances the game state by one gravity tick."""
    if id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found"
        )
    
    current_state = sessions[id]
    new_state = tick_game(current_state)
    sessions[id] = new_state
    return new_state

@app.post("/api/games/{id}/move", response_model=GameState)
def move_game_session(id: str, request: MoveRequest):
    """Performs a manual shift in the specified direction if legal."""
    if id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found"
        )
    
    current_state = sessions[id]
    new_state = move_piece(current_state, request.direction)
    sessions[id] = new_state
    return new_state
