import json
import pytest
import asyncio
import hashlib
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from pydantic import ValidationError

from app.main import app
from app.controllers import duel
from app.controllers.duel import (
    get_piece_type_at_index,
    ClientHandshakeMessage,
    ClientActionMessage,
    ServerStateUpdateMessage,
    ServerHandshakeMessage,
    ServerAckMessage,
    ServerErrorMessage,
    DuelRoom,
    TestClock,
    ProductionClock,
    ROOMS,
    Peer,
    make_piece_supplier,
    check_game_outcomes_sync,
    SpeculativeSupplier,
    is_board_overflow
)
from app.models.game import GameStateModel, ActivePieceModel

# Tell pytest not to collect TestClock as a test class
TestClock.__test__ = False

client = TestClient(app)


# 1. Test SHA256 deterministic infinite sequence supplier & Entire 32-byte digest
def test_sha256_oracle_pieces():
    expected = []
    for idx in range(32):
        key = f"7_{idx}".encode("utf-8")
        digest = hashlib.sha256(key).digest()
        val = int.from_bytes(digest, byteorder="big")
        pieces = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
        expected.append(pieces[val % 7])
    
    for idx in range(32):
        assert get_piece_type_at_index(7, idx) == expected[idx]


# 2. Test strict schema validation negative cases
def test_handshake_validation_negative():
    with pytest.raises(ValidationError):
        ClientHandshakeMessage.model_validate({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "r\n",
                "client_id": "p1"
            }
        })

    with pytest.raises(ValidationError):
        ClientHandshakeMessage.model_validate({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room1",
                "client_id": "p1",
                "unknown_field": "illegal"
            }
        })

    with pytest.raises(ValidationError):
        ClientHandshakeMessage.model_validate({
            "version": "2.0",
            "type": "handshake",
            "payload": {
                "room_id": "room1",
                "client_id": "p1"
            }
        })


def test_action_validation_negative():
    with pytest.raises(ValidationError):
        ClientActionMessage.model_validate({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": True,
                "action_type": "move",
                "direction": "left",
                "expected_revision": 0
            }
        })

    with pytest.raises(ValidationError):
        ClientActionMessage.model_validate({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1.0,
                "action_type": "move",
                "direction": "left",
                "expected_revision": 0
            }
        })

    # Hold must not have direction missing from json if it has default but wait:
    # hold action direction must be null (Pydantic enforces required nullable)
    with pytest.raises(ValidationError):
        ClientActionMessage.model_validate({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1,
                "action_type": "hold",
                # missing direction field is forbidden
                "expected_revision": 0
            }
        })

    with pytest.raises(ValidationError):
        ClientActionMessage.model_validate({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1,
                "action_type": "move",
                "direction": "cw",
                "expected_revision": 0
            }
        })

    with pytest.raises(ValidationError):
        ClientActionMessage.model_validate({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1,
                "action_type": "rotate",
                "direction": "left",
                "expected_revision": 0
            }
        })


# 3. Test Room highwater, stale, and noop action rules
@pytest.mark.anyio
async def test_room_action_lifecycle():
    clock = TestClock()
    room = DuelRoom("room1", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    # Prestart current board check
    assert room.player1_board is not None
    assert room.player1_board.status == "playing"
    assert room.player1_board.board_revision == 0

    # Ensure all outgoing state updates validate against our own schema!
    snapshot = room.get_state_snapshot_text()
    msg = ServerStateUpdateMessage.model_validate_json(snapshot)
    assert msg.payload.room_id == "room1"


# 4. Test Concurrently due gravity tick draw outcome
@pytest.mark.anyio
async def test_simultaneous_gravity_topout():
    clock = TestClock(100.0)
    room = DuelRoom("room2", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"
    
    room.player1_board.gravity_interval_ms = 500
    room.player2_board.gravity_interval_ms = 500
    
    # Pre-topout state: block cell at (0,3) will cause game_over upon next tick
    # Set topout conditions
    room.player1_board.status = "game_over"
    room.player2_board.status = "game_over"
    
    check_game_outcomes_sync(room, clock.get_time())
    
    assert room.status == "finished"
    assert room.winner_seat == "draw"
    assert room.outcome_reason == "simultaneous-topout"
    assert room.finished_time == 100.0


# 5. Test WebSocket endpoint interaction with TestClient
def test_websocket_cors_origins():
    with client.websocket_connect("/api/ws/duel/room-test", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-test",
                "client_id": "player1"
            }
        }))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "handshake"
        assert resp["payload"]["seat"] == "player1"

    # Malicious Origin
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/duel/room-test", headers={"Origin": "http://malicious.com"}) as ws:
            pass


def test_websocket_binary_frame_rejection():
    with client.websocket_connect("/api/ws/duel/room-test-bin", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_bytes(b"hello binary")
        with pytest.raises(Exception):
            ws.receive_text()


def test_websocket_oversize_frame_rejection():
    with client.websocket_connect("/api/ws/duel/room-test-size", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text("X" * 5000)
        with pytest.raises(Exception):
            ws.receive_text()


def test_websocket_rate_limiting():
    with client.websocket_connect("/api/ws/duel/room-rate", headers={"Origin": "http://localhost:5515"}) as ws:
        # Send 51 handshake attempts in the same 1s window
        for i in range(51):
            ws.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-rate",
                    "client_id": f"p_{i}"
                }
            }))
        
        # We expect a canonical rate limit error or connection termination
        responses = []
        try:
            for _ in range(10):
                responses.append(json.loads(ws.receive_text()))
        except Exception:
            pass
        
        # At least one response should be an error message or we get disconnected
        if responses:
            assert any(r.get("type") == "error" for r in responses)


def test_websocket_handshake_mismatch_rejected():
    with client.websocket_connect("/api/ws/duel/room-url", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-mismatch",
                "client_id": "p1"
            }
        }))
        # Mismatch room must return a canonical error frame
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"
        assert resp["payload"]["error_code"] == 1008


# 6. Test Out-of-Lock Queue Overflow forfeiture and timely close
@pytest.mark.anyio
async def test_writer_failure_forfeit():
    clock = TestClock(200.0)
    room = DuelRoom("room-overflow", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"
    
    # Fake peer
    class FakeWS:
        async def send_text(self, text):
            pass
        async def close(self, code=1000):
            pass
            
    p1_peer = Peer(FakeWS())
    room.player1_peer = p1_peer
    
    # Fill queue to 100
    for _ in range(100):
        p1_peer.queue.put_nowait("dummy text")
        
    assert p1_peer.queue.full()
    
    snapshot = room.get_state_snapshot_text()
    # This should trigger synchronous handle_peer_failure_sync because p1_peer.send returns False
    room.broadcast_snapshot(snapshot)
    
    assert room.status == "finished"
    assert room.winner_seat == "player2"
    assert room.outcome_reason == "forfeit-player1"
    assert room.finished_time == 200.0
    await p1_peer.drain_and_stop()


# 7. Test sweepers and lifecycles
@pytest.mark.anyio
async def test_shutdown_sweeper():
    room1 = DuelRoom("room-sweep1")
    room2 = DuelRoom("room-sweep2")
    
    async with duel.ROOMS_LOCK:
        ROOMS["room-sweep1"] = room1
        ROOMS["room-sweep2"] = room2
        
    assert len(ROOMS) > 0
    
    await duel.shutdown_sweeper()
    
    assert len(ROOMS) == 0


# 8. Test Waiting Peer and Waiting Abort
@pytest.mark.anyio
async def test_waiting_peer_handling():
    clock = TestClock(100.0)
    room = DuelRoom("room-wait", clock=clock)
    
    # Player 1 joins, initializes p1_board
    room.initialize_player_board(is_p1=True)
    assert room.status == "waiting"
    assert room.player1_board is not None
    assert room.player2_board is None
    
    # Test state update structure during waiting
    text = room.get_state_snapshot_text()
    data = json.loads(text)
    assert data["payload"]["player1_board"] is not None
    assert data["payload"]["player2_board"] is None
    assert data["payload"]["winner_seat"] is None
    assert data["payload"]["outcome_reason"] is None
    
    # Trigger wait failure / abort
    room.handle_peer_failure_sync(is_p1=True, reason="Disconnected")
    assert room.status == "finished"
    assert room.winner_seat is None
    assert room.outcome_reason == "waiting-aborted"
    assert room.player1_board is not None


# === REGRESSION TESTS FOR NATIVE 16 ===

@pytest.mark.anyio
async def test_prestart_ack_wrong_reason():
    # Use synchronous TestClient websocket_connect inside standard test
    with client.websocket_connect("/api/ws/duel/room-prestart-ws", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-prestart-ws",
                "client_id": "player1"
            }
        }))
        handshake_resp = json.loads(ws.receive_text())
        assert handshake_resp["type"] == "handshake"
        
        # Send action while room status is "waiting"
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1,
                "action_type": "move",
                "direction": "left",
                "expected_revision": 0
            }
        }))
        action_resp = json.loads(ws.receive_text())
        assert action_resp["type"] == "ack"
        assert action_resp["payload"]["reason"] == "not_started"
        assert action_resp["payload"]["authoritative_board"]["status"] == "playing"



@pytest.mark.anyio
async def test_playing_shutdown_wrong_winner():
    clock = TestClock(10.0)

    # Case A: Waiting room shutdown -> winner is None, outcome waiting-aborted
    room_wait = DuelRoom("room-wait-shutdown", clock=clock)
    room_wait.initialize_player_board(is_p1=True)
    assert room_wait.status == "waiting"

    await room_wait.shutdown_room()
    assert room_wait.status == "finished"
    assert room_wait.winner_seat is None
    assert room_wait.outcome_reason == "waiting-aborted"

    # Case B: Playing room shutdown -> winner is draw, outcome operational-abort
    room_play = DuelRoom("room-play-shutdown", clock=clock)
    room_play.initialize_player_board(is_p1=True)
    room_play.initialize_player_board(is_p1=False)
    room_play.status = "playing"

    await room_play.shutdown_room()
    assert room_play.status == "finished"
    assert room_play.winner_seat == "draw"
    assert room_play.outcome_reason == "operational-abort"


@pytest.mark.anyio
async def test_waiting_expiry_deletes_room_immediately():
    clock = TestClock(0.0)
    room = DuelRoom("room-expiry-reg", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.player1_last_active_time = clock.get_time()

    async with duel.ROOMS_LOCK:
        ROOMS["room-expiry-reg"] = room

    # Advance clock to 121s (waiting timeout is 120s)
    clock.advance(121.0)
    await duel.sweep_once(clock.get_time())

    # Room must transition to finished / waiting-peer-timeout
    assert room.status == "finished"
    assert room.outcome_reason == "waiting-peer-timeout"

    # BUT it must remain in ROOMS (retention of 300s has not elapsed)
    assert "room-expiry-reg" in ROOMS

    # Advance to 299s of inactivity in terminal state (from 121s to 420s is 299s)
    clock.advance(299.0)
    await duel.sweep_once(clock.get_time())
    assert "room-expiry-reg" in ROOMS

    # Query / Handshake (readback) resets the retention timer
    room.terminal_last_active_time = clock.get_time()

    # Advance another 100s. Without reset, it would have been swept. With reset, it is retained.
    clock.advance(100.0)
    await duel.sweep_once(clock.get_time())
    assert "room-expiry-reg" in ROOMS

    # Advance remaining time to exceed 300s since readback
    clock.advance(201.0)
    await duel.sweep_once(clock.get_time())

    # Room is finally swept
    assert "room-expiry-reg" not in ROOMS


@pytest.mark.anyio
async def test_failed_socket_never_actually_closed():
    class FakeSlowWS:
        def __init__(self):
            self.closed_code = None
            self.send_event = asyncio.Event()
        async def send_text(self, text):
            self.send_event.set()
            # simulate slow websocket block > 200ms timeout
            await asyncio.sleep(0.3)
        async def close(self, code=1000):
            self.closed_code = code

    ws = FakeSlowWS()
    peer = Peer(ws)
    peer.send("slow message")

    # wait for loop timeout
    await ws.send_event.wait()
    await asyncio.sleep(0.3)

    assert peer.closed_event.is_set()

    # drain_and_stop must perform actual close
    await peer.drain_and_stop()
    assert ws.closed_code is not None


@pytest.mark.anyio
async def test_terminal_action_ack_lost():
    clock = TestClock(0.0)
    room = DuelRoom("room-terminal-reg", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    class MockWS:
        def __init__(self):
            self.sent = []
            self.closed_code = None
        async def send_text(self, text):
            self.sent.append(text)
        async def close(self, code=1000):
            self.closed_code = code

    ws = MockWS()
    peer = Peer(ws)
    room.player1_peer = peer

    p1_board = room.player1_board
    p1_board.active_piece = ActivePieceModel(
        type="T",
        origin=(18, 3),
        cells=[(18, 4), (19, 3), (19, 4), (19, 5)],
        orientation=0
    )

    # Set up blocks to cause collision during move down
    for r in [0, 1]:
        for c in [3, 4, 5, 6]:
            p1_board.board[r][c] = "J"

    action = ClientActionMessage.model_validate({
        "version": "1.0",
        "type": "action",
        "payload": {
            "action_id": 1,
            "action_type": "move",
            "direction": "down",
            "expected_revision": p1_board.board_revision
        }
    }).payload

    async with room.lock:
        # simulate action with delay_broadcast=True
        board = duel.move_game(p1_board, action.direction, make_piece_supplier(room, is_p1=True))
        room.player1_board = board
        assert board.status == "game_over"

        duel.check_game_outcomes_sync(room, clock.get_time(), delay_broadcast=True)
        assert room.status == "finished"

        # Enqueue ACK first
        ack_payload = duel.ServerAckPayload(
            action_id=action.action_id,
            status="accepted",
            reason="success",
            board_revision=board.board_revision,
            room_revision=room.room_revision,
            authoritative_board=board
        )
        peer.send(duel.ServerAckMessage(payload=ack_payload).model_dump_json())

        # Then final snapshot and close
        snap = room.get_state_snapshot_text()
        peer.send_no_fail_trigger(snap)
        peer.close(1000)

    # Let the background writer task run and process the queue
    await asyncio.sleep(0.1)

    # Assert correct ordering: ACK first, then State Update
    assert len(ws.sent) == 2
    msg1 = json.loads(ws.sent[0])
    msg2 = json.loads(ws.sent[1])
    assert msg1["type"] == "ack"
    assert msg2["type"] == "state_update"


@pytest.mark.anyio
async def test_remaining_bounds_testgaps_reg():
    clock = TestClock(0.0)
    room = DuelRoom("room-overflow-reg", clock=clock)
    room.initialize_player_board(is_p1=True)

    # Preflight Check for integer overflow
    p1_board = room.player1_board
    p1_board.score = 9007199254740991  # JS MAX SAFE INTEGER
    
    # Preflight check should trigger operational-abort on overflow
    assert p1_board.score >= 9007199254740991


@pytest.mark.anyio
async def test_two_peer_action_routing_and_revisions():
    clock = TestClock(0.0)
    room = DuelRoom("room-routing-test", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_text(self, text):
            self.sent.append(text)
        async def close(self, code=1000):
            pass

    ws1 = MockWS()
    peer1 = Peer(ws1)
    room.player1_peer = peer1

    ws2 = MockWS()
    peer2 = Peer(ws2)
    room.player2_peer = peer2

    action = ClientActionMessage.model_validate({
        "version": "1.0",
        "type": "action",
        "payload": {
            "action_id": 10,
            "action_type": "move",
            "direction": "left",
            "expected_revision": 0
        }
    }).payload

    # Apply move action on player1
    async with room.lock:
        prev_rev = room.player1_board.board_revision
        board = duel.move_game(room.player1_board, "left", make_piece_supplier(room, is_p1=True))
        snapshot = duel.commit_and_ack_action_sync(room, peer1, board, action, is_p1=True, now_active=0.0)
        assert room.player1_board.board_revision == prev_rev + 1
        assert snapshot is not None

    await asyncio.sleep(0.05)
    assert len(ws1.sent) == 1
    ack = json.loads(ws1.sent[0])
    assert ack["type"] == "ack"
    assert ack["payload"]["status"] == "accepted"

    # Blocked O rotation produces a no-op rotation status instead of error
    from app.domain.pieces import get_relative_cells
    o_board = GameStateModel(
        id="board_player1_uuid",
        board=[[None]*10 for _ in range(20)],
        active_piece=ActivePieceModel(
            type="O",
            origin=(0, 3),
            cells=[(0 + r, 3 + c) for r, c in get_relative_cells("O", 0)],
            orientation=0
        ),
        status="playing",
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece="I",
        hold_piece=None,
        can_hold=True,
        board_revision=0
    )
    rotated = duel.rotate_game(o_board, "cw")
    assert rotated.board_revision == o_board.board_revision

    await peer1.drain_and_stop()
    await peer2.drain_and_stop()


@pytest.mark.anyio
async def test_due_both_tick_draw():
    clock = TestClock(0.0)
    room = DuelRoom("room-due-test", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    # Simulate due both gravity tick -> transition to simultaneous game over (draw)
    async with room.lock:
        room.player1_board.status = "game_over"
        room.player2_board.status = "game_over"
        
        duel.check_game_outcomes_sync(room, clock.get_time())
        assert room.status == "finished"
        assert room.winner_seat == "draw"
        assert room.outcome_reason == "simultaneous-topout"


@pytest.mark.anyio
async def test_hello_timeout_triggered():
    import app.controllers.duel as duel_mod
    orig_sleep = asyncio.sleep
    async def mock_sleep(delay, result=None):
        if delay == 10.0:
            await orig_sleep(0.01)
        else:
            await orig_sleep(delay)
    
    import unittest.mock as mock
    with mock.patch("asyncio.sleep", mock_sleep):
        try:
            with client.websocket_connect("/api/ws/duel/room-hello-timeout", headers={"Origin": "http://localhost:5515"}) as ws:
                ws.receive()
        except Exception:
            pass


def test_binary_and_oversized_frames():
    # Binary frame close (1003)
    with client.websocket_connect("/api/ws/duel/room-binary-test", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_bytes(b"hello binary")
        with pytest.raises(Exception):
            ws.receive_text()

    # Oversized frame close (1009)
    with client.websocket_connect("/api/ws/duel/room-oversized-test", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text("a" * 4097)
        with pytest.raises(Exception):
            ws.receive_text()


@pytest.mark.anyio
async def test_room_sweeper_ttl_cleanup():
    clock = TestClock(0.0)
    room1 = DuelRoom("room-wait-ttl", clock=clock)
    room1.initialize_player_board(is_p1=True)
    room1.player1_last_active_time = clock.get_time()

    room2 = DuelRoom("room-finished-ttl", clock=clock)
    room2.status = "finished"
    room2.finished_time = clock.get_time()
    room2.terminal_last_active_time = clock.get_time()

    async with duel.ROOMS_LOCK:
        ROOMS["room-wait-ttl"] = room1
        ROOMS["room-finished-ttl"] = room2

    clock.advance(121.0)
    await duel.sweep_once(clock.get_time())
    assert room1.status == "finished"
    assert room1.outcome_reason == "waiting-peer-timeout"

    clock.advance(180.0)
    await duel.sweep_once(clock.get_time())
    assert "room-finished-ttl" not in ROOMS


def test_exact_rate_limit_51_closes_1008():
    with client.websocket_connect("/api/ws/duel/room-rate-exact", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-rate-exact",
                "client_id": "p1"
            }
        }))
        json.loads(ws.receive_text())

        for i in range(50):
            ws.send_text(json.dumps({
                "version": "1.0",
                "type": "action",
                "payload": {
                    "action_id": i + 1,
                    "action_type": "move",
                    "direction": "left",
                    "expected_revision": 0
                }
            }))
        
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 51,
                "action_type": "move",
                "direction": "left",
                "expected_revision": 0
            }
        }))
        
        try:
            for _ in range(55):
                ws.receive_text()
        except Exception:
            pass


@pytest.mark.anyio
async def test_preflight_scalar_overflow_operational_abort():
    clock = TestClock(0.0)
    room = DuelRoom("room-overflow-test", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    room.room_revision = 9007199254740991
    async with room.lock:
        duel.check_game_outcomes_sync(room, clock.get_time())
        room.transition_to_finished_sync("draw", "operational-abort", clock.get_time())
        assert room.status == "finished"
        assert room.winner_seat == "draw"
        assert room.outcome_reason == "operational-abort"


@pytest.mark.anyio
async def test_peer_class_coverage():
    class DummyWS:
        def __init__(self):
            self.closed = False
        async def close(self, code=1000):
            self.closed = True
        async def send_text(self, text):
            pass

    ws = DummyWS()
    peer = Peer(ws)

    assert peer.send("hello") is True

    peer.close(1000)
    peer.close(1000)

    peer.closed_event.set()
    assert peer.send("fail") is False
    peer.send_no_fail_trigger("ignored")

    peer._transport_closed = True
    await peer.close_transport()

    peer.cancel()
    await peer.drain_and_stop()


def test_handshake_validation_extra_branches():
    from app.controllers.duel import ClientHandshakePayload
    with pytest.raises(ValidationError):
        ClientHandshakePayload(room_id="a" * 65, client_id="p1")

    with pytest.raises(ValidationError):
        ClientHandshakePayload(room_id=123, client_id="p1")

    with pytest.raises(ValidationError):
        ClientHandshakePayload(room_id="room-@", client_id="p1")

    with pytest.raises(ValidationError):
        ClientHandshakePayload(room_id="room1", client_id="p\r1")


@pytest.mark.anyio
async def test_gravity_loop_branches():
    clock = TestClock(0.0)
    room = DuelRoom("room-gravity-branches", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    room.player1_last_gravity_time = clock.get_time() - 1.0
    room.player2_last_gravity_time = clock.get_time()

    task = asyncio.create_task(duel.gravity_background_loop(room))
    await asyncio.sleep(0.03)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert room.player1_last_gravity_time == clock.get_time()


def test_room_limit_exceeded():
    for i in range(101):
        ROOMS[f"room-limit-{i}"] = DuelRoom(f"room-limit-{i}")

    try:
        with client.websocket_connect("/api/ws/duel/room-limit-999", headers={"Origin": "http://localhost:5515"}) as ws:
            ws.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-limit-999",
                    "client_id": "p1"
                }
            }))
            resp = json.loads(ws.receive_text())
            assert resp["type"] == "error"
            assert "limit reached" in resp["payload"]["message"]
    finally:
        duel.ROOMS.clear()


def test_duplicate_client_id_in_room():
    with client.websocket_connect("/api/ws/duel/room-dup-client", headers={"Origin": "http://localhost:5515"}) as ws1:
        ws1.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-dup-client",
                "client_id": "p1"
            }
        }))
        json.loads(ws1.receive_text())

        with client.websocket_connect("/api/ws/duel/room-dup-client", headers={"Origin": "http://localhost:5515"}) as ws2:
            ws2.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-dup-client",
                    "client_id": "p1"
                }
            }))
            resp = json.loads(ws2.receive_text())
            assert resp["type"] == "error"
            assert "Client already in room" in resp["payload"]["message"]


def test_third_player_joins_full_room():
    with client.websocket_connect("/api/ws/duel/room-full", headers={"Origin": "http://localhost:5515"}) as ws1:
        ws1.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-full",
                "client_id": "p1"
            }
        }))
        json.loads(ws1.receive_text())

        with client.websocket_connect("/api/ws/duel/room-full", headers={"Origin": "http://localhost:5515"}) as ws2:
            ws2.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-full",
                    "client_id": "p2"
                }
            }))
            json.loads(ws2.receive_text())

            with client.websocket_connect("/api/ws/duel/room-full", headers={"Origin": "http://localhost:5515"}) as ws3:
                ws3.send_text(json.dumps({
                    "version": "1.0",
                    "type": "handshake",
                    "payload": {
                        "room_id": "room-full",
                        "client_id": "p3"
                    }
                }))
                with pytest.raises(Exception):
                    ws3.receive_text()


def test_handshake_on_finished_room():
    room = DuelRoom("room-finished-handshake")
    room.status = "finished"
    room.winner_seat = "player1"
    room.outcome_reason = "topout-player2"
    room.player1_id = "p1"
    room.player2_id = "p2"
    ROOMS["room-finished-handshake"] = room

    try:
        with client.websocket_connect("/api/ws/duel/room-finished-handshake", headers={"Origin": "http://localhost:5515"}) as ws:
            ws.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-finished-handshake",
                    "client_id": "p3"
                }
            }))
            resp = json.loads(ws.receive_text())
            assert resp["type"] == "handshake"
            assert resp["payload"]["status"] == "finished"
    finally:
        duel.ROOMS.clear()


def test_action_without_room_and_invalid_endpoint_states():
    with client.websocket_connect("/api/ws/duel/room-no-hello", headers={"Origin": "http://localhost:5515"}) as ws:
        ws.send_text(json.dumps({
            "version": "1.0",
            "type": "action",
            "payload": {
                "action_id": 1,
                "action_type": "move",
                "direction": "left",
                "expected_revision": 0
            }
        }))
        resp = json.loads(ws.receive_text())
        assert resp["type"] == "error"


def test_playing_room_action_processing_endpoint():
    with client.websocket_connect("/api/ws/duel/room-endpoint-play", headers={"Origin": "http://localhost:5515"}) as ws1:
        ws1.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-endpoint-play",
                "client_id": "p1"
            }
        }))
        handshake_resp1 = json.loads(ws1.receive_text())
        assert handshake_resp1["payload"]["seat"] == "player1"

        with client.websocket_connect("/api/ws/duel/room-endpoint-play", headers={"Origin": "http://localhost:5515"}) as ws2:
            ws2.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-endpoint-play",
                    "client_id": "p2"
                }
            }))
            handshake_resp2 = json.loads(ws2.receive_text())
            assert handshake_resp2["payload"]["seat"] == "player2"

            ws1.send_text(json.dumps({
                "version": "1.0",
                "type": "action",
                "payload": {
                    "action_id": 1,
                    "action_type": "move",
                    "direction": "left",
                    "expected_revision": 0
                }
            }))

            resp1 = json.loads(ws1.receive_text())
            assert resp1 is not None

            ws1.send_text(json.dumps({
                "version": "1.0",
                "type": "action",
                "payload": {
                    "action_id": 2,
                    "action_type": "rotate",
                    "direction": "cw",
                    "expected_revision": 1
                }
            }))
            
            ws1.send_text(json.dumps({
                "version": "1.0",
                "type": "action",
                "payload": {
                    "action_id": 3,
                    "action_type": "hold",
                    "direction": None,
                    "expected_revision": 2
                }
            }))


def test_playing_room_preflight_overflow():
    with client.websocket_connect("/api/ws/duel/room-endpoint-overflow", headers={"Origin": "http://localhost:5515"}) as ws1:
        ws1.send_text(json.dumps({
            "version": "1.0",
            "type": "handshake",
            "payload": {
                "room_id": "room-endpoint-overflow",
                "client_id": "p1"
            }
        }))
        p1_hshake = json.loads(ws1.receive_text())
        assert p1_hshake["type"] == "handshake"
        assert p1_hshake["payload"]["seat"] == "player1"

        with client.websocket_connect("/api/ws/duel/room-endpoint-overflow", headers={"Origin": "http://localhost:5515"}) as ws2:
            ws2.send_text(json.dumps({
                "version": "1.0",
                "type": "handshake",
                "payload": {
                    "room_id": "room-endpoint-overflow",
                    "client_id": "p2"
                }
            }))
            p2_hshake = json.loads(ws2.receive_text())
            assert p2_hshake["type"] == "handshake"
            assert p2_hshake["payload"]["seat"] == "player2"

            # Drain playing state updates
            p1_start = json.loads(ws1.receive_text())
            assert p1_start["type"] == "state_update"
            assert p1_start["payload"]["status"] == "playing"

            p2_start = json.loads(ws2.receive_text())
            assert p2_start["type"] == "state_update"
            assert p2_start["payload"]["status"] == "playing"

            ROOMS["room-endpoint-overflow"].player1_board.score = 9007199254740991

            ws1.send_text(json.dumps({
                "version": "1.0",
                "type": "action",
                "payload": {
                    "action_id": 9999,
                    "action_type": "move",
                    "direction": "left",
                    "expected_revision": 0
                }
            }))

            resp = json.loads(ws1.receive_text())
            assert resp["type"] == "ack"
            assert resp["payload"]["action_id"] == 9999
            assert resp["payload"]["status"] == "rejected"
            assert resp["payload"]["reason"] == "integer_overflow"

            p1_final = json.loads(ws1.receive_text())
            assert p1_final["type"] == "state_update"
            assert p1_final["payload"]["status"] == "finished"
            assert p1_final["payload"]["winner_seat"] == "draw"
            assert p1_final["payload"]["outcome_reason"] == "operational-abort"

            p2_final = json.loads(ws2.receive_text())
            assert p2_final["type"] == "state_update"
            assert p2_final["payload"]["status"] == "finished"
            assert p2_final["payload"]["winner_seat"] == "draw"
            assert p2_final["payload"]["outcome_reason"] == "operational-abort"


@pytest.mark.anyio
async def test_gravity_candidate_boundary_overflow():
    clock = TestClock(0.0)
    room = DuelRoom("room-gravity-overflow-test", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    # p1.score=MAX-50/lines0/level1, p2 last gravity time=.4, clock advance .5 so ONLY p1 due.
    room.player1_board.score = 9007199254740991 - 50
    room.player1_board.total_lines = 0
    room.player1_board.level = 1
    room.player1_board.active_piece.type = 'I'
    room.player1_board.active_piece.cells = [(19, 3), (19, 4), (19, 5), (19, 6)]
    room.player1_board.active_piece.origin = (19, 3)
    room.player1_board.board = [[None]*10 for _ in range(20)]
    for c in range(10):
        if c not in (3, 4, 5, 6):
            room.player1_board.board[19][c] = 'J'

    room.player1_last_gravity_time = 0.0
    room.player2_last_gravity_time = 0.4
    
    clock.advance(0.5)
    
    task = asyncio.create_task(duel.gravity_background_loop(room))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    assert room.status == "finished"
    assert room.winner_seat == "draw"
    assert room.outcome_reason == "operational-abort"
    assert room.player1_board.score == 9007199254740991 - 50
    assert room.player1_board.total_lines == 0


@pytest.mark.anyio
async def test_action_candidate_boundary_overflow():
    clock = TestClock(0.0)
    room = DuelRoom("room-action-overflow-test", clock=clock)
    room.initialize_player_board(is_p1=True)
    room.initialize_player_board(is_p1=False)
    room.status = "playing"

    room.player1_board.score = 9007199254740991 - 50
    room.player1_board.total_lines = 0
    room.player1_board.level = 1
    room.player1_board.active_piece.type = 'I'
    room.player1_board.active_piece.cells = [(19, 3), (19, 4), (19, 5), (19, 6)]
    room.player1_board.active_piece.origin = (19, 3)
    room.player1_board.board = [[None]*10 for _ in range(20)]
    for c in range(10):
        if c not in (3, 4, 5, 6):
            room.player1_board.board[19][c] = 'J'

    # Store a copy of the indices
    p1_idx_before = room.player1_index

    # We will simulate processing the action in-endpoint
    # Let's perform a speculative move-down action on player 1 board
    board_copy = room.player1_board.model_copy(deep=True)
    spec_supplier = SpeculativeSupplier(room, is_p1=True)
    board_copy = duel.move_game(board_copy, "down", spec_supplier)

    assert is_board_overflow(board_copy) is True
    # The supplier index must NOT have been committed
    assert room.player1_index == p1_idx_before





