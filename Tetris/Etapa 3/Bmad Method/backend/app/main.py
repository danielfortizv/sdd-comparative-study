import os
import uuid
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, Literal, Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.domain import (
    GameState,
    create_new_game,
    move_piece,
    tick_game,
    hold_game
)

app = FastAPI(title="Stage 3 Tetris Study API", version="1.0.0")

# Restrictive Configurable CORS policy (no wildcard origin with credentials)
CORS_ORIGINS_ENV = os.getenv("CORS_ALLOWED_ORIGINS", "")
if CORS_ORIGINS_ENV:
    cors_origins = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]
else:
    cors_origins = ["http://localhost:5183", "http://127.0.0.1:5183", "http://localhost:5173"]

allow_creds = True
if "*" in cors_origins:
    if len(cors_origins) == 1:
        # Wildcard only, we must not allow credentials
        allow_creds = False
    else:
        # Multiple origins, remove wildcard so explicit allowed origins still work with credentials
        cors_origins = [origin for origin in cors_origins if origin != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Process-wide synchronization lock for single-process threadpool
state_lock = threading.RLock()

# Ephemeral in-memory sessions mapping UUID -> GameState
sessions: Dict[str, GameState] = {}

# Persistence metadata tracking
persisted_sessions: Dict[str, bool] = {}
completed_timestamps: Dict[str, str] = {}

TETRIS_DB_PATH = os.getenv("TETRIS_DB_PATH", "./data/high-scores.sqlite3")

def init_db():
    """Initializes parent directory and database schema safely on service startup."""
    db_dir = os.path.dirname(os.path.abspath(TETRIS_DB_PATH))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(TETRIS_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS high_scores (
                game_id TEXT PRIMARY KEY NOT NULL,
                score INTEGER NOT NULL CHECK (score >= 0),
                total_lines INTEGER NOT NULL CHECK (total_lines >= 0),
                level INTEGER NOT NULL CHECK (level >= 1),
                completed_at TEXT NOT NULL
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_high_scores_sort 
            ON high_scores (score DESC, completed_at ASC, game_id ASC);
        """)
        conn.commit()
    finally:
        conn.close()

# Safe immediate schema initialization
init_db()

def save_high_score(game_id: str, score: int, total_lines: int, level: int, completed_at: str):
    """Executes atomic, parameterized write for completed games once per game ID."""
    conn = sqlite3.connect(TETRIS_DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO high_scores (game_id, score, total_lines, level, completed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (game_id, score, total_lines, level, completed_at))
        conn.commit()
    finally:
        conn.close()

def ensure_persisted(state: GameState):
    """Guards database write finalization, rolling back and raising 503 upon failures."""
    if state.status != "game_over":
        return
    
    game_id = state.id
    if persisted_sessions.get(game_id, False):
        return
    
    if game_id not in completed_timestamps:
        completed_timestamps[game_id] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
    completed_at = completed_timestamps[game_id]
    
    try:
        save_high_score(game_id, state.score, state.total_lines, state.level, completed_at)
        persisted_sessions[game_id] = True
    except Exception:
        persisted_sessions[game_id] = False
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="High score storage temporarily unavailable"
        )

def check_and_handle_terminal_retry(id: str):
    """Retries database persistence safely on subsequent mutating requests if previous attempts failed."""
    state = sessions[id]
    if state.status == "game_over":
        if not persisted_sessions.get(id, False):
            ensure_persisted(state)
        return state
    return None

# Request validation schemas with strict forbidden extra fields
class GameCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

class MoveRequest(BaseModel):
    direction: Literal["left", "right", "down"]
    model_config = {"extra": "forbid"}

class HighScoreEntry(BaseModel):
    game_id: str
    score: int
    total_lines: int
    level: int
    completed_at: str

class HighScoresResponse(BaseModel):
    scores: List[HighScoreEntry]

@app.post("/api/games", status_code=status.HTTP_201_CREATED, response_model=GameState)
def create_game(request: Optional[GameCreateRequest] = None):
    """Initializes a brand new game session in memory under synchronization guard."""
    with state_lock:
        game_id = str(uuid.uuid4())
        state = create_new_game(game_id)
        sessions[game_id] = state
        return state.model_copy(deep=True)

@app.get("/api/games/{id}", response_model=GameState)
def get_game(id: str):
    """Retrieves a detached snapshot of game state without performing persistence retry."""
    with state_lock:
        if id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found"
            )
        return sessions[id].model_copy(deep=True)

@app.post("/api/games/{id}/tick", response_model=GameState)
def tick_game_session(id: str):
    """Advances the game state by one gravity tick, finalizes on game over, and supports mutating retry."""
    with state_lock:
        if id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found"
            )
        
        terminal_state = check_and_handle_terminal_retry(id)
        if terminal_state is not None:
            return terminal_state.model_copy(deep=True)
            
        current_state = sessions[id]
        new_state = tick_game(current_state)
        sessions[id] = new_state
        
        if new_state.status == "game_over":
            ensure_persisted(new_state)
            
        return new_state.model_copy(deep=True)

@app.post("/api/games/{id}/move", response_model=GameState)
def move_game_session(id: str, request: MoveRequest):
    """Performs manual shift, finalizes on game over, and supports mutating retry."""
    with state_lock:
        if id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found"
            )
        
        terminal_state = check_and_handle_terminal_retry(id)
        if terminal_state is not None:
            return terminal_state.model_copy(deep=True)
            
        current_state = sessions[id]
        new_state = move_piece(current_state, request.direction)
        sessions[id] = new_state
        
        if new_state.status == "game_over":
            ensure_persisted(new_state)
            
        return new_state.model_copy(deep=True)

@app.post("/api/games/{id}/hold", response_model=GameState)
def hold_game_session(id: str):
    """Performs hold swap, finalizes on game over, and supports mutating retry."""
    with state_lock:
        if id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game session not found"
            )
        
        terminal_state = check_and_handle_terminal_retry(id)
        if terminal_state is not None:
            return terminal_state.model_copy(deep=True)
            
        current_state = sessions[id]
        new_state = hold_game(current_state)
        sessions[id] = new_state
        
        if new_state.status == "game_over":
            ensure_persisted(new_state)
            
        return new_state.model_copy(deep=True)

@app.get("/api/high-scores", response_model=HighScoresResponse)
def get_high_scores():
    """Returns sorted leaderboard snapshot of at most ten entries under read-only lock guard."""
    with state_lock:
        try:
            conn = sqlite3.connect(TETRIS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT game_id, score, total_lines, level, completed_at
                FROM high_scores
                ORDER BY score DESC, completed_at ASC, game_id ASC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            conn.close()
            
            scores_list = [
                HighScoreEntry(
                    game_id=row[0],
                    score=row[1],
                    total_lines=row[2],
                    level=row[3],
                    completed_at=row[4]
                )
                for row in rows
            ]
            return HighScoresResponse(scores=scores_list)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="High score storage temporarily unavailable"
            )
