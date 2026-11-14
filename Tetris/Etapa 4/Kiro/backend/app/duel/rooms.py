"""Duel rooms, seats, and the room manager (Stage 4 Option A, M3).

This module defines the in-memory duel state structures and their bounded,
injectable-clock lifecycle. It intentionally holds ONLY the data structures,
the ``RoomManager``, and the ``cleanup_tick`` retention logic (task 12.1). The
per-board gravity loop (task 13.1, ``app/duel/gravity.py``) and the WebSocket
endpoint (task 14.1, ``app/ws/duel.py``) layer on top of these seams without
re-declaring them.

Design decisions encoded here (see design.md "RoomManager / Room / Seat" and
"Room lifecycle, cleanup, and concurrency"):

* **Private per-seat engine Game (Req 16.2, 16.3, 17.5).** Each ``Seat`` owns a
  PRIVATE ``engine.new_game`` ``Game``. Duel games are NEVER registered in
  ``app/store.py``, never exposed via ``GET /api/games/{id}``, never written to
  the solo SQLite, and never added to the solo leaderboard -- this module
  imports none of those modules, so zero SQL writes are possible from here.
* **Identical seed, independent advancement (Req 17.2, 17.3, 17.4).** Both
  seats receive the IDENTICAL room seed and each constructs its OWN independent
  ``random.Random`` inside its own ``Game`` (``engine.new_game(game_id,
  room_seed)``). Both boards therefore start with the SAME initial seeded 7-bag
  sequence while advancing INDEPENDENTLY: no global RNG is shared and advancing
  one seat never advances the other seat or the solo sequence.
* **Injectable monotonic clock (Req 19.4, 18.1).** ``RoomManager`` takes an
  injectable ``clock`` (a callable returning a float, default ``time.monotonic``)
  so tests drive cleanup/gravity deterministically.
* **Bounded idempotency per seat (Req 20.5).** Each seat keeps a monotonic
  high-water mark ``last_action_seq`` PLUS a bounded 256-entry LRU
  ``reply_cache`` keyed by ``action_id``. The two are kept separate so an
  evicted old id at or below the high-water mark is rejected
  ``duplicate_action_conflict`` rather than re-applied. The reply-cache and
  high-water logic consumers live in the endpoint (task 14.1); this module owns
  the bounded storage and its eviction.
* **Short snapshot lock, I/O outside it (Req 19.5, 19.6).** ``Room.state_lock``
  is a SHORT per-room lock used ONLY to take a consistent detached snapshot;
  bounded, ordered per-peer outbound I/O happens OUTSIDE the lock so one slow
  peer never blocks another room or the worker. ``snapshot_under_lock`` returns
  a detached copy; ``drain_outbound`` is called with NO lock held.
* **Status-keyed retention (Req 19.1, 19.2, 19.3, 19.7).** ``cleanup_tick`` runs
  periodically even without traffic. A ``finished`` room uses the 15-second
  finished retention (DISTINCT from the 120-second waiting/inactive retention
  and the 60-second playing idle timeout). A cancelled room, slow peer, failed
  send, and shutdown each release the room entry, its gravity task, and its
  sockets with no leak. A restart after a duel yields a fresh room -- a finished
  room's state is never reused (its entry is removed on expiry).
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Literal, Optional, Tuple

from ..rules import engine
from ..ws import contract

# ---------------------------------------------------------------------------
# Bounds imported from the single source of truth (the contract layer). These
# are re-exported under the task's short local names so later M3 modules can
# refer to either spelling, but the VALUES are never re-literal here.
# ---------------------------------------------------------------------------

#: Maximum concurrent rooms (Req 22.3).
MAX_ROOMS: int = contract.MAX_ROOMS
#: Inclusive upper bound on a room_id string length (Req 22.3).
ROOM_ID_MAX_LEN: int = contract.ID_MAX_LENGTH
#: Inclusive lower bound on a room_id string length.
ROOM_ID_MIN_LEN: int = contract.ID_MIN_LENGTH
#: Maximum inbound UTF-8 message size in bytes (Req 22.3).
MAX_MSG_BYTES: int = contract.MAX_MSG_BYTES
#: Inbound action rate per seat per fixed 1-second window (Req 22.3).
ACTION_RATE_PER_SEAT: int = contract.ACTION_RATE_PER_SEAT
#: Per-seat outbound queue depth in frames (Req 22.3).
OUTBOUND_QUEUE_DEPTH: int = contract.OUTBOUND_QUEUE_DEPTH
#: Handshake timeout in seconds (Req 22.3).
HANDSHAKE_TIMEOUT: int = contract.HANDSHAKE_TIMEOUT_S
#: Playing-room idle timeout in seconds (Req 22.3).
IDLE_TIMEOUT: int = contract.IDLE_TIMEOUT_S
#: Finished-room retention in seconds, DISTINCT from waiting retention (Req 19.2, 22.3).
FINISHED_ROOM_RETENTION: int = contract.FINISHED_ROOM_RETENTION_S
#: Waiting/inactive-room retention in seconds (Req 19.2, 22.3).
WAITING_ROOM_RETENTION: int = contract.WAITING_ROOM_RETENTION_S
#: Fixed cleanup cadence in seconds (design.md "1-second cleanup cadence").
CLEANUP_CADENCE: int = contract.CLEANUP_CADENCE_S

#: Bounded per-seat reply-cache capacity (Req 20.5): the 256 most-recent ids.
REPLY_CACHE_MAX: int = 256

#: Enumerated seat identities for a room.
SeatId = Literal["A", "B"]
SEAT_IDS: Tuple[SeatId, SeatId] = ("A", "B")

#: Room lifecycle status (distinct from a per-seat board status).
RoomStatus = Literal["waiting", "playing", "finished"]


@dataclass
class ReplyCacheEntry:
    """A cached reply plus the immutable request fingerprint that produced it.

    The fingerprint (``kind``/``expected_revision``/``room_id``/``seat_id``/
    ``action_id``) lets the endpoint distinguish an IDENTICAL duplicate (return
    the cached reply unchanged) from a reused ``action_id`` with a CHANGED
    fingerprint (reject ``duplicate_action_conflict``). ``reply`` is the opaque
    emitted ``Ack``/``Reject`` frame; this module stores it without interpreting
    it so it stays decoupled from the endpoint's frame construction.
    """

    fingerprint: Tuple[str, int, str, str, str]
    reply: object


class ReplyCache:
    """Bounded 256-entry per-seat LRU idempotency reply cache (Req 20.5).

    Keyed by ``action_id``. Insertion and a cache hit both refresh LRU recency.
    When the cache exceeds :data:`REPLY_CACHE_MAX` the least-recently-used entry
    is evicted. Eviction is COUNT-based only; there is no time-based retention
    window. The separate per-seat high-water mark (:attr:`Seat.last_action_seq`)
    lets an evicted old id be rejected ``duplicate_action_conflict`` rather than
    re-applied, so losing a reply-cache entry can never cause a second
    application of an already-processed action.
    """

    def __init__(self, capacity: int = REPLY_CACHE_MAX) -> None:
        if capacity < 1:
            raise ValueError("reply cache capacity must be >= 1")
        self._capacity = capacity
        self._entries: "OrderedDict[str, ReplyCacheEntry]" = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def capacity(self) -> int:
        return self._capacity

    def get(self, action_id: str) -> Optional[ReplyCacheEntry]:
        """Return the cached entry for ``action_id`` and refresh its recency."""

        entry = self._entries.get(action_id)
        if entry is not None:
            self._entries.move_to_end(action_id)
        return entry

    def put(
        self,
        action_id: str,
        fingerprint: Tuple[str, int, str, str, str],
        reply: object,
    ) -> None:
        """Insert or refresh ``action_id`` -> (fingerprint, reply), evicting LRU."""

        if action_id in self._entries:
            self._entries.move_to_end(action_id)
        self._entries[action_id] = ReplyCacheEntry(fingerprint, reply)
        while len(self._entries) > self._capacity:
            # popitem(last=False) removes the least-recently-used entry.
            self._entries.popitem(last=False)

    def action_ids(self) -> List[str]:
        """Return cached action ids from least- to most-recently used (testing)."""

        return list(self._entries.keys())


@dataclass
class Seat:
    """A single duel seat: a private engine game plus per-seat bookkeeping.

    ``game`` is a PRIVATE ``engine.new_game`` ``Game`` constructed from the
    room seed; it is never shared with the solo store. ``revision`` is the
    authoritative per-board revision (monotonic). ``last_action_seq`` is the
    per-seat monotonic high-water mark of the highest consumed action ordinal.
    ``reply_cache`` is the bounded 256-entry idempotency structure.
    ``outbound`` is the bounded per-seat outbound frame queue.
    ``gravity_due_monotonic`` is the next gravity due time on the injectable
    clock (populated by the gravity loop, task 13.1).
    """

    seat_id: SeatId
    game: object  # engine Game; typed as object to avoid importing the dataclass name
    rng_seed: int
    revision: int = 0
    last_action_seq: int = 0
    reply_cache: ReplyCache = field(default_factory=ReplyCache)
    outbound: Deque[object] = field(
        default_factory=lambda: deque(maxlen=OUTBOUND_QUEUE_DEPTH)
    )
    connected: bool = False
    gravity_due_monotonic: float = 0.0
    #: Writer-wakeup signal (M3 native 14 delivery correction). The independent
    #: per-connection writer task awaits this event; every ``enqueue_outbound``
    #: (and ``close_outbound``) SETS it so the writer flushes queued frames
    #: WITHOUT requiring any recipient inbound traffic. Created lazily on first
    #: use so a non-async context (unit/property test) can build a ``Seat`` with
    #: no running event loop. Typed as object to avoid an asyncio import leak.
    _outbound_signal: Optional[object] = field(default=None, repr=False)
    #: Set once the owning connection is tearing down; the writer observes it to
    #: stop after draining and never blocks forever on the signal.
    outbound_closed: bool = field(default=False, repr=False)
    #: Set by the writer when a send failed or breached the 5s bound / the queue
    #: was full; the owning coroutine reads it to classify the peer as
    #: unavailable (slow-peer forfeit in a STARTED room). No unbounded retries.
    send_failed: bool = field(default=False, repr=False)
    #: Writer-gone wakeup signal (M3 native 19 F2 writer-wake correction). The
    #: reader (``_run_action_loop``) races its blocking ``websocket.receive()``
    #: against this event so a writer failure (new OR cached ACK, in-flight-send
    #: breach, full queue) -- OR the writer completing a directed close -- WAKES
    #: and terminates the blocked reader WITHOUT waiting for another
    #: ``_flush_and_check``. The reader then funnels through the central
    #: forfeit/cleanup. It is distinct from ``_outbound_signal`` (which wakes the
    #: WRITER to flush): this one wakes the READER to stop blocking. Created
    #: lazily on first use so a seat can be built with no running event loop;
    #: typed as object to avoid an asyncio import leak. ``None`` until the reader
    #: or a wakeup first touches it.
    _writer_gone_signal: Optional[object] = field(default=None, repr=False)
    #: One-shot writer-driven close directive (M3 native 14, task 30.3). When a
    #: ROOM-WIDE operational abort (``sequence_exhausted`` / ``scalar_overflow``)
    #: is wired at the endpoint for the ACTING seat, the OTHER seat is signalled
    #: to close by setting this ``(code, reason)`` pair and waking its writer;
    #: the peer's independent writer drains any already-queued frames, then
    #: closes its OWN socket with this standard code + LITERAL reason and stops.
    #: This is how one seat's operational abort closes the WHOLE room for both
    #: peers WITHOUT fabricating any gameplay outcome and WITHOUT the reader
    #: needing inbound traffic. ``None`` means "no directed close pending".
    close_directive: Optional[Tuple[int, str]] = field(default=None, repr=False)

    def request_close(self, code: int, reason: str) -> None:
        """Queue a one-shot writer-driven close ``(code, reason)`` and wake it.

        Idempotent: the FIRST directive wins so a racing second abort/teardown
        never overwrites the literal operational-abort reason the room resolved
        on. Setting it wakes the writer so the peer closes even with no inbound
        traffic (the native-14 traffic-free delivery guarantee).
        """

        if self.close_directive is None:
            self.close_directive = (code, reason)
        self._wake_writer()

    def outbound_signal(self) -> "asyncio.Event":
        """Return (lazily creating) this seat's writer-wakeup event.

        The event is bound to the CURRENT running loop on first use; the writer
        and every enqueuer share the one event so a frame produced with NO
        recipient inbound traffic still wakes the writer. Kept out of
        construction so a seat can be built in a plain (non-async) test.
        """

        signal = self._outbound_signal
        if signal is None:
            signal = asyncio.Event()
            self._outbound_signal = signal
        return signal

    def _wake_writer(self) -> None:
        """Set the writer-wakeup signal if one exists (no-op without a loop).

        Enqueuing from a synchronous context (handshake/gravity) still wakes the
        writer when the writer has already created the event; if no writer/event
        exists yet (pure unit test), this is a harmless no-op.
        """

        signal = self._outbound_signal
        if signal is not None:
            signal.set()

    def writer_gone_signal(self) -> "asyncio.Event":
        """Return (lazily creating) this seat's writer-gone wakeup event.

        The reader awaits this event CONCURRENTLY with its blocking
        ``websocket.receive()`` so a writer failure / directed close wakes it
        without any further inbound traffic or flush. Bound to the current
        running loop on first use and shared with the writer, which SETS it via
        :meth:`mark_send_failed` / :meth:`signal_writer_gone`. If it was already
        set before the reader created it, the reader re-reads ``send_failed`` /
        ``close_directive`` directly so no wakeup is lost.
        """

        signal = self._writer_gone_signal
        if signal is None:
            signal = asyncio.Event()
            self._writer_gone_signal = signal
        return signal

    def signal_writer_gone(self) -> None:
        """Set the writer-gone wakeup signal if one exists (no-op without a loop).

        Called by the writer AFTER it performs a directed close so a reader
        blocked on ``websocket.receive()`` wakes and tears the connection down.
        Harmless when no reader has created the event yet (the reader re-reads
        the seat flags directly before blocking).
        """

        signal = self._writer_gone_signal
        if signal is not None:
            signal.set()

    def mark_send_failed(self) -> None:
        """Record a writer send failure AND wake the blocked reader (native 19 F2).

        Sets ``send_failed`` (so ``_flush_and_check`` and the acting-peer path
        still classify the peer unavailable, unchanged) AND sets the writer-gone
        wakeup signal so a reader blocked on ``websocket.receive()`` -- the IDLE
        peer that is sending nothing, or the acting peer whose in-flight send
        only failed AFTER its ``_flush_and_check`` already returned -- wakes
        immediately and triggers the central forfeit/cleanup WITHOUT waiting for
        another flush. No retry: the writer has already stopped.
        """

        self.send_failed = True
        self.signal_writer_gone()

    def enqueue_outbound(self, frame: object) -> bool:
        """Append a frame to the bounded outbound queue and wake the writer.

        Returns ``True`` if the frame was accepted, ``False`` if the queue was
        already at :data:`OUTBOUND_QUEUE_DEPTH` (a FULL queue, which the endpoint
        treats as a failed/slow peer). The bounded ``deque`` never grows past the
        cap, so a slow peer cannot exhaust worker memory. A successful enqueue
        SETS the writer-wakeup signal so the independent writer flushes the frame
        even to a peer that is sending nothing (the native-14 delivery fix).
        """

        if len(self.outbound) >= OUTBOUND_QUEUE_DEPTH:
            return False
        self.outbound.append(frame)
        self._wake_writer()
        return True

    def close_outbound(self) -> None:
        """Mark the outbound channel closed and wake the writer to drain+exit.

        Called on teardown so the writer stops awaiting the signal forever: it
        flushes whatever is already queued (best effort, still bounded) and then
        exits cleanly, leaving no leaked writer task.
        """

        self.outbound_closed = True
        self._wake_writer()

    def drain_outbound(self) -> List[object]:
        """Pop every queued outbound frame in FIFO order (called OUTSIDE locks).

        The writer performs the actual bounded, ordered socket I/O on the
        returned list without holding ``Room.state_lock``.
        """

        drained: List[object] = []
        while self.outbound:
            drained.append(self.outbound.popleft())
        return drained


@dataclass
class Room:
    """An in-memory duel room with up to two seats and a bounded lifecycle.

    ``state_lock`` is a SHORT per-room lock taken ONLY to snapshot consistent
    state; outbound I/O happens outside it. ``outcome`` is set exactly once at
    the terminal transition and never changed. The monotonic timestamps drive
    the status-keyed retention in :meth:`RoomManager.cleanup_tick`.
    """

    room_id: str
    seed: int
    status: RoomStatus = "waiting"
    seats: Dict[str, Seat] = field(default_factory=dict)
    state_lock: threading.Lock = field(default_factory=threading.Lock)
    created_monotonic: float = 0.0
    last_activity_monotonic: float = 0.0
    finished_monotonic: Optional[float] = None
    outcome: Optional[object] = None
    #: Set EXACTLY once when the room is torn down by an OPERATIONAL ABORT
    #: (M3 native 14, task 30.3): the literal close reason ``"sequence_exhausted"``
    #: or ``"scalar_overflow"``. This is DISTINCT from ``outcome`` (a gameplay
    #: result): an operational abort fabricates NO winner, so ``outcome`` stays
    #: ``None`` while this records why the room aborted. Used to make the abort
    #: idempotent (race-safe) and to let a test assert the room aborted without a
    #: fabricated gameplay outcome.
    operational_abort: Optional[str] = None
    #: Handle to this room's gravity task, if any (set by task 13.1/15.1). Held
    #: here so cleanup can release it; typed as object to avoid an asyncio import.
    gravity_task: Optional[object] = None

    def is_full(self) -> bool:
        """Return True when both seats A and B are occupied."""

        return len(self.seats) >= 2

    def free_seat_id(self) -> Optional[SeatId]:
        """Return the first unoccupied seat id (A before B), or None if full."""

        for seat_id in SEAT_IDS:
            if seat_id not in self.seats:
                return seat_id
        return None

    def both_connected(self) -> bool:
        """Return True when both seats exist AND both are connected."""

        return self.is_full() and all(s.connected for s in self.seats.values())

    def set_outcome_once(self, outcome: object, now: float) -> bool:
        """Set the terminal outcome and transition to ``finished`` exactly once.

        Returns ``True`` the first time (the duel resolves once); ``False`` on
        any later call so a finished room is never resolved a second time
        (Req 18.5, 18.6). Also stamps ``finished_monotonic`` for retention.
        """

        if self.outcome is not None or self.status == "finished":
            return False
        self.outcome = outcome
        self.status = "finished"
        self.finished_monotonic = now
        return True

    def set_operational_abort_once(self, reason: str) -> bool:
        """Mark the room OPERATIONALLY ABORTED exactly once (M3 native 14).

        An operational abort (``"sequence_exhausted"`` / ``"scalar_overflow"``)
        is NOT a gameplay result: it fabricates NO winner, so ``outcome`` is left
        untouched (``None``) and ``status`` is NOT set to ``finished`` here (the
        endpoint releases the room entry on abort). Returns ``True`` the FIRST
        time this room aborts so the acting seat performs the room-wide close +
        release exactly once; ``False`` on any later call (a racing second abort
        or a room already resolved to a gameplay outcome) so the whole room is
        never aborted or re-resolved twice. Taking the short ``state_lock`` keeps
        the first-writer decision race-safe against a concurrent resolution.
        """

        with self.state_lock:
            if self.operational_abort is not None or self.outcome is not None:
                return False
            if self.status == "finished":
                return False
            self.operational_abort = reason
            return True

    def snapshot_under_lock(self) -> Dict[str, object]:
        """Take a consistent detached snapshot while holding ``state_lock``.

        Returns a plain detached dict (not live references), so the caller can
        perform bounded, ordered outbound I/O OUTSIDE the lock without racing a
        concurrent mutation (Req 19.5). The snapshot deliberately copies only
        cheap lifecycle scalars plus per-seat revision/connected/status; the
        heavy board snapshot for a state frame is built by the endpoint from the
        seat's private game, still outside the lock.
        """

        with self.state_lock:
            return {
                "room_id": self.room_id,
                "status": self.status,
                "seed": self.seed,
                "seats": {
                    seat_id: {
                        "seat_id": seat.seat_id,
                        "revision": seat.revision,
                        "connected": seat.connected,
                        "last_action_seq": seat.last_action_seq,
                    }
                    for seat_id, seat in self.seats.items()
                },
                "outcome": self.outcome,
            }


def _seat_game_id(room_id: str, seat_id: str) -> str:
    """Build a private, duel-only game id that is never registered in the store."""

    return f"duel:{room_id}:{seat_id}"


class RoomManager:
    """In-memory manager of duel rooms with a bounded, injectable-clock lifecycle.

    The manager owns the ``rooms`` map, the injectable monotonic ``clock``, and
    the bounds. It is designed to be owned by the FastAPI lifespan (task 15.1):
    a single instance per worker. All public mutation of the ``rooms`` map is
    guarded by a short internal lock so ``assign_seat`` and ``cleanup_tick`` are
    safe to call concurrently; per-room snapshotting uses the room's own
    ``state_lock`` and outbound I/O happens outside both.
    """

    def __init__(
        self,
        clock: Optional[Callable[[], float]] = None,
        *,
        max_rooms: int = MAX_ROOMS,
        room_id_max_len: int = ROOM_ID_MAX_LEN,
        max_msg_bytes: int = MAX_MSG_BYTES,
        action_rate_per_seat: int = ACTION_RATE_PER_SEAT,
        outbound_queue_depth: int = OUTBOUND_QUEUE_DEPTH,
        handshake_timeout: int = HANDSHAKE_TIMEOUT,
        idle_timeout: int = IDLE_TIMEOUT,
        finished_room_retention: int = FINISHED_ROOM_RETENTION,
        waiting_room_retention: int = WAITING_ROOM_RETENTION,
    ) -> None:
        self.clock: Callable[[], float] = clock or time.monotonic
        self.rooms: Dict[str, Room] = {}
        self._lock = threading.Lock()
        # Bounds (Req 22.3); stored as instance attributes so a test can inject
        # smaller values without re-literal and the endpoint reads them here.
        self.max_rooms = max_rooms
        self.room_id_max_len = room_id_max_len
        self.max_msg_bytes = max_msg_bytes
        self.action_rate_per_seat = action_rate_per_seat
        self.outbound_queue_depth = outbound_queue_depth
        self.handshake_timeout = handshake_timeout
        self.idle_timeout = idle_timeout
        self.finished_room_retention = finished_room_retention
        self.waiting_room_retention = waiting_room_retention

    # -- room construction -------------------------------------------------

    def _make_seat(self, room: Room, seat_id: SeatId) -> Seat:
        """Construct a seat with its OWN private engine game from the room seed.

        Each seat builds an INDEPENDENT ``random.Random`` inside its own
        ``engine.new_game`` from the IDENTICAL room seed, so both boards start
        with the same initial 7-bag sequence while advancing independently. The
        game id is a duel-only id that is never inserted into the solo store.
        """

        game = engine.new_game(_seat_game_id(room.room_id, seat_id), room.seed)
        return Seat(seat_id=seat_id, game=game, rng_seed=room.seed)

    def assign_seat(self, room_id: str, origin: Optional[str] = None) -> Tuple[Room, Seat]:
        """Place a connection into a waiting or new room and return (room, seat).

        Creates the room on first join (bounded by ``max_rooms``); assigns seat
        A then B. When the second seat joins, the room is NOT started here
        (start gating/state-frame emission is the endpoint's job, task 14.1);
        this method only wires the seat and stamps activity. ``origin`` is
        accepted for signature compatibility with the endpoint but is validated
        at the HTTP upgrade (task 14.1), not here.

        Raises ``RoomFullError`` when the room already has two seats and
        ``RoomCapacityError`` when creating a new room would exceed ``max_rooms``.
        ``room_id`` length is validated against the bound.
        """

        if not (ROOM_ID_MIN_LEN <= len(room_id) <= self.room_id_max_len):
            raise ValueError(
                f"room_id length must be {ROOM_ID_MIN_LEN}..{self.room_id_max_len}"
            )

        now = self.clock()
        with self._lock:
            room = self.rooms.get(room_id)
            if room is None:
                if len(self.rooms) >= self.max_rooms:
                    raise RoomCapacityError("room count is at its maximum")
                room = Room(
                    room_id=room_id,
                    seed=self._derive_room_seed(room_id),
                    created_monotonic=now,
                    last_activity_monotonic=now,
                )
                self.rooms[room_id] = room

            if room.status == "finished":
                # A restart after a duel must get a FRESH room, never the
                # finished room's reused state (Req 19.7). The finished entry is
                # retained only for its drain window; a new join rejects it.
                raise RoomClosedError("room is finished")

            seat_id = room.free_seat_id()
            if seat_id is None:
                raise RoomFullError("room already has two seats")

            seat = self._make_seat(room, seat_id)
            seat.connected = True
            room.seats[seat_id] = seat
            room.last_activity_monotonic = now
            return room, seat

    def _derive_room_seed(self, room_id: str) -> int:
        """Derive a stable, bounded integer room seed from the room id.

        Both seats share this one seed. A deterministic derivation keeps a room
        reproducible for tests while never sharing a global RNG. The value is
        kept within the safe-integer ceiling.
        """

        acc = 0
        for ch in room_id:
            acc = (acc * 131 + ord(ch)) & contract.SAFE_INT_MAX
        return acc

    # -- lifecycle ---------------------------------------------------------

    def mark_activity(self, room: Room) -> None:
        """Refresh a room's last-activity stamp (e.g. on a gravity state change).

        A gravity-driven state change during ``playing`` refreshes activity so an
        actively-progressing board is never reaped as idle (Req 19 idle policy).
        """

        room.last_activity_monotonic = self.clock()

    def release_room(self, room_id: str) -> Optional[Room]:
        """Remove a room from the map and return it (or None if already gone).

        Releasing the room entry drops the manager's reference to the room, its
        gravity task handle, and its seats/sockets so no room/task/socket is
        leaked (Req 19.3). The caller (endpoint/lifespan) is responsible for the
        actual gravity-task cancel and socket close using the returned room; this
        method guarantees the MAP no longer references it so it cannot be reused.
        """

        with self._lock:
            return self.rooms.pop(room_id, None)

    def _expired(self, room: Room, now: float) -> bool:
        """Return True when a room has exceeded its STATUS-keyed retention.

        Each status has a DISTINCT bounded retention, and none contradicts
        another (Req 19.1, 19.2):

        * ``finished`` -> 15-second finished retention from ``finished_monotonic``
          (lets terminal frames drain, then release).
        * ``playing``  -> 60-second idle timeout from ``last_activity_monotonic``
          (a gravity state change refreshes activity, so an active board is not
          reaped).
        * ``waiting``  -> 120-second waiting/inactive retention from
          ``created_monotonic`` (a waiting room has no gravity, so its lifetime is
          governed solely by this retention).
        """

        if room.status == "finished":
            base = room.finished_monotonic
            if base is None:
                base = room.last_activity_monotonic
            return (now - base) >= self.finished_room_retention
        if room.status == "playing":
            return (now - room.last_activity_monotonic) >= self.idle_timeout
        # waiting / inactive
        return (now - room.created_monotonic) >= self.waiting_room_retention

    def cleanup_tick(self) -> List[Room]:
        """Release every room that has exceeded its status-keyed retention.

        Runs PERIODICALLY even without new traffic (scheduled from the lifespan,
        task 15.1). Reaped rooms are removed from the map and returned so the
        caller can perform the bounded, ordered socket close + gravity-task
        cancel OUTSIDE any manager lock (Req 19.1, 19.3, 19.5, 19.6). This method
        holds only the short manager lock to select + detach the expired rooms;
        it performs NO outbound I/O itself, so a slow peer cannot stall cleanup.

        Returns the list of released rooms (empty when nothing expired).
        """

        now = self.clock()
        reaped: List[Room] = []
        with self._lock:
            expired_ids = [
                room_id
                for room_id, room in self.rooms.items()
                if self._expired(room, now)
            ]
            for room_id in expired_ids:
                room = self.rooms.pop(room_id, None)
                if room is not None:
                    reaped.append(room)
        return reaped

    def shutdown(self) -> List[Room]:
        """Release ALL rooms on server shutdown and return them for socket close.

        Clears the map so no room/task/socket is leaked across shutdown
        (Req 19.3). The caller closes each returned room's sockets (code 1001
        ``server_shutdown``) and cancels its gravity task outside the lock.
        """

        with self._lock:
            reaped = list(self.rooms.values())
            self.rooms.clear()
        return reaped


# ---------------------------------------------------------------------------
# Bounded, named error conditions. These carry NO filesystem path, SQL text,
# exception/class detail, or stack content (Req 21.6); the endpoint maps them to
# the appropriate bounded ErrorFrame reason / close code.
# ---------------------------------------------------------------------------


class RoomError(Exception):
    """Base class for bounded room-assignment errors."""


class RoomFullError(RoomError):
    """The target room already has two seats (maps to ``room_full``)."""


class RoomCapacityError(RoomError):
    """Creating a new room would exceed ``max_rooms`` (bounded rejection)."""


class RoomClosedError(RoomError):
    """The target room is finished/gone (maps to ``room_closed``)."""


__all__ = [
    # Structures
    "Seat",
    "Room",
    "RoomManager",
    "ReplyCache",
    "ReplyCacheEntry",
    # Errors
    "RoomError",
    "RoomFullError",
    "RoomCapacityError",
    "RoomClosedError",
    # Types
    "SeatId",
    "RoomStatus",
    "SEAT_IDS",
    # Bounds (re-exported from the contract layer, never re-literal)
    "MAX_ROOMS",
    "ROOM_ID_MAX_LEN",
    "ROOM_ID_MIN_LEN",
    "MAX_MSG_BYTES",
    "ACTION_RATE_PER_SEAT",
    "OUTBOUND_QUEUE_DEPTH",
    "HANDSHAKE_TIMEOUT",
    "IDLE_TIMEOUT",
    "FINISHED_ROOM_RETENTION",
    "WAITING_ROOM_RETENTION",
    "CLEANUP_CADENCE",
    "REPLY_CACHE_MAX",
]
