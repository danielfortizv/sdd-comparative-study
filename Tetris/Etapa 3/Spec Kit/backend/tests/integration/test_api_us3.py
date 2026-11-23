import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.game_engine import active_sessions, create_session
from app.models.schemas import TetrominoSchema

client = TestClient(app)

def test_api_game_over_ignores_operations():
    active_sessions.clear()
    session = create_session()
    session.status = "game_over"
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    # Try to move left -> state should not change (retains origin [0, 4])
    res = client.post(f"/api/games/{session.id}/move", json={"direction": "left"})
    assert res.status_code == 200
    assert res.json()["activePiece"]["origin"] == [0, 4]
    
    # Try to tick -> state should not change (retains origin [0, 4])
    res = client.post(f"/api/games/{session.id}/tick")
    assert res.status_code == 200
    assert res.json()["activePiece"]["origin"] == [0, 4]

def test_api_restart_creates_fresh_session():
    active_sessions.clear()
    session = create_session()
    session.status = "game_over"
    session.board[10][5] = 5
    active_sessions[session.id] = session
    
    # Restart by creating a new session -> POST /api/games
    # Since in-memory state contains the session, starting a game creates a new UUID or resets
    response = client.post("/api/games")
    assert response.status_code == 201
    data = response.json()
    
    new_id = data["id"]
    assert new_id != session.id
    assert data["status"] == "playing"
    assert data["board"][10][5] == 0  # Should be empty board
