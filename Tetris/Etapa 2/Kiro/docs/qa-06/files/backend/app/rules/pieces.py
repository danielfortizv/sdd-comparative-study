"""Tetromino definitions and the deterministic (seeded) piece generator.

Shapes are given in their initial orientation only, as (row, column) offsets
relative to the piece bounding-box top-left origin. Rotation is out of scope
for Stage 1.
"""

from __future__ import annotations

import random
from typing import Dict, List

from ..domain.models import Coord, PieceType

# Relative cell offsets for each piece in its initial orientation.
SHAPES: Dict[PieceType, List[Coord]] = {
    "I": [(0, 0), (0, 1), (0, 2), (0, 3)],
    "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "T": [(0, 1), (1, 0), (1, 1), (1, 2)],
    "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (1, 2)],
    "J": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "L": [(0, 2), (1, 0), (1, 1), (1, 2)],
}

# All seven piece types in a stable order (used to refill the 7-bag).
ALL_TYPES: List[PieceType] = ["I", "O", "T", "S", "Z", "J", "L"]

# Spawn origin: top row, horizontally near center for the 4-wide bounding box.
SPAWN_ROW = 0
SPAWN_COLUMN = 3


def refill_bag(rng: random.Random) -> List[PieceType]:
    """Return a freshly shuffled 7-bag using the provided seeded RNG."""

    bag = list(ALL_TYPES)
    rng.shuffle(bag)
    return bag


def next_type(rng: random.Random, bag: List[PieceType]) -> PieceType:
    """Pop the next piece type, refilling and shuffling the bag when empty.

    The 7-bag scheme guarantees every type appears within each cycle while
    remaining fully deterministic for a given seed.
    """

    if not bag:
        bag.extend(refill_bag(rng))
    return bag.pop(0)
