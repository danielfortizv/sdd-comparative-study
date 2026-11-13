import pytest
import asyncio
from unittest.mock import AsyncMock
from app.services.duel_manager import DuelRoomManager, PlayerState
from app.models.schemas import WSActionMessage

def test_waiting_disconnect_releases_room():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        # Join as seat_1 (waiting state)
        await manager.join_room(room_id, ws1)
        assert room_id in manager.rooms
        assert manager.rooms[room_id]["status"] == "waiting"
        
        # Disconnect seat_1
        await manager.handle_disconnect(room_id, "seat_1")
        
        # Assert that the room has been popped and released immediately!
        assert room_id not in manager.rooms
        assert room_id not in manager.websockets
        assert room_id not in manager.gravity_tasks
        
    asyncio.run(run_test())

def test_sequence_extension_on_demand():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        room = manager.rooms[room_id]
        
        # Capture original 1000 items
        original_seq = list(room["piece_sequence"])
        assert len(original_seq) == 1000
        
        # Extend beyond 1000
        manager._ensure_piece_sequence(room, 1050)
        assert len(room["piece_sequence"]) >= 2050
        # Prefix must be byte/value identical to original prefix
        assert room["piece_sequence"][:1000] == original_seq
        
        midway_seq = list(room["piece_sequence"])
        
        # Extend beyond 2000
        manager._ensure_piece_sequence(room, 2050)
        assert len(room["piece_sequence"]) >= 3050
        # Prefix must still be completely identical
        assert room["piece_sequence"][:1000] == original_seq
        assert room["piece_sequence"][:len(midway_seq)] == midway_seq
        
        # Lagging player's original index gives the same originally assigned piece
        assert room["piece_sequence"][50] == original_seq[50]
        assert room["piece_sequence"][999] == original_seq[999]
        
    asyncio.run(run_test())

def test_duplicate_disconnect_idempotence():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        room = manager.rooms[room_id]
        assert room["status"] == "active"
        
        # Disconnect seat_1
        await manager.handle_disconnect(room_id, "seat_1")
        assert room["status"] == "finished"
        assert room["outcome"] == "seat_2_win"
        
        # Count game_over frames sent to seat_2
        go_calls = [
            args[0] for args, kwargs in ws2.send_json.call_args_list 
            if args and isinstance(args[0], dict) and args[0].get("event") == "game_over"
        ]
        assert len(go_calls) == 1
        assert go_calls[0]["payload"]["outcome"] == "seat_2_win"
        
        # Reset mock to test second disconnect
        ws2.send_json.reset_mock()
        
        # Duplicate disconnect of seat_1
        await manager.handle_disconnect(room_id, "seat_1")
        
        # Verify no more game_over frames were sent
        go_calls_duplicate = [
            args[0] for args, kwargs in ws2.send_json.call_args_list 
            if args and isinstance(args[0], dict) and args[0].get("event") == "game_over"
        ]
        assert len(go_calls_duplicate) == 0
        assert room["outcome"] == "seat_2_win"  # Outcome remains preserved
        
        # Later disconnect of seat_2
        await manager.handle_disconnect(room_id, "seat_2")
        go_calls_later = [
            args[0] for args, kwargs in ws2.send_json.call_args_list 
            if args and isinstance(args[0], dict) and args[0].get("event") == "game_over"
        ]
        assert len(go_calls_later) == 0
        assert room["outcome"] == "seat_2_win"  # Outcome remains preserved
        
    asyncio.run(run_test())

def test_strict_payload_validation_extra_fields():
    # Test that extra fields are rejected
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 1,
            "event": "action",
            "payload": {
                "seq_num": 5,
                "generation": 0,
                "action_type": "left",
                "seat": "seat_2"  # Extra forged field!
            }
        })

def test_strict_payload_validation_booleans():
    # Test that boolean types are strictly rejected for sequence numbers
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 1,
            "event": "action",
            "payload": {
                "seq_num": True,  # Boolean instead of integer!
                "generation": 0,
                "action_type": "left"
            }
        })

def test_strict_payload_validation_bounds():
    # 1. Missing version (v)
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "event": "action",
            "payload": {
                "seq_num": 1,
                "generation": 0,
                "action_type": "left"
            }
        })
        
    # 2. Version != 1
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 2,
            "event": "action",
            "payload": {
                "seq_num": 1,
                "generation": 0,
                "action_type": "left"
            }
        })
        
    # 3. seq_num lower bound (must be >= 1)
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 1,
            "event": "action",
            "payload": {
                "seq_num": 0,
                "generation": 0,
                "action_type": "left"
            }
        })
        
    # 4. generation lower bound (must be >= 0)
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 1,
            "event": "action",
            "payload": {
                "seq_num": 1,
                "generation": -1,
                "action_type": "left"
            }
        })
        
    # 5. generation upper bound (must be <= 9007199254740991)
    with pytest.raises(Exception):
        WSActionMessage.model_validate({
            "v": 1,
            "event": "action",
            "payload": {
                "seq_num": 1,
                "generation": 9007199254740992,
                "action_type": "left"
            }
        })

def test_process_action_hold_deadlock_resolution():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        # Stop automatic scheduler
        manager._cancel_room_tasks(room_id)
        
        room = manager.rooms[room_id]
        p1 = room["seat_1"]
        p2 = room["seat_2"]
        
        # Keep active pieces at row 8
        p1.active_piece.cells = [[8, 3], [8, 4], [8, 5], [8, 6]]
        p1.active_piece.origin = [8, 4]
        p2.active_piece.cells = [[8, 3], [8, 4], [8, 5], [8, 6]]
        p2.active_piece.origin = [8, 4]
        
        # Block both spawn areas (rows 0-1 filled with 1s)
        for col in range(10):
            p1.board[0][col] = 1
            p1.board[1][col] = 1
            p2.board[0][col] = 1
            p2.board[1][col] = 1
            
        # Await process_action(room, 'seat_1', 1, 0, 'hold') with a 2-second timeout.
        # Under the bug, this would deadlock/stall forever. Now it should complete immediately.
        await asyncio.wait_for(
            manager.process_action(room_id, "seat_1", 1, 0, "hold"),
            timeout=2.0
        )
        
        # Verify seat_2_win immediately
        assert room["status"] == "finished"
        assert room["outcome"] == "seat_2_win"
        assert room["reason"] == "seat_1 topped out on action"
        
        # Verify that ws2 received exactly one game_over event
        go_calls = [
            args[0] for args, kwargs in ws2.send_json.call_args_list 
            if args and isinstance(args[0], dict) and args[0].get("event") == "game_over"
        ]
        assert len(go_calls) == 1
        assert go_calls[0]["payload"]["outcome"] == "seat_2_win"
        
        # Reset mocks to test subsequent disconnect idempotence
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        
        # Trigger a later/repeated disconnect
        await manager.handle_disconnect(room_id, "seat_1")
        await manager.handle_disconnect(room_id, "seat_2")
        
        # Confirm no additional game_over event was sent
        go_calls_after = [
            args[0] for args, kwargs in ws2.send_json.call_args_list 
            if args and isinstance(args[0], dict) and args[0].get("event") == "game_over"
        ]
        assert len(go_calls_after) == 0
        assert room["outcome"] == "seat_2_win"
        
    asyncio.run(run_test())

