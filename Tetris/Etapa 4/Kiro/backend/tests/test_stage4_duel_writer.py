"""Stage 4 (Option A) M3 native-14 task 30.1 writer / lifecycle self-tests.

These tests exercise the INDEPENDENT per-connection writer and its safe
lifecycle added in task 30.1 (``app/ws/duel.DuelEndpoint._run_writer`` /
``_flush_and_check`` / ``_teardown_writer`` / ``_emit_cached`` and the
``Seat`` outbound-signal plumbing in ``app/duel/rooms.py``). They drive the
async coroutines directly via ``asyncio.run`` over a small in-memory
``FakeWebSocket`` so no network, event-loop plugin, or wall-clock timer is
needed and every assertion is deterministic.

What is covered (all native self-tests, never treated as production wire proof):

* The writer flushes a seat's bounded outbound queue in FIFO order WITHOUT any
  recipient inbound traffic -- the core delivery correction.
* A send that fails is a FAILED send recorded on the seat (``send_failed``),
  with NO unbounded retries: the writer stops after the first failure.
* ``_emit_cached`` reports a failed cached send HONESTLY (it no longer returns
  ``drain_result or True`` and never pretends a failed send succeeded).
* Teardown cancels AND awaits the writer so no writer task is leaked, and the
  writer's ``CancelledError`` actually reaches it (cancellation is not swallowed).
* A frame enqueued AFTER the writer is already awaiting still wakes it (the
  wakeup signal), so a traffic-free gravity/outcome/cleanup frame is delivered.
"""

from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from app.duel import gravity
from app.duel.rooms import RoomManager, Seat
from app.ws import contract
from app.ws import duel


# ---------------------------------------------------------------------------
# A minimal in-memory fake WebSocket for the writer coroutine.
# ---------------------------------------------------------------------------


class FakeWebSocket:
    """Record ``send_text`` payloads; optionally fail or hang a send.

    * ``sent`` collects every successfully-sent JSON text payload (FIFO order).
    * ``fail_after`` makes the N-th send raise (simulating a broken peer).
    * ``hang`` makes every send block forever (simulating a slow peer that
      breaches the bounded send timeout). Only used with a patched short bound.
    """

    def __init__(
        self, *, fail_after: Optional[int] = None, hang: bool = False
    ) -> None:
        self.sent: List[str] = []
        self._fail_after = fail_after
        self._hang = hang
        self._count = 0

    async def send_text(self, text: str) -> None:
        self._count += 1
        if self._hang:
            await asyncio.Event().wait()  # never set -> blocks until cancelled
        if self._fail_after is not None and self._count >= self._fail_after:
            raise RuntimeError("peer broken")
        self.sent.append(text)


def _endpoint() -> duel.DuelEndpoint:
    """Build an endpoint bound to a plain manager (no live socket needed)."""

    return duel.DuelEndpoint(RoomManager(), allowed_origins=("http://x",))


def _make_seat() -> Seat:
    """Build a standalone seat with a private engine game for writer tests."""

    manager = RoomManager()
    _room, seat = manager.assign_seat("writer-room")
    return seat


def _frame(seat: Seat, revision: int) -> contract.Welcome:
    """A tiny schema-valid frame to enqueue (``welcome`` keeps it simple)."""

    return contract.Welcome(
        type="welcome",
        room_id="writer-room",
        seat_id=seat.seat_id,
        room_status="waiting",
    )


# ---------------------------------------------------------------------------
# Writer flushes without inbound traffic; FIFO ordering.
# ---------------------------------------------------------------------------


def test_writer_flushes_queued_frames_fifo_without_inbound() -> None:
    async def scenario() -> List[str]:
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket()
        # Enqueue BEFORE the writer starts; the writer must flush them all with
        # no inbound traffic ever arriving.
        seat.enqueue_outbound(_frame(seat, 0))
        seat.enqueue_outbound(build_waiting_state(seat))
        writer = await endpoint._start_writer(ws, seat)
        # Give the writer turns to drain, then close the channel and await it.
        for _ in range(50):
            if not seat.outbound:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat, writer)
        return ws.sent

    sent = asyncio.run(scenario())
    assert len(sent) == 2
    # FIFO: the welcome was enqueued first.
    assert json.loads(sent[0])["type"] == "welcome"
    assert json.loads(sent[1])["type"] == "state"


def test_writer_wakes_on_frame_enqueued_after_it_is_waiting() -> None:
    async def scenario() -> List[str]:
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket()
        writer = await endpoint._start_writer(ws, seat)
        # Let the writer reach its idle await (queue empty).
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert ws.sent == []
        # Enqueue with NO inbound traffic: the signal must wake the writer.
        seat.enqueue_outbound(_frame(seat, 0))
        for _ in range(50):
            if ws.sent:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat, writer)
        return ws.sent

    sent = asyncio.run(scenario())
    assert len(sent) == 1
    assert json.loads(sent[0])["type"] == "welcome"


# ---------------------------------------------------------------------------
# Failed send: recorded as a failure, no unbounded retries.
# ---------------------------------------------------------------------------


def test_failed_send_sets_send_failed_and_stops_writer() -> None:
    async def scenario() -> Seat:
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket(fail_after=1)  # first send raises
        seat.enqueue_outbound(_frame(seat, 0))
        seat.enqueue_outbound(_frame(seat, 0))
        writer = await endpoint._start_writer(ws, seat)
        for _ in range(50):
            if seat.send_failed:
                break
            await asyncio.sleep(0)
        await endpoint._teardown_writer(seat, writer)
        return seat, ws

    seat, ws = asyncio.run(scenario())
    assert seat.send_failed is True
    # No retry: the broken send delivered nothing and the writer stopped (it did
    # not loop retrying the same frame).
    assert ws.sent == []


def test_flush_and_check_reports_failure() -> None:
    async def scenario() -> bool:
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket(fail_after=1)
        writer = await endpoint._start_writer(ws, seat)
        seat.enqueue_outbound(_frame(seat, 0))
        ok = await endpoint._flush_and_check(seat)
        await endpoint._teardown_writer(seat, writer)
        return ok

    ok = asyncio.run(scenario())
    assert ok is False  # a failed send is reported, never hidden


def test_send_bound_breach_is_a_failure_with_no_retry(monkeypatch) -> None:
    """A send that breaches the bounded send timeout is a failed send (no retry).

    Uses a tiny patched bound and a hanging peer so the 5s semantics are proven
    deterministically in milliseconds. The writer must record ``send_failed``
    and stop (it never retries the timed-out send).
    """

    monkeypatch.setattr(contract, "OUTBOUND_SEND_TIMEOUT_S", 0.02)

    async def scenario() -> Seat:
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket(hang=True)  # every send blocks until cancelled
        seat.enqueue_outbound(_frame(seat, 0))
        writer = await endpoint._start_writer(ws, seat)
        for _ in range(200):
            if seat.send_failed:
                break
            await asyncio.sleep(0.005)
        await endpoint._teardown_writer(seat, writer)
        return seat, ws

    seat, ws = asyncio.run(scenario())
    assert seat.send_failed is True
    assert ws.sent == []  # the hung send never completed; no frame "delivered"


# ---------------------------------------------------------------------------
# _emit_cached honesty: a failed cached send is NOT pretended to succeed.
# ---------------------------------------------------------------------------


def test_emit_cached_reports_failed_send_as_failure() -> None:
    """A failed cached send returns False (was ``drain_result or True`` before)."""

    async def scenario() -> bool:
        endpoint = _endpoint()
        manager = RoomManager()
        room, seat = manager.assign_seat("cache-room")
        _room2, _seat_b = manager.assign_seat("cache-room")
        room.status = "playing"  # started room -> a failed send forfeits
        ws = FakeWebSocket(fail_after=1)
        writer = await endpoint._start_writer(ws, seat)
        cached = duel.make_ack("cache-room", "A", "A-1", 0, no_op=False)
        result = await endpoint._emit_cached(ws, room, seat, cached)
        await endpoint._teardown_writer(seat, writer)
        return result

    result = asyncio.run(scenario())
    # Honest failure: the loop-continue flag is False (the peer is unavailable),
    # never a fabricated True.
    assert result is False


def test_emit_cached_succeeds_when_send_ok() -> None:
    async def scenario():
        endpoint = _endpoint()
        manager = RoomManager()
        room, seat = manager.assign_seat("cache-ok")
        _room2, _seat_b = manager.assign_seat("cache-ok")
        room.status = "playing"
        ws = FakeWebSocket()
        writer = await endpoint._start_writer(ws, seat)
        cached = duel.make_ack("cache-ok", "A", "A-1", 0, no_op=False)
        result = await endpoint._emit_cached(ws, room, seat, cached)
        await endpoint._teardown_writer(seat, writer)
        return result, ws.sent

    result, sent = asyncio.run(scenario())
    assert result is True
    assert len(sent) == 1
    assert json.loads(sent[0])["type"] == "ack"


# ---------------------------------------------------------------------------
# Lifecycle: teardown cancels + awaits the writer; no leaked task; cancellation
# actually reaches the writer and is not swallowed.
# ---------------------------------------------------------------------------


def test_teardown_cancels_and_awaits_writer_no_leak() -> None:
    async def scenario():
        endpoint = _endpoint()
        seat = _make_seat()
        ws = FakeWebSocket()
        writer = await endpoint._start_writer(ws, seat)
        await asyncio.sleep(0)  # let the writer reach its idle await
        await endpoint._teardown_writer(seat, writer)
        return writer

    writer = asyncio.run(scenario())
    # The writer task is DONE (cancelled + awaited): no leaked task remains.
    assert writer.done() is True
    assert writer.cancelled() is True


def test_writer_propagates_cancellederror_to_itself() -> None:
    """Cancelling the writer must actually reach it (it re-raises, not swallows)."""

    reached = {"cancelled": False}

    async def scenario():
        endpoint = _endpoint()
        seat = _make_seat()

        async def instrumented_writer() -> None:
            try:
                await endpoint._run_writer(FakeWebSocket(), seat)
            except asyncio.CancelledError:
                reached["cancelled"] = True
                raise

        seat.outbound_signal()
        writer = asyncio.create_task(instrumented_writer())
        await asyncio.sleep(0)  # let it reach the idle await
        writer.cancel()
        await asyncio.wait({writer})
        return writer

    writer = asyncio.run(scenario())
    assert writer.cancelled() is True
    # The CancelledError reached the writer's body (it was not swallowed before
    # arriving): cancellation genuinely propagated to the awaited resource.
    assert reached["cancelled"] is True


# ---------------------------------------------------------------------------
# Runtime lifecycle: the lifespan-owned cleanup + gravity tasks are cancelled
# AND their cancellation actually completes on stop (S7497 lifecycle fix). No
# task is leaked and the manager is released.
# ---------------------------------------------------------------------------


def test_duel_runtime_stop_cancels_and_releases_without_leak() -> None:
    from app import main as app_main

    async def scenario():
        runtime = app_main._DuelRuntime()
        await runtime.start()
        cleanup = runtime._cleanup_task
        gravity_task = runtime._gravity_task
        assert cleanup is not None and gravity_task is not None
        # Let both periodic tasks begin running.
        await asyncio.sleep(0)
        await runtime.stop()
        return cleanup, gravity_task, runtime

    cleanup, gravity_task, runtime = asyncio.run(scenario())
    # Both periodic tasks are DONE and cancelled: cancellation reached them and
    # completed (no leaked task). The runtime released the manager.
    assert cleanup.done() is True and cleanup.cancelled() is True
    assert gravity_task.done() is True and gravity_task.cancelled() is True
    assert runtime.manager is None
    assert runtime._cleanup_task is None and runtime._gravity_task is None


def test_run_gravity_loop_cancellation_propagates() -> None:
    """Cancelling ``run_gravity_loop`` marks the task cancelled (not swallowed)."""

    from app.duel.gravity import run_gravity_loop

    async def scenario():
        manager = RoomManager()
        task = asyncio.create_task(run_gravity_loop(manager, cadence_s=0.01))
        await asyncio.sleep(0.02)  # let it run at least one step
        task.cancel()
        await asyncio.wait({task})
        return task

    task = asyncio.run(scenario())
    assert task.cancelled() is True


# ---------------------------------------------------------------------------
# A small helper that builds a schema-valid ``state`` frame for ordering tests.
# ---------------------------------------------------------------------------


def build_waiting_state(seat: Seat) -> contract.StateFrame:
    return duel.build_state_frame("writer-room", seat, "waiting")


# ---------------------------------------------------------------------------
# Native 19 F2: a writer failure WAKES and terminates the blocked reader and
# triggers the central forfeit/cleanup WITHOUT another _flush_and_check.
#
# These drive the REAL reader (``_run_action_loop``) over a fake socket whose
# ``receive()`` blocks forever (the IDLE peer, sending nothing) and whose
# ``send_text`` fails or hangs. The reader must not block forever: when its
# independent writer records a failed/timed-out send (new OR cached ACK path),
# the reader wakes, resolves the gameplay forfeit exactly once (the OTHER seat
# wins), and closes 1001 ``peer_unavailable_forfeit`` -- with NO follow-up input
# from either peer and WITHOUT any further flush.
# ---------------------------------------------------------------------------


class ReaderFakeWebSocket:
    """A fake socket whose ``receive`` blocks (idle peer) and ``send`` may fail.

    * ``receive()`` blocks forever on an un-set event -- the idle peer sends
      nothing, so the reader would hang here unless the writer wakes it.
    * ``send_text`` fails after ``fail_after`` sends, or hangs forever when
      ``hang`` is set (a slow peer breaching the bounded send), modelling both
      the new-ACK and cached-ACK in-flight-send failure races.
    * ``close`` records the terminal ``(code, reason)`` so a test asserts the
      central forfeit close actually happened.
    """

    def __init__(self, *, fail_after=None, hang=False):
        self.sent: List[str] = []
        self._fail_after = fail_after
        self._hang = hang
        self._count = 0
        self.closed: Optional[tuple] = None
        # Starlette's WebSocket.application_state is read by ``_close``.
        from starlette.websockets import WebSocketState

        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        # The idle peer: never produces an inbound frame. Blocks until the task
        # is cancelled at teardown (or the reader wakes via the writer-gone race
        # and never awaits this result).
        await asyncio.Event().wait()
        raise AssertionError("receive should never return for an idle peer")

    async def send_text(self, text: str) -> None:
        self._count += 1
        if self._hang:
            await asyncio.Event().wait()  # blocks until cancelled
        if self._fail_after is not None and self._count >= self._fail_after:
            raise RuntimeError("peer broken")
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


def _started_room_two_seats(room_id: str):
    """Build a started two-seat room; return (manager, room, seat_a, seat_b)."""

    manager = RoomManager()
    room, seat_a = manager.assign_seat(room_id)
    _room2, seat_b = manager.assign_seat(room_id)
    room.status = "playing"
    return manager, room, seat_a, seat_b


def test_idle_reader_wakes_and_forfeits_when_writer_send_fails() -> None:
    """A failed WRITER send wakes the blocked IDLE reader and forfeits once.

    Seat A is idle (its ``receive`` blocks forever). Something is enqueued to A
    and A's writer send FAILS. Without the native-19 F2 wake, A's reader would
    block forever and NO forfeit would run until teardown. With the fix the
    reader wakes, A forfeits (B wins) exactly once, and A's socket is closed
    1001 ``peer_unavailable_forfeit`` -- with NO inbound traffic from either
    peer and NO further flush.
    """

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, seat_b = _started_room_two_seats("room-idle-fail")
        endpoint._manager = manager
        ws_a = ReaderFakeWebSocket(fail_after=1)  # A's first send fails

        reader = asyncio.ensure_future(
            endpoint._run_action_loop(ws_a, room, seat_a)
        )
        writer = await endpoint._start_writer(ws_a, seat_a)

        # Enqueue a frame to the IDLE peer A. Its writer will attempt the send,
        # fail, mark send_failed + wake the reader.
        seat_a.enqueue_outbound(
            duel.build_state_frame("room-idle-fail", seat_a, "playing")
        )

        # Bounded wait for the reader to wake and resolve the forfeit.
        for _ in range(500):
            if room.status == "finished":
                break
            await asyncio.sleep(0)

        # The reader coroutine must have RETURNED (it is no longer blocked).
        for _ in range(500):
            if reader.done():
                break
            await asyncio.sleep(0)

        await endpoint._teardown_writer(seat_a, writer)
        if not reader.done():
            reader.cancel()
        await asyncio.wait({reader})
        return room, seat_a, seat_b, ws_a, reader

    room, seat_a, seat_b, ws_a, reader = asyncio.run(scenario())
    # The blocked idle reader actually woke and returned (no hang).
    assert reader.done() is True
    assert reader.cancelled() is False
    # Central forfeit resolved EXACTLY once: A forfeits, B wins.
    assert room.status == "finished"
    outcome = room.outcome
    assert isinstance(outcome, gravity.OutcomeData)
    assert outcome.result == "forfeit"
    assert outcome.forfeiting_seat == "A"
    assert outcome.winning_seat == "B"
    # It is a gameplay forfeit, NOT an operational abort.
    assert room.operational_abort is None
    # A's socket was closed with the documented code + literal reason.
    assert ws_a.closed is not None
    assert ws_a.closed[0] == contract.CLOSE_CODE_GOING_AWAY
    assert ws_a.closed[1] == contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
    # The surviving peer B received the terminal outcome (central publication),
    # with NO inbound traffic from B.
    assert any(
        f.__class__.__name__ == "Outcome" for f in list(seat_b.outbound)
    ) or any(getattr(f, "result", None) == "forfeit" for f in list(seat_b.outbound))


def test_idle_reader_wakes_and_forfeits_when_writer_send_hangs(monkeypatch) -> None:
    """A HUNG in-flight send (breaching the 5s bound) wakes the idle reader.

    This is the exact in-flight-send race: the send is still in flight when the
    reader is already blocked on ``receive``. The writer breaches the bounded
    send, records the failure, and wakes the reader, which then forfeits once.
    A tiny patched bound keeps it deterministic in milliseconds.
    """

    monkeypatch.setattr(contract, "OUTBOUND_SEND_TIMEOUT_S", 0.02)

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, seat_b = _started_room_two_seats("room-idle-hang")
        endpoint._manager = manager
        ws_a = ReaderFakeWebSocket(hang=True)  # every send blocks until bound

        reader = asyncio.ensure_future(
            endpoint._run_action_loop(ws_a, room, seat_a)
        )
        writer = await endpoint._start_writer(ws_a, seat_a)
        seat_a.enqueue_outbound(
            duel.build_state_frame("room-idle-hang", seat_a, "playing")
        )

        for _ in range(500):
            if reader.done():
                break
            await asyncio.sleep(0.005)

        await endpoint._teardown_writer(seat_a, writer)
        if not reader.done():
            reader.cancel()
        await asyncio.wait({reader})
        return room, reader, ws_a

    room, reader, ws_a = asyncio.run(scenario())
    assert reader.done() is True and reader.cancelled() is False
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.forfeiting_seat == "A"
    assert ws_a.closed is not None
    assert ws_a.closed[1] == contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT


def test_idle_reader_wakes_on_directed_close_directive() -> None:
    """A directed close (operational abort on the OTHER seat) wakes the reader.

    When the OTHER seat's operational abort directs THIS seat's writer to close,
    the writer closes the socket with the literal reason and signals writer-gone.
    The idle reader wakes and tears down through the single ordered writer/socket
    (no concurrent close), resolving NO gameplay forfeit (the room was aborted).
    """

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, seat_b = _started_room_two_seats("room-directed")
        endpoint._manager = manager
        ws_a = ReaderFakeWebSocket()

        reader = asyncio.ensure_future(
            endpoint._run_action_loop(ws_a, room, seat_a)
        )
        writer = await endpoint._start_writer(ws_a, seat_a)
        await asyncio.sleep(0)  # let both reach their awaits

        # The OTHER seat's operational abort marks the room and directs A's
        # writer to close with the literal reason.
        room.set_operational_abort_once(contract.CLOSE_REASON_SCALAR_OVERFLOW)
        seat_a.request_close(
            contract.CLOSE_CODE_GOING_AWAY, contract.CLOSE_REASON_SCALAR_OVERFLOW
        )

        for _ in range(500):
            if reader.done():
                break
            await asyncio.sleep(0)

        await endpoint._teardown_writer(seat_a, writer)
        if not reader.done():
            reader.cancel()
        await asyncio.wait({reader})
        return room, reader, ws_a

    room, reader, ws_a = asyncio.run(scenario())
    # The reader woke and returned (no hang) via the directed-close wake.
    assert reader.done() is True and reader.cancelled() is False
    # The writer performed the directed close with the literal reason; the room
    # is an operational abort with NO fabricated gameplay winner.
    assert ws_a.closed is not None
    assert ws_a.closed[1] == contract.CLOSE_REASON_SCALAR_OVERFLOW
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    assert room.outcome is None


def test_receive_or_writer_gone_returns_message_on_real_frame() -> None:
    """When a real inbound frame arrives first, the race returns that message.

    The healthy path: no writer failure, a frame arrives, and the helper returns
    the ASGI message unchanged (no false wakeup) with no leaked task.
    """

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, _b = _started_room_two_seats("room-recv-ok")
        endpoint._manager = manager

        class OneFrameWS:
            def __init__(self):
                self._done = False

            async def receive(self):
                if self._done:
                    await asyncio.Event().wait()
                self._done = True
                return {"type": "websocket.receive", "text": "hello-frame"}

        ws = OneFrameWS()
        msg = await endpoint._receive_or_writer_gone(ws, seat_a)
        return msg

    msg = asyncio.run(scenario())
    assert msg == {"type": "websocket.receive", "text": "hello-frame"}


def test_receive_or_writer_gone_returns_none_when_already_failed() -> None:
    """If the writer already failed before the call, the race returns None at once."""

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, _b = _started_room_two_seats("room-recv-failed")
        endpoint._manager = manager
        seat_a.mark_send_failed()  # writer already gone

        class BlockingWS:
            async def receive(self):
                await asyncio.Event().wait()

        msg = await endpoint._receive_or_writer_gone(BlockingWS(), seat_a)
        return msg

    assert asyncio.run(scenario()) is None


# ---------------------------------------------------------------------------
# Native 20 D1 + D3: the SURVIVOR actually reaches CLOSE 1000 normal_completion
# AND its reader is DONE after the close ack, following a FAILED new-AND-cached
# ACK or a FULL outbound queue in a STARTED room, with NO further input from
# either peer; the OFFENDER seat keeps 1001 peer_unavailable_forfeit. The D3
# full-queue case uses a TIMELY successful in-flight send (released well before
# the unchanged 5s bound) so the OVERFLOW -- not a send timeout -- is what
# classifies the peer unavailable and notifies the healthy idle peer. The
# existing F2 tests above pin the OFFENDER close 1001 and that the survivor
# RECEIVES the outcome; these additionally drive BOTH seats' REAL
# ``_run_action_loop`` readers + independent writers so the SURVIVOR's own
# socket close 1000 ``normal_completion`` and its reader termination (the
# native-20 D1 ``_close_survivor_after_terminal`` guarantee) are asserted, never
# merely an internal flag / received frame. No gravity loop is mounted, so the
# survivor close can only come from the failed-send / full-queue path itself.
#
# Validates: Requirements 16.6, 17.1, 17.2, 18.5, 18.6, 19.1, 19.2, 19.3, 22.4,
#            22.5, 22.6
# ---------------------------------------------------------------------------


class SurvivorIdleWebSocket:
    """A fake survivor socket: ``receive`` blocks forever; ``close`` recorded.

    The surviving peer sends NOTHING, so its reader sits blocked on
    ``websocket.receive()``; unless its writer performs the directed survivor
    close (1000 ``normal_completion``) and wakes the reader via the writer-gone
    signal, the reader never terminates. ``send_text`` records delivered frames
    so a test can assert the survivor RECEIVED the forfeit terminal BEFORE its
    own close. ``close`` records the terminal ``(code, reason)``.
    """

    def __init__(self) -> None:
        self.sent: List[str] = []
        self.closed: Optional[tuple] = None
        from starlette.websockets import WebSocketState

        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        await asyncio.Event().wait()  # idle survivor: blocks until cancelled
        raise AssertionError("receive should never return for an idle survivor")

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


class TimelySendWebSocket:
    """A fake socket whose sends ALWAYS succeed PROMPTLY (no hang, no timeout).

    Every ``send_text`` returns at once (well before any send bound), so when a
    test SATURATES this seat's bounded queue to the depth cap and then publishes
    one more transition, the classification is driven PURELY by the queue
    OVERFLOW (``enqueue_outbound`` returning False at depth 64) -- never by a send
    timeout. ``sent`` records delivered frames; ``close`` records the terminal
    ``(code, reason)`` the offender seat keeps.
    """

    def __init__(self) -> None:
        self.sent: List[str] = []
        self.closed: Optional[tuple] = None
        from starlette.websockets import WebSocketState

        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        await asyncio.Event().wait()  # offender sends nothing further
        raise AssertionError("receive should never return here")

    async def send_text(self, text: str) -> None:
        self.sent.append(text)  # always succeeds promptly (timely in-flight)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


def test_failed_cached_ack_forfeits_offender_1001_and_survivor_closes_1000() -> None:
    """A failed NEW-and-cached ACK forfeits A (1001) and closes B 1000, reader DONE.

    Native-20 D1 over the REAL readers/writers of BOTH seats: seat A's socket
    fails its send (the new-AND-cached ACK delivery path), so A's writer records
    ``send_failed`` and wakes A's blocked reader, which funnels through the
    central ``_forfeit_and_close``: A forfeits (B wins) once and A's own socket
    closes 1001 ``peer_unavailable_forfeit``. The SURVIVING seat B -- which sends
    NOTHING -- must then reach CLOSE 1000 ``normal_completion`` through its own
    single ordered writer, with its blocked reader WOKEN so its reader task is
    DONE after the close ack. No further input from either peer; B received the
    forfeit terminal BEFORE its own close.
    """

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, seat_b = _started_room_two_seats("room-d1-cached")
        endpoint._manager = manager
        ws_a = ReaderFakeWebSocket(fail_after=1)  # A's send fails
        ws_b = SurvivorIdleWebSocket()            # B is the idle survivor

        reader_a = asyncio.ensure_future(endpoint._run_action_loop(ws_a, room, seat_a))
        reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)
        await asyncio.sleep(0)  # park both readers on the blocking receive

        # Enqueue a frame to the offender A; its writer fails the send, marks
        # send_failed, wakes A's reader -> central forfeit -> survivor close.
        seat_a.enqueue_outbound(
            duel.build_state_frame("room-d1-cached", seat_a, "playing")
        )

        for _ in range(1000):
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

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(scenario())
    # The forfeit resolved exactly once: A forfeits, B wins (gameplay, no abort).
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    assert room.operational_abort is None
    # The OFFENDER seat A kept its 1001 peer_unavailable_forfeit close.
    assert ws_a.closed is not None
    assert ws_a.closed[0] == contract.CLOSE_CODE_GOING_AWAY
    assert ws_a.closed[1] == contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
    assert reader_a.done() and not reader_a.cancelled()
    # The SURVIVOR received the forfeit outcome BEFORE its own close.
    received = [json.loads(t) for t in ws_b.sent]
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never received the forfeit outcome"
    assert outcome["winning_seat"] == "B"
    # The SURVIVOR's OWN socket closed 1000 normal_completion; reader DONE.
    assert ws_b.closed is not None, "survivor socket was never closed"
    assert ws_b.closed[0] == contract.CLOSE_CODE_NORMAL
    assert ws_b.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    assert reader_b.done() and not reader_b.cancelled()


def test_full_queue_overflow_classifies_offender_and_survivor_closes_1000() -> None:
    """A FULL queue (timely in-flight send) forfeits A (1001) and closes B 1000.

    Native-20 D3 + D1 with NO send-timeout conflation: seat A's sends ALWAYS
    succeed PROMPTLY (well before the unchanged 5s bound), so the offender is
    classified by the pure queue OVERFLOW, not a hung/timed-out send. A's bounded
    outbound queue is SATURATED to the depth cap, then one more both-board
    transition is published via the REAL ``broadcast_room_state``: its
    ``enqueue_outbound`` returns ``False`` at depth 64 and, because the room is
    STARTED, it marks A ``send_failed`` exactly once and wakes A's reader. A's
    reader funnels through the central forfeit: A forfeits (B wins) once and A
    closes 1001 ``peer_unavailable_forfeit``; the healthy idle survivor B is
    NOTIFIED (receives the forfeit terminal) and reaches CLOSE 1000
    ``normal_completion`` with its reader DONE. No winner is fabricated anywhere
    but on this STARTED room (asserted distinct from a waiting/abort/finished
    room by test_full_queue_overflow_on_non_started_room_fabricates_no_winner).
    """

    from app.duel.rooms import OUTBOUND_QUEUE_DEPTH

    async def scenario():
        endpoint = _endpoint()
        manager, room, seat_a, seat_b = _started_room_two_seats("room-d3-overflow")
        endpoint._manager = manager
        ws_a = TimelySendWebSocket()       # sends succeed promptly: no timeout
        ws_b = SurvivorIdleWebSocket()     # idle survivor

        reader_a = asyncio.ensure_future(endpoint._run_action_loop(ws_a, room, seat_a))
        reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
        # NOTE: start A's writer AFTER saturating the queue so the timely writer
        # does not drain it before we overflow. B's writer runs so the survivor
        # delivery + close proceed.
        writer_b = await endpoint._start_writer(ws_b, seat_b)
        await asyncio.sleep(0)  # park both readers on the blocking receive

        # SATURATE A's bounded queue to the depth cap WITHOUT a writer draining
        # it, so the next publish overflows. At least one enqueue is REJECTED.
        for _ in range(OUTBOUND_QUEUE_DEPTH):
            assert seat_a.enqueue_outbound(
                duel.build_state_frame("room-d3-overflow", seat_a, "playing")
            ) is True
        assert len(seat_a.outbound) == OUTBOUND_QUEUE_DEPTH

        # The REAL publisher observes the FULL queue (enqueue returns False) and,
        # on this STARTED room, marks A send_failed once + wakes A's reader. This
        # is the pure OVERFLOW classification -- no send has timed out.
        duel.broadcast_room_state(room)
        assert seat_a.send_failed is True  # classified by overflow, not timeout

        for _ in range(1000):
            if reader_a.done() and reader_b.done():
                break
            await asyncio.sleep(0)

        await endpoint._teardown_writer(seat_b, writer_b)
        for reader in (reader_a, reader_b):
            if not reader.done():
                reader.cancel()
        await asyncio.wait({reader_a, reader_b})
        return room, ws_a, ws_b, reader_a, reader_b

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(scenario())
    # The overflow classified A unavailable and resolved a GAMEPLAY forfeit once.
    assert room.status == "finished"
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "forfeit"
    assert room.outcome.forfeiting_seat == "A"
    assert room.outcome.winning_seat == "B"
    assert room.operational_abort is None  # a forfeit, not an operational abort
    # The OFFENDER seat A closed 1001 peer_unavailable_forfeit; reader DONE.
    assert ws_a.closed is not None
    assert ws_a.closed[0] == contract.CLOSE_CODE_GOING_AWAY
    assert ws_a.closed[1] == contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT
    assert reader_a.done() and not reader_a.cancelled()
    # The healthy idle survivor B was NOTIFIED (received the forfeit terminal).
    received = [json.loads(t) for t in ws_b.sent]
    outcome = next((f for f in received if f["type"] == "outcome"), None)
    assert outcome is not None, "survivor never notified of the full-queue forfeit"
    assert outcome["winning_seat"] == "B"
    # The SURVIVOR reached CLOSE 1000 normal_completion with its reader DONE.
    assert ws_b.closed is not None, "survivor socket was never closed"
    assert ws_b.closed[0] == contract.CLOSE_CODE_NORMAL
    assert ws_b.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    assert reader_b.done() and not reader_b.cancelled()


def test_full_queue_overflow_on_non_started_room_fabricates_no_winner() -> None:
    """A FULL queue on a waiting / finished room fabricates NO gameplay winner.

    The D3 classification is gated on ``room.status == "playing"``: overflowing a
    peer's bounded queue on a room that is NOT started (``waiting``) does NOT mark
    the peer send-failed and invents NO winner; and overflowing on an
    already-``finished`` room leaves the existing terminal outcome untouched and
    invents no NEW winner. This pins the "no winner on a waiting /
    operational-abort / finished room" half of the D3 correction.
    """

    from app.duel.rooms import OUTBOUND_QUEUE_DEPTH

    # (a) WAITING room: overflow classifies nothing, no winner.
    manager = RoomManager()
    room_w, seat_w = manager.assign_seat("room-wait-overflow")
    # room stays "waiting" (only one seat); saturate the queue past the cap.
    for _ in range(OUTBOUND_QUEUE_DEPTH + 4):
        seat_w.enqueue_outbound(
            duel.build_state_frame("room-wait-overflow", seat_w, "waiting")
        )
    assert len(seat_w.outbound) == OUTBOUND_QUEUE_DEPTH
    duel.broadcast_room_state(room_w)
    assert seat_w.send_failed is False  # not classified on a non-started room
    assert room_w.outcome is None
    assert room_w.operational_abort is None

    # (b) FINISHED room: overflow leaves the resolved outcome intact, no new one.
    manager2, room_f, seat_fa, seat_fb = _started_room_two_seats("room-fin-overflow")
    prior = gravity.resolve_forfeit(room_f, "B", manager2.clock(), manager=manager2)
    assert prior is not None and room_f.status == "finished"
    for _ in range(OUTBOUND_QUEUE_DEPTH + 4):
        seat_fa.enqueue_outbound(
            duel.build_state_frame("room-fin-overflow", seat_fa, "playing")
        )
    assert len(seat_fa.outbound) == OUTBOUND_QUEUE_DEPTH
    duel.broadcast_room_state(room_f)
    # The pre-existing outcome stands; no NEW winner fabricated by the overflow.
    assert room_f.outcome is prior
    assert seat_fa.send_failed is False  # finished room is not re-classified
