import pytest
import json
import asyncio
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from backend.main import app, duel_manager
from backend.models import WSMessageEnvelope, ActionPayload, ErrorPayload
from backend.duel import DuelPlayer, DuelRoom, evaluate_room_outcome, get_piece_at_index

def retrieve_msg_of_type(ws, msg_type, timeout=1.0, allow_error=False):
    # Simple, highly robust helper to read messages until one of msg_type is found
    start = time.time()
    while time.time() - start < timeout:
        data = ws.receive_text()
        msg = json.loads(data)
        if msg.get("type") == "error" and not allow_error:
            raise ValueError(f"Server returned error message: {msg['payload']['message']}")
        if msg["type"] == msg_type:
            return msg
    raise TimeoutError(f"Timed out waiting for message of type '{msg_type}'")

def retrieve_causal_msg(ws, player_id, seq_number, revision, timeout=1.0):
    """
    Receives messages in a wall-clock loop with a timeout, filtering for a state message
    where last_processed_seq >= seq_number and revision >= revision for the given player.
    """
    start = time.time()
    while time.time() - start < timeout:
        data = ws.receive_text()
        msg = json.loads(data)
        if msg.get("type") == "error":
            raise ValueError(f"Server returned error message: {msg['payload']['message']}")
        if msg["type"] == "state" and msg["payload"]["player_id"] == player_id:
            if msg["payload"]["last_processed_seq"] >= seq_number and msg["payload"]["revision"] >= revision:
                return msg
    raise TimeoutError(f"Causal message not received for player {player_id}, seq {seq_number}, revision {revision}")

def test_origin_handshake_validation():
    client = TestClient(app)
    
    # Missing Origin header -> HTTP 403 Forbidden
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/duel/test_room?player_id=p1") as ws:
            pass
            
    # Correct Origin -> Successfully connects
    headers = {"origin": "http://localhost:5173"}
    with client.websocket_connect("/api/ws/duel/test_room?player_id=p1", headers=headers) as ws:
        msg = retrieve_msg_of_type(ws, "state")
        assert msg["v"] == 1
        assert msg["type"] == "state"

def test_room_full_rejection():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    # Join Player 1
    with client.websocket_connect("/api/ws/duel/full_room?player_id=p1", headers=headers) as ws1:
        # Join Player 2
        with client.websocket_connect("/api/ws/duel/full_room?player_id=p2", headers=headers) as ws2:
            # Receive start message
            msg1 = retrieve_msg_of_type(ws1, "start")
            assert msg1["type"] == "start"
            
            # Now Player 3 tries to join the same room
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with client.websocket_connect("/api/ws/duel/full_room?player_id=p3", headers=headers) as ws3:
                    ws3.receive_text()
            assert excinfo.value.code == 4001

def test_seat_assignment_and_piece_sync():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    with client.websocket_connect("/api/ws/duel/sync_room?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/sync_room?player_id=p2", headers=headers) as ws2:
            # Verify start
            start1 = retrieve_msg_of_type(ws1, "start")
            assert start1["type"] == "start"
            
            room = duel_manager.rooms["sync_room"]
            assert room.players["p1"].seat == 1
            assert room.players["p2"].seat == 2
            
            p1_piece = room.players["p1"].session.active_piece.type
            p2_piece = room.players["p2"].session.active_piece.type
            assert p1_piece == p2_piece
            assert p1_piece == get_piece_at_index(0, room.seed)

def test_seat_ownership_and_stale_actions():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    with client.websocket_connect("/api/ws/duel/action_room?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/action_room?player_id=p2", headers=headers) as ws2:
            # wait for start
            retrieve_msg_of_type(ws1, "start")
            
            room = duel_manager.rooms["action_room"]
            p1 = room.players["p1"]
            
            # Send valid action for p1 (seq=0)
            action_payload = {
                "action": "move_left",
                "seq": 0,
                "room_id": "action_room",
                "player_id": "p1",
                "generation": p1.session.generation
            }
            envelope = {
                "v": 1,
                "type": "action",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "seq": 0,
                "payload": action_payload
            }
            ws1.send_text(json.dumps(envelope))
            
            # Wait causally for state confirming action seq=0 is processed (revises to >= 1)
            msg = retrieve_causal_msg(ws1, "p1", 0, 1)
            assert msg["payload"]["last_processed_seq"] == 0
            assert p1.seq_number == 0
            
            # Send action with wrong player_id (trying to control opponent, seq=1)
            action_payload["player_id"] = "p2"
            action_payload["seq"] = 1
            envelope["seq"] = 1
            envelope["payload"] = action_payload
            ws1.send_text(json.dumps(envelope))
            
            # Send action with stale seq (p1 seq=0, already processed)
            action_payload["player_id"] = "p1"
            action_payload["seq"] = 0
            envelope["seq"] = 0
            envelope["payload"] = action_payload
            ws1.send_text(json.dumps(envelope))
            
            # Now, to verify both bad/stale actions were rejected causally without sleeps,
            # we send a NEW valid action for p1 (seq=1)
            action_payload["player_id"] = "p1"
            action_payload["seq"] = 1
            envelope["seq"] = 1
            envelope["payload"] = action_payload
            ws1.send_text(json.dumps(envelope))
            
            # Wait causally for state confirming p1 seq=1 is processed (revises to >= 2)
            msg2 = retrieve_causal_msg(ws1, "p1", 1, 2)
            assert msg2["payload"]["last_processed_seq"] == 1
            
            # Verify p2 was NEVER mutated and sequence remains -1
            assert room.players["p2"].seq_number == -1
            # Verify p1 sequence is exactly 1 (it skipped seq=0 stale action and processed seq=1)
            assert p1.seq_number == 1

def test_disconnect_forfeit():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    with client.websocket_connect("/api/ws/duel/forfeit_room?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/forfeit_room?player_id=p2", headers=headers) as ws2:
            # Wait for start
            retrieve_msg_of_type(ws2, "start")
            
            # Disconnect Player 1
            ws1.close()
            
            # Player 2 should receive Outcome of forfeit
            msg = retrieve_msg_of_type(ws2, "outcome")
            assert msg["type"] == "outcome"
            assert msg["payload"]["winner_id"] == "p2"
            assert msg["payload"]["loser_id"] == "p1"
            assert msg["payload"]["reason"] == "forfeit"

def test_same_update_draw_evaluation():
    room = DuelRoom("draw_room", seed=1234)
    p1 = DuelPlayer("p1", None, 1, 1234)
    p2 = DuelPlayer("p2", None, 2, 1234)
    room.players = {"p1": p1, "p2": p2}
    room.status = "playing"
    
    p1.session.status = "game_over"
    p2.session.status = "game_over"
    
    evaluate_room_outcome(room, reason="top_out")
    assert room.status == "finished"
    assert room.is_draw is True
    assert room.winner_id is None
    assert room.loser_id is None

@pytest.mark.anyio
async def test_sweeper_and_synthetic_cleanup():
    room1 = duel_manager.get_or_create_room("clean_room1")
    room2 = duel_manager.get_or_create_room("clean_room2")
    
    room1.status = "finished"
    room1.finished_at = duel_manager.clock() - 65.0
    room2.last_input_time = duel_manager.clock() - 245.0
    
    await duel_manager.sweep_rooms()
    
    assert "clean_room1" not in duel_manager.rooms
    assert "clean_room2" not in duel_manager.rooms

def test_oversized_and_malformed_frames():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    # 1. Test oversize frame closes connection with 1008
    with client.websocket_connect("/api/ws/duel/malformed_room1?player_id=p1", headers=headers) as ws:
        retrieve_msg_of_type(ws, "state")
        ws.send_text("A" * 5000)
        msg = retrieve_msg_of_type(ws, "error", allow_error=True)
        assert msg["type"] == "error"
        assert "exceeds 4096-byte limit" in msg["payload"]["message"]
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()
        assert excinfo.value.code == 1008

    # 2. Test invalid JSON closes connection with 1008
    with client.websocket_connect("/api/ws/duel/malformed_room2?player_id=p1", headers=headers) as ws:
        retrieve_msg_of_type(ws, "state")
        ws.send_text("{bad-json")
        msg = retrieve_msg_of_type(ws, "error", allow_error=True)
        assert msg["type"] == "error"
        assert "Invalid message envelope" in msg["payload"]["message"]
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()
        assert excinfo.value.code == 1008

def test_strict_version_envelope_validation():
    # Test v=True (should fail validation)
    with pytest.raises(Exception):
        WSMessageEnvelope(v=True, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    # Test v=False (should fail)
    with pytest.raises(Exception):
        WSMessageEnvelope(v=False, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    # Test v=1.0 (should fail)
    with pytest.raises(Exception):
        WSMessageEnvelope(v=1.0, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    # Test v="1" (should fail)
    with pytest.raises(Exception):
        WSMessageEnvelope(v="1", type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    # Test unsupported version
    with pytest.raises(Exception):
        WSMessageEnvelope(v=2, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    # Test valid version v=1 (should pass)
    env = WSMessageEnvelope(v=1, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-1, payload=None)
    assert env.v == 1

def test_deterministic_topout_draw_gravity():
    from backend.duel import update_room_gravity
    # Create room and players
    room = DuelRoom("draw_gravity_room", seed=12345)
    room.status = "playing"
    
    p1 = DuelPlayer("player1", None, 1, 12345)
    p2 = DuelPlayer("player2", None, 2, 12345)
    room.players = {"player1": p1, "player2": p2}
    
    # 1. Preset the board: occupy spawn cells in [1, 4] for both boards
    p1.session.board[1][4] = "I"
    p2.session.board[1][4] = "I"
    
    # 2. Preset the next piece for both sessions to be "O"
    p1.session.next_piece = "O"
    p2.session.next_piece = "O"
    
    # 3. Position the active piece at the floor row 19, columns 0..3
    p1.session.active_piece.type = "I"
    p1.session.active_piece.origin = [18, 0]
    p1.session.active_piece.cells = [[19, 0], [19, 1], [19, 2], [19, 3]]
    p2.session.active_piece.type = "I"
    p2.session.active_piece.origin = [18, 0]
    p2.session.active_piece.cells = [[19, 0], [19, 1], [19, 2], [19, 3]]
    
    # Set gravity next tick time to 0.0 (already due)
    p1.next_gravity_tick_time = 0.0
    p2.next_gravity_tick_time = 0.0
    
    # Run update_room_gravity at due time 10.0
    updated = update_room_gravity(room, 10.0)
    
    assert updated is True
    # Both should top out and transition to game_over, resulting in finished status and draw
    assert p1.session.status == "game_over"
    assert p2.session.status == "game_over"
    assert room.status == "finished"
    assert room.is_draw is True
    assert room.winner_id is None
    assert room.loser_id is None

def test_gravity_one_topout_survivor():
    from backend.duel import update_room_gravity
    room = DuelRoom("survivor_room", seed=12345)
    room.status = "playing"
    
    p1 = DuelPlayer("player1", None, 1, 12345)
    p2 = DuelPlayer("player2", None, 2, 12345)
    room.players = {"player1": p1, "player2": p2}
    
    # player1's board spawn cell is occupied, causing topout
    p1.session.board[1][4] = "I"
    p1.session.next_piece = "O"
    p1.session.active_piece.type = "I"
    p1.session.active_piece.origin = [18, 0]
    p1.session.active_piece.cells = [[19, 0], [19, 1], [19, 2], [19, 3]]
    
    # player2 is safe, can move down
    p2.session.active_piece.cells = [[10, 0], [10, 1], [10, 2], [10, 3]]
    
    p1.next_gravity_tick_time = 0.0
    p2.next_gravity_tick_time = 0.0
    
    updated = update_room_gravity(room, 10.0)
    assert updated is True
    assert p1.session.status == "game_over"
    assert p2.session.status == "playing"
    assert room.status == "finished"
    assert room.is_draw is False
    assert room.winner_id == "player2"
    assert room.loser_id == "player1"

def test_gravity_one_due_non_due():
    from backend.duel import update_room_gravity
    room = DuelRoom("due_room", seed=12345)
    room.status = "playing"
    
    p1 = DuelPlayer("player1", None, 1, 12345)
    p2 = DuelPlayer("player2", None, 2, 12345)
    room.players = {"player1": p1, "player2": p2}
    
    # Both start with next_gravity_tick_time
    p1.next_gravity_tick_time = 5.0
    p2.next_gravity_tick_time = 15.0
    
    # At time 10.0, only p1 is due
    updated = update_room_gravity(room, 10.0)
    assert updated is True
    assert p1.next_gravity_tick_time > 10.0
    assert p2.next_gravity_tick_time == 15.0 # Unchanged!

def test_duplicate_player_id_rejection_no_override():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    with client.websocket_connect("/api/ws/duel/dup_room?player_id=p1", headers=headers) as ws1:
        retrieve_msg_of_type(ws1, "state")
        
        # Another connection with same player_id joins
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/api/ws/duel/dup_room?player_id=p1", headers=headers) as ws2:
                ws2.receive_text()
        assert excinfo.value.code == 4004
        
        # Verify first player is still in the room
        room = duel_manager.rooms["dup_room"]
        assert "p1" in room.players
        assert len(room.players) == 1

def test_large_piece_sequence_and_independent_hold():
    p1 = DuelPlayer("player1", None, 1, seed=999)
    # Retrieve more than 500 pieces
    for idx in range(600):
        piece = get_piece_at_index(idx, seed=999)
        assert piece in ("I", "O", "T", "J", "L", "S", "Z")
    
    # Test hold action execution on session
    assert p1.session.hold_piece is None
    original_active = p1.session.active_piece.type
    success = p1.session.hold()
    assert success is True
    assert p1.session.hold_piece == original_active

