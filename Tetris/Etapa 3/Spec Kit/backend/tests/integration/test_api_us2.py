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


def test_api_extra_fields_rejection():
    # Extra field on game creation body (POST /api/games)
    response = client.post("/api/games", json={"score": 999})
    assert response.status_code == 422 # 422 Unprocessable Entity due to extra forbidden field

    active_sessions.clear()
    session = create_session()
    
    # Extra field on move body
    response = client.post(f"/api/games/{session.id}/move", json={"direction": "left", "hacker_score": 100000})
    assert response.status_code == 422 # Rejected with 422

    # Unknown game ID returns 404
    response = client.post("/api/games/unknown-uuid/move", json={"direction": "left"})
    assert response.status_code == 404


def test_api_controlled_503_on_database_failure():
    active_sessions.clear()
    session = create_session()
    
    # Position active piece low so it collides with bottom on next tick
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    # Block spawn zone at the top
    session.board[0][4] = 1
    session.score = 600
    session.next_piece = "O"
    active_sessions[session.id] = session
    
    from unittest.mock import patch
    import sqlite3
    
    # Patch database insert to raise an exception simulating storage/lock failure
    with patch("app.services.database.insert_high_score", side_effect=sqlite3.DatabaseError("SQLITE_BUSY: database is locked")):
        response = client.post(f"/api/games/{session.id}/tick")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        # Ensure no SQL, file paths, or traceback is leaked
        assert "SQLITE" not in data["detail"]
        assert "high-scores.sqlite3" not in data["detail"]
        
    # Verify that in-memory is_persisted is False, and subsequent mutating request retries and succeeds!
    # A subsequent GET never performs retry
    response_get = client.get(f"/api/games/{session.id}")
    assert response_get.status_code == 200
    
    # Verify DB still doesn't have the record
    from app.services.database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM high_scores WHERE game_id = ?", (session.id,))
        assert cursor.fetchone()["count"] == 0
    finally:
        conn.close()
        
    # Subsequent mutating action (e.g. tick) retries persistence and succeeds!
    response_retry = client.post(f"/api/games/{session.id}/tick")
    assert response_retry.status_code == 200
    
    # Now it should be successfully saved in the DB
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM high_scores WHERE game_id = ?", (session.id,))
        assert cursor.fetchone()["count"] == 1
    finally:
        conn.close()


def test_api_get_high_scores_leaderboard():
    from app.services.database import insert_high_score
    # Insert multiple scores
    insert_high_score("game-lead-1", 100, 1, 1, "2026-10-29T12:00:00Z")
    insert_high_score("game-lead-2", 300, 3, 1, "2026-10-29T12:00:00Z")
    insert_high_score("game-lead-3", 200, 2, 1, "2026-10-29T12:00:00Z")
    
    response = client.get("/api/high-scores")
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    scores = data["scores"]
    assert len(scores) == 3
    # Check ordering: highest score (300) first, then 200, then 100
    assert scores[0]["game_id"] == "game-lead-2"
    assert scores[0]["score"] == 300
    assert scores[1]["game_id"] == "game-lead-3"
    assert scores[1]["score"] == 200
    assert scores[2]["game_id"] == "game-lead-1"
    assert scores[2]["score"] == 100


def test_api_get_high_scores_controlled_503_error():
    from unittest.mock import patch
    import sqlite3
    
    # Simulate DB error during select
    with patch("app.services.database.fetch_leaderboard", side_effect=sqlite3.OperationalError("cannot open database file")):
        response = client.get("/api/high-scores")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "cannot open" not in data["detail"]


