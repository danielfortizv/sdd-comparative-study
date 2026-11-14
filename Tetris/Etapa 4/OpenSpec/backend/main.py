import os
import sqlite3
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    GameState, MoveRequest, GameCreateRequest, HighScoresResponse, HighScoreEntry,
    ActionPayload, StartPayload, DuelBoardStatePayload, OutcomePayload, ErrorPayload, WSMessageEnvelope
)
from .engine import SessionManager, GameSession
from .database import init_db, save_high_score, get_high_scores
from .duel import DuelPlayer, DuelRoomManager, broadcast_room_update, room_gravity_loop, evaluate_room_outcome

duel_manager = DuelRoomManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe database schema initialization on startup
    init_db()
    
    # Start background room sweeper
    sweeper_task = asyncio.create_task(duel_manager.sweep_rooms_loop())
    
    yield
    
    sweeper_task.cancel()
    try:
        await sweeper_task
    except asyncio.CancelledError:
        pass

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

    if request.direction not in ("left", "right", "down", "clockwise", "counterclockwise"):
        raise HTTPException(status_code=400, detail="Invalid direction. Must be 'left', 'right', 'down', 'clockwise', or 'counterclockwise'.")

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

@app.websocket("/api/ws/duel/{room_id}")
async def websocket_duel(websocket: WebSocket, room_id: str, player_id: str):
    import json
    import re
    
    # 1. Validate room_id and player_id format BEFORE room allocation with strict trailing newline rejection
    ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+\Z")
    if (not room_id or len(room_id) > 64 or not ID_REGEX.match(room_id) or
        not player_id or len(player_id) > 64 or not ID_REGEX.match(player_id)):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 2. Handshake Origin validation
    origin = websocket.headers.get("origin")
    if not origin or origin == "null":
        raise HTTPException(status_code=403, detail="Missing or null origin")
        
    normalized_allowed = [o.rstrip("/").lower() for o in allowed_origins]
    if origin.rstrip("/").lower() not in normalized_allowed:
        raise HTTPException(status_code=403, detail="Forbidden origin")

    # 3. Matchmaking and Seat Assignment
    room = duel_manager.get_or_create_room(room_id)
    if not room:
        await websocket.accept()
        try:
            await asyncio.wait_for(websocket.close(code=4000, reason="Room Full or Limit Reached"), timeout=1.0)
        except Exception:
            pass
        return

    reject_code = None
    reject_reason = ""

    async with room.lock:
        if room.status == "finished":
            reject_code = 4003
            reject_reason = "Room already finished"
        elif player_id in room.players:
            reject_code = 4004
            reject_reason = "Duplicate player_id"
        elif len(room.players) >= 2:
            reject_code = 4001
            reject_reason = "Room Full"
        else:
            seat = 1 if len(room.players) == 0 else 2
            existing_seats = {p.seat for p in room.players.values()}
            if 1 not in existing_seats:
                seat = 1
            elif 2 not in existing_seats:
                seat = 2
                
            player = DuelPlayer(player_id=player_id, ws=websocket, seat=seat, seed=room.seed, clock_func=room.clock)
            room.players[player_id] = player

    if reject_code is not None:
        await websocket.accept()
        try:
            await asyncio.wait_for(websocket.close(code=reject_code, reason=reject_reason), timeout=1.0)
        except Exception:
            pass
        return

    await websocket.accept()

    async with room.lock:
        if player_id in room.players and len(room.players) == 2 and room.status == "waiting":
            room.status = "playing"
            room.revision += 1
            now_mon = room.clock()
            for p in room.players.values():
                p.next_gravity_tick_time = now_mon + (p.session.gravity_interval_ms / 1000.0)
                
            room.gravity_task = asyncio.create_task(room_gravity_loop(room))
            
            # Broadcast start message
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            p1_id = next((p.player_id for p in room.players.values() if p.seat == 1), "")
            p2_id = next((p.player_id for p in room.players.values() if p.seat == 2), "")
            start_payload = StartPayload(room_id=room.id, player1_id=p1_id, player2_id=p2_id)
            envelope = WSMessageEnvelope(
                v=1,
                type="start",
                timestamp=now_iso,
                seq=room.revision,
                payload=start_payload
            )
            start_msg = envelope.model_dump_json()
            for p in list(room.players.values()):
                try:
                    await asyncio.wait_for(p.ws.send_text(start_msg), timeout=1.0)
                except Exception:
                    pass

        await broadcast_room_update(room)

    # 4. Main message receive loop
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(code=msg.get("code", 1000))
                
            if "bytes" in msg:
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                err_env = WSMessageEnvelope(
                    v=1,
                    type="error",
                    timestamp=now_iso,
                    seq=room.revision,
                    payload=ErrorPayload(message="Binary frames not supported")
                )
                try:
                    await asyncio.wait_for(websocket.send_text(err_env.model_dump_json()), timeout=1.0)
                except Exception:
                    pass
                await websocket.close(code=1003, reason="Binary frames not supported")
                break
                
            if "text" not in msg:
                continue
                
            data = msg["text"]
            
            # Frame size validation
            if len(data.encode("utf-8")) > 4096:
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                err_env = WSMessageEnvelope(
                    v=1,
                    type="error",
                    timestamp=now_iso,
                    seq=room.revision,
                    payload=ErrorPayload(message="Frame size exceeds 4096-byte limit")
                )
                try:
                    await asyncio.wait_for(websocket.send_text(err_env.model_dump_json()), timeout=1.0)
                except Exception:
                    pass
                await websocket.close(code=1008, reason="Frame size exceeds limit")
                break

            try:
                msg_dict = json.loads(data)
                envelope = WSMessageEnvelope(**msg_dict)
            except Exception:
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                err_env = WSMessageEnvelope(
                    v=1,
                    type="error",
                    timestamp=now_iso,
                    seq=room.revision,
                    payload=ErrorPayload(message="Invalid message envelope")
                )
                try:
                    await asyncio.wait_for(websocket.send_text(err_env.model_dump_json()), timeout=1.0)
                except Exception:
                    pass
                await websocket.close(code=1008, reason="Invalid message envelope")
                break

            if envelope.type not in ("action", "heartbeat"):
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                err_env = WSMessageEnvelope(
                    v=1,
                    type="error",
                    timestamp=now_iso,
                    seq=room.revision,
                    payload=ErrorPayload(message="Forbidden client message type")
                )
                try:
                    await asyncio.wait_for(websocket.send_text(err_env.model_dump_json()), timeout=1.0)
                except Exception:
                    pass
                await websocket.close(code=1008, reason="Forbidden client message type")
                break

            if envelope.type == "heartbeat":
                # Heartbeat is a no-op
                continue

            if envelope.type == "action":
                action_payload: ActionPayload = envelope.payload
                
                async with room.lock:
                    if room.status != "playing":
                        continue

                    # Strict seat and room controls
                    if action_payload.player_id != player_id:
                        continue
                    if action_payload.room_id != room_id:
                        continue
                        
                    p = room.players.get(player_id)
                    if not p:
                        continue
                    if p.session.status == "game_over":
                        continue

                    # Sequence and Generation gates FIRST
                    if action_payload.seq <= p.seq_number:
                        continue
                    if action_payload.generation != p.session.generation:
                        continue

                    room.last_input_time = room.clock()
                    p.seq_number = action_payload.seq

                    action_name = action_payload.action
                    if action_name == "move_left":
                        p.session.move("left")
                    elif action_name == "move_right":
                        p.session.move("right")
                    elif action_name == "rotate_clockwise":
                        p.session.move("clockwise")
                    elif action_name == "rotate_counterclockwise":
                        p.session.move("counterclockwise")
                    elif action_name == "soft_drop":
                        p.session.move("down")
                    elif action_name == "hard_drop":
                        while p.session.status == "playing":
                            success = p.session.step_down()
                            if not success:
                                break
                    elif action_name == "hold":
                        p.session.hold()

                    room.revision += 1
                    evaluate_room_outcome(room, reason="top_out")
                    await broadcast_room_update(room)

    except WebSocketDisconnect:
        await duel_manager.handle_disconnect(room, player_id)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        await duel_manager.handle_disconnect(room, player_id)
