import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.ws_duel import duel_manager

def test_websocket_origin_validation():
    client = TestClient(app)
    
    # 1. Authorized origin should succeed
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws:
        data = ws.receive_json()
        assert data["event"] == "joined"

    # 2. Unauthorized origin should fail/reject with 403 Forbidden
    with pytest.raises(Exception):
        with client.websocket_connect("/api/duel/ws", headers={"origin": "http://malicious.com"}):
            pass

    # 3. Missing origin header should fail/reject with 403 Forbidden
    with pytest.raises(Exception):
        with client.websocket_connect("/api/duel/ws"):
            pass

def test_websocket_room_assignment_gating():
    client = TestClient(app)
    
    # Connect with an unknown room_id -> should reject with close code 4004
    with client.websocket_connect("/api/duel/ws?room_id=nonexistent_room", headers={"origin": "http://localhost:5173"}) as ws:
        with pytest.raises(Exception):
            ws.receive_json()
        
def test_websocket_full_room_rejection():
    client = TestClient(app)
    from fastapi.websockets import WebSocketDisconnect
    
    # Establish a fresh room
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws1:
        data1 = ws1.receive_json()
        room_id = data1["payload"]["room_id"]
        
        # Player 2 joins -> room becomes full and active
        with client.websocket_connect(f"/api/duel/ws?room_id={room_id}", headers={"origin": "http://localhost:5173"}) as ws2:
            data2 = ws2.receive_json()
            assert data2["payload"]["assigned_seat"] == "seat_2"
            
            # Capture identities and status before third join attempt
            room = duel_manager.rooms[room_id]
            seat_1_player_id = room["seat_1"].player_id
            seat_2_player_id = room["seat_2"].player_id
            assert room["status"] == "active"
            
            # Player 3 attempts to join -> should close with 4001 Room Full
            with client.websocket_connect(f"/api/duel/ws?room_id={room_id}", headers={"origin": "http://localhost:5173"}) as ws3:
                with pytest.raises(WebSocketDisconnect) as exc_info:
                    ws3.receive_json()
            assert exc_info.value.code == 4001

            # Assert unchanged occupied-seat identities and active room
            assert room_id in duel_manager.rooms
            assert duel_manager.rooms[room_id]["status"] == "active"
            assert duel_manager.rooms[room_id]["seat_1"].player_id == seat_1_player_id
            assert duel_manager.rooms[room_id]["seat_2"].player_id == seat_2_player_id

def test_websocket_action_processing_and_validation():
    client = TestClient(app)
    
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws1:
        data1 = ws1.receive_json()
        room_id = data1["payload"]["room_id"]
        ws1.receive_json() # receive state broadcast
        
        with client.websocket_connect(f"/api/duel/ws?room_id={room_id}", headers={"origin": "http://localhost:5173"}) as ws2:
            ws2.receive_json() # joined
            ws2.receive_json() # state broadcast
            
            # Receive active/start broadcast on ws1
            ws1.receive_json()
            
            # Send valid action (seq_num = 1)
            ws1.send_json({
                "v": 1,
                "event": "action",
                "payload": {
                    "seq_num": 1,
                    "generation": 0,
                    "action_type": "left"
                }
            })
            state_data = ws1.receive_json()
            assert state_data["event"] == "state_update"
            assert state_data["payload"]["last_action_seat"] == "seat_1"
            assert state_data["payload"]["last_action_seq"] == 1

            # Send duplicate action sequence (seq_num = 1 is duplicate since last_processed_seq_num is now 1)
            ws1.send_json({
                "v": 1,
                "event": "action",
                "payload": {
                    "seq_num": 1,
                    "generation": 0,
                    "action_type": "left"
                }
            })
            err_data = ws1.receive_json()
            assert err_data["event"] == "error"
            assert "Conflict/Stale Action" in err_data["payload"]["message"]

def test_websocket_payload_limit_enforcement():
    client = TestClient(app)
    from fastapi.websockets import WebSocketDisconnect
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws:
        ws.receive_json() # joined
        ws.receive_json() # initial state broadcast
        
        # Send a massive payload (> 1 KB)
        massive_payload = "A" * 1500
        ws.send_text(massive_payload)
        
        # Connection should close immediately
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4000

def test_websocket_active_oversized_policy_close_delivers_peer_forfeit():
    client = TestClient(app)
    from fastapi.websockets import WebSocketDisconnect
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws1:
        data1 = ws1.receive_json()
        room_id = data1["payload"]["room_id"]
        ws1.receive_json() # state broadcast
        
        with client.websocket_connect(f"/api/duel/ws?room_id={room_id}", headers={"origin": "http://localhost:5173"}) as ws2:
            ws2.receive_json() # joined
            ws2.receive_json() # state broadcast
            
            # Receive active/start broadcast on ws1
            ws1.receive_json()
            # Receive active/start broadcast on ws2
            ws2.receive_json()
            
            # Send an oversized payload from ws1 (> 1 KB)
            massive_payload = "A" * 1500
            ws1.send_text(massive_payload)
            
            # ws1 should be disconnected, eventually raising an exception on read once queue is exhausted
            with pytest.raises(WebSocketDisconnect) as exc_info:
                for _ in range(20):
                    ws1.receive_json()
            assert exc_info.value.code == 4000
                
            # ws2 should receive a game_over event indicating seat_2 has won due to forfeit
            go_event = None
            for _ in range(20):
                try:
                    msg = ws2.receive_json()
                    if msg.get("event") == "game_over":
                        go_event = msg
                        break
                except Exception:
                    break
            
            assert go_event is not None
            assert go_event["payload"]["outcome"] == "seat_2_win"
            assert "disconnected/forfeited" in go_event["payload"]["reason"]

def test_websocket_waiting_seat_policy_close_releasing_room():
    client = TestClient(app)
    from fastapi.websockets import WebSocketDisconnect
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws1:
        data1 = ws1.receive_json()
        room_id = data1["payload"]["room_id"]
        ws1.receive_json() # initial state
        
        assert room_id in duel_manager.rooms
        assert duel_manager.rooms[room_id]["status"] == "waiting"
        
        # Send an oversized payload to trigger policy close
        massive_payload = "A" * 1500
        ws1.send_text(massive_payload)
        
        # Connection should close due to the policy exception
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws1.receive_json()
        assert exc_info.value.code == 4000
        
    # Since ws1 disconnected while waiting, the room should be released immediately
    assert room_id not in duel_manager.rooms

def test_websocket_failed_join_never_cleans_up_another_seat():
    client = TestClient(app)
    with client.websocket_connect("/api/duel/ws", headers={"origin": "http://localhost:5173"}) as ws1:
        data1 = ws1.receive_json()
        room_id = data1["payload"]["room_id"]
        ws1.receive_json() # initial state
        
        assert room_id in duel_manager.rooms
        assert duel_manager.rooms[room_id]["seat_1"] is not None
        
        # Try a failed join with an unauthorized origin
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/duel/ws?room_id={room_id}", headers={"origin": "http://malicious.com"}):
                pass
                
        # Check that ws1 was not affected and seat_1 is still intact
        assert room_id in duel_manager.rooms
        assert duel_manager.rooms[room_id]["seat_1"] is not None
        assert duel_manager.rooms[room_id]["status"] == "waiting"
        
        # Try joining with an invalid query param/invalid room ID
        with client.websocket_connect("/api/duel/ws?room_id=nonexistent_room", headers={"origin": "http://localhost:5173"}) as ws_fail:
            with pytest.raises(Exception):
                ws_fail.receive_json()
                
        # Again check ws1 is completely intact
        assert room_id in duel_manager.rooms
        assert duel_manager.rooms[room_id]["seat_1"] is not None
        assert duel_manager.rooms[room_id]["status"] == "waiting"

