"""The duel WebSocket endpoint ``/ws/duel`` (Stage 4 Option A, M3, task 14.1).

This module is the SEMANTIC CORE of M3: it wires the versioned wire contract
(:mod:`app.ws.contract`), the in-memory rooms (:mod:`app.duel.rooms`), the
per-board gravity / outcome resolution (:mod:`app.duel.gravity`), and the pure
rules engine (:mod:`app.rules.engine`) into a single same-origin WebSocket
endpoint served by the one FastAPI worker.

Design anchors (see design.md "Duel transport and rooms", "Duel wire contract",
"Duel origin, bounds, close codes, and WS engine"; Req 16.1, 17.1, 17.2, 20.3-
20.11, 22.1, 22.3, 22.4, 22.5):

* **Origin denial is an HTTP-level rejection (Req 22.1).** The request ``Origin``
  is validated against an EXACT allow-list bound to the proxy host/port
  (``http://localhost:5517`` / ``http://127.0.0.1:5517`` by default, configurable
  via ``TETRIS_WS_ALLOWED_ORIGINS`` and fail-closed exactly like the HTTP CORS
  list). A disallowed Origin is rejected BEFORE ``websocket.accept()`` -- in
  Starlette, closing before accept rejects the HTTP upgrade (an HTTP 403), so the
  request never becomes a WebSocket and no WebSocket CLOSE frame is emitted.

* **Ordered check sequence (design.md, Req 20.*).** Every inbound action runs the
  EXACT documented order: (1) schema/format + ``protocol_version``; (2) seat
  ownership; (3) rate limit (fixed 1-second window, inbound actions only);
  (4) room-status/start gate (``not_started`` while ``waiting`` -- does NOT
  consume the ordinal or high-water mark, and is NOT cached); (5) reply-cache
  lookup; (6) ordinal vs high-water mark; (7) ``expected_revision`` STRICT
  equality; (8) apply to the sender's private board. Malformed, unowned, or
  rate-limited input never reaches the cache/ordinal/sequence, so it never burns
  another seat's sequence.

* **Strict equality revision window (Req 20.4, 20.6, 20.7).** A LOWER
  ``expected_revision`` than the board's authoritative revision rejects
  ``stale_revision``; a HIGHER value rejects ``future_revision``; neither mutates
  the board. A new id that is stale/future/no-op STILL consumes the ordinal
  (advances the high-water mark) and is cached, so a rejected id can never become
  newly applied once the revision catches up.

* **Bounded idempotency (Req 20.5).** A cached ``action_id`` with an IDENTICAL
  fingerprint returns the cached reply; a cached id with a CHANGED fingerprint,
  or any uncached id at or below the high-water mark, rejects
  ``duplicate_action_conflict`` without re-applying. Only an ordinal strictly
  above the high-water mark is a new action.

* **No-op ack (Req 20.8).** A legal action that changes nothing is acked with
  ``applied=True, no_op=True`` and the UNCHANGED revision; an applied change
  bumps revision by one and emits a fresh ``state`` frame.

* **Terminal paths funnel through set-once resolution (Req 18.5, 18.6).** A
  failed-send / slow-peer disconnect in a STARTED room is a GAMEPLAY FORFEIT
  resolved exactly once (``resolve_forfeit`` -> ``peer_unavailable_forfeit``,
  1001); a never-started waiting-room cancellation is a separate OPERATIONAL
  ABORT that fabricates no winner (``waiting_room_timeout``, 1001). A 1007
  transport close (wire-level invalid UTF-8 / library-managed) in a STARTED room
  applies the ordinary disconnect/forfeit/once-only cleanup; a waiting-alone 1007
  fabricates no winner.

* **Bounded, leak-free, no internals in detail (Req 21.6, 22.3, 22.4).** Oversize
  messages (1009), rate breaches (1008 ``rate_limited``), malformed JSON / in-band
  binary frames (``ErrorFrame(malformed_message)``), and a room-at-maximum
  condition are all handled boundedly; ``detail`` strings are short fixed English
  with no path/SQL/exception/stack, and no schema-invalid scalar is ever emitted.

The decision logic is deliberately factored into PURE helpers (origin check,
fingerprint builder, ordinal parser, state-frame builder, the stale/future/
no-op/duplicate decision, and the fixed-window rate limiter) so the connection
tests (task 14.2) can exercise the semantics without a live socket. The endpoint
itself only performs transport I/O and funnels every decision through these
helpers. The app registration + lifespan-owned ``RoomManager``/cleanup task is
task 15.1; this module exposes a ``build_duel_router(manager)`` factory and a
``DuelEndpoint`` callable so 15.1 can wire a lifespan-owned manager cleanly.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect, WebSocketState

from ..rules import engine
from ..api.schemas import TYPE_CODES
from . import contract
from ..duel import gravity
from ..duel.rooms import (
    Room,
    RoomCapacityError,
    RoomClosedError,
    RoomFullError,
    RoomManager,
    Seat,
)

# ---------------------------------------------------------------------------
# Origin allow-list (Req 22.1). Bound to the PROXY host/port (5517), distinct
# from the solo HTTP CORS list (5173); configurable and fail-closed exactly like
# ``main._resolve_allowed_origins``.
# ---------------------------------------------------------------------------

#: Default WS allow-list bound to the reverse-proxy host/port (Req 22.1, 22.2).
_DEFAULT_WS_ALLOWED_ORIGINS = "http://localhost:5517,http://127.0.0.1:5517"

#: Environment variable mirroring the HTTP ``TETRIS_ALLOWED_ORIGINS`` convention.
_WS_ORIGINS_ENV = "TETRIS_WS_ALLOWED_ORIGINS"


class WSOriginConfigurationError(ValueError):
    """Raised when the configured WS Origin allow-list is invalid (fail closed).

    Mirrors ``main.CORSConfigurationError``: a wildcard ``*`` origin can never be
    combined with the duel's same-origin policy, so a resolved list containing a
    literal ``*`` -- alone or mixed with concrete origins -- is rejected at
    resolution rather than silently allowing an arbitrary origin.
    """


def resolve_ws_allowed_origins(raw: Optional[str] = None) -> Tuple[str, ...]:
    """Resolve the exact, restrictive WS Origin allow-list (fail closed).

    Reads ``raw`` (defaulting to the ``TETRIS_WS_ALLOWED_ORIGINS`` environment
    variable); an unset/empty value falls back to the restrictive proxy-bound
    defaults. A resolved list containing a literal ``*`` is rejected with
    :class:`WSOriginConfigurationError` (fail closed), so only concrete explicit
    origins are ever returned. This mirrors the HTTP CORS convention in
    ``main._resolve_allowed_origins`` but binds to the proxy port 5517.
    """

    if raw is None:
        raw = os.environ.get(_WS_ORIGINS_ENV)
    if raw is None or raw.strip() == "":
        raw = _DEFAULT_WS_ALLOWED_ORIGINS
    origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    if any(origin == "*" for origin in origins):
        raise WSOriginConfigurationError(
            "A wildcard '*' origin cannot be combined with the duel same-origin "
            "policy. Set TETRIS_WS_ALLOWED_ORIGINS to explicit concrete origins."
        )
    return origins


def origin_is_allowed(origin: Optional[str], allow_list: Tuple[str, ...]) -> bool:
    """Return True iff ``origin`` EXACTLY matches an entry in ``allow_list``.

    A missing/empty ``Origin`` header is DENIED (fail closed): the same-origin
    duel always expects the proxy-provided origin, so an absent origin is not
    silently trusted. Matching is exact string equality (scheme+host+port), never
    a prefix or wildcard match.
    """

    if not origin:
        return False
    return origin in allow_list


# ---------------------------------------------------------------------------
# Pure request helpers: fingerprint, ordinal, state-frame builder.
# ---------------------------------------------------------------------------

#: The immutable request fingerprint tuple (design.md "reply cache" fingerprint):
#: ``(kind, expected_revision, room_id, seat_id, action_id)``.
Fingerprint = Tuple[str, int, str, str, str]


def build_fingerprint(action: contract.ActionMessage) -> Fingerprint:
    """Build the immutable request fingerprint for a validated action.

    The fingerprint is ``(kind, expected_revision, room_id, seat_id, action_id)``
    -- the exact tuple the reply cache stores. A cached ``action_id`` whose
    fingerprint differs from a later reuse is a ``duplicate_action_conflict``
    (a changed payload never applies or replaces the cache).
    """

    return (
        action.kind,
        action.expected_revision,
        action.room_id,
        action.seat_id,
        action.action_id,
    )


def ordinal_of(action_id: str) -> int:
    """Return the integer ordinal after the ``A-``/``B-`` seat prefix.

    The grammar (enforced by the contract validator) guarantees a seat letter, a
    hyphen, then a 1..15-digit positive decimal with no leading zeros, so a plain
    ``int`` parse of the suffix is exact and bounded by
    :data:`contract.MAX_ACTION_ORDINAL`.
    """

    return int(action_id[2:])


#: Matches an ``action_id`` that is the correct seat prefix followed by a
#: positive decimal with NO leading zero and MORE than 15 digits, i.e. an ordinal
#: that EXCEEDS the maximum valid ordinal ``999999999999999`` (fifteen nines).
#: This is EXACTLY the next-higher-than-max case: it is a syntactically clean
#: "A-"/"B-" + digits id that overflows the 1..15-digit grammar only because the
#: ordinal is too large, NOT a malformed id with stray/illegal characters. The
#: trailing negative lookahead ``(?![\s\S])`` -- the SAME anchor the canonical
#: ``action_id`` grammar uses INSTEAD of ``$`` -- forbids ANY trailing character,
#: so an id with a non-digit tail (LF/CR/CRLF/U+2028/U+2029/other) does NOT match.
#: Using ``$`` here would (under Python ``re``) match before a trailing ``\n`` and
#: wrongly reclassify a grammar-violating trailing-terminator id as a clean
#: sequence exhaustion; the lookahead preserves the strict full-string grammar.
#: Compiled with NO MULTILINE/DOTALL flags so ``^`` and the lookahead do all the
#: anchoring.
_SEQUENCE_EXHAUSTED_RE = {
    "A": re.compile(r"^A-([1-9][0-9]{15,})(?![\s\S])"),
    "B": re.compile(r"^B-([1-9][0-9]{15,})(?![\s\S])"),
}


def is_sequence_exhausted_id(seat_id: str, action_id: object) -> bool:
    """Return True iff ``action_id`` is this seat's next-higher-than-max ordinal.

    The maximum valid ordinal ``999999999999999`` is CONSUMABLE; the NEXT higher
    ordinal cannot be represented under the 1..15-digit grammar, so it fails the
    ``action_id`` pattern. This helper recognises exactly that overflow case for
    the given ``seat_id``: a clean ``"A-"``/``"B-"`` prefix (matching the seat)
    followed by a leading-zero-free decimal with 16+ digits, which is numerically
    greater than :data:`contract.MAX_ACTION_ORDINAL`. It deliberately does NOT
    match an id with any trailing non-digit character (line terminator or other),
    so a genuinely malformed/non-canonical id still takes the ordinary
    schema-error / malformed path and is never mislabelled a sequence exhaustion.
    """

    if not isinstance(action_id, str):
        return False
    pattern = _SEQUENCE_EXHAUSTED_RE.get(seat_id)
    if pattern is None:
        return False
    match = pattern.match(action_id)
    if match is None:
        return False
    # Defensive numeric confirmation: the matched ordinal exceeds the documented
    # maximum. (The 16+-digit pattern already guarantees this, but the explicit
    # bound keeps the intent self-evident and robust to any grammar change.)
    return int(match.group(1)) > contract.MAX_ACTION_ORDINAL


def _serialize_board(game: object) -> List[List[int]]:
    """Serialize a private engine game's board to the wire ``0..7`` code grid.

    Uses the SAME ``TYPE_CODES`` mapping as the solo ``schemas.serialize`` so a
    duel ``state`` frame's board matches ``GameStateOut`` exactly (0 = empty).
    """

    board = getattr(game, "board")
    return [
        [TYPE_CODES[cell] if cell is not None else 0 for cell in row]
        for row in board
    ]


def build_state_frame(
    room_id: str,
    seat: Seat,
    room_status: contract.RoomStatus,
) -> contract.StateFrame:
    """Build the schema-valid ``state`` frame from a seat's PRIVATE engine game.

    ``room_status`` (room lifecycle) is REQUIRED on every state frame and is
    distinct from the per-seat board ``status`` (``playing``/``game_over``). The
    board/active-piece/queue/Hold fields mirror ``GameStateOut`` + ``TYPE_CODES``;
    the contract model enforces the status/active-piece relationship (a
    ``playing`` frame carries a non-null active piece, a ``game_over`` frame a
    null one), so this builder never emits an inconsistent frame.
    """

    game = seat.game
    active = getattr(game, "active", None)
    active_piece: Optional[contract.ActivePiece] = None
    if active is not None:
        active_piece = contract.ActivePiece(
            type=active.type,
            origin=tuple(active.origin),
            cells=[tuple(cell) for cell in active.cells],
        )

    return contract.StateFrame(
        type="state",
        room_id=room_id,
        seat_id=seat.seat_id,
        revision=seat.revision,
        status=getattr(game, "status"),
        room_status=room_status,
        board=_serialize_board(game),
        active_piece=active_piece,
        next_piece=getattr(game, "next_type"),
        hold_piece=getattr(game, "hold_type"),
        can_hold=getattr(game, "can_hold"),
        score=getattr(game, "score"),
        total_lines=getattr(game, "total_lines"),
        level=getattr(game, "level"),
        gravity_interval_ms=getattr(game, "gravity_interval_ms"),
    )


def build_both_board_frames(room: Room) -> List[contract.StateFrame]:
    """Build a StateFrame for EVERY seat in ``room`` (both authoritative boards).

    Returns one :class:`contract.StateFrame` per occupied seat, each carrying its
    OWN target ``seat_id`` and per-board ``revision`` and the SHARED room
    ``room_status``. This is the native-14 "both authoritative boards" payload:
    the broadcast delivers the ENTIRE list to EVERY connected recipient so each
    peer observes both its own and the opponent's board, never only its own
    (the public pair run proved the prior broadcast sent each recipient only its
    own board). The frames are built from each seat's PRIVATE engine game; the
    list order is deterministic (``A`` before ``B``).
    """

    frames: List[contract.StateFrame] = []
    for seat_id in ("A", "B"):
        seat = room.seats.get(seat_id)
        if seat is not None:
            frames.append(build_state_frame(room.room_id, seat, room.status))
    return frames


def broadcast_room_state(room: Room) -> None:
    """Enqueue BOTH authoritative boards to BOTH connected peers, room-scoped.

    For a state transition (waiting/start, accepted own/remote movement/rotation/
    Hold, server no-input gravity) this enqueues the full both-board frame list
    onto EVERY connected seat's bounded outbound queue. Every recipient therefore
    receives a StateFrame for seat A AND one for seat B, each with its own
    ``seat_id``/``revision`` and the shared ``room_status``. Delivery is strictly
    scoped to ``room`` (no foreign seat/room is ever touched); the actual bounded
    network send is performed OUTSIDE any lock by each seat's independent writer,
    so enqueuing here is cheap and never blocks on a slow peer. A disconnected
    seat's queue is skipped (its writer has stopped); its frame still appears in
    the list delivered to the OTHER peer so a surviving peer still sees both
    boards. Enqueuing wakes each recipient's writer so a peer with no inbound
    traffic still receives the frames.
    """

    frames = build_both_board_frames(room)
    if not frames:
        return
    for seat in room.seats.values():
        if not seat.connected:
            continue
        for frame in frames:
            if not seat.enqueue_outbound(frame):
                # D3 (native-20): the bounded queue is FULL at depth 64. In a
                # STARTED room a full outbound queue is an UNAVAILABLE peer, not a
                # silently-dropped frame: mark the peer send-failed EXACTLY ONCE
                # and wake its OWN reader via the writer-gone signal
                # (``mark_send_failed`` is idempotent and sets both), so the
                # reader funnels through the central ``_forfeit_and_close`` and
                # the healthy idle peer is notified / the duel resolved exactly
                # once. A waiting / operational-abort / finished room invents NO
                # winner here (the classification is gated on ``status ==
                # "playing"``), and the 5s send bound, depth<=64 cap, once-outcome
                # guard, and terminal ordering are all unchanged. Stop enqueuing
                # further frames onto this now-unavailable peer's full queue.
                if room.status == "playing":
                    seat.mark_send_failed()
                break


def broadcast_outcome(room: Room, outcome: "gravity.OutcomeData") -> None:
    """Enqueue the terminal/forfeit ``outcome`` frame to BOTH connected peers.

    Builds the single schema-valid wire ``Outcome`` via the shared
    ``gravity.build_outcome_frame`` and enqueues it onto EVERY connected seat's
    bounded outbound queue so both peers observe the terminal/forfeit result
    (not only the seat whose coroutine happened to resolve it). Room-scoped;
    the independent writer performs the bounded send outside any lock.
    """

    frame = gravity.build_outcome_frame(room.room_id, outcome)
    for seat in room.seats.values():
        if seat.connected:
            seat.enqueue_outbound(frame)


def broadcast_terminal(room: Room, outcome: "gravity.OutcomeData") -> None:
    """Enqueue the FINAL both-board state AND the ``outcome`` frame, room-scoped.

    This is the SINGLE terminal-publication seam shared by EVERY terminal path --
    a normal gravity top-out/draw, a disconnect/1007/failed-send/full-queue
    gameplay forfeit, and a server-decided resolution. It first enqueues the
    final :class:`contract.StateFrame` for BOTH authoritative boards (so each
    surviving peer observes the terminal board state for itself AND the opponent,
    carrying the now-``finished`` ``room_status``), then the single terminal
    ``outcome`` frame, onto every CONNECTED seat's bounded outbound queue in FIFO
    order. Enqueuing wakes each recipient's independent writer, so the terminal
    frames reach a peer that is sending NOTHING further -- delivery never depends
    on a future gravity step or any additional client input. Room-scoped: no
    foreign seat/room is touched; the bounded network send happens OUTSIDE any
    lock in each seat's writer. A disconnected seat's queue is skipped (its
    writer has stopped), but its board frame still appears in the list the
    surviving peer receives, so a survivor still sees both final boards.
    """

    frames = build_both_board_frames(room)
    outcome_frame = gravity.build_outcome_frame(room.room_id, outcome)
    for seat in room.seats.values():
        if not seat.connected:
            continue
        for frame in frames:
            seat.enqueue_outbound(frame)
        seat.enqueue_outbound(outcome_frame)


# ---------------------------------------------------------------------------
# Fixed-window per-seat rate limiter (Req 22.3, 22.4). Fixed 1-second window
# counting INBOUND ACTION frames only; handshake/other frames are not counted.
# ---------------------------------------------------------------------------


class RateLimiter:
    """A fixed 1-second-window inbound-action counter (design.md rate policy).

    ``register_action(now)`` records one inbound action at monotonic ``now`` and
    returns ``True`` when the action is WITHIN the per-window budget, ``False``
    when it BREACHES it. The window is a fixed 1-second bucket aligned to
    ``floor(now)``; crossing into a new whole-second bucket resets the count. The
    limiter is pure w.r.t. an injected ``now`` so tests drive it deterministically.
    """

    def __init__(self, limit: int = contract.ACTION_RATE_PER_SEAT) -> None:
        self._limit = limit
        self._window_start: Optional[int] = None
        self._count = 0

    @property
    def limit(self) -> int:
        return self._limit

    def register_action(self, now: float) -> bool:
        """Record one inbound action at ``now``; return False on a breach."""

        bucket = int(now)  # fixed 1-second window aligned to the whole second
        if self._window_start is None or bucket != self._window_start:
            self._window_start = bucket
            self._count = 0
        self._count += 1
        return self._count <= self._limit


# ---------------------------------------------------------------------------
# Pure action decision (steps 5-8). Produces a tagged decision WITHOUT any
# transport or mutation; the endpoint turns it into a frame + optional apply.
# ---------------------------------------------------------------------------

#: Decision kinds produced by :func:`decide_cached_and_ordinal` (steps 5-6) and
#: :func:`decide_revision` (step 7). Kept as plain strings for easy testing.
DECISION_CACHED_HIT = "cached_hit"
DECISION_DUPLICATE_CONFLICT = "duplicate_conflict"
DECISION_STALE = "stale_revision"
DECISION_FUTURE = "future_revision"
DECISION_APPLY = "apply"


@dataclass(frozen=True)
class CacheOrdinalDecision:
    """Outcome of the reply-cache (step 5) + ordinal/high-water (step 6) checks.

    * ``kind == DECISION_CACHED_HIT`` -> ``cached_reply`` is the identical cached
      ``Ack``/``Reject`` to return verbatim (idempotent), nothing is re-applied.
    * ``kind == DECISION_DUPLICATE_CONFLICT`` -> reject ``duplicate_action_conflict``
      (changed fingerprint for a cached id, OR an uncached id at/below the
      high-water mark). Never applies, never advances the mark.
    * ``kind == DECISION_APPLY`` -> a NEW id (ordinal strictly above the mark):
      proceed to the revision check (step 7). ``new_high_water`` is the ordinal to
      stamp when the action is consumed.
    """

    kind: str
    cached_reply: Optional[object] = None
    new_high_water: Optional[int] = None


def decide_cached_and_ordinal(
    seat: Seat,
    action: contract.ActionMessage,
    fingerprint: Fingerprint,
) -> CacheOrdinalDecision:
    """Run the reply-cache (5) then ordinal-vs-high-water (6) checks -- PURE.

    This reads only the seat's bounded structures and the validated action; it
    mutates nothing. The endpoint applies the resulting consumption (cache put /
    high-water advance) once it has produced the reply frame.
    """

    cached = seat.reply_cache.get(action.action_id)
    if cached is not None:
        if cached.fingerprint == fingerprint:
            # Identical duplicate: return the cached reply verbatim (idempotent).
            return CacheOrdinalDecision(
                kind=DECISION_CACHED_HIT, cached_reply=cached.reply
            )
        # Same id, CHANGED fingerprint: never replaces the cache, never applies.
        return CacheOrdinalDecision(kind=DECISION_DUPLICATE_CONFLICT)

    ordinal = ordinal_of(action.action_id)
    if ordinal <= seat.last_action_seq:
        # Uncached id at or below the high-water mark (evicted-seen OR never-seen
        # skipped): already processed or superseded -> duplicate conflict.
        return CacheOrdinalDecision(kind=DECISION_DUPLICATE_CONFLICT)

    # A genuinely NEW id (ordinal strictly above the mark): proceed to apply.
    return CacheOrdinalDecision(kind=DECISION_APPLY, new_high_water=ordinal)


def decide_revision(seat: Seat, expected_revision: int) -> str:
    """Step 7: STRICT equality of ``expected_revision`` vs authoritative revision.

    Returns ``DECISION_STALE`` for a LOWER value, ``DECISION_FUTURE`` for a HIGHER
    value, and ``DECISION_APPLY`` for an exact match. Neither rejection mutates
    the board (the endpoint does not call the engine on a stale/future decision).
    """

    if expected_revision < seat.revision:
        return DECISION_STALE
    if expected_revision > seat.revision:
        return DECISION_FUTURE
    return DECISION_APPLY


#: Map an action ``kind`` to the pure engine mutation applied to the seat's game.
_ACTION_APPLIERS: Dict[str, Callable[[object], None]] = {
    "left": lambda g: engine.move(g, "left"),
    "right": lambda g: engine.move(g, "right"),
    "down": lambda g: engine.move(g, "down"),
    "cw": lambda g: engine.rotate(g, "cw"),
    "ccw": lambda g: engine.rotate(g, "ccw"),
    "hold": engine.hold,
}


def _board_identity(game: object) -> tuple:
    """Return a cheap comparable fingerprint of the observable board state.

    Mirrors the gravity module's change detection so an applied action bumps the
    per-board revision ONLY on a real observable change (a legal but
    nothing-changed action is a NO-OP). Captures the fields any action can move:
    board status, active-piece origin/cells/orientation, the full settled board,
    and the lock-derived counters (score/total_lines/level/can_hold/hold_type).
    """

    active = getattr(game, "active", None)
    if active is None:
        active_identity: object = None
    else:
        active_identity = (
            active.type,
            tuple(active.origin),
            tuple(tuple(cell) for cell in active.cells),
            active.orientation,
        )
    board = getattr(game, "board")
    return (
        getattr(game, "status", None),
        active_identity,
        tuple(tuple(row) for row in board),
        getattr(game, "score", None),
        getattr(game, "total_lines", None),
        getattr(game, "level", None),
        getattr(game, "can_hold", None),
        getattr(game, "hold_type", None),
    )


def apply_action_to_seat(seat: Seat, kind: str) -> bool:
    """Apply a validated action to the seat's PRIVATE game; return changed?.

    Returns ``True`` when the action produced an observable board change (the
    caller bumps ``revision`` by one and emits a fresh ``state`` frame), ``False``
    on a legal NO-OP (the caller acks ``no_op=True`` with the UNCHANGED revision).
    Only the sender's own private game is ever mutated.
    """

    before = _board_identity(seat.game)
    _ACTION_APPLIERS[kind](seat.game)
    after = _board_identity(seat.game)
    return after != before


# ---------------------------------------------------------------------------
# Scalar-overflow guard (Req 21.1). An applied action must never drive a scalar
# past its documented ceiling; if it would, the endpoint performs an OPERATIONAL
# ABORT (1001 ``scalar_overflow``) rather than emitting a schema-invalid number.
# ---------------------------------------------------------------------------


def seat_scalar_overflow(seat: Seat) -> bool:
    """Return True iff any authoritative scalar is past its documented ceiling.

    Checks the per-board ``revision``/``score``/``total_lines`` against the safe
    integer ceiling and ``level`` against its max. Used AFTER an apply/gravity
    step so the endpoint can abort with ``scalar_overflow`` instead of ever
    emitting an out-of-range scalar in a frame.
    """

    game = seat.game
    if seat.revision > contract.SAFE_INT_MAX:
        return True
    if getattr(game, "score", 0) > contract.SAFE_INT_MAX:
        return True
    if getattr(game, "total_lines", 0) > contract.SAFE_INT_MAX:
        return True
    if getattr(game, "level", 1) > contract.LEVEL_MAX:
        return True
    return False


def would_scalar_overflow(seat: Seat, changed: bool) -> bool:
    """Return True iff committing this applied action WOULD overflow a scalar.

    This is the PRE-COMMIT guard the endpoint uses at step 8 (task 30.3): it is
    evaluated AFTER ``apply_action_to_seat`` mutated the private game but BEFORE
    the endpoint bumps the authoritative ``revision`` or builds any ack/state
    frame. It inspects the post-apply game scalars (``score``/``total_lines``
    against the safe-integer ceiling, ``level`` against its max) AND the WOULD-BE
    revision -- ``seat.revision + 1`` when the action produced a real change,
    otherwise the unchanged revision -- against the safe-integer ceiling. Because
    it tests the would-be revision rather than a revision already bumped, a value
    that WOULD overflow is caught BEFORE it becomes authoritative, so the server
    never commits or emits an out-of-range ``revision``/state. The gameplay
    semantics are unchanged for every non-overflowing action.
    """

    would_be_revision = seat.revision + 1 if changed else seat.revision
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


# ---------------------------------------------------------------------------
# Frame constructors for the ack/reject replies (bounded, schema-valid).
# ---------------------------------------------------------------------------


def make_ack(
    room_id: str, seat_id: str, action_id: str, revision: int, no_op: bool
) -> contract.Ack:
    """Build an ``ack`` frame (always an acceptance; ``applied`` const True)."""

    return contract.Ack(
        type="ack",
        room_id=room_id,
        seat_id=seat_id,
        action_id=action_id,
        revision=revision,
        no_op=no_op,
    )


def make_reject(
    room_id: str,
    seat_id: str,
    action_id: str,
    reason: contract.RejectReason,
    authoritative_revision: int,
) -> contract.Reject:
    """Build a ``reject`` frame with a stable machine-readable reason."""

    return contract.Reject(
        type="reject",
        room_id=room_id,
        seat_id=seat_id,
        action_id=action_id,
        reason=reason,
        authoritative_revision=authoritative_revision,
    )


def make_error(
    reason: contract.ErrorReason,
    detail: str,
    room_id: Optional[str] = None,
    seat_id: Optional[str] = None,
) -> contract.ErrorFrame:
    """Build an ``error`` frame (no ``action_id``) with a short English detail.

    ``detail`` is a short fixed English string; it never carries a filesystem
    path, SQL text, an exception/class name, or a stack trace (Req 21.6).
    """

    return contract.ErrorFrame(
        type="error",
        room_id=room_id,
        seat_id=seat_id,
        reason=reason,
        detail=detail,
    )


# Short, fixed, internals-free English detail strings (Req 21.6).
_DETAIL_MALFORMED = "Malformed message."
_DETAIL_ROOM_FULL = "Room is full."
_DETAIL_ROOM_CLOSED = "Room is closed."
_DETAIL_ROOM_CAPACITY = "Server is at capacity."
_DETAIL_BAD_VERSION = "Unsupported protocol version."
_DETAIL_HANDSHAKE_TIMEOUT = "Handshake timed out."
_DETAIL_INTERNAL = "Internal error."

#: Bounded number of cooperative event-loop turns the reader waits for the
#: independent writer to flush an enqueued reply before giving up this flush
#: cycle. It is a BOUND, not a retry of any send: each send is attempted exactly
#: once by the writer under its own 5s timeout. This only governs how long the
#: reader yields so the single writer can run; it never re-sends a frame.
_FLUSH_MAX_TURNS = 1000


# ---------------------------------------------------------------------------
# The endpoint. A thin transport shell over the pure helpers above. It is a
# callable bound to a lifespan-owned RoomManager (task 15.1 wires it); all
# timing uses the manager's injectable clock so tests stay deterministic.
# ---------------------------------------------------------------------------


class DuelEndpoint:
    """The ``/ws/duel`` connection handler bound to a shared ``RoomManager``.

    One instance is created by the app/lifespan (task 15.1) with the single
    lifespan-owned manager and the resolved Origin allow-list; the instance is
    reused for every connection. Per-connection mutable state lives in locals, so
    the instance holds no per-socket state and is safe to share.
    """

    def __init__(
        self,
        manager: RoomManager,
        allowed_origins: Optional[Tuple[str, ...]] = None,
    ) -> None:
        self._manager = manager
        self._allowed_origins = (
            allowed_origins
            if allowed_origins is not None
            else resolve_ws_allowed_origins()
        )

    @property
    def allowed_origins(self) -> Tuple[str, ...]:
        return self._allowed_origins

    # -- outbound I/O (OUTSIDE any room lock) ------------------------------

    async def _send_frame(self, websocket: WebSocket, frame: object) -> bool:
        """Send one schema-valid frame as JSON text; return False on send failure.

        A send that raises (closed/broken peer) is a FAILED SEND: it returns
        ``False`` so the caller classifies the peer as unavailable. The frame is a
        validated contract model, so ``model_dump`` never yields a schema-invalid
        scalar. Serialization happens here, outside any room lock.
        """

        try:
            payload = frame.model_dump(mode="json")
            await websocket.send_text(json.dumps(payload))
            return True
        except Exception:
            # A broken/closed peer: treat as a failed send (Req 22.3 slow peer).
            return False

    async def _send_frame_bounded(self, websocket: WebSocket, frame: object) -> bool:
        """Send one frame under the 5s outbound bound; return False on failure.

        Wraps :meth:`_send_frame` in a single ``asyncio.wait_for`` with the
        documented :data:`contract.OUTBOUND_SEND_TIMEOUT_S` bound. A send that
        raises OR exceeds the bound is a FAILED send (``False``) -- there are NO
        retries, so a slow/blocked peer breaches the bound exactly once and is
        then classified unavailable rather than retried unbounded.
        """

        try:
            return await asyncio.wait_for(
                self._send_frame(websocket, frame),
                timeout=contract.OUTBOUND_SEND_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, TimeoutError):
            # Breached the 5s send bound: a slow/blocked peer, treated as failed.
            return False

    async def _run_writer(self, websocket: WebSocket, seat: Seat) -> None:
        """The SINGLE independent writer task for one connection (native 14).

        This coroutine is the ONLY writer for ``seat``'s socket. It runs
        concurrently with the reader (``_run_action_loop``) and flushes the
        seat's bounded outbound queue in FIFO order WITHOUT requiring any
        recipient inbound traffic: it awaits the seat's wakeup signal, drains the
        queue, and sends each frame under the bounded 5s send timeout. This is
        what finally delivers the waiting peer's ``room_status: "playing"`` start
        frame (and every traffic-free gravity/outcome/cleanup frame) to a peer
        that is sending nothing.

        Bounds/lifecycle: the queue is the bounded depth-64 ``deque``; each send
        is bounded by 5s; there are NO unbounded task/queue/send retries. On a
        failed/timed-out send the writer sets ``seat.send_failed`` and stops
        (the owning coroutine turns that into a slow-peer forfeit / cleanup), so
        one slow peer fills only its own queue and blocks neither the other peer
        nor the worker. ``CancelledError`` is re-raised so teardown cancellation
        actually reaches and unwinds this task (it is never swallowed).
        """

        signal = seat.outbound_signal()
        try:
            while True:
                # Drain everything already queued FIRST (FIFO, bounded).
                frames = seat.drain_outbound()
                for frame in frames:
                    if not await self._send_frame_bounded(websocket, frame):
                        # A failed/timed-out send: record it AND wake the blocked
                        # reader (native 19 F2). ``mark_send_failed`` sets both
                        # ``send_failed`` (the acting-peer classification) and the
                        # writer-gone signal, so a reader blocked on
                        # ``websocket.receive()`` -- the idle peer, or the acting
                        # peer whose ``_flush_and_check`` already returned while
                        # this send was still in flight -- wakes immediately and
                        # triggers the central forfeit/cleanup WITHOUT another
                        # flush. No retry: the writer stops here.
                        seat.mark_send_failed()
                        return
                # A pending writer-driven close directive (a ROOM-WIDE
                # operational abort signalled to THIS peer by the OTHER seat,
                # task 30.3) takes effect AFTER the already-queued frames drain:
                # close this socket with the standard code + LITERAL reason and
                # stop. This closes the peer for the whole room with NO fabricated
                # gameplay outcome and WITHOUT requiring this peer's inbound
                # traffic. After closing, wake the blocked reader so its
                # ``websocket.receive()`` unblocks and the connection tears down
                # through the single ordered writer/socket (no concurrent close).
                directive = seat.close_directive
                if directive is not None:
                    code, reason = directive
                    await self._close(websocket, code, reason)
                    seat.signal_writer_gone()
                    return
                if seat.outbound_closed and not seat.outbound:
                    # Channel closed and fully drained: exit with no leaked task.
                    return
                # Nothing left: wait to be woken by the next enqueue/close. The
                # wait itself is cancellable so teardown unwinds immediately.
                await signal.wait()
                signal.clear()
        except asyncio.CancelledError:
            # Teardown cancellation must REACH this writer and propagate so the
            # awaiting owner's ``await`` returns; never silently swallow it.
            raise

    async def _flush_and_check(self, seat: Seat) -> bool:
        """Yield to the writer so it flushes ``seat``'s queue; return ok?.

        The reader path enqueues a reply then calls this to let the independent
        writer drain it and to observe whether delivery failed. It returns
        ``False`` once the writer has recorded a failed/timed-out send (the
        caller classifies the peer as unavailable), ``True`` otherwise. It never
        performs socket I/O itself -- the single writer owns every send.
        """

        if seat.send_failed:
            return False
        # Cooperatively yield until the writer has drained what we enqueued (or
        # recorded a failure). The writer wakes on the enqueue signal; a bounded
        # number of event-loop turns lets it run without a busy spin.
        for _ in range(_FLUSH_MAX_TURNS):
            if seat.send_failed:
                return False
            if not seat.outbound:
                return True
            await asyncio.sleep(0)
        return not seat.send_failed

    # -- close helpers -----------------------------------------------------

    async def _close(self, websocket: WebSocket, code: int, reason: str) -> None:
        """Close the socket with a standard code and a LITERAL reason string.

        Swallows a secondary error if the socket is already closing/closed, so a
        cleanup close never raises back into the worker.
        """

        try:
            if websocket.application_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=code, reason=reason)
        except Exception:
            # Already closing/closed; nothing further to do.
            pass

    # -- the connection coroutine -----------------------------------------

    async def _start_writer(self, websocket: WebSocket, seat: Seat) -> "asyncio.Task":
        """Create and return the SINGLE independent writer task for ``seat``.

        Bound to the current running loop; the returned task is owned by
        :meth:`__call__` and is cancelled + awaited on EVERY teardown path so no
        writer task is leaked. Creating the event here (via ``outbound_signal``)
        binds the seat's wakeup signal to this loop before any enqueue races it.
        """

        seat.outbound_signal()  # bind the wakeup event to this loop up front
        return asyncio.create_task(self._run_writer(websocket, seat))

    async def _teardown_writer(
        self, seat: Optional[Seat], writer: "Optional[asyncio.Task]"
    ) -> None:
        """Cancel + await the writer task on teardown; never leak or swallow.

        Closes the seat's outbound channel (so a cleanly-draining writer can
        exit), then cancels and AWAITS the writer so its cancellation actually
        completes before the connection coroutine returns. ``CancelledError`` from
        awaiting the cancelled writer is expected here and is absorbed at THIS
        boundary only (the writer itself re-raised it, so cancellation did reach
        it) -- a stray ``CancelledError`` targeting THIS coroutine is re-raised so
        an outer shutdown cancellation is never silently swallowed.
        """

        if seat is not None:
            seat.close_outbound()
        if writer is None:
            return
        writer.cancel()
        # Await the cancelled writer so its cancellation actually completes before
        # this coroutine returns. ``asyncio.wait`` (not a bare ``await writer``)
        # lets us observe the writer's completion WITHOUT re-raising its expected
        # CancelledError into this teardown boundary, while any CancelledError
        # aimed at THIS coroutine still propagates normally from the caller.
        await asyncio.wait({writer})

    async def __call__(self, websocket: WebSocket) -> None:
        """Handle a single ``/ws/duel`` connection end to end.

        Flow: Origin check (pre-accept, HTTP-level) -> accept -> handshake
        (``hello`` -> ``welcome`` + waiting ``state``) -> start the INDEPENDENT
        per-connection writer -> gate start on both seats -> action loop (reader)
        running CONCURRENTLY with the writer -> terminal/cleanup that cancels and
        awaits BOTH the reader and the writer. Every terminal path releases the
        room entry and funnels resolution through the set-once guard so a duel
        resolves exactly once and leaks no task/socket/room.
        """

        # (Req 22.1) Origin check BEFORE accept: closing pre-accept rejects the
        # HTTP upgrade (HTTP 403), so the request never becomes a WebSocket and no
        # WebSocket CLOSE frame is emitted for a disallowed origin.
        origin = websocket.headers.get("origin")
        if not origin_is_allowed(origin, self._allowed_origins):
            await websocket.close(code=contract.CLOSE_CODE_POLICY)
            return

        await websocket.accept()

        room: Optional[Room] = None
        seat: Optional[Seat] = None
        writer: Optional[asyncio.Task] = None
        try:
            handshake = await self._run_handshake(websocket)
            if handshake is None:
                return
            room, seat, writer = handshake

            await self._run_action_loop(websocket, room, seat)
        except WebSocketDisconnect:
            # Peer went away (includes a transport 1007 close): ordinary
            # disconnect/forfeit/once-only cleanup. A waiting-alone disconnect
            # fabricates no winner.
            self._handle_disconnect(room, seat)
        except asyncio.CancelledError:
            # Shutdown/teardown cancellation of the whole connection: unwind the
            # writer, release the room, then RE-RAISE so cancellation reaches the
            # lifespan/task that cancelled us (never silently swallowed).
            self._handle_disconnect(room, seat)
            await self._teardown_writer(seat, writer)
            await self._close(
                websocket,
                contract.CLOSE_CODE_GOING_AWAY,
                contract.CLOSE_REASON_SERVER_SHUTDOWN,
            )
            raise
        except Exception:
            # Never leak an exception/stack; close with a bounded internal error.
            if room is not None and seat is not None:
                seat.enqueue_outbound(
                    make_error(
                        "internal", _DETAIL_INTERNAL, room.room_id, seat.seat_id
                    )
                )
                await self._flush_and_check(seat)
            self._handle_disconnect(room, seat)
            await self._close(
                websocket,
                contract.CLOSE_CODE_GOING_AWAY,
                contract.CLOSE_REASON_SERVER_SHUTDOWN,
            )
        finally:
            # Teardown ALWAYS cancels + awaits the independent writer so neither
            # the reader nor the writer task is ever leaked (native 14 lifecycle).
            await self._teardown_writer(seat, writer)

    # -- handshake ---------------------------------------------------------

    async def _run_handshake(
        self, websocket: WebSocket
    ) -> Optional[Tuple[Room, Seat, "asyncio.Task"]]:
        """Run ``hello`` -> ``welcome`` + waiting ``state``; assign a seat.

        Returns ``(room, seat, writer)`` on success -- the ``writer`` is the
        started independent per-connection writer task, owned/torn down by
        :meth:`__call__`. Returns ``None`` when the connection was closed during
        the handshake (bad version, malformed hello, room full / closed /
        at-capacity, or handshake timeout). Pre-seat failures are sent directly
        (no writer/seat exists yet); once a seat is assigned the writer is
        started and ALL subsequent frames flow through it. The handshake is
        bounded by the handshake timeout; a timeout closes 1001
        ``handshake_timeout``.
        """

        try:
            raw, oversize, is_binary = await self._receive_text_or_timeout(
                websocket, self._manager.handshake_timeout
            )
        except TimeoutError:
            await self._close(
                websocket,
                contract.CLOSE_CODE_GOING_AWAY,
                contract.CLOSE_REASON_HANDSHAKE_TIMEOUT,
            )
            return None

        if oversize:
            # (Req 20.3, 20.11, 22.4) The FIRST Hello/handshake is bounded by the
            # SAME 4096 UTF-8 byte limit as every post-handshake action, applied
            # BEFORE any JSON/model parse. An oversize Hello closes with the
            # STANDARD oversize code 1009 (not the 1008 malformed/policy close);
            # the frame is never buffered whole past the bound and no seat exists
            # yet, so nothing further is enqueued.
            await self._close(
                websocket,
                contract.CLOSE_CODE_OVERSIZE,
                "oversize",
            )
            return None

        if is_binary or raw is None:
            # A non-text (binary) or absent handshake frame is malformed. (This is
            # reached only for an IN-BOUND frame: an oversize binary first frame is
            # already classified oversize above and closed 1009.)
            await self._send_frame(
                websocket, make_error("malformed_message", _DETAIL_MALFORMED)
            )
            await self._close(
                websocket, contract.CLOSE_CODE_POLICY, _DETAIL_MALFORMED
            )
            return None

        hello = self._parse_hello(raw)
        if hello is None:
            await self._send_frame(
                websocket, make_error("malformed_message", _DETAIL_MALFORMED)
            )
            await self._close(
                websocket, contract.CLOSE_CODE_POLICY, _DETAIL_MALFORMED
            )
            return None

        # Assign a seat (bounded by max_rooms). Map each bounded room error to
        # its stable ErrorFrame reason; none leaks any internals.
        try:
            room, seat = self._manager.assign_seat(hello.room_id, origin=None)
        except RoomFullError:
            await self._send_frame(
                websocket, make_error("room_full", _DETAIL_ROOM_FULL, hello.room_id)
            )
            await self._close(websocket, contract.CLOSE_CODE_POLICY, "room_full")
            return None
        except RoomClosedError:
            await self._send_frame(
                websocket,
                make_error("room_closed", _DETAIL_ROOM_CLOSED, hello.room_id),
            )
            await self._close(websocket, contract.CLOSE_CODE_POLICY, "room_closed")
            return None
        except (RoomCapacityError, ValueError):
            await self._send_frame(
                websocket,
                make_error("room_closed", _DETAIL_ROOM_CAPACITY, hello.room_id),
            )
            await self._close(websocket, contract.CLOSE_CODE_POLICY, "room_full")
            return None

        # A seat exists now: start the SINGLE independent writer for this socket
        # BEFORE enqueuing any frame so every frame (including the traffic-free
        # start frame enqueued by the PEER's handshake) is delivered by the writer
        # without requiring this peer's inbound traffic.
        writer = await self._start_writer(websocket, seat)

        # welcome (room_status reflects the room at assignment time) + the
        # mandatory waiting broadcast: BOTH currently-present authoritative
        # boards to BOTH connected peers (native-14). While seat A is alone the
        # list is just A's board; once B is present each peer's waiting
        # broadcast carries both boards. The welcome is seat-targeted; the state
        # broadcast is room-scoped.
        seat.enqueue_outbound(
            contract.Welcome(
                type="welcome",
                room_id=room.room_id,
                seat_id=seat.seat_id,
                room_status=room.status,
            )
        )
        # Try to start the room now that this seat is present. If it is still
        # waiting afterwards (this seat joined alone), broadcast the waiting
        # transition (both currently-present boards to both peers -- just this
        # seat while alone). If the room started, the start broadcast below
        # supersedes a redundant waiting frame, so emit only the playing
        # transition.
        started = self._maybe_start_room(room)
        if not started:
            broadcast_room_state(room)
            if not await self._flush_and_check(seat):
                self._handle_disconnect(room, seat)
                await self._teardown_writer(seat, writer)
                return None
        else:
            # The second seat completed the room: broadcast the playing-state
            # transition -- BOTH authoritative boards to BOTH peers. The peer's
            # frames are enqueued on the PEER seat and flushed by the PEER's own
            # independent writer, so a waiting peer with no inbound traffic
            # finally receives the start frame AND the opponent's board.
            await self._emit_room_state_to_owner(websocket, room, seat)
            if seat.send_failed:
                self._handle_disconnect(room, seat)
                await self._teardown_writer(seat, writer)
                return None

        return room, seat, writer

    def _parse_hello(self, raw: str) -> Optional[contract.Hello]:
        """Parse + validate a ``hello`` frame; return None if malformed."""

        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            hello = contract.Hello(**data)
        except (ValidationError, TypeError):
            return None
        return hello

    def _maybe_start_room(self, room: Room) -> bool:
        """Transition a full, connected room from ``waiting`` to ``playing`` once.

        Seeds each seat's gravity due time from the manager clock so per-board
        gravity (task 13.1/15.1) advances from the start instant. Starting is
        idempotent: a room already ``playing``/``finished`` is left untouched.
        Returns ``True`` iff THIS call performed the waiting -> playing
        transition (so the caller broadcasts the start transition exactly once);
        ``False`` when the room was not started by this call.
        """

        if room.status != "waiting" or not room.both_connected():
            return False
        now = self._manager.clock()
        with room.state_lock:
            if room.status != "waiting" or not room.both_connected():
                return False
            room.status = "playing"
            for s in room.seats.values():
                s.gravity_due_monotonic = now + gravity._current_interval_seconds(s)
        self._manager.mark_activity(room)
        return True

    async def _emit_room_state_to_owner(
        self, websocket: WebSocket, room: Room, seat: Seat
    ) -> None:
        """Broadcast the start transition: BOTH boards to BOTH peers (native-14).

        After a start transition both seats must observe ``room_status:
        "playing"`` AND both authoritative boards. The broadcast enqueues the
        full both-board frame list onto EVERY connected seat's queue; each peer's
        own independent writer flushes it, so a waiting peer with no inbound
        traffic still receives the start frame and the opponent's board.
        Enqueuing SETS each recipient's wakeup signal (the native-14 delivery fix
        for the blocked-reader start-broadcast blocker). This owner-side call
        then yields so the owner's writer drains the owner's copy promptly.
        """

        if room.status == "playing":
            broadcast_room_state(room)
            await self._flush_and_check(seat)

    # -- action loop -------------------------------------------------------

    async def _run_action_loop(
        self, websocket: WebSocket, room: Room, seat: Seat
    ) -> None:
        """Receive and process inbound frames until disconnect or terminal close.

        Each iteration bounds the inbound size (1009 oversize), parses the frame,
        runs the ordered check sequence for an action, drains the resulting
        outbound frames, and checks for a terminal outcome. A full outbound queue
        or failed send in a STARTED room is a gameplay forfeit.
        """

        rate = RateLimiter(self._manager.action_rate_per_seat)

        while True:
            # Receive the next inbound frame, but RACE it against this seat's
            # writer-gone signal (native 19 F2). If the independent writer has
            # already recorded a failed/timed-out send (new OR cached ACK,
            # in-flight-send breach, full queue) OR completed a directed close
            # while this reader was blocked on ``websocket.receive()``, the race
            # returns immediately so the blocked reader WAKES and funnels through
            # the central forfeit/cleanup WITHOUT waiting for another
            # ``_flush_and_check``. This is what finally forfeits the IDLE peer
            # (which sends nothing) and the acting peer whose send only failed
            # after its flush already returned. The receive itself is still a
            # single ordered socket read; only the WAIT is made cancellable by
            # the writer so no concurrent/unsynchronized receive occurs.
            message = await self._receive_or_writer_gone(websocket, seat)
            if message is None:
                # The writer is gone (failed send or directed close) while the
                # reader was blocked. Route through the SINGLE ordered close path
                # rather than racing a concurrent send/close.
                if seat.close_directive is not None or room.operational_abort is not None:
                    # A directed operational-abort close already happened on the
                    # writer; the room was released by the acting seat. Just tear
                    # down this connection (teardown awaits the writer).
                    self._handle_disconnect(room, seat)
                    return
                # A failed/timed-out send: central forfeit/cleanup, no re-flush.
                await self._forfeit_and_close(websocket, room, seat)
                return

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))

            raw, oversize, is_binary = self._extract_inbound(message)

            if oversize:
                # (Req 22.4) Oversize -> 1009; bounded, never buffered whole.
                await self._close(
                    websocket,
                    contract.CLOSE_CODE_OVERSIZE,
                    "oversize",
                )
                self._handle_disconnect(room, seat)
                return

            if is_binary or raw is None:
                # In-band binary frame or non-text: application-visible malformed.
                seat.enqueue_outbound(
                    make_error(
                        "malformed_message",
                        _DETAIL_MALFORMED,
                        room.room_id,
                        seat.seat_id,
                    )
                )
                if not await self._flush_and_check(seat):
                    self._handle_disconnect(room, seat)
                    return
                continue

            handled = await self._process_inbound(websocket, room, seat, raw, rate)
            if not handled:
                # Terminal/cleanup already performed inside the handler.
                return

            if self._check_and_emit_terminal(websocket, room):
                await self._finish_and_close(websocket, room, seat)
                return

    def _extract_inbound(
        self, message: dict
    ) -> Tuple[Optional[str], bool, bool]:
        """Classify a raw ASGI websocket.receive message.

        Returns ``(text_or_none, oversize, is_binary)``. Oversize is measured on
        the UTF-8 byte length against ``max_msg_bytes`` so the bound is on the
        wire size, not the character count. A binary (``bytes``) frame is flagged
        ``is_binary`` (an in-band binary frame is application-visible malformed).
        """

        text = message.get("text")
        data = message.get("bytes")
        if text is not None:
            if len(text.encode("utf-8")) > self._manager.max_msg_bytes:
                return None, True, False
            return text, False, False
        if data is not None:
            if len(data) > self._manager.max_msg_bytes:
                return None, True, True
            return None, False, True
        return None, False, False

    async def _process_inbound(
        self,
        websocket: WebSocket,
        room: Room,
        seat: Seat,
        raw: str,
        rate: RateLimiter,
    ) -> bool:
        """Parse one inbound TEXT frame and run the ordered check sequence.

        Returns ``True`` to keep the loop running, ``False`` when a terminal
        close + cleanup was already performed (rate-limit close, failed send, or
        scalar overflow). Non-action well-formed frames after the handshake are
        treated as malformed (only actions are expected post-handshake).
        """

        # (1) schema/format. First decode JSON; invalid JSON is malformed.
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return await self._reply_malformed(websocket, room, seat)
        if not isinstance(data, dict):
            return await self._reply_malformed(websocket, room, seat)

        msg_type = data.get("type")
        if msg_type != "action":
            # A non-action frame (including a second hello) is uncorrelatable
            # here: it has no action to echo -> malformed_message.
            return await self._reply_malformed(websocket, room, seat)

        # SEQUENCE EXHAUSTION (OPERATIONAL ABORT, task 30.3). The maximum valid
        # ordinal 999999999999999 is CONSUMABLE; the NEXT higher ordinal cannot
        # be represented under the 1..15-digit grammar, so ``ActionMessage``
        # would reject it as a plain grammar violation. Detect that specific
        # overflow case FIRST -- a clean "A-"/"B-" prefix (matching THIS seat)
        # followed by a leading-zero-free 16+-digit decimal -- and treat it as a
        # ROOM-WIDE operational abort: close BOTH peers with code 1001 + the
        # literal reason "sequence_exhausted" and fabricate NO gameplay winner,
        # rather than emitting a schema reject or overflowing. This is checked
        # only for the sender's OWN seat (its own exhausted sequence); an id
        # naming the OTHER seat is not this seat's exhaustion and falls through to
        # the ordinary ownership/schema handling.
        if is_sequence_exhausted_id(seat.seat_id, data.get("action_id")):
            await self._operational_abort_and_close(
                websocket, room, seat, contract.CLOSE_REASON_SEQUENCE_EXHAUSTED
            )
            return False

        # Parse as an ActionMessage. A failure here may still carry a valid
        # canonical action_id to echo (bad_type/missing_field/extra_field), so we
        # distinguish an echoable schema error from an uncorrelatable one.
        try:
            action = contract.ActionMessage(**data)
        except ValidationError:
            return await self._reply_schema_error(websocket, room, seat, data)
        except TypeError:
            return await self._reply_malformed(websocket, room, seat)

        # (2) seat ownership: the sender must own the targeted seat. The contract
        # model already pins the action_id prefix to seat_id; here we enforce that
        # the targeted seat_id is THIS connection's seat.
        if action.seat_id != seat.seat_id:
            reject = make_reject(
                room.room_id,
                seat.seat_id,
                action.action_id,
                "not_seat_owner",
                seat.revision,
            )
            return await self._emit_reply(websocket, room, seat, reject)

        # (3) rate limit (fixed 1-second window, inbound actions only). A breach
        # emits a bounded Reject(rate_limited) and then closes 1008 rate_limited.
        if not rate.register_action(self._manager.clock()):
            seat.enqueue_outbound(
                make_reject(
                    room.room_id,
                    seat.seat_id,
                    action.action_id,
                    "rate_limited",
                    seat.revision,
                )
            )
            await self._flush_and_check(seat)
            await self._close(
                websocket,
                contract.CLOSE_CODE_POLICY,
                contract.CLOSE_REASON_RATE_LIMITED,
            )
            self._handle_disconnect(room, seat)
            return False

        # (4) room-status/start gate: an action while waiting is not_started and
        # does NOT consume the ordinal/high-water mark and is NOT cached.
        if room.status != "playing":
            reject = make_reject(
                room.room_id,
                seat.seat_id,
                action.action_id,
                "not_started",
                seat.revision,
            )
            # Emit WITHOUT caching / advancing the mark (deliberate exception).
            return await self._emit_reply(
                websocket, room, seat, reject, cache=False
            )

        # (5)+(6) reply cache + ordinal vs high-water mark.
        fingerprint = build_fingerprint(action)
        decision = decide_cached_and_ordinal(seat, action, fingerprint)

        if decision.kind == DECISION_CACHED_HIT:
            return await self._emit_cached(
                websocket, room, seat, decision.cached_reply
            )
        if decision.kind == DECISION_DUPLICATE_CONFLICT:
            reject = make_reject(
                room.room_id,
                seat.seat_id,
                action.action_id,
                "duplicate_action_conflict",
                seat.revision,
            )
            # A duplicate conflict is NOT a fresh consumption: do not advance the
            # mark and do not cache (the original cached entry, if any, stands).
            return await self._emit_reply(
                websocket, room, seat, reject, cache=False
            )

        # (7) strict expected_revision equality.
        rev_decision = decide_revision(seat, action.expected_revision)
        if rev_decision == DECISION_STALE or rev_decision == DECISION_FUTURE:
            reason = (
                "stale_revision"
                if rev_decision == DECISION_STALE
                else "future_revision"
            )
            reject = make_reject(
                room.room_id,
                seat.seat_id,
                action.action_id,
                reason,
                seat.revision,
            )
            # A NEW id that is stale/future STILL consumes the ordinal and is
            # cached, so it can never later become newly applied.
            self._consume(seat, action.action_id, fingerprint, reject, decision)
            return await self._emit_reply(
                websocket, room, seat, reject, cache=False
            )

        # (8) apply to the sender's private board.
        changed = apply_action_to_seat(seat, action.kind)

        # Scalar-overflow guard (OPERATIONAL ABORT, task 30.3): decide BEFORE
        # committing the revision bump or emitting any frame. ``would_overflow``
        # inspects the post-apply game scalars AND the WOULD-BE revision (the
        # current revision + 1 on a real change) against their ceilings, so a
        # scalar that WOULD overflow never becomes the authoritative revision and
        # is never emitted in a state/ack frame. On overflow the room aborts for
        # BOTH peers with code 1001 + the literal reason ``"scalar_overflow"`` and
        # NO fabricated gameplay winner -- it is NOT a disconnect/forfeit.
        if would_scalar_overflow(seat, changed):
            await self._operational_abort_and_close(
                websocket, room, seat, contract.CLOSE_REASON_SCALAR_OVERFLOW
            )
            return False

        if changed:
            seat.revision += 1

        ack = make_ack(
            room.room_id,
            seat.seat_id,
            action.action_id,
            seat.revision,
            no_op=not changed,
        )
        # A new applied/no-op id consumes the ordinal and is cached.
        self._consume(seat, action.action_id, fingerprint, ack, decision)
        self._manager.mark_activity(room)

        # Emit the ack to the ACTING seat, then on a real change broadcast BOTH
        # authoritative boards to BOTH connected peers (native-14): the acting
        # seat sees its own bumped board and the opponent sees the remote
        # accepted movement/rotation/Hold. A legal no-op broadcasts nothing (the
        # ack already carries the unchanged revision).
        seat.enqueue_outbound(ack)
        if changed:
            broadcast_room_state(room)
        if not await self._flush_and_check(seat):
            await self._forfeit_and_close(websocket, room, seat)
            return False
        return True

    # -- consumption / reply emission -------------------------------------

    def _consume(
        self,
        seat: Seat,
        action_id: str,
        fingerprint: Fingerprint,
        reply: object,
        decision: CacheOrdinalDecision,
    ) -> None:
        """Consume a NEW id: advance the high-water mark and cache the reply.

        Only called for a genuinely new id (ordinal strictly above the mark).
        Advances ``last_action_seq`` monotonically to the new ordinal and stores
        the (fingerprint, reply) in the bounded reply cache.
        """

        if decision.new_high_water is not None:
            if decision.new_high_water > seat.last_action_seq:
                seat.last_action_seq = decision.new_high_water
        seat.reply_cache.put(action_id, fingerprint, reply)

    async def _emit_reply(
        self,
        websocket: WebSocket,
        room: Room,
        seat: Seat,
        reply: object,
        *,
        cache: bool = True,
    ) -> bool:
        """Enqueue + drain a single ack/reject reply; classify a failed send.

        When ``cache`` is True the reply is NOT separately cached here (callers
        that need caching call :meth:`_consume` explicitly to also advance the
        mark); this method only performs the bounded outbound I/O. Returns
        ``True`` to continue the loop, ``False`` after a forfeit-close on a failed
        send in a started room.
        """

        seat.enqueue_outbound(reply)
        if not await self._flush_and_check(seat):
            await self._forfeit_and_close(websocket, room, seat)
            return False
        return True

    async def _emit_cached(
        self, websocket: WebSocket, room: Room, seat: Seat, reply: object
    ) -> bool:
        """Emit a cached reply verbatim through the SINGLE bounded writer.

        Delivers the cached ``Ack``/``Reject`` idempotently (nothing is
        re-applied) via the same independent writer as every other frame. Unlike
        the prior ``drain_result or True`` -- which PRETENDED a failed cached send
        succeeded -- a failed/timed-out cached send is reported HONESTLY: it is
        classified as a slow-peer failure and, in a STARTED room, triggers the
        one-time ``peer_unavailable_forfeit`` just like any other failed send
        (native 14 correction). Returns ``True`` to continue the loop, ``False``
        after the forfeit/cleanup close.
        """

        seat.enqueue_outbound(reply)
        if not await self._flush_and_check(seat):
            await self._forfeit_and_close(websocket, room, seat)
            return False
        return True

    async def _reply_malformed(
        self, websocket: WebSocket, room: Room, seat: Seat
    ) -> bool:
        """Answer an uncorrelatable malformed message with an ``ErrorFrame``.

        The error carries ``reason: "malformed_message"`` and NO ``action_id``
        (an invented id is forbidden). It never burns the seat's sequence.
        """

        seat.enqueue_outbound(
            make_error(
                "malformed_message", _DETAIL_MALFORMED, room.room_id, seat.seat_id
            )
        )
        if not await self._flush_and_check(seat):
            self._handle_disconnect(room, seat)
            return False
        return True

    async def _reply_schema_error(
        self, websocket: WebSocket, room: Room, seat: Seat, data: dict
    ) -> bool:
        """Classify a schema violation on a frame that MAY carry a valid id.

        If the frame carries a valid canonical ``action_id`` to echo, a
        ``Reject`` with ``bad_type``/``missing_field``/``extra_field`` is emitted;
        otherwise the message is uncorrelatable and answered with
        ``malformed_message``. This reject does NOT consume the ordinal (it never
        reached the cache/ordinal stage).
        """

        action_id = data.get("action_id")
        seat_id = data.get("seat_id")
        if (
            isinstance(action_id, str)
            and isinstance(seat_id, str)
            and self._is_echoable_action_id(action_id, seat_id)
        ):
            reason = self._schema_reject_reason(data)
            reject = make_reject(
                room.room_id, seat.seat_id, action_id, reason, seat.revision
            )
            return await self._emit_reply(websocket, room, seat, reject, cache=False)
        return await self._reply_malformed(websocket, room, seat)

    @staticmethod
    def _is_echoable_action_id(action_id: str, seat_id: str) -> bool:
        """Return True iff ``action_id`` is a canonical id echoable in a reject."""

        try:
            contract._validate_action_id(action_id)
        except ValueError:
            return False
        return seat_id in ("A", "B")

    @staticmethod
    def _schema_reject_reason(data: dict) -> contract.RejectReason:
        """Pick the bounded schema-reject reason for an echoable action frame.

        Distinguishes an extra undocumented field (``extra_field``) from a missing
        required field (``missing_field``); any other wrong-typed value defaults to
        ``bad_type``. The precise code is cosmetic for the client; all three are
        bounded schema rejections that never mutate a board.
        """

        allowed = {
            "type",
            "protocol_version",
            "room_id",
            "seat_id",
            "action_id",
            "expected_revision",
            "kind",
        }
        if any(key not in allowed for key in data.keys()):
            return "extra_field"
        required = {
            "type",
            "protocol_version",
            "room_id",
            "seat_id",
            "action_id",
            "expected_revision",
            "kind",
        }
        if any(key not in data for key in required):
            return "missing_field"
        return "bad_type"

    # -- terminal / cleanup ------------------------------------------------

    def _check_and_emit_terminal(self, websocket: WebSocket, room: Room) -> bool:
        """Return True when the room has resolved to a terminal outcome.

        Resolution is set exactly once in the room; this only reports whether the
        room is ``finished`` so the caller emits the ``outcome`` frame and closes.
        """

        return room.status == "finished" and room.outcome is not None

    async def _finish_and_close(
        self, websocket: WebSocket, room: Room, seat: Seat
    ) -> None:
        """Emit the terminal ``outcome`` frame and close 1000 normal_completion.

        The outcome is built from the room's set-once :class:`OutcomeData` via the
        shared ``gravity.build_outcome_frame`` so the endpoint and the lifespan
        loop produce identical frames. The room entry is released so no room/task/
        socket is leaked and the finished state is never reused.
        """

        outcome = room.outcome
        if isinstance(outcome, gravity.OutcomeData):
            # Terminal result goes to BOTH connected peers (native-14/native-19),
            # not only the seat whose coroutine resolved it: the final both-board
            # state AND the single ``outcome`` frame via the shared
            # ``broadcast_terminal`` seam, so this action-observed terminal
            # publishes the SAME payload as the gravity/forfeit paths. Each peer's
            # independent writer flushes its copy; this owner-side call then yields
            # so the owner's copy drains before the normal-completion close.
            broadcast_terminal(room, outcome)
            await self._flush_and_check(seat)
        await self._close(
            websocket,
            contract.CLOSE_CODE_NORMAL,
            contract.CLOSE_REASON_NORMAL_COMPLETION,
        )
        self._manager.release_room(room.room_id)

    def _close_survivor_after_terminal(self, room: Room, forfeiting_seat: str) -> None:
        """Close the SURVIVING peer through its own single ordered writer (D1).

        After a gameplay forfeit has been resolved exactly once and the terminal
        payload (final both-board state then the single ``outcome`` frame) has
        been enqueued onto the surviving peer via ``broadcast_terminal``, the idle
        survivor's reader is still blocked on ``websocket.receive()`` (it is
        sending nothing) and its writer has nothing further to close -- so without
        this directive the survivor socket never closes and, once the manager map
        entry is released, the periodic retention cleanup never sees the room to
        close it either (the native-20 D1 orphan). For EVERY still-connected seat
        OTHER than the forfeiting one, queue a one-shot writer-driven close with
        the NORMAL-completion code 1000 + literal ``normal_completion`` reason
        through the SAME single ordered writer: the writer first drains the
        already-queued terminal frames (they were enqueued before this directive),
        then closes the survivor's OWN socket and wakes its blocked reader via the
        writer-gone signal. The survivor therefore reaches CLOSE within the
        bounded finished retention WITHOUT any further input from either side and
        WITHOUT relying on a future gravity step. The forfeiting seat keeps its
        own 1001 ``peer_unavailable_forfeit`` close (performed by its caller); the
        survivor's NORMAL completion is 1000, preserving the failed-seat-vs-
        normal-completion distinction. Idempotent: ``request_close`` keeps the
        FIRST directive, so a racing teardown never overwrites the reason, and a
        seat whose writer already exited is a harmless no-op.
        """

        for other_id, other in room.seats.items():
            if other_id == forfeiting_seat:
                continue
            if not other.connected:
                continue
            other.request_close(
                contract.CLOSE_CODE_NORMAL,
                contract.CLOSE_REASON_NORMAL_COMPLETION,
            )

    async def _forfeit_and_close(
        self, websocket: WebSocket, room: Room, seat: Seat
    ) -> None:
        """Resolve a failed-send / slow-peer forfeit once and close 1001.

        A failed send / full outbound queue on a STARTED room is a GAMEPLAY
        FORFEIT: the unavailable seat forfeits, the duel resolves EXACTLY ONCE
        (the other seat wins) via ``gravity.resolve_forfeit`` (set-once), and this
        seat's socket is closed 1001 ``peer_unavailable_forfeit``. A failed send on
        a never-started room is an OPERATIONAL ABORT with no fabricated winner.
        """

        now = self._manager.clock()
        if room.status == "playing":
            # The failed/slow seat forfeits; the OTHER seat wins exactly once.
            outcome = gravity.resolve_forfeit(
                room, seat.seat_id, now, manager=self._manager
            )
            # CENTRAL TERMINAL PUBLICATION (native-19 F1). Mark the failed seat
            # disconnected FIRST so ``broadcast_terminal`` skips its (unflushable)
            # queue and enqueues the final both-board state + ``outcome`` frame
            # onto the SURVIVING peer's bounded queue, waking its independent
            # writer. The surviving peer therefore receives the forfeit result
            # with NO further input from either side and never depends on a
            # future gravity step. Enqueued exactly once (only the first resolver
            # gets a non-``None`` outcome).
            seat.connected = False
            if outcome is not None:
                broadcast_terminal(room, outcome)
                # D1 (native-20): ALSO close the SURVIVING peer through its own
                # single ordered writer (drains the terminal frames just enqueued,
                # then closes 1000 normal_completion and wakes its blocked reader)
                # so the idle survivor reaches CLOSE within the finished retention
                # with no further input and is never orphaned after the map entry
                # is released. Only the first resolver (non-``None`` outcome) does
                # this, so it happens exactly once.
                self._close_survivor_after_terminal(room, seat.seat_id)
            await self._close(
                websocket,
                contract.CLOSE_CODE_GOING_AWAY,
                contract.CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT,
            )
        else:
            await self._close(
                websocket,
                contract.CLOSE_CODE_GOING_AWAY,
                contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT,
            )
        self._handle_disconnect(room, seat)

    async def _operational_abort_and_close(
        self, websocket: WebSocket, room: Room, seat: Seat, reason: str
    ) -> None:
        """Abort the WHOLE room operationally once and close both peers (30.3).

        An operational abort (``reason`` is the literal ``"sequence_exhausted"``
        or ``"scalar_overflow"``) is DISTINCT from the gameplay
        ``peer_unavailable_forfeit``: it fabricates NO winner. The FIRST caller
        to win ``Room.set_operational_abort_once`` performs the room-wide close:

        1. Signal the OTHER seat's independent writer to close its own socket
           with code 1001 + the SAME literal reason (the writer drains any
           already-queued frames first, then closes), so the room closes for BOTH
           peers WITHOUT requiring the other peer's inbound traffic and WITHOUT
           emitting any out-of-range state/revision or fabricated outcome.
        2. Close THIS (acting) seat's socket with code 1001 + the literal reason.
        3. Release the room entry so no room/task/socket is leaked and the
           aborted room is never reused.

        ``gravity.resolve_forfeit`` / ``set_outcome_once`` are NEVER invoked here,
        so ``room.outcome`` stays ``None``: an operational abort is not a gameplay
        result. A racing second abort/forfeit/resolution loses the set-once guard
        and only closes its own socket, so the whole room aborts exactly once. The
        acting seat is marked disconnected first so a racing gravity/forfeit path
        observes it and does not fabricate an outcome on the already-aborted room.
        """

        seat.connected = False
        first = room.set_operational_abort_once(reason)
        if first:
            # Direct the OTHER seat's writer to close with the SAME literal
            # reason (room-wide close, no fabricated winner).
            for other_id, other in room.seats.items():
                if other_id == seat.seat_id:
                    continue
                other.request_close(contract.CLOSE_CODE_GOING_AWAY, reason)
        # Close THIS seat's socket with the literal operational-abort reason.
        await self._close(websocket, contract.CLOSE_CODE_GOING_AWAY, reason)
        # Release the room entry exactly once (idempotent if already released).
        if first:
            self._manager.release_room(room.room_id)

    def _handle_disconnect(
        self, room: Optional[Room], seat: Optional[Seat]
    ) -> None:
        """Clean up on a peer disconnect; resolve a started-room forfeit once.

        A disconnect in a STARTED (``playing``) room forfeits the disconnecting
        seat (resolved exactly once via the set-once guard); a disconnect in a
        ``waiting`` room is an operational abort that fabricates no winner. The
        room entry is released so no room/task/socket is leaked. Marks the seat
        disconnected first so a racing gravity/forfeit sees it.
        """

        if room is None or seat is None:
            return
        seat.connected = False
        now = self._manager.clock()
        # An OPERATIONALLY ABORTED room (``sequence_exhausted`` / ``scalar_overflow``,
        # task 30.3) fabricates NO gameplay winner: when the OTHER peer's reader
        # observes the writer-driven close it must NOT resolve a forfeit on the
        # already-aborted room. The abort's set-once marker suppresses the forfeit
        # path here while still releasing the (already released) room idempotently.
        if room.operational_abort is None and room.status == "playing":
            outcome = gravity.resolve_forfeit(
                room, seat.seat_id, now, manager=self._manager
            )
            # CENTRAL TERMINAL PUBLICATION (native-19 F1). When THIS disconnect is
            # the call that FIRST resolves the forfeit (``resolve_forfeit`` returns
            # the committed outcome, not ``None``), the remaining peer must ACTUALLY
            # receive the terminal result -- the final both-board state AND the
            # single ``outcome`` frame -- enqueued onto its bounded queue and
            # flushed by its independent writer WITHOUT any further gravity step or
            # client input. The prior code resolved the set-once outcome but
            # published nothing here, and the gravity loop's ``on_outcome`` only
            # fires when a gravity step NEWLY resolves a still-``playing`` room, so
            # an already-``finished`` room was skipped forever and the survivor
            # never saw the forfeit. Enqueuing wakes the survivor's writer; the
            # disconnected seat's own queue is harmlessly skipped (it is no longer
            # connected). A racing second caller gets ``None`` and publishes
            # nothing, so the terminal frames are enqueued exactly once.
            if outcome is not None:
                broadcast_terminal(room, outcome)
                # D1 (native-20): the forfeit outcome is DELIVERED above, but the
                # idle survivor's reader is still blocked on ``receive()`` and its
                # writer has nothing further to close. Close the SURVIVING peer
                # through its own single ordered writer (drains the terminal
                # frames just enqueued, then closes 1000 normal_completion and
                # wakes its blocked reader) so the survivor reaches CLOSE within
                # the bounded finished retention WITHOUT any further input and is
                # never orphaned once ``release_room`` drops the map entry below.
                # Only the first resolver reaches this branch, so it runs once.
                self._close_survivor_after_terminal(room, seat.seat_id)
        # Release the room entry (idempotent if already released). The peer's own
        # coroutine observes the resolution via its state/outcome frames before
        # its retention-window close. An aborted room is also released here so the
        # peer-side disconnect cleans up even if the acting seat already released.
        if room.operational_abort is not None or room.status in ("waiting", "finished"):
            self._manager.release_room(room.room_id)

    # -- receive racing the writer-gone wakeup (native 19 F2) -------------

    async def _receive_or_writer_gone(
        self, websocket: WebSocket, seat: Seat
    ) -> Optional[dict]:
        """Receive one inbound frame OR wake when the writer is gone.

        Returns the ASGI ``websocket.receive`` message when a frame (or a
        transport disconnect) arrives first, or ``None`` when this seat's
        independent writer has already recorded a failed/timed-out send OR
        completed a directed close -- the native 19 F2 writer-wake. The reader
        would otherwise block forever on ``websocket.receive()`` (the idle peer
        sends nothing; a hung in-flight send only fails AFTER the acting peer's
        ``_flush_and_check`` already returned), so neither the peer nor the
        central forfeit/cleanup ever ran.

        The method keeps ONE ordered socket read: it never issues a second
        concurrent ``receive``/send. It FIRST checks the seat flags directly so a
        failure recorded before the wakeup event was created is not missed, then
        awaits the receive and the writer-gone signal together with
        ``asyncio.wait(FIRST_COMPLETED)``. The pending task is cancelled and
        awaited boundedly so no task is leaked and cancellation truly propagates.
        """

        # A failure/close already recorded before we start: return at once so the
        # reader funnels through the central forfeit/cleanup immediately.
        if seat.send_failed or seat.close_directive is not None:
            return None

        signal = seat.writer_gone_signal()
        # Re-check AFTER creating the event: the writer may have recorded a
        # failure between the first flag check and the event's creation (its
        # ``signal_writer_gone`` was a no-op while the event did not yet exist),
        # so without this second read the wakeup would be lost and the reader
        # would block forever.
        if seat.send_failed or seat.close_directive is not None or signal.is_set():
            return None

        receive_task = asyncio.ensure_future(websocket.receive())
        signal_task = asyncio.ensure_future(signal.wait())
        try:
            done, pending = await asyncio.wait(
                {receive_task, signal_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        except asyncio.CancelledError:
            # Teardown cancellation: cancel + await BOTH owned tasks so neither
            # is leaked, then re-raise so cancellation reaches the connection
            # coroutine's handler.
            for task in (receive_task, signal_task):
                task.cancel()
            await asyncio.wait({receive_task, signal_task})
            raise

        # Cancel + bound-await the loser so no task leaks (native 19 lifecycle).
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending)

        if receive_task in done:
            # A real inbound frame (or transport disconnect) arrived first. Even
            # if the writer ALSO went gone concurrently, the socket read already
            # consumed a frame; the next loop turn re-checks the writer-gone
            # flags before blocking again, so the failure is not lost. (The
            # signal task, if still pending, was cancelled + awaited above.)
            return receive_task.result()

        # The writer-gone signal won: the writer failed/closed while blocked.
        return None

    # -- bounded receive with timeout -------------------------------------

    async def _receive_text_or_timeout(
        self, websocket: WebSocket, timeout_s: float
    ) -> Tuple[Optional[str], bool, bool]:
        """Receive + CLASSIFY the FIRST handshake frame within ``timeout_s``.

        Returns ``(text_or_none, oversize, is_binary)`` -- the SAME classification
        tuple produced by :meth:`_extract_inbound` for the post-handshake action
        loop, so the FIRST Hello/handshake is bounded by the identical 4096 UTF-8
        byte limit (``max_msg_bytes``) BEFORE any JSON/model parse:

        * ``oversize`` is measured on the UTF-8 byte length of a TEXT frame (or the
          raw byte length of a BINARY frame) against ``max_msg_bytes`` -- the wire
          size, not the character count -- so an oversize Hello is detected BEFORE
          ``_parse_hello`` runs and the caller closes with the standard oversize
          code 1009 (not the 1008 malformed/policy close). An oversize frame is
          never buffered whole past the bound.
        * ``is_binary`` flags a BINARY (``bytes``) first frame; the caller maps it
          to the application-visible malformed handshake (unchanged behaviour).
        * ``text_or_none`` is the decoded TEXT payload only when it is within the
          byte bound; it is ``None`` for an oversize TEXT frame, any BINARY frame,
          or an absent payload.

        Raises ``TimeoutError`` when no frame arrives within the bound, which the
        caller maps to ``handshake_timeout`` (unchanged). A disconnect during the
        handshake raises ``WebSocketDisconnect`` to the caller's cleanup
        (unchanged).
        """

        message = await asyncio.wait_for(websocket.receive(), timeout=timeout_s)
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        # Reuse the EXACT action-loop classification so the Hello cap, binary
        # classification, and byte-length measurement are identical.
        return self._extract_inbound(message)


def build_duel_router(
    manager: RoomManager,
    allowed_origins: Optional[Tuple[str, ...]] = None,
) -> APIRouter:
    """Build an ``APIRouter`` exposing ``/ws/duel`` bound to ``manager``.

    This is the clean seam task 15.1 uses: the app constructs ONE lifespan-owned
    ``RoomManager`` plus the resolved Origin allow-list, calls this factory, and
    includes the returned router. Keeping the endpoint a factory over an injected
    manager avoids a module-global singleton and keeps the injectable clock (and
    therefore deterministic tests) intact.
    """

    router = APIRouter()
    endpoint = DuelEndpoint(manager, allowed_origins=allowed_origins)

    @router.websocket("/ws/duel")
    async def duel_ws(websocket: WebSocket) -> None:  # pragma: no cover - thin shim
        await endpoint(websocket)

    return router


__all__ = [
    # Origin allow-list
    "WSOriginConfigurationError",
    "resolve_ws_allowed_origins",
    "origin_is_allowed",
    # Pure helpers
    "Fingerprint",
    "build_fingerprint",
    "ordinal_of",
    "build_state_frame",
    "build_both_board_frames",
    "broadcast_room_state",
    "broadcast_outcome",
    "broadcast_terminal",
    "RateLimiter",
    "CacheOrdinalDecision",
    "decide_cached_and_ordinal",
    "decide_revision",
    "apply_action_to_seat",
    "seat_scalar_overflow",
    "would_scalar_overflow",
    "is_sequence_exhausted_id",
    "make_ack",
    "make_reject",
    "make_error",
    # Decision kind constants
    "DECISION_CACHED_HIT",
    "DECISION_DUPLICATE_CONFLICT",
    "DECISION_STALE",
    "DECISION_FUTURE",
    "DECISION_APPLY",
    # Endpoint
    "DuelEndpoint",
    "build_duel_router",
]
