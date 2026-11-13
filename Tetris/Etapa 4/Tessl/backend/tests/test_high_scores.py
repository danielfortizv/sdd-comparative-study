import os
import sqlite3
import pytest
from unittest import mock
from fastapi.testclient import TestClient

from app.main import app
from app.controllers.games import GAMES, COMPLETED_AT_STORE, PERSISTED_GAMES
from app.models.game import ActivePieceModel, GameStateModel
from app.core.db import get_db_path, DatabaseError, init_db, get_high_scores

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_stores_and_db(tmp_path, monkeypatch):
    """
    Cleans up transient in-memory game stores and points TETRIS_DB_PATH
    to a temporary isolated file for each test run.
    """
    # Clean in-memory stores
    GAMES.clear()
    COMPLETED_AT_STORE.clear()
    PERSISTED_GAMES.clear()

    # Point to isolated temporary db
    temp_db_path = str(tmp_path / "test-high-scores.sqlite3")
    monkeypatch.setenv("TETRIS_DB_PATH", temp_db_path)
    
    # Initialize schema
    init_db()
    
    yield temp_db_path

    # Meaningful teardown of the temporary database file
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass

def test_root_and_db_configured(clean_stores_and_db):
    assert get_db_path() == clean_stores_and_db
    assert os.path.exists(clean_stores_and_db)

def test_top_ten_sorting_with_ties(clean_stores_and_db):
    # Req-S3-16: Sort by score DESC, completed_at ASC, game_id ASC
    from app.core.db import save_high_score, get_high_scores
    
    # Insert tied and varied scores
    # Tie in score:
    save_high_score("g1", 100, 10, 1, "2026-11-02T10:00:00Z")
    save_high_score("g2", 100, 10, 1, "2026-11-02T09:00:00Z") # completed_at is earlier, should come first
    # Tie in score and completed_at:
    save_high_score("g4", 100, 10, 1, "2026-11-02T12:00:00Z")
    save_high_score("g3", 100, 10, 1, "2026-11-02T12:00:00Z") # g3 game_id is smaller, should come first
    # Lower score:
    save_high_score("g5", 50, 5, 1, "2026-11-02T08:00:00Z")
    # Higher score:
    save_high_score("g6", 200, 20, 2, "2026-11-02T11:00:00Z")

    response = client.get("/api/high-scores")
    assert response.status_code == 200
    scores = response.json()["scores"]
    
    # Expected ordering:
    # 1. g6 (score 200)
    # 2. g2 (score 100, 09:00:00)
    # 3. g1 (score 100, 10:00:00)
    # 4. g3 (score 100, 12:00:00, id g3)
    # 5. g4 (score 100, 12:00:00, id g4)
    # 6. g5 (score 50)
    
    assert [s["game_id"] for s in scores] == ["g6", "g2", "g1", "g3", "g4", "g5"]

def test_zero_score_finalization(clean_stores_and_db):
    # Req-S3-5: Save zero scores
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Force game over
    state.status = "game_over"
    state.score = 0
    state.total_lines = 0
    state.level = 1
    
    # Mutating request should trigger finalization
    client.post(f"/api/games/{game_id}/tick")
    
    # Read high scores
    scores_res = client.get("/api/high-scores")
    scores = scores_res.json()["scores"]
    assert len(scores) == 1
    assert scores[0]["game_id"] == game_id
    assert scores[0]["score"] == 0

def test_three_terminal_paths(clean_stores_and_db, monkeypatch):
    # Req-S3-7: tick, move down, and obstructed Hold must trigger game-over and save
    
    # 1. Tick path
    res1 = client.post("/api/games")
    g1_id = res1.json()["id"]
    state1 = GAMES[g1_id]
    state1.board[1][3] = 'S' # block row 1 column 3
    state1.active_piece = ActivePieceModel(type='I', origin=(0, 3), cells=[(0,3), (0,4), (0,5), (0,6)])
    monkeypatch.setitem(GAMES, g1_id, state1)
    client.post(f"/api/games/{g1_id}/tick")
    assert GAMES[g1_id].status == "game_over"
    
    # 2. Move down path
    res2 = client.post("/api/games")
    g2_id = res2.json()["id"]
    state2 = GAMES[g2_id]
    state2.board[1][3] = 'S'
    state2.active_piece = ActivePieceModel(type='I', origin=(0, 3), cells=[(0,3), (0,4), (0,5), (0,6)])
    monkeypatch.setitem(GAMES, g2_id, state2)
    client.post(f"/api/games/{g2_id}/move", json={"direction": "down"})
    assert GAMES[g2_id].status == "game_over"
    
    # 3. Obstructed Hold path
    res3 = client.post("/api/games")
    g3_id = res3.json()["id"]
    state3 = GAMES[g3_id]
    # Prefill spawn area
    for col in (3, 4, 5, 6):
        state3.board[0][col] = 'S'
    state3.next_piece = 'I'
    monkeypatch.setitem(GAMES, g3_id, state3)
    client.post(f"/api/games/{g3_id}/hold")
    assert GAMES[g3_id].status == "game_over"
    
    # Verify all 3 saved in database
    db_scores = get_high_scores()
    assert len(db_scores) == 3
    saved_ids = {s["game_id"] for s in db_scores}
    assert saved_ids == {g1_id, g2_id, g3_id}

def test_abandoned_restarted_games_excluded(clean_stores_and_db):
    # Req-S3-8: Live, restarted, or abandoned games write no high scores
    client.post("/api/games") # Active
    res = client.post("/api/games") # Another active
    g_id = res.json()["id"]
    
    # Abandoned without reaching game_over
    db_scores = get_high_scores()
    assert len(db_scores) == 0

def test_repeated_terminal_actions_idempotent(clean_stores_and_db):
    # Req-S3-9: Repeated ticks or moves on terminal games are idempotent
    res = client.post("/api/games")
    g_id = res.json()["id"]
    state = GAMES[g_id]
    state.status = "game_over"
    state.score = 500
    
    res1 = client.post(f"/api/games/{g_id}/tick")
    timestamp_before = COMPLETED_AT_STORE[g_id]
    
    # Execute a second tick
    res2 = client.post(f"/api/games/{g_id}/tick")
    timestamp_after = COMPLETED_AT_STORE[g_id]
    
    assert timestamp_before == timestamp_after
    db_scores = get_high_scores()
    assert len(db_scores) == 1
    assert db_scores[0]["score"] == 500

def test_get_is_read_only(clean_stores_and_db):
    # Req-S3-10: GET requests never write or mutate
    res = client.post("/api/games")
    g_id = res.json()["id"]
    state = GAMES[g_id]
    state.status = "game_over"
    
    client.get(f"/api/games/{g_id}")
    # Since it's a GET, it should NOT have written to the DB
    db_scores = get_high_scores()
    assert len(db_scores) == 0

def test_extra_fields_rejection(clean_stores_and_db):
    # Req-S3-19: Strict input body check
    # Game creation with extra fields should return 422
    res_game = client.post("/api/games", json={"score": 100})
    assert res_game.status_code == 422
    
    # Game move with extra fields
    res = client.post("/api/games")
    g_id = res.json()["id"]
    res_move = client.post(f"/api/games/{g_id}/move", json={"direction": "down", "extra": "field"})
    assert res_move.status_code == 422

def test_database_failure_handling_and_retry(clean_stores_and_db, monkeypatch):
    # Req-S3-21, Req-S3-22: Return 503 and support safe retries on storage failure
    res = client.post("/api/games")
    g_id = res.json()["id"]
    state = GAMES[g_id]
    state.status = "game_over"
    state.score = 150
    
    # Mock sqlite3.connect to simulate database/filesystem failure
    with mock.patch("sqlite3.connect", side_effect=sqlite3.OperationalError("Mocked database lock/failure")):
        # A mutating request should fail with 503 Service Unavailable
        res_tick = client.post(f"/api/games/{g_id}/tick")
        assert res_tick.status_code == 503
        assert res_tick.json() == {"detail": "High scores database is temporarily unavailable."}
    
    # The game status remains game_over, and original completed_at was cached
    assert state.status == "game_over"
    assert g_id in COMPLETED_AT_STORE
    orig_completed_at = COMPLETED_AT_STORE[g_id]
    
    # Next mutating request (without mock) should succeed and write to database using the cached completed_at
    res_retry = client.post(f"/api/games/{g_id}/tick")
    assert res_retry.status_code == 200
    
    db_scores = get_high_scores()
    assert len(db_scores) == 1
    assert db_scores[0]["game_id"] == g_id
    assert db_scores[0]["score"] == 150
    assert db_scores[0]["completed_at"] == orig_completed_at

def test_reopen_app_instance_preserves_data(clean_stores_and_db):
    # Req-S3-12: High scores survive process restart
    from app.core.db import save_high_score, get_high_scores
    save_high_score("g_persist", 999, 99, 9, "2026-11-02T15:00:00Z")
    
    # Reset in-memory states (simulating backend process reboot)
    GAMES.clear()
    COMPLETED_AT_STORE.clear()
    PERSISTED_GAMES.clear()
    
    # Re-read
    scores = get_high_scores()
    assert len(scores) == 1
    assert scores[0]["game_id"] == "g_persist"
    assert scores[0]["score"] == 999
