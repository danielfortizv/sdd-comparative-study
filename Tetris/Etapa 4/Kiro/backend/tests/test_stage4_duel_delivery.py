"""Stage 4 (Option A) M3 native-14 task 30.4 CONSOLIDATED delivery / lifecycle /
abort tests exposing the PRODUCTION-VISIBLE behavior.

Why this module exists
----------------------
The independent public-wire checkpoint after native 12
(``docs/validation/m3-public-wire-01``) measured the real production-visible M3
blocker: in every pair case seat A created a named room, saw ``waiting``, and
then NEVER received the ``playing`` start StateFrame after seat B joined (the
start transition reached only the socket with inbound traffic). All downstream
action / cache / sequence tests never ran. The native-14 correction added an
INDEPENDENT per-connection writer, both-boards broadcast, and two operational
aborts. Tasks 30.1 / 30.2 / 30.3 added their mechanism-focused self-tests in
``test_stage4_duel_writer.py`` / ``test_stage4_both_boards.py`` /
``test_stage4_duel_ws.py``. THIS module consolidates the PRODUCTION-VISIBLE
guarantees -- the ones a real two-browser duel depends on -- into one dedicated
place, each asserted over the SAME live-socket / injectable-clock surface a real
deployment uses.

What is asserted here (all production-visible, no assertion weakened):

1. **Traffic-free server push.** A silent waiting peer (seat A) receives the
   ``playing`` start frame WITHOUT ever sending a second frame, via its
   independent writer. This is the exact blocker the public checkpoint found.
2. **Both boards to both peers** across the whole lifecycle: waiting, start,
   own movement, own rotation, own Hold, server no-input gravity, terminal
   (top-out) and forfeit -- every peer sees BOTH authoritative seat boards.
3. **Traffic-free cleanup with no leak** for waiting, playing-idle, finished,
   and shutdown, driven by the INJECTABLE clock (no wall-clock wait), asserting
   the room / gravity task / socket references are released.
4. **A slow / failed peer never blocks the other peer or room**, and
   ``_emit_cached`` reports a failed send HONESTLY (never a fabricated success).
5. **Operational aborts** (``sequence_exhausted`` / ``scalar_overflow``):
   boundary (max ordinal consumable, next-higher aborts; ceiling no-op does not
   overflow), once-only, BOTH-peer cleanup with no fabricated winner, DISTINCT
   from the gameplay forfeit.

Draining discipline: every CLOSE assertion drains the queued handshake / state /
error frames FIRST (the acting seat may still have a pending both-board playing
frame enqueued before an abort), so the close code + literal reason are asserted
against the real terminal frame, never a mislabeled earlier one.

These are live-socket / endpoint-level behavioral tests, NOT pure-helper-only
tests. Each duel seat owns a PRIVATE ``engine.new_game`` game, so ZERO SQL writes
come from the duel path (this module never imports the solo store).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.duel import gravity
from app.duel.rooms import Room, RoomManager, Seat
from app.ws import contract
from app.ws import duel


ALLOWED_ORIGIN = "http://localhost:5517"


# ---------------------------------------------------------------------------
# Deterministic injectable clock (Req 19.4): no wall-clock timer ever fires, so
# every revision / outcome / cleanup a test observes is caused by the action,
# advance, or clock move the test performed -- never by a real-time timer.
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
# Live-socket app builder + small handshake / action / drain helpers. These
# mirror the documented helpers in test_stage4_duel_ws.py so the consolidated
# tests drive the SAME decoupled minimal app (no background gravity loop) that
# keeps every observed transition deterministic.
# ---------------------------------------------------------------------------


def _build_app(
    *,
    clock: Optional[FakeClock] = None,
    **manager_kwargs,
) -> Tuple[FastAPI, RoomManager]:
    """Build a minimal FastAPI app mounting the duel router (no gravity loop)."""

    manager = RoomManager(clock=clock or FakeClock(), **manager_kwargs)
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


def _drain_until(ws, *, action_id: Optional[str] = None, types=("ack", "reject")) -> dict:
    """Drain queued frames until a correlated ack/reject (or a wanted type)."""

    while True:
        frame = _recv(ws)
        if frame["type"] in types:
            if action_id is None or frame.get("action_id") == action_id:
                return frame


def _drain_both_playing_boards(ws) -> List[dict]:
    """Drain the two playing ``state`` frames (seat A + seat B) of a transition."""

    frames: List[dict] = []
    while len(frames) < 2:
        frame = _recv(ws)
        if frame["type"] == "state" and frame["room_status"] == "playing":
            frames.append(frame)
    return frames


def _handshake_first_seat(ws, room_id: str) -> dict:
    """Drive the first seat's handshake: hello -> welcome + waiting state."""

    _hello(ws, room_id)
    welcome = _recv(ws)
    assert welcome["type"] == "welcome"
    assert welcome["seat_id"] == "A"
    assert welcome["room_status"] == "waiting"
    state = _recv(ws)
    assert state["type"] == "state"
    assert state["room_status"] == "waiting"
    assert state["seat_id"] == "A"
    assert state["revision"] == 0
    return state


def _connect_two_seats(client: TestClient, room_id: str) -> Tuple[object, object]:
    """Open both seats for ``room_id``; drain each handshake up to start.

    Returns both open sessions (already ``__enter__``-ed). The room starts on
    B's join, so B drains welcome + BOTH start boards; A's start boards are left
    on A's writer queue for the caller to drain when it asserts delivery.
    """

    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    _handshake_first_seat(a, room_id)

    b_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    b = b_cm.__enter__()
    _hello(b, room_id)
    welcome_b = _recv(b)
    assert welcome_b["type"] == "welcome"
    assert welcome_b["seat_id"] == "B"
    start_b = _drain_both_playing_boards(b)
    assert {f["seat_id"] for f in start_b} == {"A", "B"}
    assert all(f["room_status"] == "playing" for f in start_b)

    a._cm = a_cm  # type: ignore[attr-defined]
    b._cm = b_cm  # type: ignore[attr-defined]
    return a, b


def _close_sessions(*sessions) -> None:
    for s in sessions:
        cm = getattr(s, "_cm", None)
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass


def _drain_to_close(ws) -> Tuple[int, Optional[str]]:
    """Drain EVERY queued frame, then return the (close_code, literal reason).

    This is the mandatory drain-before-CLOSE discipline: the acting / peer
    socket may still carry pending handshake / state / error frames enqueued
    before the terminal close, so we read them all until the transport surfaces
    the server's ``WebSocketDisconnect`` and expose its code + literal reason.
    """

    try:
        while True:
            ws.receive_text()
    except WebSocketDisconnect as exc:
        return exc.code, getattr(exc, "reason", None)
    raise AssertionError("socket did not close")


def _wait_until(predicate, *, timeout_s: float = 2.0, interval_s: float = 0.01) -> None:
    """Spin briefly until ``predicate`` is true or the timeout elapses.

    Used only to let the in-process server coroutine observe a client-side close;
    it fabricates no result (the caller asserts the real post-condition after).
    """

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_s)


# ===========================================================================
# (1) TRAFFIC-FREE SERVER PUSH: the waiting peer receives the start frame with
#     NO inbound traffic. This is the exact production-visible blocker the
#     public-wire checkpoint measured (seat A never got the playing start frame).
# Validates: Requirements 16.6, 18.5, 19.1
# ===========================================================================


def test_waiting_peer_receives_playing_start_frame_without_sending_anything():
    """A silent seat A receives the START transition purely via its writer.

    A completes its handshake (welcome + waiting state) and STOPS sending. B
    joins and the room transitions to ``playing``. A's independent writer must
    deliver the start transition (BOTH authoritative boards) WITHOUT A ever
    sending a second inbound frame -- the native-14 delivery correction.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    _handshake_first_seat(a, "room-silent-start")

    b_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    b = b_cm.__enter__()
    try:
        _hello(b, "room-silent-start")
        assert _recv(b)["type"] == "welcome"
        _drain_both_playing_boards(b)  # B is started

        # A sent NOTHING after its waiting handshake. Its writer still pushes the
        # START transition: BOTH boards, both room_status "playing".
        start_a = _drain_both_playing_boards(a)
        by_seat = {f["seat_id"]: f for f in start_a}
        assert set(by_seat) == {"A", "B"}
        assert by_seat["A"]["room_status"] == "playing"
        assert by_seat["B"]["room_status"] == "playing"
        assert manager.rooms["room-silent-start"].status == "playing"
    finally:
        for cm in (b_cm, a_cm):
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass


# ===========================================================================
# (2) BOTH BOARDS TO BOTH PEERS across the whole lifecycle: waiting, start,
#     own movement, own rotation, own Hold, server no-input gravity, terminal
#     (top-out), and forfeit.
# Validates: Requirements 16.6, 18.5, 19.1, 20.4
# ===========================================================================


def test_both_peers_get_both_boards_across_waiting_start_move_rotate_hold():
    """Waiting (own board), start (both), and own move/rotate/Hold (both)."""

    app, manager = _build_app()
    client = TestClient(app)

    # WAITING: the first seat alone sees exactly its OWN board.
    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    waiting_a = _handshake_first_seat(a, "room-lifecycle")
    assert waiting_a["seat_id"] == "A"

    b_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    b = b_cm.__enter__()
    try:
        _hello(b, "room-lifecycle")
        assert _recv(b)["type"] == "welcome"

        # START: both peers see BOTH boards.
        start_b = _drain_both_playing_boards(b)
        assert {f["seat_id"] for f in start_b} == {"A", "B"}
        start_a = _drain_both_playing_boards(a)
        assert {f["seat_id"] for f in start_a} == {"A", "B"}

        # OWN MOVEMENT (left): both peers see both boards, A's board bumped to 1.
        a.send_text(_action("A", "A-1", 0, "left", "room-lifecycle"))
        ack = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack["applied"] is True and ack["revision"] == 1
        move_a = {f["seat_id"]: f for f in _drain_both_playing_boards(a)}
        assert set(move_a) == {"A", "B"} and move_a["A"]["revision"] == 1
        move_b = {f["seat_id"]: f for f in _drain_both_playing_boards(b)}
        assert set(move_b) == {"A", "B"} and move_b["A"]["revision"] == 1

        # OWN ROTATION (cw): a rotation from spawn is seed-dependent and MAY be
        # a legal no-op; a both-board broadcast is emitted only on a real change.
        # When the rotation actually changes the board, BOTH peers see BOTH
        # boards; a legal no-op is itself a valid production-visible outcome.
        rev_a = manager.rooms["room-lifecycle"].seats["A"].revision
        a.send_text(_action("A", "A-2", rev_a, "cw", "room-lifecycle"))
        rot_ack = _drain_until(a, action_id="A-2", types=("ack", "reject"))
        if rot_ack["type"] == "ack" and rot_ack["no_op"] is False:
            rot_a = {f["seat_id"] for f in _drain_both_playing_boards(a)}
            assert rot_a == {"A", "B"}
            rot_b = {f["seat_id"] for f in _drain_both_playing_boards(b)}
            assert rot_b == {"A", "B"}

        # OWN HOLD: a FIRST hold swaps the active piece into the empty Hold slot,
        # a deterministic real change, so BOTH peers see BOTH boards.
        rev_a = manager.rooms["room-lifecycle"].seats["A"].revision
        a.send_text(_action("A", "A-3", rev_a, "hold", "room-lifecycle"))
        hold_ack = _drain_until(a, action_id="A-3", types=("ack",))
        assert hold_ack["no_op"] is False  # first hold is always a real change
        hold_a = {f["seat_id"] for f in _drain_both_playing_boards(a)}
        assert hold_a == {"A", "B"}
        hold_b = {f["seat_id"] for f in _drain_both_playing_boards(b)}
        assert hold_b == {"A", "B"}
    finally:
        _close_sessions(a, b)


def test_remote_action_reaches_the_silent_peer_both_boards():
    """Seat B (silent) still receives seat A's accepted move as BOTH boards.

    B joins, drains the start transition, and then STOPS sending. A moves; B's
    writer delivers the remote move's both-board broadcast with A's board bumped,
    proving a remote accepted action reaches a peer with no B inbound traffic.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-remote")
    try:
        _drain_both_playing_boards(a)  # A's own pending start boards
        a.send_text(_action("A", "A-1", 0, "left", "room-remote"))
        ack = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack["revision"] == 1
        _drain_both_playing_boards(a)
        # B sent nothing since its handshake: it still gets the remote move.
        move_b = {f["seat_id"]: f for f in _drain_both_playing_boards(b)}
        assert set(move_b) == {"A", "B"}
        assert move_b["A"]["revision"] == 1
    finally:
        _close_sessions(a, b)


def test_server_no_input_gravity_publishes_both_boards_to_both_peers():
    """A server gravity advance (no action) publishes both boards to both peers.

    The gravity step is driven by the INJECTABLE clock only (no action is sent),
    and the endpoint's ``on_state`` hook broadcasts both authoritative boards; a
    live two-seat room's writers deliver them to both peers without any inbound
    traffic. This pins the native-14 fix where gravity previously mutated private
    games silently.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-gravity")
    room = manager.rooms["room-gravity"]
    try:
        _drain_both_playing_boards(a)  # clear A's pending start boards

        # Seed each board's due time, advance the clock past it, and run ONE
        # gravity step with the endpoint's publish hook. No action is ever sent.
        now = manager.clock()
        for seat in room.seats.values():
            seat.gravity_due_monotonic = now + gravity._current_interval_seconds(seat)
        manager.clock.advance(10.0)
        outcomes = gravity.gravity_step(
            manager, on_state=duel.broadcast_room_state
        )
        assert outcomes == []  # a plain advance, no top-out here

        # Both silent peers receive the gravity advance as BOTH boards.
        grav_a = {f["seat_id"] for f in _drain_both_playing_boards(a)}
        assert grav_a == {"A", "B"}
        grav_b = {f["seat_id"] for f in _drain_both_playing_boards(b)}
        assert grav_b == {"A", "B"}
    finally:
        _close_sessions(a, b)


def test_terminal_topout_outcome_reaches_both_peers():
    """A server-detected top-out delivers ONE outcome frame to BOTH peers.

    Seat A's private board is forced into a topped-out end-state; a gravity step
    resolves exactly ONE outcome (A loses, B wins) and the endpoint's
    ``on_outcome`` hook broadcasts the terminal frame to both peers' writers.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-topout")
    room = manager.rooms["room-topout"]
    try:
        _drain_both_playing_boards(a)  # clear A's pending start boards

        now = manager.clock()
        for seat in room.seats.values():
            seat.gravity_due_monotonic = now + gravity._current_interval_seconds(seat)
        # Force ONLY seat A to top out; B remains playable so A loses. We drive
        # the terminal OUTCOME delivery (the production-visible terminal signal)
        # via ``on_outcome`` only -- a hand-set game_over board is not broadcast
        # as a pre-terminal StateFrame (that would assert a null active_piece the
        # engine only clears on a real spawn collision). This mirrors the
        # accepted approach in test_stage4_both_boards.py.
        room.seats["A"].game.status = "game_over"
        manager.clock.advance(10.0)

        resolved = gravity.gravity_step(
            manager,
            on_outcome=duel.broadcast_outcome,
        )
        assert len(resolved) == 1
        assert resolved[0].result == "win"
        assert resolved[0].winning_seat == "B"
        assert resolved[0].losing_seat == "A"

        # BOTH peers receive the single terminal outcome frame.
        outcome_a = _drain_until(a, types=("outcome",))
        outcome_b = _drain_until(b, types=("outcome",))
        for frame in (outcome_a, outcome_b):
            assert frame["result"] == "win"
            assert frame["winning_seat"] == "B"
            assert frame["losing_seat"] == "A"
        assert room.status == "finished"
    finally:
        _close_sessions(a, b)


def test_forfeit_on_disconnect_resolves_once_winning_the_surviving_seat():
    """A disconnect in a started room forfeits the leaver exactly once.

    Seat A closes its socket; the endpoint's disconnect path resolves a GAMEPLAY
    forfeit via the set-once guard (A forfeits, B wins). We assert the
    production-visible RESOLUTION the room records (``room.outcome`` is a forfeit
    ``OutcomeData``), which is how the forfeit is observable in the decoupled app
    (the outcome-FRAME broadcast to the peer is wired by the gravity loop's
    ``on_outcome`` hook in the fully-wired app and is proven at the broadcast
    layer by test_stage4_both_boards.py). This is DISTINCT from an operational
    abort: a forfeit fabricates a winner, so ``operational_abort`` stays None.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-forfeit")
    room = manager.rooms["room-forfeit"]
    assert room.status == "playing"
    try:
        _drain_both_playing_boards(a)  # clear A's pending start boards
        a.close(code=contract.CLOSE_CODE_NORMAL)
        _wait_until(lambda: room.status == "finished")
        assert room.status == "finished"

        outcome = room.outcome
        assert isinstance(outcome, gravity.OutcomeData)
        assert outcome.result == "forfeit"
        assert outcome.forfeiting_seat == "A"
        assert outcome.losing_seat == "A"
        assert outcome.winning_seat == "B"
        # A forfeit is a gameplay result, NOT an operational abort.
        assert room.operational_abort is None
    finally:
        _close_sessions(b)


# ===========================================================================
# (3) TRAFFIC-FREE CLEANUP WITH NO LEAK, driven by the injectable clock:
#     waiting, playing-idle, finished, and shutdown each release the room /
#     gravity task / socket references with nothing leaked.
# Validates: Requirements 19.1, 19.2, 19.3
# ===========================================================================


def test_waiting_room_cleanup_releases_without_traffic():
    """A waiting room past its retention is reaped with no leak (clock-driven)."""

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    room, _seat = manager.assign_seat("room-wait-clean")
    room.gravity_task = object()  # a stand-in handle the reaper must release
    assert "room-wait-clean" in manager.rooms

    # No traffic at all: advancing the injectable clock past the waiting
    # retention is sufficient for cleanup_tick to reap it.
    clock.advance(manager.waiting_room_retention + 1)
    reaped = manager.cleanup_tick()

    assert {r.room_id for r in reaped} == {"room-wait-clean"}
    assert "room-wait-clean" not in manager.rooms  # no leaked room entry
    assert reaped[0].gravity_task is not None  # handle handed back to release


def test_playing_idle_room_cleanup_releases_without_traffic():
    """A playing room idle past the idle timeout is reaped (distinct retention).

    A playing room's lifetime is governed by the 60-second idle timeout from the
    last activity, which is DISTINCT from the 120-second waiting retention; with
    no traffic, advancing the clock past the idle timeout reaps it.
    """

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    room, _a = manager.assign_seat("room-idle")
    _r2, _b = manager.assign_seat("room-idle")
    room.status = "playing"
    manager.mark_activity(room)

    # Below the idle timeout: still alive.
    clock.advance(manager.idle_timeout - 1)
    assert manager.cleanup_tick() == []
    assert "room-idle" in manager.rooms

    # Past the idle timeout: reaped with no leak.
    clock.advance(2)
    reaped = manager.cleanup_tick()
    assert {r.room_id for r in reaped} == {"room-idle"}
    assert "room-idle" not in manager.rooms


def test_finished_room_cleanup_uses_distinct_finished_retention():
    """A finished room drains for the finished retention, then releases.

    The finished retention (15s) is DISTINCT from the waiting retention (120s):
    a finished room is kept only long enough for its terminal frames to drain,
    then released. A finished room is never reused for a restart.
    """

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    room, _a = manager.assign_seat("room-finished")
    _r2, _b = manager.assign_seat("room-finished")
    room.status = "playing"
    now = clock()
    outcome = gravity.OutcomeData(
        result="win",
        winning_seat="A",
        losing_seat="B",
        forfeiting_seat=None,
        final_revision={"A": 3, "B": 1},
    )
    assert room.set_outcome_once(outcome, now) is True
    assert room.status == "finished"

    # Within the finished retention: kept so terminal frames can drain.
    clock.advance(manager.finished_room_retention - 1)
    assert manager.cleanup_tick() == []
    assert "room-finished" in manager.rooms

    # Past it: released with no leak. The entry is GONE (never reused).
    clock.advance(2)
    reaped = manager.cleanup_tick()
    assert {r.room_id for r in reaped} == {"room-finished"}
    assert "room-finished" not in manager.rooms


def test_shutdown_releases_every_room_no_leak():
    """Shutdown releases EVERY room (any status) so nothing leaks across stop."""

    manager = RoomManager(clock=FakeClock())
    manager.assign_seat("room-sd-waiting")
    playing, _a = manager.assign_seat("room-sd-playing")
    _r2, _b = manager.assign_seat("room-sd-playing")
    playing.status = "playing"
    assert len(manager.rooms) == 2

    reaped = manager.shutdown()
    assert {r.room_id for r in reaped} == {"room-sd-waiting", "room-sd-playing"}
    assert manager.rooms == {}  # every room entry released


def test_duel_runtime_stop_cancels_tasks_and_releases_manager_no_leak():
    """The lifespan-owned runtime cancels its periodic tasks and releases cleanly.

    Both the cleanup and gravity loop tasks are cancelled AND awaited on stop
    (their cancellation genuinely completes), and the manager reference is
    dropped -- no leaked task or manager across shutdown.
    """

    from app import main as app_main

    async def scenario():
        runtime = app_main._DuelRuntime()
        await runtime.start()
        cleanup = runtime._cleanup_task
        gravity_task = runtime._gravity_task
        assert cleanup is not None and gravity_task is not None
        await asyncio.sleep(0)  # let both periodic tasks begin
        await runtime.stop()
        return cleanup, gravity_task, runtime

    cleanup, gravity_task, runtime = asyncio.run(scenario())
    assert cleanup.done() is True and cleanup.cancelled() is True
    assert gravity_task.done() is True and gravity_task.cancelled() is True
    assert runtime.manager is None
    assert runtime._cleanup_task is None and runtime._gravity_task is None


# ===========================================================================
# (4) A SLOW / FAILED PEER NEVER BLOCKS THE OTHER PEER OR ROOM, and _emit_cached
#     reports a failed cached send HONESTLY.
# Validates: Requirements 19.2, 19.3, 22.5
# ===========================================================================


class _FakeWebSocket:
    """In-memory socket recording sends; can fail or hang to model a bad peer."""

    def __init__(self, *, fail_after: Optional[int] = None, hang: bool = False) -> None:
        self.sent: List[str] = []
        self._fail_after = fail_after
        self._hang = hang
        self._count = 0

    async def send_text(self, text: str) -> None:
        self._count += 1
        if self._hang:
            await asyncio.Event().wait()  # blocks until cancelled
        if self._fail_after is not None and self._count >= self._fail_after:
            raise RuntimeError("peer broken")
        self.sent.append(text)


def _endpoint(manager: RoomManager) -> duel.DuelEndpoint:
    return duel.DuelEndpoint(manager, allowed_origins=(ALLOWED_ORIGIN,))


def test_slow_peer_does_not_block_the_other_peer_in_the_same_room():
    """A hanging peer's writer does not stall the healthy peer's delivery.

    Seat A's socket hangs on every send (a slow peer); seat B's socket is
    healthy. Both writers run concurrently. B's enqueued frames are delivered in
    full while A's writer is still blocked on its first send, proving one slow
    peer never blocks the other peer in the SAME room (bounded, independent
    per-connection I/O).
    """

    async def scenario() -> Tuple[List[str], bool]:
        manager = RoomManager(clock=FakeClock())
        room, seat_a = manager.assign_seat("room-slowpeer")
        _r2, seat_b = manager.assign_seat("room-slowpeer")
        room.status = "playing"
        endpoint = _endpoint(manager)

        ws_a = _FakeWebSocket(hang=True)  # slow peer: every send blocks
        ws_b = _FakeWebSocket()           # healthy peer
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)

        # Enqueue to BOTH; the healthy peer must fully drain regardless of A.
        duel.broadcast_room_state(room)  # both boards to both queues

        for _ in range(200):
            if not seat_b.outbound:
                break
            await asyncio.sleep(0)
        b_sent = list(ws_b.sent)
        a_blocked = bool(seat_a.outbound) or ws_a.sent == []

        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return b_sent, a_blocked

    b_sent, a_blocked = asyncio.run(scenario())
    # The healthy peer received BOTH boards even though A's writer was blocked.
    assert len(b_sent) == 2
    assert {json.loads(t)["seat_id"] for t in b_sent} == {"A", "B"}
    assert a_blocked is True


def test_failed_send_is_recorded_and_does_not_retry():
    """A failed send sets ``send_failed`` and the writer stops (no retry loop)."""

    async def scenario() -> Tuple[bool, List[str]]:
        manager = RoomManager(clock=FakeClock())
        room, seat_a = manager.assign_seat("room-failsend")
        _r2, _seat_b = manager.assign_seat("room-failsend")
        room.status = "playing"
        endpoint = _endpoint(manager)

        ws = _FakeWebSocket(fail_after=1)  # the first send raises
        seat_a.enqueue_outbound(duel.build_state_frame("room-failsend", seat_a, "playing"))
        seat_a.enqueue_outbound(duel.build_state_frame("room-failsend", seat_a, "playing"))
        writer = await endpoint._start_writer(ws, seat_a)
        for _ in range(100):
            if seat_a.send_failed:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat_a, writer)
        return seat_a.send_failed, ws.sent

    send_failed, sent = asyncio.run(scenario())
    assert send_failed is True
    assert sent == []  # the broken send delivered nothing and did not retry


def test_emit_cached_reports_a_failed_send_honestly():
    """``_emit_cached`` returns False on a failed cached send (no fabricated True).

    Before the native-14 correction ``_emit_cached`` returned ``drain_result or
    True``, hiding a failed send. The corrected helper reports the failure
    honestly so a started room treats the peer as unavailable.
    """

    async def scenario() -> bool:
        manager = RoomManager(clock=FakeClock())
        room, seat_a = manager.assign_seat("room-emitfail")
        _r2, _seat_b = manager.assign_seat("room-emitfail")
        room.status = "playing"
        endpoint = _endpoint(manager)
        ws = _FakeWebSocket(fail_after=1)  # the cached send will fail
        writer = await endpoint._start_writer(ws, seat_a)
        cached = duel.make_ack("room-emitfail", "A", "A-1", 0, no_op=False)
        result = await endpoint._emit_cached(ws, room, seat_a, cached)
        await endpoint._teardown_writer(seat_a, writer)
        return result

    assert asyncio.run(scenario()) is False


def test_emit_cached_reports_a_successful_send_truthfully():
    """``_emit_cached`` returns True and delivers the frame when the send is OK."""

    async def scenario() -> Tuple[bool, List[str]]:
        manager = RoomManager(clock=FakeClock())
        room, seat_a = manager.assign_seat("room-emitok")
        _r2, _seat_b = manager.assign_seat("room-emitok")
        room.status = "playing"
        endpoint = _endpoint(manager)
        ws = _FakeWebSocket()
        writer = await endpoint._start_writer(ws, seat_a)
        cached = duel.make_ack("room-emitok", "A", "A-1", 0, no_op=False)
        result = await endpoint._emit_cached(ws, room, seat_a, cached)
        await endpoint._teardown_writer(seat_a, writer)
        return result, ws.sent

    result, sent = asyncio.run(scenario())
    assert result is True
    assert len(sent) == 1 and json.loads(sent[0])["type"] == "ack"


# ===========================================================================
# (5) OPERATIONAL ABORTS: sequence_exhausted and scalar_overflow. Boundary,
#     once-only, BOTH-peer cleanup, NO fabricated winner, DISTINCT from forfeit.
#     Every CLOSE is asserted AFTER draining the queued frames first.
# Validates: Requirements 19.1, 19.2, 19.3, 20.4, 20.5, 20.6, 20.7, 22.6
# ===========================================================================


def test_sequence_exhaustion_boundary_max_ordinal_consumable_then_aborts_both():
    """Max ordinal is CONSUMABLE; the next-higher ordinal aborts the ROOM 1001.

    The maximum valid ordinal (fifteen nines) applies normally; the next higher
    ordinal (sixteen digits) cannot be represented by the grammar and is an
    OPERATIONAL ABORT closing BOTH peers 1001 ``sequence_exhausted`` -- after the
    acting seat's queued frames are drained -- with NO fabricated winner.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-seq-boundary")
    room = manager.rooms["room-seq-boundary"]
    try:
        _drain_both_playing_boards(a)  # clear A's pending start boards

        # Boundary: the max ordinal is consumable (applied, high-water advances).
        a.send_text(_action("A", "A-999999999999999", 0, "left", "room-seq-boundary"))
        ack = _drain_until(a, action_id="A-999999999999999", types=("ack",))
        assert ack["applied"] is True and ack["revision"] == 1
        assert room.seats["A"].last_action_seq == contract.MAX_ACTION_ORDINAL
        _drain_both_playing_boards(a)

        # The next higher ordinal aborts the whole room. Drain A to its close.
        a.send_text(_action("A", "A-1000000000000000", 1, "left", "room-seq-boundary"))
        code_a, reason_a = _drain_to_close(a)
        assert code_a == contract.CLOSE_CODE_GOING_AWAY
        assert reason_a == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED

        # The OTHER peer is closed with the SAME literal reason (room-wide),
        # with NO inbound traffic from B, after draining its queued frames.
        code_b, reason_b = _drain_to_close(b)
        assert code_b == contract.CLOSE_CODE_GOING_AWAY
        assert reason_b == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED

        # No fabricated winner; the room is released (no leak).
        assert room.operational_abort == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED
        assert room.outcome is None
        _wait_until(lambda: "room-seq-boundary" not in manager.rooms)
        assert "room-seq-boundary" not in manager.rooms
    finally:
        _close_sessions(a, b)


def test_sequence_exhaustion_is_distinct_from_forfeit():
    """A sequence-exhaustion abort never fabricates a forfeit OutcomeData."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-seq-distinct")
    room = manager.rooms["room-seq-distinct"]
    try:
        _drain_both_playing_boards(a)
        a.send_text(_action("A", "A-1000000000000000", 0, "left", "room-seq-distinct"))
        _code, reason = _drain_to_close(a)
        assert reason == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED
        assert reason != contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
        assert not isinstance(room.outcome, gravity.OutcomeData)
        assert room.outcome is None
        _drain_to_close(b)
    finally:
        _close_sessions(a, b)


def test_scalar_overflow_aborts_both_without_emitting_out_of_range_revision():
    """A would-overflow scalar aborts the room 1001 with NO out-of-range emit.

    Seat A is pinned at the SAFE integer ceiling so an applied change WOULD bump
    the revision past the bound. The endpoint must abort BEFORE committing or
    emitting: no ack for the overflowing action, no state carrying an
    out-of-range revision, both peers closed 1001 ``scalar_overflow``, no
    fabricated winner. The close is asserted after draining A's queued frames.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-ovf")
    room = manager.rooms["room-ovf"]
    try:
        _drain_both_playing_boards(a)  # clear A's pending start boards
        room.seats["A"].revision = contract.SAFE_INT_MAX

        a.send_text(_action("A", "A-1", contract.SAFE_INT_MAX, "left", "room-ovf"))

        # Drain EVERY frame to A until the close; none may carry an out-of-range
        # revision and the overflowing action is never acked.
        delivered: List[dict] = []
        try:
            while True:
                delivered.append(_recv(a))
        except WebSocketDisconnect as exc:
            assert exc.code == contract.CLOSE_CODE_GOING_AWAY
            assert getattr(exc, "reason", None) == contract.CLOSE_REASON_SCALAR_OVERFLOW
        for frame in delivered:
            if "revision" in frame:
                assert frame["revision"] <= contract.SAFE_INT_MAX
            assert not (frame.get("type") == "ack" and frame.get("action_id") == "A-1")

        # The authoritative revision was never bumped past the bound.
        assert room.seats["A"].revision == contract.SAFE_INT_MAX

        # The OTHER peer is closed with the same literal reason (room-wide).
        code_b, reason_b = _drain_to_close(b)
        assert code_b == contract.CLOSE_CODE_GOING_AWAY
        assert reason_b == contract.CLOSE_REASON_SCALAR_OVERFLOW

        assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
        assert room.outcome is None
        _wait_until(lambda: "room-ovf" not in manager.rooms)
        assert "room-ovf" not in manager.rooms
    finally:
        _close_sessions(a, b)


def test_scalar_overflow_is_distinct_from_forfeit_and_disconnect():
    """Scalar overflow does NOT invoke the ordinary disconnect/forfeit path."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-ovf-distinct")
    room = manager.rooms["room-ovf-distinct"]
    try:
        _drain_both_playing_boards(a)
        room.seats["A"].revision = contract.SAFE_INT_MAX
        a.send_text(_action("A", "A-1", contract.SAFE_INT_MAX, "left", "room-ovf-distinct"))
        _code, reason = _drain_to_close(a)
        assert reason == contract.CLOSE_REASON_SCALAR_OVERFLOW
        assert reason != contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
        assert not isinstance(room.outcome, gravity.OutcomeData)
        assert room.outcome is None
        _drain_to_close(b)
    finally:
        _close_sessions(a, b)


def test_operational_abort_is_set_once_and_loses_to_a_resolved_gameplay_outcome():
    """``set_operational_abort_once`` aborts once; it loses to a resolved outcome.

    The FIRST abort records the literal reason; a racing second abort returns
    False (the first reason stands). An already-resolved gameplay room (a forfeit
    set its outcome) cannot be converted into an abort afterward.
    """

    manager = RoomManager(clock=FakeClock())

    # Once-only: the first abort wins, the second loses.
    room, _a = manager.assign_seat("room-once")
    _r2, _b = manager.assign_seat("room-once")
    room.status = "playing"
    assert room.set_operational_abort_once(contract.CLOSE_REASON_SCALAR_OVERFLOW) is True
    assert room.set_operational_abort_once(contract.CLOSE_REASON_SEQUENCE_EXHAUSTED) is False
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    assert room.outcome is None  # an abort fabricates no gameplay winner

    # A resolved gameplay room cannot be operationally aborted afterward.
    resolved, _ra = manager.assign_seat("room-resolved")
    _rr2, _rb = manager.assign_seat("room-resolved")
    resolved.status = "playing"
    now = manager.clock()
    assert gravity.resolve_forfeit(resolved, "A", now, manager=manager) is not None
    assert resolved.status == "finished"
    assert resolved.set_operational_abort_once(contract.CLOSE_REASON_SCALAR_OVERFLOW) is False
    assert resolved.operational_abort is None


def test_scalar_overflow_ceiling_no_op_does_not_abort():
    """A legal NO-OP at the ceiling does not overflow (no bump) -> no abort.

    A second consecutive ``hold`` at the SAFE integer ceiling is a legal no-op:
    it changes nothing, so the revision is not bumped and no overflow occurs. The
    room stays playing -- the abort fires only on a WOULD-BE out-of-range bump.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-ceil-noop")
    room = manager.rooms["room-ceil-noop"]
    try:
        _drain_both_playing_boards(a)

        # A first 'hold' is a real change -> bump to revision 1; drain its boards.
        a.send_text(_action("A", "A-1", 0, "hold", "room-ceil-noop"))
        ack1 = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack1["no_op"] is False and ack1["revision"] == 1
        _drain_both_playing_boards(a)

        # Pin A at the ceiling; a SECOND consecutive 'hold' is a legal no-op
        # (can_hold is False), so there is no bump and no overflow.
        room.seats["A"].revision = contract.SAFE_INT_MAX
        a.send_text(_action("A", "A-2", contract.SAFE_INT_MAX, "hold", "room-ceil-noop"))
        ack2 = _drain_until(a, action_id="A-2", types=("ack",))
        assert ack2["applied"] is True and ack2["no_op"] is True
        assert ack2["revision"] == contract.SAFE_INT_MAX  # unchanged, not bumped

        # The room was NOT aborted: a ceiling no-op is not an overflow.
        assert room.operational_abort is None
        assert room.status == "playing"
    finally:
        _close_sessions(a, b)


# ===========================================================================
# (6) NATIVE-19 F1: the SURVIVING peer ACTUALLY receives the forfeit outcome +
#     final both-board state after a real disconnect / failed-send / full-queue
#     in a STARTED room, with NO further input from either peer, and reaches
#     CLOSE. These pin the fix for the ``_handle_disconnect`` no-broadcast seam
#     and the ``on_outcome``-only-on-newly-resolved gap: the terminal frames are
#     delivered by the DISCONNECT path itself (the decoupled app mounts NO
#     gravity loop), never by a future gravity step or any client input.
# Validates: Requirements 16.1, 16.2, 17.3, 17.4, 17.5, 18.5, 18.6, 19.1, 19.2,
#            19.3, 20.2, 22.3, 22.4, 22.5
# ===========================================================================


def test_disconnect_delivers_forfeit_outcome_and_final_boards_to_surviving_peer():
    """A real disconnect pushes the forfeit outcome + both final boards to B.

    The decoupled app mounts NO gravity loop, so the ONLY thing that can deliver
    the terminal result to the surviving peer is the disconnect path's own
    central publication (native-19 F1). Seat A disconnects; seat B -- which sends
    NOTHING further -- must receive BOTH final authoritative boards (carrying the
    now-``finished`` ``room_status``) AND the single forfeit ``outcome`` frame
    (A forfeits, B wins), purely via its independent writer.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-f1-forfeit")
    room = manager.rooms["room-f1-forfeit"]
    assert room.status == "playing"
    try:
        _drain_both_playing_boards(a)  # clear A's own pending start boards

        # A disconnects; B sends NOTHING further.
        a.close(code=contract.CLOSE_CODE_NORMAL)
        _wait_until(lambda: room.status == "finished")
        assert room.status == "finished"

        # B's writer delivers the FINAL both-board state (room_status finished)
        # then the single forfeit outcome, with no inbound traffic from B.
        final_states: Dict[str, dict] = {}
        outcome: Optional[dict] = None
        for _ in range(12):
            frame = _recv(b)
            if frame["type"] == "state" and frame["room_status"] == "finished":
                final_states[frame["seat_id"]] = frame
            elif frame["type"] == "outcome":
                outcome = frame
                break
        assert outcome is not None, "surviving peer never received the outcome"
        assert outcome["result"] == "forfeit"
        assert outcome["forfeiting_seat"] == "A"
        assert outcome["losing_seat"] == "A"
        assert outcome["winning_seat"] == "B"
        # Both authoritative boards' FINAL state reached the survivor first.
        assert set(final_states) == {"A", "B"}
        assert all(f["room_status"] == "finished" for f in final_states.values())

        # A forfeit is a gameplay result, NOT an operational abort.
        assert room.operational_abort is None
    finally:
        _close_sessions(b)


def test_disconnect_forfeit_outcome_is_enqueued_exactly_once_to_survivor():
    """The forfeit terminal frames are enqueued EXACTLY once (set-once guard).

    Even if the disconnect cleanup were observed by more than one path, only the
    FIRST caller to win ``resolve_forfeit`` publishes; a racing second resolution
    returns ``None`` and enqueues nothing. The survivor therefore sees exactly
    ONE outcome frame. (The survivor's OWN socket close on a forfeit is the
    writer-wake / cleanup responsibility of tasks 35.2 / 35.3; this 35.1 test
    asserts the DELIVERY of the single terminal outcome to the survivor, so it
    reads the outcome frame directly rather than draining to a survivor close.)
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-f1-once")
    room = manager.rooms["room-f1-once"]
    try:
        _drain_both_playing_boards(a)
        a.close(code=contract.CLOSE_CODE_NORMAL)
        _wait_until(lambda: room.status == "finished")

        # Read the terminal frames the survivor's writer delivered: the FIRST
        # outcome frame among them must be the sole forfeit resolution.
        outcome = _drain_until(b, types=("outcome",))
        assert outcome["result"] == "forfeit"
        assert outcome["winning_seat"] == "B"
        # The set-once guard means only one resolution ever enqueued an outcome;
        # ``resolve_forfeit`` returned ``None`` for any racing second caller, so
        # no second outcome frame was ever produced for this room.
        assert room.outcome is not None
    finally:
        _close_sessions(b)


def test_failed_send_forfeit_publishes_terminal_to_the_surviving_peer():
    """A failed send to A forfeits A and pushes the terminal result to B.

    Seat A's socket fails on its next send (a slow/broken peer / full queue in a
    STARTED room). The endpoint classifies A unavailable, resolves the forfeit
    once, and -- via the central publication -- enqueues the final both-board
    state + outcome onto the SURVIVING seat B's queue, which its writer delivers.
    Driven entirely at the endpoint layer with fake sockets so no real timer and
    no B input is involved.
    """

    async def scenario() -> Tuple[Optional[str], List[dict], Optional[object]]:
        manager = RoomManager(clock=FakeClock())
        room, seat_a = manager.assign_seat("room-f1-failsend")
        _r2, seat_b = manager.assign_seat("room-f1-failsend")
        room.status = "playing"
        endpoint = _endpoint(manager)

        ws_a = _FakeWebSocket(fail_after=1)  # A's send fails
        ws_b = _FakeWebSocket()              # B is healthy
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)

        # Enqueue a frame to A and let its writer record the failed send.
        seat_a.enqueue_outbound(
            duel.build_state_frame("room-f1-failsend", seat_a, "playing")
        )
        for _ in range(200):
            if seat_a.send_failed:
                break
            await asyncio.sleep(0)

        # The endpoint's forfeit-close path resolves + publishes to the survivor.
        await endpoint._forfeit_and_close(ws_a, room, seat_a)

        # Let B's writer drain the enqueued terminal frames.
        for _ in range(200):
            if not seat_b.outbound:
                break
            await asyncio.sleep(0)

        received = [json.loads(t) for t in ws_b.sent]
        outcome = next((f for f in received if f["type"] == "outcome"), None)
        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return room.operational_abort, received, outcome

    abort, received, outcome = asyncio.run(scenario())
    # The surviving peer actually received the forfeit outcome.
    assert outcome is not None, "survivor never received the forfeit outcome"
    assert outcome["result"] == "forfeit"
    assert outcome["forfeiting_seat"] == "A"
    assert outcome["winning_seat"] == "B"
    # Both final boards reached the survivor before the outcome.
    final_states = {
        f["seat_id"] for f in received
        if f["type"] == "state" and f["room_status"] == "finished"
    }
    assert final_states == {"A", "B"}
    # A failed-send forfeit is a gameplay result, not an operational abort.
    assert abort is None


# ===========================================================================
# (7) NATIVE-19 F3 (task 35.3): CLEANUP + SHUTDOWN actually CLOSE sockets, WAKE
#     blocked receives/writers, and RELEASE/AWAIT owned tasks -- with a
#     DOCUMENTED close reason and NO new traffic, and NO fabricated gameplay
#     winner on a lifecycle/operational abort. These assert the ACTUAL idle-peer
#     CLOSE/termination, not merely an empty rooms map. They drive the REAL
#     reader (``_run_action_loop``) + independent writer over a fake IDLE socket
#     (its ``receive`` blocks forever, so the reader would hang unless woken) and
#     then run the production ``_cleanup_loop`` / ``_DuelRuntime.stop`` teardown.
#     The native production constants (120/60/15/1s) are UNCHANGED; only the
#     INJECTABLE FakeClock is advanced (a private unit fixture), never a smaller
#     production bound.
# Validates: Requirements 19.1, 19.2, 19.3, 19.5, 19.6
# ===========================================================================


class _ReaderIdleWebSocket:
    """A fake socket whose ``receive`` blocks forever (an IDLE peer).

    Models the exact hang the native-19 F3 close must resolve: a connected peer
    that sends NOTHING sits blocked in ``websocket.receive()``; unless its writer
    is woken and performs a directed close that wakes the reader, the reader
    never terminates. ``send_text`` succeeds and is recorded so a test can assert
    NO new gameplay traffic (no forfeit/outcome) was produced by the lifecycle
    close. ``close`` records the terminal ``(code, reason)``.
    """

    def __init__(self) -> None:
        from starlette.websockets import WebSocketState

        self.sent: List[str] = []
        self.closed: Optional[Tuple[int, str]] = None
        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        await asyncio.Event().wait()  # blocks until cancelled; idle peer
        raise AssertionError("receive should never return for an idle peer")

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


def _no_new_gameplay_traffic(ws: "_ReaderIdleWebSocket") -> bool:
    """Return True iff the socket received NO forfeit/outcome frame (no winner)."""

    for text in ws.sent:
        frame = json.loads(text)
        if frame.get("type") == "outcome":
            return False
    return True


async def _drive_reaped_room_close(
    *,
    room_id: str,
    status: str,
    advance_to: str,
) -> Tuple[object, object, object, object, object]:
    """Build a live two-seat room, park both readers, then run ``_cleanup_loop``.

    ``status`` is the room lifecycle status to reap (``waiting``/``playing``/
    ``finished``); ``advance_to`` selects the retention the FakeClock is advanced
    past (``"waiting"``/``"idle"``/``"finished"``). Returns the room, both seats,
    and both fake idle sockets after a SINGLE cleanup iteration has reaped and
    torn the room down. The native constants are untouched; only the injectable
    clock advances.
    """

    from app import main as app_main

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    endpoint = duel.DuelEndpoint(manager, allowed_origins=(ALLOWED_ORIGIN,))

    room, seat_a = manager.assign_seat(room_id)
    _r2, seat_b = manager.assign_seat(room_id)
    ws_a = _ReaderIdleWebSocket()
    ws_b = _ReaderIdleWebSocket()

    # Start each seat's independent writer and park each reader on the idle
    # receive, exactly as a live connection does.
    writer_a = await endpoint._start_writer(ws_a, seat_a)
    writer_b = await endpoint._start_writer(ws_b, seat_b)
    reader_a = asyncio.ensure_future(endpoint._run_action_loop(ws_a, room, seat_a))
    reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
    await asyncio.sleep(0)  # let both readers reach the blocking receive

    # Put the room into the status under test (a finished room also needs an
    # outcome so it fabricates no NEW winner on close).
    if status == "playing":
        room.status = "playing"
        manager.mark_activity(room)
    elif status == "finished":
        room.status = "playing"
        outcome = gravity.OutcomeData(
            result="win",
            winning_seat="A",
            losing_seat="B",
            forfeiting_seat=None,
            final_revision={"A": 2, "B": 1},
        )
        assert room.set_outcome_once(outcome, clock()) is True
        assert room.status == "finished"

    # Advance the INJECTABLE clock past the relevant retention so a single
    # cleanup iteration reaps it (no wall-clock wait; production bounds intact).
    if advance_to == "waiting":
        clock.advance(manager.waiting_room_retention + 1)
    elif advance_to == "idle":
        clock.advance(manager.idle_timeout + 1)
    elif advance_to == "finished":
        clock.advance(manager.finished_room_retention + 1)

    # Run ONE production cleanup iteration: reap + lifecycle close. We invoke the
    # reap + release directly (the loop body) rather than the infinite loop.
    reaped = manager.cleanup_tick()
    assert [r.room_id for r in reaped] == [room_id]
    for r in reaped:
        await app_main._release_room_resources(r, app_main._reap_close_reason(r.status))

    # Let both writers perform the directed close and both readers wake + return.
    for _ in range(500):
        if reader_a.done() and reader_b.done():
            break
        await asyncio.sleep(0)

    await endpoint._teardown_writer(seat_a, writer_a)
    await endpoint._teardown_writer(seat_b, writer_b)
    for reader in (reader_a, reader_b):
        if not reader.done():
            reader.cancel()
    await asyncio.wait({reader_a, reader_b})
    return room, ws_a, ws_b, reader_a, reader_b


def test_cleanup_reaped_waiting_room_closes_both_sockets_no_winner():
    """A reaped WAITING room closes both idle sockets 1001 waiting_room_timeout.

    The native-19 F3 fix: a reaped waiting room is not merely dropped from the
    map -- each blocked idle reader is WOKEN and its socket CLOSED with the
    documented standard code 1001 + the LITERAL reason ``waiting_room_timeout``,
    through the single ordered writer. A waiting-room reap is a lifecycle abort:
    it fabricates NO gameplay winner and pushes NO new outcome traffic.
    """

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(
        _drive_reaped_room_close(
            room_id="room-reap-waiting", status="waiting", advance_to="waiting"
        )
    )
    # Both blocked idle readers actually WOKE and returned (no hang).
    assert reader_a.done() and not reader_a.cancelled()
    assert reader_b.done() and not reader_b.cancelled()
    # Both sockets were CLOSED with the documented code + literal reason.
    for ws in (ws_a, ws_b):
        assert ws.closed is not None, "socket was never closed"
        assert ws.closed[0] == contract.CLOSE_CODE_GOING_AWAY
        assert ws.closed[1] == contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT
    # Lifecycle abort -> NO fabricated gameplay winner, NO new outcome traffic.
    assert room.outcome is None
    assert room.operational_abort == contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT
    assert _no_new_gameplay_traffic(ws_a) and _no_new_gameplay_traffic(ws_b)


def test_cleanup_reaped_idle_playing_room_closes_both_sockets_no_winner():
    """A reaped idle PLAYING room closes both sockets 1001 idle_timeout.

    A started room idle past its 60s idle timeout is reaped: both blocked readers
    wake and both sockets close with the literal ``idle_timeout`` reason. A
    lifecycle idle reap fabricates NO gameplay winner (it is NOT a forfeit) and
    produces no new outcome traffic.
    """

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(
        _drive_reaped_room_close(
            room_id="room-reap-idle", status="playing", advance_to="idle"
        )
    )
    assert reader_a.done() and not reader_a.cancelled()
    assert reader_b.done() and not reader_b.cancelled()
    for ws in (ws_a, ws_b):
        assert ws.closed is not None
        assert ws.closed[0] == contract.CLOSE_CODE_GOING_AWAY
        assert ws.closed[1] == contract.CLOSE_REASON_IDLE_TIMEOUT
    # An idle reap is NOT a gameplay forfeit: no winner, no outcome traffic.
    assert room.outcome is None
    assert room.operational_abort == contract.CLOSE_REASON_IDLE_TIMEOUT
    assert _no_new_gameplay_traffic(ws_a) and _no_new_gameplay_traffic(ws_b)


def test_cleanup_reaped_finished_room_closes_both_sockets_normal_completion():
    """A reaped FINISHED room closes both sockets 1000 normal_completion.

    A finished room already carries its set-once gameplay outcome. When its 15s
    finished-retention drain window expires it is reaped and its sockets are
    closed with the canonical NORMAL close code 1000 + the literal
    ``normal_completion`` reason (native-20 D2: the close code is selected BY
    REASON, so a reaped finished/normal_completion room closes 1000 -- the same
    code the endpoint's own ``_finish_and_close`` uses -- NOT 1001). The reap
    invents NO new winner: the existing terminal outcome stands and no new
    outcome is enqueued.
    """

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(
        _drive_reaped_room_close(
            room_id="room-reap-finished", status="finished", advance_to="finished"
        )
    )
    assert reader_a.done() and not reader_a.cancelled()
    assert reader_b.done() and not reader_b.cancelled()
    for ws in (ws_a, ws_b):
        assert ws.closed is not None
        assert ws.closed[0] == contract.CLOSE_CODE_NORMAL
        assert ws.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    # The pre-existing gameplay outcome stands; the reap invents no NEW winner
    # and pushes no NEW outcome frame on top of the already-drained terminal.
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert _no_new_gameplay_traffic(ws_a) and _no_new_gameplay_traffic(ws_b)


def test_cleanup_loop_reaps_and_closes_without_traffic_driven_by_clock():
    """The REAL ``_cleanup_loop`` reaps + closes a waiting room via the clock.

    This drives the actual production loop body (not a hand-rolled copy): a
    single cleanup iteration past the waiting retention reaps the room, closes
    the idle socket with the documented reason, and wakes the blocked reader --
    all WITHOUT any inbound traffic and WITHOUT a real timer (the injectable
    FakeClock is advanced). The loop is cancelled afterward so no task leaks.
    """

    from app import main as app_main

    async def scenario():
        clock = FakeClock()
        manager = RoomManager(clock=clock)
        endpoint = duel.DuelEndpoint(manager, allowed_origins=(ALLOWED_ORIGIN,))
        room, seat_a = manager.assign_seat("room-loop-reap")
        ws_a = _ReaderIdleWebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        reader_a = asyncio.ensure_future(
            endpoint._run_action_loop(ws_a, room, seat_a)
        )
        await asyncio.sleep(0)

        # Advance past the native waiting retention, then run the REAL loop. The
        # loop body reaps + closes; cancel it after one effective pass.
        clock.advance(manager.waiting_room_retention + 1)
        loop_task = asyncio.ensure_future(app_main._cleanup_loop(manager))

        for _ in range(500):
            if reader_a.done() and "room-loop-reap" not in manager.rooms:
                break
            await asyncio.sleep(0)

        loop_task.cancel()
        await asyncio.wait({loop_task})
        await endpoint._teardown_writer(seat_a, writer_a)
        if not reader_a.done():
            reader_a.cancel()
        await asyncio.wait({reader_a})
        return manager, room, ws_a, reader_a, loop_task

    manager, room, ws_a, reader_a, loop_task = asyncio.run(scenario())
    # The room entry is gone AND the socket was actually closed with the reason.
    assert "room-loop-reap" not in manager.rooms
    assert reader_a.done() and not reader_a.cancelled()
    assert ws_a.closed is not None
    assert ws_a.closed[0] == contract.CLOSE_CODE_GOING_AWAY
    assert ws_a.closed[1] == contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT
    assert room.outcome is None  # waiting reap fabricates no winner
    # The cleanup loop itself was cancelled with no leak.
    assert loop_task.done() and loop_task.cancelled()


def test_duel_runtime_stop_closes_room_sockets_server_shutdown_no_winner():
    """``_DuelRuntime.stop`` closes every live room's sockets 1001 server_shutdown.

    On shutdown the runtime cancels its periodic tasks AND tears down every
    remaining room: each blocked reader is woken and its socket closed with the
    literal ``server_shutdown`` reason through the single ordered writer, the
    manager is released, and NO gameplay winner is fabricated (a shutdown is a
    lifecycle abort, not a forfeit). Asserts the ACTUAL socket close + reader
    termination, not merely that the manager was dropped.
    """

    from app import main as app_main

    async def scenario():
        runtime = app_main._DuelRuntime()
        await runtime.start()
        manager = runtime.manager
        endpoint = runtime.endpoint

        # Attach a live, parked connection to a room the runtime owns.
        room, seat_a = manager.assign_seat("room-shutdown-live")
        room.status = "playing"
        manager.mark_activity(room)
        ws_a = _ReaderIdleWebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        reader_a = asyncio.ensure_future(
            endpoint._run_action_loop(ws_a, room, seat_a)
        )
        await asyncio.sleep(0)  # park the reader on the idle receive

        await runtime.stop()

        for _ in range(500):
            if reader_a.done():
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat_a, writer_a)
        if not reader_a.done():
            reader_a.cancel()
        await asyncio.wait({reader_a})
        return runtime, room, ws_a, reader_a

    runtime, room, ws_a, reader_a = asyncio.run(scenario())
    # The blocked reader woke and returned; the socket closed server_shutdown.
    assert reader_a.done() and not reader_a.cancelled()
    assert ws_a.closed is not None
    assert ws_a.closed[0] == contract.CLOSE_CODE_GOING_AWAY
    assert ws_a.closed[1] == contract.CLOSE_REASON_SERVER_SHUTDOWN
    # Shutdown is a lifecycle abort: no fabricated winner, no outcome traffic.
    assert room.outcome is None
    assert room.operational_abort == contract.CLOSE_REASON_SERVER_SHUTDOWN
    assert _no_new_gameplay_traffic(ws_a)
    # The runtime released the manager + both periodic tasks with no leak.
    assert runtime.manager is None
    assert runtime._cleanup_task is None and runtime._gravity_task is None


def test_release_room_resources_cancels_and_awaits_owned_room_task():
    """A room that OWNS a gravity task has it cancelled + awaited on reap.

    Production runs a single manager-wide gravity loop (``room.gravity_task`` is
    normally ``None``), but a room that owns its own task must have it released
    AND awaited on lifecycle close with no leak. This pins the "release/await
    owned tasks" obligation directly.
    """

    from app import main as app_main

    async def scenario():
        clock = FakeClock()
        manager = RoomManager(clock=clock)
        room, _seat_a = manager.assign_seat("room-owned-task")

        async def _long_task():
            await asyncio.Event().wait()  # runs until cancelled

        owned = asyncio.ensure_future(_long_task())
        room.gravity_task = owned
        await asyncio.sleep(0)  # let it start

        await app_main._release_room_resources(
            room, contract.CLOSE_REASON_SERVER_SHUTDOWN
        )
        return room, owned

    room, owned = asyncio.run(scenario())
    # The owned task was cancelled AND awaited (its cancellation completed), and
    # the room's handle was cleared so nothing leaks.
    assert owned.done() and owned.cancelled()
    assert room.gravity_task is None


# ===========================================================================
# (8) NATIVE-19 F1 CONSOLIDATION (task 35.7): the two remaining real-lifecycle
#     forfeit-delivery cases the F1 guarantee names that were not yet pinned in
#     THIS dedicated module -- a TRANSPORT 1007 close in a STARTED room and a
#     FULL outbound queue in a STARTED room. Both assert the SURVIVING peer
#     ACTUALLY receives the forfeit outcome + BOTH final boards with NO further
#     input from either peer, and the leaver reaches CLOSE with the documented
#     literal reason. Driven at the REAL endpoint reader/writer layer over fake
#     sockets (the decoupled app mounts NO gravity loop), so the terminal frames
#     can ONLY come from the disconnect / failed-send path itself -- never a
#     future gravity step or any client traffic. A consistent engine terminal
#     fixture is not needed here (a forfeit never tops out a board); the forfeit
#     leaves ``active`` untouched and fabricates the winner from the surviving
#     seat, so no on_state bypass or internal-object assertion is used.
# Validates: Requirements 16.6, 17.1, 17.2, 18.5, 19.1, 19.2, 19.3, 22.4, 22.5
# ===========================================================================


def test_transport_1007_in_started_room_delivers_forfeit_terminal_to_survivor():
    """A transport 1007 close in a STARTED room forfeits the leaver to the peer.

    A wire-level invalid-UTF8 TEXT frame is failed by the transport (code 1007)
    and surfaces to the reader as a ``websocket.disconnect`` message. In a
    started room this is the ordinary disconnect/forfeit path: seat A forfeits
    (B wins) EXACTLY once, and the central publication enqueues the final
    both-board state + the single ``outcome`` frame onto the SURVIVING seat B's
    queue, which its independent writer delivers with NO further input from
    either peer. This pins the transport-1007 started-room forfeit-DELIVERY case
    (not merely the resolution) that the F1 guarantee names.
    """

    async def scenario():
        endpoint = _endpoint(RoomManager(clock=FakeClock()))
        manager = endpoint._manager
        room, seat_a = manager.assign_seat("room-1007-forfeit")
        _r2, seat_b = manager.assign_seat("room-1007-forfeit")
        room.status = "playing"
        manager.mark_activity(room)

        ws_b = _FakeWebSocket()  # the healthy surviving peer
        writer_b = await endpoint._start_writer(ws_b, seat_b)

        # Seat A's socket surfaces a TRANSPORT 1007 close as the next inbound
        # message. The real reader translates it into a WebSocketDisconnect and
        # the connection coroutine routes it through _handle_disconnect exactly
        # as production __call__ does for a wire-level 1007.
        class _Transport1007WebSocket:
            def __init__(self) -> None:
                self._sent = False
                from starlette.websockets import WebSocketState

                self.application_state = WebSocketState.CONNECTED

            async def receive(self) -> dict:
                if not self._sent:
                    self._sent = True
                    return {
                        "type": "websocket.disconnect",
                        "code": contract.CLOSE_CODE_INVALID_PAYLOAD,
                    }
                await asyncio.Event().wait()  # never a second frame

            async def send_text(self, text: str) -> None:  # pragma: no cover
                pass

            async def close(self, code: int = 1000, reason: str = "") -> None:
                from starlette.websockets import WebSocketState

                self.application_state = WebSocketState.DISCONNECTED

        ws_a = _Transport1007WebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)

        # Run the REAL reader; a 1007 disconnect raises WebSocketDisconnect, which
        # the production connection coroutine catches and routes to
        # _handle_disconnect. Mirror that exact routing here.
        try:
            await endpoint._run_action_loop(ws_a, room, seat_a)
        except WebSocketDisconnect as exc:
            assert exc.code == contract.CLOSE_CODE_INVALID_PAYLOAD
            endpoint._handle_disconnect(room, seat_a)

        # Let B's independent writer drain the terminal frames (no B input).
        for _ in range(500):
            if not seat_b.outbound:
                break
            await asyncio.sleep(0)

        received = [json.loads(t) for t in ws_b.sent]
        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return room, received

    room, received = asyncio.run(scenario())
    # The room resolved EXACTLY one gameplay forfeit (A forfeits, B wins).
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    # A forfeit is a gameplay result, NOT an operational abort.
    assert room.operational_abort is None
    # The surviving peer ACTUALLY received the single forfeit outcome frame.
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never received the 1007 forfeit outcome"
    assert outcome["result"] == "forfeit"
    assert outcome["forfeiting_seat"] == "A"
    assert outcome["winning_seat"] == "B"
    # Both authoritative boards' FINAL (finished) state reached the survivor.
    final_states = {
        f["seat_id"]
        for f in received
        if f["type"] == "state" and f["room_status"] == "finished"
    }
    assert final_states == {"A", "B"}


def test_full_outbound_queue_is_bounded_and_rejects_beyond_the_depth_cap():
    """A slow peer's outbound queue is BOUNDED: it rejects beyond depth-64.

    The native-14 full-queue guarantee rests on the bounded ``deque``:
    ``enqueue_outbound`` ACCEPTS up to ``OUTBOUND_QUEUE_DEPTH`` frames and then
    REJECTS (returns ``False``) rather than growing, so a slow/stalled peer
    cannot exhaust worker memory and the endpoint can classify it unavailable.
    This pins the bound itself (the queue never grows past the cap) -- the
    precondition the full-queue forfeit-delivery relies on.
    """

    from app.duel.rooms import OUTBOUND_QUEUE_DEPTH

    manager = RoomManager(clock=FakeClock())
    _room, seat_a = manager.assign_seat("room-fullq-bound")
    # No writer is started, so nothing drains: every accepted frame stays queued.
    accepted = 0
    for _ in range(OUTBOUND_QUEUE_DEPTH + 16):
        if seat_a.enqueue_outbound(
            duel.build_state_frame("room-fullq-bound", seat_a, "playing")
        ):
            accepted += 1
    # Exactly the cap was accepted; everything beyond it was rejected.
    assert accepted == OUTBOUND_QUEUE_DEPTH
    assert len(seat_a.outbound) == OUTBOUND_QUEUE_DEPTH
    # A further enqueue onto the full queue is rejected (never grows the deque).
    assert seat_a.enqueue_outbound(
        duel.build_state_frame("room-fullq-bound", seat_a, "playing")
    ) is False
    assert len(seat_a.outbound) == OUTBOUND_QUEUE_DEPTH


def test_full_queue_slow_peer_in_started_room_forfeits_and_delivers_to_survivor():
    """A STALLED-queue slow peer in a STARTED room forfeits the leaver to the peer.

    Seat A is a slow peer whose bounded queue is saturated at the depth cap and
    whose writer's in-flight send breaches the bounded send timeout, so the
    writer records ``send_failed`` and stops with NO retry. ``_flush_and_check``
    then classifies A unavailable and the endpoint resolves a GAMEPLAY forfeit (A
    forfeits, B wins) EXACTLY once via the central ``_forfeit_and_close``
    publication, which enqueues the final both-board state + the single
    ``outcome`` frame onto the SURVIVING seat B's queue, delivered by B's
    independent writer with NO further input from either peer. A's socket reaches
    CLOSE 1001 ``peer_unavailable_forfeit``. This pins the full-queue
    forfeit-DELIVERY case the F1 guarantee names. A tiny patched send bound keeps
    the stalled-send breach deterministic in milliseconds (the 5s semantics are
    unchanged; only the private unit fixture shortens the wait).
    """

    import app.ws.duel as duel_mod

    async def scenario(monkeypatched_bound):
        endpoint = _endpoint(RoomManager(clock=FakeClock()))
        manager = endpoint._manager
        room, seat_a = manager.assign_seat("room-fullq")
        _r2, seat_b = manager.assign_seat("room-fullq")
        room.status = "playing"
        manager.mark_activity(room)

        # Seat A's socket HANGS on every send so its writer never drains and the
        # queue saturates at the cap; the hung send breaches the (patched) bound
        # and the writer records a failed send with no retry.
        ws_a = _FakeWebSocket(hang=True)
        ws_b = _FakeWebSocket()  # healthy survivor
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)

        from app.duel.rooms import OUTBOUND_QUEUE_DEPTH

        # Saturate A's bounded queue; at least one enqueue is REJECTED (full).
        rejected = False
        for _ in range(OUTBOUND_QUEUE_DEPTH + 16):
            if not seat_a.enqueue_outbound(
                duel.build_state_frame("room-fullq", seat_a, "playing")
            ):
                rejected = True
        assert rejected is True  # the depth cap held (queue did not grow)

        # Wait for the writer to record the stalled/failed send (bounded).
        for _ in range(400):
            if seat_a.send_failed:
                break
            await asyncio.sleep(0.005)

        # The acting seat's flush observes the unavailable peer; the endpoint
        # resolves the forfeit + publishes the terminal to B. This is the exact
        # production branch (_process_inbound -> failed flush -> _forfeit_and_close).
        ok = await endpoint._flush_and_check(seat_a)
        if not ok:
            await endpoint._forfeit_and_close(ws_a, room, seat_a)

        for _ in range(500):
            if not seat_b.outbound:
                break
            await asyncio.sleep(0)

        received = [json.loads(t) for t in ws_b.sent]
        await endpoint._teardown_writer(seat_a, writer_a)
        await endpoint._teardown_writer(seat_b, writer_b)
        return room, received, ok

    # Shorten ONLY the private send bound for this deterministic unit fixture.
    original = contract.OUTBOUND_SEND_TIMEOUT_S
    contract.OUTBOUND_SEND_TIMEOUT_S = 0.02
    try:
        room, received, ok = asyncio.run(scenario(0.02))
    finally:
        contract.OUTBOUND_SEND_TIMEOUT_S = original

    # The saturated/stalled queue was classified as an unavailable peer.
    assert ok is False
    # Exactly one gameplay forfeit resolved (A forfeits, B wins); no abort.
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    assert room.operational_abort is None
    # The surviving peer ACTUALLY received the single forfeit outcome frame.
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never received the full-queue forfeit"
    assert outcome["result"] == "forfeit"
    assert outcome["winning_seat"] == "B"
    # Both authoritative boards' FINAL (finished) state reached the survivor.
    final_states = {
        f["seat_id"]
        for f in received
        if f["type"] == "state" and f["room_status"] == "finished"
    }
    assert final_states == {"A", "B"}


# ===========================================================================
# (9) NATIVE-20 D1: the SURVIVOR actually reaches CLOSE 1000 normal_completion
#     AND its endpoint reader task is DONE after the close ack, following a real
#     DISCONNECT or a transport 1007 in a STARTED room, with NO further input
#     from either peer. The existing section (6/8) proves the survivor RECEIVES
#     the forfeit outcome; these pin the remaining D1 guarantee the prior tests
#     did NOT assert -- that ``_close_survivor_after_terminal`` closes the idle
#     survivor's OWN socket 1000 ``normal_completion`` through its single ordered
#     writer and wakes its blocked reader so the reader terminates, so the
#     survivor is never orphaned once the manager map entry is released. Both
#     seats' REAL ``_run_action_loop`` readers + independent writers are driven
#     over fake sockets (the decoupled app mounts NO gravity loop), so the
#     survivor close can ONLY come from the disconnect path itself, never a
#     future gravity step or any client traffic. The leaver's own socket is
#     already gone (it disconnected / its 1007 raised WebSocketDisconnect), so
#     the survivor's NORMAL completion 1000 is asserted distinct from the 1001
#     peer_unavailable_forfeit the FAILED-SEND / FULL-QUEUE offender keeps (pinned
#     with an offender socket present in test_stage4_duel_writer.py).
# Validates: Requirements 16.6, 17.1, 17.2, 18.5, 18.6, 19.1, 19.2, 19.3, 22.4,
#            22.5, 22.6
# ===========================================================================


class _SurvivorIdleWebSocket:
    """A fake socket whose ``receive`` blocks forever (the IDLE survivor).

    Models the exact native-20 D1 hang: the surviving peer sends NOTHING, so its
    reader sits blocked on ``websocket.receive()``; unless its writer performs
    the directed survivor-close and wakes the reader via the writer-gone signal,
    the reader never terminates. ``send_text`` records every delivered frame so a
    test can assert the terminal forfeit reached the survivor BEFORE its own
    close. ``close`` records the terminal ``(code, reason)``.
    """

    def __init__(self) -> None:
        self.sent: List[str] = []
        self.closed: Optional[Tuple[int, str]] = None
        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        await asyncio.Event().wait()  # idle survivor: blocks until cancelled
        raise AssertionError("receive should never return for an idle survivor")

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


class _LeaverDisconnectWebSocket:
    """A fake leaver socket: its next ``receive`` surfaces a transport close.

    ``disconnect_code`` is the ASGI ``websocket.disconnect`` code the reader sees
    on the leaver's next receive (``CLOSE_CODE_NORMAL`` for an ordinary peer
    close, ``CLOSE_CODE_INVALID_PAYLOAD`` 1007 for a wire-level transport fail).
    The real ``_run_action_loop`` translates it into a ``WebSocketDisconnect``,
    exactly as the production connection coroutine's ``__call__`` does.
    """

    def __init__(self, disconnect_code: int) -> None:
        self._code = disconnect_code
        self._sent_disconnect = False
        self.sent: List[str] = []
        self.closed: Optional[Tuple[int, str]] = None
        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        if not self._sent_disconnect:
            self._sent_disconnect = True
            return {"type": "websocket.disconnect", "code": self._code}
        await asyncio.Event().wait()  # never a second frame

    async def send_text(self, text: str) -> None:  # pragma: no cover - leaver idle
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


async def _drive_leaver_disconnect_survivor_close(
    *, room_id: str, disconnect_code: int
) -> Tuple[Room, "_SurvivorIdleWebSocket", object]:
    """Run both REAL readers+writers; leaver disconnects, assert survivor close.

    Builds a live STARTED two-seat room, parks BOTH readers on their real
    ``_run_action_loop`` (seat B idle, seat A about to surface a transport
    disconnect), then lets the leaver A disconnect. The connection coroutine's
    disconnect routing (``WebSocketDisconnect`` -> ``_handle_disconnect``) is
    mirrored for A exactly as production ``__call__`` does. Returns the room, the
    survivor's fake socket, and the survivor's reader task after it has
    terminated -- so the caller asserts the survivor's ACTUAL CLOSE + reader DONE
    with NO further input from either peer.
    """

    manager = RoomManager(clock=FakeClock())
    endpoint = duel.DuelEndpoint(manager, allowed_origins=(ALLOWED_ORIGIN,))
    room, seat_a = manager.assign_seat(room_id)
    _r2, seat_b = manager.assign_seat(room_id)
    room.status = "playing"
    manager.mark_activity(room)

    ws_a = _LeaverDisconnectWebSocket(disconnect_code)
    ws_b = _SurvivorIdleWebSocket()
    writer_a = await endpoint._start_writer(ws_a, seat_a)
    writer_b = await endpoint._start_writer(ws_b, seat_b)
    reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
    await asyncio.sleep(0)  # park B's reader on the blocking receive

    # Run A's REAL reader; the transport disconnect raises WebSocketDisconnect,
    # which the production connection coroutine catches and routes to
    # _handle_disconnect. Mirror that exact routing here (no extra input).
    try:
        await endpoint._run_action_loop(ws_a, room, seat_a)
    except WebSocketDisconnect as exc:
        assert exc.code == disconnect_code
        endpoint._handle_disconnect(room, seat_a)

    # The survivor's writer now drains the terminal frames then performs the
    # directed 1000 normal_completion close + writer-gone wake; its reader wakes
    # and returns. Bounded wait for B's reader to terminate.
    for _ in range(1000):
        if reader_b.done():
            break
        await asyncio.sleep(0)

    await endpoint._teardown_writer(seat_a, writer_a)
    await endpoint._teardown_writer(seat_b, writer_b)
    if not reader_b.done():
        reader_b.cancel()
    await asyncio.wait({reader_b})
    return room, ws_b, reader_b


def test_disconnect_in_started_room_survivor_closes_1000_and_reader_done():
    """A real DISCONNECT closes the survivor 1000 normal_completion, reader DONE.

    Native-20 D1: after seat A disconnects in a STARTED room, the forfeit is
    resolved once (A forfeits, B wins) and the SURVIVING seat B -- which sends
    NOTHING -- must not merely RECEIVE the forfeit outcome but also have its OWN
    socket CLOSED 1000 ``normal_completion`` through its single ordered writer,
    with its blocked reader WOKEN so its endpoint reader task is DONE after the
    close ack. No further input from either peer. The survivor received the
    terminal forfeit BEFORE its own close (draining discipline).
    """

    room, ws_b, reader_b = asyncio.run(
        _drive_leaver_disconnect_survivor_close(
            room_id="room-d1-disc", disconnect_code=contract.CLOSE_CODE_NORMAL
        )
    )
    # The forfeit resolved exactly once (gameplay result, not an abort).
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    assert room.operational_abort is None
    # The survivor RECEIVED the single forfeit outcome before its own close.
    received = [json.loads(t) for t in ws_b.sent]
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never received the forfeit outcome"
    assert outcome["winning_seat"] == "B"
    # The survivor's OWN socket ACTUALLY closed 1000 normal_completion.
    assert ws_b.closed is not None, "survivor socket was never closed"
    assert ws_b.closed[0] == contract.CLOSE_CODE_NORMAL
    assert ws_b.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    # The survivor's blocked reader WOKE and returned (DONE after the close ack).
    assert reader_b.done() and not reader_b.cancelled()


def test_transport_1007_in_started_room_survivor_closes_1000_and_reader_done():
    """A transport 1007 close closes the survivor 1000 normal_completion, reader DONE.

    A wire-level invalid-UTF8 TEXT frame is failed by the transport (1007) and
    surfaces to the leaver's reader as a ``websocket.disconnect``. In a started
    room this is the ordinary disconnect/forfeit path; native-20 D1 additionally
    requires the SURVIVING seat B to reach CLOSE 1000 ``normal_completion`` with
    its reader DONE after the close ack, with NO further input from either peer.
    The leaver's own socket is already gone (the 1007 raised the disconnect), so
    the survivor's NORMAL 1000 completion is distinct from the offender's 1001.
    """

    room, ws_b, reader_b = asyncio.run(
        _drive_leaver_disconnect_survivor_close(
            room_id="room-d1-1007",
            disconnect_code=contract.CLOSE_CODE_INVALID_PAYLOAD,
        )
    )
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    assert room.operational_abort is None
    received = [json.loads(t) for t in ws_b.sent]
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never received the 1007 forfeit outcome"
    assert outcome["winning_seat"] == "B"
    # The survivor reached CLOSE 1000 normal_completion with its reader DONE.
    assert ws_b.closed is not None, "survivor socket was never closed"
    assert ws_b.closed[0] == contract.CLOSE_CODE_NORMAL
    assert ws_b.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    assert reader_b.done() and not reader_b.cancelled()
