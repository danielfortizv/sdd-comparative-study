"""Pure game rules for Tetris Stage 1 (Option A).

All functions operate on domain models only and have no dependency on the HTTP
layer, so they can be exercised directly in unit tests. The engine owns the
authoritative behavior: spawning, movement, collision, locking, line clearing,
and game-over detection.
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
from . import pieces

Direction = Literal["left", "right", "down"]


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


def spawn(game: Game) -> None:
    """Spawn the next piece.

    If the spawned piece overlaps a settled block or leaves the board bounds,
    the game transitions to ``game_over`` and no active piece is set.
    """

    piece_type = pieces.next_type(game.rng, game.bag)
    origin: Coord = (pieces.SPAWN_ROW, pieces.SPAWN_COLUMN)
    cells = _absolute_cells(piece_type, origin)

    if not _is_valid(game.board, cells):
        game.status = "game_over"
        game.active = None
        return

    game.active = ActivePiece(type=piece_type, origin=origin, cells=cells)


def new_game(game_id: str, seed: int) -> Game:
    """Create a fresh game with an empty board and the first spawned piece."""

    rng = random.Random(seed)
    game = Game(
        id=game_id,
        status="playing",
        board=empty_board(),
        active=None,
        rng=rng,
        seed=seed,
        bag=[],
    )
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
    """Settle the active piece, clear completed lines, then spawn the next.

    Line clearing always occurs before the next spawn.
    """

    if game.active is None:
        return

    for row, col in game.active.cells:
        game.board[row][col] = game.active.type

    clear_lines(game)
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
