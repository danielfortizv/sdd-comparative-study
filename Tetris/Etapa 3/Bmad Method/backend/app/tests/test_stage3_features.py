import os
import uuid
import sqlite3
import pytest
import threading
import time
from fastapi.testclient import TestClient
from app.main import app, TETRIS_DB_PATH, init_db, persisted_sessions, completed_timestamps, sessions
import app.main as app_module

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db_and_sessions(tmp_path, monkeypatch):
    """Fixture to reset database and ephemeral sessions before each test using isolated tmp_path."""
    test_db = os.path.join(tmp_path, "high-scores.sqlite3")
    monkeypatch.setattr(app_module, "TETRIS_DB_PATH", str(test_db))
            
    # Reinitialize DB and clear registry
    init_db()
    app_module.sessions.clear()
    app_module.persisted_sessions.clear()
    app_module.completed_timestamps.clear()

def test_db_initialization_and_schema():
    """Verify that schema initialization creates appropriate fields and indexes."""
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(high_scores);")
    columns = {row[1]: (row[2], row[3]) for row in cursor.fetchall()}
    
    # Check fields and typing/not-null
    assert "game_id" in columns
    assert "score" in columns
    assert "total_lines" in columns
    assert "level" in columns
    assert "completed_at" in columns
    
    assert columns["game_id"] == ("TEXT", 1) # NOT NULL is 1
    assert columns["score"] == ("INTEGER", 1)
    assert columns["total_lines"] == ("INTEGER", 1)
    assert columns["level"] == ("INTEGER", 1)
    assert columns["completed_at"] == ("TEXT", 1)
    conn.close()

def test_high_score_eligibility_and_zero_scores():
    """Ensure completed games (even with score=0) are saved, while active/restarts are not."""
    # Create game
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Active game should not be in high_scores database
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM high_scores WHERE game_id = ?", (game_id,))
    assert cursor.fetchone()[0] == 0
    conn.close()
    
    # Force game_over in memory and trigger finalization
    with app_module.state_lock:
        state = app_module.sessions[game_id]
        state.status = "game_over"
        state.score = 0
        state.total_lines = 0
        state.level = 1
    
    # Mutating action like tick on a terminal state triggers database save
    tick_res = client.post(f"/api/games/{game_id}/tick")
    assert tick_res.status_code == 200
    
    # Ensure it's now in database
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT score, total_lines, level FROM high_scores WHERE game_id = ?", (game_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 0 # Zero score preserved
    conn.close()

def test_idempotency_and_uniqueness():
    """Repeated terminal actions must not duplicate database entries or modify completion timestamp."""
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    with app_module.state_lock:
        state = app_module.sessions[game_id]
        state.status = "game_over"
        state.score = 500
    
    # First finalization
    client.post(f"/api/games/{game_id}/tick")
    
    # Fetch first timestamp
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT completed_at FROM high_scores WHERE game_id = ?", (game_id,))
    first_time = cursor.fetchone()[0]
    conn.close()
    
    # Repeated terminal mutation
    client.post(f"/api/games/{game_id}/tick")
    
    # Check that timestamp remains identical and count is exactly 1
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT completed_at, COUNT(*) FROM high_scores WHERE game_id = ?", (game_id,))
    row = cursor.fetchone()
    assert row[0] == first_time
    assert row[1] == 1
    conn.close()

def test_failure_and_recovery_503(monkeypatch):
    """Test 503 response on SQLite failure, in-memory state preservation, and safe mutating retry."""
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Force game over
    with app_module.state_lock:
        state = app_module.sessions[game_id]
        state.status = "game_over"
        state.score = 250
        
    # Simulate DB storage failure by switching TETRIS_DB_PATH to a read-only or invalid path using monkeypatch
    monkeypatch.setattr(app_module, "TETRIS_DB_PATH", "/invalid_directory/invalid_file.sqlite3")
    
    # Mutation on terminal game should fail with 503 and hide trace info
    tick_res = client.post(f"/api/games/{game_id}/tick")
    assert tick_res.status_code == 503
    assert tick_res.json() == {"detail": "High score storage temporarily unavailable"}
    
    # Game must still be in-memory as game_over but un-persisted
    assert game_id in app_module.sessions
    assert app_module.sessions[game_id].status == "game_over"
    assert app_module.persisted_sessions[game_id] is False
    
    # Recovery: restore DB path
    monkeypatch.undo()
    
    # Subsequent mutating request should retry and succeed
    retry_res = client.post(f"/api/games/{game_id}/tick")
    assert retry_res.status_code == 200
    assert app_module.persisted_sessions[game_id] is True
    
    # Ensure it's in the DB
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM high_scores WHERE game_id = ?", (game_id,))
    assert cursor.fetchone()[0] == 250
    conn.close()

def test_leaderboard_ties_and_sorting():
    """Verify that leaderboard yields top 10 sorted by score DESC, completed_at ASC, game_id ASC."""
    # Insert multiple scores directly into DB
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    
    scores_data = [
        ("g1", 1000, 10, 2, "2026-11-02T12:00:00Z"),
        ("g2", 2000, 20, 4, "2026-11-02T12:00:00Z"),
        ("g3", 1500, 15, 3, "2026-11-02T12:00:00Z"),
        ("g4", 1500, 15, 3, "2026-11-02T11:00:00Z"), # Older completed_at
        ("g5", 1500, 15, 3, "2026-11-02T13:00:00Z"), # Newer completed_at
        ("g6", 500, 5, 1, "2026-11-02T12:00:00Z"),
        ("g7", 1500, 15, 3, "2026-11-02T11:00:00Z"), # Tie on score & completed_at, but ID 'g7' > 'g4'
        ("g8", 3000, 30, 5, "2026-11-02T12:00:00Z"),
        ("g9", 0, 0, 1, "2026-11-02T12:00:00Z"),
        ("g10", 2500, 25, 5, "2026-11-02T12:00:00Z"),
        ("g11", 100, 1, 1, "2026-11-02T12:00:00Z"),
        ("g12", 800, 8, 2, "2026-11-02T12:00:00Z")
    ]
    
    cursor.executemany("""
        INSERT INTO high_scores (game_id, score, total_lines, level, completed_at)
        VALUES (?, ?, ?, ?, ?)
    """, scores_data)
    conn.commit()
    conn.close()
    
    # Request leaderboard
    res = client.get("/api/high-scores")
    assert res.status_code == 200
    scores = res.json()["scores"]
    
    # Must be at most 10 entries
    assert len(scores) == 10
    
    # Validate sorting:
    # 1st: g8 (3000)
    # 2nd: g10 (2500)
    # 3rd: g2 (2000)
    # 4th: g4 (1500, completed_at 11:00, id g4)
    # 5th: g7 (1500, completed_at 11:00, id g7)
    # 6th: g3 (1500, completed_at 12:00, id g3)
    # 7th: g5 (1500, completed_at 13:00, id g5)
    # 8th: g1 (1000)
    # 9th: g12 (800)
    # 10th: g6 (500)
    # Excluded: g11 (100), g9 (0)
    
    expected_order = ["g8", "g10", "g2", "g4", "g7", "g3", "g5", "g1", "g12", "g6"]
    actual_order = [s["game_id"] for s in scores]
    assert actual_order == expected_order

def test_strict_payload_body_validation():
    """Extra fields in game creation and move request bodies must be rejected with 422."""
    # Bodyless creation should succeed
    create_res = client.post("/api/games")
    assert create_res.status_code == 201
    game_id = create_res.json()["id"]
    
    # Creation with extra parameters should fail
    create_bad_res = client.post("/api/games", json={"score_metadata": 9999})
    assert create_bad_res.status_code == 422
    
    # Normal movement body should succeed
    move_res = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert move_res.status_code == 200
    
    # Movement body with extra fields must fail
    move_bad_res = client.post(f"/api/games/{game_id}/move", json={"direction": "left", "extra": "field"})
    assert move_bad_res.status_code == 422

def test_sql_injection_protection(monkeypatch):
    """Verify parameterized SQL protection against SQL-injection-like string inputs."""
    malicious_id = "g1'; DROP TABLE high_scores; --"
    create_res = client.post("/api/games")
    orig_game_id = create_res.json()["id"]
    
    # Inject malicious game state fields using monkeypatch
    with app_module.state_lock:
        state = app_module.sessions[orig_game_id]
        monkeypatch.setattr(state, "id", malicious_id)
        monkeypatch.setattr(state, "status", "game_over")
        monkeypatch.setattr(state, "score", 9999)
        monkeypatch.setitem(app_module.sessions, malicious_id, state)
        
    client.post(f"/api/games/{malicious_id}/tick")
    
    # Table must still exist and the record must be inserted safely as a text value
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM high_scores WHERE game_id = ?", (malicious_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 9999
    conn.close()

def test_persistence_after_new_store_instance(monkeypatch):
    """Scores must survive and remain readable after a new database instance opens the same SQLite file."""
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    with app_module.state_lock:
        state = app_module.sessions[game_id]
        monkeypatch.setattr(state, "status", "game_over")
        monkeypatch.setattr(state, "score", 777)
        
    client.post(f"/api/games/{game_id}/tick")
    
    # Simulate process restart by reloading the DB in a fresh SQLite handle
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM high_scores WHERE game_id = ?", (game_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 777
    conn.close()

def test_concurrency_multithreading_rlock(monkeypatch):
    """Simulate high concurrent thread requests to verify lock synchronization and uniqueness preservation."""
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    with app_module.state_lock:
        state = app_module.sessions[game_id]
        monkeypatch.setattr(state, "status", "game_over")
        monkeypatch.setattr(state, "score", 1200)
        
    errors = []
    
    def worker():
        try:
            res = client.post(f"/api/games/{game_id}/tick")
            # Should either succeed or return 503 if we simulated failure (which we don't here)
            assert res.status_code in [200, 503]
        except AssertionError:
            raise
        except Exception as e:
            errors.append(e)
            
    threads = [threading.Thread(target=worker) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0
    
    # Confirm exactly 1 record was written
    conn = sqlite3.connect(app_module.TETRIS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM high_scores WHERE game_id = ?", (game_id,))
    assert cursor.fetchone()[0] == 1
    conn.close()
