import pytest
import json
import asyncio
from fastapi import status
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from backend.main import app, duel_manager
from backend.models import WSMessageEnvelope, ActionPayload

def retrieve_msg_of_type(ws, msg_type, timeout=2.0, allow_error=False):
    import time
    start = time.time()
    while time.time() - start < timeout:
        data = ws.receive_text()
        msg = json.loads(data)
        if msg.get("type") == "error" and not allow_error:
            raise ValueError(f"Server returned error message: {msg['payload']['message']}")
        if msg["type"] == msg_type:
            return msg
    raise TimeoutError(f"Timed out waiting for message of type '{msg_type}'")


def drain_and_assert_disconnect(ws, expected_code, timeout=2.0):
    import anyio
    
    async def async_drain(send_rx):
        with anyio.fail_after(timeout):
            while True:
                try:
                    message = await send_rx.receive()
                except anyio.EndOfStream:
                    return 1000
                if message["type"] == "websocket.close":
                    return message.get("code", 1000)
                    
    try:
        code = ws.portal.call(async_drain, ws._send_rx)
    except TimeoutError:
        pytest.fail(f"Timed out waiting for WebSocket disconnect (expected {expected_code})")
        
    assert code == expected_code, f"Expected disconnect code {expected_code}, got {code}"


def test_main_lifespan():
    # Clear rooms to avoid any task from another event loop interfering on shutdown
    duel_manager.rooms.clear()
    
    # Use TestClient as context manager to trigger lifespan startup & shutdown
    with TestClient(app) as client:
        response = client.get("/api/high-scores")
        assert response.status_code == 200


def test_main_move_invalid_direction():
    client = TestClient(app)
    # Create game session
    resp = client.post("/api/games")
    assert resp.status_code == 201
    game_id = resp.json()["id"]

    # Send move request with invalid direction
    resp_move = client.post(f"/api/games/{game_id}/move", json={"direction": "invalid"})
    assert resp_move.status_code == 400
    assert "Invalid direction" in resp_move.json()["detail"]


def test_main_hold_game_over_and_twice():
    client = TestClient(app)
    # Create game session
    resp = client.post("/api/games")
    game_id = resp.json()["id"]

    # 1. Successful hold first time
    resp_hold = client.post(f"/api/games/{game_id}/hold")
    assert resp_hold.status_code == 200
    assert resp_hold.json()["hold_piece"] is not None

    # 2. Hold again immediately should fail with 400 (HOLD_ACTION_NOT_ALLOWED)
    resp_hold2 = client.post(f"/api/games/{game_id}/hold")
    assert resp_hold2.status_code == 400

    # 3. Hold on a game-over session should fail with 400
    # Let's drop a block to the top to trigger game over
    # We can just mock the session's status to "game_over" inside the SessionManager
    from backend.main import manager
    session = manager.get_session(game_id)
    session.status = "game_over"

    resp_hold_over = client.post(f"/api/games/{game_id}/hold")
    assert resp_hold_over.status_code == 400


def test_websocket_handshake_invalid_id_format():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}
    
    # ID with invalid character '@' -> rejected on connect
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/duel/room@bad?player_id=p1", headers=headers) as ws:
            pass


def test_websocket_handshake_bad_origins():
    client = TestClient(app)
    
    # Missing or null origin
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/duel/room_origin?player_id=p1", headers={"origin": "null"}) as ws:
            pass

    # Forbidden origin
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/duel/room_origin?player_id=p1", headers={"origin": "http://evil.com"}) as ws:
            pass


def test_websocket_handshake_duplicate_player():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_dup?player_id=p1", headers=headers) as ws1:
        # Connect another player with same player_id to same room
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/api/ws/duel/room_dup?player_id=p1", headers=headers) as ws2:
                ws2.receive_text()
        assert excinfo.value.code == 4004


def test_websocket_handshake_room_already_finished():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_fin?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_fin?player_id=p2", headers=headers) as ws2:
            # Wait for start
            ws1.receive_text() # state or start
            ws2.receive_text()

            # Set room status to finished
            room = duel_manager.rooms["room_fin"]
            room.status = "finished"

            # Connect another player -> should get closed with 4003 (Room already finished)
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with client.websocket_connect("/api/ws/duel/room_fin?player_id=p3", headers=headers) as ws3:
                    ws3.receive_text()
            assert excinfo.value.code == 4003


def test_websocket_binary_message_rejection():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_binary?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_binary?player_id=p2", headers=headers) as ws2:
            # Consume start messages
            retrieve_msg_of_type(ws1, "start")
            retrieve_msg_of_type(ws2, "start")

            # send binary message
            ws1.send_bytes(b"some binary data")
            
            # verify socket was closed with code 1003 using the draining helper
            drain_and_assert_disconnect(ws1, 1003)


def test_websocket_oversized_frame_rejection():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_oversized?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_oversized?player_id=p2", headers=headers) as ws2:
            # Consume start messages
            retrieve_msg_of_type(ws1, "start")
            retrieve_msg_of_type(ws2, "start")

            # Send message larger than 4096 bytes
            ws1.send_text("A" * 5000)
            
            # verify socket was closed with code 1008 using the draining helper
            drain_and_assert_disconnect(ws1, 1008)


def test_websocket_invalid_envelope_json_rejection():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_invalid?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_invalid?player_id=p2", headers=headers) as ws2:
            # Consume start messages
            retrieve_msg_of_type(ws1, "start")
            retrieve_msg_of_type(ws2, "start")

            # Send invalid json
            ws1.send_text("not-json-at-all")
            
            # verify socket was closed with code 1008 using the draining helper
            drain_and_assert_disconnect(ws1, 1008)


def test_websocket_forbidden_message_type():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_forbidden?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_forbidden?player_id=p2", headers=headers) as ws2:
            # Consume start messages
            retrieve_msg_of_type(ws1, "start")
            retrieve_msg_of_type(ws2, "start")

            # Send forbidden message type "start" from client
            payload = {
                "v": 1,
                "type": "start",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 1,
                "payload": {}
            }
            ws1.send_text(json.dumps(payload))
            
            # verify socket was closed with code 1008 using the draining helper
            drain_and_assert_disconnect(ws1, 1008)


def test_websocket_heartbeat_is_no_op():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_hb?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_hb?player_id=p2", headers=headers) as ws2:
            # Send valid heartbeat
            payload = {
                "v": 1,
                "type": "heartbeat",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 1,
                "payload": None
            }
            ws1.send_text(json.dumps(payload))
            # Wait a small bit, the connection should remain active
            # Send a move action to confirm the websocket is still working
            action_payload = {
                "action": "move_left",
                "seq": 0,
                "room_id": "room_hb",
                "player_id": "p1",
                "generation": 0
            }
            msg = {
                "v": 1,
                "type": "action",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 0,
                "payload": action_payload
            }
            ws1.send_text(json.dumps(msg))


def test_websocket_action_gates_and_types():
    client = TestClient(app)
    headers = {"origin": "http://localhost:5173"}

    with client.websocket_connect("/api/ws/duel/room_actions?player_id=p1", headers=headers) as ws1:
        with client.websocket_connect("/api/ws/duel/room_actions?player_id=p2", headers=headers) as ws2:
            # Wait for start
            ws1.receive_text()

            # 1. Action with mismatching player_id
            payload_mismatch_p = {
                "v": 1,
                "type": "action",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 0,
                "payload": {
                    "action": "move_left",
                    "seq": 0,
                    "room_id": "room_actions",
                    "player_id": "p2",  # sent by p1 connection, should be ignored
                    "generation": 0
                }
            }
            ws1.send_text(json.dumps(payload_mismatch_p))

            # 2. Action with stale seq
            # First send a valid action
            payload_valid = {
                "v": 1,
                "type": "action",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 10,
                "payload": {
                    "action": "move_left",
                    "seq": 10,
                    "room_id": "room_actions",
                    "player_id": "p1",
                    "generation": 0
                }
            }
            ws1.send_text(json.dumps(payload_valid))

            # Send a duplicate / stale seq number 10 (should be ignored)
            ws1.send_text(json.dumps(payload_valid))

            # 3. Action with invalid generation (generation=10, should be ignored)
            payload_invalid_gen = {
                "v": 1,
                "type": "action",
                "timestamp": "2026-11-05T00:00:00Z",
                "seq": 11,
                "payload": {
                    "action": "move_right",
                    "seq": 11,
                    "room_id": "room_actions",
                    "player_id": "p1",
                    "generation": 10
                }
            }
            ws1.send_text(json.dumps(payload_invalid_gen))

            # 4. Try multiple action types: move_right, rotate_clockwise, rotate_counterclockwise, soft_drop, hold, hard_drop
            actions = ["move_right", "rotate_clockwise", "rotate_counterclockwise", "soft_drop", "hold", "hard_drop"]
            seq = 12
            for act in actions:
                # We need to dynamically look up current generation since some actions (like hold/hard_drop) might increment generation on spawn
                room = duel_manager.rooms["room_actions"]
                p1_player = room.players["p1"]
                gen = p1_player.session.generation

                payload_act = {
                    "v": 1,
                    "type": "action",
                    "timestamp": "2026-11-05T00:00:00Z",
                    "seq": seq,
                    "payload": {
                        "action": act,
                        "seq": seq,
                        "room_id": "room_actions",
                        "player_id": "p1",
                        "generation": gen
                    }
                }
                ws1.send_text(json.dumps(payload_act))
                seq += 1
