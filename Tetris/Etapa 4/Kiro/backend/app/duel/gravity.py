"""Per-board server-side gravity for the duel (Stage 4 Option A, M3).

This module owns the AUTHORITATIVE per-board gravity progression for a duel
``Room`` and the single terminal-outcome decision that follows a gravity
evaluation or a disconnect. It layers strictly on top of the seams already
provided by :mod:`app.duel.rooms` (``Seat``, ``Room``, ``RoomManager``) and the
pure :mod:`app.rules.engine`; it declares no new lifecycle state of its own.

Design decisions encoded here (see design.md "Per-board server-side gravity"
and "Duel outcome resolution", Req 18.1-18.6, 19.4):

* **Pure, synchronous step core (Req 19.4).** :func:`advance_due_boards` and
  :func:`resolve_forfeit` are PURE/synchronous functions that take the current
  monotonic ``now`` as an INPUT. They never call ``time.monotonic`` themselves,
  so a test can drive gravity deterministically with a fake injectable clock.
  The async scheduling loop (:func:`gravity_step` / :func:`run_gravity_loop`)
  is kept thin and separate; the lifespan wiring/task creation is task 15.1.

* **Independent per-board advancement (Req 18.1, 18.2).** Each seat's next due
  time ``gravity_due_monotonic`` is derived from THAT board's current
  ``gravity_interval_ms`` via the inherited formula
  ``gravity_interval_ms = max(100, 500 - 50 * (level - 1))`` (already applied by
  ``engine.lock`` and surfaced on the seat's ``Game``). Only a board whose due
  time has elapsed is advanced (one ``engine.tick`` per elapsed interval), and
  its next due time is recomputed from its current interval. Advancing one seat
  never advances the other -- each seat owns a PRIVATE engine ``Game``.

* **Revision only advances on a real change (Req 20.2 consistency).** A seat's
  ``revision`` is bumped ONLY when ``engine.tick`` actually changed that board's
  observable state. A no-op tick (e.g. a board already ``game_over``) leaves the
  revision untouched, consistent with the per-board revision-only-advances-on-
  change rule shared with the action path.

* **Evaluate ALL due boards, then decide once (Req 18.3, 18.4).** The step
  advances every due board FIRST, then evaluates the terminal state EXACTLY
  once: if BOTH boards topped out in this evaluation the outcome is a DRAW; if
  exactly one board remains playable the surviving seat WINS. Resolution always
  flows through ``Room.set_outcome_once`` so a duel resolves EXACTLY once
  (Req 18.5, 18.6) -- a finished room is never resolved a second time.

* **Disconnect is a forfeit resolved once (Req 18.5).** :func:`resolve_forfeit`
  resolves the duel EXACTLY once via ``Room.set_outcome_once``: the disconnecting
  seat forfeits and the other seat wins. A disconnect+gravity race therefore
  resolves the duel exactly once because both paths funnel through the same
  set-once guard.

* **Stop at terminal (Req 18.6).** Gravity only advances while
  ``room.status == "playing"``. Once the room is ``finished`` the step is a
  no-op, so a resolved room's gravity stops.

The decision core produces a DETACHED :class:`OutcomeData` (seats + per-seat
final revisions + result kind). Building the actual wire ``Outcome`` frame is a
thin, shared helper (:func:`build_outcome_frame`) the endpoint (task 14.1) and
the lifespan loop (task 15.1) can both call, keeping a clean seam between the
pure decision and the wire-frame construction.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..rules import engine
from ..ws import contract
from .rooms import Room, RoomManager, Seat, SeatId

#: Fixed per-room gravity evaluation cadence in seconds (design.md "1-second
#: cleanup cadence"). The async loop re-evaluates at this cadence; the pure step
#: itself is cadence-agnostic (it compares each board's due time against ``now``).
GRAVITY_CADENCE_S: float = contract.CLEANUP_CADENCE_S

#: Upper bound on ticks applied to a single board within ONE evaluation. A board
#: whose due time is far in the past (e.g. the clock jumped forward) is advanced
#: at most this many ticks per evaluation so one board can never monopolise the
#: worker; the remaining backlog is caught up on the next evaluation. This keeps
#: the step bounded regardless of how large ``now - gravity_due_monotonic`` is.
MAX_TICKS_PER_EVALUATION: int = 64


def _board_is_game_over(seat: Seat) -> bool:
    """Return True when this seat's private board has topped out (``game_over``)."""

    return getattr(seat.game, "status", None) == "game_over"


def _snapshot_board_identity(seat: Seat) -> tuple:
    """Return a cheap comparable fingerprint of the observable board state.

    Used to detect whether an ``engine.tick`` actually changed anything so the
    per-board ``revision`` is bumped ONLY on a real change. The fingerprint
    captures the fields a gravity tick can move: board status, the active
    piece's origin/cells, and the lock-derived counters (score/total_lines/
    level). It deliberately avoids deep-copying the whole board; a gravity tick
    that locks a piece always changes at least one of these fields.
    """

    game = seat.game
    active = getattr(game, "active", None)
    active_identity: object
    if active is None:
        active_identity = None
    else:
        active_identity = (
            active.type,
            tuple(active.origin),
            tuple(tuple(cell) for cell in active.cells),
            active.orientation,
        )
    return (
        getattr(game, "status", None),
        active_identity,
        getattr(game, "score", None),
        getattr(game, "total_lines", None),
        getattr(game, "level", None),
    )


def _seat_scalar_would_overflow(seat: Seat, *, pending_revision_bump: bool) -> bool:
    """Return True iff committing this seat's advanced board WOULD overflow a scalar.

    This is the GRAVITY-side analogue of the endpoint's pre-commit
    ``would_scalar_overflow`` action guard (task 30.3 / 35.6): a server no-input
    gravity tick must NEVER drive a scalar past its documented ceiling and then
    publish an out-of-range ``state``/``outcome`` frame. It is evaluated AFTER
    the board was advanced by :func:`advance_seat_gravity` but BEFORE this seat's
    authoritative ``revision`` is bumped and BEFORE any frame is published, so a
    value that WOULD overflow is caught while it is still only a would-be value.

    It inspects the post-tick game scalars (``score``/``total_lines`` against the
    safe-integer ceiling, ``level`` against its max) AND the WOULD-BE revision --
    ``seat.revision + 1`` when this evaluation changed the board (so a bump is
    pending), otherwise the unchanged ``seat.revision`` -- against the
    safe-integer ceiling. Testing the would-be revision rather than a revision
    already bumped means an overflow aborts the room BEFORE the revision becomes
    authoritative, so no out-of-range ``revision`` is ever committed or emitted.
    """

    would_be_revision = seat.revision + 1 if pending_revision_bump else seat.revision
    if would_be_revision > contract.SAFE_INT_MAX:
        return True
    game = seat.game
    if getattr(game, "score", 0) > contract.SAFE_INT_MAX:
        return True
    if getattr(game, "total_lines", 0) > contract.SAFE_INT_MAX:
        return True
    if getattr(game, "level", 1) > contract.LEVEL_MAX:
        return True
    return False


def _current_interval_seconds(seat: Seat) -> float:
    """Return this board's current gravity interval in SECONDS.

    The interval is read from the seat's private ``Game.gravity_interval_ms``,
    which ``engine.lock`` keeps equal to ``max(100, 500 - 50 * (level - 1))``.
    Converting to seconds keeps the due-time arithmetic on the same monotonic
    scale as the injectable clock.
    """

    interval_ms = getattr(seat.game, "gravity_interval_ms", contract.GRAVITY_INTERVAL_MAX_MS)
    return interval_ms / 1000.0


def advance_seat_gravity(seat: Seat, now: float) -> bool:
    """Advance ONE seat's board for every gravity interval elapsed by ``now``.

    Returns ``True`` when the board's observable state actually changed (so the
    caller bumps that seat's ``revision`` exactly once for this evaluation),
    ``False`` on a pure no-op. The seat's ``gravity_due_monotonic`` is advanced
    by its CURRENT interval for each applied tick (recomputing the interval each
    time, so a lock that raised the level immediately shortens the next step),
    bounded by :data:`MAX_TICKS_PER_EVALUATION`. A board that is already
    ``game_over`` is never advanced.
    """

    if _board_is_game_over(seat):
        # A topped-out board never advances again; keep its due time pinned so it
        # is not repeatedly "due" on every evaluation.
        return False

    changed = False
    ticks = 0
    while (
        seat.gravity_due_monotonic <= now
        and ticks < MAX_TICKS_PER_EVALUATION
        and not _board_is_game_over(seat)
    ):
        before = _snapshot_board_identity(seat)
        engine.tick(seat.game)
        after = _snapshot_board_identity(seat)
        if after != before:
            changed = True
        # Recompute the next due time from the board's CURRENT interval (a lock
        # during this tick may have shortened it).
        seat.gravity_due_monotonic += _current_interval_seconds(seat)
        ticks += 1

    return changed


@dataclass(frozen=True)
class OutcomeData:
    """Detached result of a terminal evaluation (pure decision, no wire frame).

    ``result`` is one of ``"win"`` / ``"draw"`` / ``"forfeit"``. The seat fields
    follow the contract's per-result relationships:

    * ``win``   -> ``winning_seat`` and ``losing_seat`` are two DISTINCT seats;
      ``forfeiting_seat`` is ``None``.
    * ``draw``  -> all three seat fields are ``None``.
    * ``forfeit`` -> ``forfeiting_seat == losing_seat``; ``winning_seat`` is the
      other (surviving) seat.

    ``final_revision`` is the per-seat authoritative revision at resolution,
    keyed by seat id (``"A"``/``"B"``). The endpoint/lifespan turns this detached
    record into the schema-valid wire ``Outcome`` via :func:`build_outcome_frame`.
    """

    result: contract.OutcomeResult
    winning_seat: Optional[SeatId]
    losing_seat: Optional[SeatId]
    forfeiting_seat: Optional[SeatId]
    final_revision: Dict[str, int]


def _final_revision_map(room: Room) -> Dict[str, int]:
    """Build the per-seat final-revision map, defaulting a missing seat to 0.

    Both seat ids are always present in the map (the contract's ``FinalRevision``
    requires both ``A`` and ``B``); an unoccupied seat reports revision ``0``.
    """

    revisions: Dict[str, int] = {"A": 0, "B": 0}
    for seat_id, seat in room.seats.items():
        revisions[seat_id] = seat.revision
    return revisions


def _other_seat(seat_id: SeatId) -> SeatId:
    """Return the opposite seat id (A<->B)."""

    return "B" if seat_id == "A" else "A"


def evaluate_outcome(room: Room) -> Optional[OutcomeData]:
    """Decide the single terminal outcome after all due boards were advanced.

    Returns the :class:`OutcomeData` when the duel should resolve from a gravity
    evaluation, or ``None`` when the duel is still in progress. This function is
    PURE: it only reads the room/seat state. The caller is responsible for
    committing the outcome via :func:`resolve_outcome` (which funnels through
    ``Room.set_outcome_once`` so resolution happens exactly once).

    Decision (Req 18.3, 18.4):

    * BOTH boards topped out -> ``draw``.
    * exactly one board playable -> that seat ``win``s (the other seat loses).
    * both still playable -> ``None`` (not terminal yet).

    A room without two seats is never resolved by gravity here (the endpoint
    governs the waiting/forfeit paths); it returns ``None``.
    """

    if len(room.seats) != 2:
        return None

    playable = [
        seat_id
        for seat_id, seat in room.seats.items()
        if not _board_is_game_over(seat)
    ]

    if len(playable) == 0:
        # Simultaneous top-out within this single evaluation -> DRAW.
        return OutcomeData(
            result="draw",
            winning_seat=None,
            losing_seat=None,
            forfeiting_seat=None,
            final_revision=_final_revision_map(room),
        )
    if len(playable) == 1:
        winner = playable[0]
        loser = _other_seat(winner)
        return OutcomeData(
            result="win",
            winning_seat=winner,
            losing_seat=loser,
            forfeiting_seat=None,
            final_revision=_final_revision_map(room),
        )
    # Both boards still playable: no terminal outcome yet.
    return None


def resolve_outcome(
    room: Room,
    outcome: OutcomeData,
    now: float,
    *,
    manager: Optional[RoomManager] = None,
) -> bool:
    """Commit a decided outcome EXACTLY once via ``Room.set_outcome_once``.

    Returns ``True`` the first time the room resolves (status -> ``finished``,
    outcome stored), ``False`` if the room was already finished (so a second
    event never re-resolves it, Req 18.5, 18.6). When ``manager`` is supplied the
    room's activity stamp is refreshed on the first resolution so the finished
    room's retention window starts cleanly.
    """

    resolved = room.set_outcome_once(outcome, now)
    if resolved and manager is not None:
        manager.mark_activity(room)
    return resolved


def advance_due_boards(
    room: Room,
    now: float,
    *,
    manager: Optional[RoomManager] = None,
) -> Optional[OutcomeData]:
    """Advance every due board, then decide the single terminal outcome once.

    This is the PURE/synchronous gravity step (Req 18.1-18.4, 18.6). Behaviour:

    1. If the room is not ``playing`` it is a NO-OP returning ``None`` (gravity
       stops once a room is finished).
    2. Every seat whose ``gravity_due_monotonic <= now`` is advanced via
       :func:`advance_seat_gravity`; a real state change bumps that seat's
       ``revision`` exactly once and refreshes room activity (so an actively
       progressing board is never reaped as idle, Req 19 idle policy).
    3. AFTER advancing all due boards, the terminal state is evaluated EXACTLY
       once (:func:`evaluate_outcome`) and, when terminal, committed via
       :func:`resolve_outcome` (``Room.set_outcome_once``). The committed
       :class:`OutcomeData` is returned so the caller can emit the terminal
       ``outcome`` frame; ``None`` is returned when the duel is still in progress.

    The ``now`` is an INPUT (never read from ``time.monotonic`` here) so a test
    drives gravity deterministically with a fake clock.
    """

    if room.status != "playing":
        return None

    any_change = False
    for seat in room.seats.values():
        if seat.gravity_due_monotonic <= now:
            changed = advance_seat_gravity(seat, now)
            # SCALAR-OVERFLOW OPERATIONAL ABORT ON THE GRAVITY TRANSITION
            # (task 35.6). A server no-input gravity tick that WOULD push this
            # board's ``score``/``total_lines``/``level`` past its documented
            # ceiling -- or whose would-be bumped ``revision`` would exceed the
            # safe-integer ceiling -- must NOT commit the revision bump, must NOT
            # resolve a gameplay outcome, and must NOT publish any out-of-range
            # ``state``/``outcome`` frame. It aborts the WHOLE room operationally
            # (1001 ``"scalar_overflow"``, no fabricated winner) BEFORE
            # publishing, mirroring the action path's pre-commit guard. Checked
            # against the WOULD-BE revision (``seat.revision + 1`` when this
            # evaluation changed the board) so the overflow is caught while it is
            # still a would-be value. Returning ``None`` here leaves no dead
            # gravity task from a ValidationError: the room is marked aborted and
            # both writers are directed to close, so both readers wake and tear
            # down WITHOUT a further gravity step.
            if _seat_scalar_would_overflow(seat, pending_revision_bump=changed):
                _operational_abort_room(
                    room, contract.CLOSE_REASON_SCALAR_OVERFLOW
                )
                return None
            if changed:
                seat.revision += 1
                any_change = True

    if any_change and manager is not None:
        manager.mark_activity(room)

    outcome = evaluate_outcome(room)
    if outcome is None:
        return None
    if resolve_outcome(room, outcome, now, manager=manager):
        return outcome
    return None


def _operational_abort_room(room: Room, reason: str) -> bool:
    """Mark the room operationally aborted once and direct BOTH writers to close.

    Shared gravity-side operational-abort helper (task 35.6). An operational
    abort (``reason`` is the literal ``"scalar_overflow"`` here) is DISTINCT from
    the gameplay ``peer_unavailable_forfeit``: it fabricates NO winner, so
    ``room.outcome`` is left untouched (``None``) and ``Room.set_outcome_once`` /
    :func:`resolve_forfeit` are NEVER invoked.

    The FIRST caller to win ``Room.set_operational_abort_once`` directs EVERY
    seat's independent writer to close its own socket with code 1001 + the SAME
    literal ``reason`` (the writer drains any already-queued frames first, then
    closes). Each peer's blocked reader wakes on the directed close and funnels
    through the endpoint's disconnect cleanup, which observes
    ``room.operational_abort`` and so does NOT fabricate a forfeit on the aborted
    room. The gravity loop never publishes a ``state``/``outcome`` frame for an
    operationally-aborted room (see :func:`gravity_step`), so no out-of-range
    scalar is ever emitted. A racing second abort/resolution loses the set-once
    guard and this is a no-op. Returns ``True`` the first time the room aborts.
    """

    first = room.set_operational_abort_once(reason)
    if first:
        for seat in room.seats.values():
            seat.request_close(contract.CLOSE_CODE_GOING_AWAY, reason)
    return first


def resolve_forfeit(
    room: Room,
    forfeiting_seat: SeatId,
    now: float,
    *,
    manager: Optional[RoomManager] = None,
) -> Optional[OutcomeData]:
    """Resolve a disconnect as a forfeit EXACTLY once (Req 18.5).

    The ``forfeiting_seat`` forfeits and the OTHER seat wins. Resolution funnels
    through ``Room.set_outcome_once``, so a disconnect that races a gravity
    evaluation (or a second disconnect event) can only resolve the duel once:
    the first caller to win the set-once guard decides the outcome and every
    later caller gets ``None``.

    Returns the committed :class:`OutcomeData` on the first (winning) resolution,
    or ``None`` when the room was already finished (already resolved by gravity
    or a prior forfeit). A forfeit is only meaningful for a two-seat room; a
    never-started waiting room's cancellation is an OPERATIONAL ABORT handled by
    the endpoint (no gameplay winner) and is not resolved here.
    """

    if room.status != "playing":
        return None
    if len(room.seats) != 2:
        return None

    winner = _other_seat(forfeiting_seat)
    outcome = OutcomeData(
        result="forfeit",
        winning_seat=winner,
        losing_seat=forfeiting_seat,
        forfeiting_seat=forfeiting_seat,
        final_revision=_final_revision_map(room),
    )
    if resolve_outcome(room, outcome, now, manager=manager):
        return outcome
    return None


def build_outcome_frame(room_id: str, outcome: OutcomeData) -> contract.Outcome:
    """Build the schema-valid wire ``Outcome`` frame from a decided outcome.

    This is the thin, SHARED seam between the pure decision core and the wire
    layer: the endpoint (task 14.1) and the lifespan loop (task 15.1) both call
    this instead of re-constructing the frame. The resulting ``Outcome`` is
    validated by the contract model's per-result seat-relationship rules, so an
    inconsistent :class:`OutcomeData` is rejected at construction rather than
    emitted as an invalid frame.
    """

    return contract.Outcome(
        type="outcome",
        room_id=room_id,
        result=outcome.result,
        winning_seat=outcome.winning_seat,
        losing_seat=outcome.losing_seat,
        forfeiting_seat=outcome.forfeiting_seat,
        final_revision=contract.FinalRevision(
            A=outcome.final_revision.get("A", 0),
            B=outcome.final_revision.get("B", 0),
        ),
    )


# ---------------------------------------------------------------------------
# Thin async scheduling layer. Kept deliberately small and separate from the
# pure step so it stays trivially testable; the lifespan wiring/task creation
# (a single periodic task against the injectable clock) is task 15.1.
# ---------------------------------------------------------------------------


def gravity_step(
    manager: RoomManager,
    *,
    on_state: Optional[Callable[[Room], None]] = None,
    on_outcome: Optional[Callable[[Room, OutcomeData], None]] = None,
) -> List[OutcomeData]:
    """Run ONE synchronous gravity evaluation across every playing room.

    Reads ``now`` from the manager's INJECTABLE clock exactly once so all rooms
    are evaluated against a single consistent instant. For each room still
    ``playing`` it calls :func:`advance_due_boards`; when a room's boards
    actually advanced this step the optional ``on_state`` callback is invoked so
    the AUTHORITATIVE boards are PUBLISHED after the server no-input gravity
    advance (native-14: the loop previously mutated private games silently).
    When a room resolves, the optional ``on_outcome`` callback is invoked (e.g.
    to enqueue the terminal ``outcome`` frame) and the resolved outcome is
    collected. ``on_state`` runs for a resolved room too, so the final
    pre-terminal boards reach both peers before the outcome. Iterates over a
    detached snapshot of the rooms so a concurrent release does not break the
    loop. Returns the list of outcomes resolved this step (possibly empty).
    """

    now = manager.clock()
    resolved: List[OutcomeData] = []
    for room in list(manager.rooms.values()):
        if room.status != "playing":
            continue
        # Capture whether any board was actually due BEFORE advancing so a pure
        # no-step evaluation does not publish a redundant frame.
        due = any(
            seat.gravity_due_monotonic <= now for seat in room.seats.values()
        )
        outcome = advance_due_boards(room, now, manager=manager)
        if room.operational_abort is not None:
            # SCALAR-OVERFLOW OPERATIONAL ABORT (task 35.6): the gravity
            # transition detected a would-be scalar overflow and aborted the
            # room BEFORE publishing. Skip BOTH ``on_state`` and ``on_outcome``
            # so no out-of-range ``state``/``outcome`` frame is ever emitted; the
            # abort already directed both writers to close 1001 +
            # ``scalar_overflow`` with no fabricated winner. ``advance_due_boards``
            # returns ``None`` on abort, so nothing is collected either.
            continue
        if due and on_state is not None:
            # Publish both authoritative boards after the no-input gravity
            # advance (the room may now be ``finished``; the callback reads the
            # current room status, so the final boards carry the terminal
            # room_status).
            on_state(room)
        if outcome is not None:
            resolved.append(outcome)
            if on_outcome is not None:
                on_outcome(room, outcome)
    return resolved


async def run_gravity_loop(
    manager: RoomManager,
    *,
    cadence_s: float = GRAVITY_CADENCE_S,
    on_state: Optional[Callable[[Room], None]] = None,
    on_outcome: Optional[Callable[[Room, OutcomeData], None]] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Drive :func:`gravity_step` periodically until cancelled or stopped.

    This thin async wrapper is what the lifespan owns (task 15.1): it sleeps
    ``cadence_s`` between evaluations and exits cleanly on cancellation or when
    ``stop_event`` is set, so the task is never leaked on shutdown. All timing
    decisions inside the step still come from the manager's injectable clock, so
    the loop only governs the real-time cadence, not the gravity arithmetic.
    The ``on_state``/``on_outcome`` callbacks are forwarded to each step so the
    lifespan can publish both authoritative boards (and the terminal outcome) to
    both peers after a no-input gravity advance (native-14).
    """

    try:
        while stop_event is None or not stop_event.is_set():
            gravity_step(manager, on_state=on_state, on_outcome=on_outcome)
            await asyncio.sleep(cadence_s)
    except asyncio.CancelledError:
        # Cooperative cancellation: RE-RAISE so the cancellation genuinely
        # propagates to this task (it is marked cancelled and its awaiter in the
        # lifespan observes it) rather than being silently swallowed. Swallowing
        # it here would hide the cancellation and is the S7497 lifecycle finding
        # corrected by native-14 task 30.1. The surrounding ``await asyncio.sleep``
        # has already been interrupted, so nothing is leaked by re-raising.
        raise


__all__ = [
    "GRAVITY_CADENCE_S",
    "MAX_TICKS_PER_EVALUATION",
    "OutcomeData",
    "advance_seat_gravity",
    "advance_due_boards",
    "evaluate_outcome",
    "resolve_outcome",
    "resolve_forfeit",
    "build_outcome_frame",
    "gravity_step",
    "run_gravity_loop",
]
