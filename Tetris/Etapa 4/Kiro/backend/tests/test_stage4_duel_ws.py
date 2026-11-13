"""Stage 4 (Option A) M3 duel WebSocket tests (task 14.2).

This module hosts the numbered Correctness **Property 12** (strict
expected-revision acceptance window) plus the duel ``/ws/duel`` CONNECTION
tests for the endpoint built in task 14.1 (``app/ws/duel.py``). It is the test
counterpart of task 14.1 and sits beside the room-layer properties
(``tests/test_stage4_duel_properties.py``, task 12.2).

How the live socket is driven
------------------------------
The connection tests build their OWN minimal FastAPI app that mounts
``build_duel_router(manager)`` with a deterministic, injectable ``FakeClock``
manager and NO background gravity/cleanup loop. This keeps the tests decoupled
from the app-wiring task (15.1) and fully deterministic: gravity never fires on
its own, so every revision/outcome a test observes is caused by the action it
sent, never by a real-time timer. The Starlette ``TestClient`` runs the ASGI
app in-process over its own WebSocket transport, so a live ``websocket_connect``
works WITHOUT the production WS engine (``wsproto``/``websockets``) that task
15.2 pins for the uvicorn runtime.

A separate group of tests drives the REAL solo app (``app.main.app``) through
``TestClient`` to assert the inherited solo surface is preserved while a duel is
live: duel results never reach ``GET /api/high-scores``, solo play and solo
SQLite persistence keep working during a duel, and the restrictive HTTP CORS
policy is unchanged.

Invalid-UTF8 note (documented limitation)
-----------------------------------------
A GENUINE wire-level invalid-UTF8 TEXT frame (a masked TEXT frame whose payload
is the raw byte ``0xFF``) is failed by the transport with the standard close
code 1007 (RFC 6455 §8.1 / §7.4.1). The in-process ASGI ``TestClient`` transport
CANNOT represent such a frame: an ASGI ``websocket.receive`` TEXT event carries a
Python ``str`` (always valid Unicode), so there is no way to inject a raw
invalid-UTF8 TEXT frame through ``TestClient`` (its send surface is
``send_text`` / ``send_bytes`` / ``send_json`` only). The raw-wire 1007
assertion is therefore labelled a RESEARCHER / production-proxy check and is NOT
fabricated here. What IS asserted end-to-end is the DISTINCT application-visible
path: a browser binary ``Uint8Array`` carrying ``0xFF`` arrives as an in-band
BINARY frame and gets the ``malformed_message`` ``ErrorFrame`` path. The 1007
SEMANTICS (a 1007 close in a STARTED room runs the ordinary disconnect / forfeit
/ once-only cleanup; a waiting-alone 1007 fabricates no winner) are asserted
behaviorally by closing the live socket with code 1007 and observing the room's
set-once resolution.

These tests NEVER touch the solo store from the duel path: each duel seat owns a
PRIVATE ``engine.new_game`` game, so ZERO SQL writes come from the duel.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st
from starlette.websockets import WebSocketDisconnect

from app.duel import gravity
from app.duel.rooms import RoomManager, Seat
from app.ws import contract
from app.ws import duel


# ---------------------------------------------------------------------------
# Deterministic injectable clock (mirrors tests/test_stage4_duel_properties.py).
# ---------------------------------------------------------------------------


class FakeClock:
    """A deterministic, monotonic, injectable clock for the RoomManager.

    ``__call__`` returns the current value so it is a drop-in for
    ``time.monotonic``; ``advance`` moves time forward. Using an injectable clock
    (Req 19.4) keeps every connection test deterministic -- no wall-clock timer
    ever fires between the frames a test sends.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, delta: float) -> None:
        if delta < 0:
            raise ValueError("clock must be monotonic")
        self._now += delta


ALLOWED_ORIGIN = "http://localhost:5517"
DISALLOWED_ORIGIN = "http://evil.example"


def _build_app(
    *,
    clock: Optional[FakeClock] = None,
    allowed_origins: Tuple[str, ...] = (ALLOWED_ORIGIN,),
    **manager_kwargs,
) -> Tuple[FastAPI, RoomManager]:
    """Build a minimal FastAPI app mounting the duel router (no gravity loop).

    Returns ``(app, manager)`` so a test can both drive the socket via a
    ``TestClient`` and inspect the lifespan-free manager's rooms directly. The
    manager uses a ``FakeClock`` so gravity NEVER advances on its own; this
    decouples the connection tests from the app-wiring task (15.1) and keeps the
    revision/outcome a test observes caused solely by the action it sent.
    """

    manager = RoomManager(clock=clock or FakeClock(), **manager_kwargs)
    app = FastAPI()
    app.include_router(duel.build_duel_router(manager, allowed_origins=allowed_origins))
    return app, manager


# ---------------------------------------------------------------------------
# Small live-socket helpers (handshake drain, action framing, terminal drain).
# ---------------------------------------------------------------------------


def _hello(ws, room_id: str) -> None:
    """Send a valid ``hello`` for ``room_id``."""

    ws.send_text(
        json.dumps(
            {"type": "hello", "protocol_version": contract.PROTOCOL_VERSION, "room_id": room_id}
        )
    )


def _action(
    seat_id: str,
    action_id: str,
    expected_revision: int,
    kind: str,
    room_id: str,
) -> str:
    """Serialize a valid ``action`` frame to JSON text."""

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
    """Receive one JSON frame and parse it."""

    return json.loads(ws.receive_text())


def _handshake_first_seat(ws, room_id: str) -> dict:
    """Drive the first seat's handshake: hello -> welcome + waiting state.

    Returns the parsed waiting ``state`` frame after draining the ``welcome``.
    """

    _hello(ws, room_id)
    welcome = _recv(ws)
    assert welcome["type"] == "welcome"
    assert welcome["seat_id"] == "A"
    assert welcome["room_status"] == "waiting"
    state = _recv(ws)
    assert state["type"] == "state"
    assert state["room_status"] == "waiting"
    assert state["revision"] == 0
    return state


def _drain_until(ws, *, action_id: Optional[str] = None, types=("ack", "reject")) -> dict:
    """Drain queued frames until a correlated ack/reject (or a wanted type).

    The endpoint may flush pending ``state`` frames (e.g. the playing-state frame
    enqueued at start) BEFORE the ack/reject for the action just sent; this
    helper drains those first so the assertion targets the correlated reply.
    """

    while True:
        frame = _recv(ws)
        if frame["type"] in types:
            if action_id is None or frame.get("action_id") == action_id:
                return frame


def _connect_two_seats(
    client: TestClient, room_id: str
) -> Tuple[object, object]:
    """Open both seats for ``room_id`` and drain each handshake to start.

    Returns the two open ``WebSocketTestSession`` context managers (already
    ``__enter__``-ed); the caller is responsible for closing them. After the
    second seat joins the room transitions to ``playing``; the second seat
    drains welcome + waiting-state + playing-state, the first seat's playing
    state is flushed lazily on its next outbound.
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
    # Native-14/task-30.2 both-boards delivery: the room starts on B's join, so
    # B receives the START transition as TWO playing StateFrames (seat A board
    # AND seat B board), NOT a standalone waiting frame then a single own frame.
    start_b = _drain_both_playing_boards(b)
    assert {f["seat_id"] for f in start_b} == {"A", "B"}
    assert all(f["room_status"] == "playing" for f in start_b)

    # Stash the context managers on the sessions so the caller can close cleanly.
    a._cm = a_cm  # type: ignore[attr-defined]
    b._cm = b_cm  # type: ignore[attr-defined]
    return a, b


def _drain_both_playing_boards(ws) -> List[dict]:
    """Drain the two playing ``state`` frames (seat A + seat B) of a transition.

    A single state transition (start, accepted action, gravity) now delivers
    BOTH authoritative boards to every peer: one StateFrame per seat, each with
    its own ``seat_id``/``revision`` and the shared ``room_status``. This helper
    reads exactly two ``state`` frames with ``room_status == "playing"``,
    skipping any interleaved non-state frame, and returns them.
    """

    frames: List[dict] = []
    while len(frames) < 2:
        frame = _recv(ws)
        if frame["type"] == "state" and frame["room_status"] == "playing":
            frames.append(frame)
    return frames


def _close_sessions(*sessions) -> None:
    """Close each stashed websocket context manager, swallowing teardown noise."""

    for s in sessions:
        cm = getattr(s, "_cm", None)
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass


# ===========================================================================
# Property 12: Strict expected-revision acceptance window.
#
# For any (authoritative_revision, expected_revision) pair, the strict-equality
# revision decision ACCEPTS iff the two are EQUAL, REJECTS a LOWER
# expected_revision as ``stale_revision``, and REJECTS a HIGHER one as
# ``future_revision``. Neither rejection mutates the board (the endpoint does not
# call the engine on a stale/future decision). This exercises the PURE
# ``decide_revision`` helper over a broad input space (every ordering of the two
# revisions, including the boundaries just-below / just-above / equal), which is
# exactly the acceptance window the endpoint enforces at step 7 of the ordered
# check sequence.
#
# The same window is also exercised END-TO-END over a live socket in the
# connection tests below (stale/future/exact-apply), so Property 12 is proven
# both for broad input coverage (here) and on the integration path (there).
#
# Validates: Requirements 20.4, 20.6, 20.7
# ===========================================================================
# Feature: tetris-stage4-option-a, Property 12
@settings(max_examples=300)
@given(
    authoritative=st.integers(min_value=0, max_value=contract.SAFE_INT_MAX),
    expected=st.integers(min_value=0, max_value=contract.SAFE_INT_MAX),
)
def test_property_12_strict_expected_revision_window(authoritative, expected):
    # A seat whose authoritative revision is the generated value. We set the
    # revision directly on a real Seat so the helper is exercised exactly as the
    # endpoint calls it (seat.revision is the authoritative board revision).
    seat = Seat(seat_id="A", game=object(), rng_seed=0, revision=authoritative)

    decision = duel.decide_revision(seat, expected)

    if expected == authoritative:
        # Exact match -> ACCEPT (proceed to apply at step 8).
        assert decision == duel.DECISION_APPLY
    elif expected < authoritative:
        # A LOWER expected revision is STALE.
        assert decision == duel.DECISION_STALE
    else:
        # A HIGHER expected revision is from the FUTURE.
        assert decision == duel.DECISION_FUTURE

    # The decision NEVER mutates the seat's authoritative revision (a stale /
    # future rejection leaves the board untouched; an exact match does not bump
    # the revision here -- the apply step, not the decision, does that).
    assert seat.revision == authoritative

    # The accept predicate is EXACTLY strict equality, nothing wider or narrower.
    assert (decision == duel.DECISION_APPLY) == (expected == authoritative)


# Feature: tetris-stage4-option-a, Property 12
@settings(max_examples=150)
@given(authoritative=st.integers(min_value=1, max_value=contract.SAFE_INT_MAX - 1))
def test_property_12_boundaries_are_rejections(authoritative):
    """The two values ADJACENT to the authoritative revision are the window edge.

    Just-below is the tightest stale case and just-above the tightest future
    case; only the exact value is accepted, confirming the window has width zero.
    """

    seat = Seat(seat_id="A", game=object(), rng_seed=0, revision=authoritative)
    assert duel.decide_revision(seat, authoritative - 1) == duel.DECISION_STALE
    assert duel.decide_revision(seat, authoritative) == duel.DECISION_APPLY
    assert duel.decide_revision(seat, authoritative + 1) == duel.DECISION_FUTURE


# ===========================================================================
# Connection tests over a live TestClient websocket (decoupled minimal app).
# ===========================================================================


def test_handshake_hello_welcome_waiting_state():
    """hello -> welcome + authoritative waiting ``state`` for the first seat."""

    app, manager = _build_app()
    client = TestClient(app)
    with client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN}) as ws:
        state = _handshake_first_seat(ws, "room-handshake")
        assert state["seat_id"] == "A"
        assert state["status"] == "playing"  # the board itself is playing
        assert state["active_piece"] is not None
        assert manager.rooms["room-handshake"].status == "waiting"


def test_start_gating_requires_both_seats():
    """An action is gated ``not_started`` until BOTH seats are present."""

    app, manager = _build_app()
    client = TestClient(app)
    with client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN}) as a:
        _handshake_first_seat(a, "room-gate")
        # Only one seat: the room is waiting, so an action is not_started.
        a.send_text(_action("A", "A-1", 0, "left", "room-gate"))
        reject = _drain_until(a, action_id="A-1", types=("reject",))
        assert reject["reason"] == "not_started"
        # not_started does NOT consume the ordinal / high-water mark.
        assert manager.rooms["room-gate"].seats["A"].last_action_seq == 0
        assert manager.rooms["room-gate"].status == "waiting"


def test_applied_action_acks_and_emits_bumped_state():
    """An applied action acks (no_op=False) and emits a fresh bumped ``state``."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-apply")
    try:
        # 'left' from spawn is a real move -> applied, revision bumps 0 -> 1.
        a.send_text(_action("A", "A-1", 0, "left", "room-apply"))
        ack = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack["applied"] is True
        assert ack["no_op"] is False
        assert ack["revision"] == 1
        # Both authoritative boards follow the ack on a real change: the acting
        # seat A board (now revision 1) AND the opponent seat B board. A sees
        # BOTH, never only its own.
        boards = _drain_both_playing_boards(a)
        by_seat = {f["seat_id"]: f for f in boards}
        assert set(by_seat) == {"A", "B"}
        assert by_seat["A"]["revision"] == 1
        assert manager.rooms["room-apply"].seats["A"].revision == 1
    finally:
        _close_sessions(a, b)


def test_no_op_action_acks_applied_true_no_op_true_unchanged_revision():
    """A legal no-op acks applied=True, no_op=True with the UNCHANGED revision."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-noop")
    try:
        # A first 'hold' swaps the active piece into Hold (a real change) and
        # clears can_hold; this bumps the revision 0 -> 1.
        a.send_text(_action("A", "A-1", 0, "hold", "room-noop"))
        ack1 = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack1["no_op"] is False
        assert ack1["revision"] == 1
        _drain_both_playing_boards(a)  # drain both boards from the applied hold

        # A SECOND consecutive 'hold' is rejected by the engine (can_hold is
        # False), so it changes nothing: a legal NO-OP acked applied=True,
        # no_op=True with the UNCHANGED revision 1. This no-op is seed
        # independent (it never depends on the spawned piece's geometry).
        a.send_text(_action("A", "A-2", 1, "hold", "room-noop"))
        ack2 = _drain_until(a, action_id="A-2", types=("ack",))
        assert ack2["applied"] is True
        assert ack2["no_op"] is True
        assert ack2["revision"] == 1
        assert manager.rooms["room-noop"].seats["A"].revision == 1
    finally:
        _close_sessions(a, b)


def test_stale_and_future_revision_rejects():
    """A lower expected_revision is stale; a higher one is future (live path)."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-sf")
    try:
        # Advance the board to revision 1 with an applied move.
        a.send_text(_action("A", "A-1", 0, "left", "room-sf"))
        ack = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack["revision"] == 1
        _drain_both_playing_boards(a)  # drain both boards from the applied move

        # expected_revision 0 < authoritative 1 -> stale.
        a.send_text(_action("A", "A-2", 0, "left", "room-sf"))
        stale = _drain_until(a, action_id="A-2", types=("reject",))
        assert stale["reason"] == "stale_revision"
        assert stale["authoritative_revision"] == 1

        # expected_revision 5 > authoritative 1 -> future.
        a.send_text(_action("A", "A-3", 5, "left", "room-sf"))
        future = _drain_until(a, action_id="A-3", types=("reject",))
        assert future["reason"] == "future_revision"
        assert future["authoritative_revision"] == 1
    finally:
        _close_sessions(a, b)


def test_duplicate_action_id_idempotency_returns_cached_reply():
    """A re-sent identical action_id returns the cached reply verbatim."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-dup")
    try:
        a.send_text(_action("A", "A-1", 0, "left", "room-dup"))
        ack1 = _drain_until(a, action_id="A-1", types=("ack",))
        _drain_both_playing_boards(a)  # drain both boards from the first apply
        rev_after = manager.rooms["room-dup"].seats["A"].revision

        # Re-send the IDENTICAL action_id + fingerprint: the cached ack is
        # returned verbatim and NOTHING is re-applied (revision unchanged).
        a.send_text(_action("A", "A-1", 0, "left", "room-dup"))
        ack2 = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack2 == ack1
        assert manager.rooms["room-dup"].seats["A"].revision == rev_after
    finally:
        _close_sessions(a, b)


def test_duplicate_action_conflict_for_id_below_high_water_mark():
    """An uncached id at/below the high-water mark rejects duplicate_conflict."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-conf")
    try:
        # Advance the high-water mark to ordinal 5 with a new action A-5.
        a.send_text(_action("A", "A-5", 0, "cw", "room-conf"))
        _drain_until(a, action_id="A-5", types=("ack", "reject"))
        assert manager.rooms["room-conf"].seats["A"].last_action_seq == 5

        # A-3 is below the mark and was never cached -> duplicate_action_conflict,
        # never applied.
        a.send_text(_action("A", "A-3", 0, "cw", "room-conf"))
        reject = _drain_until(a, action_id="A-3", types=("reject",))
        assert reject["reason"] == "duplicate_action_conflict"
    finally:
        _close_sessions(a, b)


def test_not_seat_owner_reject():
    """An action naming a seat the sender does not own rejects not_seat_owner."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-owner")
    try:
        # Seat A sends an action targeting seat B (a canonical B- action_id).
        a.send_text(_action("B", "B-1", 0, "left", "room-owner"))
        reject = _drain_until(a, action_id="B-1", types=("reject",))
        assert reject["reason"] == "not_seat_owner"
        # The targeted (other) seat's board was not mutated.
        assert manager.rooms["room-owner"].seats["B"].revision == 0
    finally:
        _close_sessions(a, b)


def test_not_started_while_waiting_does_not_consume_ordinal():
    """A waiting-room action is not_started and does not burn the ordinal."""

    app, manager = _build_app()
    client = TestClient(app)
    with client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN}) as a:
        _handshake_first_seat(a, "room-ns")
        a.send_text(_action("A", "A-7", 0, "left", "room-ns"))
        reject = _drain_until(a, action_id="A-7", types=("reject",))
        assert reject["reason"] == "not_started"
        # The high-water mark is untouched: a later real action can still use 7.
        assert manager.rooms["room-ns"].seats["A"].last_action_seq == 0
        assert "A-7" not in manager.rooms["room-ns"].seats["A"].reply_cache.action_ids()


def test_oversize_message_closes_1009():
    """An oversize inbound TEXT frame closes 1009 without buffering it whole."""

    app, manager = _build_app(max_msg_bytes=128)
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-big")
    try:
        # Native-14/task-30.2 correction: seat A's independent writer delivers
        # A's pending playing both-board frames PROACTIVELY (no inbound traffic
        # needed), so drain BOTH first; the oversize 1009 close is ordered after.
        start_a = _drain_both_playing_boards(a)
        assert {f["seat_id"] for f in start_a} == {"A", "B"}
        with pytest.raises(WebSocketDisconnect) as excinfo:
            a.send_text("x" * 512)
            # The endpoint closes before any reply; the next receive observes it.
            a.receive_text()
        assert excinfo.value.code == contract.CLOSE_CODE_OVERSIZE
    finally:
        _close_sessions(b)


def test_oversize_first_hello_handshake_closes_1009_before_parse():
    """The FIRST Hello/handshake is bounded by the 4096 byte cap -> 1009 (task 35.4).

    An oversize FIRST handshake frame is caught by the SAME UTF-8 byte bound as a
    post-handshake action, applied BEFORE any JSON/model parse, and closes with
    the STANDARD oversize code 1009 -- NOT the 1008 malformed/policy close the
    pre-correction code emitted when an oversize Hello fell through to the hello
    decode. The oversize Hello here is valid JSON (a real ``hello`` payload padded
    past the byte bound), so the 1009 is driven by the byte cap, not a parse
    failure.
    """

    app, manager = _build_app(max_msg_bytes=128)
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
    ) as ws:
        # A well-formed hello payload whose UTF-8 byte length exceeds the 128-byte
        # bound: the oversize cap must fire BEFORE the model parse, so the valid
        # JSON never reaches ``_parse_hello``.
        oversize_hello = json.dumps(
            {
                "type": "hello",
                "protocol_version": contract.PROTOCOL_VERSION,
                "room_id": "room-oversize-hello",
                "pad": "x" * 256,
            }
        )
        assert len(oversize_hello.encode("utf-8")) > 128
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.send_text(oversize_hello)
            # The endpoint closes before any welcome/state; the next receive sees it.
            ws.receive_text()
        assert excinfo.value.code == contract.CLOSE_CODE_OVERSIZE
    # No seat was ever assigned: the room was never created (closed pre-parse).
    assert "room-oversize-hello" not in manager.rooms


def test_oversize_binary_first_hello_closes_1009_not_malformed():
    """An oversize BINARY first frame is oversize (1009), not the malformed path.

    The byte-bound classification runs BEFORE the binary->malformed handshake
    mapping, so an oversize binary first frame closes 1009 like any other
    oversize message; only an IN-BOUND binary first frame takes the
    ``malformed_message`` handshake path (asserted separately).
    """

    app, manager = _build_app(max_msg_bytes=128)
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.send_bytes(bytes([0x00]) * 256)  # oversize binary first frame
            ws.receive_text()
        assert excinfo.value.code == contract.CLOSE_CODE_OVERSIZE


def test_inbound_binary_first_hello_still_malformed_handshake():
    """An IN-BOUND binary first frame keeps the malformed-handshake path (1008).

    This preserves the pre-task-35.4 binary-first-frame behaviour: a small
    (within-bound) binary first frame is an application-visible malformed
    handshake answered with an ``ErrorFrame(malformed_message)`` and a 1008
    policy close, NOT the oversize 1009 path. Only the oversize classification
    changed; the in-bound binary classification is unchanged.
    """

    app, manager = _build_app()
    client = TestClient(app)
    with client.websocket_connect(
        "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
    ) as ws:
        ws.send_bytes(bytes([0xFF]))  # small in-bound binary first frame
        error = _recv(ws)
        assert error["type"] == "error"
        assert error["reason"] == "malformed_message"
        assert error["detail"] == "Malformed message."
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()
        assert excinfo.value.code == contract.CLOSE_CODE_POLICY


def test_rate_limit_breach_rejects_then_closes_1008():
    """Breaching the fixed-window rate emits reject(rate_limited) then 1008."""

    app, manager = _build_app(action_rate_per_seat=3)
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-rate")
    try:
        rev = 0
        reasons: List[str] = []
        close_code: Optional[int] = None
        try:
            for i in range(1, 6):
                aid = f"A-{i}"
                a.send_text(_action("A", aid, rev, "cw", "room-rate"))
                frame = _drain_until(a, action_id=aid, types=("ack", "reject"))
                if frame["type"] == "ack":
                    rev = frame["revision"]
                else:
                    reasons.append(frame["reason"])
        except WebSocketDisconnect as exc:
            close_code = exc.code
        # The 4th action in the same fixed 1-second window breaches the budget.
        assert "rate_limited" in reasons
        assert close_code == contract.CLOSE_CODE_POLICY
    finally:
        _close_sessions(b)


def test_room_at_maximum_emits_error_frame_and_bounded_close():
    """A second DISTINCT room over max_rooms is a bounded ErrorFrame + close."""

    app, manager = _build_app(max_rooms=1)
    client = TestClient(app)
    with client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN}) as a:
        _handshake_first_seat(a, "room-one")
        # A second distinct room would exceed max_rooms=1: bounded rejection.
        with client.websocket_connect(
            "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
        ) as b:
            _hello(b, "room-two")
            error = _recv(b)
            assert error["type"] == "error"
            assert error["reason"] == "room_closed"
            # detail is a short fixed English string with no internals.
            assert error["detail"] == "Server is at capacity."
            with pytest.raises(WebSocketDisconnect) as excinfo:
                b.receive_text()
            assert excinfo.value.code == contract.CLOSE_CODE_POLICY


def test_origin_rejection_denies_the_http_upgrade():
    """A disallowed Origin is denied at the HTTP upgrade (no normal CLOSE frame).

    Closing BEFORE ``accept()`` rejects the upgrade; Starlette's ``TestClient``
    surfaces this as a ``WebSocketDisconnect`` raised while ENTERING the context
    manager (the socket never opened), which is distinct from a normal in-session
    CLOSE frame.
    """

    app, manager = _build_app(allowed_origins=(ALLOWED_ORIGIN,))
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/ws/duel", headers={"origin": DISALLOWED_ORIGIN}
        ) as ws:
            # Reaching a receive would mean the upgrade opened: it must not.
            ws.receive_text()
    assert excinfo.value.code == contract.CLOSE_CODE_POLICY
    # No room was ever created for the denied connection.
    assert manager.rooms == {}


def test_missing_origin_is_denied_fail_closed():
    """An absent Origin header is DENIED (fail closed), never silently trusted."""

    app, manager = _build_app(allowed_origins=(ALLOWED_ORIGIN,))
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/duel") as ws:
            ws.receive_text()
    assert excinfo.value.code == contract.CLOSE_CODE_POLICY


def test_malformed_json_text_frame_gets_error_frame():
    """A well-formed socket frame that is not valid JSON -> malformed_message."""

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-badjson")
    try:
        a.send_text("this is not json {")
        error = _drain_until(a, types=("error",))
        assert error["reason"] == "malformed_message"
        assert error["detail"] == "Malformed message."
        # A malformed message never burns the seat's sequence.
        assert manager.rooms["room-badjson"].seats["A"].last_action_seq == 0
    finally:
        _close_sessions(a, b)


# ---------------------------------------------------------------------------
# Invalid-UTF8 / binary distinction (Req 22.5; RFC 6455 §8.1 / §7.4.1).
# ---------------------------------------------------------------------------


def test_browser_binary_uint8array_ff_gets_malformed_message_error_frame():
    """A browser binary ``Uint8Array`` 0xFF frame -> ``malformed_message`` path.

    This is the APPLICATION-VISIBLE in-band BINARY frame, DISTINCT from a
    wire-level invalid-UTF8 TEXT frame. An in-band binary frame reaches the
    endpoint as a ``bytes`` payload and is answered with an ``ErrorFrame`` whose
    reason is ``malformed_message`` -- it does NOT fail the transport.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-bin")
    try:
        a.send_bytes(bytes([0xFF]))  # a browser Uint8Array([0xFF]) binary frame
        error = _drain_until(a, types=("error",))
        assert error["reason"] == "malformed_message"
        assert error["detail"] == "Malformed message."
        # The seat is NOT torn down by an application-visible malformed binary:
        # the loop continues, so a subsequent valid action still works.
        a.send_text(_action("A", "A-1", 0, "left", "room-bin"))
        ack = _drain_until(a, action_id="A-1", types=("ack",))
        assert ack["applied"] is True
    finally:
        _close_sessions(a, b)


def test_raw_invalid_utf8_text_frame_1007_is_a_researcher_check():
    """RESEARCHER / production-proxy check: raw invalid-UTF8 TEXT -> 1007.

    A GENUINE masked TEXT frame carrying the raw byte ``0xFF`` is failed by the
    transport with the standard close code 1007 (RFC 6455 §8.1 / §7.4.1). The
    in-process ASGI ``TestClient`` transport CANNOT represent such a frame: an
    ASGI ``websocket.receive`` TEXT event always carries a valid-Unicode Python
    ``str``, and ``TestClient``'s send surface is ``send_text`` / ``send_bytes``
    / ``send_json`` only -- none can emit a raw invalid-UTF8 TEXT frame. We
    therefore do NOT fabricate a 1007 we did not observe; the raw-wire assertion
    is a production-proxy (a real browser / WS engine such as the task-15.2 pin)
    check. The DISTINCT application-visible binary 0xFF path IS asserted
    end-to-end above, and the 1007 SEMANTICS (forfeit vs no-winner) are asserted
    behaviorally below.
    """

    # Confirm the documented transport limitation structurally: the TestClient
    # websocket session exposes no API to inject a raw invalid-UTF8 TEXT frame.
    from starlette.testclient import WebSocketTestSession

    send_methods = {m for m in dir(WebSocketTestSession) if m.startswith("send")}
    assert send_methods == {"send", "send_bytes", "send_json", "send_text"}
    # A Python str is always valid Unicode, so send_text cannot carry raw 0xFF;
    # send_bytes produces a BINARY frame (the malformed_message path), not a
    # TEXT frame. Hence a genuine invalid-UTF8 TEXT frame is unreachable here.
    pytest.skip(
        "Researcher check: a genuine wire-level invalid-UTF8 TEXT frame (raw "
        "0xFF) and its 1007 transport close require a real WS engine / browser; "
        "the in-process ASGI TestClient cannot represent it. The 1007 semantics "
        "are covered behaviorally by the dedicated tests below."
    )


def test_1007_close_in_started_room_runs_forfeit_once():
    """A 1007 close in a STARTED room -> ordinary disconnect/forfeit/once-only.

    Closing the live socket with code 1007 drives the SAME disconnect path the
    endpoint takes for a transport-failed 1007: in a STARTED room the
    disconnecting seat forfeits and the duel resolves EXACTLY once (the other
    seat wins), via the set-once guard.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-1007")
    room = manager.rooms["room-1007"]
    assert room.status == "playing"
    try:
        # Close seat A with code 1007 (the transport invalid-UTF8 close code).
        a.close(code=contract.CLOSE_CODE_INVALID_PAYLOAD)
        # Give the server coroutine a moment to observe the disconnect.
        _wait_until(lambda: room.status == "finished")
        assert room.status == "finished"
        outcome = room.outcome
        assert isinstance(outcome, gravity.OutcomeData)
        assert outcome.result == "forfeit"
        assert outcome.forfeiting_seat == "A"
        assert outcome.losing_seat == "A"
        assert outcome.winning_seat == "B"
    finally:
        _close_sessions(b)


def test_1007_close_while_waiting_alone_fabricates_no_winner():
    """A waiting-alone 1007 close is an operational abort: no winner fabricated."""

    app, manager = _build_app()
    client = TestClient(app)
    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    _handshake_first_seat(a, "room-wait1007")
    room = manager.rooms["room-wait1007"]
    assert room.status == "waiting"

    # Close alone with 1007: a never-started room fabricates NO winner and the
    # room entry is released (no leaked room/outcome).
    a.close(code=contract.CLOSE_CODE_INVALID_PAYLOAD)
    _wait_until(lambda: "room-wait1007" not in manager.rooms)
    assert "room-wait1007" not in manager.rooms
    assert room.outcome is None  # no fabricated winner
    try:
        a_cm.__exit__(None, None, None)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Slow-peer / failed-send cleanup, concurrent-terminal resolution, shutdown.
# ---------------------------------------------------------------------------


def test_failed_send_in_started_room_is_a_forfeit_resolved_once():
    """A failed send / full outbound queue in a STARTED room is a gameplay forfeit.

    A full per-seat outbound queue is treated as a failed/slow peer: the endpoint
    resolves a forfeit via ``gravity.resolve_forfeit`` (set-once). We drive the
    helper the endpoint uses with a two-seat STARTED room so the behavior is
    asserted deterministically without needing to stall a real socket.
    """

    manager = RoomManager(clock=FakeClock())
    room, seat_a = manager.assign_seat("room-slow")
    _room2, seat_b = manager.assign_seat("room-slow")
    room.status = "playing"
    now = manager.clock()

    outcome = gravity.resolve_forfeit(room, "A", now, manager=manager)
    assert outcome is not None
    assert outcome.result == "forfeit"
    assert outcome.forfeiting_seat == "A"
    assert outcome.winning_seat == "B"
    assert room.status == "finished"


def test_concurrent_terminal_resolution_resolves_exactly_once():
    """Two racing terminal events resolve the duel EXACTLY once (set-once)."""

    manager = RoomManager(clock=FakeClock())
    room, _a = manager.assign_seat("room-race")
    _room2, _b = manager.assign_seat("room-race")
    room.status = "playing"
    now = manager.clock()

    # First terminal event wins (A forfeits -> B wins); the second is a no-op.
    first = gravity.resolve_forfeit(room, "A", now, manager=manager)
    second = gravity.resolve_forfeit(room, "B", now, manager=manager)
    assert first is not None and first.result == "forfeit"
    assert first.winning_seat == "B"
    assert second is None  # set-once: the duel never resolves a second time
    assert room.status == "finished"


def test_cleanup_releases_expired_rooms():
    """``cleanup_tick`` releases rooms past their status-keyed retention."""

    clock = FakeClock()
    manager = RoomManager(clock=clock)
    manager.assign_seat("room-expire")
    assert "room-expire" in manager.rooms

    # Advance past the waiting retention; cleanup reaps it with no leak.
    clock.advance(manager.waiting_room_retention + 1)
    reaped = manager.cleanup_tick()
    assert {r.room_id for r in reaped} == {"room-expire"}
    assert "room-expire" not in manager.rooms


def test_shutdown_releases_all_rooms():
    """``shutdown`` releases EVERY room so nothing leaks across shutdown."""

    manager = RoomManager(clock=FakeClock())
    manager.assign_seat("room-s1")
    manager.assign_seat("room-s2")
    assert len(manager.rooms) == 2

    reaped = manager.shutdown()
    assert {r.room_id for r in reaped} == {"room-s1", "room-s2"}
    assert manager.rooms == {}


# ===========================================================================
# Native 14 (task 30.1): independent per-connection writer delivers the start
# frame to the WAITING peer WITHOUT that peer sending anything. This is the
# production-visible blocker the correction fixes (the public Chrome pair saw
# seat A never receive the room_status:"playing" start frame after B joined).
# ===========================================================================


def test_waiting_peer_receives_start_frame_without_inbound_traffic():
    """Seat A gets the playing start frame via its writer with NO A inbound.

    A connects and completes its handshake (welcome + waiting state), then STOPS
    sending. B joins, which transitions the room to ``playing``. Before the
    correction, A's playing StateFrame was only flushed on A's NEXT outbound, so
    a silent A never observed the start. With the independent per-connection
    writer, A's writer delivers the playing frame proactively; A reads it without
    ever sending another frame.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    a = a_cm.__enter__()
    _handshake_first_seat(a, "room-start")

    b_cm = client.websocket_connect("/ws/duel", headers={"origin": ALLOWED_ORIGIN})
    b = b_cm.__enter__()
    try:
        _hello(b, "room-start")
        # Drain B's handshake frames so the room is fully started. The room
        # starts on B's join, so B receives welcome then the START transition as
        # BOTH authoritative boards (seat A board + seat B board), both playing.
        assert _recv(b)["type"] == "welcome"
        start_b = _drain_both_playing_boards(b)
        assert {f["seat_id"] for f in start_b} == {"A", "B"}

        # A sent NOTHING after its handshake (only its earlier waiting frame).
        # Its independent writer must have delivered the START transition anyway:
        # BOTH authoritative boards (its own AND the opponent's), proving a
        # silent waiting peer receives both boards without any inbound traffic.
        start_a = _drain_both_playing_boards(a)
        by_seat = {f["seat_id"]: f for f in start_a}
        assert set(by_seat) == {"A", "B"}
        assert by_seat["A"]["room_status"] == "playing"
        assert by_seat["B"]["room_status"] == "playing"
    finally:
        try:
            b_cm.__exit__(None, None, None)
        except Exception:
            pass
        try:
            a_cm.__exit__(None, None, None)
        except Exception:
            pass


def _wait_until(predicate, *, timeout_s: float = 2.0, interval_s: float = 0.01) -> None:
    """Spin briefly until ``predicate`` is true or the timeout elapses.

    Used only to give the server coroutine a chance to observe a client-side
    close on the in-process transport; it never fabricates a result (the caller
    asserts the real post-condition after this returns).
    """

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_s)


# ===========================================================================
# Solo isolation / preservation (REAL solo app via TestClient).
#
# The duel must not change the inherited solo surface: duel results never reach
# GET /api/high-scores, solo play + solo SQLite persistence keep working during
# a live duel, and the restrictive HTTP CORS policy is unchanged.
# ===========================================================================


def _solo_client() -> TestClient:
    """Return a TestClient over the REAL solo app (lifespan-managed duel runtime).

    The autouse ``_isolated_state`` fixture (tests/conftest.py) points
    ``TETRIS_DB_PATH`` at a fresh temp SQLite file and resets the store accessor,
    so the leaderboard reads from a known, empty baseline per test.
    """

    from app.main import app as solo_app

    return TestClient(solo_app)


def _drive_solo_game_over(client: TestClient, game_id: str) -> dict:
    """Drive a solo game to game_over through the HTTP tick path (persists a HS).

    Obstructs the spawn region on the in-memory game (no line clear), then ticks
    through the production path so the game finalizes and writes its high-score
    summary to the solo SQLite -- exactly the inherited Stage 3 approach.
    """

    from app import store as game_store

    game = game_store.get(game_id)
    for r in range(2):
        for c in range(3, 7):
            game.board[r][c] = "I"
    resp = client.post(f"/api/games/{game_id}/tick")
    assert resp.status_code == 200
    return resp.json()


def test_duel_results_never_appear_in_solo_high_scores():
    """A duel (and its resolution) writes NOTHING to GET /api/high-scores.

    The duel surface is driven against the REAL solo app: a live duel seat plus
    duel actions never touch the solo SQLite, so the leaderboard stays empty. We
    drive a SINGLE seat here (the room stays ``waiting``, so the background
    gravity loop never advances it) to keep the in-process TestClient transport
    deadlock-free; a two-seat STARTED room's terminal resolution is proven to be
    a pure in-memory ``OutcomeData`` (never a store write) by the decoupled
    set-once resolution tests above and the room-layer properties (task 12.2).
    """

    with _solo_client() as client:
        assert client.get("/api/high-scores").json() == {"scores": []}
        with client.websocket_connect(
            "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
        ) as a:
            _hello(a, "iso-room")
            a.receive_text()  # welcome
            a.receive_text()  # waiting state
            # A waiting-room action is gated (not_started) and writes no SQL.
            a.send_text(_action("A", "A-1", 0, "left", "iso-room"))
            reject = _drain_until(a, action_id="A-1", types=("reject",))
            assert reject["reason"] == "not_started"
        # The solo leaderboard is still empty: nothing on the duel path persists.
        assert client.get("/api/high-scores").json() == {"scores": []}


def test_solo_play_and_sqlite_persistence_continue_during_a_duel():
    """Solo create/tick and solo SQLite high-score persistence work mid-duel."""

    with _solo_client() as client:
        with client.websocket_connect(
            "/ws/duel", headers={"origin": ALLOWED_ORIGIN}
        ) as ws:
            _hello(ws, "live-duel")
            ws.receive_text()  # welcome
            ws.receive_text()  # waiting state

            # Solo play continues: create a game and finalize it to SQLite.
            created = client.post("/api/games")
            assert created.status_code == 200
            gid = created.json()["id"]
            terminal = _drive_solo_game_over(client, gid)
            assert terminal["status"] == "game_over"

        # The solo high score persisted to SQLite and is the SOLO game id, never
        # a duel's private ``duel:<room>:<seat>`` id.
        scores = client.get("/api/high-scores").json()["scores"]
        assert len(scores) == 1
        assert scores[0]["game_id"] == gid
        assert not scores[0]["game_id"].startswith("duel:")


def test_restrictive_http_cors_policy_is_preserved_unchanged():
    """The inherited solo CORS policy (5173 allow-list, credentials) is unchanged.

    The duel binds a SEPARATE WS Origin allow-list to the proxy port (5517) and
    must not alter the HTTP CORS middleware: an allowed solo origin is echoed
    with credentials, a disallowed origin is not reflected, and the WS proxy
    origin (5517) is NOT a solo HTTP CORS origin.
    """

    with _solo_client() as client:
        # Allowed solo dev origin is reflected with credentials.
        preflight = client.options(
            "/api/high-scores",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "GET",
            },
        )
        assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert preflight.headers.get("access-control-allow-credentials") == "true"

        # A disallowed origin is NOT reflected (no credentialed grant).
        disallowed = client.get(
            "/api/high-scores", headers={"origin": DISALLOWED_ORIGIN}
        )
        assert disallowed.headers.get("access-control-allow-origin") is None

        # The WS proxy origin (5517) is NOT part of the solo HTTP CORS allow-list.
        ws_origin = client.get(
            "/api/high-scores", headers={"origin": ALLOWED_ORIGIN}
        )
        assert ws_origin.headers.get("access-control-allow-origin") is None


# ===========================================================================
# Native 14 (task 30.3): OPERATIONAL ABORTS wired at the endpoint.
#
# Two whole-room operational aborts are DISTINCT from the gameplay
# ``peer_unavailable_forfeit``: they fabricate NO winner, close BOTH peers with
# the standard going-away code 1001 and a LITERAL reason, release the room, and
# never emit an out-of-range state/revision.
#
#   * SEQUENCE EXHAUSTION: the maximum valid ordinal ``999999999999999`` is
#     CONSUMABLE; the NEXT higher ordinal (which cannot be represented by the
#     1..15-digit grammar) closes the room 1001 ``sequence_exhausted``.
#   * SCALAR OVERFLOW: an applied action whose committed scalar WOULD exceed the
#     SAFE integer bound closes the room 1001 ``scalar_overflow`` WITHOUT ever
#     committing or emitting the out-of-range value.
#
# The researcher checkpoint (docs/validation/12-m3-source-review/report.json)
# found ws/duel.py had NO sequence_exhausted path and that scalar overflow
# closed only the actor then invoked the ordinary disconnect/forfeit (fabricating
# a gameplay outcome). These tests pin the corrected behaviour.
# ===========================================================================


def _close_code_reason(ws) -> Tuple[int, Optional[str]]:
    """Receive until the socket closes; return the (close_code, reason) pair.

    Drains any queued frames first (the acting seat may still have a pending
    both-board playing frame enqueued before the abort), then surfaces the
    server's close code AND literal reason from the ``WebSocketDisconnect`` so a
    test can assert the exact operational-abort reason string.
    """

    try:
        while True:
            ws.receive_text()
    except WebSocketDisconnect as exc:
        return exc.code, getattr(exc, "reason", None)
    raise AssertionError("socket did not close")


# ---------------------------------------------------------------------------
# Pure helpers (deterministic, no socket).
# ---------------------------------------------------------------------------


def test_is_sequence_exhausted_id_recognises_only_the_next_higher_ordinal():
    """The max ordinal is NOT exhaustion; the next-higher 16-digit ordinal IS."""

    # The maximum VALID ordinal (fifteen nines) is consumable, NOT exhaustion.
    assert duel.is_sequence_exhausted_id("A", "A-999999999999999") is False
    # The next higher ordinal (sixteen digits) IS sequence exhaustion.
    assert duel.is_sequence_exhausted_id("A", "A-1000000000000000") is True
    assert duel.is_sequence_exhausted_id("B", "B-1000000000000000") is True
    # A prefix that does NOT match the seat is not this seat's exhaustion.
    assert duel.is_sequence_exhausted_id("A", "B-1000000000000000") is False
    # A non-str / ordinary id / leading-zero id is never exhaustion.
    assert duel.is_sequence_exhausted_id("A", None) is False
    assert duel.is_sequence_exhausted_id("A", 123) is False
    assert duel.is_sequence_exhausted_id("A", "A-1") is False


def test_is_sequence_exhausted_id_rejects_trailing_line_terminators():
    """A 16+-digit id with a trailing line terminator is NOT exhaustion.

    Such an id is a genuine grammar violation (the strict full-string
    ``action_id`` grammar forbids a trailing LF/CR/CRLF/U+2028/U+2029) and must
    take the ordinary schema-error / malformed path, never be reclassified as a
    clean sequence exhaustion.
    """

    for terminator in ("\n", "\r", "\r\n", "\u2028", "\u2029"):
        assert (
            duel.is_sequence_exhausted_id("A", "A-1000000000000000" + terminator)
            is False
        )


def test_would_scalar_overflow_tests_the_would_be_revision_before_commit():
    """``would_scalar_overflow`` catches the WOULD-BE revision, not a bumped one."""

    # At the ceiling, a CHANGING action would bump revision past the bound.
    seat = Seat(seat_id="A", game=object(), rng_seed=0, revision=contract.SAFE_INT_MAX)
    assert duel.would_scalar_overflow(seat, changed=True) is True
    # A NO-OP (no bump) at the ceiling stays exactly at the bound: no overflow.
    assert duel.would_scalar_overflow(seat, changed=False) is False
    # Below the ceiling, a changing action is fine.
    seat_ok = Seat(seat_id="A", game=object(), rng_seed=0, revision=contract.SAFE_INT_MAX - 1)
    assert duel.would_scalar_overflow(seat_ok, changed=True) is False
    # The seat's authoritative revision is never mutated by the pure check.
    assert seat.revision == contract.SAFE_INT_MAX
    assert seat_ok.revision == contract.SAFE_INT_MAX - 1


# ---------------------------------------------------------------------------
# Sequence exhaustion (live socket).
# ---------------------------------------------------------------------------


def test_max_ordinal_consumable_then_next_higher_is_sequence_exhausted():
    """Max ordinal consumed; the next-higher ordinal aborts the ROOM 1001.

    The literal reason is ``sequence_exhausted``, both peers are closed, the room
    is released, and NO gameplay winner is fabricated (``outcome`` stays None) --
    DISTINCT from a forfeit.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-seq")
    room = manager.rooms["room-seq"]
    try:
        # The MAXIMUM valid ordinal (fifteen nines) is CONSUMABLE: a real applied
        # 'left' bumps the revision 0 -> 1 and advances the high-water mark.
        a.send_text(_action("A", "A-999999999999999", 0, "left", "room-seq"))
        ack = _drain_until(a, action_id="A-999999999999999", types=("ack",))
        assert ack["applied"] is True
        assert ack["revision"] == 1
        assert room.seats["A"].last_action_seq == contract.MAX_ACTION_ORDINAL
        _drain_both_playing_boards(a)  # drain the both-board broadcast

        # The NEXT higher ordinal (sixteen digits) cannot be represented by the
        # grammar: it is an OPERATIONAL ABORT closing the room 1001
        # ``sequence_exhausted`` -- NOT a schema reject, NOT a forfeit.
        a.send_text(_action("A", "A-1000000000000000", 1, "left", "room-seq"))
        code, reason = _close_code_reason(a)
        assert code == contract.CLOSE_CODE_GOING_AWAY
        assert reason == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED

        # The OTHER peer is closed with the SAME literal reason (room-wide), with
        # NO inbound traffic from B required.
        code_b, reason_b = _close_code_reason(b)
        assert code_b == contract.CLOSE_CODE_GOING_AWAY
        assert reason_b == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED

        # The abort fabricates NO gameplay winner and releases the room.
        assert room.operational_abort == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED
        assert room.outcome is None
        _wait_until(lambda: "room-seq" not in manager.rooms)
        assert "room-seq" not in manager.rooms
    finally:
        _close_sessions(a, b)


def test_sequence_exhausted_is_distinct_from_peer_unavailable_forfeit():
    """A sequence-exhaustion abort never produces a forfeit OutcomeData.

    The gameplay ``peer_unavailable_forfeit`` resolves a winner via
    ``set_outcome_once``; the operational abort does NOT, so the room's
    ``outcome`` stays None and its ``operational_abort`` marker carries the
    DISTINCT literal reason.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-seq-distinct")
    room = manager.rooms["room-seq-distinct"]
    try:
        a.send_text(_action("A", "A-1000000000000000", 0, "left", "room-seq-distinct"))
        code, reason = _close_code_reason(a)
        assert reason == contract.CLOSE_REASON_SEQUENCE_EXHAUSTED
        # Never the gameplay forfeit reason, never a fabricated OutcomeData.
        assert reason != contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
        assert not isinstance(room.outcome, gravity.OutcomeData)
        assert room.outcome is None
        _close_code_reason(b)
    finally:
        _close_sessions(a, b)


# ---------------------------------------------------------------------------
# Scalar overflow (live socket).
# ---------------------------------------------------------------------------


def test_scalar_overflow_aborts_room_without_emitting_out_of_range_revision():
    """A would-overflow scalar aborts the room 1001 with NO out-of-range emit.

    Seat A is driven to the SAFE integer ceiling; an applied change WOULD bump
    the revision past the bound. The endpoint must NOT commit or emit that
    out-of-range revision: it closes the room 1001 ``scalar_overflow`` for BOTH
    peers, fabricating NO winner. We assert no ack/state frame carrying an
    out-of-range revision is ever delivered before the close.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-ovf")
    room = manager.rooms["room-ovf"]
    try:
        # Drain seat A's pending start both-board frames first.
        _drain_both_playing_boards(a)
        # Pin A's authoritative revision at the SAFE integer ceiling so the next
        # APPLIED (changing) action would bump it to SAFE_INT_MAX + 1.
        room.seats["A"].revision = contract.SAFE_INT_MAX

        # A real 'left' move changes the board, so committing would overflow the
        # revision. The endpoint aborts BEFORE committing/emitting.
        a.send_text(_action("A", "A-1", contract.SAFE_INT_MAX, "left", "room-ovf"))

        # Collect every frame delivered to A until the close; none may carry an
        # out-of-range revision, and no ack for this action may be emitted.
        delivered: List[dict] = []
        try:
            while True:
                delivered.append(_recv(a))
        except WebSocketDisconnect as exc:
            assert exc.code == contract.CLOSE_CODE_GOING_AWAY
            assert getattr(exc, "reason", None) == contract.CLOSE_REASON_SCALAR_OVERFLOW
        for frame in delivered:
            # No out-of-range scalar is ever emitted.
            if "revision" in frame:
                assert frame["revision"] <= contract.SAFE_INT_MAX
            # The overflowing action is never acked.
            assert not (frame.get("type") == "ack" and frame.get("action_id") == "A-1")

        # The authoritative revision was NOT bumped past the bound (the abort was
        # decided BEFORE the commit).
        assert room.seats["A"].revision == contract.SAFE_INT_MAX
        # Room-wide abort, no fabricated winner.
        assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
        assert room.outcome is None

        # The OTHER peer is closed with the same literal reason (room-wide).
        code_b, reason_b = _close_code_reason(b)
        assert code_b == contract.CLOSE_CODE_GOING_AWAY
        assert reason_b == contract.CLOSE_REASON_SCALAR_OVERFLOW
        _wait_until(lambda: "room-ovf" not in manager.rooms)
        assert "room-ovf" not in manager.rooms
    finally:
        _close_sessions(a, b)


def test_scalar_overflow_is_distinct_from_forfeit_and_disconnect():
    """Scalar overflow does NOT invoke the ordinary disconnect/forfeit path.

    The pre-correction code closed only the actor then ran the ordinary
    disconnect, which in a playing room resolved a forfeit (a fabricated gameplay
    winner). The corrected abort leaves ``outcome`` None and sets the DISTINCT
    ``operational_abort`` marker.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-ovf-distinct")
    room = manager.rooms["room-ovf-distinct"]
    try:
        _drain_both_playing_boards(a)
        room.seats["A"].revision = contract.SAFE_INT_MAX
        a.send_text(_action("A", "A-1", contract.SAFE_INT_MAX, "left", "room-ovf-distinct"))
        code, reason = _close_code_reason(a)
        assert reason == contract.CLOSE_REASON_SCALAR_OVERFLOW
        assert reason != contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
        # No forfeit OutcomeData was fabricated for the room.
        assert not isinstance(room.outcome, gravity.OutcomeData)
        assert room.outcome is None
        _close_code_reason(b)
    finally:
        _close_sessions(a, b)


def test_operational_abort_resolves_the_room_exactly_once():
    """``set_operational_abort_once`` aborts the room once; a race loses.

    The first abort wins and records the literal reason; a second abort (or a
    racing gameplay resolution) returns False so the whole room never aborts or
    re-resolves twice, mirroring the set-once outcome guard.
    """

    manager = RoomManager(clock=FakeClock())
    room, _a = manager.assign_seat("room-once")
    _room2, _b = manager.assign_seat("room-once")
    room.status = "playing"

    first = room.set_operational_abort_once(contract.CLOSE_REASON_SCALAR_OVERFLOW)
    second = room.set_operational_abort_once(contract.CLOSE_REASON_SEQUENCE_EXHAUSTED)
    assert first is True
    assert second is False  # set-once: the first reason stands
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    # An operational abort fabricates no gameplay result and does not finish the
    # room here (the endpoint releases the room entry).
    assert room.outcome is None

    # A gameplay resolution after an operational abort does NOT overwrite it:
    # set_outcome_once still succeeds on the room object (distinct guard), but the
    # endpoint's abort path never calls it, so the two markers stay independent.
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW


def test_set_operational_abort_once_loses_to_an_existing_gameplay_outcome():
    """An already-resolved gameplay room cannot be operationally aborted.

    If a gameplay forfeit/terminal already set the room ``outcome`` (status
    ``finished``), a later operational-abort attempt loses the set-once guard, so
    a resolved duel is never converted into an abort.
    """

    manager = RoomManager(clock=FakeClock())
    room, _a = manager.assign_seat("room-resolved")
    _room2, _b = manager.assign_seat("room-resolved")
    room.status = "playing"
    now = manager.clock()
    # A gameplay forfeit resolves the room first.
    assert gravity.resolve_forfeit(room, "A", now, manager=manager) is not None
    assert room.status == "finished"
    # The operational abort now loses: a resolved gameplay room is not aborted.
    assert room.set_operational_abort_once(contract.CLOSE_REASON_SCALAR_OVERFLOW) is False
    assert room.operational_abort is None


# ---------------------------------------------------------------------------
# Preserved strict typing + action_id grammar (FROZEN; not weakened by 30.3).
# ---------------------------------------------------------------------------


def test_strict_int_typing_rejects_bool_string_and_float_one_point_zero():
    """Inbound strict-int fields reject bool / string / lexical 1.0 (preserved).

    Task 30.3 must NOT weaken the STRICT decoded-int typing: a boolean, a string,
    and a float ``1.0`` are all rejected at runtime for ``protocol_version`` and
    ``expected_revision`` (JSON Schema ``integer`` alone would accept an integral
    1.0).
    """

    import pydantic

    base = {
        "type": "action",
        "protocol_version": 1,
        "room_id": "r",
        "seat_id": "A",
        "action_id": "A-1",
        "expected_revision": 0,
        "kind": "left",
    }
    for bad in (True, "0", 1.0):
        payload = dict(base)
        payload["expected_revision"] = bad
        with pytest.raises(pydantic.ValidationError):
            contract.ActionMessage(**payload)
    for bad in (True, "1", 1.0):
        payload = dict(base)
        payload["protocol_version"] = bad
        with pytest.raises(pydantic.ValidationError):
            contract.ActionMessage(**payload)


def test_action_id_grammar_rejects_trailing_line_terminators_preserved():
    """The full-string ``action_id`` grammar still rejects trailing terminators.

    LF / CR / CRLF / U+2028 / U+2029 after the ordinal are rejected by the
    Python ``re``-backed custom validator (never a soft ``$``). Task 30.3 does
    not weaken this; a trailing terminator is a grammar violation, NOT a
    sequence exhaustion.
    """

    for terminator in ("\n", "\r", "\r\n", "\u2028", "\u2029"):
        with pytest.raises(ValueError):
            contract._validate_action_id("A-1" + terminator)
    # The clean canonical id still validates.
    assert contract._validate_action_id("A-1") == "A-1"


def test_sequence_exhausted_id_with_trailing_terminator_is_not_an_abort():
    """A 16-digit id with a trailing LF is a schema error, not an abort.

    Over the live socket such a frame fails the ``action_id`` grammar and is
    answered on the ordinary malformed path (no canonical id to echo), leaving
    the room PLAYING -- it is never reclassified as a clean sequence exhaustion.
    """

    app, manager = _build_app()
    client = TestClient(app)
    a, b = _connect_two_seats(client, "room-seq-bad")
    room = manager.rooms["room-seq-bad"]
    try:
        _drain_both_playing_boards(a)
        # A 16-digit ordinal with a trailing LF: a grammar violation, NOT a clean
        # next-higher ordinal, so it is NOT a sequence-exhaustion abort.
        a.send_text(
            json.dumps(
                {
                    "type": "action",
                    "protocol_version": contract.PROTOCOL_VERSION,
                    "room_id": "room-seq-bad",
                    "seat_id": "A",
                    "action_id": "A-1000000000000000\n",
                    "expected_revision": 0,
                    "kind": "left",
                }
            )
        )
        error = _drain_until(a, types=("error",))
        assert error["reason"] == "malformed_message"
        # The room was NOT aborted and stays playing.
        assert room.operational_abort is None
        assert room.status == "playing"
    finally:
        _close_sessions(a, b)
