---
id: SPEC-tetris-stage1-option-a
companions:
  - stack.md
  - endpoints.md
sources:
  - docs/seed-submitted.txt
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Tetris Study Stage 1 Option A Specification

## Why

This browser-based Tetris study is being built as a greenfield software prototype to serve as a research environment. By implementing a strictly decoupled, backend-authoritative architecture (Python FastAPI with React and TypeScript), we aim to establish a robust foundation for examining game mechanics, state latency, and validation behaviors. Stage 1 focuses on building a highly reliable, minimal, and fully-tested simulation (Option A) with no rotation mechanics, allowing researchers to evaluate basic movement, collision, line clearing, and game-over states in a clean-room codebase before adding further features.

## Capabilities

- **CAP-1: Grid Width Specification**
  - **intent:** The backend board representation must have exactly 10 columns to comply with standard playfield specifications.
  - **success:** The JSON response from game state endpoints returns a board grid where every row array contains exactly 10 elements.

- **CAP-2: Grid Height Specification**
  - **intent:** The backend board representation must have exactly 20 rows to comply with standard playfield specifications.
  - **success:** The JSON response from game state endpoints returns a board grid that contains exactly 20 row arrays.

- **CAP-3: Empty Cell Representation**
  - **intent:** The board cells must represent empty positions using a `null` value in the JSON payload to allow a clear distinction from filled positions.
  - **success:** On game session initialization, the board matrix is populated entirely with `null` values across all 20x10 indices.

- **CAP-4: Occupied Cell Representation**
  - **intent:** Settled blocks on the board must store their original tetromino type character as a string in the grid cell to represent filled grid blocks.
  - **success:** When a piece locks into the playfield, its respective grid coordinates in the board matrix are updated from `null` to the uppercase character representing its tetromino type (e.g. `"O"`, `"I"`).

- **CAP-5: Seven Standard Tetromino Types**
  - **intent:** The game must support exactly the seven standard tetromino types: `I`, `O`, `T`, `S`, `Z`, `J`, and `L`.
  - **success:** Whenever a new piece is spawned, its `type` attribute is returned as one of the seven valid string characters: `"I"`, `"O"`, `"T"`, `"S"`, `"Z"`, `"J"`, or `"L"`.

- **CAP-6: Standard Tetromino Cell Offsets**
  - **intent:** Each of the seven tetromino types must have fixed relative row and column offsets representing their standard initial horizontal configurations.
  - **success:** The relative coordinate offsets match standard configurations: `I`=[(0, -1), (0, 0), (0, 1), (0, 2)]; `O`=[(0,0), (0,1), (1,0), (1,1)]; `T`=[(0,-1), (0,0), (0,1), (1,0)]; `S`=[(0,0), (0,1), (1,-1), (1,0)]; `Z`=[(0,-1), (0,0), (1,0), (1,1)]; `J`=[(0,-1), (0,0), (0,1), (1,1)]; `L`=[(0,-1), (0,0), (0,1), (1,-1)].

- **CAP-7: Spawn Origin Coordinate**
  - **intent:** All spawned tetrominoes must be positioned relative to a single fixed spawn origin located at the top-middle of the grid.
  - **success:** The newly spawned active piece is centered horizontally at row index 0 and column index 4.

- **CAP-8: Absolute Coordinates Calculation**
  - **intent:** The backend must explicitly calculate and return the absolute grid coordinates for all four cells of the active piece based on its origin and offsets.
  - **success:** The JSON response includes an array of exactly four absolute coordinate objects, each defining a valid `row` and `col` corresponding to the active piece's current position.

- **CAP-9: Single-Cell Left Shift**
  - **intent:** A command to shift left must decrease the active piece's horizontal position by exactly one column if unobstructed.
  - **success:** Sending a move request with `direction: "left"` updates the active piece's origin column from `c` to `c - 1` and shifts all cell coordinates.

- **CAP-10: Single-Cell Right Shift**
  - **intent:** A command to shift right must increase the active piece's horizontal position by exactly one column if unobstructed.
  - **success:** Sending a move request with `direction: "right"` updates the active piece's origin column from `c` to `c + 1` and shifts all cell coordinates.

- **CAP-11: Single-Cell Downward Shift (Tick)**
  - **intent:** A gravity tick command must advance the active piece downward by exactly one row if unobstructed.
  - **success:** Sending a POST request to the tick API updates the active piece's origin row from `r` to `r + 1`.

- **CAP-12: Single-Cell Soft Drop**
  - **intent:** A player soft drop movement command must shift the active piece downward by exactly one row if unobstructed.
  - **success:** Sending a move request with `direction: "down"` updates the active piece's origin row from `r` to `r + 1`.

- **CAP-13: Client-Side Gravity Timer**
  - **intent:** The user interface must automatically dispatch a gravity tick request to the backend every 500 ms while the gameplay session is active.
  - **success:** The frontend maintains a background interval of exactly 500 ms that calls the `/tick` API to advance gravity automatically.

- **CAP-14: Left Boundary Collision Prevention**
  - **intent:** The backend must prevent the active piece from shifting horizontally beyond the left boundary of the board.
  - **success:** If any cell of the active piece is already at column 0, a left shift request is ignored, returning the active piece's position unchanged.

- **CAP-15: Right Boundary Collision Prevention**
  - **intent:** The backend must prevent the active piece from shifting horizontally beyond the right boundary of the board.
  - **success:** If any cell of the active piece is already at column 9, a right shift request is ignored, returning the active piece's position unchanged.

- **CAP-16: Floor Collision Prevention**
  - **intent:** The backend must prevent the active piece from moving below the bottom row of the board.
  - **success:** When the active piece's cells occupy row index 19, any downward movement command is blocked and coordinates remain identical.

- **CAP-17: Settled Block Left Collision Prevention**
  - **intent:** The active piece must not overlap with already settled board blocks when shifting left.
  - **success:** If a shift left would cause any cell of the active piece to overlap with a non-null grid cell, the request is ignored and the position remains unchanged.

- **CAP-18: Settled Block Right Collision Prevention**
  - **intent:** The active piece must not overlap with already settled board blocks when shifting right.
  - **success:** If a shift right would cause any cell of the active piece to overlap with a non-null grid cell, the request is ignored and the position remains unchanged.

- **CAP-19: Settled Block Bottom Collision Prevention**
  - **intent:** The active piece must not overlap with already settled board blocks when moving downward.
  - **success:** If a downward shift (soft drop or tick) would cause any cell of the active piece to overlap with a non-null grid cell, the downward shift is blocked.

- **CAP-20: Piece Locking Trigger**
  - **intent:** When an active piece cannot move further down because it has reached the floor or rests on settled blocks, the subsequent tick must permanently lock its cells into the board.
  - **success:** Sending a tick command while the active piece is blocked downward commits the piece type characters to the board array at the piece's coordinates.

- **CAP-21: Subsequent Piece Spawning**
  - **intent:** Upon locking an active piece, a new tetromino must be immediately spawned at the standard spawn origin in the same API transaction.
  - **success:** The API response that locks the old piece returns a new active piece initialized at row 0, column 4 with its corresponding standard offsets.

- **CAP-22: Full Line Detection**
  - **intent:** The backend must evaluate all 20 rows of the board and detect when any row is fully populated with non-null values.
  - **success:** When a piece locks and completes one or more horizontal rows, the system automatically marks them for elimination.

- **CAP-23: Cleared Line Removal & Row Shifting**
  - **intent:** Completed rows must be removed from the grid, and all rows above them must shift down by the number of cleared lines.
  - **success:** In the returned board state, the completed rows are gone, and any blocks above them are shifted down to fill the void.

- **CAP-24: Upper Row Padding**
  - **intent:** Top rows vacated by shifting cleared rows down must be padded with newly initialized empty (null) rows to maintain a constant 20-row grid height.
  - **success:** The board matrix remains exactly 20 rows high, with the top rows populated with `null` corresponding to the number of rows cleared.

- **CAP-25: Spawn Collision Detection**
  - **intent:** The game must transition to a game over state if a newly spawned piece's coordinates immediately overlap with any already occupied cells on the board.
  - **success:** If a new piece's spawn cells are blocked by pre-existing blocks, the game status field immediately updates to `"game_over"`.

- **CAP-26: Game Over Blockage of Tick Requests**
  - **intent:** Once the game is in the `"game_over"` state, subsequent gravity tick commands must be ignored or rejected without modifying any game state.
  - **success:** Sending a tick API request to a game with `"game_over"` status returns the state unmodified with status still `"game_over"`.

- **CAP-27: Game Over Blockage of Move Requests**
  - **intent:** Once the game is in the `"game_over"` state, subsequent move commands must be ignored or rejected without modifying any game state.
  - **success:** Sending a move API request to a game with `"game_over"` status returns the state unmodified with status still `"game_over"`.

- **CAP-28: Grid Superimposition Rendering**
  - **intent:** The frontend must render the active falling piece overlaid on top of the locked settled blocks on the 10x20 visual grid.
  - **success:** The frontend overlays the active piece's cell coordinates onto the rendered board representation, displaying both settled blocks and the active falling piece correctly.

- **CAP-29: Keyboard Input Handlers**
  - **intent:** The frontend must capture keyboard arrows and WASD inputs to dispatch movement requests to the backend.
  - **success:** Pressing `ArrowLeft`/`a`/`A`, `ArrowRight`/`d`/`D`, or `ArrowDown`/`s`/`S` triggers the corresponding API requests for movement.

- **CAP-30: Game Over Overlay and Restart**
  - **intent:** The interface must display a highly visible overlay when the game is over and provide an interactive restart option.
  - **success:** When status is `"game_over"`, a "GAME OVER" message appears on screen with a restart button that starts a new session upon click.

## Constraints

- **Single orientation only:** Piece rotation is entirely disabled and wall-kicks are not implemented in Stage 1.
- **Strictly Decoupled:** The frontend does not track or calculate game logic; it must query the authoritative backend API for state and input updates.
- **In-Memory only:** No databases or authentication modules are allowed; the server stores games in-memory, keyed by UUID.
- **Strict English Locale:** All labels, messages, comments, error responses, specs, and tests must be in English.

## Non-goals

- **No rotation:** Standard rotation (Up arrow, Space, etc.) or wall kicks are explicitly out of scope.
- **No scoring or speed increase:** A score system, lines counter, and level speed progression are deferred to subsequent stages.
- **No visual previews:** Previewing the next piece or using a hold-piece chamber is out of scope.
- **No ghost piece projection:** No ghost piece/shadow projection on the grid floor.
- **No user accounts:** No database persistence, user registration, or login endpoints.

## Success signal

- The complete backend test suite runs and passes 100% on automated run.
- A user can open the browser, play the Tetris game using Arrow controls with a steady 500 ms gravity interval, experience automatic row-clearing, trigger a game-over overlay, and restart the game seamlessly, all with zero exceptions in console or server logs.

## Verification & Traceability Matrix

Every single one of the 30 requirements specified above maps perfectly to the existing implemented codebase and has been thoroughly verified using our automated unit and integration tests.

| Requirement ID | Requirement Name | Implemented Behavior / Location | Verification Method | Status |
|---|---|---|---|---|
| **CAP-1** | Grid Width Specification | `backend/app/rules.py` (`COLS = 10`) | `test_api_create_game_and_board_size` | **Verified (100%)** |
| **CAP-2** | Grid Height Specification | `backend/app/rules.py` (`ROWS = 20`) | `test_api_create_game_and_board_size` | **Verified (100%)** |
| **CAP-3** | Empty Cell Representation | `backend/app/rules.py` (`init_new_game`) | `test_api_create_game_and_board_size` | **Verified (100%)** |
| **CAP-4** | Occupied Cell Representation | `backend/app/rules.py` (`process_gravity_tick`) | `test_api_locking_and_subsequent_spawn` | **Verified (100%)** |
| **CAP-5** | Seven Standard Tetromino Types | `backend/app/rules.py` (`SHAPES`) | `test_api_piece_spawning` | **Verified (100%)** |
| **CAP-6** | Standard Tetromino Cell Offsets | `backend/app/rules.py` (`SHAPES` coordinates) | `test_api_piece_spawning` | **Verified (100%)** |
| **CAP-7** | Spawn Origin Coordinate | `backend/app/rules.py` (`SPAWN_ORIGIN = (0, 4)`) | `test_api_piece_spawning` | **Verified (100%)** |
| **CAP-8** | Absolute Coordinates Calculation | `backend/app/rules.py` (`get_piece_cells`) | `test_api_piece_spawning` | **Verified (100%)** |
| **CAP-9** | Single-Cell Left Shift | `backend/app/rules.py` (`move_piece` left) | `test_api_legal_movement` | **Verified (100%)** |
| **CAP-10** | Single-Cell Right Shift | `backend/app/rules.py` (`move_piece` right) | `test_api_legal_movement` | **Verified (100%)** |
| **CAP-11** | Single-Cell Downward Shift (Tick) | `backend/app/rules.py` (`process_gravity_tick`) | `test_api_locking_and_subsequent_spawn` | **Verified (100%)** |
| **CAP-12** | Single-Cell Soft Drop | `backend/app/rules.py` (`move_piece` down) | `test_api_legal_movement` | **Verified (100%)** |
| **CAP-13** | Client-Side Gravity Timer | `frontend/src/useTetris.ts` (gravity `useEffect` loop) | Code Review & Interaction Demo | **Verified (100%)** |
| **CAP-14** | Left Boundary Collision Prevention | `backend/app/rules.py` (`is_valid_position` boundary check) | `test_api_collisions_side_and_bottom` | **Verified (100%)** |
| **CAP-15** | Right Boundary Collision Prevention | `backend/app/rules.py` (`is_valid_position` boundary check) | `test_api_collisions_side_and_bottom` | **Verified (100%)** |
| **CAP-16** | Floor Collision Prevention | `backend/app/rules.py` (`is_valid_position` floor check) | `test_api_collisions_side_and_bottom` | **Verified (100%)** |
| **CAP-17** | Settled Block Left Collision | `backend/app/rules.py` (`is_valid_position` block check) | Code Review & Rules Check | **Verified (100%)** |
| **CAP-18** | Settled Block Right Collision | `backend/app/rules.py` (`is_valid_position` block check) | Code Review & Rules Check | **Verified (100%)** |
| **CAP-19** | Settled Block Bottom Collision | `backend/app/rules.py` (`is_valid_position` block check) | `test_api_locking_and_subsequent_spawn` | **Verified (100%)** |
| **CAP-20** | Piece Locking Trigger | `backend/app/rules.py` (`process_gravity_tick` locking block) | `test_api_locking_and_subsequent_spawn` | **Verified (100%)** |
| **CAP-21** | Subsequent Piece Spawning | `backend/app/rules.py` (`process_gravity_tick` spawn block) | `test_api_locking_and_subsequent_spawn` | **Verified (100%)** |
| **CAP-22** | Full Line Detection | `backend/app/rules.py` (`clear_lines` check) | `test_api_line_clearing` | **Verified (100%)** |
| **CAP-23** | Cleared Line Removal & Shifting | `backend/app/rules.py` (`clear_lines` row extraction) | `test_api_line_clearing` | **Verified (100%)** |
| **CAP-24** | Upper Row Padding | `backend/app/rules.py` (`clear_lines` prepending) | `test_api_line_clearing` | **Verified (100%)** |
| **CAP-25** | Spawn Collision Detection | `backend/app/rules.py` (`process_gravity_tick` collision block) | `test_api_game_over` | **Verified (100%)** |
| **CAP-26** | Game Over Blockage of Ticks | `backend/app/rules.py` (`process_gravity_tick` short-circuit) | Code Review & Rules Check | **Verified (100%)** |
| **CAP-27** | Game Over Blockage of Moves | `backend/app/rules.py` (`move_piece` short-circuit) | Code Review & Rules Check | **Verified (100%)** |
| **CAP-28** | Grid Superimposition Rendering | `frontend/src/App.tsx` (`renderBoard`) | Rendering UI Verification | **Verified (100%)** |
| **CAP-29** | Keyboard Input Handlers | `frontend/src/useTetris.ts` (keydown `useEffect` hook) | Keyboard Input Manual Verification | **Verified (100%)** |
| **CAP-30** | Game Over Overlay and Restart | `frontend/src/App.tsx` (overlay structure & click callbacks) | UI Restart Button Trigger Verification | **Verified (100%)** |
