# Feature Specification: Extend Tetris to Stage 2 - Score, Level, Hold, Next Preview

**Feature Branch**: `002-extend-tetris-stage2`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Extend the existing Stage 1, option A browser-based Tetris implementation to Stage 2, option A as a brownfield change. Preserve its 10-by-20 board, seven unrotated tetrominoes, left/right/soft-drop controls, collision, locking, line clearing, game over, restart, Python FastAPI backend, React/TypeScript frontend, and in-memory authoritative backend state. Start from this tool's own Stage 1 source and specifications. Create or update this tool's native specification artifacts before changing application code. Use English for all tool interactions, specifications, application text, code comments, and tests. Work only inside this tool's Stage 2 directory."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scoring, Leveling, and Progressive Gravity (Priority: P1)

As a Tetris player, I want my score, total line count, and current level to be tracked and displayed, and the falling speed of the blocks to increase as my level increases, so that the game becomes progressively more challenging and provides a sense of achievement.

**Why this priority**: Scoring, levels, and progressive speed are the core feedback loops that drive engagement and progression in Tetris.

**Independent Test**: Can be tested by starting a game, clearing lines (via simulation/mock or normal play), and verifying that the backend increases the line count, calculates the correct score based on the level prior to clearing, computes the level correctly, and decreases `gravity_interval_ms` down to a minimum of 100 ms.

**Acceptance Scenarios**:

1. **Given** a new game session is created, **When** the session starts, **Then** `score` must be 0, `total_lines` cleared must be 0, `level` must be 1, and `gravity_interval_ms` must be 500 ms.
2. **Given** the current level is 1, **When** a piece locks and clears exactly 1 row, **Then** the player must be awarded 100 points (`score` becomes 100), `total_lines` must become 1, `level` must remain 1, and `gravity_interval_ms` must remain 500 ms.
3. **Given** the current level is 2 and `total_lines` is 10, **When** a piece locks and clears exactly 2 rows, **Then** the player must be awarded 600 points (300 * 2), `total_lines` must become 12, `level` must remain 2, and `gravity_interval_ms` must remain 450 ms.
4. **Given** the current level is 1 and `total_lines` is 9, **When** a piece locks and clears exactly 2 rows, **Then** the player must be awarded 300 points (300 * 1), `total_lines` must become 11, the new `level` must become 2 (since 11 >= 10), and the new `gravity_interval_ms` must become 450 ms.
5. **Given** the current level is 10, **When** the level is active, **Then** `gravity_interval_ms` must be 100 ms (since 500 - 50 * (10 - 1) = 50 ms is less than the 100 ms minimum limit).
6. **Given** a piece locks and clears no rows, **When** the game state is updated, **Then** the `score` must not increase (0 additional points), and `total_lines` count and `level` must remain unchanged.

---

### User Story 2 - Holding and Swapping Tetrominoes (Priority: P2)

As a Tetris player, I want to temporarily store the active falling piece in a "Hold" slot and either retrieve it or swap it with a previously held piece, so that I can save a useful piece for later or rescue myself from an awkward block arrangement.

**Why this priority**: The hold mechanic adds tactical depth, allowing players to plan moves ahead and manage unfavorable piece distributions.

**Independent Test**: Can be tested by pressing the "C" key or the "Hold" button to verify the active piece is stored, a new piece is spawned, and subsequent presses swap the stored piece back in, while enforcing that only one swap is permitted per spawned piece.

**Acceptance Scenarios**:

1. **Given** a new game starts with an empty Hold slot and `can_hold` is true, **When** the player triggers a Hold action, **Then** the current `activePiece` type (one-letter string, e.g., `"I"`) must be stored in `hold_piece`, the queued `next_piece` type must spawn as the `activePiece` at the top-center, a new random next piece type must be generated in `next_piece`, and `can_hold` must become false.
2. **Given** the Hold slot is occupied and `can_hold` is true, **When** the player triggers a Hold action, **Then** the current `activePiece` type must swap positions with the held piece type stored in `hold_piece`, the previously held tetromino type must spawn as the active piece `activePiece` and re-enter at the top-center in its initial unrotated orientation, the previously active piece type must be stored in `hold_piece`, `can_hold` must become false, and the `next_piece` must remain completely unchanged.
3. **Given** `can_hold` is false, **When** the player triggers a Hold action, **Then** the command must be ignored and the game state must remain completely unchanged.
4. **Given** a piece has been held and `can_hold` is false, **When** that piece is shifted down and locks into the board, **Then** a new piece must spawn from the `next_piece`, and `can_hold` must be reset to true.
5. **Given** a Hold action is triggered, **When** the swapped piece is spawned at the top-center but its initial coordinates overlap with settled blocks, **Then** the game status must immediately transition to `"game_over"`.

---

### User Story 3 - Stage 2 UI Display and Sync (Priority: P3)

As a Tetris player, I want to see the score, total lines, level, held piece, and next piece preview on the screen, and I want the controls to respond instantly and reliably without lagging or reversing the state due to slow network responses, so that I have a smooth and synchronized playing experience.

**Why this priority**: Clear visibility of the state and responsive, reliable input synchronization are essential for high-speed Stage 2 gameplay.

**Independent Test**: Verify that the score, lines, level, next preview, and hold slots are correctly rendered on the UI. Simulate network latency or rapid input and verify that old backend responses do not override the newer state on the screen.

**Acceptance Scenarios**:

1. **Given** the game is in `"playing"` status, **When** the UI renders, **Then** the dashboard must show the current `score`, `level`, `total_lines` count, a visual preview of the upcoming `next_piece` (based on its one-letter tetromino type), and a visual display of the currently `hold_piece` (or empty if null).
2. **Given** the level increases from 1 to 2, **When** the frontend receives the updated state, **Then** the automatic tick timer must immediately adjust its interval from 500 ms to 450 ms based on `gravity_interval_ms`.
3. **Given** the game is in `"playing"` status, **When** the player presses the 'C' or 'c' key on their keyboard, or clicks the "Hold" button, **Then** the frontend must immediately dispatch a POST request to `/api/games/{id}/hold`.
4. **Given** multiple move or tick requests are in flight, **When** responses are received out-of-order, **Then** the frontend must discard stale responses and only apply state updates that correspond to the most recent authoritative backend state.

### Edge Cases

- **Immediate Hold Game Over**: If a player swaps the active piece with a held piece that immediately collides with the settled blocks at the top-center spawning coordinates, the backend must transition the game to `"game_over"` status instantly and prevent any subsequent moves.
- **Hold immediately after restart**: When restarting the game, the `hold_piece` is reset to null, and `can_hold` is reset to true. The player must be allowed to hold the very first piece of the new game.
- **Four-line clear isolated validation**: Since rotation is not implemented, a four-line clear (Tetris) may not be achievable in manual play. However, the scoring rule for a 4-line clear (800 points * level) must be fully implemented, active in the backend logic, and verified via automated tests.

## Requirements *(mandatory)*

### Functional Requirements

#### Scoring, Leveling, and Gravity Requirements
- **FR-001**: The backend MUST initialize the game `score` to 0, `total_lines` to 0, and `level` to 1.
- **FR-002**: When a piece locks and clears horizontal lines, points MUST be awarded according to the number of rows cleared simultaneously:
  - 1 row: `100 * level`
  - 2 rows: `300 * level`
  - 3 rows: `500 * level`
  - 4 rows: `800 * level`
  where `level` is the level active *immediately before* the lock.
- **FR-003**: If a piece locks and clears 0 rows, the score MUST NOT increase.
- **FR-004**: Manual soft drop (`"down"` movement) MUST NOT grant any additional points.
- **FR-005**: Immediately after scoring, the cleared line count MUST be added to `total_lines`.
- **FR-006**: The game level MUST be recalculated after adding cleared lines as `1 + floor(total_lines / 10)`.
- **FR-007**: The progressive gravity interval `gravity_interval_ms` MUST be dynamically calculated after level updates as `max(100, 500 - 50 * (level - 1))`.

#### Next Piece Queue Requirements
- **FR-008**: The backend MUST maintain a queued `next_piece` represented as a one-letter tetromino type string (`I`, `O`, `T`, `S`, `Z`, `J`, `L`) that will spawn next.
- **FR-009**: Upon game initialization or restart, the backend MUST randomly generate both the initial `activePiece` and the initial `next_piece` (each selected from the standard 7 shapes using fresh random generation as specified by Stage 1).
- **FR-010**: Retrieving the game state via GET `/api/games/{id}` MUST return the state without modifying or consuming the queued `next_piece`.
- **FR-011**: When an active piece locks normally (and no Hold action is active), the current `next_piece` type MUST be used to spawn the new `activePiece` at the top-center spawn origin, and a new random tetromino type MUST be generated as the `next_piece`.

#### Hold Mechanic Requirements
- **FR-012**: The backend MUST maintain a single-piece Hold slot `hold_piece` represented as a one-letter tetromino type string (`I`, `O`, `T`, `S`, `Z`, `J`, `L`) or null, which is initially empty (null).
- **FR-013**: The backend MUST track a boolean flag `can_hold` indicating whether a Hold action is currently allowed. `can_hold` MUST start as true.
- **FR-014**: The backend MUST expose a `POST /api/games/{id}/hold` endpoint that executes a Hold command and returns the updated game state.
- **FR-015**: When a Hold action is requested and `can_hold` is true, and `hold_piece` is empty (null):
  - The current `activePiece` tetromino type MUST be stored in `hold_piece`.
  - The current `next_piece` tetromino type MUST be used to spawn the new `activePiece` at the top-center spawn origin.
  - A new random tetromino type MUST be generated as the `next_piece`.
  - `can_hold` MUST be set to false.
- **FR-016**: When a Hold action is requested and `can_hold` is true, and `hold_piece` is occupied (not null):
  - The current `activePiece` tetromino type MUST swap with `hold_piece` (the active piece's type is stored in `hold_piece`, and the previously held tetromino type is used to spawn the new `activePiece` at the top-center spawn origin).
  - The `next_piece` MUST NOT be modified or consumed.
  - `can_hold` MUST be set to false.
- **FR-017**: When `can_hold` is false, any request to `POST /api/games/{id}/hold` MUST be ignored and return the current state unmodified.
- **FR-018**: The `can_hold` flag MUST be reset to true ONLY when an active piece locks.
- **FR-019**: If a piece spawning from a Hold action overlaps with settled blocks at the top-center spawn origin, the game status MUST immediately transition to `"game_over"` and `activePiece` MUST be set to null.

#### Game Over, State, and Compatibility Requirements
- **FR-020**: When the game status is `"game_over"`, all requests to tick, move, or hold MUST return the current state unmodified.
- **FR-021**: Re-initializing or restarting a game session via `POST /api/games` MUST reset all variables: `score = 0`, `total_lines = 0`, `level = 1`, `gravity_interval_ms = 500`, `hold_piece = null`, and `can_hold = true`, and generate fresh random `activePiece` and `next_piece`.
- **FR-022**: All backend endpoints MUST return the extended Stage 2 state JSON shape:
  ```json
  {
    "id": "uuid-string",
    "board": [
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      "...(20 rows total)..."
    ],
    "activePiece": {
      "type": "I",
      "cells": [[0,3], [0,4], [0,5], [0,6]],
      "origin": [0,4]
    },
    "status": "playing",
    "score": 0,
    "total_lines": 0,
    "level": 1,
    "gravity_interval_ms": 500,
    "next_piece": "T",
    "hold_piece": null,
    "can_hold": true
  }
  ```

#### Frontend Interface Requirements
- **FR-023**: The frontend MUST display the new Stage 2 statistics panel including `score`, `total_lines`, and `level`, updating them immediately upon receiving backend state.
- **FR-024**: The frontend MUST display a "Next Piece" preview panel rendering the shape corresponding to `next_piece` from the state.
- **FR-025**: The frontend MUST display a "Hold Piece" panel rendering the shape corresponding to `hold_piece` (or a blank placeholder if empty/null).
- **FR-026**: The frontend MUST provide a clickable "Hold" button.
- **FR-027**: The frontend MUST listen to keyboard events and map the `C` or `c` key to trigger a `POST /api/games/{id}/hold` request.
- **FR-028**: The frontend MUST dynamically schedule its automatic tick interval based on the `gravity_interval_ms` field from the latest backend state response.
- **FR-029**: The frontend MUST prevent overlapping tick/move/hold requests and filter out stale responses (e.g. by discarding responses from older sequence numbers or maintaining a locking state while requests are in flight) to ensure the board state never jumps backward or flickers.

### Key Entities

- **Game**: Represents the authoritative state of a single Tetris game session.
  - *Attributes*:
    - `id`: A unique string identifier.
    - `board`: A 20x10 grid of cell states (empty 0, or filled 1-7).
    - `activePiece`: The current falling tetromino object (legacy Stage 1 camelCase key, nullable).
    - `status`: A string indicator (`"playing"` or `"game_over"`).
    - `score`: Numeric score of the session.
    - `total_lines`: Cumulative cleared-line count.
    - `level`: Current level of the game.
    - `gravity_interval_ms`: Current interval for gravity ticks in milliseconds.
    - `next_piece`: One-letter tetromino type queued to spawn next (string).
    - `hold_piece`: One-letter tetromino type stored in Hold slot (string or null).
    - `can_hold`: Boolean indicating if a Hold action is currently allowed.

- **Tetromino**: Represents the shape, coordinates, and behavior of a piece (as used in `activePiece`).
  - *Attributes*:
    - `type`: One of the seven standard shapes (I, O, T, S, Z, J, L).
    - `cells`: An array of four cell coordinates `[row, col]` currently occupied by the piece.
    - `origin`: The rotation/positional pivot coordinate `[row, col]` of the piece on the grid.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gravity ticks MUST schedule and execute at an interval controlled by `gravity_interval_ms` (ranging from 500 ms at level 1 to 100 ms at level 9+). The frontend MUST dynamically reschedule its automatic tick timer immediately upon receiving any change in `gravity_interval_ms`.
- **SC-002**: The backend MUST expose a `POST /api/games/{id}/hold` endpoint that executes piece swaps in-memory, updating `hold_piece`, `activePiece`, and `can_hold` state appropriately, and returning the updated game state in under typical backend execution cycles.
- **SC-003**: Cumulative lines, score, and level calculations MUST be updated in the backend state following a row lock, with 100% mathematical accuracy according to the formula (`1 row: 100 * level`, `2 rows: 300 * level`, `3 rows: 500 * level`, `4 rows: 800 * level`, where level is calculated as `1 + floor(total_lines / 10)`).
- **SC-004**: Hold operations MUST swap the active piece's type with the held piece type. When `hold_piece` is empty, the first hold MUST store the active piece type in `hold_piece`, spawn the next piece as `activePiece`, generate a new random next piece type as `next_piece`, and set `can_hold` to false.
- **SC-005**: Spawning a piece from Hold (or spawning a new piece on lock-spawn) that overlaps with settled blocks on the board MUST immediately transition `status` to `"game_over"` and set `activePiece` to null.

## Assumptions

- **No Piece Rotation**: Piece rotation is explicitly out of scope for this stage. This is a study control.
- **No Soft Drop Points**: Manual soft drop does not grant any extra points. This is a study control.
- **Isolated Domain Test for Four-Row Clear**: Since piece rotation is not implemented, a four-row clear may be physically impossible to achieve during normal manual play. However, the scoring logic for 4 cleared rows (800 * level) must be fully implemented and verified using a mock/isolated unit test.
- **In-Memory Store**: All game sessions, counters, and queues are maintained strictly in-memory and do not persist across backend server restarts.
- **Target OS**: The application is developed and tested on Windows (`win32`) environments.
- **Single-Player Focus**: Multi-player features, persistent high scores, authentication, and accounts are out of scope.

## QA Acceptance Requirements (Post-Generation QA Iteration 1)

The following strict QA acceptance requirements are added to ensure correct implementation, robust test coverage, and complete production-path verification:

### Backend Verification Requirements
1. **Scoring & Gravity Production Path Verification (QA-01)**:
   - Do NOT duplicate formula logic (e.g. `get_points`, `calc_level`, `calc_gravity`) within the test files. All tests must verify the actual production path executed by `tick_session` or the official production domain helper functions.
   - Test scoring and gravity calculations for exactly 0, 1, 2, 3, and 4 cleared rows under various pre-lock levels (e.g. Level 1, Level 2).
   - Test level transition boundary crossings explicitly (e.g., crossing from 9 to 10 lines, and crossing from 9 to 11 lines via a double-clear).
   - Verify that soft drops do not award any additional points.
   - Verify that gravity reaches and stays at the 100 ms floor.
   - Use valid, unrotated horizontal/vertical piece and board configurations as fixtures for reachable line clears.
   - For 3 and 4 cleared rows (which are physically unreachable without rotation during manual play), an isolated domain fixture or a mocked cleared-row count may be used, but it must execute the real production scoring/state-update path.
2. **Deterministic Random Selection & Draw Counts (QA-02)**:
   - Patch the production random source (`secrets.choice`) with deterministic sequences.
   - Assert precise draw counts: 
     - New game: exactly 2 draws (one active, one next).
     - Normal piece lock: exactly 1 draw (for the new next piece).
     - First hold (empty Hold slot): exactly 1 draw (to replenish next piece).
     - Swap hold (occupied Hold slot): exactly 0 draws.
     - Repeated state GET requests: exactly 0 draws.
     - Rejected hold (can_hold is false): exactly 0 draws.
     - All actions after game over (tick, move, hold): exactly 0 draws.
   - Simple inequality assertions are insufficient, as a new random draw can return the same type.
3. **Deep State Snapshot Comparison (QA-03 / QA-04)**:
   - Compare full serialized deep snapshots of the game state to guarantee immutability for repeated GET, rejected Hold, and every tick, move, and hold attempt after game over.
   - Before a restart, dirty every Stage 2 counter, hold flag/slot, and board cell. Verify that after restart, every Stage 2 default is restored (score = 0, lines = 0, level = 1, gravity_interval_ms = 500, hold_piece = null, can_hold = true), the board is fully empty, a new unique ID is generated, and the active/next pieces are valid.
4. **Correction of Mislabeled Fixtures (QA-05)**:
   - Replace any bent pieces mislabeled as "I" in unit/integration scoring fixtures with the real unrotated horizontal I template (`[[0, 3], [0, 4], [0, 5], [0, 6]]`) and matching board gaps.
   - Preserve original behavior assertions and all meaningful Stage 1 regression checks.

### Frontend Correctness & Verification Requirements
5. **Restart Isolation and Request Ownership (QA-06)**:
   - Implement a monotonically increasing restart/generation counter. Never reset request counters across restarts.
   - Ensure that a late-resolving response, error, or `finally` block from an older generation does NOT overwrite a newer game state, set its error, release its lock, or clear its loading state.
   - While a restart is pending, prevent any old-game commands (move, tick, hold) from dispatching or restoring the old session.
   - Promptly cancel and suppress the old game's gravity timer on restart.
6. **Mutation Request Serialization (QA-06)**:
   - Serialize all tick, move, and hold mutation requests with a synchronous in-flight guard or equivalent ordered queue.
   - Discard responses from older sequence numbers or previous generations. Sequence numbers alone do not establish authoritative server execution order; in-flight guards must prevent concurrent overlapping mutations.
   - Locks must recover after errors and be released only by their owning generation/request.
7. **Deferred Promise Concurrency Tests (QA-06 / QA-09)**:
   - Implement deferred-promise frontend tests that verify:
     - Two overlapping start calls resolving in reverse order (newest must win, oldest must be discarded).
     - Old creation failure/finally resolving while a newer start is pending does not corrupt state.
     - Old-game actions attempted during a pending restart are blocked.
     - An old action finishing after the new game has started is discarded.
     - Lock ownership and recovery after requests fail.
8. **Timer Scheduling and Keyboard Input Tests (QA-09)**:
   - Test the actual gravity timer at 500 ms, 450 ms, and 100 ms, verifying cancellation and rescheduling.
   - Ensure no overlapping delayed ticks are created.
   - Ensure the timer stops immediately on game over or component unmount, and recovers after request failures.
   - Test keyboard inputs for lowercase 'c' and uppercase 'C' independently.
9. **Next Piece Preview and Component Layout (QA-07)**:
   - Correct the T tetromino preview representation to match the backend's initial orientation: one centered cell on the top row, three on the next row (i.e. coordinates `[[0, 4], [1, 3], [1, 4], [1, 5]]` relative to standard templates).
   - Verify all seven preview shapes (I, O, T, S, Z, J, L) against normalized backend template coordinates.
   - Add rendered App/component unit tests for score, lines, level, empty/populated Hold, next preview, Hold button clicks, and disabled states.
   - Keep preview row/grid CSS; add layout styles only if still absent.
   - Use stable coordinate keys (e.g. `row-col` or similar stable strings) for cell rendering, not changing values or raw array index keys.

### Quality, Environment, and Reproducibility Requirements
10. **Dependency Vulnerabilities & Environment Integrity (QA-10)**:
    - Address original npm dependency vulnerabilities with compatible patched versions recorded in `package-lock.json`. Do not use `--force` or `--legacy-peer-deps`.
    - Do not use suppressions, rule exclusions, or weakened assertions to pass.
    - Any Python installations or environment updates must use a Stage 2 local virtual environment (`.venv`) and never mutate the shared Stage 1 toolchain.
11. **Coverage Reports (QA-11)**:
    - Produce current backend coverage XML at `docs/coverage.xml`, frontend LCOV at `frontend/coverage/lcov.info`, and text/text-summary output.
    - Explicitly configure coverage reporters; default HTML/clover reports do not satisfy LCOV. Include all src files in coverage. Keep production TypeScript build and test type checks active.
12. **Automation & Audit Reports (QA-12)**:
    - Run non-watch backend/frontend suites, production builds, and audits. Save commands and outputs under `docs/` with `qa-iteration-1` labels.
    - Run `../shared/scan-spec-kit.ps1` and `../shared/fetch-sonar-spec-kit.ps1` for project `tetris-stage2-speckit` and verify the gate using current coverage.

