# Requirements Specification: Browser-Based Tetris Study - Stage 2, Option A (Revised)

This document contains the authoritative, atomic, and testable requirements for Stage 2, Option A of the browser-based Tetris study, extending Stage 1 Option A. It resolves all identified gaps regarding concurrency, timers, scoring, UI, verification, and compliance.

---

## 1. Atomic Requirements (Req-S2-1 to Req-S2-40)

### Group S2-A: Stage 2 State Expansion & PII Compliance
- **Req-S2-1:** The backend game state representation MUST expand to include the following fields:
  - `score` (integer, starts at 0)
  - `total_lines` (integer, cumulative cleared-line count, starts at 0)
  - `level` (integer, starts at 1)
  - `gravity_interval_ms` (integer, starts at 500)
  - `next_piece` (string/TetrominoType, representing the previewed next piece)
  - `hold_piece` (string/TetrominoType or `null`, representing the held piece, starts as `null`)
  - `can_hold` (boolean, indicates if Hold can be performed, starts as `true`)
- **Req-S2-2:** Every backend API route (including all game endpoints and any existing root welcome/greeting routes) MUST explicitly declare an explicit Pydantic model in the `response_model` argument of its route decorator, in compliance with the `maria/fastapi` pii-sanitisation rule. Routes MUST NOT return raw dicts or untyped data. The existing `GameStateModel` already qualifies as a response model for the game endpoints, and its public imports and HTTP payload MUST stay compatible. No unnecessary class renaming (such as introducing a new `GameResponse`) is required.
- **Req-S2-3:** The state schema returned by all game endpoints (`POST /api/games`, `GET /api/games/{id}`, `POST /api/games/{id}/tick`, `POST /api/games/{id}/move`, and `POST /api/games/{id}/hold`) MUST conform to this extended, validated structure:
  ```json
  {
    "id": "string-uuid",
    "board": [ [null, null, ...], ... ],
    "active_piece": {
      "type": "I" | "O" | "T" | "S" | "Z" | "J" | "L",
      "origin": [row, col],
      "cells": [ [row, col], ... ]
    } | null,
    "status": "playing" | "game_over",
    "score": 0,
    "total_lines": 0,
    "level": 1,
    "gravity_interval_ms": 500,
    "next_piece": "I" | "O" | "T" | "S" | "Z" | "J" | "L",
    "hold_piece": "I" | "O" | "T" | "S" | "Z" | "J" | "L" | null,
    "can_hold": true
  }
  ```

### Group S2-B: Randomized Spawning and Next Piece Lifecycle
- **Req-S2-4:** At game creation (`POST /api/games`) or game restart, the game MUST spawn an initial `active_piece` at origin `(0, 3)` using a randomly selected Tetromino type, and independently generate a random Tetromino type for `next_piece`.
- **Req-S2-5:** Peeking at game state via `GET /api/games/{id}` MUST be read-only and MUST NOT consume, alter, or advance `next_piece`, nor mutate any other part of the state.
- **Req-S2-6:** When a piece locks into the board (and does not trigger an immediate game over via row-zero locking):
  - A normal spawn of a new piece MUST be performed.
  - The new `active_piece` MUST be created at origin `(0, 3)` using the current `next_piece` type.
  - A new random Tetromino type MUST be generated and assigned to `next_piece` to replace the consumed preview.
  - `can_hold` MUST be reset to `true`.
- **Req-S2-7:** If a normal spawn is attempted (Req-S2-6) but the newly spawned piece is obstructed at origin `(0, 3)` (meaning its initial absolute coordinates are illegal due to overlap with settled board blocks), the game status MUST transition from `"playing"` to `"game_over"`, and `active_piece` MUST be set to `null`. This spawn attempt consumes the previewed `next_piece` and generates exactly one new `next_piece` before transitioning to `"game_over"`.

### Group S2-C: Hold Piece Mechanism
- **Req-S2-8:** The API MUST expose a new endpoint `POST /api/games/{id}/hold` which allows the user to hold the current piece once per active piece life.
- **Req-S2-9:** If `can_hold` is `false` (meaning a Hold was already performed for the current active piece life) or if the game status is `"game_over"`, any hold request MUST be rejected, returning the current game state unchanged without any mutations (returning HTTP 200 with the unmodified state).
- **Req-S2-10 (First Hold):** If `can_hold` is `true` and `hold_piece` is `null`:
  - The current `active_piece.type` MUST be saved into `hold_piece`.
  - The `active_piece` MUST be replaced by spawning a new piece at origin `(0, 3)` in its initial orientation using the current `next_piece` type.
  - A new random Tetromino type MUST be generated and assigned to `next_piece` (consuming the preview and generating exactly one new preview).
  - `can_hold` MUST be set to `false`.
- **Req-S2-11 (Subsequent Swap Hold):** If `can_hold` is `true` and `hold_piece` is NOT `null`:
  - The current `active_piece.type` and the current `hold_piece` type MUST be swapped.
  - The `active_piece` MUST be replaced by spawning a new piece at origin `(0, 3)` in its initial orientation using the previous `hold_piece` type.
  - The current `next_piece` MUST remain unchanged (it is NOT consumed, and no new preview is generated).
  - `can_hold` MUST be set to `false`.
- **Req-S2-12 (Obstructed Hold):** When a Hold is triggered (either first or swap), if spawning the new piece at origin `(0, 3)` is obstructed (meaning its absolute coordinates overlap with any settled blocks on the board), the game status MUST transition from `"playing"` to `"game_over"`, and `active_piece` MUST be set to `null`.
- **Req-S2-13 (Hold on Restart):** On game restart, `hold_piece` MUST be reset to `null` and `can_hold` to `true`.

### Group S2-D: Scoring, Leveling, and Progressive Gravity
- **Req-S2-14:** Scoring MUST be evaluated immediately after an active piece locks and lines (if any) are cleared.
- **Req-S2-15:** For a lock that clears $N$ rows simultaneously (where $N \in \{1, 2, 3, 4\}$), the score awarded immediately MUST be calculated as follows, multiplied by the level $L_{\text{prev}}$ *immediately before* that lock:
  - For $N = 1$ row cleared: $+100 \times L_{\text{prev}}$ points.
  - For $N = 2$ rows cleared: $+300 \times L_{\text{prev}}$ points.
  - For $N = 3$ rows cleared: $+500 \times L_{\text{prev}}$ points.
  - For $N = 4$ rows cleared: $+800 \times L_{\text{prev}}$ points.
- **Req-S2-16:** A lock that clears no rows ($N=0$) MUST award $0$ points.
- **Req-S2-17:** Soft dropping (moving down manually via `POST /api/games/{id}/move` with direction `"down"`) MUST NOT grant any additional points.
- **Req-S2-18 (Level Formula):** After adding the newly cleared rows $N$ to the cumulative line count `total_lines`, the new level $L$ MUST be computed as:
  $$L = 1 + \lfloor \frac{\text{total\_lines}}{10} \rfloor$$
- **Req-S2-19 (Progressive Gravity Formula):** The gravity interval `gravity_interval_ms` MUST be updated based on the new level $L$ using the formula:
  $$\text{gravity\_interval\_ms} = \max(100, 500 - 50 \times (L - 1))$$

### Group S2-E: Terminal Transition Rules (Game Over & Preview Interaction)
- **Req-S2-20 (Row-Zero Locking):** The row-zero locking rule (legacy Req26) is retained: if a gravity tick is executed and the active piece is already locked at row 0 (any of its cells lie in row 0) and cannot move down, the game status MUST transition to `"game_over"`.
- **Req-S2-21 (No Preview Consumption on Row-Zero Locking):** When row-zero locking triggers (Req-S2-20), the game ends immediately without attempting a normal spawn. Therefore, the previewed `next_piece` MUST NOT be consumed, and no new `next_piece` draw/invention occurs.

### Group S2-F: Isolated-Domain Testing Fixtures for 3 & 4 Line Clears
- **Req-S2-22:** Since the seven unrotated canonical Tetromino shapes (unrotated, as rotation is forbidden) have a maximum vertical height of at most 2 rows, it is mathematically impossible to clear 3 or 4 rows simultaneously during normal UI-based play.
- **Req-S2-23:** To verify the scoring logic for 3 and 4 row clears without rotating an I, creating a vertical/custom tetromino, fabricating active cells, or mutating SHAPES (even in the isolated domain tests), the backend test suite MUST use **explicitly labeled isolated-domain fixtures** (such as `backend/tests/test_scoring.py`). These fixtures will programmatically pre-populate a board with exactly THREE or FOUR ALREADY-COMPLETE settled rows, and place an otherwise canonical O above those rows at a legal resting origin (e.g. resting directly on top of the completed rows). The test locks this canonical O through the real tick/lock/clear/scoring path, verifying exact rows, scoring thresholds ($500$ or $800$ times the pre-lock level), level calculation thresholds, and canonical relative cells. The prefilled completed rows make this a scoring-domain fixture, not reachable ordinary gameplay.
- **Req-S2-24:** The application code and documentation MUST NOT claim that ordinary UI gameplay can clear 3 or 4 rows, nor provide any UI-level controls or mechanisms (such as rotation or custom/vertical shapes) to enable 3 or 4 row clears during standard gameplay. The seven canonical shapes are kept immutable.

### Group S2-G: Frontend Game Lifecycle and Mutating FIFO Request Queue
- **Req-S2-25 (Lifecycle Generations):** The frontend MUST assign a unique *Lifecycle Generation ID* (such as a monotonic integer) that is incremented on every game creation and game restart. The client-side state MUST track this `generationId`.
- **Req-S2-26 (Strict Mutating Request FIFO Queueing):** The frontend MUST serialize all game-bound mutating network requests (tick, move, hold) within their owning game generation. It MUST maintain a request queue processed in FIFO order:
  - No game-bound mutating request can be dispatched to the network until all preceding mutating requests in that same generation have completed both network transit and JSON parsing.
  - Merely dropping older responses while concurrently dispatching mutations does not ensure backend ordering. FIFO sequencing is mandatory.
- **Req-S2-27 (Restart Preemption and Old-Generation Queue Isolation):** A game creation or restart is executed independently of the game-bound queue. A restart MUST create a NEW game generation immediately and issue its create request (new `POST /api/games` returning HTTP 200) without waiting behind any old queued or in-flight fetch or JSON parse. No game-bound request may dispatch before the new game's ID is ready. On game creation or restart, the old request queue and in-flight guards MUST be immediately aborted, discarded, and the generation invalidated.
- **Req-S2-28 (Post-Transit and Post-Parse Ownership Checks):** The frontend MUST verify the active `generationId` ownership at two separate stages:
  1. Immediately after the fetch resolves (before calling `response.json()`).
  2. Immediately after the parsed JSON payload is returned (`await response.json()`).
  - These checks MUST be executed across all success, error (`catch`), and `finally` paths.
  - If a check fails (meaning a restart or game disposal occurred during transit or parsing), the response MUST be discarded, no state updates MUST be written, and the stale completion MUST NOT clear the newer generation's in-flight guard or reschedule its timers. Successive create/restart responses and errors are generation-owned after both fetch and JSON parsing. Unmount/disposal invalidates the generation.
- **Req-S2-29 (Usable Hold on Restart):** Hold MUST remain immediately usable again in the new game generation even if a hold request from a previous game generation is still pending or in-flight.

### Group S2-H: Automatic Ticks and Rescheduling Rules
- **Req-S2-30 (At Most One In-Flight Tick):** Automatic ticks MUST have at most one owned queued/in-flight tick request per game generation.
- **Req-S2-31 (Timer Safety and Multi-Queue Ownership):** The client-side game engine MUST make timer ownership safe across two or more queued manual mutations, not just one. If mutation A completes while mutation B is already queued, A MUST NOT leave an active timeout that later fires during or after B. The engine MUST prefer scheduling the automatic gravity tick timeout ONLY when the owning mutation queue is idle. Any queued manual dispatch (as well as level/gravity changes, game restart, game over, or component unmount) MUST also immediately cancel any exact previously scheduled timer handle.
- **Req-S2-32 (Slow Response Burst Prevention):** Automatic ticks MUST NOT create a burst of rapid descents following slow network responses, and overdue automatic ticks MUST NOT be replayed as a burst. At most one owned queued/in-flight automatic tick can exist at any time. After the last authoritative completion, the gravity timer MUST wait a FULL latest gravity interval from that completion before firing, verified against the active generation.
- **Req-S2-33 (Strict Timer Validation & Error Handling):** Stale completions, mutation error/finally paths, and older generation events cannot leave a dangling timer or clear a newer timer. Explicit test scenarios must prove:
  - (a) Queued mutation A, followed by delayed mutation B whose response changes the interval to 450ms: no gravity tick fires before 450ms after B's completion.
  - (b) Queued mutation A, followed by mutation B returning game_over: no later timeout or tick is executed.
  - (c) Mutation B error/finally path and stale old-generation completion cannot leave a dangling timer or clear a newer timer.
- **Req-S2-34 (StrictMode Compatibility):** The client-side game engine MUST handle setup, cleanup, and re-setup safely across React StrictMode. Timer cleanup MUST NOT permanently disable keyboard controls or leave dangling interval timers. On restart, input handlers MUST be cleanly reinstalled for the new game, and cleanup of the old game's listeners must not permanently disable controls.

### Group S2-I: Explicit UI and Verification Artifacts Requirements
- **Req-S2-35 (HUD Indicators):** The frontend UI MUST render:
  - **Score HUD:** displays current `score` integer.
  - **Lines HUD:** displays current `total_lines` integer.
  - **Level HUD:** displays current `level` integer.
  - **Gravity HUD:** displays current `gravity_interval_ms` (e.g., "500 ms").
- **Req-S2-36 (Preview and Hold Panels):** The frontend UI MUST render:
  - **Next Preview Container:** displays the canonical shape of the `next_piece`.
  - **Hold Container:** displays the canonical shape of the `hold_piece` (or empty if `null`), along with a visual text/color indicator of the `can_hold` status.
- **Req-S2-37 (Interactive Controls):** The UI MUST support:
  - A visual "Hold" button which is disabled (`disabled={!canHold || isGameOver}`) when `can_hold` is `false` or the game status is `"game_over"`.
  - A keyboard route for Hold: pressing the `C` or `c` key triggering Hold.
  - A mouse click route for Hold: clicking the Hold button.
- **Req-S2-38 (Coverage Artifact Paths):** Verification MUST generate the following artifacts at the specified locations:
  - Backend test coverage report (XML format) MUST be generated at `docs/coverage.xml`.
  - Full production frontend-src test coverage report (LCOV format) MUST be generated at `frontend/coverage/lcov.info`.
- **Req-S2-39 (Sonar Quality Gate & NPM Audit):**
  - The independently configured Sonar gate requires: **New Coverage >= 80%**, **New Duplication <= 3%**, and **Zero new violations**. No thresholds shall be weakened.
  - Baseline npm audit reports 7 vulnerabilities (3 moderate, 2 high, 2 critical) which MUST be remediated through compatible, verified package updates.
- **Req-S2-40 (Frozen Common Seed):** Game mechanics remain frozen: no rotation, no hard drop, no wall kicks, no combos, no persistence, no database, and no multiplayer. Random seed `20260929` or explicit piece lists in test fixtures remain the sole basis for deterministic verification.

---

## 2. Acceptance Criteria

| ID | Description | Detailed Acceptance Criteria |
| --- | --- | --- |
| **AC-S2-1** | State Schema and PII Compliance | `POST /api/games` returns HTTP 200 with an empty board, a randomly spawned active piece, `score: 0`, `total_lines: 0`, `level: 1`, `gravity_interval_ms: 500`, a valid `next_piece`, `hold_piece: null`, and `can_hold: true`. Every route declares an explicit `response_model` (such as `GameStateModel` for games, preserving compatibility and payload) conforming to the allowlist in the PII rule. |
| **AC-S2-2** | Score, Level, and Gravity Scaling | Locking a piece that clears 1 or 2 rows awards `100 * level` or `300 * level` points immediately using the pre-lock level, updates `total_lines`, recalculates `level`, and reduces `gravity_interval_ms` dynamically with a floor of 100 ms. |
| **AC-S2-3** | Isolated-Domain unit tests | Explicitly labeled backend unit tests pre-populate the board with 3 or 4 ALREADY-COMPLETE settled rows, and place a canonical O at a legal resting origin above them. The tests lock the canonical O block through the real tick/lock/clear/scoring path (without rotation or custom shapes) and verify exact rows, Level-scoring multipliers (500/800 times pre-lock level), and canonical relative cells. |
| **AC-S2-4** | First Hold - Empty Hold Slot | Executing `POST /api/games/{id}/hold` when `hold_piece` is `null` and `can_hold` is `true` saves the current active piece type in `hold_piece`, spawns the `next_piece` at `(0, 3)`, bumps the `next_piece` preview with a new random piece, and sets `can_hold` to `false`. |
| **AC-S2-5** | Swap Hold - Occupied Hold Slot | Executing `POST /api/games/{id}/hold` when `hold_piece` is occupied and `can_hold` is `true` swaps the current active piece with `hold_piece`, spawns the previous held piece at `(0, 3)`, leaves `next_piece` unchanged (no new preview generated), and sets `can_hold` to `false`. |
| **AC-S2-6** | Hold Rejection & Reset | After a piece locks (whether it clears rows or not), `can_hold` is reset to `true`. Calling Hold when `can_hold` is `false` or after game over returns HTTP 200 with unchanged state. |
| **AC-S2-7** | Terminal Transitions - No Preview Consumption | If a gravity tick results in row-zero locking (game over), the game state transitions to `"game_over"`, and the `next_piece` is NOT consumed (remains identical to before the tick). |
| **AC-S2-8** | Obstructed Spawn and Hold Game Over | If an obstructed normal spawn or an obstructed Hold spawn is triggered at origin `(0, 3)`, the game state transitions to `"game_over"` and `active_piece` is set to `null`. |
| **AC-S2-9** | Client-Side Lifecycle FIFO Concurrency | The frontend serializes game-bound mutating requests (tick, move, hold) in a strict FIFO queue within each `generationId`. Restart immediately preempts, invalidates the old generation, clears all old queues/guards, and issues its create request independently of any old queued or in-flight operations. Stale/out-of-order completions are checked post-transit and post-parse and discarded on mismatch. No game-bound request may dispatch before the new game's ID is ready. |
| **AC-S2-10** | Client-Side Tick Rescheduling & React StrictMode | Gravity ticks have at most one owned tick per generation, prevent bursts, and are cancelled exactly on manual action, restart, unmount, and level change. If mutation A completes while mutation B is already queued, A must not leave an active timeout. The engine prefers scheduling only when the mutation queue is idle, and any queued manual dispatch immediately cancels any exact previously scheduled handle. Tests prove: (a) queued A then delayed B changing interval to 450ms, no tick before 450ms after B; (b) queued A then B game_over, no later timeout/tick; (c) B error/finally/stale completion cannot leave or clear a newer timer. React StrictMode's setup/cleanup works without leaking timers or permanently disabling input handlers. |

---

## 3. Run and Test Commands

All configuration and verification commands remain **pending** until actually executed in the implementation and verification phases.

### Backend Commands (run from `backend/` directory):
- **Run FastAPI server:**
  ```bash
  fastapi dev app/main.py --port 8000
  ```
- **Run backend tests:**
  ```bash
  pytest -v
  ```
- **Collect coverage and generate XML report:**
  ```bash
  pytest --cov=app --cov-report=xml:../docs/coverage.xml tests/
  ```
  *(Generates the XML report directly in the workspace `docs/` folder, which is `../docs/` from the `backend/` folder.)*

### Frontend Commands (run from `frontend/` directory):
- **Production Build (Zero Compile/Type Errors):**
  ```bash
  npm run build
  ```
- **Linting and Type-Checking:**
  ```bash
  npm run lint
  # and/or
  npx tsc --noEmit
  ```
- **Run local development server:**
  ```bash
  npm run dev
  ```
- **Run frontend tests with full coverage:**
  ```bash
  npx vitest run --coverage
  # or
  npm run test -- --coverage
  ```
  *(Utilizes a compatible installed Vitest coverage provider such as `@vitest/coverage-v8`, ensuring that the production-src coverage includes every production module, including `main.tsx`, and outputs the LCOV report directly to `frontend/coverage/lcov.info`.)*
