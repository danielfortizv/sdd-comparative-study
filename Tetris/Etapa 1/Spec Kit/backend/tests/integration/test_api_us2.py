import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.game_engine import active_sessions, create_session
from app.models.schemas import TetrominoSchema

client = TestClient(app)

def test_api_line_clear_integration():
    active_sessions.clear()
    session = create_session()
    
    # Fill row 19 except column 0
    session.board[19] = [0] + [2] * 9
    
    # Active piece has a cell that will land on row 19, column 0 on tick
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[18, 0], [18, 1], [18, 2], [19, 0]],
        origin=[18, 0]
    )
    active_sessions[session.id] = session
    
    # Advance gravity tick -> piece collides (since shifting down puts row 19 cell to row 20)
    # Piece locks -> row 19 is now completely filled -> row 19 clears -> row 18 shifts to row 19
    response = client.post(f"/api/games/{session.id}/tick")
    assert response.status_code == 200
    data = response.json()
    
    # Row 19 should now be what row 18 was after lock: [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert data["board"][19][0] == 1
    assert data["board"][19][1] == 1
    assert data["board"][19][2] == 1
    assert data["board"][19][3] == 0
