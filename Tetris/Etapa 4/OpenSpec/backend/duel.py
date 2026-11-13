import asyncio
import time
import secrets
import datetime
import logging
from typing import Dict, Optional, List
from fastapi import WebSocket
from .engine import GameSession, TetrisEngine
from .models import (
    WSMessageEnvelope,
    StartPayload,
    DuelBoardStatePayload,
    OutcomePayload,
    ErrorPayload,
    get_piece_at_index
)

logger = logging.getLogger(__name__)

class DuelGameSession(GameSession):
    def __init__(self, session_id: str, seed: int):
        self.seed = seed
        self.piece_index = 0
        self.generation = 0  # Starts at 0, increments on every spawn or hold swap
        
        self.id = session_id
        self.board = TetrisEngine.create_empty_board()
        self.status = "playing"
        self.score = 0
        self.total_lines = 0
        self.level = 1
        self.gravity_interval_ms = 500
        self.hold_piece = None
        self.can_hold = True
        self.next_pieces = []
        self.finalized = False
        
        # Spawn initial piece using deterministic sequence
        spawn_type = get_piece_at_index(self.piece_index, self.seed)
        self.active_piece, self.status = TetrisEngine.spawn_piece(self.board, spawn_type)
        self.piece_index += 1
        self.next_piece = get_piece_at_index(self.piece_index, self.seed)
        
        if self.status == "game_over":
            self.can_hold = False

    def _spawn_next(self):
        spawn_type = self.next_piece
        self.active_piece, self.status = TetrisEngine.spawn_piece(self.board, spawn_type)
        self.piece_index += 1
        self.next_piece = get_piece_at_index(self.piece_index, self.seed)
        self.generation += 1  # spawn increments generation
        
        if self.status == "game_over":
            self.can_hold = False

    def hold(self) -> bool:
        if self.status == "game_over" or not self.can_hold:
            return False

        current_type = self.active_piece.type

        if self.hold_piece is None:
            self.hold_piece = current_type
            spawn_type = self.next_piece
            self.active_piece, self.status = TetrisEngine.spawn_piece(self.board, spawn_type)
            self.piece_index += 1
            self.next_piece = get_piece_at_index(self.piece_index, self.seed)
            self.generation += 1
        else:
            temp = self.hold_piece
            self.hold_piece = current_type
            self.active_piece, self.status = TetrisEngine.spawn_piece(self.board, temp)
            self.generation += 1

        self.can_hold = False
        if self.status == "game_over":
            self.can_hold = False
        return True

class DuelPlayer:
    def __init__(self, player_id: str, ws: WebSocket, seat: int, seed: int, clock_func=None):
        self.player_id = player_id
        self.ws = ws
        self.seat = seat  # 1 or 2
        self.session = DuelGameSession(session_id=player_id, seed=seed)
        self.seq_number = -1  # last processed action sequence number
        clock = clock_func or time.monotonic
        self.next_gravity_tick_time = clock() + (self.session.gravity_interval_ms / 1000.0)

class DuelRoom:
    def __init__(self, room_id: str, seed: int, clock_func=None):
        self.id = room_id
        self.seed = seed
        self.clock = clock_func or time.monotonic
        self.players: Dict[str, DuelPlayer] = {}  # player_id -> DuelPlayer
        self.status = "waiting"  # "waiting", "playing", "finished"
        self.winner_id: Optional[str] = None
        self.loser_id: Optional[str] = None
        self.is_draw = False
        self.reason: Optional[str] = None
        self.last_input_time = self.clock()  # only updated on explicit C2S actions
        self.finished_at: Optional[float] = None
        self.lock = asyncio.Lock()
        self.gravity_task: Optional[asyncio.Task] = None
        self.revision = 0  # monotonic state revision

def evaluate_room_outcome(room: DuelRoom, reason: str = "top_out"):
    if room.status == "finished":
        return
    
    p1 = None
    p2 = None
    for p in room.players.values():
        if p.seat == 1:
            p1 = p
        elif p.seat == 2:
            p2 = p
            
    if not p1 or not p2:
        return
        
    p1_over = (p1.session.status == "game_over")
    p2_over = (p2.session.status == "game_over")
    
    if p1_over and p2_over:
        room.status = "finished"
        room.is_draw = True
        room.winner_id = None
        room.loser_id = None
        room.finished_at = room.clock()
        room.reason = reason
    elif p1_over:
        room.status = "finished"
        room.is_draw = False
        room.winner_id = p2.player_id
        room.loser_id = p1.player_id
        room.finished_at = room.clock()
        room.reason = reason
    elif p2_over:
        room.status = "finished"
        room.is_draw = False
        room.winner_id = p1.player_id
        room.loser_id = p2.player_id
        room.finished_at = room.clock()
        room.reason = reason

async def broadcast_room_update(room: DuelRoom):
    try:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        
        if room.status == "finished":
            payload = OutcomePayload(
                room_id=room.id,
                winner_id=room.winner_id,
                loser_id=room.loser_id,
                is_draw=room.is_draw,
                reason=room.reason or "top_out"
            )
            envelope = WSMessageEnvelope(
                v=1,
                type="outcome",
                timestamp=now_iso,
                seq=room.revision,
                payload=payload
            )
            msg_str = envelope.model_dump_json()
            for p in list(room.players.values()):
                try:
                    await asyncio.wait_for(p.ws.send_text(msg_str), timeout=1.0)
                except Exception:
                    pass
            return

        # Broadcast state updates for both seats to all players
        for p in list(room.players.values()):
            state_payload = DuelBoardStatePayload(
                room_id=room.id,
                seat=p.seat,
                player_id=p.player_id,
                board=p.session.board,
                active_piece=p.session.active_piece,
                status=p.session.status,
                score=p.session.score,
                total_lines=p.session.total_lines,
                level=p.session.level,
                gravity_interval_ms=p.session.gravity_interval_ms,
                next_piece=p.session.next_piece,
                hold_piece=p.session.hold_piece,
                can_hold=p.session.can_hold,
                revision=room.revision,
                generation=p.session.generation,
                last_processed_seq=p.seq_number
            )
            envelope = WSMessageEnvelope(
                v=1,
                type="state",
                timestamp=now_iso,
                seq=room.revision,
                payload=state_payload
            )
            msg_str = envelope.model_dump_json()
            for recipient in list(room.players.values()):
                try:
                    await asyncio.wait_for(recipient.ws.send_text(msg_str), timeout=1.0)
                except Exception:
                    pass
    except Exception as exc:
        import traceback
        print(f"EXCEPTION IN BROADCAST_ROOM_UPDATE: {exc}", flush=True)
        traceback.print_exc()
        raise exc

def update_room_gravity(room: DuelRoom, now: float) -> bool:
    """
    Ticks gravity for players whose gravity step is due.
    Returns True if state was updated.
    """
    p1 = None
    p2 = None
    for p in room.players.values():
        if p.seat == 1:
            p1 = p
        elif p.seat == 2:
            p2 = p
            
    if not p1 or not p2:
        return False
        
    p1_due = (now >= p1.next_gravity_tick_time)
    p2_due = (now >= p2.next_gravity_tick_time)
    
    updated = False
    if p1_due and p1.session.status == "playing":
        p1.session.step_down()
        p1.next_gravity_tick_time = now + (p1.session.gravity_interval_ms / 1000.0)
        updated = True
    if p2_due and p2.session.status == "playing":
        p2.session.step_down()
        p2.next_gravity_tick_time = now + (p2.session.gravity_interval_ms / 1000.0)
        updated = True
        
    if updated:
        room.revision += 1
        evaluate_room_outcome(room, reason="top_out")
    return updated

async def room_gravity_loop(room: DuelRoom):
    try:
        while room.status == "playing":
            await asyncio.sleep(0.01)  # check every 10ms
            
            async with room.lock:
                if room.status != "playing":
                    break
                    
                now = room.clock()
                if update_room_gravity(room, now):
                    await broadcast_room_update(room)
    except asyncio.CancelledError:
        logger.info("room_gravity_loop cancelled")
        raise

class DuelRoomManager:
    def __init__(self, clock_func=None):
        self.rooms: Dict[str, DuelRoom] = {}
        self.sweeper_task: Optional[asyncio.Task] = None
        self.clock = clock_func or time.monotonic

    def get_or_create_room(self, room_id: str) -> Optional[DuelRoom]:
        if room_id in self.rooms:
            return self.rooms[room_id]
        
        if len(self.rooms) >= 100:
            return None  # Max rooms storage limit exceeded
            
        seed = secrets.randbits(32)
        room = DuelRoom(room_id, seed, clock_func=self.clock)
        self.rooms[room_id] = room
        return room

    async def handle_disconnect(self, room: DuelRoom, player_id: str):
        async with room.lock:
            if room.status == "finished":
                # Clean up if room was already finished
                return
                
            p = room.players.get(player_id)
            if not p:
                return
                
            opponent = None
            for op_id, op in room.players.items():
                if op_id != player_id:
                    opponent = op
                    break
                    
            if room.status == "playing" and opponent:
                room.status = "finished"
                room.is_draw = False
                room.winner_id = opponent.player_id
                room.loser_id = player_id
                room.finished_at = room.clock()
                room.reason = "forfeit"
                await broadcast_room_update(room)
            else:
                room.status = "finished"
                room.finished_at = room.clock()
                room.reason = "forfeit"
                try:
                    current_t = asyncio.current_task()
                except Exception:
                    current_t = None
                if room.gravity_task and room.gravity_task != current_t:
                    room.gravity_task.cancel()
                    room.gravity_task = None

    async def _close_ws_bounded(self, ws: WebSocket):
        try:
            await asyncio.wait_for(ws.close(), timeout=1.0)
        except Exception:
            pass

    async def sweep_rooms(self):
        now = self.clock()
        to_delete = []
        for room_id, room in list(self.rooms.items()):
            if room.status == "finished":
                if room.finished_at and (now - room.finished_at >= 60.0):
                    to_delete.append(room_id)
            else:
                # finished after 240s of inactivity
                if now - room.last_input_time > 240.0:
                    to_delete.append(room_id)
                    
        close_tasks = []
        for room_id in to_delete:
            room = self.rooms.pop(room_id, None)
            if room:
                try:
                    current_t = asyncio.current_task()
                except Exception:
                    current_t = None
                if room.gravity_task and room.gravity_task != current_t:
                    room.gravity_task.cancel()
                
                for p in list(room.players.values()):
                    close_tasks.append(self._close_ws_bounded(p.ws))
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

    async def sweep_rooms_loop(self, interval: float = 60.0):
        try:
            while True:
                await asyncio.sleep(interval)
                await self.sweep_rooms()
        except asyncio.CancelledError:
            await self.shutdown()
            raise

    async def shutdown(self):
        tasks = []
        for room_id, room in list(self.rooms.items()):
            try:
                current_t = asyncio.current_task()
            except Exception:
                current_t = None
            if room.gravity_task and room.gravity_task != current_t:
                room.gravity_task.cancel()
                tasks.append(room.gravity_task)
            for p in list(room.players.values()):
                tasks.append(self._close_ws_bounded(p.ws))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.rooms.clear()
