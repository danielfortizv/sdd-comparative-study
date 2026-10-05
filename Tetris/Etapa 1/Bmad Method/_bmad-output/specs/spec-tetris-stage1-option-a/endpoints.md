# HTTP API Specification Companion

This companion defines the JSON schemas, endpoint definitions, and behavior contracts for communication between the React frontend and the Python FastAPI backend.

---

## 1. Game State Schema

The central response structure is a JSON representation of the `GameState`. Every endpoint returned state must adhere strictly to this schema to prevent rendering discrepancies.

### Schema Fields:
- `game_id` (string/UUID): Unique session identifier.
- `board` (array of arrays): A 20x10 matrix (rows x columns).
  - Each element is either `null` (representing an empty cell) or a string (e.g. `"I"`, `"O"`, `"T"`, `"S"`, `"Z"`, `"J"`, `"L"`) indicating a locked cell of that tetromino type.
- `active_piece` (object or `null`): The currently falling tetromino. If `null`, no piece is currently active (e.g., game over).
  - `type` (string): Standard tetromino type (`"I"`, `"O"`, `"T"`, `"S"`, `"Z"`, `"J"`, `"L"`).
  - `origin` (object): Position coordinate of the piece's anchor point on the board.
    - `row` (integer): Row position (0 to 19).
    - `col` (integer): Column position (0 to 9).
  - `cells` (array of objects): Absolute coordinates of the active piece's 4 cells on the grid.
    - Each cell is `{ "row": integer, "col": integer }`.
- `status` (string): Current gameplay status. Must be exactly `"playing"` or `"game_over"`.

### Example JSON State:
```json
{
  "game_id": "c1f7a0be-14bd-4eb5-8e7c-d6b9d6281be3",
  "board": [
    [null, null, null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null, null, null],
    ...
    [null, null, null, null, null, null, null, null, null, null],
    ["I", "I", "I", "I", null, null, null, null, null, null]
  ],
  "active_piece": {
    "type": "T",
    "origin": { "row": 2, "col": 4 },
    "cells": [
      { "row": 1, "col": 4 },
      { "row": 2, "col": 3 },
      { "row": 2, "col": 4 },
      { "row": 2, "col": 5 }
    ]
  },
  "status": "playing"
}
```

---

## 2. API Endpoints

### 2.1. Create/Restart Game
- **Method:** `POST`
- **Path:** `/api/games`
- **Description:** Instantiates a new game session with a clean 20x10 board, spawns the first tetromino, stores it in memory, and returns the newly generated state.
- **Request Body:** None
- **Response:** `200 OK` (Game State JSON)

### 2.2. Get Game State
- **Method:** `GET`
- **Path:** `/api/games/{id}`
- **Description:** Fetches the current live in-memory state of the session.
- **Request Body:** None
- **Response:** `200 OK` (Game State JSON) or `404 Not Found` (if ID does not exist).

### 2.3. Gravity Tick
- **Method:** `POST`
- **Path:** `/api/games/{id}/tick`
- **Description:** Advances the game clock by one gravity tick. This is the central ticker handler.
  - **Rule 1:** If the active piece can descend legally, it moves down 1 unit.
  - **Rule 2:** If it cannot descend further, it locks. Completed lines are cleared, and a new tetromino spawns.
  - **Rule 3:** If the new tetromino immediately collides with existing settled cells, the status becomes `"game_over"`.
- **Request Body:** None
- **Response:** `200 OK` (Game State JSON) or `404 Not Found`.

### 2.4. Move Active Piece
- **Method:** `POST`
- **Path:** `/api/games/{id}/move`
- **Description:** Shifts the active piece 1 unit in the specified direction if the move is legal. If illegal, the movement request is silently ignored and the current state is returned unchanged.
- **Request Body:**
  ```json
  {
    "direction": "left" | "right" | "down"
  }
  ```
- **Response:** `200 OK` (Game State JSON) or `404 Not Found`.
- **Notes:**
  - `direction: "down"` performs a soft drop, moving the piece down 1 unit. It does not perform locking instantly unless followed by a tick or another down move when already at bottom.
