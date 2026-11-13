"""Hypothesis property-based tests for the Stage 4 rotation engine (M1).

This module hosts the numbered Correctness Properties from the Stage 4 Option A
design document. Each property is implemented as a single Hypothesis test using
MEANINGFUL generators (piece type, orientation index, board origin) and runs at
least 100 examples via ``@settings(max_examples=100)``.

These properties assert rotation INVARIANTS -- four-cycle identity, cw/ccw
inverse identity, the O-piece no-op, and four-distinct-in-bounds cells -- rather
than the specific cell geometry of any single orientation (the deterministic
geometry oracle lives in ``test_stage4_rotation.py``). It is therefore fine that
some properties read ``rotation.cells_for`` / ``rotation.ORIENTATIONS`` as the
system under test; none of them use the production table as an oracle for the
correctness of specific cells.

Task boundary: this file currently contains ONLY Properties 1-4 (task 2.4). The
section after Property 4 is intentionally left open for Properties 5-9, which
task 2.5 will APPEND to this same module later.
"""

from __future__ import annotations

import random

from hypothesis import given, settings, strategies as st

from app.domain.models import ActivePiece, Game, empty_board
from app.rules import engine, rotation


# ---------------------------------------------------------------------------
# Shared generators (meaningful input spaces, not trivial constants).
# ---------------------------------------------------------------------------
ALL_TYPES = ["I", "O", "T", "S", "Z", "J", "L"]
NON_O_TYPES = [t for t in ALL_TYPES if t != "O"]

# Orientation offsets span up to 3 rows / 3 cols beyond the origin (the I box is
# 4x4). To keep every candidate cell inside the 20x10 board (rows 0..19,
# cols 0..9) for ANY orientation, constrain generated origins to rows 0..16 and
# cols 0..6 so origin + 3 stays in bounds regardless of piece/orientation.
piece_types = st.sampled_from(ALL_TYPES)
non_o_types = st.sampled_from(NON_O_TYPES)
orientations = st.integers(min_value=0, max_value=3)
directions = st.sampled_from(["cw", "ccw"])
in_bounds_origins = st.tuples(
    st.integers(min_value=0, max_value=16),  # row0: row0 + 3 <= 19
    st.integers(min_value=0, max_value=6),   # col0: col0 + 3 <= 9
)


def _playing_game(piece_type, origin, orientation=0, board=None):
    """Build a 'playing' game with a controlled active piece at (orientation, origin)."""
    game = Game(
        id="prop-test",
        status="playing",
        board=board if board is not None else empty_board(),
        active=None,
        rng=random.Random(1),
        seed=1,
        bag=[],
    )
    cells = rotation.cells_for(piece_type, orientation, origin)
    game.active = ActivePiece(
        type=piece_type, origin=origin, cells=cells, orientation=orientation
    )
    return game


# ---------------------------------------------------------------------------
# Property 1: CW/CCW four-cycle identity (pure-table level).
#
# For any NON-O piece type and any starting orientation 0..3, four successive
# rotations in the SAME direction (cw, and separately ccw), with no intervening
# collision/movement/lock, restore BOTH the orientation index and the
# occupied-cell SET to their starting values. Verified purely via
# rotation.next_orientation + rotation.cells_for at a fixed in-bounds origin, so
# "no intervening collision" is guaranteed by construction.
#
# Validates: Requirements 2.3, 9.2
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 1
@settings(max_examples=200)
@given(piece_type=non_o_types, start=orientations, origin=in_bounds_origins)
def test_property_1_cw_ccw_four_cycle_identity(piece_type, start, origin):
    start_cells = set(rotation.cells_for(piece_type, start, origin))

    for direction in ("cw", "ccw"):
        orientation = start
        for _ in range(4):
            orientation = rotation.next_orientation(orientation, direction)
        # Four quarter-turns in the same direction return to the start index.
        assert orientation == start
        # ...and therefore to the identical occupied-cell set.
        assert set(rotation.cells_for(piece_type, orientation, origin)) == start_cells


# ---------------------------------------------------------------------------
# Property 2: CW then CCW is the identity.
#
# For any piece type (including O), orientation index, and in-bounds origin, a
# cw followed by a ccw (no intervening collision) restores the orientation index
# and the occupied-cell set. Exercised at the engine level on an empty board
# with the active piece placed at a SAFE in-bounds origin, so both the cw and the
# following ccw are accepted with column offset 0 (no kick) -- a genuine no-kick
# round trip identity.
#
# Validates: Requirements 2.7
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 2
@settings(max_examples=150)
@given(piece_type=piece_types, start=orientations, origin=in_bounds_origins)
def test_property_2_cw_then_ccw_is_identity(piece_type, start, origin):
    game = _playing_game(piece_type, origin, orientation=start)
    before_orientation = game.active.orientation
    before_origin = game.active.origin
    before_cells = set(game.active.cells)

    engine.rotate(game, "cw")
    engine.rotate(game, "ccw")

    # Orientation index, origin, and occupied-cell set are all restored. On the
    # fully in-bounds empty board both rotations take offset 0, so no kick can
    # shift the origin on the round trip.
    assert game.active.orientation == before_orientation
    assert game.active.origin == before_origin
    assert set(game.active.cells) == before_cells


# ---------------------------------------------------------------------------
# Property 3: O rotation is a no-op.
#
# For any in-bounds origin and either direction, rotating the O piece via
# engine.rotate leaves BOTH its occupied-cell set and its orientation index
# identical to before.
#
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 3
@settings(max_examples=150)
@given(origin=in_bounds_origins, direction=directions, start=orientations)
def test_property_3_o_rotation_is_no_op(origin, direction, start):
    game = _playing_game("O", origin, orientation=start)
    before_orientation = game.active.orientation
    before_origin = game.active.origin
    before_cells = set(game.active.cells)

    engine.rotate(game, direction)

    assert game.active.orientation == before_orientation
    assert game.active.origin == before_origin
    assert set(game.active.cells) == before_cells


# ---------------------------------------------------------------------------
# Property 4: Every orientation has exactly four distinct cells.
#
# For any piece type, orientation 0..3, and an origin that keeps every candidate
# cell inside the board, rotation.cells_for returns exactly four cells, all
# distinct, each within rows 0..19 and cols 0..9. The origin generator is
# constrained (rows 0..16, cols 0..6) so that origin + 3 stays in bounds for any
# orientation's offsets.
#
# Validates: Requirements 2.1, 2.5, 2.6
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 4
@settings(max_examples=200)
@given(piece_type=piece_types, orientation=orientations, origin=in_bounds_origins)
def test_property_4_every_orientation_has_four_distinct_in_bounds_cells(
    piece_type, orientation, origin
):
    cells = rotation.cells_for(piece_type, orientation, origin)

    # Exactly four cells, all distinct.
    assert len(cells) == 4
    assert len(set(cells)) == 4

    # Every cell is inside the 20x10 board.
    for row, col in cells:
        assert 0 <= row <= 19
        assert 0 <= col <= 9


# ===========================================================================
# TASK 2.5 -- Properties 5-9 (rejected-rotation immutability, accepted-rotation
# minimal change, wall-kick first-fit order, spawn/Hold orientation reset, and
# lock preserving rotated geometry) are APPENDED to this same module by a later
# invocation. This section is intentionally left open here.
# ===========================================================================

# ---------------------------------------------------------------------------
# Additional shared helpers for Properties 5-9 (task 2.5).
#
# These reuse the module-level generators and the _playing_game helper declared
# above for Properties 1-4; they add only what Properties 5-9 need without
# altering the existing section.
# ---------------------------------------------------------------------------

# Nonzero counter generators used to prove an accepted/rejected rotation never
# touches any authoritative scoring/level/queue/Hold field.
scores = st.integers(min_value=0, max_value=999999)
total_lines_vals = st.integers(min_value=0, max_value=200)
levels = st.integers(min_value=1, max_value=20)
gravity_ms_vals = st.integers(min_value=100, max_value=500)
piece_or_none = st.sampled_from([None, "I", "O", "T", "S", "Z", "J", "L"])
booleans = st.booleans()
seeds = st.integers(min_value=0, max_value=2**31 - 1)


def _authoritative_snapshot(game):
    """Snapshot every authoritative field a rotation must not change.

    Captures the full RNG state too, so we can prove a rotation never advances
    the seeded generator (which would shift the piece sequence).
    """
    active = game.active
    return {
        "status": game.status,
        "score": game.score,
        "level": game.level,
        "total_lines": game.total_lines,
        "next_type": game.next_type,
        "hold_type": game.hold_type,
        "can_hold": game.can_hold,
        "gravity_interval_ms": game.gravity_interval_ms,
        "board": [row[:] for row in game.board],
        "rng_state": game.rng.getstate(),
        "active_type": None if active is None else active.type,
        "active_origin": None if active is None else active.origin,
        "active_orientation": None if active is None else active.orientation,
        "active_cells": None if active is None else list(active.cells),
    }


def _apply_counters(game, score, total_lines, level, gravity_ms,
                    next_type, hold_type, can_hold):
    """Force nonzero / varied authoritative counters onto a hand-built game."""
    game.score = score
    game.total_lines = total_lines
    game.level = level
    game.gravity_interval_ms = gravity_ms
    game.next_type = next_type
    game.hold_type = hold_type
    game.can_hold = can_hold


def _firstfit_oracle(board, piece_type, target, origin):
    """Independent re-implementation of the engine's column-only first-fit search.

    Returns the (origin, cells) of the FIRST candidate, evaluating column
    offsets in the exact order 0, -1, +1, -2, +2, whose cells are all in bounds
    (rows 0..19, cols 0..9) and overlap no occupied board cell. Returns None if
    no candidate fits. Deliberately does NOT call engine code so it is a true
    oracle for Property 7.
    """
    row0, col0 = origin
    for dc in [0, -1, 1, -2, 2]:
        cand_origin = (row0, col0 + dc)
        cells = rotation.cells_for(piece_type, target, cand_origin)
        ok = True
        for r, c in cells:
            if r < 0 or r > 19 or c < 0 or c > 9 or board[r][c] is not None:
                ok = False
                break
        if ok:
            return cand_origin, cells
    return None


# ---------------------------------------------------------------------------
# Property 5: Rejected rotation is fully immutable.
#
# For any game state in which the raw rotation AND every kick candidate collide,
# a rotation request leaves the active piece's origin and orientation index, and
# score/level/total_lines/next_piece/hold_piece/can_hold/gravity_interval_ms/
# board/status, all equal to their pre-request values.
#
# GENERATION STRATEGY: build a guaranteed-rejection scenario. Use the I piece in
# a HORIZONTAL current orientation (0) at row 17 on an empty board: a cw turn
# targets the vertical orientation 1 (cells at row offsets 0..3 -> rows 17..20)
# and a ccw turn targets the vertical orientation 3 (also row offsets 0..3).
# Either target reaches row 20, which is off the floor (ROWS == 20), for EVERY
# column candidate, since kicks are column-only and never change a row. So the
# raw rotation and all four kick candidates collide by construction. We vary the
# column, direction, and all authoritative counters, snapshot everything
# (including the RNG state), rotate, and assert nothing changed.
#
# Validates: Requirements 3.5, 4.1, 4.2, 4.3, 4.4, 4.5
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 5
@settings(max_examples=150)
@given(
    col0=st.integers(min_value=0, max_value=6),
    direction=directions,
    score=scores,
    total_lines=total_lines_vals,
    level=levels,
    gravity_ms=gravity_ms_vals,
    next_type=piece_or_none,
    hold_type=piece_or_none,
    can_hold=booleans,
    seed=seeds,
)
def test_property_5_rejected_rotation_is_fully_immutable(
    col0, direction, score, total_lines, level, gravity_ms,
    next_type, hold_type, can_hold, seed,
):
    # I piece, horizontal current orientation 0, origin row 17 -> any rotation
    # target is vertical (rows 17..20) and collides with the floor for every
    # column candidate (kicks are column-only).
    origin = (17, col0)
    game = _playing_game("I", origin, orientation=0)
    game.rng = random.Random(seed)
    _apply_counters(
        game, score, total_lines, level, gravity_ms,
        next_type, hold_type, can_hold,
    )

    # Sanity: confirm this really is a guaranteed-rejection scenario by checking
    # the raw target and every kick candidate are out of bounds / colliding.
    target = rotation.next_orientation(game.active.orientation, direction)
    assert _firstfit_oracle(game.board, "I", target, origin) is None

    before = _authoritative_snapshot(game)
    engine.rotate(game, direction)
    after = _authoritative_snapshot(game)

    assert after == before


# ---------------------------------------------------------------------------
# Property 6: Accepted rotation changes only orientation and (on a kick) origin.
#
# For any game state and ACCEPTED rotation, the only authoritative fields that
# change are the active piece's orientation index and (on a kick) its origin and
# derived cells; score/level/total_lines/next_piece/hold_piece/can_hold/
# gravity_interval_ms are unchanged, and the piece is neither locked nor advanced
# by gravity (status stays playing, board unchanged, the active piece still
# exists).
#
# GENERATION STRATEGY: place a non-O piece on an EMPTY board at a safe in-bounds
# origin (rows 0..16, cols 0..6) so the rotation is ALWAYS accepted with column
# offset 0 (no kick). Set nonzero/varied counters, rotate, then assert the
# counters/board/status are unchanged, the active piece still exists, the origin
# is unchanged (offset 0 was accepted) and the orientation advanced by exactly
# the expected next_orientation.
#
# Validates: Requirements 5.1, 5.2, 5.3, 5.4
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 6
@settings(max_examples=150)
@given(
    piece_type=non_o_types,
    start=orientations,
    origin=in_bounds_origins,
    direction=directions,
    score=scores,
    total_lines=total_lines_vals,
    level=levels,
    gravity_ms=gravity_ms_vals,
    next_type=piece_or_none,
    hold_type=piece_or_none,
    can_hold=booleans,
    seed=seeds,
)
def test_property_6_accepted_rotation_changes_only_orientation(
    piece_type, start, origin, direction, score, total_lines, level,
    gravity_ms, next_type, hold_type, can_hold, seed,
):
    game = _playing_game(piece_type, origin, orientation=start)
    game.rng = random.Random(seed)
    _apply_counters(
        game, score, total_lines, level, gravity_ms,
        next_type, hold_type, can_hold,
    )

    before = _authoritative_snapshot(game)
    expected_target = rotation.next_orientation(start, direction)

    engine.rotate(game, direction)

    # On a fully in-bounds empty board the offset-0 candidate always fits, so the
    # rotation is accepted and never kicks.
    assert game.active is not None  # not locked / not cleared
    assert game.status == "playing"  # no gravity advance, no lock

    # Orientation advanced exactly to the expected next orientation.
    assert game.active.orientation == expected_target
    # No kick: origin unchanged, cells are the rotated cells at the same origin.
    assert game.active.origin == before["active_origin"]
    assert set(game.active.cells) == set(
        rotation.cells_for(piece_type, expected_target, origin)
    )

    # No authoritative scoring/level/queue/Hold/board/RNG field changed.
    assert game.score == before["score"]
    assert game.level == before["level"]
    assert game.total_lines == before["total_lines"]
    assert game.next_type == before["next_type"]
    assert game.hold_type == before["hold_type"]
    assert game.can_hold == before["can_hold"]
    assert game.gravity_interval_ms == before["gravity_interval_ms"]
    assert [row[:] for row in game.board] == before["board"]
    assert game.rng.getstate() == before["rng_state"]


# ---------------------------------------------------------------------------
# Property 7: Wall-kick first-fit in the exact order.
#
# For any game state where a rotation is accepted, the accepted result is the
# FIRST candidate in the column order 0, -1, +1, -2, +2 whose column-only-offset
# cell set is fully in bounds and overlaps no locked cell; no later candidate is
# selected when an earlier one fits.
#
# GENERATION STRATEGY: generate a non-O piece type, current orientation, origin,
# direction, and a small set of random locked cells (excluding the piece's own
# current cells, so the starting state is itself valid). Independently compute
# the first-fit result with _firstfit_oracle (a re-implementation that never
# calls engine code), run engine.rotate, and assert the engine's outcome matches
# the oracle exactly: both reject -> everything unchanged, or both accept the
# SAME origin and the SAME occupied-cell set. This proves the engine selects the
# first-fit candidate in the exact order.
#
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 7
@settings(max_examples=200)
@given(
    piece_type=non_o_types,
    start=orientations,
    origin=in_bounds_origins,
    direction=directions,
    locked=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=19),
            st.integers(min_value=0, max_value=9),
        ),
        max_size=12,
    ),
)
def test_property_7_wall_kick_first_fit_in_exact_order(
    piece_type, start, origin, direction, locked
):
    board = empty_board()
    # The piece's own current cells must stay clear so the starting state is
    # valid; lock every OTHER generated cell as a settled block.
    current_cells = set(rotation.cells_for(piece_type, start, origin))
    for (r, c) in locked:
        if (r, c) not in current_cells:
            board[r][c] = piece_type

    game = _playing_game(piece_type, origin, orientation=start, board=board)

    target = rotation.next_orientation(start, direction)
    oracle = _firstfit_oracle(board, piece_type, target, origin)

    before = _authoritative_snapshot(game)
    engine.rotate(game, direction)

    if oracle is None:
        # No candidate fits -> the engine must reject and change nothing.
        assert _authoritative_snapshot(game) == before
    else:
        oracle_origin, oracle_cells = oracle
        # The engine must accept exactly the first-fit candidate the oracle chose.
        assert game.active is not None
        assert game.active.orientation == target
        assert game.active.origin == oracle_origin
        assert set(game.active.cells) == set(oracle_cells)
        # Still playing; nothing locked or scored.
        assert game.status == "playing"
        assert game.score == before["score"]
        assert game.rng.getstate() == before["rng_state"]


# ---------------------------------------------------------------------------
# Property 8: Spawn and Hold reset orientation to 0.
#
# For any sequence of rotations followed by a spawn or either Hold path, the
# piece that enters play has orientation index 0 at the spawn origin, regardless
# of its prior orientation.
#
# GENERATION STRATEGY: use engine.new_game(seed) with a generated seed; apply a
# generated number of rotations to the active piece (building up a nonzero
# orientation for non-O pieces); then trigger each entry path and assert the
# newly-entered active piece has orientation 0 at SPAWN_ORIGIN:
#   (a) lock -> spawn: force a lock via repeated engine.tick until a NEW piece
#       spawns (origin returns to SPAWN_ORIGIN), then check it.
#   (b) first-Hold path: engine.hold on a fresh game with an empty hold slot.
#   (c) swap-Hold path: re-enable Hold (lock the held-against piece) then hold
#       again to exercise the occupied-slot swap.
# Everything is deterministic per generated seed.
#
# Validates: Requirements 6.1, 6.2, 6.3, 6.4
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 8
@settings(max_examples=150)
@given(seed=seeds, rotations=st.integers(min_value=0, max_value=6),
       direction=directions)
def test_property_8_spawn_and_hold_reset_orientation_to_zero(
    seed, rotations, direction
):
    spawn_origin = engine.SPAWN_ORIGIN

    # (a) lock -> spawn path. Drive the current piece to lock; the FIRST tick
    # after which a different active-piece object appears is the spawn moment.
    # We must inspect the newly-spawned piece at that exact moment, before any
    # further gravity tick can move it off the spawn origin.
    game = engine.new_game("prop8-spawn", seed)
    for _ in range(rotations):
        engine.rotate(game, direction)
    original_piece = game.active
    for _ in range(40):
        engine.tick(game)
        if game.status != "playing" or game.active is None:
            break
        if game.active is not original_piece:
            # A brand-new piece has just entered play via lock -> spawn.
            assert game.active.orientation == 0
            assert game.active.origin == spawn_origin
            break

    # (b) first-Hold path (empty hold slot).
    game_b = engine.new_game("prop8-hold1", seed)
    for _ in range(rotations):
        engine.rotate(game_b, direction)
    engine.hold(game_b)
    assert game_b.active is not None
    assert game_b.active.orientation == 0
    assert game_b.active.origin == spawn_origin

    # (c) swap-Hold path (occupied hold slot). Re-enable Hold by locking the
    # current piece (tick until a new piece spawns and can_hold is restored),
    # then rotate and Hold again to trigger the occupied-slot swap.
    held_against = game_b.active
    for _ in range(40):
        engine.tick(game_b)
        if game_b.status != "playing" or game_b.active is None:
            break
        if game_b.active is not held_against and game_b.can_hold:
            break
    if game_b.status == "playing" and game_b.active is not None and game_b.can_hold:
        for _ in range(rotations):
            engine.rotate(game_b, direction)
        engine.hold(game_b)  # occupied-slot swap
        assert game_b.active is not None
        assert game_b.active.orientation == 0
        assert game_b.active.origin == spawn_origin


# ---------------------------------------------------------------------------
# Property 9: Lock preserves rotated geometry.
#
# For any rotated active piece that locks, the settled board contains exactly the
# rotated occupied-cell set (translated by any moves) after the lock, and the
# inherited lock/clear/score/spawn ordering is applied.
#
# GENERATION STRATEGY: construct a controlled game on an EMPTY board with a non-O
# piece placed high (at the safe in-bounds origin generator), apply an ACCEPTED
# rotation (offset 0 on the empty board), record the rotated occupied cells, then
# lock via a direct engine.lock call. Only four cells settle so no line can clear
# (a full row needs ten), hence the settled cells remain in the board. Assert
# every rotated cell is now occupied by that piece type, and that the inherited
# ordering ran (a new piece spawned at SPAWN_ORIGIN and can_hold was re-enabled).
#
# Validates: Requirements 7.1, 7.2, 7.3
# ---------------------------------------------------------------------------
# Feature: tetris-stage4-option-a, Property 9
@settings(max_examples=150)
@given(
    piece_type=non_o_types,
    start=orientations,
    origin=in_bounds_origins,
    direction=directions,
    seed=seeds,
)
def test_property_9_lock_preserves_rotated_geometry(
    piece_type, start, origin, direction, seed
):
    game = _playing_game(piece_type, origin, orientation=start)
    # Give the game a preview piece and seeded RNG so lock -> spawn has something
    # to draw (hand-built games start with next_type = None; the engine lazily
    # initializes it, but we set it explicitly for a deterministic spawn).
    game.rng = random.Random(seed)
    game.next_type = None  # engine.lock -> spawn will lazily draw a preview
    game.can_hold = False  # lock must re-enable Hold (inherited ordering)

    # Accepted rotation on the empty board (offset 0); record the rotated cells.
    engine.rotate(game, direction)
    assert game.active is not None
    rotated_cells = set(game.active.cells)
    rotated_type = game.active.type

    engine.lock(game)

    # The four rotated cells are now settled with the rotated piece's type. Four
    # cells can never complete a ten-wide row, so no clear removes them.
    for (r, c) in rotated_cells:
        assert game.board[r][c] == rotated_type

    # Inherited lock/clear/score/Hold/spawn ordering ran. can_hold is re-enabled
    # before the spawn on every lock path, so it is True regardless of whether
    # the subsequent spawn succeeds.
    assert game.can_hold is True

    # The spawn that follows the lock either places a new piece at the canonical
    # spawn origin at orientation 0, or -- when the just-settled rotated cells
    # obstruct the spawn origin -- ends the game (the inherited spawn-collision
    # behavior). Either way the rotated geometry above is preserved on the board.
    if game.status == "playing":
        assert game.active is not None
        assert game.active.origin == engine.SPAWN_ORIGIN
        assert game.active.orientation == 0
    else:
        assert game.status == "game_over"
        assert game.active is None
