"""Unit tests for the pure game rules (no HTTP layer)."""

from __future__ import annotations

import random

import pytest

from app.domain.models import COLS, ROWS, ActivePiece, Game, empty_board
from app.rules import engine, pieces


def make_game(seed: int = 1) -> Game:
    """Build a game via the engine (empty board, first spawn)."""

    return engine.new_game("test", seed)


def blank_game(seed: int = 1) -> Game:
    """Build a game with an empty board and no active piece for crafted tests."""

    rng = random.Random(seed)
    return Game(
        id="test",
        status="playing",
        board=empty_board(),
        active=None,
        rng=rng,
        seed=seed,
        bag=[],
    )


# --- Board dimensions (Req 1) ---

def test_board_has_20_rows():
    game = make_game()
    assert len(game.board) == ROWS == 20


def test_board_rows_have_10_columns():
    game = make_game()
    assert all(len(row) == COLS == 10 for row in game.board)


def test_board_starts_empty():
    game = make_game()
    assert all(cell is None for row in game.board for cell in row)


# --- Spawning (Req 5) ---

def test_spawn_origin_at_top_row():
    game = make_game()
    assert game.active is not None
    assert game.active.origin[0] == 0


def test_spawn_origin_column_is_center():
    game = make_game()
    assert game.active.origin[1] == pieces.SPAWN_COLUMN == 3


def test_spawn_cells_within_bounds():
    game = make_game()
    for row, col in game.active.cells:
        assert 0 <= row < ROWS
        assert 0 <= col < COLS


# --- Piece set and determinism (Req 3, 4) ---

def test_spawned_type_is_standard():
    game = make_game()
    assert game.active.type in pieces.ALL_TYPES


def test_bag_covers_all_seven_types():
    game = blank_game()
    seen = set()
    for _ in range(7):
        seen.add(pieces.next_type(game.rng, game.bag))
    assert seen == set(pieces.ALL_TYPES)


def test_same_seed_produces_same_sequence():
    a = blank_game(seed=42)
    b = blank_game(seed=42)
    seq_a = [pieces.next_type(a.rng, a.bag) for _ in range(20)]
    seq_b = [pieces.next_type(b.rng, b.bag) for _ in range(20)]
    assert seq_a == seq_b


# --- Horizontal movement and walls (Req 9, 10, 12) ---

def test_move_left_decreases_column():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.move(game, "left")
    assert game.active.origin[1] == 3
    assert (0, 3) in game.active.cells


def test_move_right_increases_column():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.move(game, "right")
    assert game.active.origin[1] == 5
    assert (0, 6) in game.active.cells


def test_left_wall_blocks_move():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 0), cells=[(0, 0), (0, 1), (1, 0), (1, 1)])
    engine.move(game, "left")
    assert game.active.origin[1] == 0  # unchanged


def test_right_wall_blocks_move():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 8), cells=[(0, 8), (0, 9), (1, 8), (1, 9)])
    engine.move(game, "right")
    assert game.active.origin[1] == 8  # unchanged


# --- Stack collision on horizontal move (Req 13) ---

def test_stack_blocks_horizontal_move():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    game.board[0][3] = "I"  # settled block to the left
    engine.move(game, "left")
    assert game.active.origin[1] == 4  # unchanged


# --- Gravity and bottom collision (Req 8, 14) ---

def test_tick_moves_piece_down():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.tick(game)
    assert game.active.origin[0] == 1
    assert (1, 4) in game.active.cells


def test_bottom_row_blocks_downward_and_locks():
    game = blank_game()
    # O piece resting on the floor (rows 18 and 19).
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.tick(game)
    # Piece locked into the board.
    assert game.board[19][4] == "O"
    assert game.board[18][5] == "O"


# --- Stack collision below (Req 15) ---

def test_stack_below_causes_lock():
    game = blank_game()
    game.board[19][4] = "I"  # settled block directly below
    game.active = ActivePiece(type="O", origin=(17, 4), cells=[(17, 4), (17, 5), (18, 4), (18, 5)])
    engine.tick(game)
    assert game.board[18][4] == "O"  # locked, could not descend into (19,4)


# --- Soft drop (Req 11) ---

def test_soft_drop_moves_down():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.move(game, "down")
    assert game.active.origin[0] == 1


def test_soft_drop_locks_when_blocked():
    game = blank_game()
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.move(game, "down")
    assert game.board[19][4] == "O"


# --- Locking (Req 16) ---

def test_lock_writes_all_cells():
    game = blank_game()
    game.active = ActivePiece(type="T", origin=(18, 3), cells=[(18, 4), (19, 3), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.board[18][4] == "T"
    assert game.board[19][3] == "T"
    assert game.board[19][4] == "T"
    assert game.board[19][5] == "T"


# --- Line clearing (Req 18, 19, 20, 21) ---

def test_single_line_clear():
    game = blank_game()
    # Fill the bottom row except two cells, then lock an O to complete it.
    for col in range(COLS):
        if col not in (4, 5):
            game.board[19][col] = "I"
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    # Bottom row cleared: the two O cells that were at row 18 shift to row 19.
    assert game.board[19][4] == "O"
    assert game.board[19][5] == "O"
    # And the rest of row 19 is empty again.
    assert all(game.board[19][c] is None for c in range(COLS) if c not in (4, 5))


def test_multiple_line_clear():
    game = blank_game()
    for row in (18, 19):
        for col in range(COLS):
            if col not in (4, 5):
                game.board[row][col] = "I"
    # O fills the remaining 2x2 hole across both rows, completing them.
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    # Both rows cleared; board fully empty again.
    assert all(cell is None for r in game.board for cell in r)


def test_no_clear_preserves_rows():
    game = blank_game()
    game.board[19][0] = "I"  # partial row
    game.active = ActivePiece(type="O", origin=(0, 4), cells=[(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.lock(game)
    assert game.board[19][0] == "I"
    assert len(game.board) == ROWS


def test_clear_preserves_relative_order():
    game = blank_game()
    # Row 17 partial marker, row 19 full.
    game.board[17][0] = "T"
    for col in range(COLS):
        if col not in (4, 5):
            game.board[19][col] = "I"
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    # The lone T marker should have shifted down by one (17 -> 18).
    assert game.board[18][0] == "T"


# --- Game over (Req 22, 23) ---

def test_game_over_on_spawn_collision():
    game = blank_game()
    # Occupy the spawn region without completing any row, so the next piece
    # cannot be placed but no line clears. Leave column 0 empty in rows 0-1.
    for col in range(1, COLS):
        game.board[0][col] = "I"
        game.board[1][col] = "I"
    game.active = ActivePiece(type="O", origin=(18, 4), cells=[(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)  # locks, clears nothing, then spawns into filled top
    assert game.status == "game_over"
    assert game.active is None


def test_no_gameplay_after_game_over():
    game = blank_game()
    game.status = "game_over"
    game.active = None
    snapshot = [row[:] for row in game.board]
    engine.tick(game)
    engine.move(game, "left")
    assert game.status == "game_over"
    assert game.board == snapshot


# --- Deterministic sequence via new_game (Req 4) ---

def test_new_game_sequence_deterministic():
    g1 = engine.new_game("a", 7)
    g2 = engine.new_game("b", 7)
    types1 = [g1.active.type]
    types2 = [g2.active.type]
    for _ in range(10):
        engine.lock(g1)
        engine.lock(g2)
        if g1.active:
            types1.append(g1.active.type)
        if g2.active:
            types2.append(g2.active.type)
    assert types1 == types2
