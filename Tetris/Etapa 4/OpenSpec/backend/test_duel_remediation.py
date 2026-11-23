import pytest
import asyncio
from fastapi.websockets import WebSocket
from unittest.mock import AsyncMock, MagicMock, patch
from backend.duel import (
    DuelGameSession,
    DuelPlayer,
    DuelRoom,
    evaluate_room_outcome,
    broadcast_room_update,
    update_room_gravity,
    room_gravity_loop,
    DuelRoomManager
)

def test_duel_game_session_hold_branches():
    # 1. Hold when game is over (should return False)
    sess = DuelGameSession(session_id="test", seed=42)
    sess.status = "game_over"
    assert sess.hold() is False

    # 2. Hold when can_hold is False (should return False)
    sess2 = DuelGameSession(session_id="test2", seed=42)
    sess2.can_hold = False
    assert sess2.hold() is False

    # 3. Successful hold first time (hold_piece is None)
    sess3 = DuelGameSession(session_id="test3", seed=42)
    original_active = sess3.active_piece.type
    original_next = sess3.next_piece
    assert sess3.hold() is True
    assert sess3.hold_piece == original_active
    assert sess3.can_hold is False

    # 4. Swap hold piece when hold_piece is not None
    sess3.can_hold = True
    active_before_swap = sess3.active_piece.type
    assert sess3.hold() is True
    assert sess3.hold_piece == active_before_swap
    assert sess3.active_piece.type == original_active

    # 5. Spawn collision on hold
    sess4 = DuelGameSession(session_id="test4", seed=42)
    # Fill the board to guarantee spawn collision (game over)
    for r in range(20):
        for c in range(10):
            sess4.board[r][c] = "I"
    assert sess4.hold() is True
    assert sess4.status == "game_over"
    assert sess4.can_hold is False


def test_evaluate_room_outcome_edge_cases():
    room = DuelRoom(room_id="room1", seed=100)
    
    # 1. Status already finished (no-op)
    room.status = "finished"
    evaluate_room_outcome(room)
    assert room.status == "finished"

    # 2. No players in room (should return early)
    room.status = "playing"
    evaluate_room_outcome(room)
    assert room.status == "playing"

    # 3. Only one player (should return early)
    p1 = MagicMock()
    p1.player_id = "p1"
    p1.seat = 1
    p1.session = DuelGameSession(session_id="p1", seed=10)
    room.players["p1"] = p1
    evaluate_room_outcome(room)
    assert room.status == "playing"

    # 4. Both players playing (no-op)
    p2 = MagicMock()
    p2.player_id = "p2"
    p2.seat = 2
    p2.session = DuelGameSession(session_id="p2", seed=10)
    room.players["p2"] = p2
    evaluate_room_outcome(room)
    assert room.status == "playing"

    # 5. Outcome survivor: P1 game_over, P2 playing -> P2 wins
    p1.session.status = "game_over"
    p2.session.status = "playing"
    evaluate_room_outcome(room)
    assert room.status == "finished"
    assert room.winner_id == "p2"
    assert room.loser_id == "p1"
    assert room.is_draw is False
    assert room.reason == "top_out"

    # 6. Outcome survivor: P1 playing, P2 game_over -> P1 wins
    room.status = "playing"
    p1.session.status = "playing"
    p2.session.status = "game_over"
    evaluate_room_outcome(room)
    assert room.status == "finished"
    assert room.winner_id == "p1"
    assert room.loser_id == "p2"
    assert room.is_draw is False
    assert room.reason == "top_out"


@pytest.mark.anyio
async def test_broadcast_room_update_failures():
    # Mock DuelRoom
    room = DuelRoom(room_id="room1", seed=100)
    
    # Create two players with mock WebSockets
    p1_ws = MagicMock()
    p1_ws.send_text = AsyncMock()
    p1 = DuelPlayer(player_id="p1", ws=p1_ws, seat=1, seed=10)
    
    p2_ws = MagicMock()
    p2_ws.send_text = AsyncMock()
    p2_ws.send_text.side_effect = Exception("Connection lost")
    p2 = DuelPlayer(player_id="p2", ws=p2_ws, seat=2, seed=10)
    
    room.players["p1"] = p1
    room.players["p2"] = p2

    # 1. Finished room broadcast (should try sending to all and handle exceptions silently)
    room.status = "finished"
    room.winner_id = "p1"
    room.loser_id = "p2"
    room.reason = "top_out"
    await broadcast_room_update(room)
    p1_ws.send_text.assert_called()
    p2_ws.send_text.assert_called()

    # Reset mocks
    p1_ws.send_text.reset_mock()
    p2_ws.send_text.reset_mock()

    # 2. State broadcast (should send to all and handle exception silently)
    room.status = "playing"
    await broadcast_room_update(room)
    p1_ws.send_text.assert_called()
    p2_ws.send_text.assert_called()

    # 3. Outer exception trigger in broadcast_room_update
    # We mock room.type or similar to raise AttributeError to enter outer exception block
    bad_room = MagicMock()
    bad_room.status = "playing"
    bad_room.players = "not-a-dict-raises-attribute-error" # will raise AttributeError on .values()
    with pytest.raises(Exception):
        await broadcast_room_update(bad_room)


def test_update_room_gravity_edge_cases():
    # No players or 1 player in room
    room = DuelRoom(room_id="room1", seed=100)
    assert update_room_gravity(room, 10.0) is False

    # Add players
    p1 = DuelPlayer(player_id="p1", ws=MagicMock(), seat=1, seed=10)
    p2 = DuelPlayer(player_id="p2", ws=MagicMock(), seat=2, seed=10)
    room.players["p1"] = p1
    room.players["p2"] = p2

    # Set gravity tick time to future -> no update
    p1.next_gravity_tick_time = 20.0
    p2.next_gravity_tick_time = 20.0
    assert update_room_gravity(room, 10.0) is False


@pytest.mark.anyio
async def test_room_gravity_loop_and_cancellation():
    # Setup room
    room = DuelRoom(room_id="room1", seed=100)
    p1 = DuelPlayer(player_id="p1", ws=MagicMock(), seat=1, seed=10)
    p2 = DuelPlayer(player_id="p2", ws=MagicMock(), seat=2, seed=10)
    room.players["p1"] = p1
    room.players["p2"] = p2
    room.status = "playing"

    # Start loop in background
    task = asyncio.create_task(room_gravity_loop(room))
    await asyncio.sleep(0.02) # let it run a bit
    
    # Cancel task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.anyio
async def test_room_manager_limits_and_sweeper():
    manager = DuelRoomManager(clock_func=lambda: 500.0)
    
    # 1. 100 rooms cap
    manager.rooms = {f"room_{i}": DuelRoom(f"room_{i}", 42) for i in range(100)}
    new_room = manager.get_or_create_room("extra_room")
    assert new_room is None

    # Reset rooms
    manager.rooms.clear()

    # 2. Sweeper for finished and inactive rooms
    # Room 1: finished room, finished_at is 100s ago (should be swept)
    r1 = DuelRoom("r1", 100, clock_func=lambda: 500.0)
    r1.status = "finished"
    r1.finished_at = 400.0
    
    # Use real background tasks
    async def dummy():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass
    r1.gravity_task = asyncio.create_task(dummy())

    # Room 2: finished room, finished_at is recent (should NOT be swept)
    r2 = DuelRoom("r2", 100, clock_func=lambda: 500.0)
    r2.status = "finished"
    r2.finished_at = 490.0
    # Room 3: active room, last_input_time is recent (should NOT be swept)
    r3 = DuelRoom("r3", 100, clock_func=lambda: 500.0)
    r3.status = "playing"
    r3.last_input_time = 490.0
    # Room 4: inactive room, last_input_time is 300s ago (should be swept)
    r4 = DuelRoom("r4", 100, clock_func=lambda: 500.0)
    r4.status = "playing"
    r4.last_input_time = 200.0
    r4.gravity_task = asyncio.create_task(dummy())

    # Add players with mock WebSocket to close
    ws1 = MagicMock()
    ws1.close = AsyncMock()
    p1 = DuelPlayer("p1", ws1, 1, 10)
    r1.players["p1"] = p1

    ws4 = MagicMock()
    ws4.close = AsyncMock()
    p4 = DuelPlayer("p4", ws4, 1, 10)
    r4.players["p4"] = p4

    manager.rooms = {
        "r1": r1,
        "r2": r2,
        "r3": r3,
        "r4": r4
    }

    # Cover asyncio.current_task throwing an exception in sweep_rooms
    with patch("asyncio.current_task", side_effect=Exception("Failed task retrieval")):
        await manager.sweep_rooms()

    assert "r1" not in manager.rooms
    assert "r2" in manager.rooms
    assert "r3" in manager.rooms
    assert "r4" not in manager.rooms

    ws1.close.assert_called()
    ws4.close.assert_called()


@pytest.mark.anyio
async def test_room_manager_sweeper_loop_cancel():
    manager = DuelRoomManager()
    
    # Start loop in background
    task = asyncio.create_task(manager.sweep_rooms_loop(interval=0.01))
    await asyncio.sleep(0.03)
    
    # Cancel loop
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.anyio
async def test_room_manager_handle_disconnect_edge_cases():
    manager = DuelRoomManager()
    
    # 1. Disconnect on finished room (should return early)
    r1 = DuelRoom("r1", 100)
    r1.status = "finished"
    await manager.handle_disconnect(r1, "p1")
    
    # 2. Disconnect on non-existent player
    r2 = DuelRoom("r2", 100)
    r2.status = "playing"
    await manager.handle_disconnect(r2, "non_existent")
    assert r2.status == "playing"

    # 3. Disconnect when only 1 player is in the room
    r3 = DuelRoom("r3", 100)
    r3.status = "playing"
    p1 = DuelPlayer("p1", MagicMock(), 1, 10)
    r3.players["p1"] = p1
    
    async def dummy():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass
    r3.gravity_task = asyncio.create_task(dummy())
    
    # Mock current_task to raise Exception
    with patch("asyncio.current_task", side_effect=Exception("Failed current_task")):
        await manager.handle_disconnect(r3, "p1")
    assert r3.status == "finished"
    assert r3.reason == "forfeit"


@pytest.mark.anyio
async def test_room_manager_shutdown_coverage():
    manager = DuelRoomManager()
    room = DuelRoom("room1", 42)
    room.status = "playing"
    
    # Add a real gravity task to room
    async def dummy():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass
    room.gravity_task = asyncio.create_task(dummy())
    
    # Add players
    ws1 = MagicMock()
    ws1.close = AsyncMock()
    p1 = DuelPlayer("p1", ws1, 1, 42)
    room.players["p1"] = p1
    manager.rooms["room1"] = room
    
    # Mock current_task exception inside shutdown
    with patch("asyncio.current_task", side_effect=Exception("mock error")):
        await manager.shutdown()
        
    assert len(manager.rooms) == 0
    ws1.close.assert_called_once()
