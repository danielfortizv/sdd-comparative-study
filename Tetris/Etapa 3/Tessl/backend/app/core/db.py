import os
import sqlite3
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

def get_db_path() -> str:
    return os.getenv("TETRIS_DB_PATH", "./data/high-scores.sqlite3")

def init_db():
    db_path = get_db_path()
    parent_dir = os.path.dirname(db_path)
    
    # Safely handle parent directory creation
    if parent_dir:
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError:
            logger.exception(f"Failed to create database directory {parent_dir}")
            raise DatabaseError("Failed to initialize database storage directory")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
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
            CREATE INDEX IF NOT EXISTS idx_high_scores_sorting 
            ON high_scores(score DESC, completed_at ASC, game_id ASC);
        """)
        conn.commit()
    except (sqlite3.Error, OSError):
        logger.exception(f"Failed to initialize database at {db_path}")
        raise DatabaseError("Failed to initialize database tables")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                # Do not mask the original exception if one was raised,
                # but log the failure to close the connection.
                logger.warning(f"Error closing connection during init_db: {e}")

def save_high_score(game_id: str, score: int, total_lines: int, level: int, completed_at: str):
    db_path = get_db_path()
    
    # Ensure tables/dirs are initialized safely (handles global TestClient missing lifespan trigger)
    init_db()
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO high_scores (game_id, score, total_lines, level, completed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (game_id, score, total_lines, level, completed_at))
        conn.commit()
    except sqlite3.IntegrityError:
        # Already persisted, ignore to support idempotency
        pass
    except (sqlite3.Error, OSError):
        logger.exception("Database error saving high score")
        raise DatabaseError("Database error occurred while saving score")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection during save_high_score: {e}")

def get_high_scores():
    db_path = get_db_path()
    
    # Ensure tables/dirs are initialized safely
    init_db()
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, score, total_lines, level, completed_at
            FROM high_scores
            ORDER BY score DESC, completed_at ASC, game_id ASC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        scores = []
        for row in rows:
            scores.append({
                "game_id": row[0],
                "score": row[1],
                "total_lines": row[2],
                "level": row[3],
                "completed_at": row[4]
            })
        return scores
    except (sqlite3.Error, OSError):
        logger.exception("Database error reading high scores")
        raise DatabaseError("Database error occurred while retrieving leaderboard")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection during get_high_scores: {e}")
