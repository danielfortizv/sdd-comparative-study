import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.game_engine import active_sessions, create_session
from app.models.schemas import TetrominoSchema

client = TestClient(app)

def test_api_line_clear_integration():
    active_sessions.clear()
    session = create_session()
    
    # Pre-existing blocks on row 18 (so they will shift down to row 19 on clear)
    session.board[18] = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    
    # Fill row 19 except columns 3, 4, 5, 6 (where the horizontal I piece will land)
    session.board[19] = [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
    
    # Active piece is a real horizontal I piece at row 19
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    active_sessions[session.id] = session
    
    # Advance gravity tick -> piece collides (since shifting down puts row 19 cells to row 20)
    # Piece locks -> row 19 is now completely filled -> row 19 clears -> row 18 shifts to row 19
    response = client.post(f"/api/games/{session.id}/tick")
    assert response.status_code == 200
    data = response.json()
    
    # Row 19 should now be what row 18 was before clear: [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert data["board"][19][0] == 1
    assert data["board"][19][1] == 1
    assert data["board"][19][2] == 1
    assert data["board"][19][3] == 0


def test_api_hold_endpoint_success():
    active_sessions.clear()
    session = create_session()
    session.next_piece = "O"
    session.can_hold = True
    session.hold_piece = None
    active_sessions[session.id] = session
    
    initial_active_type = session.active_piece.type
    
    response = client.post(f"/api/games/{session.id}/hold")
    assert response.status_code == 200
    data = response.json()
    assert data["hold_piece"] == initial_active_type
    assert data["activePiece"]["type"] == "O"
    assert data["can_hold"] is False


def test_api_hold_endpoint_not_found():
    response = client.post("/api/games/nonexistent-id/hold")
    assert response.status_code == 404


def test_api_hold_endpoint_rejected():
    active_sessions.clear()
    session = create_session()
    session.can_hold = False
    session.hold_piece = "I"
    active_sessions[session.id] = session
    
    initial_active_type = session.active_piece.type
    
    response = client.post(f"/api/games/{session.id}/hold")
    assert response.status_code == 200
    data = response.json()
    # State remains unmodified because hold is rejected
    assert data["hold_piece"] == "I"
    assert data["activePiece"]["type"] == initial_active_type
    assert data["can_hold"] is False
