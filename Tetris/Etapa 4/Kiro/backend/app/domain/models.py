"""Core domain models for the Tetris game.

These are plain data structures with no framework dependencies so that the
game rules can be tested in isolation from the HTTP layer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

from ..persistence.store import HighScoreRecord

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
    # Internal engine orientation index (0..3). Stage 4 rotation state only;
    # NOT serialized into GameStateOut and not part of the public solo schema.
    # Defaults to 0 so the field stays backward-compatible with callers that
    # construct an ActivePiece without specifying an orientation.
    orientation: int = 0


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
    # --- Stage 2 additions ---
    # Cumulative score; only ever changes on a lock via the line-clear award.
    score: int = 0
    # Total rows cleared since the game started.
    total_lines: int = 0
    # Derived level: 1 + floor(total_lines / 10).
    level: int = 1
    # Derived gravity interval in milliseconds: max(100, 500 - 50 * (level - 1)).
    gravity_interval_ms: int = 500
    # The single queued preview piece. Always a valid type while readable,
    # including after game over. Populated during new_game before the first
    # spawn and refilled whenever a spawn consumes it.
    next_type: Optional[PieceType] = None
    # The single held piece type, or None when the hold slot is empty.
    hold_type: Optional[PieceType] = None
    # True when Hold is allowed for the current active piece.
    can_hold: bool = True
    # --- Stage 3 finalization bookkeeping (in memory only) ---
    # A High_Score_Record has already been persisted for this game.
    finalized: bool = False
    # Terminal but not yet persisted; a later mutating request retries the write.
    pending_finalization: bool = False
    # UTC ISO-8601 completion timestamp, written once at the first terminal
    # transition and never changed by any later retry or action.
    completed_at: Optional[str] = None
    # Immutable snapshot captured once at the first terminal transition, BEFORE
    # any storage I/O. Every finalization attempt and retry reuses this same
    # frozen record, so completed_at is never regenerated and the terminal game
    # is never re-mutated by finalization. These fields are never persisted as
    # game state; only the High_Score_Record summary is persisted.
    finalization_record: Optional[HighScoreRecord] = None


def empty_board() -> Board:
    """Return a fresh ROWS x COLS board with every cell empty."""

    return [[None for _ in range(COLS)] for _ in range(ROWS)]
