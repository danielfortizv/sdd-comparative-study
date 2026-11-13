import asyncio
import json
import logging
import random
import hashlib
import re
import secrets
from typing import Dict, Optional, Tuple, List, Callable, Literal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError, Field, model_validator

from app.models.game import GameStateModel, ActivePieceModel, TetrominoType
from app.domain.pieces import get_relative_cells, get_random_piece_type
from app.domain.rules import tick_game, move_game, hold_game, rotate_game, is_legal_position

logger = logging.getLogger(__name__)
router = APIRouter()

# Restrictive Stage 4 origins policy
AUTHORIZED_ORIGINS = {
    "http://localhost:5515",
    "http://127.0.0.1:5515",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
}

# Monotonic production and test clocks
class ProductionClock:
    def get_time(self) -> float:
        import time
        return time.monotonic()

class TestClock:
    def __init__(self, start_time: float = 0.0):
        self._time: float = start_time

    def get_time(self) -> float:
        return self._time

    def advance(self, seconds: float):
        self._time += seconds

def get_piece_type_at_index(seed: int, index: int) -> str:
    PIECES = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
    key = f"{seed}_{index}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    val = int.from_bytes(digest, byteorder="big")
    return PIECES[val % 7]

# Pydantic validation models for inbound websocket frames
class ClientHandshakePayload(BaseModel):
    room_id: str
    client_id: str

    model_config = {
        "extra": "forbid",
        "strict": True,
        "str_strip_whitespace": False
    }

    @model_validator(mode="after")
    def validate_handshake_fields(self) -> 'ClientHandshakePayload':
        for name, val in (("room_id", self.room_id), ("client_id", self.client_id)):
            if not isinstance(val, str):
                raise ValueError(f"{name} must be a string")
            if not val or len(val) > 64:
                raise ValueError(f"{name} length must be between 1 and 64")
            if any(c in val for c in ('\r', '\n', '\u2028', '\u2029')):
                raise ValueError(f"{name} cannot contain line breaks or control characters")
            if not re.match(r"^[a-zA-Z0-9_-]+$", val):
                raise ValueError(f"{name} must contain only alphanumeric, hyphens, and underscores")
        return self

class ClientHandshakeMessage(BaseModel):
    version: Literal["1.0"]
    type: Literal["handshake"]
    payload: ClientHandshakePayload

    model_config = {
        "extra": "forbid",
        "strict": True,
        "str_strip_whitespace": False
    }

class ClientActionPayload(BaseModel):
    action_id: int
    action_type: Literal["move", "rotate", "hold"]
    direction: Literal["left", "right", "down", "cw", "ccw"] | None
    expected_revision: int

    model_config = {
        "extra": "forbid",
        "strict": True,
        "str_strip_whitespace": False
    }

    @model_validator(mode="after")
    def validate_action_fields(self) -> 'ClientActionPayload':
        if type(self.action_id) is bool or type(self.expected_revision) is bool:
            raise ValueError("bool is not allowed for integer fields")
        if not (1 <= self.action_id <= 9007199254740991):
            raise ValueError("action_id out of range")
        if not (0 <= self.expected_revision <= 9007199254740991):
            raise ValueError("expected_revision out of range")

        if self.action_type == "move":
            if self.direction not in ("left", "right", "down"):
                raise ValueError("move action requires direction left, right, or down")
        elif self.action_type == "rotate":
            if self.direction not in ("cw", "ccw"):
                raise ValueError("rotate action requires direction cw or ccw")
        elif self.action_type == "hold":
            if self.direction is not None:
                raise ValueError("hold action direction must be null")
        return self

class ClientActionMessage(BaseModel):
    version: Literal["1.0"]
    type: Literal["action"]
    payload: ClientActionPayload

    model_config = {
        "extra": "forbid",
        "strict": True,
        "str_strip_whitespace": False
    }


# Pydantic models for validated canonical outbound messages
class ServerHandshakePayload(BaseModel):
    room_id: str
    seat: Literal["player1", "player2"]
    status: Literal["waiting", "playing", "finished"]
    player1_id: Optional[str] = None
    player2_id: Optional[str] = None

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerHandshakeMessage(BaseModel):
    version: Literal["1.0"] = "1.0"
    type: Literal["handshake"] = "handshake"
    payload: ServerHandshakePayload

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerAckPayload(BaseModel):
    action_id: int
    status: Literal["accepted", "noop", "rejected"]
    reason: str
    board_revision: int
    room_revision: int
    authoritative_board: GameStateModel

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerAckMessage(BaseModel):
    version: Literal["1.0"] = "1.0"
    type: Literal["ack"] = "ack"
    payload: ServerAckPayload

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerStateUpdatePayload(BaseModel):
    room_id: str
    room_revision: int
    status: Literal["waiting", "playing", "finished"]
    player1_board: Optional[GameStateModel] = None
    player2_board: Optional[GameStateModel] = None
    winner_seat: Optional[Literal["player1", "player2", "draw"]] = None
    outcome_reason: Optional[Literal[
        "topout-player1", "topout-player2", "simultaneous-topout",
        "forfeit-player1", "forfeit-player2", "waiting-peer-timeout",
        "waiting-aborted", "operational-abort"
    ]] = None

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerStateUpdateMessage(BaseModel):
    version: Literal["1.0"] = "1.0"
    type: Literal["state_update"] = "state_update"
    payload: ServerStateUpdatePayload

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerErrorPayload(BaseModel):
    error_code: int
    message: str

    model_config = {
        "extra": "forbid",
        "strict": True
    }

class ServerErrorMessage(BaseModel):
    version: Literal["1.0"] = "1.0"
    type: Literal["error"] = "error"
    payload: ServerErrorPayload

    model_config = {
        "extra": "forbid",
        "strict": True
    }


def make_canonical_error(code: int, message: str) -> str:
    payload = ServerErrorPayload(error_code=code, message=message)
    msg = ServerErrorMessage(payload=payload)
    return msg.model_dump_json()


class Peer:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.queue = asyncio.Queue(maxsize=100)
        self.closed_event = asyncio.Event()
        self._transport_closed = False
        self._close_called = False
        self._close_code = 1000
        self.write_task = asyncio.create_task(socket_writer_loop(websocket, self.queue, self))

    def send(self, text: str) -> bool:
        if self.closed_event.is_set():
            return False
        try:
            self.queue.put_nowait(text)
            return True
        except asyncio.QueueFull:
            self.closed_event.set()
            return False

    def send_no_fail_trigger(self, text: str):
        if self.closed_event.is_set():
            return
        try:
            self.queue.put_nowait(text)
        except Exception:
            pass

    def close(self, code: int = 1000):
        if self._close_called:
            return
        self._close_called = True
        self._close_code = code
        while self.queue.full():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        try:
            self.queue.put_nowait({"_type": "close", "code": code})
        except Exception:
            pass

    def cancel(self):
        if not self.write_task.done():
            self.write_task.cancel()

    async def drain_and_stop(self):
        if not self.write_task.done():
            try:
                await asyncio.wait_for(self.queue.join(), timeout=0.1)
            except Exception:
                pass
        if not self.write_task.done():
            self.write_task.cancel()
            await asyncio.gather(self.write_task, return_exceptions=True)
        await self.close_transport()

    async def close_transport(self):
        if not self._transport_closed:
            self._transport_closed = True
            self.closed_event.set()
            try:
                await asyncio.wait_for(self.websocket.close(code=self._close_code), timeout=0.1)
            except Exception:
                pass


async def socket_writer_loop(websocket: WebSocket, queue: asyncio.Queue, peer: Peer):
    try:
        while True:
            item = await queue.get()
            try:
                if isinstance(item, dict) and item.get("_type") == "close":
                    code = item.get("code", 1000)
                    peer._close_code = code
                    try:
                        await asyncio.wait_for(websocket.close(code=code), timeout=0.1)
                    except Exception:
                        pass
                    peer._transport_closed = True
                    queue.task_done()
                    break
                
                text = item
                send_task = asyncio.create_task(websocket.send_text(text))
                try:
                    await asyncio.wait_for(asyncio.shield(send_task), timeout=0.200)
                except asyncio.TimeoutError:
                    logger.error("Write timeout in socket_writer_loop")
                    send_task.cancel()
                    try:
                        await asyncio.wait({send_task}, timeout=0.050)
                    except Exception:
                        pass
                    await peer.close_transport()
                    queue.task_done()
                    break
                except Exception:
                    send_task.cancel()
                    queue.task_done()
                    break
            except Exception:
                queue.task_done()
                break
            queue.task_done()
    except asyncio.CancelledError:
        raise
    finally:
        peer.closed_event.set()
        try:
            await peer.close_transport()
        except Exception:
            pass


class DuelRoom:
    def __init__(self, room_id: str, clock=None):
        self.room_id = room_id
        self.clock = clock or ProductionClock()
        self.status: Literal["waiting", "playing", "finished"] = "waiting"
        self.room_revision: int = 0
        self.seed: int = secrets.randbelow(1000001)
        
        self.player1_id: Optional[str] = None
        self.player2_id: Optional[str] = None
        
        self.player1_peer: Optional[Peer] = None
        self.player2_peer: Optional[Peer] = None
        
        self.player1_board: Optional[GameStateModel] = None
        self.player2_board: Optional[GameStateModel] = None
        
        self.player1_highwater: int = 0
        self.player2_highwater: int = 0
        self.player1_index: int = 0
        self.player2_index: int = 0
        
        self.player1_last_gravity_time: float = 0.0
        self.player2_last_gravity_time: float = 0.0
        self.player1_last_active_time: float = self.clock.get_time()
        self.player2_last_active_time: float = self.clock.get_time()
        self.finished_time: Optional[float] = None
        self.terminal_last_active_time: Optional[float] = None
        
        self.winner_seat: Optional[Literal["player1", "player2", "draw"]] = None
        self.outcome_reason: Optional[Literal[
            "topout-player1", "topout-player2", "simultaneous-topout",
            "forfeit-player1", "forfeit-player2", "waiting-peer-timeout",
            "waiting-aborted", "operational-abort"
        ]] = None
        
        self.lock = asyncio.Lock()
        self.gravity_task: Optional[asyncio.Task] = None
        self.cached_snapshot: Optional[str] = None

    def initialize_player_board(self, is_p1: bool):
        p_active = get_piece_type_at_index(self.seed, 0)
        p_next = get_piece_type_at_index(self.seed, 1)
        board = GameStateModel(
            id="board_player1_uuid" if is_p1 else "board_player2_uuid",
            board=[[None]*10 for _ in range(20)],
            active_piece=ActivePieceModel(
                type=p_active,
                origin=(0, 3),
                cells=[(0 + r, 3 + c) for r, c in get_relative_cells(p_active, 0)],
                orientation=0
            ),
            status="playing",
            score=0,
            total_lines=0,
            level=1,
            gravity_interval_ms=500,
            next_piece=p_next,
            hold_piece=None,
            can_hold=True,
            board_revision=0
        )
        if is_p1:
            self.player1_index = 1
            self.player1_board = board
            self.player1_last_gravity_time = self.clock.get_time()
        else:
            self.player2_index = 1
            self.player2_board = board
            self.player2_last_gravity_time = self.clock.get_time()

    def get_state_snapshot_text(self) -> str:
        if self.status == "finished" and self.cached_snapshot is not None:
            return self.cached_snapshot

        payload = ServerStateUpdatePayload(
            room_id=self.room_id,
            room_revision=self.room_revision,
            status=self.status,
            player1_board=self.player1_board,
            player2_board=self.player2_board,
            winner_seat=self.winner_seat,
            outcome_reason=self.outcome_reason
        )
        msg = ServerStateUpdateMessage(payload=payload)
        text = msg.model_dump_json()
        if self.status == "finished":
            self.cached_snapshot = text
        return text

    def broadcast_snapshot(self, snapshot: str):
        for peer in (self.player1_peer, self.player2_peer):
            if peer:
                success = peer.send(snapshot)
                if not success:
                    is_p1 = (peer == self.player1_peer)
                    logger.error(f"Queue full for {'player1' if is_p1 else 'player2'} in broadcast_snapshot")
                    self.handle_peer_failure_sync(is_p1, "Queue Full")

    def transition_to_finished_sync(self, winner_seat: Optional[Literal["player1", "player2", "draw"]], outcome_reason: str, now: Optional[float] = None, delay_broadcast: bool = False):
        if self.status == "finished":
            return
            
        if now is None:
            now = self.clock.get_time()
            
        self.status = "finished"
        self.winner_seat = winner_seat
        self.outcome_reason = outcome_reason
        self.finished_time = now
        self.terminal_last_active_time = now
        
        if self.room_revision < 9007199254740991:
            self.room_revision += 1
            
        snapshot = self.get_state_snapshot_text()
        
        if self.gravity_task and not self.gravity_task.done():
            self.gravity_task.cancel()

        if not delay_broadcast:
            if self.player1_peer:
                self.player1_peer.send_no_fail_trigger(snapshot)
                self.player1_peer.close(1000)
            if self.player2_peer:
                self.player2_peer.send_no_fail_trigger(snapshot)
                self.player2_peer.close(1000)

    def handle_peer_failure_sync(self, is_p1: bool, reason: str):
        if self.status == "finished":
            return
            
        now = self.clock.get_time()
        
        if self.status == "waiting":
            winner = None
            outcome = "waiting-aborted"
            if self.player1_board is None:
                self.initialize_player_board(is_p1=True)
        else:
            winner = "player2" if is_p1 else "player1"
            outcome = "forfeit-player1" if is_p1 else "forfeit-player2"
            
        self.transition_to_finished_sync(winner, outcome, now)

    async def shutdown_room(self, code: int = 1000):
        async with self.lock:
            if self.status != "finished":
                now = self.clock.get_time()
                if self.status == "waiting":
                    winner = None
                    outcome = "waiting-aborted"
                else:
                    winner = "draw"
                    outcome = "operational-abort"
                if self.status == "waiting" and self.player1_board is None:
                    self.initialize_player_board(is_p1=True)
                self.transition_to_finished_sync(winner, outcome, now)

        peers = []
        if self.player1_peer:
            peers.append(self.player1_peer)
        if self.player2_peer:
            peers.append(self.player2_peer)
            
        for peer in peers:
            await peer.drain_and_stop()


ROOMS: Dict[str, DuelRoom] = {}
ROOMS_LOCK = asyncio.Lock()

def make_piece_supplier(room: DuelRoom, is_p1: bool) -> Callable[[], str]:
    def supplier() -> str:
        if is_p1:
            room.player1_index += 1
            idx = room.player1_index
        else:
            room.player2_index += 1
            idx = room.player2_index
        return get_piece_type_at_index(room.seed, idx)
    return supplier

class SpeculativeSupplier:
    def __init__(self, room: DuelRoom, is_p1: bool):
        self.room = room
        self.is_p1 = is_p1
        self.orig_index = room.player1_index if is_p1 else room.player2_index
        self.current_index = self.orig_index

    def __call__(self) -> str:
        self.current_index += 1
        return get_piece_type_at_index(self.room.seed, self.current_index)

    def commit(self):
        if self.is_p1:
            self.room.player1_index = self.current_index
        else:
            self.room.player2_index = self.current_index

def is_board_overflow(board: GameStateModel) -> bool:
    MAX = 9007199254740991
    return (
        board.board_revision >= MAX or
        board.score >= MAX or
        board.total_lines >= MAX or
        board.level >= MAX
    )

def check_game_outcomes_sync(room: DuelRoom, now: float, delay_broadcast: bool = False):
    if room.status != "playing":
        return
        
    p1_over = room.player1_board.status == "game_over" if room.player1_board else False
    p2_over = room.player2_board.status == "game_over" if room.player2_board else False
    
    if p1_over and p2_over:
        room.transition_to_finished_sync("draw", "simultaneous-topout", now, delay_broadcast=delay_broadcast)
    elif p1_over:
        room.transition_to_finished_sync("player2", "topout-player1", now, delay_broadcast=delay_broadcast)
    elif p2_over:
        room.transition_to_finished_sync("player1", "topout-player2", now, delay_broadcast=delay_broadcast)

async def gravity_background_loop(room: DuelRoom):
    try:
        while room.status == "playing":
            await asyncio.sleep(0.02)
            
            snapshot = None
            async with room.lock:
                if room.status != "playing":
                    break
                
                now = room.clock.get_time()
                
                # Immediate preflight check for pre-existing overflow
                if room.room_revision >= 9007199254740991:
                    room.transition_to_finished_sync("draw", "operational-abort", now)
                    snapshot = room.get_state_snapshot_text()
                elif (room.player1_board and is_board_overflow(room.player1_board)) or (room.player2_board and is_board_overflow(room.player2_board)):
                    room.transition_to_finished_sync("draw", "operational-abort", now)
                    snapshot = room.get_state_snapshot_text()
                else:
                    p1_interval = (room.player1_board.gravity_interval_ms / 1000.0) if room.player1_board else 0.5
                    p2_interval = (room.player2_board.gravity_interval_ms / 1000.0) if room.player2_board else 0.5
                    
                    p1_due = (now - room.player1_last_gravity_time) >= p1_interval
                    p2_due = (now - room.player2_last_gravity_time) >= p2_interval
                    
                    if p1_due or p2_due:
                        overflow_detected = False
                        
                        next_p1_board = None
                        spec_supplier_p1 = None
                        if p1_due and room.player1_board and room.player1_board.status != "game_over":
                            if is_board_overflow(room.player1_board):
                                overflow_detected = True
                            else:
                                board_p1_copy = room.player1_board.model_copy(deep=True)
                                spec_supplier_p1 = SpeculativeSupplier(room, is_p1=True)
                                candidate_board_p1 = tick_game(board_p1_copy, spec_supplier_p1)
                                if is_board_overflow(candidate_board_p1) or (room.room_revision + 1 >= 9007199254740991):
                                    overflow_detected = True
                                else:
                                    next_p1_board = candidate_board_p1
                                    
                        next_p2_board = None
                        spec_supplier_p2 = None
                        if p2_due and room.player2_board and room.player2_board.status != "game_over" and room.status == "playing":
                            if is_board_overflow(room.player2_board):
                                overflow_detected = True
                            else:
                                board_p2_copy = room.player2_board.model_copy(deep=True)
                                spec_supplier_p2 = SpeculativeSupplier(room, is_p1=False)
                                candidate_board_p2 = tick_game(board_p2_copy, spec_supplier_p2)
                                if is_board_overflow(candidate_board_p2) or (room.room_revision + 1 >= 9007199254740991):
                                    overflow_detected = True
                                else:
                                    next_p2_board = candidate_board_p2

                        if overflow_detected:
                            room.transition_to_finished_sync("draw", "operational-abort", now)
                            snapshot = room.get_state_snapshot_text()
                        else:
                            if next_p1_board is not None:
                                spec_supplier_p1.commit()
                                room.player1_board = next_p1_board
                                room.player1_last_gravity_time = now
                            if next_p2_board is not None:
                                spec_supplier_p2.commit()
                                room.player2_board = next_p2_board
                                room.player2_last_gravity_time = now
                                
                            if room.status == "playing":
                                room.room_revision += 1
                                check_game_outcomes_sync(room, now)
                            
                            snapshot = room.get_state_snapshot_text()
            
            if snapshot:
                room.broadcast_snapshot(snapshot)
                
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception(f"Exception in room {room.room_id} gravity loop: {str(e)}")

async def room_sweeper_loop():
    try:
        while True:
            await asyncio.sleep(60.0)
            await sweep_once(ProductionClock().get_time())
    except asyncio.CancelledError:
        raise

async def sweep_once(now_val: float):
    rooms_to_shutdown = []
    async with ROOMS_LOCK:
        to_remove = []
        for r_id, room in list(ROOMS.items()):
            room_now = room.clock.get_time()
            if room.status == "finished":
                ref_time = room.terminal_last_active_time if room.terminal_last_active_time is not None else room.finished_time
                if ref_time is not None and room_now - ref_time >= 300.0:
                    to_remove.append(r_id)
            elif room.status == "waiting":
                if room_now - room.player1_last_active_time >= 120.0:
                    async with room.lock:
                        room.transition_to_finished_sync(None, "waiting-peer-timeout", room_now)
            elif room.status == "playing":
                if (room_now - room.player1_last_active_time >= 120.0) and (room_now - room.player2_last_active_time >= 120.0):
                    async with room.lock:
                        room.transition_to_finished_sync("draw", "operational-abort", room_now)
        
        for r_id in to_remove:
            room = ROOMS.pop(r_id)
            rooms_to_shutdown.append(room)
            
    for room in rooms_to_shutdown:
        logger.info(f"Sweeping room {room.room_id} from memory store.")
        await room.shutdown_room()

async def shutdown_sweeper():
    async with ROOMS_LOCK:
        rooms = list(ROOMS.values())
        ROOMS.clear()
        
    for room in rooms:
        await room.shutdown_room()

_sweeper_task: Optional[asyncio.Task] = None

def start_sweeper():
    global _sweeper_task
    if _sweeper_task is None or _sweeper_task.done():
        _sweeper_task = asyncio.create_task(room_sweeper_loop())

async def stop_sweeper():
    global _sweeper_task
    if _sweeper_task and not _sweeper_task.done():
        _sweeper_task.cancel()
        await asyncio.gather(_sweeper_task, return_exceptions=True)
    _sweeper_task = None


async def receive_message_with_timeout(websocket: WebSocket, peer: Peer) -> Optional[dict]:
    receive_task = asyncio.create_task(websocket.receive())
    close_wait_task = asyncio.create_task(peer.closed_event.wait())
    
    done, pending = await asyncio.wait(
        [receive_task, close_wait_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    for t in pending:
        t.cancel()
        
    if close_wait_task in done:
        return None
        
    return receive_task.result()


def commit_and_ack_action_sync(room: DuelRoom, peer: Peer, board: GameStateModel, action: ClientActionPayload, is_p1: bool, now_active: float) -> Optional[str]:
    if is_p1:
        room.player1_board = board
    else:
        room.player2_board = board
        
    if room.room_revision < 9007199254740991:
        room.room_revision += 1
        
    check_game_outcomes_sync(room, now_active, delay_broadcast=True)
    
    ack_payload = ServerAckPayload(
        action_id=action.action_id,
        status="accepted",
        reason="success",
        board_revision=board.board_revision,
        room_revision=room.room_revision,
        authoritative_board=board
    )
    peer.send(ServerAckMessage(payload=ack_payload).model_dump_json())
    
    if room.status == "finished":
        snapshot_text = room.get_state_snapshot_text()
        if room.player1_peer:
            room.player1_peer.send_no_fail_trigger(snapshot_text)
            room.player1_peer.close(1000)
        if room.player2_peer:
            room.player2_peer.send_no_fail_trigger(snapshot_text)
            room.player2_peer.close(1000)
        return None
    else:
        return room.get_state_snapshot_text()


@router.websocket("/api/ws/duel/{room_id}")
async def ws_duel_endpoint(websocket: WebSocket, room_id: str):
    start_sweeper()

    # We use ProductionClock by default, but tests can inject a mocked clock.
    clock = ProductionClock()

    origin = websocket.headers.get("origin")
    if not origin or origin not in AUTHORIZED_ORIGINS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    peer = Peer(websocket)

    handshake_payload: Optional[ClientHandshakePayload] = None
    
    async def hello_timeout():
        await asyncio.sleep(10.0)
        if handshake_payload is None:
            peer.close(1008)
            peer.closed_event.set()

    timeout_task = asyncio.create_task(hello_timeout())
    
    window_start = clock.get_time()
    message_count = 0

    room: Optional[DuelRoom] = None
    is_p1 = True
    client_id = ""
    assigned_seat: Optional[Literal["player1", "player2"]] = None

    try:
        while not peer.closed_event.is_set():
            raw_msg = await receive_message_with_timeout(websocket, peer)
            if raw_msg is None:
                break

            if "bytes" in raw_msg:
                peer.close(1003)
                return

            text = raw_msg.get("text")
            if text is None:
                break

            if len(text.encode("utf-8")) > 4096:
                peer.close(1009)
                return

            now = clock.get_time()
            if now - window_start >= 1.0:
                window_start = now
                message_count = 1
            else:
                message_count += 1
                if message_count > 50:
                    err_msg = make_canonical_error(1008, "Rate limit exceeded")
                    peer.send_no_fail_trigger(err_msg)
                    peer.close(1008)
                    return

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                err_msg = make_canonical_error(1008, "Invalid JSON")
                peer.send_no_fail_trigger(err_msg)
                peer.close(1008)
                return

            if handshake_payload is None:
                try:
                    msg_parsed = ClientHandshakeMessage.model_validate(data)
                    handshake_payload = msg_parsed.payload
                except ValidationError as e:
                    err_msg = make_canonical_error(1008, f"Invalid handshake schema: {str(e)}")
                    peer.send_no_fail_trigger(err_msg)
                    peer.close(1008)
                    return

                client_id = handshake_payload.client_id
                timeout_task.cancel()

                if handshake_payload.room_id != room_id:
                    err_msg = make_canonical_error(1008, "Room ID mismatch")
                    peer.send_no_fail_trigger(err_msg)
                    peer.close(1008)
                    return

                async with ROOMS_LOCK:
                    if handshake_payload.room_id not in ROOMS:
                        if len(ROOMS) >= 100:
                            err_msg = make_canonical_error(1008, "Server room limit reached")
                            peer.send_no_fail_trigger(err_msg)
                            peer.close(1008)
                            return
                        ROOMS[handshake_payload.room_id] = DuelRoom(handshake_payload.room_id, clock=clock)
                    
                    room = ROOMS[handshake_payload.room_id]

                async with room.lock:
                    if room.status == "finished":
                        handshake_ack_payload = ServerHandshakePayload(
                            room_id=room.room_id,
                            seat="player1",
                            status="finished",
                            player1_id=room.player1_id,
                            player2_id=room.player2_id
                        )
                        handshake_ack = ServerHandshakeMessage(payload=handshake_ack_payload)
                        peer.send(handshake_ack.model_dump_json())
                        peer.send(room.get_state_snapshot_text())
                        peer.close(1000)
                        return

                    if room.player1_id is None:
                        room.player1_id = client_id
                        room.player1_peer = peer
                        is_p1 = True
                        assigned_seat = "player1"
                        room.initialize_player_board(is_p1=True)
                    elif room.player2_id is None:
                        if room.player1_id == client_id:
                            err_msg = make_canonical_error(1008, "Client already in room")
                            peer.send_no_fail_trigger(err_msg)
                            peer.close(1008)
                            return
                        room.player2_id = client_id
                        room.player2_peer = peer
                        is_p1 = False
                        assigned_seat = "player2"
                        room.initialize_player_board(is_p1=False)
                    else:
                        peer.close(4001)
                        return

                    handshake_ack_payload = ServerHandshakePayload(
                        room_id=room.room_id,
                        seat=assigned_seat,
                        status=room.status,
                        player1_id=room.player1_id,
                        player2_id=room.player2_id
                    )
                    handshake_ack = ServerHandshakeMessage(payload=handshake_ack_payload)
                    peer.send(handshake_ack.model_dump_json())

                    snapshot = None
                    if room.player1_id and room.player2_id and room.status == "waiting":
                        room.status = "playing"
                        if room.room_revision < 9007199254740991:
                            room.room_revision += 1
                        room.gravity_task = asyncio.create_task(gravity_background_loop(room))
                        snapshot = room.get_state_snapshot_text()
                
                if snapshot:
                    room.broadcast_snapshot(snapshot)
                continue

            if room is None:
                peer.close(1008)
                return

            try:
                action_msg = ClientActionMessage.model_validate(data)
                action = action_msg.payload
            except ValidationError as e:
                err_msg = make_canonical_error(1008, f"Invalid action schema: {str(e)}")
                peer.send_no_fail_trigger(err_msg)
                peer.close(1008)
                return

            snapshot = None
            async with room.lock:
                now_active = room.clock.get_time()
                if is_p1:
                    room.player1_last_active_time = now_active
                else:
                    room.player2_last_active_time = now_active

                highwater = room.player1_highwater if is_p1 else room.player2_highwater
                if action.action_id <= highwater:
                    continue

                if is_p1:
                    room.player1_highwater = action.action_id
                else:
                    room.player2_highwater = action.action_id

                if room.status != "playing":
                    reason_val = "not_started" if room.status == "waiting" else "not_playing"
                    ack_payload = ServerAckPayload(
                        action_id=action.action_id,
                        status="rejected",
                        reason=reason_val,
                        board_revision=0,
                        room_revision=room.room_revision,
                        authoritative_board=room.player1_board if is_p1 and room.player1_board else (room.player2_board or room.player1_board)
                    )
                    ack_msg = ServerAckMessage(payload=ack_payload)
                    peer.send(ack_msg.model_dump_json())
                    continue

                board = room.player1_board if is_p1 else room.player2_board
                if not board or board.status == "game_over":
                    continue

                # Monotonic integer bounds preflight check
                if (room.room_revision >= 9007199254740991 or 
                    board.board_revision >= 9007199254740991 or 
                    board.score >= 9007199254740991 or 
                    board.total_lines >= 9007199254740991 or 
                    board.level >= 9007199254740991):
                    room.transition_to_finished_sync("draw", "operational-abort", now_active, delay_broadcast=True)
                    ack_payload = ServerAckPayload(
                        action_id=action.action_id,
                        status="rejected",
                        reason="integer_overflow",
                        board_revision=board.board_revision,
                        room_revision=room.room_revision,
                        authoritative_board=board
                    )
                    peer.send(ServerAckMessage(payload=ack_payload).model_dump_json())
                    
                    # Manual broadcast and close
                    snapshot_text = room.get_state_snapshot_text()
                    if room.player1_peer:
                        room.player1_peer.send_no_fail_trigger(snapshot_text)
                        room.player1_peer.close(1000)
                    if room.player2_peer:
                        room.player2_peer.send_no_fail_trigger(snapshot_text)
                        room.player2_peer.close(1000)
                    continue

                if action.expected_revision != board.board_revision:
                    status_reason = "stale revision" if action.expected_revision < board.board_revision else "future revision"
                    ack_payload = ServerAckPayload(
                        action_id=action.action_id,
                        status="rejected",
                        reason=status_reason,
                        board_revision=board.board_revision,
                        room_revision=room.room_revision,
                        authoritative_board=board
                    )
                    ack_msg = ServerAckMessage(payload=ack_payload)
                    peer.send(ack_msg.model_dump_json())
                    continue

                prev_rev = board.board_revision
                
                # Speculative preflight check of candidate action state
                board_copy = board.model_copy(deep=True)
                spec_supplier = SpeculativeSupplier(room, is_p1)
                
                if action.action_type == "move":
                    board_copy = move_game(board_copy, action.direction, spec_supplier)
                elif action.action_type == "rotate":
                    board_copy = rotate_game(board_copy, action.direction)
                elif action.action_type == "hold":
                    board_copy = hold_game(board_copy, spec_supplier)

                if is_board_overflow(board_copy) or room.room_revision + 1 >= 9007199254740991:
                    # Overflow detected on candidate! Do not commit and do not consume supplier index.
                    room.transition_to_finished_sync("draw", "operational-abort", now_active, delay_broadcast=True)
                    
                    ack_payload = ServerAckPayload(
                        action_id=action.action_id,
                        status="rejected",
                        reason="integer_overflow",
                        board_revision=board.board_revision, # previous valid revision
                        room_revision=room.room_revision,   # previous valid room revision
                        authoritative_board=board           # previous valid board
                    )
                    peer.send(ServerAckMessage(payload=ack_payload).model_dump_json())
                    
                    # Manual broadcast and close
                    snapshot_text = room.get_state_snapshot_text()
                    if room.player1_peer:
                        room.player1_peer.send_no_fail_trigger(snapshot_text)
                        room.player1_peer.close(1000)
                    if room.player2_peer:
                        room.player2_peer.send_no_fail_trigger(snapshot_text)
                        room.player2_peer.close(1000)
                    continue

                # No overflow! Now apply the action for real
                if action.action_type == "move":
                    board = move_game(board, action.direction, make_piece_supplier(room, is_p1))
                    if board.board_revision == prev_rev:
                        ack_payload = ServerAckPayload(
                            action_id=action.action_id,
                            status="noop",
                            reason="blocked",
                            board_revision=board.board_revision,
                            room_revision=room.room_revision,
                            authoritative_board=board
                        )
                        ack_msg = ServerAckMessage(payload=ack_payload)
                        peer.send(ack_msg.model_dump_json())
                    else:
                        snapshot = commit_and_ack_action_sync(room, peer, board, action, is_p1, now_active)

                elif action.action_type == "rotate":
                    board = rotate_game(board, action.direction)
                    if board.board_revision == prev_rev:
                        ack_payload = ServerAckPayload(
                            action_id=action.action_id,
                            status="noop",
                            reason="blocked" if board.active_piece and board.active_piece.type != 'O' else "no-op rotation",
                            board_revision=board.board_revision,
                            room_revision=room.room_revision,
                            authoritative_board=board
                        )
                        ack_msg = ServerAckMessage(payload=ack_payload)
                        peer.send(ack_msg.model_dump_json())
                    else:
                        snapshot = commit_and_ack_action_sync(room, peer, board, action, is_p1, now_active)

                elif action.action_type == "hold":
                    board = hold_game(board, make_piece_supplier(room, is_p1))
                    if board.board_revision == prev_rev:
                        ack_payload = ServerAckPayload(
                            action_id=action.action_id,
                            status="noop",
                            reason="blocked",
                            board_revision=board.board_revision,
                            room_revision=room.room_revision,
                            authoritative_board=board
                        )
                        ack_msg = ServerAckMessage(payload=ack_payload)
                        peer.send(ack_msg.model_dump_json())
                    else:
                        snapshot = commit_and_ack_action_sync(room, peer, board, action, is_p1, now_active)

            if snapshot:
                room.broadcast_snapshot(snapshot)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"Exception inside WebSocket handler for room {room_id}: {str(e)}")
    finally:
        timeout_task.cancel()
        if room and assigned_seat is not None:
            async with room.lock:
                if assigned_seat == "player1":
                    room.player1_peer = None
                else:
                    room.player2_peer = None

                if room.status != "finished":
                    room.handle_peer_failure_sync(is_p1, "Disconnected")

        if peer:
            await peer.drain_and_stop()
