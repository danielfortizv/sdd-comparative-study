"""Independent-oracle rotation table unit tests (Stage 4, M1 / task 2.3).

Requirements: 9.1, 9.2, 9.3, 2.3, 2.4, 2.5, 2.7.

CRITICAL independence note (Req 9.1): the expected per-piece per-orientation
occupied-cell tables below are declared INDEPENDENTLY and literally in this
module. They are the test oracle and are deliberately NOT imported from
``rotation.ORIENTATIONS`` (importing the module's own table as the expected
value would make the test tautological). Every assertion compares the engine's
``rotation.cells_for`` output against these hand-written literals.

Cells are compared as SETS (order-independent), since the engine may emit its
four cells in a fixed table order that need not match the literal order here.

Task boundary: this module intentionally contains ONLY the table/oracle tests
for task 2.3. The deterministic kick/reject/O/I fixture tests belong to task
2.6 and are added to this same module later; they are intentionally absent here.
"""

from __future__ import annotations

import pytest

from app.domain.models import ActivePiece, Game, empty_board
from app.rules import engine, pieces, rotation


# ---------------------------------------------------------------------------
# Independently-declared expected tables (the ORACLE). Hand-written literals.
# ORIENTATION_ORACLE[type][orientation_index] -> list of 4 (row, col) offsets
# from the piece origin. These MUST NOT be sourced from rotation.ORIENTATIONS.
# ---------------------------------------------------------------------------
ORIENTATION_ORACLE = {
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # o0: spawn0 horizontal on row 0
        [(0, 3), (1, 3), (2, 3), (3, 3)],   # o1: cw  -> vertical in column 3
        [(3, 0), (3, 1), (3, 2), (3, 3)],   # o2: 180 -> horizontal on row 3
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # o3: ccw -> vertical in column 0
    ],
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],   # o0
        [(0, 1), (1, 1), (1, 2), (2, 1)],   # o1
        [(1, 0), (1, 1), (1, 2), (2, 1)],   # o2
        [(0, 1), (1, 0), (1, 1), (2, 1)],   # o3
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],   # o0
        [(0, 1), (1, 1), (1, 2), (2, 2)],   # o1
        [(1, 1), (1, 2), (2, 0), (2, 1)],   # o2
        [(0, 0), (1, 0), (1, 1), (2, 1)],   # o3
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],   # o0
        [(0, 2), (1, 1), (1, 2), (2, 1)],   # o1
        [(1, 0), (1, 1), (2, 1), (2, 2)],   # o2
        [(0, 1), (1, 0), (1, 1), (2, 0)],   # o3
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],   # o0
        [(0, 1), (0, 2), (1, 1), (2, 1)],   # o1
        [(1, 0), (1, 1), (1, 2), (2, 2)],   # o2
        [(0, 1), (1, 1), (2, 0), (2, 1)],   # o3
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],   # o0
        [(0, 1), (1, 1), (2, 1), (2, 2)],   # o1
        [(1, 0), (1, 1), (1, 2), (2, 0)],   # o2
        [(0, 0), (0, 1), (1, 1), (2, 1)],   # o3
    ],
}

ALL_TYPES = ["I", "O", "T", "S", "Z", "J", "L"]

# Representative in-bounds origins. Max offset is row 3 / col 3, so origin (0,0)
# keeps every table cell in-bounds; (5, 4) is a second representative interior
# origin that also stays within the 20x10 board for all orientations.
REPRESENTATIVE_ORIGINS = [(0, 0), (5, 4)]


def _expected_abs(piece_type, orientation, origin):
    """Absolute cells from the independent oracle (NOT from rotation.py)."""
    row0, col0 = origin
    return {(row0 + dr, col0 + dc) for dr, dc in ORIENTATION_ORACLE[piece_type][orientation]}


# ---------------------------------------------------------------------------
# cells_for matches the independent oracle for every (type, orientation, origin)
# Requirements: 9.1, 9.2, 9.3, 2.5
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("piece_type", ALL_TYPES)
@pytest.mark.parametrize("orientation", [0, 1, 2, 3])
@pytest.mark.parametrize("origin", REPRESENTATIVE_ORIGINS)
def test_cells_for_matches_independent_oracle(piece_type, orientation, origin):
    actual = set(rotation.cells_for(piece_type, orientation, origin))
    expected = _expected_abs(piece_type, orientation, origin)
    assert actual == expected


# Also assert at origin (0,0) specifically so the raw offsets are directly
# visible in a focused failure (Req 9.3).
@pytest.mark.parametrize("piece_type", ALL_TYPES)
@pytest.mark.parametrize("orientation", [0, 1, 2, 3])
def test_cells_for_offsets_visible_at_origin_zero(piece_type, orientation):
    actual = set(rotation.cells_for(piece_type, orientation, (0, 0)))
    expected = {(dr, dc) for dr, dc in ORIENTATION_ORACLE[piece_type][orientation]}
    assert actual == expected


# Every orientation yields exactly four distinct cells (Req 2.5, 2.6).
@pytest.mark.parametrize("piece_type", ALL_TYPES)
@pytest.mark.parametrize("orientation", [0, 1, 2, 3])
def test_every_orientation_has_four_distinct_cells(piece_type, orientation):
    cells = rotation.cells_for(piece_type, orientation, (0, 0))
    assert len(cells) == 4
    assert len(set(cells)) == 4


# ---------------------------------------------------------------------------
# Orientation 0 of every piece equals that piece's spawn0 set (pieces.SHAPES).
# Requirements: 2.3
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("piece_type", ALL_TYPES)
def test_orientation_zero_equals_spawn0(piece_type):
    spawn0 = set(pieces.SHAPES[piece_type])
    o0 = set(rotation.cells_for(piece_type, 0, (0, 0)))
    assert o0 == spawn0
    # Oracle sanity: the independent oracle's o0 also equals spawn0.
    assert {(dr, dc) for dr, dc in ORIENTATION_ORACLE[piece_type][0]} == spawn0


# ---------------------------------------------------------------------------
# I piece uses the corrected fixed-pivot (1.5, 1.5) row-0 spawn geometry across
# all four orientations (Req 2.3, 2.5). Asserted against the independent oracle.
# ---------------------------------------------------------------------------
def test_i_piece_fixed_pivot_row0_geometry():
    # Independent oracle literals for the I piece, re-stated for emphasis.
    assert ORIENTATION_ORACLE["I"][0] == [(0, 0), (0, 1), (0, 2), (0, 3)]
    assert ORIENTATION_ORACLE["I"][1] == [(0, 3), (1, 3), (2, 3), (3, 3)]
    assert ORIENTATION_ORACLE["I"][2] == [(3, 0), (3, 1), (3, 2), (3, 3)]
    assert ORIENTATION_ORACLE["I"][3] == [(0, 0), (1, 0), (2, 0), (3, 0)]

    # The engine's cells_for matches each independently-declared orientation.
    assert set(rotation.cells_for("I", 0, (0, 0))) == {(0, 0), (0, 1), (0, 2), (0, 3)}
    assert set(rotation.cells_for("I", 1, (0, 0))) == {(0, 3), (1, 3), (2, 3), (3, 3)}
    assert set(rotation.cells_for("I", 2, (0, 0))) == {(3, 0), (3, 1), (3, 2), (3, 3)}
    assert set(rotation.cells_for("I", 3, (0, 0))) == {(0, 0), (1, 0), (2, 0), (3, 0)}


# ---------------------------------------------------------------------------
# O rotation is a FULL no-op in BOTH directions, exercised at the ENGINE level:
# the orientation index AND the occupied cells are unchanged (Req 2.4, 2.7).
# ---------------------------------------------------------------------------
def _o_game():
    """Build a playing game whose active piece is an O at a safe interior origin."""
    game = Game(
        id="o-test",
        status="playing",
        board=empty_board(),
        active=None,
        rng=__import__("random").Random(1),
        seed=1,
        bag=[],
    )
    origin = (5, 4)
    cells = rotation.cells_for("O", 0, origin)
    game.active = ActivePiece(type="O", origin=origin, cells=cells, orientation=0)
    return game


def test_engine_rotate_o_cw_is_full_no_op():
    game = _o_game()
    before_orientation = game.active.orientation
    before_origin = game.active.origin
    before_cells = set(game.active.cells)

    engine.rotate(game, "cw")

    assert game.active.orientation == before_orientation
    assert game.active.origin == before_origin
    assert set(game.active.cells) == before_cells


def test_engine_rotate_o_ccw_is_full_no_op():
    game = _o_game()
    before_orientation = game.active.orientation
    before_origin = game.active.origin
    before_cells = set(game.active.cells)

    engine.rotate(game, "ccw")

    assert game.active.orientation == before_orientation
    assert game.active.origin == before_origin
    assert set(game.active.cells) == before_cells


def test_engine_rotate_o_repeated_both_directions_no_op():
    game = _o_game()
    before_orientation = game.active.orientation
    before_cells = set(game.active.cells)
    for direction in ("cw", "cw", "ccw", "ccw", "cw", "ccw"):
        engine.rotate(game, direction)
    assert game.active.orientation == before_orientation
    assert set(game.active.cells) == before_cells


# ===========================================================================
# TASK 2.6 -- Deterministic kick / reject / first-fit fixture tests.
# Requirements: 9.4, 9.5, 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5.
#
# These are HAND-COMPUTED, scenario-driven fixtures. Each expected accepted
# cell set and origin is derived literally from rotation.ORIENTATIONS (see the
# ORIENTATION_ORACLE above) and the engine's column-only kick order
# 0, -1, +1, -2, +2 -- NOT by calling engine.rotate on the same inputs and
# reading back the answer. The scenario is constructed, the concrete expected
# outcome is written as literals, and engine.rotate's result is asserted
# against those literals.
#
# Board is 20 rows (0..19) x 10 cols (0..9); a cell is occupied by a PieceType
# or empty (None). Kicks are COLUMN-only: no row offset is ever applied, so a
# piece that can only be made to fit by moving UP must be REJECTED (no floor
# kick). This section is additive and does not touch the task-2.3 oracle tests.
# ===========================================================================

import random as _random


def _playing_game(active_type, origin, orientation=0, board=None):
    """Build a playing game with a controlled active piece at (orientation, origin).

    The active cells are computed from rotation.cells_for for the GIVEN current
    orientation (the pre-rotation state); the expected POST-rotation cells in
    each test are independent hand-written literals, so this helper only sets up
    the starting position and never supplies the asserted answer.
    """
    game = Game(
        id="kick-test",
        status="playing",
        board=board if board is not None else empty_board(),
        active=None,
        rng=_random.Random(1),
        seed=1,
        bag=[],
    )
    cells = rotation.cells_for(active_type, orientation, origin)
    game.active = ActivePiece(
        type=active_type, origin=origin, cells=cells, orientation=orientation
    )
    return game


# ---------------------------------------------------------------------------
# 1. LEFT-WALL kick (Req 3.1, 3.2, 3.4).
#
# T piece, current orientation 0, rotate CCW -> target orientation 3.
# ORIENTATION_ORACLE["T"][3] = [(0,1),(1,0),(1,1),(2,1)].
# Start origin = (5, -1) so the raw rotation (offset 0) places a cell at col -1.
#   offset  0 -> col0 = -1: abs cols {0,-1,0,0}  -> col -1 OUT OF BOUNDS (fail)
#   offset -1 -> col0 = -2: abs cols {-1,-2,-1,-1} -> OUT OF BOUNDS (fail)
#   offset +1 -> col0 =  0: abs cols {1,0,1,1}   -> all in 0..9 (FIRST FIT)
# Accepted origin = (5, 0); accepted cells (hand-computed from the oracle):
#   (5+0,0+1)=(5,1) (5+1,0+0)=(6,0) (5+1,0+1)=(6,1) (5+2,0+1)=(7,1)
# ---------------------------------------------------------------------------
def test_left_wall_kick_selects_first_fitting_offset():
    game = _playing_game("T", origin=(5, -1), orientation=0)

    engine.rotate(game, "ccw")

    assert game.active.orientation == 3
    assert game.active.origin == (5, 0)  # raw(0) and -1 rejected; +1 accepted
    assert set(game.active.cells) == {(5, 1), (6, 0), (6, 1), (7, 1)}
    # All accepted cells are in bounds.
    for r, c in game.active.cells:
        assert 0 <= r <= 19 and 0 <= c <= 9


# ---------------------------------------------------------------------------
# 2. RIGHT-WALL kick (Req 3.1, 3.2, 3.4).
#
# T piece, current orientation 0, rotate CW -> target orientation 1.
# ORIENTATION_ORACLE["T"][1] = [(0,1),(1,1),(1,2),(2,1)].
# Start origin = (5, 8) so the raw rotation (offset 0) places a cell at col 10.
#   offset  0 -> col0 = 8: abs cols {9,9,10,9} -> col 10 OUT OF BOUNDS (fail)
#   offset -1 -> col0 = 7: abs cols {8,8,9,8}  -> all in 0..9 (FIRST FIT)
# Accepted origin = (5, 7); accepted cells (hand-computed from the oracle):
#   (5,8) (6,8) (6,9) (7,8)
# ---------------------------------------------------------------------------
def test_right_wall_kick_selects_first_fitting_negative_offset():
    game = _playing_game("T", origin=(5, 8), orientation=0)

    engine.rotate(game, "cw")

    assert game.active.orientation == 1
    assert game.active.origin == (5, 7)  # raw(0) rejected; -1 accepted
    assert set(game.active.cells) == {(5, 8), (6, 8), (6, 9), (7, 8)}
    for r, c in game.active.cells:
        assert 0 <= r <= 19 and 0 <= c <= 9


# ---------------------------------------------------------------------------
# 3. FLOOR case -> REJECTION, because kicks are COLUMN-only (Req 3.3, 4.*).
#
# I piece, current orientation 0, rotate CW -> target orientation 1.
# ORIENTATION_ORACLE["I"][1] = [(0,3),(1,3),(2,3),(3,3)] -> rows {r0,r0+1,r0+2,r0+3}.
# Start origin = (17, 3): the target rows become {17,18,19,20}. Row 20 is below
# the floor (max row 19). Every column offset leaves the ROWS unchanged, so all
# five candidates (0,-1,+1,-2,+2) keep the row-20 cell and all FAIL. There is no
# vertical kick, so the rotation is fully REJECTED and nothing changes: the
# piece stays horizontal at orientation 0, origin (17,3), cells on row 17.
# ---------------------------------------------------------------------------
def test_floor_case_is_rejected_because_kicks_are_column_only():
    game = _playing_game("I", origin=(17, 3), orientation=0)
    before_cells = set(game.active.cells)
    assert before_cells == {(17, 3), (17, 4), (17, 5), (17, 6)}  # sanity

    engine.rotate(game, "cw")

    # Rejected: orientation, origin, and cells all unchanged.
    assert game.active.orientation == 0
    assert game.active.origin == (17, 3)
    assert set(game.active.cells) == before_cells


# ---------------------------------------------------------------------------
# 4. LOCKED-CELL kick (Req 3.1, 3.4).
#
# T piece, current orientation 0, rotate CW -> target orientation 1.
# ORIENTATION_ORACLE["T"][1] = [(0,1),(1,1),(1,2),(2,1)].
# Start origin = (5, 4). Lock a settled block at (6, 6).
#   offset  0 -> col0 = 4: cells {(5,5),(6,5),(6,6),(7,5)} -> hits locked (6,6) (fail)
#   offset -1 -> col0 = 3: cells {(5,4),(6,4),(6,5),(7,4)} -> all empty+in-bounds (FIRST FIT)
# Accepted origin = (5, 3); accepted cells (hand-computed): (5,4)(6,4)(6,5)(7,4).
# ---------------------------------------------------------------------------
def test_locked_cell_kick_selects_first_clear_offset():
    board = empty_board()
    board[6][6] = "L"  # settled block that blocks ONLY the raw (offset 0) rotation
    game = _playing_game("T", origin=(5, 4), orientation=0, board=board)

    engine.rotate(game, "cw")

    assert game.active.orientation == 1
    assert game.active.origin == (5, 3)  # raw(0) overlaps locked cell; -1 accepted
    assert set(game.active.cells) == {(5, 4), (6, 4), (6, 5), (7, 4)}
    # The accepted cells never overlap the settled block.
    assert (6, 6) not in set(game.active.cells)
    assert game.board[6][6] == "L"  # the locked cell itself is untouched


# ---------------------------------------------------------------------------
# 5. FIRST-FIT PRIORITY: earlier candidate wins over a later fitting one
#    (Req 3.2, 3.4). This is the critical ordering test.
#
# T piece, current orientation 0, rotate CW -> target orientation 1.
# ORIENTATION_ORACLE["T"][1] = [(0,1),(1,1),(1,2),(2,1)].
# Start origin = (5, 4). Lock a settled block at (5, 5) ONLY.
#   offset  0 -> col0 = 4: cells {(5,5),(6,5),(6,6),(7,5)} -> hits locked (5,5) (fail)
#   offset -1 -> col0 = 3: cells {(5,4),(6,4),(6,5),(7,4)} -> all clear  (FITS, EARLIER)
#   offset +1 -> col0 = 5: cells {(5,6),(6,6),(6,7),(7,6)} -> all clear  (would FIT, LATER)
# (5,5) is unique to the raw offset-0 set: it is absent from both the -1 and +1
# candidate sets, so BOTH -1 and +1 are legal. The engine MUST take -1 (earlier
# in 0,-1,+1,-2,+2) and never consider +1.
# Accepted origin = (5, 3); accepted cells: (5,4)(6,4)(6,5)(7,4).
# ---------------------------------------------------------------------------
def test_first_fit_prefers_earlier_offset_over_later_fitting_offset():
    board = empty_board()
    board[5][5] = "Z"  # blocks ONLY raw offset 0; leaves both -1 and +1 legal
    game = _playing_game("T", origin=(5, 4), orientation=0, board=board)

    # Pre-compute the LATER (+1) candidate to prove it would have fit, so the
    # test genuinely demonstrates first-fit priority rather than "+1 was the
    # only option". These literals are hand-derived, not taken from rotate().
    plus_one_cells = {(5, 6), (6, 6), (6, 7), (7, 6)}
    for r, c in plus_one_cells:
        assert board[r][c] is None  # +1 really is a fitting candidate

    engine.rotate(game, "cw")

    assert game.active.orientation == 1
    # The EARLIER (-1) candidate is selected, not the later (+1) one.
    assert game.active.origin == (5, 3)
    assert set(game.active.cells) == {(5, 4), (6, 4), (6, 5), (7, 4)}
    # Explicitly assert the later fitting candidate was NOT used.
    assert game.active.origin != (5, 5)
    assert set(game.active.cells) != plus_one_cells


# ---------------------------------------------------------------------------
# 6. FULLY REJECTED rotation leaves EVERYTHING unchanged (Req 3.5, 4.1-4.5).
#
# Reuses the column-only floor impossibility: an I piece at origin (17,3)
# rotated CW needs row 20 for every one of the five column candidates, so the
# rotation is fully rejected. A complete snapshot of authoritative state is
# captured BEFORE the call and asserted unchanged AFTER, including orientation
# index and origin (which must be exactly the pre-request values).
# ---------------------------------------------------------------------------
def test_fully_rejected_rotation_is_completely_immutable():
    board = empty_board()
    # A few unrelated settled cells to confirm the board contents are untouched.
    board[19][0] = "J"
    board[19][1] = "J"
    game = _playing_game("I", origin=(17, 3), orientation=0, board=board)

    # Populate the full authoritative counter/queue/Hold surface so every field
    # has a concrete pre-request value to compare against.
    game.gravity_interval_ms = 350
    game.score = 1234
    game.level = 4
    game.total_lines = 37
    game.next_type = "S"
    game.hold_type = "Z"
    game.can_hold = False

    # --- Snapshot BEFORE ---
    before_orientation = game.active.orientation
    before_origin = game.active.origin
    before_cells = set(game.active.cells)
    before_type = game.active.type
    before_status = game.status
    before_gravity = game.gravity_interval_ms
    before_score = game.score
    before_level = game.level
    before_total_lines = game.total_lines
    before_next = game.next_type
    before_hold = game.hold_type
    before_can_hold = game.can_hold
    before_board = [row[:] for row in game.board]
    before_rng_state = game.rng.getstate()

    engine.rotate(game, "cw")

    # --- Assert UNCHANGED AFTER ---
    # orientation index and origin are EXACTLY the pre-request values.
    assert game.active.orientation == before_orientation
    assert game.active.origin == before_origin
    assert set(game.active.cells) == before_cells
    assert game.active.type == before_type
    assert game.status == before_status
    assert game.gravity_interval_ms == before_gravity
    assert game.score == before_score
    assert game.level == before_level
    assert game.total_lines == before_total_lines
    assert game.next_type == before_next   # next_piece unchanged
    assert game.hold_type == before_hold    # hold_piece unchanged
    assert game.can_hold == before_can_hold
    assert game.board == before_board       # full board contents unchanged
    # The generator was never drawn from (no spawn/lock/tick side effects).
    assert game.rng.getstate() == before_rng_state
