import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.game_engine import active_sessions, create_session
from app.models.schemas import TetrominoSchema

client = TestClient(app)

def test_api_create_game():
    active_sessions.clear()
    response = client.post("/api/games")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "board" in data
    assert "activePiece" in data
    assert data["status"] == "playing"
    
    # Verify it exists in active_sessions on backend
    game_id = data["id"]
    assert game_id in active_sessions

def test_api_get_game():
    active_sessions.clear()
    session = create_session()
    response = client.get(f"/api/games/{session.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session.id

def test_api_get_game_not_found():
    response = client.get("/api/games/unknown-id")
    assert response.status_code == 404

def test_api_tick_game():
    active_sessions.clear()
    session = create_session()
    # Force state
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    response = client.post(f"/api/games/{session.id}/tick")
    assert response.status_code == 200
    data = response.json()
    # O piece moved down once, row starts at 0, should now be at 1
    assert data["activePiece"]["origin"] == [1, 4]

def test_api_move_game():
    active_sessions.clear()
    session = create_session()
    # Force state
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    # Move left
    response = client.post(f"/api/games/{session.id}/move", json={"direction": "left"})
    assert response.status_code == 200
    data = response.json()
    assert data["activePiece"]["origin"] == [0, 3]
    
    # Invalid move direction
    response = client.post(f"/api/games/{session.id}/move", json={"direction": "up"})
    assert response.status_code == 422


def test_api_immutable_get():
    active_sessions.clear()
    session = create_session()
    # Ensure next_piece is set
    session.next_piece = "T"
    active_sessions[session.id] = session
    
    for _ in range(3):
        response = client.get(f"/api/games/{session.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["next_piece"] == "T"


def test_api_schema_response_keys():
    active_sessions.clear()
    response = client.post("/api/games")
    assert response.status_code == 201
    data = response.json()
    
    assert "score" in data
    assert "total_lines" in data
    assert "level" in data
    assert "gravity_interval_ms" in data
    assert "next_piece" in data
    assert "hold_piece" in data
    assert "can_hold" in data
    
    assert data["score"] == 0
    assert data["total_lines"] == 0
    assert data["level"] == 1
    assert data["gravity_interval_ms"] == 500
    assert data["next_piece"] in {"I", "O", "T", "S", "Z", "J", "L"}
    assert data["hold_piece"] is None
    assert data["can_hold"] is True
