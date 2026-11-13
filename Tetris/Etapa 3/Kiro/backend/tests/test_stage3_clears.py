"""Synthetic 3-row and 4-row line-clear fixtures over the REAL engine path.

The engine exposes no standalone line-clear API that takes a synthetic shape;
its real pure API is ``new_game``, ``spawn``, ``clear_lines``, ``lock``,
``tick``, ``move``, ``hold`` operating on a ``Game``. ``lock(game)`` settles the
active piece and then calls ``clear_lines(game)`` on ``game.board``.

These fixtures prefill complete rows DIRECTLY on ``game.board`` and position a
controlled canonical UNROTATED piece, then drive the unchanged production path
by calling ``engine.lock`` on the real ``Game``. Three- and four-line clears are
UNREACHABLE through ordinary unrotated gameplay, which is precisely why these
are synthetic fixtures over the real path. No piece is rotated and no gameplay
piece is invented.
"""

from __future__ import annotations

from app.domain.models import ActivePiece, COLS, Game, empty_board
from app.rules import engine, scoring


def _make_game(game_id="g-clear", seed=0):
    g = engine.new_game(game_id, seed)
    # Reset to a clean board and known counters for a controlled fixture.
    g.board = empty_board()
    g.score = 0
    g.total_lines = 0
    g.level = 1
    g.gravity_interval_ms = scoring.gravity_ms_for(1)
    return g


def _fill_rows_except_column(g, rows, empty_col):
    """Fill the given rows completely except one column, so a drop completes them."""

    for r in rows:
        for c in range(COLS):
            if c != empty_col:
                g.board[r][c] = "I"


def _place_vertical_filler(g, rows, col):
    """Place a canonical UNROTATED I-piece-derived single-column filler.

    We settle a controlled active piece occupying ``col`` across ``rows`` so the
    real ``lock`` completes those rows via ``clear_lines``. The piece type and
    cells are explicit and unrotated.
    """

    cells = [(r, col) for r in rows]
    g.active = ActivePiece(type="I", origin=(rows[0], col), cells=cells)


def test_triple_clear_uses_real_scoring_path():
    g = _make_game()
    bottom = [17, 18, 19]
    _fill_rows_except_column(g, bottom, empty_col=0)
    _place_vertical_filler(g, bottom, col=0)

    pre_level = g.level
    engine.lock(g)

    # Three rows cleared via the real clear_lines + scoring path.
    assert g.total_lines == 3
    assert g.score == scoring.line_award(3, pre_level)
    assert g.level == scoring.level_for(3)
    assert g.gravity_interval_ms == scoring.gravity_ms_for(g.level)


def test_tetris_clear_uses_real_scoring_path():
    g = _make_game()
    bottom = [16, 17, 18, 19]
    _fill_rows_except_column(g, bottom, empty_col=0)
    _place_vertical_filler(g, bottom, col=0)

    pre_level = g.level
    engine.lock(g)

    assert g.total_lines == 4
    assert g.score == scoring.line_award(4, pre_level)
    assert g.level == scoring.level_for(4)
    assert g.gravity_interval_ms == scoring.gravity_ms_for(g.level)
