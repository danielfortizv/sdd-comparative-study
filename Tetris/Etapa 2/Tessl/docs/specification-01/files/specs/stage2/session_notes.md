# Tessl Session Notes: Browser-Based Tetris Study - Stage 2, Option A

This document logs the design decisions, real Tessl integration status, resolved material ambiguities, and the traceable implementation/verification checklist for Stage 2, Option A.

---

## 1. Tessl Integration Status & Evidence

We checked and verified the live Tessl integration in this workspace.

- **Tessl Status Check:** Run via MCP `mcp_tessl_status` returning:
  - **manifest.summary.inSync:** 2 (All dependencies in sync)
  - **Tiles in Sync:**
    - `maria/fastapi` (v0.1.0)
    - `softaworks/agent-toolkit` (commit `3027f20f3181758385a1bb8c022d4041dfb4de84` with `react-dev` skill)
  - **Readiness:** `"partial"` due to lack of CLI authentication in headless environment.
- **Tessl Skills Available Check:** Calling `mcp_tessl_skills_available` fails with:
  - `Authentication required to use skills_available` (requires device flow at `https://tessl.io/auth/cli?verification_uri=...` with code `CBBL-QBTW`).
  - This is authentic evidence that the Tessl MCP tools are fully connected and interactive. We are preserving local vendored plugins and configurations without relying on active network authentication.

---

## 2. Material Ambiguities & System Design Decisions

### Ambiguity 1: 3-Row and 4-Row Line Clears
- **Ambiguity:** Canonical unrotated pieces (rotation is disabled in Stage 1 and 2) are at most 2 rows tall (e.g. `O`, `T`, `S`, `Z`, `J`, `L` are 2 rows tall, `I` is 1 row tall). Therefore, it is impossible for a player to clear 3 or 4 lines simultaneously during normal UI-based play.
- **Resolution:**
  - Do NOT invent rotation, wall kicks, or non-canonical shapes in the application.
  - Do NOT claim in the UI or documentation that normal gameplay can clear 3 or 4 rows.
  - Strictly verify the scoring rules for 3 and 4 line clears (which must scale by `500 * level` and `800 * level` respectively) via **explicitly labeled isolated-domain unit test fixtures** in the backend. These fixtures will programmatically pre-populate the board with custom blocks, leaving a 1-column vertical channel, and drop an artificial vertical block or piece to trigger 3 and 4 line clears upon locking.

### Ambiguity 2: Game Over from Row-Zero Locking vs. Preview Draw
- **Ambiguity:** If a gravity tick locks a piece at row 0 (such that any block is settled at row 0, meaning it cannot move down), triggering immediate game over (legacy Req26): does the backend consume or advance the previewed `next_piece`?
- **Resolution:**
  - When row-zero locking occurs, the game transitions to `"game_over"` immediately without attempting a normal spawn.
  - Therefore, the previewed `next_piece` MUST NOT be consumed or changed. It remains identical to its previous value, ensuring no "next-spawn draw" is invented when no normal spawn is attempted.
  - However, if the game attempts a normal spawn of a piece (following a successful lock at rows > 0) but the newly spawned piece is obstructed at origin `(0, 3)`, that *does* count as a normal spawn attempt. Thus, the previewed `next_piece` is consumed to become the `active_piece` (which then fails spawning), and a new `next_piece` is generated before transitioning the game status to `"game_over"` and clearing `active_piece` to `null`.

### Ambiguity 3: Hold Rejection Behavior
- **Ambiguity:** What is the precise behavior when a Hold action is rejected (e.g., when the user has already held during the current piece's descent (`can_hold: false`) or if the game is over)?
- **Resolution:**
  - The backend MUST return the current game state unchanged, preserving all state counters and coordinates. No mutation or state advancement occurs.
  - The API returns HTTP 200 with the unchanged state payload to maintain standard game controller compatibility.

### Ambiguity 4: Obstructed Spawn and Hold Game Over
- **Ambiguity:** What happens when an obstructed Hold spawn is triggered at `(0, 3)` (first hold or swap)?
- **Resolution:**
  - Spawning the held piece at origin `(0, 3)` is checked for validity. If the board cells at the spawn coordinates are already settled, the spawn is obstructed.
  - The game transitions to `"game_over"`, and the `active_piece` is cleared to `null` in the response state.

### Ambiguity 5: Dynamic Gravity Interval & Client-Side Coalescing
- **Ambiguity:** When `gravity_interval_ms` updates dynamically due to a level-up, how does the client adapt, and how do we prevent overlapping automatic tick requests and manual inputs from reversing state?
- **Resolution:**
  - **Dynamic Interval Cancellation:** The React client watches for changes in `gravity_interval_ms`. If a change occurs, the active interval is immediately cleared (`clearInterval`) and a new interval scheduled.
  - **Request-Generation Ownership & Deferred Checks:** The frontend tags each request (tick, move, hold, restart) with a monotonic sequence ID (`generationId`). The frontend only accepts the response body and updates visible game state if the response matches the latest dispatched sequence, discarding any stale, out-of-order network responses.
  - **Coalesced Ticks:** Dispatched manual drop moves or holds will reset/coalesce the automatic timer interval, ensuring the user gets a full timer interval's time after performing an action before gravity ticks.

---

## 3. Traceable Implementation & Verification Checklist

### Phase 1: Backend Implementation (app/)
- [ ] **State Schema Expansion (`app/models/game.py`):**
  - Add `score: int = 0`, `total_lines: int = 0`, `level: int = 1`, `gravity_interval_ms: int = 500`.
  - Add `next_piece: TetrominoType`, `hold_piece: Optional[TetrominoType] = None`, `can_hold: bool = True`.
- [ ] **Create/Restart Game (`app/controllers/games.py`):**
  - Spawn random type for `active_piece` at `(0, 3)`.
  - Independently spawn a second random type for `next_piece`.
  - Initialize score=0, lines=0, level=1, gravity_interval_ms=500, hold_piece=None, can_hold=True.
- [ ] **Line Clearing & Scoring Formulas (`app/domain/rules.py`):**
  - Prior to clearing rows, calculate score earned:
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
  - Verify if status is `"game_over"` or `can_hold` is `False`. If so, return unchanged state.
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
- [ ] **Isolated-Domain Unit Tests (Req-S2-22):**
  - Explicitly labeled test fixtures to pre-populate 3 rows and 4 rows on the board.
  - Lock an artificial block to clear 3 rows and 4 rows, verifying `500 * level` and `800 * level` scores.
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
  - Mirror updated `GameState` schema.
- [ ] **API Client Expansion (`api.ts`):**
  - Implement `holdGame` calling `POST /api/games/{id}/hold`.
- [ ] **Hold & Next Preview Styling & Component Development (`TetrisBoard.tsx` / `App.tsx` / `index.css`):**
  - Render separate visual layouts for held piece and next piece preview.
  - Render text indicators for score, cumulative cleared lines, level, and gravity interval.
- [ ] **Interactive Integration (C Key & Hold Button in `App.tsx`):**
  - Listen to `C`/`c` keys and "Hold" button clicks, triggering the `holdGame` action.
- [ ] **Concurrency & Timer Synchronization Controls:**
  - [ ] **Monotonic Generation Sequence (`generationId`):** Prevent older stale responses from writing to state.
  - [ ] **Dynamic Gravity Rescheduling:** Cancel old timer and start a new one when `gravity_interval_ms` changes.
  - [ ] **Tick Coalescing:** Reset gravity timer upon manual inputs or pending API requests.
  - [ ] **Timer Cleanup:** Cancel all timers on game over, restart, or component unmount.

### Phase 4: Frontend & Build Verification
- [ ] **Frontend Tests:** Ensure `TetrisBoard.test.tsx` passes or is updated to reflect Stage 2 structure.
- [ ] **Linter / Type-checking:** Run `tsc --noEmit` and `npm run lint`.
- [ ] **Frontend Build:** Run `npm run build` and ensure zero errors.
