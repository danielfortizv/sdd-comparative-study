import pytest
from app.services.game_engine import (
    create_session,
    tick_session,
    move_session_piece,
    active_sessions
)
from app.models.schemas import TetrominoSchema

def test_game_over_on_spawn_overlap():
    active_sessions.clear()
    session = create_session()
    
    # Force settled blocks at the spawn location (rows 0 and 1, cols 3-6)
    for c in range(3, 7):
        session.board[0][c] = 2
        session.board[1][c] = 2
        
    # Set the active piece resting on the bottom so that on next tick, it will lock and trigger spawning next piece
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    active_sessions[session.id] = session
    
    # Tick to lock. The engine tries to spawn a new piece, but it collides immediately with the settled blocks we placed at the top.
    updated = tick_session(session.id)
    
    assert updated.status == "game_over"
    assert updated.active_piece is None

def test_game_over_ignores_moves_and_ticks():
    active_sessions.clear()
    session = create_session()
    session.status = "game_over"
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    # Any movement commands should be ignored and leave board/piece identical
    updated = move_session_piece(session.id, "left")
    assert updated.active_piece.origin == [0, 4]
    
    # Any gravity ticks should be ignored and leave state identical
    updated = tick_session(session.id)
    assert updated.active_piece.origin == [0, 4]
