"""Pure rotation engine: orientation tables and helpers (Stage 4, M1).

This module is deliberately pure: it imports only ``typing`` and the domain /
pieces modules (no FastAPI, no ``sqlite3``, no new third-party dependency), so
the rotation data and helpers stay independently testable.

Orientation is represented as an explicit orientation index ``0..3`` plus
declared per-piece per-orientation occupied-cell data tables, each anchored to
the inherited ``spawn0`` geometry so orientation ``0`` equals
``pieces.SHAPES[type]``. The tables are declared data (NOT derived at runtime
from the rotation algorithm under test), which lets a test assert the engine's
cells for ``(type, orientation)`` against the same declared table without
re-deriving them through the algorithm it verifies (Req 2.8, 9.1).
"""

from __future__ import annotations

from typing import Dict, List, Literal

from ..domain.models import Coord, PieceType

# Rotation direction (exactly the two documented, case-sensitive values).
RotationDirection = Literal["cw", "ccw"]

# Candidate COLUMN offsets, in the exact evaluation order (Req 3.2, 3.4).
# Horizontal only: no row offset is ever applied (Req 3.3).
KICK_OFFSETS: List[int] = [0, -1, 1, -2, 2]

# ORIENTATIONS[type][orientation_index] -> list of 4 (row, col) offsets from the
# piece origin. orientation 0 == pieces.SHAPES[type]. Declared data, NOT derived
# at runtime from the algorithm under test (Req 2.8, 9.1).
#
# Every piece's four orientations are rigid 90-degree quarter-turns about ONE
# declared fixed pivot POINT (fractional allowed). The CW transform about pivot
# (pr, pc) is (r, c) -> (pr + (c - pc), pc - (r - pr)) and CCW is its exact
# inverse. The declared pivot for each piece is recorded in its comment.
ORIENTATIONS: Dict[PieceType, List[List[Coord]]] = {
    # I: single FIXED fractional pivot at (1.5, 1.5) (the center of the 4x4 I box).
    # spawn0 (orientation 0) is HORIZONTAL on row 0 and is AUTHORITATIVE/unchanged.
    # Each orientation is a rigid 90-degree CW quarter-turn of the previous about
    # (1.5, 1.5): CW: (r,c) -> (1.5 + (c-1.5), 1.5 - (r-1.5)); CCW is its inverse.
    # Never an SRS table that assumes the I spawns on row 1.
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # 0: spawn0 (row 0, cols 0..3) -- authoritative
        [(0, 3), (1, 3), (2, 3), (3, 3)],   # 1: cw  -> vertical in column 3
        [(3, 0), (3, 1), (3, 2), (3, 3)],   # 2: 180 -> horizontal on row 3
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # 3: ccw -> vertical in column 0
    ],
    # O: single declared fixed pivot (0.5, 0.5); FULL no-op -- all four indices
    # share the spawn0 set AND O rotation does not change the orientation index
    # either (see engine.rotate).
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    # T: pivot at (1, 1); spawn0 points up.
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],   # 0: spawn0
        [(0, 1), (1, 1), (1, 2), (2, 1)],   # 1: cw
        [(1, 0), (1, 1), (1, 2), (2, 1)],   # 2: 180
        [(0, 1), (1, 0), (1, 1), (2, 1)],   # 3: ccw
    ],
    # S: pivot at (1, 1).
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],   # 0: spawn0
        [(0, 1), (1, 1), (1, 2), (2, 2)],   # 1: cw
        [(1, 1), (1, 2), (2, 0), (2, 1)],   # 2: 180
        [(0, 0), (1, 0), (1, 1), (2, 1)],   # 3: ccw
    ],
    # Z: pivot at (1, 1).
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],   # 0: spawn0
        [(0, 2), (1, 1), (1, 2), (2, 1)],   # 1: cw
        [(1, 0), (1, 1), (2, 1), (2, 2)],   # 2: 180
        [(0, 1), (1, 0), (1, 1), (2, 0)],   # 3: ccw
    ],
    # J: pivot at (1, 1); spawn0 corner top-left.
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],   # 0: spawn0
        [(0, 1), (0, 2), (1, 1), (2, 1)],   # 1: cw
        [(1, 0), (1, 1), (1, 2), (2, 2)],   # 2: 180
        [(0, 1), (1, 1), (2, 0), (2, 1)],   # 3: ccw
    ],
    # L: pivot at (1, 1); spawn0 corner top-right.
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],   # 0: spawn0
        [(0, 1), (1, 1), (2, 1), (2, 2)],   # 1: cw
        [(1, 0), (1, 1), (1, 2), (2, 0)],   # 2: 180
        [(0, 0), (0, 1), (1, 1), (2, 1)],   # 3: ccw
    ],
}


def cells_for(piece_type: PieceType, orientation: int, origin: Coord) -> List[Coord]:
    """Absolute cells for a piece at (orientation, origin). Exactly 4, distinct (Req 2.6)."""
    row0, col0 = origin
    return [(row0 + dr, col0 + dc) for dr, dc in ORIENTATIONS[piece_type][orientation % 4]]


def next_orientation(orientation: int, direction: RotationDirection) -> int:
    """cw -> (o + 1) mod 4 ; ccw -> (o - 1) mod 4 (Req 1.1, 1.2)."""
    return (orientation + (1 if direction == "cw" else -1)) % 4
