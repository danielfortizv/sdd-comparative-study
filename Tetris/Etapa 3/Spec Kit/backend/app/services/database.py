import os
import sqlite3
import logging
from typing import List, Dict, Any

# Configure logger
logger = logging.getLogger("tetris.database")

def get_db_path() -> str:
    """
    Get the configured SQLite database file path.
    Defaults to './data/high-scores.sqlite3'.
    """
    return os.environ.get("TETRIS_DB_PATH", "./data/high-scores.sqlite3")

def get_db_connection() -> sqlite3.Connection:
    """
    Establish a connection to the SQLite database.
    Configures WAL mode, busy timeout, and foreign keys.
    """
    db_path = get_db_path()
    # Ensure parent directory exists
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Configure production settings for performance and safety
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    
    return conn

def init_db() -> None:
    """
    Initialize the SQLite database schema and indices.
    Safe to call multiple times (idempotent).
    """
    db_path = get_db_path()
    logger.info(f"Initializing database at: {db_path}")
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS high_scores (
                    game_id TEXT PRIMARY KEY NOT NULL,
                    score INTEGER NOT NULL CHECK(score >= 0),
                    total_lines INTEGER NOT NULL CHECK(total_lines >= 0),
                    level INTEGER NOT NULL CHECK(level >= 1),
                    completed_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_high_scores_leaderboard 
                ON high_scores (score DESC, completed_at ASC, game_id ASC);
            """)
        logger.info("Database schema and index initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize database schema")
        raise e
    finally:
        conn.close()

def insert_high_score(game_id: str, score: int, total_lines: int, level: int, completed_at: str) -> bool:
    """
    Atomically inserts a completed game score.
    Returns True if successfully inserted, or False if duplicate (IntegrityError).
    Raises SQLite database errors to be caught at router layer for 503 errors.
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO high_scores (game_id, score, total_lines, level, completed_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (game_id, score, total_lines, level, completed_at)
            )
        return True
    except sqlite3.IntegrityError as e:
        # Check if it's a primary key violation, which means we already persisted it (idempotency)
        if "UNIQUE constraint failed" in str(e) or "PRIMARY KEY" in str(e):
            logger.warning(f"Duplicate high score insertion blocked for game_id={game_id}")
            return False
        raise e
    finally:
        conn.close()

def fetch_leaderboard() -> List[Dict[str, Any]]:
    """
    Fetch at most 10 high score records.
    Ordered by score descending, then completed_at ascending, then game_id ascending.
    Does NOT mutate state or create database records.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT game_id, score, total_lines, level, completed_at
            FROM high_scores
            ORDER BY score DESC, completed_at ASC, game_id ASC
            LIMIT 10;
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
