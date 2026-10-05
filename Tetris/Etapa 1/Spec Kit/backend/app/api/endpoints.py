from fastapi import APIRouter, HTTPException
from app.models.schemas import GameSessionSchema, MoveRequest
from app.services.game_engine import (
    active_sessions,
    create_session,
    move_session_piece,
    tick_session
)

router = APIRouter(prefix="/api/games")

@router.post("", response_model=GameSessionSchema, status_code=201)
def create_game():
    return create_session()

@router.get("/{id}", response_model=GameSessionSchema)
def get_game(id: str):
    if id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    return active_sessions[id]

@router.post("/{id}/tick", response_model=GameSessionSchema)
def tick_game(id: str):
    if id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    return tick_session(id)

@router.post("/{id}/move", response_model=GameSessionSchema)
def move_game(id: str, request: MoveRequest):
    if id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Game session {id} not found")
    return move_session_piece(id, request.direction)
