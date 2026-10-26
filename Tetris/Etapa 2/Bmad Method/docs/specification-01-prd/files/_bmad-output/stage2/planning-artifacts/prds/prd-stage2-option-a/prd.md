---
title: "Product Requirements Document: Stage 2 Tetris Study (Option A)"
status: final
created: 2026-10-25T12:00
updated: 2026-10-25T12:00
---

# PRD: Stage 2 Tetris Study (Option A)

## 0. Document Purpose
This Product Requirements Document (PRD) outlines the behavioral, functional, and user-experience requirements for Stage 2 (Option A) of the Tetris Study. This phase represents a brownfield extension of the decoupled Tetris prototype, introducing game progress systems (Score, Cleared Lines, Levels, Progressive Gravity), a Next Piece Queue, and a Hold Piece Slot. 

This document builds directly upon the Stage 1 specifications (`_bmad-output/planning-artifacts/prds/prd-Bmad Method Full-2026-10-05/prd.md`) and the original Product Brief. It maintains Glossary-anchored terminology, stable Functional IDs, and explicit user journeys, ensuring full backward compatibility with the existing 13 regression tests and client-server REST API contracts.

## 1. Vision
The Stage 2 Tetris Study completes the classic Tetris gameplay loop by adding progression, strategy, and difficulty curves, while strictly preserving the decoupled client-server architecture. Most modern games implement progression on the frontend, leaving them vulnerable to client-side timing drift or manipulation. In contrast, this study keeps the React client purely stateless, rendering progression metrics directly from an authoritative FastAPI backend.

With the introduction of Hold Piece mechanics, Next Piece Previews, and progressive gravity, the prototype demonstrates how a thin client can maintain a highly responsive, real-time feel under dynamic parameters. The backend remains the sole arbitrator of random shape generation, score logic, levels, and tick intervals, while the frontend dynamically schedules gravity intervals from the server's authoritative timer.

## 2. Target User

### 2.1 Jobs To Be Done
- **Progression & Level Testing (Functional):** As a Software Architect, I want to review how progressive level difficulty and gravity changes can be synchronized across client and server without causing state lag or race conditions.
- **Stateful Mechanics Evaluation (Contextual):** As a Study Reviewer, I want to evaluate a brownfield game engine where advanced piece-holding, queuing, and line scoring are validated by backend automated tests.
- **Modern UI Styling Reference (Emotional):** As a Frontend Developer, I want to see a clean, modern sidebar-enabled Tetris interface rendered with React, TypeScript, and Vanilla CSS that updates responsively under StrictMode.

### 2.2 Non-Users (v1)
- **Rotation-seeking Gamer:** A consumer seeking Tetromino rotation or wall-kicks. This remains strictly out of scope for this stage to isolate progress and hold-queue physics.

### 2.3 Key User Journeys

- **UJ-3: Winston swaps active piece with an empty Hold slot**
  - **Persona + context:** Winston, a software architect reviewing state synchronization.
  - **Entry state:** Game is active with status `"playing"`. `hold_piece` is `null`, `can_hold` is `true`. The active piece is `"O"` and the previewed `next_piece` is `"I"`.
  - **Path:**
    1. Winston presses the `C` key or clicks the "Hold" button. The frontend dispatches a `POST /api/games/{id}/hold` request.
    2. The backend intercepts the hold request, stores `"O"` inside the `hold_piece` slot, and updates `can_hold` to `false`.
    3. Because the `hold_piece` slot was empty, the backend consumes the previewed next piece `"I"`, spawns `"I"` as the new `active_piece` at the normal spawn origin `(0,3)` in its initial standard orientation, and randomly generates a new previewed piece (e.g. `"T"`) for `next_piece`.
    4. The backend returns the updated state payload to the frontend.
  - **Climax:** Winston sees the `"O"` shape appear in the Hold panel, `"I"` appear at the top as the new active piece, and `"T"` update in the Next Preview panel. The Hold button becomes visually disabled (`can_hold: false`).
  - **Resolution:** Winston continues playing. Once the active `"I"` piece locks, `can_hold` resets to `true`, and Winston is permitted to swap pieces again.

- **UJ-4: Amelia tests gravity speedup and progressive levels**
  - **Persona + context:** Amelia, a developer validating the difficulty curves.
  - **Entry state:** Amelia is playing at `level` 1 with a total cleared line count of 9. Her current `gravity_interval_ms` is 500ms.
  - **Path:**
    1. Amelia positions an active piece over a single-completed row at the bottom of the grid and lets it lock.
    2. The backend detects 1 cleared line, adding 100 points multiplied by level 1 (100 points) to `score`.
    3. The backend updates the cumulative cleared lines to 10 (`total_lines = 10`).
    4. The backend computes the new level: `level = 1 + floor(10 / 10) = 2`.
    5. The backend computes the new gravity interval: `max(100, 500 - 50 * (2 - 1)) = 450ms` and updates `gravity_interval_ms` in the state.
    6. The backend returns the new state.
  - **Climax:** The React frontend receives the updated state, renders `level: 2`, `score: 100`, `lines: 10`, and immediately clears the existing 500ms timer to schedule the next gravity tick at 450ms.
  - **Resolution:** The game proceeds noticeably faster, and Amelia confirms that gravity speedup is determined authoritatively by backend state.

- **UJ-5: Obstructed Hold Re-entry Game Over**
  - **Persona + context:** Amelia, testing boundary failures.
  - **Entry state:** Amelia is playing. The `hold_piece` slot contains `"J"`. The board is piled up to row 1.
  - **Path:**
    1. Amelia has used her hold earlier in this piece's lifecycle and locked it, so `can_hold` is `true`. She decides to retrieve `"J"` by pressing `C`.
    2. The frontend dispatches `POST /api/games/{id}/hold`.
    3. The backend attempts to swap the current active piece into the Hold slot and spawn the held `"J"` piece at standard spawn origin coordinates `(0,3)`.
    4. However, the standard spawning cells for `"J"` are already occupied by settled blocks.
  - **Climax:** The backend detects the spawn obstruction. It immediately changes `status` to `"game_over"`, disables further movements, and returns the state. The active piece fields are safely returned (with the previous piece now in Hold), but standard spawn coordinates are obstructed. To prevent rendering an illegal overlapping active piece, the frontend checks that status is `"game_over"` and skips active piece rendering.
  - **Resolution:** The screen displays a "Game Over" screen with a "Restart" button. All counters and hold states are reset to 0/null upon restart.

## 3. Glossary
- **Score** — Cumulative numeric points representing player achievement, computed and owned entirely by the backend.
- **Cleared Lines (or Lines)** — Cumulative count of completed rows cleared across all piece locks.
- **Level** — Current difficulty tier, starting at 1, incremented by 1 for every 10 cumulative lines cleared.
- **Gravity Interval (or gravity_interval_ms)** — Duration in milliseconds between automatic gravity ticks, computed from the current Level, floored at 100ms.
- **Hold Slot (or hold_piece)** — Ephemeral storage slot that holds at most one Tetromino shape code, which the player can swap with the active piece.
- **can_hold** — Boolean state variable indicating whether the player is currently permitted to execute a Hold swap. Reset to `true` on piece lock, and set to `false` immediately upon a swap.
- **Next Preview (or next_piece)** — Authoritative queued Tetromino shape code owned by the backend, displayed to the player as the next piece to spawn.
- **Obstructed Spawn** — An intersection condition where standard spawn origin coordinates `(0,3)` (or `(0,4)` for O) are blocked by settled blocks, triggering an immediate game over.

## 4. Features

### 4.1 Progressive Level and Gravity Interval Progression
**Description:** Implements a dynamic, level-based gravity interval on both backend and frontend to progress difficulty as lines are cleared. Realizes UJ-4.

**Functional Requirements:**
- **FR-31: Initial State Counters**
  A fresh game session must start with standard progression parameters: `score` set to 0, cumulative cleared lines `total_lines` set to 0, `level` set to 1, and `gravity_interval_ms` set to 500ms.
  - *Consequence:* These parameters are exposed in all API state JSON responses.
- **FR-32: Level Calculation**
  The current level must be updated immediately after scoring is calculated, using the formula: `level = 1 + floor(total_lines / 10)`.
  - *Consequence:* Clearing lines 0–9 sets Level 1; clearing lines 10–19 sets Level 2; clearing lines 20–29 sets Level 3, and so on.
- **FR-33: Progressive Gravity Interval**
  The gravity interval (in milliseconds) must be calculated on the backend from the current Level using the formula: `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`.
  - *Consequence:* Level 1 runs at 500ms, Level 2 at 450ms, Level 3 at 400ms, and Level 9+ at the 100ms floor.
- **FR-34: Frontend Gravity Scheduling**
  The frontend client must dynamically reschedule its automatic tick timer to run every `gravity_interval_ms` whenever the state's interval value changes.
  - *Consequence:* Standard React `useEffect` loops must clear and recreate intervals based on `game.gravity_interval_ms`, ensuring no timing gaps or double ticks occur.

### 4.2 Multi-Line Scoring Engine
**Description:** Awards points for clearing lines based on the number of completed rows in a single lock and the player's level. Realizes UJ-4.

**Functional Requirements:**
- **FR-35: Cleared Line Scoring Formulas**
  Points must be awarded immediately upon piece locking based on the number of completed rows simultaneously cleared:
  - 1 row cleared: `100 * level`
  - 2 rows cleared: `300 * level`
  - 3 rows cleared: `500 * level`
  - 4 rows cleared: `800 * level`
  - *Consequence:* The multiplier `level` is the level of the game immediately *before* that lock (pre-clear level).
- **FR-36: Non-Clearing Lock Score**
  If a locked piece clears zero rows, no points are awarded (`0` points added to `score`).
- **FR-37: Soft Drop Score Exclusion**
  Manual soft drop inputs (downward movements) must grant no additional points.
  - *Consequence:* Soft drop only advances rows; it does not increment the score.

### 4.3 Hold Slot and Piece Swap
**Description:** Introduces a strategic holding mechanism allowing players to store a Tetromino and swap it with the falling piece. Realizes UJ-3, UJ-5.

**Functional Requirements:**
- **FR-38: Hold Endpoint**
  The backend shall expose a standard endpoint `POST /api/games/{id}/hold` that swaps the current active piece and the piece in the Hold slot.
  - *Consequence:* Returns the fully updated `GameState` payload.
- **FR-39: Hold Cooldown Lock**
  The player can use the Hold action at most once per active piece. `can_hold` must be set to `false` immediately after a swap, and becomes `true` again only after a piece locks into the board.
- **FR-40: Empty Hold Swap (First Hold)**
  If the `hold_piece` slot is empty (`null`) when a Hold is triggered, the backend shall:
  1. Move the current `active_piece.shape` into the `hold_piece` slot.
  2. Consume the queued `next_piece` to spawn a new active piece at standard spawn origin coordinates `(0,3)` in standard orientation.
  3. Generate exactly one new random Tetromino shape and assign it to `next_piece`.
  4. Set `can_hold` to `false`.
- **FR-41: Occupied Hold Swap**
  If the `hold_piece` slot is occupied when a Hold is triggered, the backend shall:
  1. Swap the current `active_piece.shape` and the `hold_piece`.
  2. Spawn the retrieved piece (former hold piece) at standard spawn origin coordinates `(0,3)` in its initial standard orientation.
  3. Put the former active piece shape into the `hold_piece` slot.
  4. Keep the current `next_piece` unchanged (do *not* consume the preview).
  5. Set `can_hold` to `false`.
- **FR-42: Held Piece Standard Spawn Origin and Orientation**
  A retrieved held piece must always spawn centered horizontally at row 0 (coordinates matching the standard spawning template for that shape).
- **FR-43: Obstructed Hold Re-entry**
  If retrieving a held piece results in immediate collision with settled blocks at the spawn coordinates, the game must immediately set status to `"game_over"`.
- **FR-44: Immutable Rejected Holds**
  Hold requests dispatched when `can_hold` is `false`, when status is `"game_over"`, or with an invalid session ID must be rejected without mutating the game state.
  - *Consequence:* Return standard HTTP 400 Bad Request or HTTP 404 Not Found as appropriate, or return the unmodified `GameState`.

### 4.4 Next Piece Preview
**Description:** Maintains an authoritative next piece preview in state, showing the upcoming piece to spawn. Realizes UJ-3.

**Functional Requirements:**
- **FR-45: Next Piece State Representation**
  All game state responses must expose the `next_piece` parameter, containing the canonical shape code of the upcoming Tetromino.
- **FR-46: Next Preview Lifecycle**
  The next piece preview is consumed ONLY on standard piece spawn (post-lock) or during an empty-hold swap. Swapping with an occupied hold piece must NOT consume the next piece preview.
- **FR-47: State Peek Invariance**
  Retrieving the state via `GET /api/games/{id}` must never consume, alter, or cycle the previewed next piece.

### 4.5 Obstructed Spawn Representation
**Description:** Prevents displaying illegal overlapping active pieces when the spawn area is obstructed. Realizes UJ-5.

**Functional Requirements:**
- **FR-48: Clean Game-Over Spawn Transition**
  When a newly spawned piece or a retrieved held piece is obstructed at standard spawn coordinates:
  1. The game status must be set to `"game_over"`.
  2. The backend must return the state representing the final settled board. To prevent rendering an illegal active piece overlapping the settled blocks, the frontend must check `status === "game_over"` and skip rendering the active piece.

---

### Cross-Cutting NFRs
- **NFR-3: Timer Race Condition Prevention**
  The client's gravity scheduler must handle latency or pending keyboard queues gracefully. Concurrent manual move events must not overlap or cause gravity ticks to double-fire.
- **NFR-4: Stale Request Suppression**
  The client must discard out-of-order or obsolete API responses (e.g. from network lag) to prevent reversing the visible game state.

---

## 5. Non-Goals (Explicit)
- **Piece Rotation & SRS:** No piece rotation control (UP arrow, Space) or rotation logic.
- **Ghost Piece Preview:** No ghost piece silhouette at the bottom of the grid.
- **7-Bag Randomizer:** No bag-based randomized shape generator; standard random distribution remains sufficient for production gameplay.
- **Data Persistence:** No database integration, user profiles, authentication, or high-score storage across API restarts.

---

## 6. MVP Scope

### 6.1 In Scope
- Autonomously extend the existing Python FastAPI backend to track `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_piece`, `hold_piece` (nullable), and `can_hold`.
- Expose `POST /api/games/{id}/hold` in backend routing.
- Implement UI sidebar panels in frontend: Score, Lines, Level, Hold Slot (with a modern Hold button), and Next Piece Preview.
- Support Hold triggers via `C` key and Hold button.
- Comprehensive backend tests validating hold swaps, progressive levels, gravity thresholds, scoring multipliers, and obstructed spawn game-overs.

### 6.2 Out of Scope for MVP
- High score local storage or player profile settings.
- Sound effects or graphical particle effects on clears.
- Advanced piece spinning or rotation mechanics.

---

## 7. Success Metrics
- **SM-3 (Scoring Correctness):** 100% of line clears calculate scores exactly using the pre-lock Level multiplier.
- **SM-4 (Hold Loop Integrity):** Swapping with occupied Hold slots maintains the exact shape code, resets orientation to default, and prevents double-hold triggers.
- **SM-C2 (Timer Resiliency):** Rescheduling gravity intervals dynamically does not cause timer jitter or double tick movements on the client.

---

## 8. Open Questions
1. **Should the score be persistent?**
   *Decision:* No, score resides in-memory per game session and is deleted when the session restarts or the FastAPI process terminates.

---

## 9. Assumptions Index
- **[ASSUMPTION-6]**: Spawning a piece (either normal or hold) centers it using the same shape templates and coordinate origins as Stage 1.
- **[ASSUMPTION-7]**: The Level calculation and gravity speedups are calculated on-the-fly inside the line clear locking logic before returning the final state.
