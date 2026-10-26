# Implementation Plan

> All tasks are unchecked. This is a specification-only phase; no application, test, or dependency files are modified in this invocation. Execute these tasks only in a later implementation phase. After any later defect, revise this native spec first, then regenerate or adjust code through the tool rather than directly patching generated application code.

- [ ] 1. Extend backend domain model with Stage 2 fields
  - Add `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_type`, `hold_type`, and `can_hold` to the `Game` dataclass in `app/domain/models.py`
  - Keep `ActivePiece`, `Board`, `PieceType`, `Status`, `empty_board`, `ROWS`, `COLS` unchanged
  - Do not change canonical shapes or the generator
  - _Requirements: 1, 6, 11_

- [ ] 2. Add pure scoring/level/gravity formulas
  - Create `app/rules/scoring.py` with `line_award(cleared, pre_lock_level)`, `level_for(total_lines)`, and `gravity_ms_for(level)`
  - Encode the exact tables: 0/1/2/3/4 → 0/100/300/500/800; `level = 1 + total_lines // 10`; `gravity = max(100, 500 - 50*(level-1))`
  - _Requirements: 2, 3, 4_

- [ ] 3. Add preview-queue helpers to the engine
  - Add `_draw_preview` (exactly one `pieces.next_type` draw) and `_consume_preview` (return current preview, refill with one draw) to `app/rules/engine.py`
  - Do not modify `app/rules/pieces.py`
  - _Requirements: 6, 7_

- [ ] 4. Update `new_game` and `spawn` to use the preview queue
  - Initialize all Stage 2 counters and hold state in `new_game`; draw the first preview before the first spawn
  - Make `spawn` consume the preview (one draw to refill) and place at `(SPAWN_ROW, SPAWN_COLUMN)`; retain spawn-collision → `game_over`
  - Ensure a normal spawn performs exactly one generator draw
  - _Requirements: 1, 7, 11_

- [ ] 5. Add scoring, leveling, gravity, and hold re-enable to `lock`
  - In `lock`: settle → `clear_lines` → compute award with the pre-lock level → update `total_lines`, `level`, `gravity_interval_ms` → set `can_hold = True` → `spawn`
  - Preserve the settle → clear → spawn ordering; ensure soft drop grants no points (score only changes inside `lock`)
  - Handle the level 9→10 boundary (pre-lock level scores; gravity becomes 100 after)
  - _Requirements: 2, 3, 4, 8, 9, 12_

- [ ] 6. Implement `engine.hold`
  - No-op when not playing, no active piece, or `can_hold` is false (zero draws)
  - Empty slot: move active type to hold, consume preview (one draw), place incoming at spawn origin, set `can_hold=false`
  - Occupied slot: swap active/hold (zero draws), place incoming at spawn origin, set `can_hold=false`
  - Incoming piece spawn-collision → `game_over`, clear active
  - _Requirements: 7, 8, 10_

- [ ] 7. Extend API schema serialization
  - Add `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_piece`, `hold_piece`, `can_hold` to `GameStateOut` in `app/api/schemas.py`
  - Keep board as integer codes and the active piece under `active_piece`
  - Map `next_type → next_piece`, `hold_type → hold_piece`
  - _Requirements: 6, 12_

- [ ] 8. Add the Hold endpoint controller
  - Add `POST /api/games/{id}/hold` in `app/api/games.py` calling `engine.hold` and returning the serialized state; reuse `_get_or_404`
  - Keep `POST /api/games` at HTTP 200 and the other routes unchanged
  - _Requirements: 8, 12_

- [ ] 9. Backend tests: scoring/level/gravity units
  - Test `line_award` for 0–4 rows across levels; `level_for` boundaries (9→1, 10→2); `gravity_ms_for` at 1/9/10+ with the 100 ms floor
  - _Requirements: 2, 3, 4, 18_

- [ ] 10. Backend tests: isolated-domain multi-row clears
  - Explicitly labeled fixtures with prefilled complete rows driving the real `engine.lock`/`clear_lines` path for 1/2/3/4-row awards and resulting counters/level/gravity
  - Verify 0/1/2-row cases and the pre-lock level 9→10 crossing; do not mutate canonical shapes or present rotated UI play
  - _Requirements: 2, 3, 4, 5, 18_

- [ ] 11. Backend tests: preview draw counts and state-read purity
  - Assert exactly one draw on normal spawn and first Hold; zero on occupied swap, rejected Hold, reads, and post-game-over actions
  - Assert repeated `GET` leaves all fields and generator state unchanged
  - _Requirements: 6, 7, 10, 18_

- [ ] 12. Backend tests: Hold mechanics and API contract
  - Empty-slot hold, occupied swap, rejection when `can_hold` false, re-enable after lock, incoming spawn-collision → game over, 404 unknown id, no-op after game over, response shape
  - New test asserting the expanded top-level key set and HTTP 200 on create; keep the legacy `test_state_payload_shape` active-piece sub-shape assertion unchanged
  - Confirm all 39 legacy backend test functions still pass
  - _Requirements: 8, 12, 18_

- [ ] 13. Backend coverage artifact
  - Produce `docs/coverage.xml` via `pytest --cov=app --cov-report=xml:../docs/coverage.xml`; record exact command and exit status
  - _Requirements: 18_

- [ ] 14. Frontend types and API client
  - Add the 7 new fields to `GameState` in `src/types.ts`; add `holdGame(id)` to `src/api.ts`
  - _Requirements: 6, 13, 14_

- [ ] 15. Rewrite `useGame` for generation-scoped FIFO ordering and coalesced dynamic ticks
  - Add a generation token bumped on create/restart/dispose; validate generation after `fetch` and after `response.json()`, including create/restart and error/finally paths
  - Serialize manual mutating requests FIFO per generation; isolate queues across generations; allow a new game's Hold while an old Hold is pending
  - Schedule automatic ticks per generation with `setTimeout(gravity_interval_ms)`, coalesced to at most one queued/in-flight tick; reschedule on interval change; cancel the exact pending timeout on manual input, restart, interval change, game over, and unmount
  - Ensure stale completions never clear the current guard/timer; keep StrictMode setup/cleanup/re-setup correct
  - Expose `move`, `hold`, `restart`
  - _Requirements: 15, 16_

- [ ] 16. Frontend rendering of Stage 2 state
  - Add a `Preview` mini-grid component; render `score`/`total_lines`/`level`, `next_piece`, and `hold_piece` (empty state when null) in a sidebar/panel
  - No local rule logic; values come only from backend state
  - _Requirements: 13_

- [ ] 17. Frontend Hold controls and preserved controls
  - Add a Hold button (disabled when `!can_hold` or not playing) and a `C`/`c` key handler that dispatch a hold request
  - Keep Left/Right/Soft Drop/Restart controls, English labels, and the game-over message
  - _Requirements: 13, 14, 17_

- [ ] 18. Add a compatible frontend test framework (implementation phase only)
  - Add Vitest + Testing Library with coverage emitting LCOV at `frontend/coverage/lcov.info`; wire an `npm run test` script
  - Specify this in design before installing; do not add during the specification-only phase
  - _Requirements: 18_

- [ ] 19. Frontend tests: scheduling, ordering, and lifecycle
  - Dynamic interval from `gravity_interval_ms`, reschedule on change, stop on game over
  - Delayed `fetch` and delayed `response.json()` across restart; FIFO manual actions; stale error/finally discarded; old-vs-new Hold; repeated restart; queue isolation; tick coalescing (no burst); exact timeout cancellation; StrictMode setup/cleanup/re-setup
  - Assert observable requests/state/timer timing, not implementation internals
  - _Requirements: 15, 16, 18_

- [ ] 20. Frontend tests: rendering and controls
  - Score/lines/level shown from state; next preview; hold display and disabled Hold button per `can_hold`; `C`/`c` key and Hold button click dispatch a hold; existing controls still work
  - Ensure production `frontend/src` modules are exercised so LCOV includes all production files
  - _Requirements: 13, 14, 18_

- [ ] 21. Reproducible build and audit evidence
  - Run the TypeScript production build (`npm run build`) and record exact log/exit status
  - Run `npm audit --json`; plan a compatible, non-breaking remediation for the baseline 3 vulnerabilities (1 moderate, 2 high) and record the final audit honestly
  - _Requirements: 17, 18_

- [ ] 22. Quality gate verification and documentation
  - Verify new coverage ≥ 80%, new duplication ≤ 3%, zero new violations without weakening thresholds, suppressing findings without evidence, excluding uncovered production files, or altering legacy regression assertions
  - Update `backend/README.md` and `frontend/README.md` with Stage 2 run/test/build/coverage/audit commands; document any material ambiguity resolution and quality remediations before code changes
  - _Requirements: 12, 18_
