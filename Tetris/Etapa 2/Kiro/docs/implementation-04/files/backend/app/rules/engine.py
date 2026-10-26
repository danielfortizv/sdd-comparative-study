"""Pure game rules for Tetris Stage 2 (Option A).

All functions operate on domain models only and have no dependency on the HTTP
layer, so they can be exercised directly in unit tests. The engine owns the
authoritative behavior: spawning, movement, collision, locking, line clearing,
game-over detection, and -- new in Stage 2 -- scoring, leveling, progressive
gravity, a one-piece preview queue, and a one-piece Hold.
"""

from __future__ import annotations

import random
from typing import List, Literal

from ..domain.models import (
    COLS,
    ROWS,
    ActivePiece,
    Board,
    Coord,
    Game,
    PieceType,
    empty_board,
)
from . import pieces, scoring

Direction = Literal["left", "right", "down"]

SPAWN_ORIGIN: Coord = (pieces.SPAWN_ROW, pieces.SPAWN_COLUMN)


def _absolute_cells(piece_type: PieceType, origin: Coord) -> List[Coord]:
    """Return the absolute board cells for a piece at the given origin."""

    row0, col0 = origin
    return [(row0 + dr, col0 + dc) for dr, dc in pieces.SHAPES[piece_type]]


def _is_valid(board: Board, cells: List[Coord]) -> bool:
    """Return True if every cell is in bounds and not on a settled block."""

    for row, col in cells:
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            return False
        if board[row][col] is not None:
            return False
    return True


def _draw_preview(game: Game) -> PieceType:
    """Draw exactly one piece type from the seeded 7-bag generator."""

    return pieces.next_type(game.rng, game.bag)


def _consume_preview(game: Game) -> PieceType:
    """Take the current preview as the incoming piece and refill with one draw.

    On the normal path ``game.next_type`` is already populated (by ``new_game``
    or a prior spawn), so this performs exactly one generator draw: the refill.
    If a game is constructed directly without a preview (``next_type is None``),
    the preview is lazily initialized with one draw before the refill; this
    fallback only ever runs for such hand-built games and never affects the
    draw counts of games created through ``new_game``.
    """

    if game.next_type is None:
        game.next_type = _draw_preview(game)
    incoming = game.next_type
    game.next_type = _draw_preview(game)
    return incoming


def _place(game: Game, piece_type: PieceType) -> None:
    """Place ``piece_type`` at the canonical spawn origin or end the game.

    On overlap or out-of-bounds at the spawn origin the game transitions to
    ``game_over`` and the active piece is cleared, consistent with the frozen
    Stage 1 spawn-collision behavior.
    """

    cells = _absolute_cells(piece_type, SPAWN_ORIGIN)
    if not _is_valid(game.board, cells):
        game.status = "game_over"
        game.active = None
        return
    game.active = ActivePiece(type=piece_type, origin=SPAWN_ORIGIN, cells=cells)


def spawn(game: Game) -> None:
    """Spawn the previewed piece and draw exactly one new preview.

    The preview is consumed as the piece that enters play (one generator draw
    to refill the preview). If the spawned piece overlaps a settled block or
    leaves the board bounds, the game transitions to ``game_over``.
    """

    piece_type = _consume_preview(game)
    _place(game, piece_type)


def new_game(game_id: str, seed: int) -> Game:
    """Create a fresh game with all Stage 2 counters and the first spawn."""

    rng = random.Random(seed)
    game = Game(
        id=game_id,
        status="playing",
        board=empty_board(),
        active=None,
        rng=rng,
        seed=seed,
        bag=[],
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_type=None,
        hold_type=None,
        can_hold=True,
    )
    # Draw the first preview, then spawn (which consumes it and draws the next).
    game.next_type = _draw_preview(game)
    spawn(game)
    return game


def clear_lines(game: Game) -> int:
    """Remove fully filled rows, shifting rows down and inserting empty rows.

    Returns the number of rows cleared. Relative vertical order of the
    surviving rows is preserved.
    """

    surviving = [row for row in game.board if any(cell is None for cell in row)]
    cleared = ROWS - len(surviving)
    if cleared == 0:
        return 0

    new_rows: Board = [[None for _ in range(COLS)] for _ in range(cleared)]
    game.board = new_rows + surviving
    return cleared


def lock(game: Game) -> None:
    """Settle the active piece, clear lines, score, level, then spawn.

    Ordering: settle -> clear -> score/level/gravity -> re-enable Hold -> spawn.
    Scoring uses the pre-lock level captured before the level update. Line
    clearing always occurs before the next spawn.
    """

    if game.active is None:
        return

    for row, col in game.active.cells:
        game.board[row][col] = game.active.type

    cleared = clear_lines(game)

    pre_lock_level = game.level
    game.score += scoring.line_award(cleared, pre_lock_level)
    game.total_lines += cleared
    game.level = scoring.level_for(game.total_lines)
    game.gravity_interval_ms = scoring.gravity_ms_for(game.level)

    # Re-enable Hold for the next active piece (once per active piece).
    game.can_hold = True

    spawn(game)


def _can_move_down(game: Game) -> bool:
    """Return True if the active piece can descend by one row."""

    if game.active is None:
        return False
    candidate = [(row + 1, col) for row, col in game.active.cells]
    return _is_valid(game.board, candidate)


def tick(game: Game) -> None:
    """Advance one gravity tick: move the active piece down or lock it."""

    if game.status != "playing" or game.active is None:
        return

    if _can_move_down(game):
        origin = (game.active.origin[0] + 1, game.active.origin[1])
        game.active.origin = origin
        game.active.cells = [(row + 1, col) for row, col in game.active.cells]
    else:
        lock(game)


def move(game: Game, direction: Direction) -> None:
    """Apply a player move.

    ``left`` / ``right`` shift horizontally when legal, otherwise no-op.
    ``down`` performs a soft drop, locking the piece if it cannot descend.
    Soft drop never changes the score (score only changes inside ``lock``).
    """

    if game.status != "playing" or game.active is None:
        return

    if direction == "down":
        tick(game)
        return

    delta = -1 if direction == "left" else 1
    origin = (game.active.origin[0], game.active.origin[1] + delta)
    candidate = [(row, col + delta) for row, col in game.active.cells]

    if _is_valid(game.board, candidate):
        game.active.origin = origin
        game.active.cells = candidate


def hold(game: Game) -> None:
    """Hold or swap the active piece.

    No-op when not playing, there is no active piece, or ``can_hold`` is false
    (zero generator draws). On an empty hold slot the active type is held and
    the previewed piece enters play (one draw to refill the preview). On an
    occupied slot the active and held types are swapped (zero draws). The
    incoming piece is placed at the canonical spawn origin; if it is obstructed
    there the game ends. Using Hold disables it until the next lock.
    """

    if game.status != "playing" or game.active is None:
        return
    if not game.can_hold:
        return

    current = game.active.type
    if game.hold_type is None:
        game.hold_type = current
        incoming = _consume_preview(game)  # one generator draw
    else:
        incoming = game.hold_type
        game.hold_type = current  # swap, no draw

    _place(game, incoming)
    game.can_hold = False
