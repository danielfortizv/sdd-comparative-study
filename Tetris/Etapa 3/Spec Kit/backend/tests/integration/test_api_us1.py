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


def test_api_gravity_game_over_finalization():
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
            
    # Set score and lines
    session.score = 500
    session.total_lines = 10
    session.level = 2
    session.next_piece = "O"
    active_sessions[session.id] = session
    
    # Tick should cause collision, set status to game_over, and trigger finalization
    response = client.post(f"/api/games/{session.id}/tick")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "game_over"
    
    # Query SQLite database to verify the record was written correctly
    from app.services.database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM high_scores WHERE game_id = ?", (session.id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["score"] == 500
        assert row["total_lines"] == 10
        assert row["level"] == 2
        assert "completed_at" in row.keys()
    finally:
        conn.close()


def test_api_obstructed_hold_finalization():
    active_sessions.clear()
    session = create_session()
    
    # Block spawn zone at the top
    session.board[0][4] = 1
            
    session.hold_piece = "O"
    session.score = 300
    session.total_lines = 3
    session.level = 1
    active_sessions[session.id] = session
    
    # Hold should cause overlap collision and trigger finalization
    response = client.post(f"/api/games/{session.id}/hold")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "game_over"
    
    # Verify DB entry
    from app.services.database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM high_scores WHERE game_id = ?", (session.id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["score"] == 300
        assert row["total_lines"] == 3
        assert row["level"] == 1
    finally:
        conn.close()


def test_api_restart_or_abandon_does_not_persist():
    active_sessions.clear()
    session = create_session()
    
    # Play some game without hitting game over
    response = client.get(f"/api/games/{session.id}")
    assert response.status_code == 200
    
    # Abandon the game (create a new game instead of completing)
    response_new = client.post("/api/games")
    assert response_new.status_code == 201
    
    # DB should have NO records for either since they haven't ended in game_over
    from app.services.database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM high_scores")
        row = cursor.fetchone()
        assert row["count"] == 0
    finally:
        conn.close()


def test_api_idempotent_finalization_and_concurrency():
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
    session.score = 800
    session.next_piece = "O"
    active_sessions[session.id] = session
    
    # Fire multiple concurrent/sequential ticks (terminal actions)
    # First tick triggers finalization
    response1 = client.post(f"/api/games/{session.id}/tick")
    assert response1.status_code == 200
    
    # Get original completed_at timestamp
    from app.services.database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT completed_at FROM high_scores WHERE game_id = ?", (session.id,))
        row1 = cursor.fetchone()
        assert row1 is not None
        orig_timestamp = row1["completed_at"]
    finally:
        conn.close()
        
    # Second tick is a repeat terminal action (should be idempotent no-op on DB write)
    response2 = client.post(f"/api/games/{session.id}/tick")
    assert response2.status_code == 200
    
    # Check that record is still singular and has the EXACT same timestamp
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count, completed_at FROM high_scores WHERE game_id = ?", (session.id,))
        row2 = cursor.fetchone()
        assert row2["count"] == 1
        assert row2["completed_at"] == orig_timestamp
    finally:
        conn.close()

