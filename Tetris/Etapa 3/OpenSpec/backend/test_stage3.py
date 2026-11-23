import os
import sqlite3
import shutil
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app, manager, try_finalize_session
from backend.database import get_db_path, init_db, save_high_score, get_high_scores
from backend.models import MoveRequest, GameCreateRequest, ActivePiece
from backend.engine import GameSession, TetrisEngine

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """Sets up a clean, isolated temporary test database environment for each test (TEST-ISOLATION-01)."""
    db_file = tmp_path / "test-high-scores.sqlite3"
    db_path_str = str(db_file)
    monkeypatch.setenv("TETRIS_DB_PATH", db_path_str)
    
    # Initialize fresh DB
    init_db()

client = TestClient(app)

# =====================================================================
# REQ-045: SQLite Schema Initialization and Reload Persistence
# =====================================================================

def test_db_schema_initialization():
    """Verify that init_db creates parent folder and correct tables/indices."""
    db_path = get_db_path()
    assert os.path.exists(db_path), "Database file must be created"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='high_scores';")
    assert cursor.fetchone() is not None, "high_scores table must exist"
    
    # Verify index
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_high_scores_score_completed';")
    assert cursor.fetchone() is not None, "Index idx_high_scores_score_completed must exist"
    conn.close()

def test_db_reload_persistence(monkeypatch):
    """Verify high scores survive app/store reloads when opening same DB file."""
    # Write some scores
    save_high_score("game-1", 1500, 10, 2, "2026-10-28T12:00:00Z")
    save_high_score("game-2", 3000, 20, 3, "2026-10-28T12:05:00Z")
    
    # Simulate reload by initializing database again
    init_db()
    
    # Verify scores are preserved
    scores = get_high_scores()
    assert len(scores) == 2
    assert scores[0]["game_id"] == "game-2"
    assert scores[0]["score"] == 3000
    assert scores[1]["game_id"] == "game-1"
    assert scores[1]["score"] == 1500


# =====================================================================
# REQ-046 & REQ-057: Persistent High Score Recording & Immutability
# =====================================================================

def test_persistent_recording_on_game_over():
    """Verify that natural game over (e.g. from tick/move) persists score exactly once."""
    session = manager.create_session()
    session.score = 5000
    session.total_lines = 45
    session.level = 5
    
    # Transition session to game_over status
    session.status = "game_over"
    
    # Trigger finalization
    try_finalize_session(session)
    assert session.finalized is True
    
    # Check score was written to DB
    scores = get_high_scores()
    assert len(scores) == 1
    assert scores[0]["game_id"] == session.id
    assert scores[0]["score"] == 5000
    assert scores[0]["total_lines"] == 45
    assert scores[0]["level"] == 5
    
    # Attempt second finalization (must be rejected/ignored, leaving original immutable)
    orig_completed_at = scores[0]["completed_at"]
    try_finalize_session(session)
    
    scores_after = get_high_scores()
    assert len(scores_after) == 1
    assert scores_after[0]["completed_at"] == orig_completed_at


def test_exclude_restarted_and_abandoned_games():
    """Verify active or restarted sessions do not write scores."""
    session = manager.create_session()
    session.score = 1200
    session.status = "playing"
    
    # We do NOT finalize it. Let's restart (generate a new game)
    new_session = manager.create_session()
    
    # DB must remain empty since neither session naturally reached terminal game_over and finalized
    assert len(get_high_scores()) == 0


def test_hold_spawn_collision_first_and_occupied_obstruction_paths():
    """Verify both first-Hold empty-slot and occupied-Hold spawn collisions trigger game-over and persistence (TEST-FIXTURE-02)."""
    # Scenario A: first-time Hold empty-slot collision
    session_a = manager.create_session()
    session_a.active_piece = ActivePiece(
        type="O",
        origin=[17, 0],
        cells=[[18, 1], [18, 2], [19, 1], [19, 2]]
    )
    session_a.board[1][4] = "I"  # Obstruction at S spawning cell
    # Spawn S piece as next
    session_a.next_piece = "S"
    
    # Trigger hold
    assert session_a.hold() is True
    assert session_a.status == "game_over"
    
    try_finalize_session(session_a)
    assert len(get_high_scores()) == 1
    assert get_high_scores()[0]["game_id"] == session_a.id

    # Scenario B: occupied Hold swap collision
    session_b = manager.create_session()
    session_b.active_piece = ActivePiece(
        type="O",
        origin=[17, 0],
        cells=[[18, 1], [18, 2], [19, 1], [19, 2]]
    )
    session_b.board[1][4] = "I"  # settled block obstructing held T spawn shape
    session_b.hold_piece = "T"
    
    assert session_b.hold() is True
    assert session_b.status == "game_over"
    
    try_finalize_session(session_b)
    # Total scores in DB should now be 2
    assert len(get_high_scores()) == 2


# =====================================================================
# REQ-047: Leaderboard Retrieval, Truncation, and Tie-Breakers
# =====================================================================

def test_leaderboard_sorting_and_truncation():
    """Verify sorting (score DESC, completed_at ASC, game_id ASC) and max 10 scores."""
    # Write 12 scores with ties
    # Ties in score, chronological ordering
    save_high_score("g1", 1000, 10, 1, "2026-10-28T12:00:00Z")
    save_high_score("g2", 1000, 10, 1, "2026-10-28T12:00:00Z")  # Tie in score & time, lexicographical tie break (g1 < g2)
    save_high_score("g3", 1000, 10, 1, "2026-10-28T11:59:00Z")  # Earliest score 1000
    save_high_score("g4", 1200, 12, 2, "2026-10-28T12:05:00Z")  # Highest score
    
    # Add 8 more low scores to verify truncation (total 12 entries)
    for i in range(5, 13):
        save_high_score(f"g{i}", 100, 2, 1, f"2026-10-28T12:10:0{i}Z")
        
    response = client.get("/api/high-scores")
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    scores = data["scores"]
    assert len(scores) == 10, "Leaderboard must truncate at exactly 10 scores"
    
    # Assert correct ordering
    assert scores[0]["game_id"] == "g4"  # Highest score 1200
    assert scores[1]["game_id"] == "g3"  # Score 1000, earliest (11:59:00)
    assert scores[2]["game_id"] == "g1"  # Score 1000, second (12:00:00), game_id lexicographically before g2
    assert scores[3]["game_id"] == "g2"  # Score 1000, third (12:00:00)
    
    # Ensure exact 5 schema fields are returned
    for score in scores:
        assert set(score.keys()) == {"game_id", "score", "total_lines", "level", "completed_at"}


# =====================================================================
# REQ-048 & REQ-049: Database Failures (503) & Finalization Retry
# =====================================================================

def test_database_failure_returns_sanitized_503(monkeypatch):
    """Verify database errors return controlled 503 without leaking stack traces or file paths."""
    # Break database path or mock get_high_scores to throw sqlite3.Error
    def mock_get_high_scores():
        raise sqlite3.OperationalError("Mock database lock error")
    
    monkeypatch.setattr("backend.main.get_high_scores", mock_get_get_high_scores := mock_get_high_scores)
    
    response = client.get("/api/high-scores")
    assert response.status_code == 503
    assert response.json() == {"detail": "Storage service unavailable"}


def test_finalization_retry_behavior_on_mutating_request(monkeypatch):
    """Verify mutating request retries persistence if it previously failed, while GET does not."""
    session = manager.create_session()
    session.status = "game_over"
    session.score = 999
    session.finalized = False
    
    # 1. Mock DB write failure
    write_failed = True
    def mock_save_high_score(*args, **kwargs):
        nonlocal write_failed
        if write_failed:
            raise sqlite3.OperationalError("Database locked!")
        # On retry, succeed!
        # Do standard database save
        save_high_score(*args, **kwargs)
        
    monkeypatch.setattr("backend.main.save_high_score", mock_save_high_score)
    
    # Get game must NOT retry (GET is idempotent, doesn't call try_finalize_session)
    response_get = client.get(f"/api/games/{session.id}")
    assert response_get.status_code == 200
    assert len(get_high_scores()) == 0
    assert session.finalized is False
    
    # Mutating request (POST tick) will attempt finalization and fail with 503
    response_tick = client.post(f"/api/games/{session.id}/tick")
    assert response_tick.status_code == 503
    assert response_tick.json() == {"detail": "Storage service unavailable"}
    assert session.finalized is False
    
    # Now simulate DB becoming healthy
    write_failed = False
    
    # Subsequent mutating request retries and succeeds!
    response_move = client.post(f"/api/games/{session.id}/move", json={"direction": "down"})
    assert response_move.status_code == 200
    assert session.finalized is True
    assert len(get_high_scores()) == 1
    assert get_high_scores()[0]["score"] == 999


# =====================================================================
# REQ-051: CORS Policies
# =====================================================================

def test_cors_headers():
    """Verify explicit allowed CORS headers, and wildcard exclusion when credentials exist."""
    response = client.options("/api/high-scores", headers={
        "Origin": "http://localhost:5183",
        "Access-Control-Request-Method": "GET"
    })
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5183"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_wildcard_rejection(monkeypatch):
    """Verify that setting ALLOWED_ORIGINS to '*' or containing '*' raises a ValueError on startup."""
    import importlib
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    import backend.main
    with pytest.raises(ValueError, match="Insecure CORS configuration"):
        importlib.reload(backend.main)
    
    # Restore normal state
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    importlib.reload(backend.main)


# =====================================================================
# REQ-056: Request Body Strictness
# =====================================================================

def test_request_body_strictness():
    """Verify extra payload fields are rejected with 422, leaving game state unchanged."""
    create_response = client.post("/api/games")
    game_id = create_response.json()["id"]
    
    # 1. POST /api/games with extra fields -> reject
    bad_create = client.post("/api/games", json={"score": 99999})
    assert bad_create.status_code == 422
    
    # 2. POST /api/games/{id}/move with extra fields -> reject
    bad_move = client.post(f"/api/games/{game_id}/move", json={"direction": "left", "score": 99999})
    assert bad_move.status_code == 422
    
    # State remains untouched and valid empty body/bodyless is preserved
    good_move = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert good_move.status_code == 200
