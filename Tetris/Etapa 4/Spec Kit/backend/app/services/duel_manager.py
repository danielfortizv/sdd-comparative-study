import asyncio
import secrets
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from fastapi import WebSocket

from app.models.schemas import TetrominoSchema
from app.services.game_engine import (
    TROMINO_TYPES,
    TETROMINO_TEMPLATES,
    ROTATION_ORIENTATIONS,
    has_collision,
    clear_lines_in_board,
    find_current_orientation
)

logger = logging.getLogger("tetris.duel_manager")

class PlayerState:
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.board: List[List[int]] = [[0] * 10 for _ in range(20)]
        self.active_piece: Optional[TetrominoSchema] = None
        self.active_piece_generation: int = 0
        self.last_processed_seq_num: int = 0
        self.next_piece_index: int = 0
        self.hold_piece: Optional[str] = None
        self.can_hold: bool = True
        self.score: int = 0
        self.total_lines: int = 0
        self.level: int = 1
        self.status: str = "playing"  # "playing", "game_over", "disconnected"

class DuelRoomManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, Any]] = {}
        # Mapping: room_id -> { "seat_1": WebSocket, "seat_2": WebSocket }
        self.websockets: Dict[str, Dict[str, Optional[WebSocket]]] = {}
        # Mapping: room_id -> room_scheduler_task (exactly one scheduler loop per room)
        self.gravity_tasks: Dict[str, Optional[asyncio.Task]] = {}
        # Thread-safe lock for manager mutations
        self.lock = asyncio.Lock()
        # Active sweep task
        self.sweep_task: Optional[asyncio.Task] = None

    def start_sweep_task(self):
        if self.sweep_task is None:
            try:
                loop = asyncio.get_running_loop()
                self.sweep_task = loop.create_task(self.sweep_inactive_rooms())
            except RuntimeError:
                pass

    async def create_room(self, room_id: Optional[str] = None) -> str:
        # Lazy start sweep task if not already running
        self.start_sweep_task()
        async with self.lock:
            # Enforce server capacity limit of 100 rooms
            if len(self.rooms) >= 100:
                raise ValueError("Server capacity limit reached: Max 100 active rooms")

            if not room_id:
                room_id = secrets.token_hex(16)
            
            if room_id in self.rooms:
                return room_id

            # Pre-generate 1000 piece sequence
            piece_sequence = [secrets.choice(TROMINO_TYPES) for _ in range(1000)]
            
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.rooms[room_id] = {
                "room_id": room_id,
                "status": "waiting",  # "waiting", "active", "finished"
                "seat_1": None,
                "seat_2": None,
                "piece_sequence": piece_sequence,
                "last_action_seat": None,
                "last_action_seq": None,
                "last_action_observable_change": False,
                "created_at": now_iso,
                "last_activity": now_iso,
                "revision": 0,
                "outcome": None,
                "reason": None
            }
            self.websockets[room_id] = {"seat_1": None, "seat_2": None}
            self.gravity_tasks[room_id] = None
            logger.info(f"Duel Room {room_id} created successfully.")
            return room_id

    async def join_room(self, room_id: str, websocket: WebSocket) -> Tuple[str, str]:
        """
        Attempts to join a room. Returns (room_id, assigned_seat).
        Raises ValueError with custom messages on failure.
        """
        async with self.lock:
            if room_id not in self.rooms:
                raise ValueError("Room not found")

            room = self.rooms[room_id]
            if room["status"] == "finished":
                raise ValueError("Room already finished")

            if room["seat_1"] is None:
                seat = "seat_1"
            elif room["seat_2"] is None:
                seat = "seat_2"
            else:
                raise ValueError("Room full")

            player_id = secrets.token_hex(16)
            player_state = PlayerState(player_id)
            room[seat] = player_state
            self.websockets[room_id][seat] = websocket
            
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            room["last_activity"] = now_iso

            logger.info(f"Player {player_id} joined room {room_id} as {seat}")

            # If both seats are filled, start the match!
            if room["seat_1"] is not None and room["seat_2"] is not None:
                room["status"] = "active"
                # Initialize active pieces for both seats using identical sequence
                p1: PlayerState = room["seat_1"]
                p2: PlayerState = room["seat_2"]
                
                seq = room["piece_sequence"]
                
                # Seat 1 spawn
                spawn_type = seq[0]
                template = TETROMINO_TEMPLATES[spawn_type]
                p1.active_piece = TetrominoSchema(
                    type=spawn_type,
                    cells=template["cells"],
                    origin=template["origin"]
                )
                p1.next_piece_index = 1
                p1.active_piece_generation = 0
                
                # Seat 2 spawn
                p2.active_piece = TetrominoSchema(
                    type=spawn_type,
                    cells=template["cells"],
                    origin=template["origin"]
                )
                p2.next_piece_index = 1
                p2.active_piece_generation = 0

                # Start the single room scheduler loop for both seats
                self.gravity_tasks[room_id] = asyncio.create_task(
                    self.room_scheduler_loop(room_id)
                )
                logger.info(f"Duel Match in Room {room_id} started! Single room scheduler active.")

            return room_id, seat

    def _ensure_piece_sequence(self, room: Dict[str, Any], index: int):
        seq = room["piece_sequence"]
        if index >= len(seq):
            needed = (index + 1000) - len(seq)
            if needed > 0:
                if "rng" not in room:
                    import random
                    import secrets
                    room["rng"] = random.Random(secrets.randbits(128))
                rng = room["rng"]
                room["piece_sequence"].extend(rng.choice(TROMINO_TYPES) for _ in range(needed))

    async def get_room_snapshot(self, room_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return None
            return self._serialize_room(room)

    def _serialize_seat(self, seat_state: Optional[PlayerState], piece_sequence: List[str]) -> Optional[Dict[str, Any]]:
        if not seat_state:
            return None
        
        # Calculate preview next_piece type
        next_piece = piece_sequence[seat_state.next_piece_index] if seat_state.next_piece_index < len(piece_sequence) else "I"
        
        return {
            "player_id": seat_state.player_id,
            "board": seat_state.board,
            "active_piece": {
                "type": seat_state.active_piece.type,
                "cells": seat_state.active_piece.cells,
                "origin": seat_state.active_piece.origin
            } if seat_state.active_piece else None,
            "active_piece_generation": seat_state.active_piece_generation,
            "last_processed_seq_num": seat_state.last_processed_seq_num,
            "score": seat_state.score,
            "total_lines": seat_state.total_lines,
            "level": seat_state.level,
            "status": seat_state.status,
            "next_piece": next_piece,
            "hold_piece": seat_state.hold_piece,
            "can_hold": seat_state.can_hold
        }

    def _serialize_room(self, room: Dict[str, Any]) -> Dict[str, Any]:
        for seat_name in ["seat_1", "seat_2"]:
            seat_state = room.get(seat_name)
            if seat_state:
                self._ensure_piece_sequence(room, seat_state.next_piece_index)
        return {
            "room_id": room["room_id"],
            "status": room["status"],
            "last_action_seat": room["last_action_seat"],
            "last_action_seq": room["last_action_seq"],
            "last_action_observable_change": room["last_action_observable_change"],
            "seat_1": self._serialize_seat(room["seat_1"], room["piece_sequence"]),
            "seat_2": self._serialize_seat(room["seat_2"], room["piece_sequence"]),
            "outcome": room["outcome"],
            "reason": room["reason"]
        }

    async def broadcast_state(self, room_id: str):
        room = self.rooms.get(room_id)
        if not room:
            return

        room["revision"] += 1
        serialized = self._serialize_room(room)
        
        payload = {
            "v": 1,
            "event": "state_update",
            "payload": {
                "revision": room["revision"],
                **serialized
            }
        }

        sockets = self.websockets.get(room_id, {})
        for seat, ws in list(sockets.items()):
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass

    async def broadcast_game_over(self, room_id: str, outcome: str, reason: str):
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return
            if room.get("game_over_sent"):
                return
            room["game_over_sent"] = True

        payload = {
            "v": 1,
            "event": "game_over",
            "payload": {
                "outcome": outcome,
                "reason": reason
            }
        }
        sockets = self.websockets.get(room_id, {})
        for seat, ws in list(sockets.items()):
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass

    async def room_scheduler_loop(self, room_id: str):
        """
        Single room scheduler tracking independently due times per seat,
        evaluating due gravity ticks atomically in one single batch.
        """
        loop = asyncio.get_running_loop()
        next_due = {}
        
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room or room["status"] != "active":
                return
            for seat in ["seat_1", "seat_2"]:
                p_state = room[seat]
                if p_state and p_state.status == "playing":
                    interval_ms = max(100, 500 - 50 * (p_state.level - 1))
                    next_due[seat] = loop.time() + (interval_ms / 1000.0)
                else:
                    next_due[seat] = float('inf')

        try:
            while True:
                now = loop.time()
                min_due = min(next_due.get("seat_1", float('inf')), next_due.get("seat_2", float('inf')))
                if min_due == float('inf'):
                    break
                
                sleep_time = max(0.001, min_due - now)
                await asyncio.sleep(sleep_time)

                now = loop.time()
                due_seats = []
                topped_out_batch = []
                should_broadcast = False

                async with self.lock:
                    room = self.rooms.get(room_id)
                    if not room or room["status"] != "active":
                        break

                    for seat in ["seat_1", "seat_2"]:
                        p_state = room[seat]
                        if p_state and p_state.status == "playing":
                            if now >= next_due[seat]:
                                due_seats.append(seat)
                        else:
                            next_due[seat] = float('inf')

                    if not due_seats:
                        continue

                    # Process all due seats in one atomic batch
                    for seat in due_seats:
                        p_state = room[seat]
                        active = p_state.active_piece
                        if not active:
                            continue

                        proposed_cells = [[r + 1, c] for r, c in active.cells]
                        proposed_origin = [active.origin[0] + 1, active.origin[1]]

                        if not has_collision(p_state.board, proposed_cells):
                            active.cells = proposed_cells
                            active.origin = proposed_origin
                            should_broadcast = True
                        else:
                            # Lock piece and spawn next
                            color_id = TETROMINO_TEMPLATES[active.type]["color"]
                            for r, c in active.cells:
                                if 0 <= r <= 19 and 0 <= c <= 9:
                                    p_state.board[r][c] = color_id

                            cleared = clear_lines_in_board(p_state.board)
                            level_before = p_state.level
                            score_award = {1: 100, 2: 300, 3: 500, 4: 800}.get(cleared, 0) * level_before
                            p_state.score += score_award
                            p_state.total_lines += cleared
                            p_state.level = 1 + p_state.total_lines // 10
                            p_state.can_hold = True

                            # Spawn next piece
                            next_idx = p_state.next_piece_index
                            self._ensure_piece_sequence(room, next_idx)
                            spawn_type = room["piece_sequence"][next_idx]
                            p_state.next_piece_index += 1

                            template = TETROMINO_TEMPLATES[spawn_type]
                            p_state.active_piece_generation += 1

                            if has_collision(p_state.board, template["cells"]):
                                p_state.status = "game_over"
                                p_state.active_piece = None
                                topped_out_batch.append(seat)
                            else:
                                p_state.active_piece = TetrominoSchema(
                                    type=spawn_type,
                                    cells=template["cells"],
                                    origin=template["origin"]
                                )
                            should_broadcast = True

                        if p_state.status == "playing":
                            interval_ms = max(100, 500 - 50 * (p_state.level - 1))
                            next_due[seat] = loop.time() + (interval_ms / 1000.0)
                        else:
                            next_due[seat] = float('inf')

                    # If anyone topped out in this batch, finish the match immediately
                    if topped_out_batch:
                        room["status"] = "finished"
                        self._cancel_room_tasks(room_id)
                        
                        # Preserve action correlation on gravity updates
                        room["last_action_seat"] = "system"
                        room["last_action_seq"] = None
                        room["last_action_observable_change"] = True

                        if len(topped_out_batch) == 2:
                            room["outcome"] = "draw"
                            room["reason"] = "Both players topped out within the same tick loop iteration"
                        else:
                            topped_out_seat = topped_out_batch[0]
                            surviving_seat = "seat_2" if topped_out_seat == "seat_1" else "seat_1"
                            room["outcome"] = f"{surviving_seat}_win"
                            room["reason"] = f"{topped_out_seat} topped out under gravity"

                # Out of lock, broadcast updates
                if topped_out_batch:
                    await self.broadcast_state(room_id)
                    await self.broadcast_game_over(room_id, room["outcome"], room["reason"])
                    break
                elif should_broadcast:
                    # Preserve action correlation on gravity updates
                    async with self.lock:
                        room = self.rooms.get(room_id)
                        if room:
                            room["last_action_seat"] = "system"
                            room["last_action_seq"] = None
                            room["last_action_observable_change"] = True
                    await self.broadcast_state(room_id)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Exception in room scheduler loop for {room_id}")

    def _cancel_room_tasks(self, room_id: str):
        task = self.gravity_tasks.get(room_id)
        if task:
            task.cancel()
        self.gravity_tasks[room_id] = None

    async def handle_top_out(self, room_id: str, topped_out_seat: str):
        """
        Backward-compatibility helper for testing top-out outcomes in unit tests.
        """
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room or room["status"] != "active":
                return

            seat_1_state: PlayerState = room["seat_1"]
            seat_2_state: PlayerState = room["seat_2"]

            s1_go = seat_1_state.status == "game_over"
            s2_go = seat_2_state.status == "game_over"

            if s1_go and s2_go:
                room["status"] = "finished"
                room["outcome"] = "draw"
                room["reason"] = "Both players topped out within the same tick loop iteration"
            elif topped_out_seat == "seat_1":
                room["status"] = "finished"
                room["outcome"] = "seat_2_win"
                room["reason"] = "seat_1 topped out under gravity"
            else:
                room["status"] = "finished"
                room["outcome"] = "seat_1_win"
                room["reason"] = "seat_2 topped out under gravity"

            self._cancel_room_tasks(room_id)

        await self.broadcast_state(room_id)
        await self.broadcast_game_over(room_id, room["outcome"], room["reason"])

    async def process_action(self, room_id: str, seat: str, seq_num: int, generation: int, action_type: str) -> Optional[Dict[str, Any]]:
        """
        Thread-safe authoritative processing of a client action.
        Returns None on success or an error dictionary on rejection/conflict.
        """
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return {"error": {"code": 404, "message": "Room not found"}}

            if room["status"] != "active":
                return {"error": {"code": 400, "message": "Room not active"}}

            p_state: PlayerState = room[seat]
            if not p_state or p_state.status != "playing":
                return {"error": {"code": 400, "message": "Player status is not playing"}}

            # Monotonic sequence check
            if seq_num <= p_state.last_processed_seq_num:
                return {"error": {"code": 409, "message": "Conflict/Stale Action: Duplicate or out-of-order sequence number"}}

            # Generation stale action check
            if generation != p_state.active_piece_generation:
                return {"error": {"code": 409, "message": "Conflict/Stale Action: Outdated piece generation"}}

            # Update seq num
            p_state.last_processed_seq_num = seq_num

            # Update last activity
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            room["last_activity"] = now_iso

            active = p_state.active_piece
            if not active:
                return {"error": {"code": 400, "message": "No active piece"}}

            cells = active.cells
            origin = active.origin
            observable_change = False

            if action_type == "left":
                proposed_cells = [[r, c - 1] for r, c in cells]
                proposed_origin = [origin[0], origin[1] - 1]
                if not has_collision(p_state.board, proposed_cells):
                    active.cells = proposed_cells
                    active.origin = proposed_origin
                    observable_change = True
            elif action_type == "right":
                proposed_cells = [[r, c + 1] for r, c in cells]
                proposed_origin = [origin[0], origin[1] + 1]
                if not has_collision(p_state.board, proposed_cells):
                    active.cells = proposed_cells
                    active.origin = proposed_origin
                    observable_change = True
            elif action_type == "down":
                proposed_cells = [[r + 1, c] for r, c in cells]
                proposed_origin = [origin[0] + 1, origin[1]]
                if not has_collision(p_state.board, proposed_cells):
                    active.cells = proposed_cells
                    active.origin = proposed_origin
                    observable_change = True
            elif action_type in ("cw", "ccw"):
                if active.type != "O":
                    current_o = find_current_orientation(active.type, cells, origin)
                    if action_type == "cw":
                        new_o = (current_o + 1) % 4
                    else:
                        new_o = (current_o - 1) % 4

                    new_offsets = ROTATION_ORIENTATIONS[active.type][new_o]
                    for dx in (0, -1, 1, -2, 2):
                        proposed_cells = [[origin[0] + offset_r, origin[1] + offset_c + dx] for offset_r, offset_c in new_offsets]
                        proposed_origin = [origin[0], origin[1] + dx]

                        if not has_collision(p_state.board, proposed_cells):
                            active.cells = proposed_cells
                            active.origin = proposed_origin
                            observable_change = True
                            break
            elif action_type == "hold":
                if p_state.can_hold:
                    if p_state.hold_piece is None:
                        p_state.hold_piece = active.type
                        next_idx = p_state.next_piece_index
                        self._ensure_piece_sequence(room, next_idx)
                        spawn_type = room["piece_sequence"][next_idx]
                        p_state.next_piece_index += 1
                    else:
                        old_hold = p_state.hold_piece
                        p_state.hold_piece = active.type
                        spawn_type = old_hold

                    template = TETROMINO_TEMPLATES[spawn_type]
                    p_state.active_piece_generation += 1
                    
                    if has_collision(p_state.board, template["cells"]):
                        p_state.status = "game_over"
                        p_state.active_piece = None
                        observable_change = True
                    else:
                        p_state.active_piece = TetrominoSchema(
                            type=spawn_type,
                            cells=template["cells"],
                            origin=template["origin"]
                        )
                        observable_change = True
                    
                    p_state.can_hold = False

            # Update action tracking attributes for WS client verification
            room["last_action_seat"] = seat
            room["last_action_seq"] = seq_num
            room["last_action_observable_change"] = observable_change

            # Synchronously decide the winner immediately on action-induced top-out (no delay)
            is_game_over = (p_state.status == "game_over")
            if is_game_over:
                room["status"] = "finished"
                surviving_seat = "seat_2" if seat == "seat_1" else "seat_1"
                room["outcome"] = f"{surviving_seat}_win"
                room["reason"] = f"{seat} topped out on action"
                self._cancel_room_tasks(room_id)
                outcome = room["outcome"]
                reason = room["reason"]

        if is_game_over:
            await self.broadcast_state(room_id)
            await self.broadcast_game_over(room_id, outcome, reason)
            return None

        # Broadcast state to both players
        await self.broadcast_state(room_id)
        return None

    async def handle_disconnect(self, room_id: str, seat: str):
        """
        Handles websocket drop. Instantly forfeits the disconnecting seat,
        transitioning the parent room status to finished, reporting forfeit win
        to the surviving player.
        """
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return

            p_state = room[seat]
            if p_state:
                p_state.status = "disconnected"

            self.websockets[room_id][seat] = None

            if room["status"] == "active":
                room["status"] = "finished"
                surviving_seat = "seat_2" if seat == "seat_1" else "seat_1"
                room["outcome"] = f"{surviving_seat}_win"
                room["reason"] = f"{seat} disconnected/forfeited"
                self._cancel_room_tasks(room_id)

            elif room["status"] == "waiting":
                # Player left while waiting: clear the seat
                room[seat] = None
                self.websockets[room_id][seat] = None
                if room["seat_1"] is None and room["seat_2"] is None:
                    # Release waiting room immediately on sole player disconnect
                    self.rooms.pop(room_id, None)
                    self.websockets.pop(room_id, None)
                    self.gravity_tasks.pop(room_id, None)
                    logger.info(f"Released waiting room {room_id} immediately on sole player disconnect")
                    return

        await self.broadcast_state(room_id)
        if room["status"] == "finished":
            await self.broadcast_game_over(room_id, room["outcome"], room["reason"])

    async def sweep_inactive_rooms(self):
        """
        Runs every 60 seconds. Checks for room inactivity (5 minutes).
        Cancels gravity futures, closes websockets, and releases room resources.
        """
        while True:
            await asyncio.sleep(60)
            async with self.lock:
                rooms_to_delete = []
                now = datetime.now(timezone.utc)
                for room_id, room in list(self.rooms.items()):
                    last_act_dt = datetime.strptime(room["last_activity"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    age_seconds = (now - last_act_dt).total_seconds()
                    
                    # Sweep if inactive for 5 minutes or finished and inactive for 1 minute
                    if age_seconds > 300 or (room["status"] == "finished" and age_seconds > 60):
                        rooms_to_delete.append(room_id)

                for room_id in rooms_to_delete:
                    logger.info(f"Sweeping inactive duel room {room_id}")
                    # Cancel any active tasks
                    self._cancel_room_tasks(room_id)
                    # Close sockets if they are still connected
                    sockets = self.websockets.pop(room_id, {})
                    for seat, ws in sockets.items():
                        if ws:
                            try:
                                await ws.close(code=4008, reason="Idle Timeout")
                            except Exception:
                                pass
                    self.rooms.pop(room_id, None)
                    self.gravity_tasks.pop(room_id, None)

    async def close_all_rooms(self):
        """
        Closes all active and waiting rooms, cancelling tasks and closing all websockets on app shutdown.
        """
        async with self.lock:
            # Cancel sweep task
            if self.sweep_task:
                self.sweep_task.cancel()
                self.sweep_task = None
            
            # Cancel all room tasks
            for room_id in list(self.rooms.keys()):
                self._cancel_room_tasks(room_id)
                sockets = self.websockets.pop(room_id, {})
                for seat, ws in sockets.items():
                    if ws:
                        try:
                            await ws.close(code=1001, reason="Server Shutdown")
                        except Exception:
                            pass
            self.rooms.clear()
            self.gravity_tasks.clear()