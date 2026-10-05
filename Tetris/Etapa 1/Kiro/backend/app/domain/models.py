"""Core domain models for the Tetris game.

These are plain data structures with no framework dependencies so that the
game rules can be tested in isolation from the HTTP layer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

# The seven standard tetromino types.
PieceType = Literal["I", "O", "T", "S", "Z", "J", "L"]

# High-level game status.
Status = Literal["playing", "game_over"]

# Board dimensions. Row 0 is the top row; row ROWS - 1 is the bottom row.
# Column 0 is the leftmost column; column COLS - 1 is the rightmost column.
ROWS = 20
COLS = 10

# A board cell is either empty (None) or occupied by a settled block of a type.
Cell = Optional[PieceType]
Board = List[List[Cell]]

# A coordinate is an absolute (row, column) pair on the board.
Coord = Tuple[int, int]


@dataclass
class ActivePiece:
    """The piece currently controlled by gravity and player input."""

    type: PieceType
    # Origin is the (row, column) of the piece bounding box top-left corner.
    origin: Coord
    # Absolute occupied board cells for the current position.
    cells: List[Coord]


@dataclass
class Game:
    """Authoritative in-memory state for a single game."""

    id: str
    status: Status
    board: Board
    active: Optional[ActivePiece]
    # Seeded RNG carrying the deterministic piece sequence state.
    rng: random.Random
    seed: int
    # Remaining shuffled 7-bag used by the piece generator.
    bag: List[PieceType]


def empty_board() -> Board:
    """Return a fresh ROWS x COLS board with every cell empty."""

    return [[None for _ in range(COLS)] for _ in range(ROWS)]
