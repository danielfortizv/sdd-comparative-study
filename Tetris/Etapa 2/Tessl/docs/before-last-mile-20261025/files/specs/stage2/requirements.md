# Requirements Specification: Browser-Based Tetris Study - Stage 2, Option A

This document contains the authoritative, atomic, and testable requirements for Stage 2, Option A of the browser-based Tetris study, extending Stage 1 Option A.

---

## 1. Atomic Requirements (Req-S2-1 to Req-S2-30)

### Group S2-A: Stage 2 State Expansion
- **Req-S2-1:** The backend game state representation MUST expand to include the following fields:
  - `score` (integer, starts at 0)
  - `total_lines` (integer, cumulative cleared-line count, starts at 0)
  - `level` (integer, starts at 1)
  - `gravity_interval_ms` (integer, starts at 500)
  - `next_piece` (string/TetrominoType, representing the previewed next piece)
  - `hold_piece` (string/TetrominoType or `null`, representing the held piece, starts as `null`)
  - `can_hold` (boolean, indicates if Hold can be performed, starts as `true`)
- **Req-S2-2:** The state schema returned by all game endpoints (`POST /api/games`, `GET /api/games/{id}`, `POST /api/games/{id}/tick`, `POST /api/games/{id}/move`, and `POST /api/games/{id}/hold`) MUST conform to this extended structure:
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
- **Req-S2-3:** At game creation (`POST /api/games`) or game restart, the game MUST spawn an initial `active_piece` at origin `(0, 3)` using a randomly selected Tetromino type, and independently generate a random Tetromino type for `next_piece`.
- **Req-S2-4:** Peeking at game state via `GET /api/games/{id}` MUST be read-only and MUST NOT consume, alter, or advance `next_piece`, nor mutate any other part of the state.
- **Req-S2-5:** When a piece locks into the board (and does not trigger an immediate game over via row-zero locking):
  - A normal spawn of a new piece MUST be performed.
  - The new `active_piece` MUST be created at origin `(0, 3)` using the current `next_piece` type.
  - A new random Tetromino type MUST be generated and assigned to `next_piece` to replace the consumed preview.
  - `can_hold` MUST be reset to `true`.
- **Req-S2-6:** If a normal spawn is attempted (Req-S2-5) but the newly spawned piece is obstructed at origin `(0, 3)` (meaning its initial absolute coordinates are illegal due to overlap with settled board blocks), the game status MUST transition from `"playing"` to `"game_over"`, and `active_piece` MUST be set to `null`. This spawn attempt consumes the previewed `next_piece` and generates exactly one new `next_piece` before transitioning to `"game_over"`.

### Group S2-C: Hold Piece Mechanism
- **Req-S2-7:** The API MUST expose a new endpoint `POST /api/games/{id}/hold` which allows the user to hold the current piece once per active piece life.
- **Req-S2-8:** If `can_hold` is `false` (meaning a Hold was already performed for the current active piece life) or if the game status is `"game_over"`, any hold request MUST be rejected, returning the current game state unchanged without any mutations.
- **Req-S2-9 (First Hold):** If `can_hold` is `true` and `hold_piece` is `null`:
  - The current `active_piece.type` MUST be saved into `hold_piece`.
  - The `active_piece` MUST be replaced by spawning a new piece at origin `(0, 3)` in its initial orientation using the current `next_piece` type.
  - A new random Tetromino type MUST be generated and assigned to `next_piece` (consuming the preview and generating exactly one new preview).
  - `can_hold` MUST be set to `false`.
- **Req-S2-10 (Subsequent Swap Hold):** If `can_hold` is `true` and `hold_piece` is NOT `null`:
  - The current `active_piece.type` and the current `hold_piece` type MUST be swapped.
  - The `active_piece` MUST be replaced by spawning a new piece at origin `(0, 3)` in its initial orientation using the previous `hold_piece` type.
  - The current `next_piece` MUST remain unchanged (it is NOT consumed, and no new preview is generated).
  - `can_hold` MUST be set to `false`.
- **Req-S2-11 (Obstructed Hold):** When a Hold is triggered (either first or swap), if spawning the new piece at origin `(0, 3)` is obstructed (meaning its absolute coordinates overlap with any settled blocks on the board), the game status MUST transition from `"playing"` to `"game_over"`, and `active_piece` MUST be set to `null`.
- **Req-S2-12 (No Hold on Game Over / Restart):** Restart resets `hold_piece` to `null` and `can_hold` to `true`.

### Group S2-D: Scoring, Leveling, and Progressive Gravity
- **Req-S2-13:** Scoring MUST be evaluated immediately after an active piece locks and lines (if any) are cleared.
- **Req-S2-14:** For a lock that clears $N$ rows simultaneously (where $N \in \{1, 2, 3, 4\}$), the score awarded immediately MUST be calculated as follows, multiplied by the level $L_{\text{prev}}$ *immediately before* that lock:
  - For $N = 1$ row cleared: $+100 \times L_{\text{prev}}$ points.
  - For $N = 2$ rows cleared: $+300 \times L_{\text{prev}}$ points.
  - For $N = 3$ rows cleared: $+500 \times L_{\text{prev}}$ points.
  - For $N = 4$ rows cleared: $+800 \times L_{\text{prev}}$ points.
- **Req-S2-15:** A lock that clears no rows ($N=0$) MUST award $0$ points.
- **Req-S2-16:** Soft dropping (moving down manually via `POST /api/games/{id}/move` with direction `"down"`) MUST NOT grant any additional points.
- **Req-S2-17 (Level Formula):** After adding the newly cleared rows $N$ to the cumulative line count `total_lines`, the new level $L$ MUST be computed as:
  $$L = 1 + \lfloor \frac{\text{total\_lines}}{10} \rfloor$$
- **Req-S2-18 (Progressive Gravity Formula):** The gravity interval `gravity_interval_ms` MUST be updated based on the new level $L$ using the formula:
  $$\text{gravity\_interval\_ms} = \max(100, 500 - 50 \times (L - 1))$$

### Group S2-E: Terminal Transition Rules (Game Over & Preview Interaction)
- **Req-S2-19 (Row-Zero Locking):** The row-zero locking rule (legacy Req26) is retained: if a gravity tick is executed and the active piece is already locked at row 0 (any of its cells lie in row 0) and cannot move down, the game status MUST transition to `"game_over"`.
- **Req-S2-20 (No Preview Consumption on Row-Zero Locking):** When row-zero locking triggers (Req-S2-19), the game ends immediately without attempting a normal spawn. Therefore, the previewed `next_piece` MUST NOT be consumed, and no new `next_piece` draw/invention occurs.

### Group S2-F: Isolated-Domain Testing Fixtures for 3 & 4 Line Clears
- **Req-S2-21:** Since the seven unrotated canonical Tetromino shapes (unrotated, as rotation is forbidden) have a maximum vertical height of at most 2 rows, it is mathematically impossible to clear 3 or 4 rows simultaneously during normal UI-based play.
- **Req-S2-22:** To verify the scoring logic for 3 and 4 row clears, the backend test suite MUST implement and run **explicitly labeled isolated-domain fixtures**. These fixtures will programmatically pre-populate a game board with custom settled blocks, leaving custom vertical gaps, and place a custom active piece to trigger 3 and 4 line clears upon locking.
- **Req-S2-23:** The application code and documentation MUST NOT claim that ordinary UI gameplay can clear 3 or 4 rows, nor provide any UI-level controls or mechanisms (such as rotation) to enable 3 or 4 row clears during standard gameplay.

### Group S2-G: Frontend Concurrency, Timer, and State Integrity
- **Req-S2-24 (Request-Generation Ownership):** The client-side application MUST assign a monotonic integer sequence / generation ID to each sent API request (ticks, moves, holds, and restarts) to establish request ownership.
- **Req-S2-25 (Deferred Response-Body Checks):** The frontend MUST implement deferred response-body checks. Upon receiving an API response, the frontend MUST compare its associated request-generation ID with the latest active generation ID. If the response corresponds to a stale (earlier) generation, it MUST be discarded, and must not update the visible game state, preventing state reversal.
- **Req-S2-26 (Per-Generation Mutation Ordering):** Client-side state updates MUST strictly follow the monotonic request-generation order, ensuring that mutations are applied in the exact sequence they were requested.
- **Req-S2-27 (Coalesced Automatic Ticks):** Automatic gravity ticks MUST be coalesced with user-triggered movements. When a manual action (such as soft drop, shift, or hold) is successfully performed, or when an API call is actively in-flight, the client-side tick scheduler MUST delay or reset the automatic gravity tick timer to prevent rapid double-ticks or premature gravity descent.
- **Req-S2-28 (Dynamic Interval Cancellation):** The client-side gravity timer MUST dynamically adapt to the `gravity_interval_ms` returned in the backend state. Whenever the `gravity_interval_ms` value changes (due to a level-up), the active timer/interval MUST be cancelled immediately, and a new gravity timer scheduled using the updated `gravity_interval_ms`.
- **Req-S2-29 (Game-Over & Restart Cleanup / Disposal):** Upon transitioning to `"game_over"` or triggering a restart / unmounting the component, the client-side game engine MUST immediately cancel and clear all active gravity timers/intervals, remove all keyboard listeners, and properly dispose of resources.
- **Req-S2-30 (Hold Controls Integration):** The frontend UI MUST:
  - Render a visual "Hold" container showing the `hold_piece` type (with its representative color/blocks, or empty if `null`), and a label showing whether hold is currently available (`can_hold`).
  - Render a visual "Next Preview" container showing the `next_piece` type.
  - Provide a visual "Hold" button in the control panel.
  - Listen for the C key (`KeyboardEvent.key === 'c' || KeyboardEvent.key === 'C'`) and dispatch a `POST /api/games/{id}/hold` request when pressed.
  - Bind keyboard inputs and buttons under the same request-generation ownership and throttling controls (Req-S2-24, Req-S2-27) as existing movement commands.

---

## 2. Acceptance Criteria

| ID | Description | Acceptance Criteria |
| --- | --- | --- |
| **AC-S2-1** | Stage 2 State Structure | `POST /api/games` returns HTTP 200 with an empty board, a randomly spawned active piece, `score: 0`, `total_lines: 0`, `level: 1`, `gravity_interval_ms: 500`, a valid `next_piece`, `hold_piece: null`, and `can_hold: true`. |
| **AC-S2-2** | Score, Level, and Gravity Scaling | Locking a piece that clears 1 or 2 rows awards `100 * level` or `300 * level` points immediately, updates `total_lines`, recalculates `level`, and reduces `gravity_interval_ms` dynamically. A lock with no line clears awards 0 points. |
| **AC-S2-3** | Isolated-Domain 3 & 4 Line Clears | Explicitly labeled backend test fixtures prepopulating the board can trigger 3 and 4 line clears, awarding respectively `500 * level` and `800 * level` points. |
| **AC-S2-4** | First Hold - Empty Hold Slot | Executing `POST /api/games/{id}/hold` when `hold_piece` is `null` and `can_hold` is `true` saves the current active piece type in `hold_piece`, spawns the `next_piece` at `(0, 3)`, bumps the `next_piece` preview with a new random piece, and sets `can_hold` to `false`. |
| **AC-S2-5** | Swap Hold - Occupied Hold Slot | Executing `POST /api/games/{id}/hold` when `hold_piece` is occupied and `can_hold` is `true` swaps the current active piece with `hold_piece`, spawns the previous held piece at `(0, 3)`, leaves `next_piece` unchanged (no new preview generated), and sets `can_hold` to `false`. |
| **AC-S2-6** | Hold Locking Reset | After a piece locks (whether it clears rows or not), `can_hold` is reset to `true`, allowing Hold to be used again. |
| **AC-S2-7** | Hold Rejection & Movement Limits | Calling Hold when `can_hold` is `false`, or after the game is in `game_over` state, is rejected and does not mutate any state. |
| **AC-S2-8** | Terminal Transitions - No Preview Consumption | If a gravity tick results in row-zero locking (game over), the game state transitions to `"game_over"`, and the `next_piece` is NOT consumed (remains identical to before the tick). |
| **AC-S2-9** | Obstructed Spawn and Hold Game Over | If an obstructed normal spawn or an obstructed Hold spawn is triggered at origin `(0, 3)`, the game state transitions to `"game_over"` and `active_piece` is set to `null`. |
| **AC-S2-10** | Client-Side Timer and Concurrency Controls | The frontend clears and reschedules gravity ticks dynamically when `gravity_interval_ms` changes, throttles and drops responses that are out-of-order (older request-generation IDs), coalesces automatic gravity ticks with manual drops/holds, and disposes of all timers and key listeners on game over, restart, or component unmount. |

---

## 3. Run and Test Commands

### Backend:
- **Run:** `fastapi dev app/main.py --port 8000`
- **Test:** `pytest -v`

### Frontend:
- **Build/Lint/Run:**
  - Build: `npm run build`
  - Lint/Type-check: `npm run lint` or `tsc --noEmit`
  - Run dev server: `npm run dev`
