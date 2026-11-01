"""Unit tests for the pure Stage 2 scoring/level/gravity formulas (Req 2,3,4)."""

from __future__ import annotations

import pytest

from app.rules import scoring


# --- line_award: base table times the pre-lock level (Req 2) ---

@pytest.mark.parametrize(
    "cleared, expected_base",
    [(0, 0), (1, 100), (2, 300), (3, 500), (4, 800)],
)
def test_line_award_base_at_level_1(cleared, expected_base):
    assert scoring.line_award(cleared, 1) == expected_base


@pytest.mark.parametrize("level", [1, 2, 3, 5, 9, 10, 25])
def test_line_award_scales_with_pre_lock_level(level):
    assert scoring.line_award(1, level) == 100 * level
    assert scoring.line_award(2, level) == 300 * level
    assert scoring.line_award(3, level) == 500 * level
    assert scoring.line_award(4, level) == 800 * level


@pytest.mark.parametrize("level", [1, 2, 9, 10, 100])
def test_zero_clear_awards_zero_at_any_level(level):
    assert scoring.line_award(0, level) == 0


# --- level_for boundaries (Req 3) ---

@pytest.mark.parametrize("total_lines", range(0, 10))
def test_level_is_one_for_0_through_9(total_lines):
    assert scoring.level_for(total_lines) == 1


@pytest.mark.parametrize("total_lines", range(10, 20))
def test_level_is_two_for_10_through_19(total_lines):
    assert scoring.level_for(total_lines) == 2


@pytest.mark.parametrize(
    "total_lines, expected_level",
    [(9, 1), (10, 2), (89, 9), (90, 10)],
)
def test_level_crossing_boundaries(total_lines, expected_level):
    assert scoring.level_for(total_lines) == expected_level


# --- gravity_ms_for: 50 ms per level, 100 ms floor (Req 4) ---

@pytest.mark.parametrize(
    "level, expected_ms",
    [(1, 500), (2, 450), (9, 100)],
)
def test_gravity_at_level(level, expected_ms):
    assert scoring.gravity_ms_for(level) == expected_ms


@pytest.mark.parametrize("level", [10, 11, 20, 50])
def test_gravity_floor_at_level_10_or_more(level):
    assert scoring.gravity_ms_for(level) == 100
