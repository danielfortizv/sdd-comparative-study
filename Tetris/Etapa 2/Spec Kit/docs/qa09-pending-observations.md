# Correction 09 — read-only observations while generation is active

Snapshot: 2026-10-20 08:19:33 America/Bogota. This note is not a final correction audit. No application/test/specification files were edited and no suites, servers, scanners, or Gemini processes were started by the reviewer.

## First backend test rewrite

Compared `backend/tests/unit/test_game_engine_us1.py` with `docs/generation-08/files/backend/tests/unit/test_game_engine_us1.py` and the original Stage 1 Spec Kit test file. A read-only Python AST comparison found all six inherited Stage 1 test functions unchanged, including all 29 assertions:

| Inherited function | Current line | Assertions retained |
| --- | --- | --- |
| `test_has_collision_boundaries` | 12 | 5 |
| `test_has_collision_settled_blocks` | 25 | 2 |
| `test_create_session` | 34 | 7 |
| `test_move_left_right` | 46 | 4 |
| `test_manual_down_does_not_lock` | 76 | 3 |
| `test_tick_falling_and_lock` | 93 | 8 |

The four removed session-08 test functions are `test_scoring_rules_isolated`, `test_level_boundary_calculation`, `test_pre_lock_level_scoring`, and `test_progressive_gravity_calculations`. The new tests exercise actual `tick_session` or `move_session_piece` behavior instead of locally copied formulas:

- `test_scoring_rules_production`, line 128: real lock paths for zero, one, and two rows; mocked row-clear results passed through the real production scoring path for three and four rows. The last two are explicitly isolated domain fixtures, not ordinary gameplay evidence.
- `test_level_transitions_and_gravity_floor_production`, line 229: real one-/two-row clears crossing 9 to 10/11 lines, pre-lock multiplier assertions, and production recalculation reaching/staying at the 100-ms floor.
- `test_no_points_on_soft_drop_production`, line 308: production soft drop preserves a nonzero score.

`test_next_piece_queue_generation` remains at line 322. Queue draw-count work belongs to the still-active correction; no conclusion is made about its final state here.

## Direct line-clearing regression coverage

The suspected direct-clearing coverage loss is not present in this snapshot. Neither Stage 1 nor session 08 imported `clear_lines_in_board` in the US1 file. Direct-clearing tests belong to `backend/tests/unit/test_game_engine_us2.py` and are still present:

- `test_clear_lines_single_row`, lines 4-19: four assertions for cleared count, shifted survivor cell, empty adjacent cell, and new empty top row.
- `test_clear_lines_multiple_rows`, lines 21-35: four assertions for cleared count, shifted survivor cell, and two new empty top rows.

These same tests and assertion counts exist in both original Stage 1 and the retained session-08 snapshot. No duplicate direct-clearing test is needed to address this concern. Recheck the final correction tree before closing QA-01/QA-05 or assigning acceptance statuses.
