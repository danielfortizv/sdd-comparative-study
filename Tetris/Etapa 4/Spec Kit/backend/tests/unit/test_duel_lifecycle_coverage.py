import pytest
import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.duel_manager import DuelRoomManager, PlayerState

def test_sweep_inactive_rooms_lifecycle():
    async def run_test():
        manager = DuelRoomManager()
        
        # Setup rooms with synthetic ages
        # Room 1: Expired active (>300s) -> should be deleted
        r1 = await manager.create_room()
        manager.rooms[r1]["status"] = "active"
        
        # Room 2: Expired finished (>60s) -> should be deleted
        r2 = await manager.create_room()
        manager.rooms[r2]["status"] = "finished"
        
        # Room 3: Fresh active (<=300s) -> should be kept
        r3 = await manager.create_room()
        manager.rooms[r3]["status"] = "active"
        
        # Room 4: Fresh finished (<=60s) -> should be kept
        r4 = await manager.create_room()
        manager.rooms[r4]["status"] = "finished"
        
        # Room 5: Expired waiting (>300s) -> should be deleted
        r5 = await manager.create_room()
        manager.rooms[r5]["status"] = "waiting"
        
        # Room 6: Fresh waiting (<=300s) -> should be kept
        r6 = await manager.create_room()
        manager.rooms[r6]["status"] = "waiting"

        now = datetime.datetime.now(datetime.timezone.utc)
        
        def fmt_dt(dt):
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        manager.rooms[r1]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=305))
        manager.rooms[r2]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=65))
        manager.rooms[r3]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=295))
        manager.rooms[r4]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=55))
        manager.rooms[r5]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=305))
        manager.rooms[r6]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=10))

        # Add mock websockets
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        # ws3 is a failing socket to verify remaining cleanup occurs anyway
        ws3 = AsyncMock()
        ws3.close.side_effect = Exception("Socket close error")
        
        manager.websockets[r1] = {"seat_1": ws1, "seat_2": None}
        manager.websockets[r2] = {"seat_1": None, "seat_2": ws2}
        manager.websockets[r5] = {"seat_1": ws3, "seat_2": None}

        # Add mock gravity tasks to cancel
        task1 = MagicMock()
        task2 = MagicMock()
        task5 = MagicMock()
        
        manager.gravity_tasks[r1] = task1
        manager.gravity_tasks[r2] = task2
        manager.gravity_tasks[r5] = task5

        # Run sweep using patched asyncio.sleep to run exactly once
        sleep_calls = 0
        async def mock_sleep(secs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls > 1:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            try:
                await manager.sweep_inactive_rooms()
            except asyncio.CancelledError:
                pass

        # Assertions
        # Deleted rooms: r1, r2, r5
        assert r1 not in manager.rooms
        assert r2 not in manager.rooms
        assert r5 not in manager.rooms
        
        # Kept rooms: r3, r4, r6
        assert r3 in manager.rooms
        assert r4 in manager.rooms
        assert r6 in manager.rooms

        # Check WebSocket close calls
        ws1.close.assert_called_once_with(code=4008, reason="Idle Timeout")
        ws2.close.assert_called_once_with(code=4008, reason="Idle Timeout")
        ws3.close.assert_called_once_with(code=4008, reason="Idle Timeout")

        # Check gravity tasks cancellation
        task1.cancel.assert_called_once()
        task2.cancel.assert_called_once()
        task5.cancel.assert_called_once()

        # Repeat a sweep to check no duplicate close
        ws1.close.reset_mock()
        ws2.close.reset_mock()
        ws3.close.reset_mock()
        
        # Change r3 to expired now
        manager.rooms[r3]["last_activity"] = fmt_dt(now - datetime.timedelta(seconds=305))
        ws_r3 = AsyncMock()
        manager.websockets[r3] = {"seat_1": ws_r3, "seat_2": None}
        task3 = MagicMock()
        manager.gravity_tasks[r3] = task3
        
        sleep_calls = 0
        with patch("asyncio.sleep", side_effect=mock_sleep):
            try:
                await manager.sweep_inactive_rooms()
            except asyncio.CancelledError:
                pass
                
        assert r3 not in manager.rooms
        ws_r3.close.assert_called_once_with(code=4008, reason="Idle Timeout")
        task3.cancel.assert_called_once()
        
        # Ensure previous closed websockets were not closed again
        ws1.close.assert_not_called()
        ws2.close.assert_not_called()
        ws3.close.assert_not_called()

    asyncio.run(run_test())

def test_close_all_rooms_cleanup():
    async def run_test():
        manager = DuelRoomManager()
        
        # 1. First cover already-empty manager
        assert manager.sweep_task is None
        await manager.close_all_rooms()
        assert len(manager.rooms) == 0
        assert len(manager.gravity_tasks) == 0
        
        # 2. Setup manager with some rooms, sockets, gravity tasks, and a live sweep task
        sweep_task_mock = MagicMock()
        manager.sweep_task = sweep_task_mock
        
        r1 = await manager.create_room()
        r2 = await manager.create_room()
        
        # Add websockets (one ws will raise exception)
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.close.side_effect = Exception("Shutdown close failed")
        
        manager.websockets[r1] = {"seat_1": ws1, "seat_2": None}
        manager.websockets[r2] = {"seat_1": None, "seat_2": ws2}
        
        # Add gravity tasks
        task1 = MagicMock()
        task2 = MagicMock()
        manager.gravity_tasks[r1] = task1
        manager.gravity_tasks[r2] = task2
        
        # Run close_all_rooms
        await manager.close_all_rooms()
        
        # Assert sweep task was canceled and reset to None
        sweep_task_mock.cancel.assert_called_once()
        assert manager.sweep_task is None
        
        # Assert room gravity tasks were canceled
        task1.cancel.assert_called_once()
        task2.cancel.assert_called_once()
        
        # Assert sockets closed with 1001/ServerShutdown
        ws1.close.assert_called_once_with(code=1001, reason="Server Shutdown")
        ws2.close.assert_called_once_with(code=1001, reason="Server Shutdown")
        
        # Assert rooms/websockets/tasks cleared
        assert len(manager.rooms) == 0
        assert len(manager.gravity_tasks) == 0

    asyncio.run(run_test())

def test_get_room_snapshot_behavior():
    async def run_test():
        manager = DuelRoomManager()
        
        # 1. Test unknown room id
        snapshot = await manager.get_room_snapshot("nonexistent_room")
        assert snapshot is None
        
        # 2. Test valid room with no players (waiting state)
        room_id = await manager.create_room()
        snapshot = await manager.get_room_snapshot(room_id)
        assert snapshot is not None
        assert snapshot["room_id"] == room_id
        assert snapshot["status"] == "waiting"
        assert snapshot["seat_1"] is None
        assert snapshot["seat_2"] is None
        
        # 3. Test valid room with players (active state)
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.join_room(room_id, ws1)
        await manager.join_room(room_id, ws2)
        
        snapshot = await manager.get_room_snapshot(room_id)
        assert snapshot is not None
        assert snapshot["room_id"] == room_id
        assert snapshot["status"] == "active"
        
        seat1 = snapshot["seat_1"]
        assert seat1 is not None
        assert seat1["player_id"] is not None
        assert seat1["score"] == 0
        assert seat1["level"] == 1
        assert seat1["total_lines"] == 0
        assert seat1["status"] == "playing"
        assert seat1["active_piece_generation"] == 0
        assert seat1["last_processed_seq_num"] == 0
        assert len(seat1["board"]) == 20
        assert len(seat1["board"][0]) == 10
        assert seat1["hold_piece"] is None
        assert seat1["can_hold"] is True
        
        # Clean up
        manager._cancel_room_tasks(room_id)

    asyncio.run(run_test())
