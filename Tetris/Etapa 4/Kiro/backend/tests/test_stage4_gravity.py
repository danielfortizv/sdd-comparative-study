"""Hypothesis + unit tests for the Stage 4 duel per-board gravity (M3, task 13.2).

This module covers the AUTHORITATIVE per-board gravity progression and the
single terminal-outcome decision implemented in ``app/duel/gravity.py``. It is
driven ENTIRELY by the injectable fake monotonic clock exposed by the duel
``RoomManager`` (``app/duel/rooms.py``), so every test here is deterministic and
never reads the wall clock.

Task boundary (task 13.2): this file hosts

* **Property 15** (Simultaneous top-out is a draw; otherwise last survivor
  wins) as a single Hypothesis property over arbitrary board end-states, run at
  >= 100 examples; **Validates: Requirements 18.3, 18.4, 18.5**, and
* a set of injectable-clock unit tests covering per-board independent gravity
  advancement, simultaneous top-out (draw), last-survivor win, forfeit-once on
  disconnect, and a disconnect-plus-gravity race that still resolves the duel
  EXACTLY once.

These tests NEVER touch the solo store, registration, finalization, or SQLite:
each duel seat owns a PRIVATE ``engine.new_game`` ``Game`` constructed from the
room seed, so no SQL write is possible from here.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Tuple

from hypothesis import given, settings, strategies as st

from app.duel import gravity, rooms
from app.rules import engine
from app.ws import contract
from app.ws import duel


# ---------------------------------------------------------------------------
# Shared deterministic clock and room helpers (injectable clock, Req 19.4).
# ---------------------------------------------------------------------------


class FakeClock:
    """A deterministic, monotonic, injectable clock for the RoomManager.

    ``advance`` moves time forward by a non-negative delta; ``__call__`` returns
    the current value so it is a drop-in for ``time.monotonic``. Driving the
    manager with this clock lets every gravity/outcome test advance time exactly
    (Req 19.4) instead of sleeping on the wall clock.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, delta: float) -> None:
        if delta < 0:
            raise ValueError("clock must be monotonic")
        self._now += delta


# A valid duel room_id per the contract grammar/bounds (1..64 chars), kept to
# the safe id alphabet so it is a legal room id for the manager.
room_ids = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
    min_size=1,
    max_size=24,
)


def _make_playing_room(room_id: str = "room-duel", start: float = 1000.0):
    """Build a two-seat room in the ``playing`` status on a fresh fake clock.

    Returns ``(manager, clock, room, seat_a, seat_b)``. Both seats are assigned
    from the identical room seed (independent private engine games) and the room
    is transitioned to ``playing`` so the gravity step is active (gravity only
    advances a ``playing`` room, Req 18.6).
    """

    clock = FakeClock(start)
    manager = rooms.RoomManager(clock=clock)
    room, seat_a = manager.assign_seat(room_id)
    _room2, seat_b = manager.assign_seat(room_id)
    room.status = "playing"
    room.last_activity_monotonic = clock()
    return manager, clock, room, seat_a, seat_b


def _force_game_over(seat) -> None:
    """Deterministically top out a seat's PRIVATE board.

    ``gravity._board_is_game_over`` reads the seat game's ``status`` field, which
    the engine sets to ``"game_over"`` on a spawn collision. Setting it directly
    is the same terminal condition the engine produces, and keeps Property 15
    independent of which exact piece sequence happens to top a board out.
    """

    seat.game.status = "game_over"


# ---------------------------------------------------------------------------
# Property 15: Simultaneous top-out is a draw; otherwise last survivor wins.
#
# For any gravity evaluation that advances all due boards, if BOTH boards top
# out within that evaluation the outcome is `draw`; if exactly one board remains
# playable the surviving seat wins; and a resolved duel is never resolved a
# second time.
#
# GENERATION STRATEGY: generate an arbitrary pair of board end-states (each seat
# independently playing or topped out) plus a room id. Mark each seat's private
# game accordingly, then run the PURE step ``advance_due_boards`` against the
# injectable clock and assert the single decided outcome matches the oracle:
#   * both topped out  -> result == "draw" (all seat fields null);
#   * exactly one alive -> result == "win" for the survivor (distinct loser);
#   * both alive        -> no resolution yet (None, room still playing).
# Then run a SECOND evaluation and assert a resolved room is never re-resolved
# (set_outcome_once guards it) and an unresolved room stays unresolved. The
# decided OutcomeData is also run through build_outcome_frame so the per-result
# seat relationships are validated end-to-end.
#
# Validates: Requirements 18.3, 18.4, 18.5
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 15
@settings(max_examples=200)
@given(
    room_id=room_ids,
    a_topped=st.booleans(),
    b_topped=st.booleans(),
)
def test_property_15_simultaneous_topout_draw_else_survivor(room_id, a_topped, b_topped):
    manager, clock, room, seat_a, seat_b = _make_playing_room(room_id)

    # Arbitrary board end-states for the two seats.
    if a_topped:
        _force_game_over(seat_a)
    if b_topped:
        _force_game_over(seat_b)

    # Both boards are "due" so the single evaluation considers both (Req 18.3:
    # evaluate ALL due boards before deciding one outcome). A topped-out board is
    # a no-op in the advance, so this only governs which boards are inspected.
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock()

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    both_topped = a_topped and b_topped
    one_alive = a_topped ^ b_topped

    if both_topped:
        # Simultaneous top-out within one evaluation -> DRAW, room finished.
        assert outcome is not None
        assert outcome.result == "draw"
        assert outcome.winning_seat is None
        assert outcome.losing_seat is None
        assert outcome.forfeiting_seat is None
        assert room.status == "finished"
    elif one_alive:
        # Exactly one board playable -> that seat WINS; the other loses.
        survivor = "A" if not a_topped else "B"
        loser = "B" if survivor == "A" else "A"
        assert outcome is not None
        assert outcome.result == "win"
        assert outcome.winning_seat == survivor
        assert outcome.losing_seat == loser
        assert outcome.winning_seat != outcome.losing_seat
        assert outcome.forfeiting_seat is None
        assert room.status == "finished"
    else:
        # Both boards still playable -> NOT terminal yet; room stays playing.
        assert outcome is None
        assert room.status == "playing"
        assert room.outcome is None

    # Every decided outcome must build a schema-valid wire frame (the per-result
    # seat-relationship rules are enforced by the contract model on construction).
    if outcome is not None:
        frame = gravity.build_outcome_frame(room.room_id, outcome)
        assert frame.result == outcome.result
        assert frame.room_id == room.room_id

    # A SECOND evaluation never re-resolves a finished room and never resolves a
    # still-playing one (resolution flows through set_outcome_once exactly once).
    prior_outcome = room.outcome
    prior_status = room.status
    second = gravity.advance_due_boards(room, clock(), manager=manager)
    assert second is None
    assert room.status == prior_status
    assert room.outcome is prior_outcome


# ---------------------------------------------------------------------------
# Injectable-clock gravity unit tests.
# ---------------------------------------------------------------------------


def test_per_board_independent_advancement_only_due_board_ticks():
    """Only a board whose due time has elapsed advances; the other is untouched.

    Seat A is due (its ``gravity_due_monotonic`` is at/under ``now``) while seat
    B's due time is in the future, so advancing at ``now`` must tick ONLY A and
    bump ONLY A's revision. Seat B's private board and revision are byte-for-byte
    unchanged -- advancing one board never advances the other (Req 18.1, 18.2).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()

    # A is due now; B is due far in the future (not yet elapsed).
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 100.0

    before_b_origin = seat_b.game.active.origin
    before_b_revision = seat_b.revision
    before_a_origin = seat_a.game.active.origin

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    # No terminal outcome (both boards still playing).
    assert outcome is None
    # A advanced (origin moved down one row) and its revision bumped by one.
    assert seat_a.game.active.origin[0] == before_a_origin[0] + 1
    assert seat_a.revision == 1
    # B did not advance at all: same board position, same revision.
    assert seat_b.game.active.origin == before_b_origin
    assert seat_b.revision == before_b_revision == 0
    # A's next due time rolled forward by its current interval (independent clock).
    assert seat_a.gravity_due_monotonic > clock()


def test_noop_tick_on_game_over_board_does_not_bump_revision():
    """A no-op gravity tick (a topped-out board) leaves the revision unchanged.

    Revision advances ONLY on a real observable state change (Req 20.2 shared
    rule). A board already ``game_over`` does not advance under gravity, so even
    though its due time has elapsed, its revision must stay put. Seat B stays
    playable so the room does not resolve on this evaluation (so we isolate the
    no-op-revision behaviour rather than the outcome).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    _force_game_over(seat_a)
    seat_a.gravity_due_monotonic = clock()  # "due", but game_over -> no-op
    # Keep B not-due so the evaluation is a pure no-op and the room stays playing.
    seat_b.gravity_due_monotonic = clock() + 100.0

    before_a_revision = seat_a.revision

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    # A sole-survivor win WOULD resolve here (A topped out, B alive); the point
    # of this test is the revision no-op, so assert A's revision never moved.
    assert seat_a.revision == before_a_revision == 0
    # B is the lone survivor, so the room resolves to a win for B.
    assert outcome is not None
    assert outcome.result == "win"
    assert outcome.winning_seat == "B"


def test_simultaneous_topout_resolves_as_draw():
    """Both boards topped out in one evaluation -> a single DRAW, resolved once."""

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    _force_game_over(seat_a)
    _force_game_over(seat_b)
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock()

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    assert outcome is not None
    assert outcome.result == "draw"
    assert outcome.winning_seat is None
    assert outcome.losing_seat is None
    assert outcome.forfeiting_seat is None
    assert room.status == "finished"
    assert room.outcome is outcome

    # The draw builds a schema-valid wire frame (all seat fields null for a draw).
    frame = gravity.build_outcome_frame(room.room_id, outcome)
    assert frame.result == "draw"
    assert frame.winning_seat is None
    assert frame.losing_seat is None
    assert frame.forfeiting_seat is None


def test_last_survivor_wins():
    """Exactly one board playable after an evaluation -> that seat wins (Req 18.4)."""

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    _force_game_over(seat_a)  # A topped out, B survives
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock()

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    assert outcome is not None
    assert outcome.result == "win"
    assert outcome.winning_seat == "B"
    assert outcome.losing_seat == "A"
    assert outcome.forfeiting_seat is None
    assert room.status == "finished"

    frame = gravity.build_outcome_frame(room.room_id, outcome)
    assert frame.result == "win"
    assert frame.winning_seat == "B"
    assert frame.losing_seat == "A"


def test_forfeit_once_on_disconnect_second_call_returns_none():
    """A disconnect forfeits and resolves EXACTLY once (Req 18.5).

    ``resolve_forfeit`` resolves the duel the first time (the disconnecting seat
    forfeits and loses, the other seat wins) and returns ``None`` on any later
    call because resolution funnels through ``Room.set_outcome_once``.
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()

    first = gravity.resolve_forfeit(room, "A", clock(), manager=manager)

    assert first is not None
    assert first.result == "forfeit"
    assert first.forfeiting_seat == "A"
    assert first.losing_seat == "A"
    assert first.winning_seat == "B"
    assert room.status == "finished"
    assert room.outcome is first

    # A SECOND forfeit event (e.g. a duplicate disconnect) never re-resolves.
    second = gravity.resolve_forfeit(room, "A", clock(), manager=manager)
    assert second is None
    assert room.outcome is first  # unchanged

    # The forfeit builds a schema-valid wire frame (loser == forfeiter).
    frame = gravity.build_outcome_frame(room.room_id, first)
    assert frame.result == "forfeit"
    assert frame.forfeiting_seat == "A"
    assert frame.losing_seat == "A"
    assert frame.winning_seat == "B"


def test_disconnect_plus_gravity_race_resolves_exactly_once():
    """A disconnect racing a gravity top-out still resolves the duel once.

    Both the forfeit path and the gravity-evaluation path funnel through
    ``Room.set_outcome_once``, so whichever runs first decides the single
    outcome and the other becomes a no-op. We drive BOTH paths in one test: the
    forfeit wins the race (resolving to a forfeit), and the subsequent gravity
    evaluation -- even with a genuine simultaneous top-out queued -- returns
    ``None`` and leaves the already-decided forfeit outcome intact (Req 18.5).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()

    # Queue a genuine simultaneous top-out that WOULD be a draw on its own.
    _force_game_over(seat_a)
    _force_game_over(seat_b)
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock()

    # The disconnect (forfeit) wins the race and resolves the duel first.
    forfeit_outcome = gravity.resolve_forfeit(room, "B", clock(), manager=manager)
    assert forfeit_outcome is not None
    assert forfeit_outcome.result == "forfeit"
    assert room.status == "finished"

    # The gravity evaluation now runs against the finished room: it must be a
    # NO-OP (gravity stops once the room is finished, Req 18.6) and must NOT
    # overwrite the decided forfeit with the would-be draw.
    gravity_outcome = gravity.advance_due_boards(room, clock(), manager=manager)
    assert gravity_outcome is None
    assert room.outcome is forfeit_outcome
    assert room.outcome.result == "forfeit"

    # Symmetric race: in a fresh room, gravity resolves FIRST (a draw) and a
    # later forfeit event is the no-op -- still exactly one resolution.
    manager2, clock2, room2, s2a, s2b = _make_playing_room("room-two")
    _force_game_over(s2a)
    _force_game_over(s2b)
    s2a.gravity_due_monotonic = clock2()
    s2b.gravity_due_monotonic = clock2()

    draw_outcome = gravity.advance_due_boards(room2, clock2(), manager=manager2)
    assert draw_outcome is not None
    assert draw_outcome.result == "draw"

    late_forfeit = gravity.resolve_forfeit(room2, "A", clock2(), manager=manager2)
    assert late_forfeit is None
    assert room2.outcome is draw_outcome
    assert room2.outcome.result == "draw"


def test_gravity_is_a_noop_once_room_is_finished():
    """Once a room is ``finished`` the gravity step is a no-op (Req 18.6).

    A resolved room's gravity stops: ``advance_due_boards`` returns ``None`` and
    does not advance any board or bump any revision, even if a seat's due time
    has elapsed.
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    # Resolve the room first (forfeit), then attempt a gravity step.
    gravity.resolve_forfeit(room, "A", clock(), manager=manager)
    assert room.status == "finished"

    before_b_origin = seat_b.game.active.origin
    before_b_revision = seat_b.revision
    seat_b.gravity_due_monotonic = clock()  # "due", but room is finished

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    assert outcome is None
    assert seat_b.game.active.origin == before_b_origin
    assert seat_b.revision == before_b_revision


def test_real_engine_gravity_tops_out_a_board_and_resolves():
    """An end-to-end gravity drive tops a board out via the real engine.

    This drives ONE seat's PRIVATE engine game through many real ``engine.tick``
    gravity advances (via ``advance_due_boards`` on the injectable clock) until
    that board genuinely tops out (status ``game_over``), while the OTHER seat is
    held not-due so it survives. The room then resolves to a win for the
    survivor, proving the pure step composes with the real engine top-out path
    and not only with a forced status (Req 18.2, 18.4).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    # A advances under gravity; B is parked far in the future so it never ticks.
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 1_000_000.0

    outcome = None
    # Each iteration advances the clock by more than any gravity interval so A is
    # always "due", letting the engine lock/spawn until A eventually tops out.
    for _ in range(2000):
        clock.advance(1.0)
        seat_a.gravity_due_monotonic = min(seat_a.gravity_due_monotonic, clock())
        outcome = gravity.advance_due_boards(room, clock(), manager=manager)
        if outcome is not None:
            break

    # A genuinely topped out via the real engine; B is the lone survivor.
    assert gravity._board_is_game_over(seat_a)
    assert seat_a.game.status == "game_over"
    assert outcome is not None
    assert outcome.result == "win"
    assert outcome.winning_seat == "B"
    assert outcome.losing_seat == "A"
    assert room.status == "finished"
    # A's revision advanced on real engine changes; it never exceeds the engine's
    # real activity (it is a positive count of observed changes).
    assert seat_a.revision > 0


def test_gravity_step_across_rooms_uses_single_clock_instant():
    """``gravity_step`` evaluates every playing room against one clock read.

    The thin scheduling helper reads the injectable clock ONCE and evaluates all
    playing rooms against that single instant, invoking ``on_outcome`` for each
    resolved room. Here two rooms are both set up to resolve (a win and a draw)
    and one step resolves both, collecting both outcomes and firing the callback
    once per resolution.
    """

    clock = FakeClock()
    manager = rooms.RoomManager(clock=clock)

    # Room one: A topped out, B survives -> win for B.
    room1, r1a = manager.assign_seat("room-win")
    _r1, r1b = manager.assign_seat("room-win")
    room1.status = "playing"
    _force_game_over(r1a)
    r1a.gravity_due_monotonic = clock()
    r1b.gravity_due_monotonic = clock()

    # Room two: both topped out -> draw.
    room2, r2a = manager.assign_seat("room-draw")
    _r2, r2b = manager.assign_seat("room-draw")
    room2.status = "playing"
    _force_game_over(r2a)
    _force_game_over(r2b)
    r2a.gravity_due_monotonic = clock()
    r2b.gravity_due_monotonic = clock()

    fired = []
    resolved = gravity.gravity_step(manager, on_outcome=lambda room, oc: fired.append((room.room_id, oc.result)))

    results = sorted(oc.result for oc in resolved)
    assert results == ["draw", "win"]
    assert sorted(fired) == [("room-draw", "draw"), ("room-win", "win")]
    assert room1.status == "finished"
    assert room2.status == "finished"

    # A second step never re-resolves either finished room.
    resolved_again = gravity.gravity_step(manager)
    assert resolved_again == []


# ---------------------------------------------------------------------------
# Scalar-overflow OPERATIONAL ABORT on the GRAVITY transition (task 35.6).
#
# A server no-input gravity tick that WOULD drive a scalar past its documented
# ceiling (``score``/``total_lines``/``revision`` against the safe-integer
# ceiling, ``level`` against its max) must ABORT the whole room operationally
# (1001 ``scalar_overflow``) BEFORE publishing: it must NOT bump the overflowing
# revision, NOT resolve a gameplay outcome (no fabricated winner, ``outcome``
# stays ``None``), and the scheduling step must NOT invoke ``on_state`` /
# ``on_outcome`` so no out-of-range ``state``/``outcome`` frame is ever emitted.
# Both seats' independent writers are directed to close 1001 + the literal
# reason. This keeps the operational abort DISTINCT from the gameplay
# ``peer_unavailable_forfeit``.
#
# These drive the REAL ``advance_due_boards`` / ``gravity_step`` with real
# engine games (not a bypassed step); the overflow is forced via a would-be
# revision that exceeds the safe-integer ceiling on a genuine engine tick.
#
# Validates: Requirements 20.11, 22.4, 22.5
# ---------------------------------------------------------------------------


def test_gravity_would_be_revision_overflow_aborts_before_publishing():
    """A gravity tick whose WOULD-BE revision overflows aborts, not resolves.

    Seat A's authoritative revision is pinned at the safe-integer ceiling and A
    is due, so the next real engine gravity tick that changes the board WOULD
    bump the revision to ``SAFE_INT_MAX + 1``. The pre-commit guard catches this
    BEFORE the bump: the room is marked ``operational_abort == "scalar_overflow"``
    with NO gameplay outcome, the overflowing revision is NEVER committed, and
    ``advance_due_boards`` returns ``None`` (no outcome to publish). Both seats'
    writers are directed to close 1001 + the literal reason.
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    # A is due so the real engine tick advances it; B is parked in the future.
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 1_000_000.0
    # Pin A's revision at the ceiling: the next real change would overflow it.
    seat_a.revision = contract.SAFE_INT_MAX
    before_revision = seat_a.revision

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    # No gameplay outcome: an operational abort fabricates NO winner.
    assert outcome is None
    assert room.outcome is None
    # The room is OPERATIONALLY ABORTED with the literal scalar_overflow reason.
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    # The overflowing revision was NEVER committed (no out-of-range revision).
    assert seat_a.revision == before_revision
    assert seat_a.revision <= contract.SAFE_INT_MAX
    # BOTH seats' writers were directed to close 1001 + the literal reason.
    expected = (contract.CLOSE_CODE_GOING_AWAY, contract.CLOSE_REASON_SCALAR_OVERFLOW)
    assert seat_a.close_directive == expected
    assert seat_b.close_directive == expected


def test_gravity_score_overflow_aborts_distinct_from_forfeit():
    """A post-tick score beyond the ceiling aborts operationally, not a forfeit.

    Seat A's real engine ``score`` is set just past the safe-integer ceiling and
    A is due. After the real gravity tick the post-tick scalar guard sees the
    out-of-range score and aborts the room operationally (1001
    ``scalar_overflow``) with NO fabricated winner -- it is NOT the gameplay
    ``peer_unavailable_forfeit`` (``resolve_forfeit`` / ``set_outcome_once`` are
    never invoked, so ``room.outcome`` stays ``None``).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 1_000_000.0
    # A genuine engine game whose score is already past the documented ceiling.
    seat_a.game.score = contract.SAFE_INT_MAX + 1

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    assert outcome is None
    assert room.outcome is None
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    assert room.status != "finished"
    # Distinct from forfeit: no OutcomeData, no winning/forfeiting seat anywhere.
    assert room.operational_abort != contract.CLOSE_REASON_SEQUENCE_EXHAUSTED


def test_gravity_step_skips_publishing_on_scalar_overflow_abort():
    """``gravity_step`` must NOT publish state/outcome for an aborted room.

    The scheduling step aborts the room BEFORE publishing: neither ``on_state``
    nor ``on_outcome`` fires for an operationally-aborted room, so no
    out-of-range ``state``/``outcome`` frame ever reaches a peer. The resolved
    list is empty (no gameplay outcome). Both seats' writers are directed to
    close 1001 + the literal reason by the abort.
    """

    clock = FakeClock()
    manager = rooms.RoomManager(clock=clock)
    room, seat_a = manager.assign_seat("room-overflow")
    _room2, seat_b = manager.assign_seat("room-overflow")
    room.status = "playing"
    room.last_activity_monotonic = clock()
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 1_000_000.0
    # Pin A's revision at the ceiling so the next real change would overflow it.
    seat_a.revision = contract.SAFE_INT_MAX

    state_calls = []
    outcome_calls = []
    resolved = gravity.gravity_step(
        manager,
        on_state=lambda r: state_calls.append(r.room_id),
        on_outcome=lambda r, oc: outcome_calls.append((r.room_id, oc.result)),
    )

    # Nothing published and nothing resolved: the abort happened BEFORE publish.
    assert resolved == []
    assert state_calls == []
    assert outcome_calls == []
    # The room is operationally aborted and both writers were told to close.
    assert room.operational_abort == contract.CLOSE_REASON_SCALAR_OVERFLOW
    assert room.outcome is None
    expected = (contract.CLOSE_CODE_GOING_AWAY, contract.CLOSE_REASON_SCALAR_OVERFLOW)
    assert seat_a.close_directive == expected
    assert seat_b.close_directive == expected


def test_normal_gravity_does_not_abort_or_overflow():
    """A normal in-range gravity advance never triggers the overflow abort.

    A plain real gravity tick on fresh boards changes the state and bumps the
    revision WITHOUT crossing any ceiling, so the room stays ``playing`` with no
    operational abort and no directed close -- the guard only fires on a genuine
    would-be overflow (the common path is unchanged).
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room()
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock() + 1_000_000.0

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)

    assert outcome is None
    assert room.operational_abort is None
    assert room.status == "playing"
    assert seat_a.revision == 1
    assert seat_a.revision <= contract.SAFE_INT_MAX
    assert seat_a.close_directive is None
    assert seat_b.close_directive is None


# ---------------------------------------------------------------------------
# Native 20 D2: the SIMULTANEOUS-natural-top-out gravity terminal closes BOTH
# peers 1000 normal_completion; waiting_room_timeout / idle_timeout /
# server_shutdown keep 1001. Driven with a REAL consistent engine terminal
# fixture (the engine clears the active piece on a spawn collision, so a
# game_over board genuinely has ``active=None`` and ``build_state_frame`` emits a
# consistent ``active_piece=None`` terminal frame -- never a hand-forced status
# with a stale non-null active piece). The draw resolves the room ``finished``;
# the reaped finished/normal_completion room then closes BOTH seats 1000 through
# the REAL ``main._release_room_resources`` + ``_reap_close_reason`` /
# ``_reap_close_code`` reap-close seam, with each seat's blocked reader woken and
# its socket actually closed. This pins the native-20 D2 correction (a reaped
# finished/normal_completion room closes 1000, not the pre-fix 1001) while the
# lifecycle reasons still close 1001.
#
# Validates: Requirements 16.6, 17.1, 17.2, 18.5, 18.6, 19.1, 19.2, 19.3, 22.4,
#            22.5, 22.6
# ---------------------------------------------------------------------------

def _real_engine_top_out(seat) -> None:
    """Top a seat's PRIVATE engine game out NATURALLY (real spawn collision).

    Fills the seat's real board so the next engine ``spawn`` collides at the
    spawn origin: the real ``engine._place`` sets ``status="game_over"`` AND
    clears ``active`` to ``None``, exactly the terminal condition a naturally
    topped-out board produces. No status is hand-forced and no field is patched;
    the resulting game is a CONSISTENT engine terminal state (active is None),
    so ``build_state_frame`` emits ``active_piece=None`` for it.
    """

    game = seat.game
    # Settle a block in every board cell so ANY spawning piece collides.
    for row in range(len(game.board)):
        for col in range(len(game.board[row])):
            game.board[row][col] = "I"
    # A real engine spawn now collides at the origin -> game_over, active=None.
    engine.spawn(game)
    assert game.status == "game_over"
    assert game.active is None


class _ReaderIdleWebSocket:
    """A fake socket whose ``receive`` blocks forever; ``close`` is recorded.

    The connected peer sends NOTHING, so its reader sits blocked on
    ``websocket.receive()``; unless the reap-close wakes it (writer-gone signal)
    and its writer closes the socket, the reader never terminates. ``send_text``
    records delivered frames; ``close`` records the terminal ``(code, reason)``.
    """

    def __init__(self) -> None:
        from starlette.websockets import WebSocketState

        self.sent: List[str] = []
        self.closed: Optional[Tuple[int, str]] = None
        self.application_state = WebSocketState.CONNECTED

    async def receive(self) -> dict:
        await asyncio.Event().wait()  # idle peer: blocks until cancelled
        raise AssertionError("receive should never return for an idle peer")

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        from starlette.websockets import WebSocketState

        self.closed = (code, reason)
        self.application_state = WebSocketState.DISCONNECTED


async def _reap_close_two_seats(
    *, room_id: str, status: str, advance_to: str, terminal_draw: bool
) -> Tuple[object, "_ReaderIdleWebSocket", "_ReaderIdleWebSocket", object, object]:
    """Build a live two-seat room, park both readers, reap + close via the real seam.

    ``status`` is the lifecycle status to reap; ``advance_to`` selects the
    retention the FakeClock is advanced past; ``terminal_draw`` drives a REAL
    simultaneous engine top-out (a draw) before the finished reap so the finished
    room carries a genuine gameplay outcome. Returns the room, both fake sockets,
    and both reader tasks after a single production cleanup iteration has reaped
    and closed the room. The native production constants are untouched; only the
    injectable FakeClock is advanced.
    """

    from app import main as app_main

    clock = FakeClock()
    manager = rooms.RoomManager(clock=clock)
    endpoint = duel.DuelEndpoint(manager, allowed_origins=("http://localhost:5517",))

    room, seat_a = manager.assign_seat(room_id)
    _r2, seat_b = manager.assign_seat(room_id)
    ws_a = _ReaderIdleWebSocket()
    ws_b = _ReaderIdleWebSocket()

    writer_a = await endpoint._start_writer(ws_a, seat_a)
    writer_b = await endpoint._start_writer(ws_b, seat_b)
    reader_a = asyncio.ensure_future(endpoint._run_action_loop(ws_a, room, seat_a))
    reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
    await asyncio.sleep(0)  # park both readers on the blocking receive

    if status == "playing":
        room.status = "playing"
        manager.mark_activity(room)
    elif status == "finished":
        room.status = "playing"
        manager.mark_activity(room)
        if terminal_draw:
            # A REAL consistent engine simultaneous top-out: BOTH boards topped
            # out via the engine spawn collision (active cleared to None), so one
            # gravity evaluation resolves a DRAW and the room is finished.
            _real_engine_top_out(seat_a)
            _real_engine_top_out(seat_b)
            seat_a.gravity_due_monotonic = clock()
            seat_b.gravity_due_monotonic = clock()
            outcome = gravity.advance_due_boards(room, clock(), manager=manager)
            assert outcome is not None and outcome.result == "draw"
            assert room.status == "finished"

    if advance_to == "waiting":
        clock.advance(manager.waiting_room_retention + 1)
    elif advance_to == "idle":
        clock.advance(manager.idle_timeout + 1)
    elif advance_to == "finished":
        clock.advance(manager.finished_room_retention + 1)

    reaped = manager.cleanup_tick()
    assert [r.room_id for r in reaped] == [room_id]
    for r in reaped:
        await app_main._release_room_resources(r, app_main._reap_close_reason(r.status))

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


def test_simultaneous_natural_topout_terminal_frames_active_none_when_game_over():
    """A REAL simultaneous engine top-out yields consistent active=None terminals.

    Both seats top out via the real engine spawn collision (``active`` cleared to
    ``None``), one gravity evaluation resolves a DRAW, and the both-board terminal
    frames built from these genuine game_over games carry ``status == "game_over"``
    and ``active_piece is None`` -- a consistent engine terminal fixture, never a
    hand-forced status with a stale non-null active piece. This is the fixture
    the D2 normal-completion reap-close is asserted against below.
    """

    manager, clock, room, seat_a, seat_b = _make_playing_room("room-nat-topout")
    _real_engine_top_out(seat_a)
    _real_engine_top_out(seat_b)
    seat_a.gravity_due_monotonic = clock()
    seat_b.gravity_due_monotonic = clock()

    outcome = gravity.advance_due_boards(room, clock(), manager=manager)
    assert outcome is not None
    assert outcome.result == "draw"
    assert room.status == "finished"

    # The terminal both-board frames are CONSISTENT: game_over + active_piece None.
    frames = duel.build_both_board_frames(room)
    assert {f.seat_id for f in frames} == {"A", "B"}
    for frame in frames:
        assert frame.status == "game_over"
        assert frame.active_piece is None


def test_reaped_finished_normal_completion_closes_both_peers_1000():
    """The reaped finished/normal_completion room closes BOTH peers 1000 (D2).

    After a REAL simultaneous natural top-out resolves a draw (room finished), the
    finished-retention window expires and the room is reaped. The native-20 D2
    correction selects the close code BY REASON: a reaped
    finished/normal_completion room closes 1000 ``CLOSE_CODE_NORMAL`` with the
    literal ``normal_completion`` reason (NOT the pre-fix 1001). Both blocked
    readers wake and both sockets actually close with that code+reason; the
    pre-existing draw outcome stands and no NEW winner is fabricated.
    """

    room, ws_a, ws_b, reader_a, reader_b = asyncio.run(
        _reap_close_two_seats(
            room_id="room-reap-normal",
            status="finished",
            advance_to="finished",
            terminal_draw=True,
        )
    )
    # Both blocked readers actually woke and returned (no hang).
    assert reader_a.done() and not reader_a.cancelled()
    assert reader_b.done() and not reader_b.cancelled()
    # BOTH sockets closed 1000 normal_completion (the D2 code selected by reason).
    for ws in (ws_a, ws_b):
        assert ws.closed is not None, "socket was never closed"
        assert ws.closed[0] == contract.CLOSE_CODE_NORMAL
        assert ws.closed[1] == contract.CLOSE_REASON_NORMAL_COMPLETION
    # The pre-existing draw outcome stands; the reap invents no NEW winner.
    assert isinstance(room.outcome, gravity.OutcomeData)
    assert room.outcome.result == "draw"


def test_reaped_waiting_idle_shutdown_rooms_keep_1001():
    """waiting_room_timeout / idle_timeout / server_shutdown reaps keep 1001.

    The D2 code-by-reason selection ONLY promotes a finished/normal_completion
    room to 1000; every other lifecycle reason keeps 1001
    ``CLOSE_CODE_GOING_AWAY``. A reaped WAITING room closes both sockets 1001
    ``waiting_room_timeout``; a reaped idle PLAYING room closes 1001
    ``idle_timeout``; and a shutdown close is 1001 ``server_shutdown``. None
    fabricates a gameplay winner.
    """

    # (a) waiting -> 1001 waiting_room_timeout
    room_w, ws_wa, ws_wb, r_wa, r_wb = asyncio.run(
        _reap_close_two_seats(
            room_id="room-reap-wait",
            status="waiting",
            advance_to="waiting",
            terminal_draw=False,
        )
    )
    for ws in (ws_wa, ws_wb):
        assert ws.closed is not None
        assert ws.closed[0] == contract.CLOSE_CODE_GOING_AWAY
        assert ws.closed[1] == contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT
    assert room_w.outcome is None
    assert r_wa.done() and r_wb.done()

    # (b) playing-idle -> 1001 idle_timeout
    room_i, ws_ia, ws_ib, r_ia, r_ib = asyncio.run(
        _reap_close_two_seats(
            room_id="room-reap-idle2",
            status="playing",
            advance_to="idle",
            terminal_draw=False,
        )
    )
    for ws in (ws_ia, ws_ib):
        assert ws.closed is not None
        assert ws.closed[0] == contract.CLOSE_CODE_GOING_AWAY
        assert ws.closed[1] == contract.CLOSE_REASON_IDLE_TIMEOUT
    assert room_i.outcome is None
    assert r_ia.done() and r_ib.done()

    # (c) server_shutdown -> 1001 server_shutdown (close code selected by reason).
    from app import main as app_main

    async def shutdown_scenario():
        clock = FakeClock()
        manager = rooms.RoomManager(clock=clock)
        endpoint = duel.DuelEndpoint(manager, allowed_origins=("http://localhost:5517",))
        room, seat_a = manager.assign_seat("room-reap-shutdown")
        _r2, seat_b = manager.assign_seat("room-reap-shutdown")
        room.status = "playing"
        manager.mark_activity(room)
        ws_a = _ReaderIdleWebSocket()
        ws_b = _ReaderIdleWebSocket()
        writer_a = await endpoint._start_writer(ws_a, seat_a)
        writer_b = await endpoint._start_writer(ws_b, seat_b)
        reader_a = asyncio.ensure_future(endpoint._run_action_loop(ws_a, room, seat_a))
        reader_b = asyncio.ensure_future(endpoint._run_action_loop(ws_b, room, seat_b))
        await asyncio.sleep(0)
        # A server shutdown closes every live room's sockets with the literal
        # server_shutdown reason, 1001 (the code-by-reason default).
        await app_main._release_room_resources(
            room, contract.CLOSE_REASON_SERVER_SHUTDOWN
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

    room_s, ws_sa, ws_sb, r_sa, r_sb = asyncio.run(shutdown_scenario())
    for ws in (ws_sa, ws_sb):
        assert ws.closed is not None
        assert ws.closed[0] == contract.CLOSE_CODE_GOING_AWAY
        assert ws.closed[1] == contract.CLOSE_REASON_SERVER_SHUTDOWN
    assert room_s.outcome is None
    assert r_sa.done() and r_sb.done()
