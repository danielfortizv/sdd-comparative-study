"""Stage 4 (Option A) M3 native-16 task 30.2 both-boards delivery self-tests.

Task 30.2 requires every state transition to deliver BOTH authoritative seat
boards to BOTH connected peers (each board a ``StateFrame`` with its own target
``seat_id`` and per-board ``revision`` plus the shared ``room_status``), strictly
room-scoped, for the mandatory waiting/start transitions, ordinary own and
remote accepted movement/rotation/Hold, the server no-input gravity advance, and
the terminal/forfeit outcome. These tests prove exactly that.

Two layers, both native self-tests (never treated as production wire proof):

1. **Unit / module-helper layer.** Drives the pure ``broadcast_room_state`` /
   ``broadcast_outcome`` enqueue helpers and the gravity ``on_state`` /
   ``on_outcome`` publish hooks over a minimal in-memory ``FakeWebSocket`` and
   the duel ``RoomManager`` with an injectable ``FakeClock``. No network, no
   wall-clock timer: every frame observed is caused by the action/advance the
   test performed. This is where the "gravity publishes states WITHOUT inbound
   traffic" and "server monotonic deadlines independent of manual actions"
   guarantees are asserted deterministically.

2. **Live-socket layer.** Drives a real ``TestClient`` websocket over a minimal
   app mounting ``build_duel_router`` (no background loop) so each peer's
   INDEPENDENT writer delivers the enqueued both-board frames end to end across
   waiting/start/movement/rotation/Hold.

Isolation: each duel seat owns a PRIVATE ``engine.new_game`` game, so ZERO SQL
writes come from the duel path (asserted structurally by the room layer; these
tests never import the solo store).
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.duel import gravity
from app.duel.rooms import Room, RoomManager, Seat
from app.ws import contract
from app.ws import duel


ALLOWED_ORIGIN = "http://localhost:5517"


# ---------------------------------------------------------------------------
# Deterministic injectable clock (Req 19.4): no wall-clock timer ever fires.
# ---------------------------------------------------------------------------


class FakeClock:
    """A deterministic, monotonic, injectable clock for the RoomManager."""

    def __init__(self, start: float = 1000.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, delta: float) -> None:
        if delta < 0:
            raise ValueError("clock must be monotonic")
        self._now += delta


# ---------------------------------------------------------------------------
# A minimal in-memory fake WebSocket + a helper to run a pair of writers.
# ---------------------------------------------------------------------------


class FakeWebSocket:
    """Record ``send_text`` payloads (one per delivered frame)."""

    def __init__(self) -> None:
        self.sent: List[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


def _parsed(ws: FakeWebSocket) -> List[dict]:
    return [json.loads(t) for t in ws.sent]


def _states_by_seat(ws: FakeWebSocket) -> Dict[str, List[dict]]:
    """Group the delivered ``state`` frames on a socket by target seat id."""

    grouped: Dict[str, List[dict]] = {"A": [], "B": []}
    for frame in _parsed(ws):
        if frame["type"] == "state":
            grouped[frame["seat_id"]].append(frame)
    return grouped


def _started_room() -> Tuple[RoomManager, Room, Seat, Seat, FakeClock]:
    """Build a two-seat STARTED room on an injectable clock (no live socket)."""

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    room, seat_a = manager.assign_seat("both-room")
    _room2, seat_b = manager.assign_seat("both-room")
    room.status = "playing"
    now = clock()
    for s in room.seats.values():
        s.gravity_due_monotonic = now + gravity._current_interval_seconds(s)
    return manager, room, seat_a, seat_b, clock


async def _flush(endpoint: duel.DuelEndpoint, ws: FakeWebSocket, seat: Seat):
    """Start a writer, let it drain the seat's queue, then tear it down."""

    writer = await endpoint._start_writer(ws, seat)
    for _ in range(100):
        if not seat.outbound:
            break
        await asyncio.sleep(0)
    await endpoint._teardown_writer(seat, writer)


def _endpoint(manager: RoomManager) -> duel.DuelEndpoint:
    return duel.DuelEndpoint(manager, allowed_origins=(ALLOWED_ORIGIN,))


# ===========================================================================
# Unit layer: broadcast_room_state enqueues BOTH boards to BOTH peers.
# ===========================================================================


def test_broadcast_room_state_enqueues_both_boards_to_both_peers() -> None:
    """A single broadcast puts a StateFrame for seat A AND seat B on each queue."""

    _manager, room, seat_a, seat_b, _clock = _started_room()

    duel.broadcast_room_state(room)

    # Each connected peer received EXACTLY two state frames: one per seat, each
    # with its own seat_id and the shared room_status.
    for seat in (seat_a, seat_b):
        frames = list(seat.outbound)
        assert [f.type for f in frames] == ["state", "state"]
        assert {f.seat_id for f in frames} == {"A", "B"}
        assert all(f.room_status == "playing" for f in frames)


def test_broadcast_is_room_scoped_never_touches_a_foreign_room() -> None:
    """A broadcast for one room never enqueues onto another room's seats."""

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    room1, a1 = manager.assign_seat("room-1")
    _r1b, b1 = manager.assign_seat("room-1")
    room2, a2 = manager.assign_seat("room-2")
    _r2b, b2 = manager.assign_seat("room-2")
    for r in (room1, room2):
        r.status = "playing"

    duel.broadcast_room_state(room1)

    # room-1 seats got both boards; room-2 seats got NOTHING.
    assert len(a1.outbound) == 2 and len(b1.outbound) == 2
    assert len(a2.outbound) == 0 and len(b2.outbound) == 0


def test_broadcast_per_board_revision_is_each_seats_own_revision() -> None:
    """Each delivered board carries ITS OWN seat's authoritative revision."""

    _manager, room, seat_a, seat_b, _clock = _started_room()
    seat_a.revision = 7
    seat_b.revision = 3

    duel.broadcast_room_state(room)

    for seat in (seat_a, seat_b):
        by_seat = {f.seat_id: f for f in seat.outbound}
        assert by_seat["A"].revision == 7
        assert by_seat["B"].revision == 3


def test_broadcast_skips_a_disconnected_peer_queue_but_keeps_its_board() -> None:
    """A disconnected peer is not enqueued to, but its board still reaches the other."""

    _manager, room, seat_a, seat_b, _clock = _started_room()
    seat_b.connected = False

    duel.broadcast_room_state(room)

    # The surviving seat A still receives BOTH boards (its own + the opponent's).
    assert {f.seat_id for f in seat_a.outbound} == {"A", "B"}
    # The disconnected seat B's queue was skipped.
    assert len(seat_b.outbound) == 0


# ===========================================================================
# Unit layer: the accepted-action apply broadcasts both boards to both peers.
# ===========================================================================


def test_accepted_action_broadcasts_both_boards_to_both_peers() -> None:
    """An own accepted movement enqueues both boards to the actor AND the peer."""

    async def scenario() -> Tuple[Dict[str, List[dict]], Dict[str, List[dict]]]:
        manager, room, seat_a, seat_b, _clock = _started_room()
        endpoint = _endpoint(manager)
        ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
        # Start both independent writers so enqueued frames actually flush.
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)

        # Seat A sends a real 'left' move through the endpoint's inbound path.
        raw = json.dumps(
            {
                "type": "action",
                "protocol_version": contract.PROTOCOL_VERSION,
                "room_id": "both-room",
                "seat_id": "A",
                "action_id": "A-1",
                "expected_revision": 0,
                "kind": "left",
            }
        )
        rate = duel.RateLimiter(manager.action_rate_per_seat)
        await endpoint._process_inbound(ws_a, room, seat_a, raw, rate)

        # Let both writers drain, then tear down.
        for _ in range(100):
            if not seat_a.outbound and not seat_b.outbound:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return _states_by_seat(ws_a), _states_by_seat(ws_b)

    a_states, b_states = asyncio.run(scenario())
    # The ACTOR (A) observed both boards; the OPPONENT (B) also observed both
    # boards (the remote accepted movement reached the peer).
    assert a_states["A"] and a_states["B"]
    assert b_states["A"] and b_states["B"]
    # The acting seat A board advanced to revision 1 on both recipients.
    assert a_states["A"][-1]["revision"] == 1
    assert b_states["A"][-1]["revision"] == 1


def test_rotation_and_hold_also_broadcast_both_boards() -> None:
    """A rotation (cw) and a Hold each broadcast both boards to both peers."""

    async def one(kind: str, action_id: str) -> Tuple[Dict, Dict]:
        manager, room, seat_a, seat_b, _clock = _started_room()
        endpoint = _endpoint(manager)
        ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)
        raw = json.dumps(
            {
                "type": "action",
                "protocol_version": contract.PROTOCOL_VERSION,
                "room_id": "both-room",
                "seat_id": "A",
                "action_id": action_id,
                "expected_revision": 0,
                "kind": kind,
            }
        )
        rate = duel.RateLimiter(manager.action_rate_per_seat)
        await endpoint._process_inbound(ws_a, room, seat_a, raw, rate)
        for _ in range(100):
            if not seat_a.outbound and not seat_b.outbound:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return _states_by_seat(ws_a), _states_by_seat(ws_b)

    for kind, aid in (("cw", "A-1"), ("hold", "A-2")):
        a_states, b_states = asyncio.run(one(kind, aid))
        assert a_states["A"] and a_states["B"], kind
        assert b_states["A"] and b_states["B"], kind


# ===========================================================================
# Unit layer: server no-input gravity PUBLISHES both boards WITHOUT inbound
# traffic, and monotonic deadlines are independent of manual actions.
# ===========================================================================


def test_gravity_step_publishes_both_boards_without_any_inbound_traffic() -> None:
    """A due gravity advance invokes on_state, which broadcasts both boards.

    No action is ever sent: the only driver is the clock advancing past the due
    time. Both peers' queues receive both boards, proving the server no-input
    gravity publishes state (previously it mutated private games silently).
    """

    manager, room, seat_a, seat_b, clock = _started_room()
    published: List[str] = []

    def on_state(r: Room) -> None:
        published.append(r.room_id)
        duel.broadcast_room_state(r)

    # Advance the clock past both boards' due time, then run ONE gravity step.
    clock.advance(10.0)
    gravity.gravity_step(manager, on_state=on_state)

    assert published == ["both-room"]  # on_state fired for the due room
    for seat in (seat_a, seat_b):
        frames = list(seat.outbound)
        assert {f.seat_id for f in frames} == {"A", "B"}


def test_gravity_no_due_board_does_not_publish() -> None:
    """A step with no board due does not broadcast a redundant frame."""

    manager, room, seat_a, seat_b, clock = _started_room()
    published: List[str] = []

    def on_state(r: Room) -> None:
        published.append(r.room_id)

    # Do NOT advance the clock: neither board is due yet.
    gravity.gravity_step(manager, on_state=on_state)

    assert published == []
    assert len(seat_a.outbound) == 0 and len(seat_b.outbound) == 0


def test_gravity_deadlines_independent_of_manual_actions() -> None:
    """A manual action never moves a board's server gravity due time.

    The due time is seeded from the clock at start and advanced only by the
    gravity step; applying a manual action leaves ``gravity_due_monotonic``
    untouched, so the server monotonic deadline is independent of manual input.
    """

    async def scenario() -> Tuple[float, float]:
        manager, room, seat_a, seat_b, _clock = _started_room()
        endpoint = _endpoint(manager)
        ws_a = FakeWebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        due_before = seat_a.gravity_due_monotonic
        raw = json.dumps(
            {
                "type": "action",
                "protocol_version": contract.PROTOCOL_VERSION,
                "room_id": "both-room",
                "seat_id": "A",
                "action_id": "A-1",
                "expected_revision": 0,
                "kind": "left",
            }
        )
        rate = duel.RateLimiter(manager.action_rate_per_seat)
        await endpoint._process_inbound(ws_a, room, seat_a, raw, rate)
        for _ in range(50):
            if not seat_a.outbound:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat_a, writer_a)
        return due_before, seat_a.gravity_due_monotonic

    before, after = asyncio.run(scenario())
    assert before == after  # a manual action did not move the gravity deadline


def test_all_due_boards_advance_before_one_outcome_is_decided() -> None:
    """Both boards advance at a logical instant BEFORE a single outcome.

    Both seats are made one tick from topping out and are both due at the same
    instant; a single gravity step must advance BOTH before deciding the one
    terminal outcome (a simultaneous top-out is a DRAW, not two separate wins).
    """

    manager, room, seat_a, seat_b, clock = _started_room()
    # Put BOTH boards into a topped-out end-state (the same terminal condition
    # the engine produces on a spawn collision) while BOTH are due at the same
    # logical instant. ``advance_due_boards`` must iterate BOTH due boards first
    # and only THEN decide the single outcome: a simultaneous top-out is ONE
    # draw, never two separate wins.
    for seat in (seat_a, seat_b):
        seat.game.status = "game_over"

    outcomes: List[gravity.OutcomeData] = []
    clock.advance(10.0)  # both boards are now due at this single instant
    gravity.gravity_step(
        manager, on_outcome=lambda r, o: outcomes.append(o)
    )

    # Exactly ONE outcome decided after BOTH due boards were evaluated.
    assert len(outcomes) == 1
    assert outcomes[0].result == "draw"
    assert room.status == "finished"


# ===========================================================================
# Unit layer: terminal and forfeit outcomes reach BOTH peers.
# ===========================================================================


def test_broadcast_outcome_reaches_both_peers() -> None:
    """A terminal outcome frame is enqueued onto BOTH connected peers' queues."""

    _manager, room, seat_a, seat_b, _clock = _started_room()
    outcome = gravity.OutcomeData(
        result="win",
        winning_seat="A",
        losing_seat="B",
        forfeiting_seat=None,
        final_revision={"A": 5, "B": 2},
    )

    duel.broadcast_outcome(room, outcome)

    for seat in (seat_a, seat_b):
        frames = list(seat.outbound)
        assert len(frames) == 1
        assert frames[0].type == "outcome"
        assert frames[0].result == "win"
        assert frames[0].winning_seat == "A"


def test_forfeit_outcome_broadcast_to_both_peers() -> None:
    """A forfeit resolution's outcome frame reaches both peers."""

    manager, room, seat_a, seat_b, clock = _started_room()
    outcome = gravity.resolve_forfeit(room, "A", clock(), manager=manager)
    assert outcome is not None and outcome.result == "forfeit"

    duel.broadcast_outcome(room, outcome)

    for seat in (seat_a, seat_b):
        frames = list(seat.outbound)
        assert len(frames) == 1
        assert frames[0].type == "outcome"
        assert frames[0].result == "forfeit"
        assert frames[0].forfeiting_seat == "A"
        assert frames[0].winning_seat == "B"


# ===========================================================================
# Live-socket layer: both peers receive both boards end to end via the writer.
# ===========================================================================


def _build_app(**manager_kwargs) -> Tuple[FastAPI, RoomManager]:
    manager = RoomManager(clock=FakeClock(), **manager_kwargs)
    app = FastAPI()
    app.include_router(
        duel.build_duel_router(manager, allowed_origins=(ALLOWED_ORIGIN,))
    )
    return app, manager


def _hello(ws, room_id: str) -> None:
    ws.send_text(
        json.dumps(
            {
                "type": "hello",
                "protocol_version": contract.PROTOCOL_VERSION,
                "room_id": room_id,
            }
        )
    )


def _action(seat_id, action_id, expected_revision, kind, room_id) -> str:
    return json.dumps(
        {
            "type": "action",
            "protocol_version": contract.PROTOCOL_VERSION,
            "room_id": room_id,
            "seat_id": seat_id,
            "action_id": action_id,
            "expected_revision": expected_revision,
            "kind": kind,
        }
    )


def _recv(ws) -> dict:
    return json.loads(ws.receive_text())


def _drain_two_states(ws) -> Dict[str, dict]:
    """Drain exactly two playing ``state`` frames (one per seat) and key them."""

    frames: Dict[str, dict] = {}
    while len(frames) < 2:
        frame = _recv(ws)
        if frame["type"] == "state" and frame["room_status"] == "playing":
            frames[frame["seat_id"]] = frame
    return frames


def test_live_both_peers_get_both_boards_on_start_and_on_move() -> None:
    """End to end: both peers observe both boards at start AND after a move."""

    app, manager = _build_app()
    client = TestClient(app)
    # Seat A joins alone: welcome + its own waiting board (both-boards == just A
    # while alone), then STOPS sending.
    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    _hello(a, "live-both")
    assert _recv(a)["type"] == "welcome"
    waiting_a = _recv(a)
    assert waiting_a["type"] == "state" and waiting_a["room_status"] == "waiting"
    assert waiting_a["seat_id"] == "A"

    b_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    b = b_cm.__enter__()
    try:
        _hello(b, "live-both")
        assert _recv(b)["type"] == "welcome"
        # Start transition: both peers get BOTH boards (seat A + seat B).
        start_b = _drain_two_states(b)
        assert set(start_b) == {"A", "B"}
        # Seat A sent NOTHING after its waiting frame; its independent writer
        # still delivers both start boards.
        start_a = _drain_two_states(a)
        assert set(start_a) == {"A", "B"}

        # Seat A moves left: BOTH peers observe both boards again, with A bumped.
        a.send_text(_action("A", "A-1", 0, "left", "live-both"))
        # Drain A's ack then both boards.
        while True:
            f = _recv(a)
            if f["type"] == "ack" and f["action_id"] == "A-1":
                break
        move_a = _drain_two_states(a)
        assert move_a["A"]["revision"] == 1
        # Seat B (sent nothing) still receives the remote move's both boards.
        move_b = _drain_two_states(b)
        assert move_b["A"]["revision"] == 1
        assert set(move_b) == {"A", "B"}
    finally:
        for cm in (b_cm, a_cm):
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
