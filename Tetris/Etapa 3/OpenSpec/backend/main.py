import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import GameState, MoveRequest, GameCreateRequest, HighScoresResponse, HighScoreEntry
from .engine import SessionManager, GameSession
from .database import init_db, save_high_score, get_high_scores

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe database schema initialization on startup
    init_db()
    yield

app = FastAPI(title="Stateless Tetris API", version="1.0.0", lifespan=lifespan)

# Define secure CORS policy configuration
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5183",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5183",
    ]

# Explicitly reject wildcard origin when credentials are enabled to prevent insecure wildcard credentials configuration
if "*" in allowed_origins:
    raise ValueError("Insecure CORS configuration: Wildcard '*' is not allowed when credentials are enabled.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trapping sqlite3.Error operations and returning a controlled clean 503 response
@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    import traceback
    print("Database error caught by global handler:", traceback.format_exc())
    return JSONResponse(
        status_code=503,
        content={"detail": "Storage service unavailable"}
    )

manager = SessionManager()

# Centralized error detail constant
GAME_SESSION_NOT_FOUND = "Game session not found"
APPLICATION_JSON = "application/json"
HOLD_ACTION_NOT_ALLOWED = "Hold action is not allowed at this moment."

RESPONSES_404 = {
    404: {
        "description": GAME_SESSION_NOT_FOUND,
        "content": {APPLICATION_JSON: {"example": {"detail": GAME_SESSION_NOT_FOUND}}},
    }
}

RESPONSES_404_400 = {
    404: {
        "description": GAME_SESSION_NOT_FOUND,
        "content": {APPLICATION_JSON: {"example": {"detail": GAME_SESSION_NOT_FOUND}}},
    },
    400: {
        "description": "Invalid parameters or action not allowed",
        "content": {APPLICATION_JSON: {"example": {"detail": HOLD_ACTION_NOT_ALLOWED}}},
    }
}

def try_finalize_session(session: GameSession) -> None:
    """Attempts to persist final game state exactly once when session transitions to game_over."""
    if session.status == "game_over" and not session.finalized:
        completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        save_high_score(
            game_id=session.id,
            score=session.score,
            total_lines=session.total_lines,
            level=session.level,
            completed_at=completed_at
        )
        session.finalized = True

@app.post("/api/games", response_model=GameState, status_code=status.HTTP_201_CREATED)
async def create_game(request: Optional[GameCreateRequest] = None):
    # Creates an authoritative backend game. Banned metadata handled automatically by Pydantic extra="forbid".
    session = manager.create_session()
    return session.to_state()

@app.get("/api/games/{game_id}", response_model=GameState, responses=RESPONSES_404)
async def get_game(game_id: str):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail=GAME_SESSION_NOT_FOUND)
    # Read-only GET requests must not write high-score or mutate state (GET idempotency)
    return session.to_state()

@app.post("/api/games/{game_id}/move", response_model=GameState, responses=RESPONSES_404_400)
async def move_game(game_id: str, request: MoveRequest):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail=GAME_SESSION_NOT_FOUND)
    
    if request.direction not in ("left", "right", "down"):
        raise HTTPException(status_code=400, detail="Invalid direction. Must be 'left', 'right', or 'down'.")
    
    async with manager.get_lock(game_id):
        if session.status == "game_over":
            try_finalize_session(session)
        else:
            session.move(request.direction)
            try_finalize_session(session)
        return session.to_state()

@app.post("/api/games/{game_id}/tick", response_model=GameState, responses=RESPONSES_404)
async def tick_game(game_id: str):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail=GAME_SESSION_NOT_FOUND)
    
    async with manager.get_lock(game_id):
        if session.status == "game_over":
            try_finalize_session(session)
        else:
            session.step_down()
            try_finalize_session(session)
        return session.to_state()

@app.post("/api/games/{game_id}/hold", response_model=GameState, responses=RESPONSES_404_400)
async def hold_game(game_id: str):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail=GAME_SESSION_NOT_FOUND)
    
    async with manager.get_lock(game_id):
        if session.status == "game_over":
            try_finalize_session(session)
            raise HTTPException(
                status_code=400,
                detail=HOLD_ACTION_NOT_ALLOWED
            )
        else:
            success = session.hold()
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail=HOLD_ACTION_NOT_ALLOWED
                )
            try_finalize_session(session)
        return session.to_state()

@app.get("/api/high-scores", response_model=HighScoresResponse)
async def leaderboard():
    # Read-only GET requests must not mutate state or write entries
    scores = get_high_scores()
    return HighScoresResponse(scores=scores)
