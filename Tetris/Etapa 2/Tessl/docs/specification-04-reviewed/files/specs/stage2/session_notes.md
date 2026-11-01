# Tessl Session Notes: Browser-Based Tetris Study - Stage 2, Option A (Revised)

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
- **Tessl CLI / Authentication Provenance:** The Tessl CLI currently remains unauthenticated. The skills authentication failure observed previously belongs to the earlier recorded invocation. Note that Google Cloud SDK login is a separate service and is NOT Tessl authentication. No researcher or agent has completed Tessl login in this workflow, and the Tessl CLI is unauthenticated. Local context and plugin file reads are accurately labeled. To maintain strict security, we will not initiate a new login or device flow, nor put any ephemeral codes, session tokens, or URLs into these specifications. No new `skills_available` or `search` calls were performed in invocation 03.

- **FastAPI Plugin Context Reading:** We read the locally installed FastAPI rules:
  - File: `.tessl/plugins/maria/fastapi/rules/pii-sanitisation.md`
  - Context: The `pii-sanitisation` rule mandates that every FastAPI route MUST declare an explicit Pydantic `response_model` to serve as an allowlist to prevent exposure of PII. This rule applies to ALL routes (including any existing root welcome route and game-related endpoints). The existing `GameStateModel` is a valid response model that already qualifies, preserving compatible public imports and HTTP payload. No class renaming is performed.

- **React Skill Context Reading:** We read the locally installed React developer skill:
  - File: `.tessl/plugins/softaworks/agent-toolkit/skills/react-dev/SKILL.md`
  - Context: This skill covers type-safe React patterns, including React 18/19 and proper event/timer handlers. We align our state-management design with these type-safe patterns to ensure robust event listener setup/cleanup across React StrictMode.

---

## 2. Material Ambiguities & System Design Decisions

### Ambiguity 1: Game Lifecycle, Queueing, and Generation Ownership
- **Ambiguity:** How to guarantee that rapid manual movements, tick completions, and holds do not experience race conditions or out-of-order execution, and how to isolate old requests upon game creation/restart.
- **Design Resolution:**
  - **Lifecycle Generation IDs:** The frontend maintains a `generationId` integer incremented on each initial game creation and restart.
  - **FIFO Serialized Request Queue:** The frontend serializes all game-bound mutating network requests (tick, move, hold) within their owning game generation using a strict FIFO queue. No game-bound mutating request can be dispatched to the network until all preceding mutating requests in that same generation have completed both network transit and JSON parsing.
  - **Restart Preemption:** A restart is executed independently of the game-bound queue. A restart creates a NEW generation immediately, clearing any old queued requests, resetting in-flight guards, and issuing its create request immediately (via standard Stage 1 restart behavior: new `POST /api/games` returning HTTP 200). It must never wait behind any old queued or in-flight fetch or JSON parse. No game-bound request may dispatch before the new game's ID is ready.
  - **Double-Verification of Ownership:**
    - The active `generationId` ownership is verified at two separate stages: immediately after `fetch()` resolves (before calling `response.json()`), and immediately after `await response.json()` finishes parsing.
    - These checks run across all success, error (`catch`), and `finally` paths.
    - If a mismatch is detected, the response is discarded, no state is updated, and the stale completion does not clear the newer generation's guard or reschedule its timers. Successive create/restart responses and errors are generation-owned after both fetch and JSON parsing. Unmount/disposal invalidates the generation.

### Ambiguity 2: Automatic Gravity Ticks and Timer Rescheduling
- **Ambiguity:** How to prevent gravity ticks from double-firing, bursting, or executing out-of-order alongside manual actions, and how to handle interval changes cleanly in StrictMode.
- **Design Resolution:**
  - **Multi-Queue Timer Safety:** The client-side game engine must make timer ownership safe across two queued manual mutations, not just one. If mutation A completes while mutation B is already queued, A must not leave an active timeout that later fires during or after B.
  - **Idle-Only Scheduling:** The engine prefers scheduling the automatic gravity tick timeout only when the owning mutation queue is idle. Any queued manual dispatch must also immediately cancel any exact previously scheduled handle.
  - **Burst and Overdue Tick Prevention:** There is at most one owned queued/in-flight automatic tick at any time, and overdue automatic ticks must never be replayed as a burst. After the last authoritative completion, the gravity timer waits a FULL latest gravity interval from that completion.
  - **Comprehensive Validation Scenarios:** Explicit tests prove:
    - (a) Queued mutation A, followed by delayed mutation B whose response changes the interval to 450ms: no automatic tick fires before 450ms after B's completion.
    - (b) Queued mutation A, followed by mutation B returning game_over: no later timeout or tick fires.
    - (c) Mutation B error/finally paths and stale old-generation completions cannot leave or clear a newer timer.
  - **StrictMode Cleanup:** Setting up listeners and timers in React StrictMode can result in mount-unmount-remount cycles. We manage cleanup such that unmounting removes all event listeners and clears timers, and mounting safely restores them without leaving duplicate listeners or dangling timeouts. On restart, input listeners are cleanly re-bound for the new game, and cleanup of the old game's listeners will not permanently disable controls.

### Ambiguity 3: UI Design Scaffolding & HUD
- **Ambiguity:** How to layout the score, lines, level, progressive gravity interval, next preview, and hold indicators.
- **Design Resolution:**
  - **Score/Lines/Level/Gravity HUD:** Rendered in a side panel with clear CSS margins and labels (e.g., `"Score: 1200"`, `"Lines: 12"`, `"Level: 2"`, `"Interval: 450 ms"`).
  - **Next Preview Panel:** Renders the single `next_piece` from the backend in a compact 4x4 visual sub-board.
  - **Hold Panel:** Renders the held piece (or empty if `null`) alongside a text label indicating Hold availability (e.g., `"Hold: Available"` in green, or `"Hold: Used"` in red).
  - **Hold Button:** A clear interactive HTML button in the control panel. Clicking this button or pressing the `C`/`c` keys triggers the Hold request. The button is styled as disabled (`disabled`) when `can_hold` is false or when the game status is `"game_over"`.
  - **Backend Consistency:** Keeps `POST /api/games` returning HTTP 200 with `active_piece` at origin `(0, 3)` and the row-zero terminal branch.

### Ambiguity 4: 3-Row and 4-Row Clear Verification
- **Ambiguity:** Unrotated tetrominoes (no rotation is supported in Stage 1/2) cannot clear 3 or 4 rows simultaneously in ordinary play.
- **Design Resolution:**
  - We do not rotate an I, create a vertical/custom tetromino, fabricate active cells, or mutate SHAPES, even in the isolated domain tests. The seven canonical shapes remain completely immutable.
  - **Isolated-Domain Unit Tests:** To verify the scoring rules for 3 and 4 row clears (500 and 800 multiplied by pre-lock level, respectively), we use explicitly labeled isolated fixtures with THREE or FOUR ALREADY-COMPLETE settled rows, and an otherwise canonical O above those rows at a legal resting origin (such as row 17/18, resting on top of the completed rows). The test locks this canonical O through the real tick/lock/clear/scoring path. The prefilled completed rows make this a scoring-domain fixture, not reachable ordinary gameplay. The tests verify exact rows, scoring thresholds (500/800 times the pre-lock level), level progression, and canonical relative cells.

### Ambiguity 5: Compliance and Verification Artifacts
- **Ambiguity:** Establishing independent Sonar compliance and testing standards with explicit command and directory details.
- **Design Resolution:**
  - **Backend Coverage XML:** Executed via `pytest --cov=app --cov-report=xml:../docs/coverage.xml tests/` from the `backend/` directory, saving the XML directly to `docs/coverage.xml` (in the root directory).
  - **Frontend Coverage LCOV:** Executed via `npm run test -- --coverage` or `npx vitest run --coverage` from the `frontend/` directory, using a compatible coverage provider (e.g. `@vitest/coverage-v8`). The production-src coverage includes every production module (including `main.tsx`) and generates the report at `frontend/coverage/lcov.info`.
  - **Production TypeScript Build:** Runs `npm run build` in the `frontend/` directory with zero compile/type errors.
  - **Dependency Audit:** Runs `npm audit` on frontend and handles remediation. We identify that 7 baseline vulnerabilities (3 moderate, 2 high, 2 critical) will be patched in Stage 2 with fully compatible package upgrades.
  - **Quality Gates:** Sonar requirements are strictly enforced (New Coverage >= 80%, New Duplication <= 3%, zero new violations) with no exclusions or bypasses.

---

## 3. Traceable Implementation & Verification Checklist

All implementation and verification items are **pending** until executed during Stage 2.

### Phase 1: Backend Implementation (app/)
- [ ] **State Schema Expansion (`app/models/game.py`):**
  - Add `score: int = 0`, `total_lines: int = 0`, `level: int = 1`, `gravity_interval_ms: int = 500`.
  - Add `next_piece: TetrominoType`, `hold_piece: Optional[TetrominoType] = None`, `can_hold: bool = True`.
  - Ensure `GameStateModel` is updated with these fields, keeping public imports and HTTP payload fully compatible.
  - Declare explicit `response_model` on all API routes, including games and welcome/greeting endpoints to comply with the `maria/fastapi` rules.
- [ ] **Create/Restart Game (`app/controllers/games.py`):**
  - Spawn random type for `active_piece` at `(0, 3)`.
  - Independently spawn a second random type for `next_piece`.
  - Initialize score=0, lines=0, level=1, gravity_interval_ms=500, hold_piece=None, can_hold=True.
- [ ] **Line Clearing & Scoring Formulas (`app/domain/rules.py`):**
  - Prior to clearing rows, calculate score earned using the pre-lock level:
    - 0 rows cleared: +0 points.
    - 1 row cleared: `+100 * level` points.
    - 2 rows cleared: `+300 * level` points.
    - 3 rows cleared: `+500 * level` points (for isolated-domain tests).
    - 4 rows cleared: `+800 * level` points (for isolated-domain tests).
  - Add score points to `score` field.
  - Add cleared rows to `total_lines`.
  - Update level: `level = 1 + floor(total_lines / 10)`.
  - Update interval: `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`.
- [ ] **Normal Spawn Logic on Lock (`app/domain/rules.py`):**
  - If a piece locks and row-zero locking does NOT trigger:
    - Attempt spawn using current `next_piece` at `(0, 3)`.
    - Generate a new random piece type for `next_piece`.
    - Set `can_hold = True`.
    - If obstructed, set status `"game_over"` and clear `active_piece = None`.
- [ ] **Row-Zero Locking Terminal Rules (`app/domain/rules.py`):**
  - If locked piece contains cells in row 0, set status `"game_over"` immediately.
  - Do NOT spawn a new piece, do NOT consume `next_piece` (keep it exactly as is), and set `active_piece = None`.
- [ ] **Hold Piece Controller Route (`POST /api/games/{id}/hold` in `app/controllers/games.py` and `app/domain/rules.py`):**
  - Verify if status is `"game_over"` or `can_hold` is `False`. If so, return unchanged state (HTTP 200).
  - If `hold_piece` is `None` (First Hold):
    - Save current `active_piece.type` to `hold_piece`.
    - Spawn current `next_piece` as the new `active_piece` at origin `(0, 3)`.
    - Generate a new random `next_piece`.
    - Set `can_hold = False`.
  - If `hold_piece` is occupied (Swap Hold):
    - Swap current `active_piece.type` with `hold_piece`.
    - Spawn the previous `hold_piece` as the new `active_piece` at origin `(0, 3)`.
    - Keep `next_piece` unchanged.
    - Set `can_hold = False`.
  - Check for obstructed spawn during hold: if illegal, set status `"game_over"` and `active_piece = None`.

### Phase 2: Backend Verification (tests/)
- [ ] **Stage 2 State Verification Tests:**
  - Verify default initial values in `POST /api/games`.
  - Verify that `GET /api/games/{id}` does not mutate anything.
- [ ] **Scoring and Progression Tests:**
  - Verify 0-row, 1-row, and 2-row clears and corresponding score multipliers.
  - Verify level progression from level 1 to level 2 (clearing 10 lines) and gravity interval decrease from 500ms to 450ms.
- [ ] **Isolated-Domain Unit Tests (Req-S2-23):**
  - Set up explicitly labeled test fixtures to pre-populate 3 or 4 ALREADY-COMPLETE settled rows on the board, and place an otherwise canonical O above those rows at a legal resting origin.
  - Lock the canonical O through the real tick/lock/clear/scoring path (without rotating an I, creating a vertical/custom tetromino, fabricating active cells, or mutating SHAPES).
  - Assert exact rows cleared, level-scoring multipliers (500 or 800 multiplied by pre-lock level), and canonical relative cells.
- [ ] **Threshold-Crossing Level Calculation Test:**
  - Prefill board with 9 lines cleared previously. Lock a piece to clear 1 row (crossing to 10 total lines). Verify that the score uses Level 1 (pre-lock level), and then the level becomes 2.
- [ ] **Gravity Floor Test:**
  - Verify that level 10 (and above) enforces the 100 ms gravity floor.
- [ ] **Hold Mechanism Unit Tests:**
  - Verify first hold saves piece, spawns `next_piece`, draws a new preview, and disables hold.
  - Verify swap hold swaps piece, spawns previous held piece, preserves next preview, and disables hold.
  - Verify hold reset (`can_hold` becomes true again) upon any locking event.
  - Verify rejection of holds when `can_hold` is false or game is over.
- [ ] **Terminal Transitions Verification Tests:**
  - Verify that row-zero locking triggers immediate game-over and does NOT consume the `next_piece` preview.
  - Verify that obstructed normal spawn and obstructed Hold spawn set status to `"game_over"` and clear `active_piece` to `null`.

### Phase 3: Frontend Implementation (src/)
- [ ] **Types Extension (`types.ts`):**
  - Mirror updated `GameState` schema (matching `GameStateModel` from backend).
- [ ] **API Client Expansion (`api.ts`):**
  - Implement `holdGame` calling `POST /api/games/{id}/hold`.
- [ ] **HUD, Hold, and Preview Rendering (`TetrisBoard.tsx`):**
  - Render separate visual layouts for held piece and next piece preview.
  - Render text indicators for score, cumulative cleared lines, level, and gravity interval.
- [ ] **Interactive Integration (C Key & Hold Button in `App.tsx`):**
  - Listen to `C`/`c` keys and "Hold" button clicks, triggering the `holdGame` action.
- [ ] **Concurrency & Timer Synchronization Controls:**
  - [ ] **Monotonic Generation Sequence (`generationId`):** Track and increment on each create/restart.
  - [ ] **FIFO Serialization Queue:** Queue mutating requests to prevent concurrent execution.
  - [ ] **Double-Verification Checks:** Validate `generationId` after transit and after JSON parsing.
  - [ ] **Dynamic Gravity Rescheduling:** Cancel old timer and start a new one when `gravity_interval_ms` changes.
  - [ ] **Tick Coalescing:** Reset/defer gravity timer upon manual inputs or pending API requests.
  - [ ] **StrictMode Cleanup:** Ensure event listeners and timers are cleanly setup/cleaned up. On restart, input listeners are cleanly reloaded.

### Phase 4: Frontend & Build Verification
- [ ] **Frontend Concurrency Verification Tests:**
  - [ ] **Delayed Fetch Resolution:** Trigger a move, restart the game, ensure the delayed move response is discarded and does not overwrite state.
  - [ ] **Delayed JSON Parsing:** Ensure that a restart during the JSON parsing phase of a move or tick does not overwrite state.
  - [ ] **Old-Generation Queue Isolation:** Ensure old queued moves do not execute or affect a newly restarted game.
  - [ ] **Stale finally/error completion:** Ensure stale network failures do not touch active in-flight guards.
  - [ ] **Pending Hold vs Usable Hold:** Trigger a delayed Hold, restart, verify a new Hold works instantly.
  - [ ] **FIFO Manual Mutations:** Trigger Left, Left, Down in rapid succession and assert sequential network dispatch.
  - [ ] **Coalesced Automatic Ticks:** Verify automatic ticks defer/coalesce during manual drops or holds.
  - [ ] **Exact Timeout Cancellation:** Verify `clearTimeout` on manual moves or level changes.
  - [ ] **StrictMode Lifecycle:** Verify setup, cleanup, and re-setup cycles leave keyboard listeners and timers intact.
- [ ] **Linter / Type-checking:** Run `tsc --noEmit` and `npm run lint` from the `frontend/` directory.
- [ ] **Frontend Build:** Run `npm run build` in the `frontend/` directory and ensure zero errors.
- [ ] **Coverage Reports:** Run coverage commands to verify `docs/coverage.xml` and `frontend/coverage/lcov.info` are generated correctly.
- [ ] **NPM Audit Remediation:** Apply and verify dependency updates to fix the 7 baseline vulnerabilities.
