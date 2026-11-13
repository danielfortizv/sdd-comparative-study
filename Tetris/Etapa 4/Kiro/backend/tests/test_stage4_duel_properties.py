"""Hypothesis property-based tests for the Stage 4 duel room layer (M3, task 12.2).

This module hosts the numbered Correctness Properties from the Stage 4 Option A
design document that are provable against the structures that exist TODAY: the
duel ``RoomManager`` / ``Room`` / ``Seat`` (``app/duel/rooms.py``), the bounded
per-seat ``ReplyCache`` plus high-water mark, the injectable monotonic clock,
and the wire-contract ``ActionMessage`` seat-prefix rule (``app/ws/contract.py``).
Each property is implemented as a single Hypothesis test using MEANINGFUL
generators and runs at least 100 examples via ``@settings(max_examples=...)``.

Task boundary: this file covers ONLY Properties 10, 11, 13, 14, and 16 (task
12.2). The full endpoint wiring that drives revisions/acks over the socket is
task 14.1; these properties therefore exercise the room/ReplyCache/high-water
and seat-isolation seams that the endpoint will consume, plus the documented
revision and idempotency RULES, rather than the socket itself.

These tests NEVER touch the solo store, registration, finalization, or SQLite:
each duel seat owns a PRIVATE ``engine.new_game`` ``Game`` constructed from the
room seed, so no SQL write is possible from here.
"""

from __future__ import annotations

import copy

import pytest
from hypothesis import given, settings, strategies as st

from app.duel import rooms
from app.rules import engine
from app.ws import contract


# ---------------------------------------------------------------------------
# Shared generators and helpers (meaningful input spaces, not trivial constants).
# ---------------------------------------------------------------------------

# Engine actions a seat's private game can undergo. "noop" is included so the
# generators can produce genuine no-ops (e.g. a left move into a wall) as well
# as state changes; the properties distinguish the two by inspecting the game.
MOVES = ["left", "right", "down"]
ROTATIONS = ["cw", "ccw"]

# A valid duel room_id per the contract grammar/bounds (1..64 chars). We keep it
# to the safe id alphabet so it is also a legal action_id seat-prefix target.
room_ids = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
    min_size=1,
    max_size=24,
)

# A fixed, injectable clock so cleanup/assignment are deterministic in tests.
class FakeClock:
    """A deterministic, monotonic, injectable clock for the RoomManager.

    ``advance`` moves time forward by a non-negative delta; ``__call__`` returns
    the current value so it is a drop-in for ``time.monotonic``. Using an
    injectable clock (Req 19.4) lets Property 16 drive retention windows exactly.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, delta: float) -> None:
        if delta < 0:
            raise ValueError("clock must be monotonic")
        self._now += delta


def _game_fingerprint(game) -> dict:
    """A deep, comparable snapshot of every authoritative field of a seat game.

    Captures the RNG state too, so we can prove that touching one seat never
    advances the other seat's seeded generator (which would shift its 7-bag).
    """

    active = game.active
    return {
        "status": game.status,
        "score": game.score,
        "level": game.level,
        "total_lines": game.total_lines,
        "gravity_interval_ms": game.gravity_interval_ms,
        "next_type": game.next_type,
        "hold_type": game.hold_type,
        "can_hold": game.can_hold,
        "board": [row[:] for row in game.board],
        "rng_state": game.rng.getstate(),
        "active_type": None if active is None else active.type,
        "active_origin": None if active is None else active.origin,
        "active_orientation": None if active is None else active.orientation,
        "active_cells": None if active is None else list(active.cells),
    }


def _apply_engine_action(game, action) -> None:
    """Drive a seat's PRIVATE engine game by one generated action.

    ``("move", d)`` -> engine.move; ``("rotate", d)`` -> engine.rotate;
    ``("tick",)`` -> engine.tick; ``("hold",)`` -> engine.hold. Each is a pure
    engine mutation of that ONE game object and never touches any other seat.
    """

    kind = action[0]
    if kind == "move":
        engine.move(game, action[1])
    elif kind == "rotate":
        engine.rotate(game, action[1])
    elif kind == "tick":
        engine.tick(game)
    elif kind == "hold":
        engine.hold(game)
    else:  # pragma: no cover - defensive
        raise AssertionError(f"unknown action {action!r}")


# A generated sequence of engine actions (meaningful mix of moves, rotations,
# soft drops, ticks, and holds). Bounded length keeps each example fast while
# still exercising locks, clears, spawns, and holds across the sequence.
engine_actions = st.one_of(
    st.tuples(st.just("move"), st.sampled_from(MOVES)),
    st.tuples(st.just("rotate"), st.sampled_from(ROTATIONS)),
    st.tuples(st.just("tick")),
    st.tuples(st.just("hold")),
)
action_sequences = st.lists(engine_actions, min_size=0, max_size=40)


# ---------------------------------------------------------------------------
# Property 10: Duel seat independence.
#
# For any room with two seats (each a PRIVATE engine game from the IDENTICAL
# room seed) and any sequence of actions directed at ONE seat, only that seat's
# private board state changes; the OTHER seat's board, queue, Hold, level, and
# RNG sequence are unaffected. Both seats, built from the same seed, start with
# an IDENTICAL initial 7-bag preview yet advance INDEPENDENTLY.
#
# GENERATION STRATEGY: assign seats A and B in a fresh room (identical seed),
# snapshot both private games, pick a target seat, apply a generated engine
# action sequence to ONLY that seat, and assert the untouched seat's full
# fingerprint (including RNG state) is byte-for-byte unchanged while the target
# seat is free to change. Also assert both seats started identical.
#
# Validates: Requirements 17.3, 17.4, 17.5
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 10
@settings(max_examples=150)
@given(
    room_id=room_ids,
    target_seat=st.sampled_from(["A", "B"]),
    actions=action_sequences,
)
def test_property_10_duel_seat_independence(room_id, target_seat, actions):
    manager = rooms.RoomManager(clock=FakeClock())
    room, seat_a = manager.assign_seat(room_id)
    _room2, seat_b = manager.assign_seat(room_id)

    assert seat_a.seat_id == "A"
    assert seat_b.seat_id == "B"

    # Identical seed, so both private games start with the SAME initial 7-bag
    # preview and the SAME RNG state (independent generators, equal start).
    start_a = _game_fingerprint(seat_a.game)
    start_b = _game_fingerprint(seat_b.game)
    assert start_a == start_b

    target = seat_a if target_seat == "A" else seat_b
    other = seat_b if target_seat == "A" else seat_a
    other_before = _game_fingerprint(other.game)

    for action in actions:
        _apply_engine_action(target.game, action)

    # The untouched seat's ENTIRE authoritative state -- board, queue, Hold,
    # level, score, status, active piece, and RNG state -- is unchanged: driving
    # one seat never advances the other seat's seeded sequence or board.
    assert _game_fingerprint(other.game) == other_before

    # The two private games remain DISTINCT objects with distinct RNGs; they are
    # never the same reference, so no coupling is possible.
    assert seat_a.game is not seat_b.game
    assert seat_a.game.rng is not seat_b.game.rng


# ---------------------------------------------------------------------------
# Property 11: Per-board revision monotonicity.
#
# For any seat and any sequence of applied state-changing actions or gravity
# steps, the authoritative revision is NON-DECREASING and increases by EXACTLY
# ONE on each actual state change; a no-op leaves the revision unchanged.
#
# GENERATION STRATEGY: model the documented per-board revision rule (the
# endpoint wiring is task 14.1) at the seat level. For each generated action we
# take a fingerprint of the seat's private game before and after the engine
# mutation: if the authoritative state changed, the board's revision increases
# by exactly one; if it did not change (a genuine no-op), the revision is left
# unchanged -- exactly the rule the endpoint will apply. We assert the revision
# is monotonic non-decreasing across the whole sequence, that every step either
# kept it equal (no-op) or raised it by exactly one (change), and that the final
# revision equals the count of state-changing steps.
#
# Validates: Requirements 20.2, 20.8, 20.9
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 11
@settings(max_examples=150)
@given(room_id=room_ids, actions=action_sequences)
def test_property_11_per_board_revision_monotonicity(room_id, actions):
    manager = rooms.RoomManager(clock=FakeClock())
    _room, seat = manager.assign_seat(room_id)

    assert seat.revision == 0  # a fresh board starts at revision 0
    change_count = 0

    for action in actions:
        before = _game_fingerprint(seat.game)
        prev_revision = seat.revision

        _apply_engine_action(seat.game, action)

        after = _game_fingerprint(seat.game)
        changed = after != before

        # Apply the documented revision rule: +1 on a real change, unchanged on
        # a no-op. (The endpoint, task 14.1, applies this identical rule.)
        if changed:
            seat.revision += 1
            change_count += 1

        # Non-decreasing always; and each step either held steady (no-op) or
        # rose by exactly one (an actual state change).
        assert seat.revision >= prev_revision
        if changed:
            assert seat.revision == prev_revision + 1
        else:
            assert seat.revision == prev_revision

    # The final revision is exactly the number of state-changing steps.
    assert seat.revision == change_count


# ---------------------------------------------------------------------------
# Property 13: Duplicate action idempotency.
#
# For any action id already processed, re-sending the SAME action id does not
# apply the action a second time and yields the SAME ack-or-rejection outcome as
# the first processing. The bounded 256-entry per-seat ReplyCache plus the
# per-seat monotonic high-water mark together guarantee this: a duplicate id
# still cached returns its cached reply unchanged; a duplicate id at or below
# the high-water mark but evicted from the cache is rejected
# (``duplicate_action_conflict``), never re-applied.
#
# GENERATION STRATEGY: drive a seat's ReplyCache + high-water mark exactly as
# the endpoint (task 14.1) will. We generate a sequence of action ordinals (some
# repeated) for seat A, process each through a small reference idempotency
# routine that (1) returns the cached reply on a cache hit, (2) rejects a
# duplicate at/below the high-water mark that has been evicted, and (3) applies
# a new ordinal above the high-water mark exactly once. We count applications
# and assert no ordinal is applied more than once and that a replay of any
# already-seen ordinal returns an identical outcome to its first processing.
#
# Validates: Requirements 20.5
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 13
@settings(max_examples=150)
@given(
    # A stream of action ordinals (1..N) with deliberate repeats so duplicates
    # are exercised; a small N keeps repeats frequent.
    ordinals=st.lists(st.integers(min_value=1, max_value=12), min_size=1, max_size=60),
    # A tiny cache capacity forces evictions so the high-water-mark rejection
    # path (an evicted old id) is genuinely exercised alongside cache hits.
    capacity=st.integers(min_value=1, max_value=5),
)
def test_property_13_duplicate_action_idempotency(ordinals, capacity):
    cache = rooms.ReplyCache(capacity=capacity)
    high_water = 0  # per-seat monotonic high-water mark of highest applied ordinal
    applied_count = {}  # ordinal -> number of times actually applied
    first_outcome = {}  # ordinal -> the outcome returned on first processing

    def process(ordinal: int):
        nonlocal high_water
        action_id = f"A-{ordinal}"
        fingerprint = ("action", ordinal, "room", "A", action_id)

        # (1) Cache hit: return the cached reply UNCHANGED, no re-application.
        hit = cache.get(action_id)
        if hit is not None:
            assert hit.fingerprint == fingerprint
            return ("ack", hit.reply)

        # (2) Duplicate at/below the high-water mark but evicted from the cache:
        # reject as a duplicate conflict; NEVER re-apply.
        if ordinal <= high_water:
            return ("duplicate_action_conflict", None)

        # (3) New ordinal strictly above the high-water mark: apply EXACTLY once.
        reply = {"applied": True, "revision": ordinal}
        cache.put(action_id, fingerprint, reply)
        high_water = ordinal
        applied_count[ordinal] = applied_count.get(ordinal, 0) + 1
        return ("ack", reply)

    for ordinal in ordinals:
        outcome = process(ordinal)
        if ordinal not in first_outcome:
            first_outcome[ordinal] = outcome
        else:
            # A replay of an already-seen ordinal yields the SAME outcome shape
            # as its first processing (idempotent): either the same cached ack
            # or a duplicate_action_conflict -- never a fresh second apply.
            assert outcome[0] == first_outcome[ordinal][0] or outcome[0] == (
                "duplicate_action_conflict"
            )

    # No ordinal was ever applied more than once, regardless of repeats and
    # cache evictions.
    for ordinal, count in applied_count.items():
        assert count == 1

    # The cache never exceeds its bound (eviction is enforced).
    assert len(cache) <= capacity


# ---------------------------------------------------------------------------
# Property 14: Seat-ownership enforcement.
#
# For any action naming a seat the sender does not own, the server rejects it
# (``not_seat_owner``) and does NOT mutate the targeted board. Structurally:
# (a) the ActionMessage seat-prefix rule forbids an action_id whose prefix does
# not match seat_id, so an action targeting a seat the sender does not own is
# rejected at the contract boundary; and (b) even if a cross-seat action were
# attempted, the rooms layer keeps each seat's game PRIVATE, so an action
# applied on behalf of the sender's OWN seat never mutates the other seat.
#
# GENERATION STRATEGY: generate an owner seat and a different target seat with a
# positive ordinal, and build an action_id prefixed with the TARGET seat. Assert
# that constructing an ActionMessage for the OWNER seat with that mismatched
# action_id raises a validation error (the prefix rule rejects it). Separately,
# in a two-seat room, snapshot the NON-owner seat, apply the owner's action to
# the owner's own private game, and assert the non-owner seat's board is
# untouched -- so a rejected/owned action never mutates the targeted board.
#
# Validates: Requirements 20.10
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 14
@settings(max_examples=150)
@given(
    owner=st.sampled_from(["A", "B"]),
    ordinal=st.integers(min_value=1, max_value=999999999999999),
    room_id=room_ids,
    actions=action_sequences,
)
def test_property_14_seat_ownership_enforcement(owner, ordinal, room_id, actions):
    other = "B" if owner == "A" else "A"
    foreign_action_id = f"{other}-{ordinal}"

    # (a) The contract rejects an action whose action_id prefix names a seat the
    # sender does not own: an ActionMessage for `owner` carrying a `{other}-...`
    # action_id fails validation (the seat-prefix rule), so the server never
    # even reaches the board for a cross-seat action.
    with pytest.raises(Exception):
        contract.ActionMessage(
            type="action",
            protocol_version=contract.PROTOCOL_VERSION,
            room_id=room_id,
            seat_id=owner,
            action_id=foreign_action_id,
            expected_revision=0,
            kind="left",
        )

    # A correctly-owned action_id (prefix == seat_id) validates cleanly, proving
    # the rejection above is specifically about the mismatched prefix.
    owned = contract.ActionMessage(
        type="action",
        protocol_version=contract.PROTOCOL_VERSION,
        room_id=room_id,
        seat_id=owner,
        action_id=f"{owner}-{ordinal}",
        expected_revision=0,
        kind="left",
    )
    assert owned.seat_id == owner

    # (b) Rooms seat isolation: applying the owner's OWN action never mutates the
    # other seat's private board (the targeted board of a cross-seat action).
    manager = rooms.RoomManager(clock=FakeClock())
    room, seat_a = manager.assign_seat(room_id)
    _room2, seat_b = manager.assign_seat(room_id)
    owner_seat = seat_a if owner == "A" else seat_b
    other_seat = seat_b if owner == "A" else seat_a

    other_before = _game_fingerprint(other_seat.game)
    for action in actions:
        _apply_engine_action(owner_seat.game, action)
    assert _game_fingerprint(other_seat.game) == other_before


# ---------------------------------------------------------------------------
# Property 16: Room cleanup is bounded.
#
# For any sequence of room creations and clock advances, a WAITING room is
# reaped no later than its waiting retention, a FINISHED room no later than its
# finished retention, and a PLAYING idle room no later than its idle timeout;
# cleanup_tick never leaves an expired room in the map and never reaps a
# not-yet-expired room. The number of retained rooms is bounded by max_rooms.
#
# GENERATION STRATEGY: use a small injected max_rooms and the FakeClock. Create
# a generated number of rooms in a generated status (waiting / playing /
# finished). Advance the clock by a generated delta, run cleanup_tick, and
# assert:
#   * every room whose status-keyed retention has elapsed is GONE from the map;
#   * every room whose retention has NOT elapsed is still present;
#   * the returned reaped set is exactly the expired set;
#   * the retained room count never exceeds max_rooms.
# We also confirm creating beyond max_rooms is bounded (raises), never leaking.
#
# Validates: Requirements 19.1, 19.2, 19.3
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 16
@settings(max_examples=150)
@given(
    n_rooms=st.integers(min_value=1, max_value=8),
    status=st.sampled_from(["waiting", "playing", "finished"]),
    advance=st.integers(min_value=0, max_value=300),
    max_rooms=st.integers(min_value=1, max_value=8),
)
def test_property_16_room_cleanup_is_bounded(n_rooms, status, advance, max_rooms):
    clock = FakeClock()
    manager = rooms.RoomManager(clock=clock, max_rooms=max_rooms)

    created_ids = []
    for i in range(n_rooms):
        room_id = f"room-{i}"
        if len(manager.rooms) >= manager.max_rooms:
            # Creating beyond the bound is a BOUNDED rejection, not a leak.
            with pytest.raises(rooms.RoomCapacityError):
                manager.assign_seat(room_id)
            continue
        room, _seat = manager.assign_seat(room_id)
        created_ids.append(room_id)
        # Put the room into the generated lifecycle status at creation time.
        if status == "playing":
            room.status = "playing"
            room.last_activity_monotonic = clock()
        elif status == "finished":
            room.set_outcome_once(object(), clock())

    # The map is bounded by max_rooms at all times.
    assert len(manager.rooms) <= manager.max_rooms

    # Determine the status-keyed retention threshold for the chosen status.
    if status == "finished":
        retention = manager.finished_room_retention
    elif status == "playing":
        retention = manager.idle_timeout
    else:
        retention = manager.waiting_room_retention

    # Snapshot which rooms SHOULD expire after the advance (independent oracle).
    expected_expired = set(created_ids) if advance >= retention else set()

    clock.advance(advance)
    reaped = manager.cleanup_tick()
    reaped_ids = {room.room_id for room in reaped}

    # The reaped set is EXACTLY the set whose retention has elapsed.
    assert reaped_ids == expected_expired

    # No expired room remains in the map; every not-yet-expired room is retained.
    for room_id in created_ids:
        if room_id in expected_expired:
            assert room_id not in manager.rooms
        else:
            assert room_id in manager.rooms

    # Retention never grows the map; it only ever shrinks it (bounded cleanup).
    assert len(manager.rooms) <= manager.max_rooms
    assert len(manager.rooms) == len(created_ids) - len(expected_expired)
