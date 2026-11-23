import os
import pytest
import sqlite3
from app.services.database import get_db_path, init_db, insert_high_score, fetch_leaderboard, get_db_connection

@pytest.fixture(autouse=True)
def setup_temp_db(tmp_path, monkeypatch):
    """
    Automatically set a unique temporary database path for each unit test.
    This guarantees complete database isolation.
    """
    temp_db_file = tmp_path / "subdir" / "temp-scores.sqlite3"
    monkeypatch.setenv("TETRIS_DB_PATH", str(temp_db_file))
    yield temp_db_file
    # Cleanup after test if needed
    if temp_db_file.exists():
        try:
            # Close WAL connections first if open
            pass
        except Exception:
            pass

def test_db_init_and_directory_creation(setup_temp_db):
    # Directory should not exist yet
    db_dir = setup_temp_db.parent
    assert not db_dir.exists()
    
    # Run initialization
    init_db()
    
    # Directory and file should now exist
    assert db_dir.exists()
    assert setup_temp_db.exists()
    
    # Connect and check columns
    conn = get_db_connection()
    try:
        cursor = conn.execute("PRAGMA table_info(high_scores);")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "game_id" in columns
        assert "score" in columns
        assert "total_lines" in columns
        assert "level" in columns
        assert "completed_at" in columns
        assert columns["game_id"].upper() == "TEXT"
    finally:
        conn.close()

def test_sql_injection_defense(setup_temp_db):
    init_db()
    
    # Attempt SQL injection as field values (e.g. game_id with quotes)
    injection_id = "'; DROP TABLE high_scores; --"
    # Should safely insert without executing injection or raising errors
    success = insert_high_score(
        game_id=injection_id,
        score=1000,
        total_lines=10,
        level=2,
        completed_at="2026-10-29T12:00:00Z"
    )
    assert success is True
    
    # Verify the table still exists and contains the raw string
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT game_id FROM high_scores")
        row = cursor.fetchone()
        assert row is not None
        assert row["game_id"] == injection_id
    finally:
        conn.close()

def test_leaderboard_sorting_rules(setup_temp_db):
    init_db()
    
    # Insert multiple records, including ties
    # Rules: score DESC, completed_at ASC, game_id ASC
    records = [
        # Tie score, diff times
        ("game-tie-later", 500, 5, 1, "2026-10-29T15:00:00Z"),
        ("game-tie-earlier", 500, 5, 1, "2026-10-29T14:00:00Z"),
        # Higher score
        ("game-highest", 1000, 10, 2, "2026-10-29T12:00:00Z"),
        # Lower score
        ("game-lowest", 100, 1, 1, "2026-10-29T12:00:00Z"),
        # Same score, same time, different ID lexicographically
        ("game-tie-id-z", 500, 5, 1, "2026-10-29T14:00:00Z"),
        ("game-tie-id-a", 500, 5, 1, "2026-10-29T14:00:00Z"),
    ]
    
    for gid, sc, tl, lv, ca in records:
        insert_high_score(gid, sc, tl, lv, ca)
        
    leaderboard = fetch_leaderboard()
    
    # Expected order:
    # 1. game-highest (score 1000)
    # 2. game-tie-earlier (score 500, completed_at 14:00:00, id lexicographically higher than tie-id-a but earlier time)
    # 3. game-tie-id-a (score 500, completed_at 14:00:00, earlier than 15:00:00, game_id 'game-tie-id-a' < 'game-tie-id-z')
    # 4. game-tie-id-z (score 500, completed_at 14:00:00, earlier than 15:00:00, game_id 'game-tie-id-z')
    # 5. game-tie-later (score 500, completed_at 15:00:00)
    # 6. game-lowest (score 100)
    
    assert len(leaderboard) == 6
    assert leaderboard[0]["game_id"] == "game-highest"
    assert leaderboard[1]["game_id"] == "game-tie-earlier"
    assert leaderboard[2]["game_id"] == "game-tie-id-a"
    assert leaderboard[3]["game_id"] == "game-tie-id-z"
    assert leaderboard[4]["game_id"] == "game-tie-later"
    assert leaderboard[5]["game_id"] == "game-lowest"

def test_leaderboard_limit_ten(setup_temp_db):
    init_db()
    for i in range(15):
        insert_high_score(f"game-{i:02d}", i * 10, i, 1, "2026-10-29T12:00:00Z")
        
    leaderboard = fetch_leaderboard()
    assert len(leaderboard) == 10
    # Top entry should be game-14 (score 140)
    assert leaderboard[0]["game_id"] == "game-14"
    assert leaderboard[0]["score"] == 140
