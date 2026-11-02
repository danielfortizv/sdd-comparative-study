"""Pure scoring, leveling, and gravity formulas for Stage 2 (Option A).

These functions encode the fixed experimental controls for Stage 2 and have no
dependency on the engine or HTTP layer, so they can be unit-tested directly and
reused by ``rules/engine.py``. They do not authorize any out-of-scope feature.
"""

from __future__ import annotations

# Base line-clear award by number of rows cleared simultaneously, before the
# pre-lock level multiplier is applied. A lock clearing no rows awards zero.
LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


def line_award(cleared: int, pre_lock_level: int) -> int:
    """Return the score for clearing ``cleared`` rows at ``pre_lock_level``.

    The award is the base value for the cleared-row count multiplied by the
    level in effect immediately before the lock (the pre-lock level).
    """

    return LINE_SCORES[cleared] * pre_lock_level


def level_for(total_lines: int) -> int:
    """Return the level derived from the cumulative cleared-line count."""

    return 1 + total_lines // 10


def gravity_ms_for(level: int) -> int:
    """Return the gravity interval in milliseconds for the given level.

    The interval decreases by 50 ms per level above 1 and never drops below the
    100 ms floor.
    """

    return max(100, 500 - 50 * (level - 1))
