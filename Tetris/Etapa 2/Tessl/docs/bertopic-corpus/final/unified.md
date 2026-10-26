# Requirements Specification: Browser-Based Tetris Study - Stage 2, Option A (Revised)

## Q01-retry Note (October 25, 2026)
All original Stage2 functionality remains required; StrictMode generations must be monotonic, never reset/reused; both failing external scenarios must pass; Sonar gate remains FAILED until actual OK, with exact new violations distinguished from inherited open findings.

This document contains the authoritative, atomic, and testable requirements for Stage 2, Option A of the browser-based Tetris study, extending Stage 1 Option A. It resolves all identified gaps regarding concurrency, timers, scoring, UI, verification, and compliance.

---

## Post-Implementation Independent QA (Q01) Correction Specification
This section records the concrete observed failures and explicit acceptance criteria for the Q01 correction.

### 1. Concrete Observed Failures
- **Failure 1 (StrictMode Dead Controls):** Under React StrictMode's mount-unmount-remount cycle, the first unmount sets `generationIdRef.current = -1`. When the second mount starts and increments it, the active generation is set to `0`. Since the mutation queue (`queueMutation`) rejects any request with `currentGen <= 0`, all subsequent user actions (Hold, movement keys) are ignored, and controls remain dead.
- **Failure 2 (Stale Response Overwrite):** If a user restarts the game after StrictMode's second mount, the generation number resets or is reused (e.g., set to 1). This allows the deferred/slow response from the first obsolete initial creation to overwrite the new state of the restarted game (setting ID to obsolete and score to 999).

### 2. Explicit Acceptance Criteria
- **AC-Q01-1 (Monotonic Lifecycle Generation ownership):** The frontend MUST use strictly monotonic lifecycle generation IDs that never reuse a prior generation or set the active generation to `<= 0`. StrictMode must NOT be disabled.
- **AC-Q01-2 (Stale response protection):** Old creation responses must be completely isolated and ignored if a restart or unmount has occurred. Tests must verify wrapping App in StrictMode, deferring the first create response, and asserting correct control responsiveness and no stale state replacement after restart.
- **AC-Q01-3 (Zero Sonar violations):** All 7 new Sonar violations (empty catch blocks, nested template literals, redundant `act()`, low contrast colors, missing documented responses, duplicated string literal, pydantic missing default value) MUST be resolved in the code and tests.

---

## Post-Implementation Independent QA (Q02) Correction Specification
This section records the concrete observed failures, CLI settings schema corrections, and explicit acceptance criteria for the Q02 correction phase.

### 1. Concrete Observed Failures
- **Failure 3 (Obsolete Create Rejection with Falsey Error Falls Through):** An independent researcher edge-case harness (`docs/acceptance/07-independent-repeat/falsey-vitest.json`) fails. It renders the real App under StrictMode, resolves the second creation, restarts successfully, then rejects the obsolete first creation with `null`. The old catch block sets the new game's connection-error panel despite being obsolete. This happens because the catch block uses `const ignoredErr = err; if (ignoredErr) return;`, which falls through when `err` is falsey (e.g., `null` or `undefined`), thereby incorrectly setting the current game's error state. Promise lifecycle ownership must be absolute and independent of error truthiness.
- **Failure 4 (Incorrect .gemini/settings.json Aliases Schema):** The customAliases under `modelConfigs` in `.gemini/settings.json` wrongly use string values. The official schema requires nested objects containing modelConfig values.

### 2. Explicit Acceptance Criteria
- **AC-Q02-1 (Unconditional Return for Obsolete Lifecycles):** For every obsolete lifecycle (where `generationIdRef.current !== currentGen`), the return MUST be completely unconditional in all catch/finally paths. It must NOT check or depend on the error's truthiness.
- **AC-Q02-2 (Clean Current-Generation Failure Handling):** For current-generation failures, the error must be handled or reported appropriately without using empty if statements, dummy variables, or void casts, to satisfy Sonar rules cleanly.
- **AC-Q02-3 (Correct Custom Aliases Object Schema):** The `.gemini/settings.json` customAliases configuration MUST be updated to use the nested object structure:
  ```json
  "modelConfigs": {
    "customAliases": {
      "loop-detection": { "modelConfig": { "model": "gemini-3.5-flash" } },
      "loop-detection-double-check": { "modelConfig": { "model": "gemini-3.5-flash" } }
    }
  }
  ```
- **AC-Q02-4 (Regression Testing for Falsey Obsolete Rejections):** Add dedicated, automated regression tests verifying that falsey obsolete rejections (using both `null` and `undefined`) are cleanly discarded without displaying an error panel or corrupting the current game state, while retaining all prior race outcomes and tests.

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


# Tessl Session Notes: Browser-Based Tetris Study - Stage 2, Option A (Revised)

## Q01-retry Note (October 25, 2026)
All original Stage2 functionality remains required; StrictMode generations must be monotonic, never reset/reused; both failing external scenarios must pass; Sonar gate remains FAILED until actual OK, with exact new violations distinguished from inherited open findings.

This document logs the design decisions, real Tessl integration status, resolved material ambiguities, and the traceable implementation/verification checklist for Stage 2, Option A.

---

## 1. Tessl Integration Status & Evidence

We inspected and verified the local plugin configuration and status in this workspace.

- **Tessl Status Check:** In invocation 03, the agent called `mcp_tessl_status` once and read local plugin files to orient in the project. The status tool reported:
  - **manifest.summary.inSync:** 2 (All dependencies in sync)
  - **Tiles in Sync:**
    - `maria/fastapi` (v0.1.0) - located locally at `.tessl/plugins/maria/fastapi/`
    - `softaworks/agent-toolkit` (commit `3027f20f3181758385a1bb8c022d4041dfb4de84` with `react-dev` skill) - located locally at `.tessl/plugins/softaworks/agent-toolkit/`
  - **Readiness:** `"partial"` due to lack of CLI authentication (`"not-authenticated"` blocker).
- **Tessl CLI / Authentication Provenance:** The Tessl CLI currently remains unauthenticated.

- **FastAPI Plugin Context Reading:** We read the locally installed FastAPI rules:
  - File: `.tessl/plugins/maria/fastapi/rules/pii-sanitisation.md`
  - Context: The `pii-sanitisation` rule mandates that every FastAPI route MUST declare an explicit Pydantic `response_model` to serve as an allowlist to prevent exposure of PII. This rule applies to ALL routes.

- **React Skill Context Reading:** We read the locally installed React developer skill:
  - File: `.tessl/plugins/softaworks/agent-toolkit/skills/react-dev/SKILL.md`
  - Context: This skill covers type-safe React patterns, including React 18/19 and proper event/timer handlers.

---

## 2. Observed Workflow Deviation (Invocation 05)

To ensure strict compliance with engineering standards, we record the following workflow deviation honestly:
- **Deviation:** Historical internal code and test fixes in invocation 05 occurred **without prior specification revision**. The code and tests were modified first, and the specifications were not updated beforehand to reflect the exact failures or design updates. 
- **Correction:** For the current correction (Post-implementation independent QA Q01), we are revising the specifications first in `specs/stage2/requirements.md` and `specs/stage2/session_notes.md` before making any application, test, or configuration file edits.

---

## 3. Concrete Observed Failures & Explicit Acceptance

We observed the following concrete failures from the QA Vitest suite (`05-races-configured-vitest.json`):

### Failure 1 (StrictMode Controls Disabled)
- **Observation:** Under React StrictMode (which runs setup-cleanup-setup on mount), the cleanup of the first mount sets `generationIdRef.current = -1`. The subsequent second mount's start increments `generationIdRef` to `0`. However, the mutation queue (`queueMutation`) rejects any request where `currentGen <= 0`. As a result, the initial game appears, but Hold and keyboard dispatch perform no mutations (the controls are dead).
- **Root Cause:** Reusing or resetting generations to `<= 0` causes the queue guards to reject valid actions under StrictMode's lifecycle.
- **Acceptance Criteria:** Use strictly monotonic lifecycle ownership that never reuses a prior generation, and ensures the active generation is always positive and verified. Do not remove StrictMode or weaken guards.

### Failure 2 (Stale Response Overwrite on Restart)
- **Observation:** After StrictMode's second creation succeeds and the user restarts successfully, resolving the first obsolete initial creation overwrites the new state (setting id to obsolete, score 999). StrictMode cleanup/reset plus restart reuses generation 1, letting the old creation's deferred response overwrite the restarted state.
- **Root Cause:** A restarted game can have its state overwritten by a stale `create` response because generation numbers are reused or the fetch/JSON responses from older creations are not fully isolated.
- **Acceptance Criteria:** Ensure old create/fetch/JSON/catch/finally paths cannot regain ownership of the state or overwrite the current active generation. Add meaningful tests that wrap App in StrictMode, defer the first create response, and assert both correct initial controls and no obsolete replacement after restart.

### Failure 3 (Obsolete Create Rejection with Falsey Error Falls Through)
- **Observation:** An independent researcher edge-case harness (`docs/acceptance/07-independent-repeat/falsey-vitest.json`) fails under StrictMode. It renders the real App under StrictMode, resolves the second creation, restarts successfully, then rejects the obsolete first creation with `null`. The old catch block sets the new game's connection-error panel despite being obsolete.
- **Root Cause:** The old catch block contained conditional logic: `const ignoredErr = err; if (ignoredErr) return;`. Since `err` was `null` (a falsey value), the return statement was bypassed. Thus, the obsolete rejection fell through and set the error state of the current/new active game.
- **Acceptance Criteria:** Restore unconditional return for every obsolete lifecycle in all catch/finally paths. Do not check error truthiness when verifying generation/lifecycle ownership.

### Failure 4 (Incorrect customAliases Schema in settings.json)
- **Observation:** `.gemini/settings.json` has customAliases set as strings instead of the nested object structure containing `modelConfig`.
- **Root Cause:** The aliases were configured as strings instead of objects as defined in the official model config schema.
- **Acceptance Criteria:** Update the settings configuration file with the exact required object nesting structure.

---

## 4. SonarQube Quality Gate Status & Violations

The SonarQube Quality Gate is currently in the **ERROR** state due to the following 7 new violations:
1. `typescript:S2486`: `App.tsx` catch blocks are empty after console.error removal (lines 104, 173).
2. `typescript:S4624`: `App.tsx` nested template literal in mini-grid className (line 257).
3. `typescript:S8980`: `App.test.tsx` redundant `act()` wrappers around helpers which flush themselves (lines 181, 249).
4. `css:S7924`: `index.css` line 471 low-contrast newly added hold styling.
5. `python:S8415`: `games.py` Hold404 missing declared responses (HTTPException with status code 404 must be documented in the `responses` parameter).
6. `python:S1192`: Duplicated literal `"Game session not found"` 4 times in `games.py`.
7. `python:S8396`: Optional field in `game.py` (e.g. `hold_piece`) is missing an explicit default value.

These are **new violations** introduced during Stage 2 development. They are not inherited baseline waivers, and the Quality Gate is strictly **failed** until we fix them. We will resolve all 7 new violations directly in the source/css/tests.

---

## 5. Traceable Implementation & Verification Checklist

- [x] **Surgical StrictMode Lifecycle & Timer Fixes (App.tsx):**
  - Implement strictly monotonic generation IDs that never reset to <= 0.
  - Correctly clean up old timers and event handlers on unmount, without permanently disabling controls.
  - Implement double checks on JSON parsing and fetch resolution using active generation.
- [x] **Surgical Q02 Obsolete Catch/Finally Fixes (App.tsx):**
  - Ensure catch and finally blocks of obsolete lifecycles return unconditionally.
  - Remove all conditional `if (ignoredErr)` guards in catch blocks that rely on error truthiness.
  - Handle current-generation errors cleanly and appropriately, without using empty if statements, dummy variables, or void casts.
- [x] **Correct customAliases Schema (.gemini/settings.json):**
  - Update `.gemini/settings.json` `customAliases` under `modelConfigs` to use the correct nested object structure.
- [x] **Resolve SonarQube typescript:S2486:**
  - Add appropriate error handling or comments explaining why errors are ignored in catch blocks.
- [x] **Resolve SonarQube typescript:S4624:**
  - Refactor nested template literals in classNames (App.tsx line 257, TetrisBoard.tsx line 31).
- [x] **Resolve SonarQube typescript:S8980:**
  - Remove redundant `act()` wrappers around already-flushing helpers in `App.test.tsx` (lines 181, 249).
- [x] **Resolve SonarQube css:S7924:**
  - Fix contrast issues in `index.css` line 471 (and other lines like 237, 245, 279, 295, 301).
- [x] **Resolve SonarQube python:S8415:**
  - Document the HTTP 404 response model or description in `games.py` route decorators.
- [x] **Resolve SonarQube python:S1192:**
  - Define a constant for `"Game session not found"` in `games.py`.
- [x] **Resolve SonarQube python:S8396:**
  - Add explicit default values in `game.py` (e.g., `Field(None)` or `None`).
- [x] **Regression Testing for Q02 Falsey Obsolete Rejections (App.test.tsx):**
  - Create robust, automated regression tests verifying that obsolete rejections with `null` or `undefined` do not display error panels or affect the new active game.
  - Ensure all 6 prior race outcomes are retained and pass successfully.
  - Run the fresh new vitest config test suite (Expected 1/1 pass).

