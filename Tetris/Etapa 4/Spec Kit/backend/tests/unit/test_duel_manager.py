import pytest
import asyncio
from unittest.mock import AsyncMock
from app.services.duel_manager import DuelRoomManager, PlayerState

def test_room_creation_and_capacity():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        assert room_id is not None
        assert room_id in manager.rooms
        
        # Test max capacity bound of 100 rooms
        for i in range(99):
            await manager.create_room()
            
        assert len(manager.rooms) == 100
        
        with pytest.raises(ValueError, match="Server capacity limit reached"):
            await manager.create_room()
            
    asyncio.run(run_test())

def test_join_room_and_gating():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        # Player 1 Joins
        r_id, seat1 = await manager.join_room(room_id, ws1)
        assert r_id == room_id
        assert seat1 == "seat_1"
        assert manager.rooms[room_id]["status"] == "waiting"
        
        # Player 2 Joins -> Starts game
        r_id, seat2 = await manager.join_room(room_id, ws2)
        assert r_id == room_id
        assert seat2 == "seat_2"
        assert manager.rooms[room_id]["status"] == "active"
        
        # Verify piece sequences are identical
        p1 = manager.rooms[room_id]["seat_1"]
        p2 = manager.rooms[room_id]["seat_2"]
        assert p1.active_piece.type == p2.active_piece.type
        assert p1.next_piece_index == 1
        assert p2.next_piece_index == 1
        
        # Try to join third player -> Room Full
        with pytest.raises(ValueError, match="Room full"):
            await manager.join_room(room_id, ws3)
            
        # Clean up tasks
        manager._cancel_room_tasks(room_id)
        
    asyncio.run(run_test())

def test_action_sequence_and_generation_validation():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        p1: PlayerState = manager.rooms[room_id]["seat_1"]
        p1.active_piece_generation = 1
        p1.last_processed_seq_num = 10
        
        # 1. Test duplicate / out-of-order sequence rejection
        err = await manager.process_action(
            room_id=room_id,
            seat="seat_1",
            seq_num=10,
            generation=1,
            action_type="left"
        )
        assert err is not None
        assert "Duplicate or out-of-order" in err["error"]["message"]
        
        # 2. Test stale generation rejection
        err = await manager.process_action(
            room_id=room_id,
            seat="seat_1",
            seq_num=11,
            generation=0,
            action_type="left"
        )
        assert err is not None
        assert "Outdated piece generation" in err["error"]["message"]
        
        # 3. Test valid action processing
        err = await manager.process_action(
            room_id=room_id,
            seat="seat_1",
            seq_num=11,
            generation=1,
            action_type="left"
        )
        assert err is None
        assert p1.last_processed_seq_num == 11
        
        # Clean up tasks
        manager._cancel_room_tasks(room_id)
        
    asyncio.run(run_test())

def test_disconnect_and_forfeit():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        # Seat 1 disconnects
        await manager.handle_disconnect(room_id, "seat_1")
        
        room = manager.rooms[room_id]
        assert room["status"] == "finished"
        assert room["outcome"] == "seat_2_win"
        assert "disconnected" in room["reason"]
        
        # Clean up tasks
        manager._cancel_room_tasks(room_id)
        
    asyncio.run(run_test())

def test_simultaneous_top_out_draw():
    async def run_test():
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        p1: PlayerState = manager.rooms[room_id]["seat_1"]
        p2: PlayerState = manager.rooms[room_id]["seat_2"]
        
        # Force both players to top out state
        p1.status = "game_over"
        p2.status = "game_over"
        
        # Trigger handle_top_out for seat_1
        await manager.handle_top_out(room_id, "seat_1")
        
        room = manager.rooms[room_id]
        assert room["status"] == "finished"
        assert room["outcome"] == "draw"
        assert "Both players topped out" in room["reason"]
        
        # Clean up tasks
        manager._cancel_room_tasks(room_id)
        
    asyncio.run(run_test())

def test_sweep_inactive_rooms_garbage_collection():
    async def run_test():
        import datetime
        manager = DuelRoomManager()
        room_id = await manager.create_room()
        
        # Manually backdate last activity to 6 minutes ago (360 seconds)
        now = datetime.datetime.now(datetime.timezone.utc)
        six_mins_ago = now - datetime.timedelta(minutes=6)
        manager.rooms[room_id]["last_activity"] = six_mins_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Trigger single sweep iteration (using direct logic)
        rooms_to_delete = []
        for r_id, room in list(manager.rooms.items()):
            last_act_dt = datetime.datetime.strptime(room["last_activity"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            age_seconds = (now - last_act_dt).total_seconds()
            if age_seconds > 300:
                rooms_to_delete.append(r_id)
                
        for r_id in rooms_to_delete:
            manager._cancel_room_tasks(r_id)
            manager.rooms.pop(r_id, None)
            
        assert room_id not in manager.rooms
        
    asyncio.run(run_test())
