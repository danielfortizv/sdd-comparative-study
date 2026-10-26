"""Stage 2 engine tests: scoring via the real lock path, preview draw counts,
leveling/gravity thresholds, and state-read purity (Req 2,3,4,5,6,7,10).

The multi-row clears use explicitly labeled ISOLATED DOMAIN fixtures: crafted
boards with prefilled complete rows that drive the real engine.lock /
clear_lines production path. They do NOT mutate canonical shapes, do NOT invent
rotated or custom gameplay pieces, and make no claim about rotated UI play.
"""

from __future__ import annotations

import random

import pytest

from app.domain.models import COLS, ActivePiece, Game, empty_board
from app.rules import engine, pieces


def seeded_game(seed: int = 123) -> Game:
    """A fully engine-initialized game (preview populated, first spawn done)."""

    return engine.new_game("test", seed)


def craft_game(seed: int = 1) -> Game:
    """A hand-built playing game with an empty board and a populated preview.

    The preview is seeded exactly as new_game does (one draw) so that the
    engine's 'exactly one draw per spawn' contract holds for crafted fixtures.
    """

    rng = random.Random(seed)
    game = Game(
        id="test",
        status="playing",
        board=empty_board(),
        active=None,
        rng=rng,
        seed=seed,
        bag=[],
    )
    game.next_type = engine._draw_preview(game)
    return game


def fill_row_except(game: Game, row: int, empties: list[int]) -> None:
    """ISOLATED DOMAIN helper: prefill a board row leaving only ``empties`` open."""

    for col in range(COLS):
        if col not in empties:
            game.board[row][col] = "I"


# --- Isolated-domain single/double clears via the real lock path (Req 2,5) ---

def test_isolated_single_row_clear_awards_100_at_level_1():
    game = craft_game()
    fill_row_except(game, 19, [4, 5])
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.score == 100
    assert game.total_lines == 1
    assert game.level == 1
    assert game.gravity_interval_ms == 500


def test_isolated_double_row_clear_awards_300_at_level_1():
    game = craft_game()
    for row in (18, 19):
        fill_row_except(game, row, [4, 5])
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.score == 300
    assert game.total_lines == 2
    assert game.level == 1


def test_no_clear_awards_zero_and_keeps_counters():
    game = craft_game()
    game.board[19][0] = "I"  # partial row, no clear
    game.active = ActivePiece("O", (0, 4), [(0, 4), (0, 5), (1, 4), (1, 5)])
    engine.lock(game)
    assert game.score == 0
    assert game.total_lines == 0
    assert game.level == 1
    assert game.gravity_interval_ms == 500


# --- Isolated-domain triple/tetris clears via clear_lines/lock scoring path ---
# These rows are not reachable in ordinary unrotated play; the award is applied
# here by driving the real production scoring step with cleared == 3 and 4.

def _lock_with_cleared(seed: int, pre_level: int, pre_total: int, cleared: int) -> Game:
    """Prefill ``cleared`` complete bottom rows, set pre-lock counters, lock.

    The active piece is placed on an already-complete bottom span so that
    engine.lock settles it, clear_lines removes the complete rows, and the real
    scoring step runs with the intended cleared-row count.
    """

    game = craft_game(seed)
    game.level = pre_level
    game.total_lines = pre_total
    # Make the bottom `cleared` rows complete except a 2-wide notch, then fill
    # the notch with the settling O so exactly `cleared` rows complete.
    top = 20 - cleared
    for row in range(top, 20):
        fill_row_except(game, row, [4, 5])
    # Stack O pieces is only 2 tall; for cleared > 2 prefill the notch on the
    # upper complete rows directly and let the O complete the lowest two.
    for row in range(top, 18):
        game.board[row][4] = "I"
        game.board[row][5] = "I"
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    return game


def test_isolated_triple_row_clear_awards_500_at_level_1():
    game = _lock_with_cleared(seed=7, pre_level=1, pre_total=0, cleared=3)
    assert game.score == 500
    assert game.total_lines == 3
    assert game.level == 1


def test_isolated_tetris_row_clear_awards_800_at_level_1():
    game = _lock_with_cleared(seed=9, pre_level=1, pre_total=0, cleared=4)
    assert game.score == 800
    assert game.total_lines == 4
    assert game.level == 1


def test_tetris_award_scales_with_pre_lock_level():
    # Pre-lock level 3, a 4-row clear awards 800 * 3 = 2400.
    game = _lock_with_cleared(seed=11, pre_level=3, pre_total=20, cleared=4)
    assert game.score == 2400
    assert game.total_lines == 24
    assert game.level == 3  # level_for(24) == 3


# --- Primary TOTAL LINES 9 -> 10 threshold, real production path (Req 3.6) ---

def test_threshold_9_to_10_production_path():
    game = craft_game(seed=5)
    game.level = 1
    game.total_lines = 9
    fill_row_except(game, 19, [4, 5])
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.score == 100          # pre-lock level 1
    assert game.total_lines == 10
    assert game.level == 2
    assert game.gravity_interval_ms == 450


# --- Level-9-to-10 crossing at 89 -> 90, real production path (Req 4.6) ---

def test_crossing_89_to_90_production_path():
    game = craft_game(seed=6)
    game.level = 9
    game.total_lines = 89
    fill_row_except(game, 19, [4, 5])
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.score == 900          # pre-lock level 9
    assert game.total_lines == 90
    assert game.level == 10
    assert game.gravity_interval_ms == 100


# --- Soft drop grants no points (Req 9) ---

def test_soft_drop_does_not_change_score():
    game = seeded_game()
    before = game.score
    engine.move(game, "down")
    assert game.score == before == 0


# --- Preview draw counts (Req 7) ---

class DrawCounter:
    """Spy that counts generator draws by wrapping pieces.next_type."""

    def __init__(self):
        self.count = 0
        self._orig = pieces.next_type

    def __enter__(self):
        counter = self

        def wrapped(rng, bag):
            counter.count += 1
            return counter._orig(rng, bag)

        pieces.next_type = wrapped
        engine.pieces.next_type = wrapped
        return self

    def __exit__(self, *exc):
        pieces.next_type = self._orig
        engine.pieces.next_type = self._orig


def test_new_game_draws_two_for_first_preview_and_spawn():
    # new_game draws the first preview (1) then spawn consumes+refills (1).
    with DrawCounter() as c:
        engine.new_game("g", 1)
    assert c.count == 2


def test_normal_spawn_via_lock_draws_exactly_one():
    game = seeded_game()
    with DrawCounter() as c:
        # Lock with no active piece-complete rows -> settle + spawn (one draw).
        engine.lock(game)
    assert c.count == 1


def test_first_hold_empty_slot_draws_exactly_one():
    game = seeded_game()
    with DrawCounter() as c:
        engine.hold(game)
    assert c.count == 1


def test_occupied_swap_hold_draws_zero():
    game = seeded_game()
    engine.hold(game)        # fills the hold slot (and used can_hold)
    game.can_hold = True     # simulate a new active piece became holdable
    with DrawCounter() as c:
        engine.hold(game)    # occupied slot -> swap, no draw
    assert c.count == 0


def test_rejected_hold_draws_zero():
    game = seeded_game()
    game.can_hold = False
    with DrawCounter() as c:
        engine.hold(game)
    assert c.count == 0


def test_state_read_style_access_draws_zero():
    game = seeded_game()
    snapshot_next = game.next_type
    with DrawCounter() as c:
        # Reading fields performs no engine mutation.
        _ = (game.score, game.level, game.next_type, game.hold_type, game.can_hold)
    assert c.count == 0
    assert game.next_type == snapshot_next


def test_post_game_over_actions_draw_zero():
    game = seeded_game()
    game.status = "game_over"
    game.active = None
    with DrawCounter() as c:
        engine.tick(game)
        engine.move(game, "left")
        engine.hold(game)
    assert c.count == 0


def test_next_piece_valid_queued_type_after_game_over():
    # Force a spawn collision to end the game, then assert next_type is valid.
    game = craft_game()
    for col in range(1, COLS):
        game.board[0][col] = "I"
        game.board[1][col] = "I"
    # Active O that will lock without clearing, then spawn into the filled top.
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    engine.lock(game)
    assert game.status == "game_over"
    assert game.next_type in pieces.ALL_TYPES
