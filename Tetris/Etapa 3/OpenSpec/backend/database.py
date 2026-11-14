import os
import sqlite3
from typing import List, Dict, Any, Optional

def get_db_path() -> str:
    """Returns the database path from the environment or default."""
    return os.environ.get("TETRIS_DB_PATH", "./data/high-scores.sqlite3")

def init_db() -> None:
    """Safely creates the parent directory of TETRIS_DB_PATH and initializes the schema."""
    db_path = get_db_path()
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    
    # Establish connection and initialize schema
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS high_scores (
                game_id TEXT PRIMARY KEY,
                score INTEGER NOT NULL,
                total_lines INTEGER NOT NULL,
                level INTEGER NOT NULL,
                completed_at TEXT NOT NULL
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_high_scores_score_completed 
            ON high_scores(score DESC, completed_at ASC, game_id ASC);
        """)
        conn.commit()
    finally:
        conn.close()

def save_high_score(game_id: str, score: int, total_lines: int, level: int, completed_at: str) -> None:
    """Persists a single high score row. Enforces unique constraint via standard INSERT."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO high_scores (game_id, score, total_lines, level, completed_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (game_id, score, total_lines, level, completed_at)
        )
        conn.commit()
    finally:
        conn.close()

def get_high_scores() -> List[Dict[str, Any]]:
    """Retrieves the top 10 scores, sorted by score DESC, completed_at ASC, game_id ASC."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT game_id, score, total_lines, level, completed_at
            FROM high_scores
            ORDER BY score DESC, completed_at ASC, game_id ASC
            LIMIT 10;
            """
        )
        rows = cursor.fetchall()
        scores = []
        for r in rows:
            scores.append({
                "game_id": r[0],
                "score": r[1],
                "total_lines": r[2],
                "level": r[3],
                "completed_at": r[4]
            })
        return scores
    finally:
        conn.close()
