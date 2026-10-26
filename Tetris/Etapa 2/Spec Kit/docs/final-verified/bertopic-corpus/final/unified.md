# Specification Quality Checklist: Extend Tetris to Stage 2

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-20
**Feature**: [specs/002-extend-tetris-stage2/spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable and verifiable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **2026-10-20 Revision**: Revised specification to align with the authoritative study control seed constraints:
  - Ensured every game-state response uses the exact snake_case JSON keys: `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_piece`, `hold_piece`, and `can_hold`.
  - Preserved the existing Stage 1 `activePiece` legacy camelCase key, mapped to the existing tetromino object.
  - Represented `next_piece` and `hold_piece` as single-letter tetromino type strings (`I`, `O`, `T`, `S`, `Z`, `J`, `L`), with `hold_piece` being nullable.
  - Removed all arbitrary and unmeasurable performance criteria (such as 10 ms timer drift, 50 ms endpoint latency, 100 ms UI latency) and replaced them with functional, verifiable success criteria tied to the seed constraints.
  - Retained the exact Stage 1 random piece generation model, without imposing any equal random shape probabilities beyond fresh random generation.
  - Retained the exact scoring and Hold rules as specified by the study control seed.

## Native Quality & SonarQube Baseline Requirements
- [x] **Documented 404 responses**: All endpoints throwing `HTTPException` with status 404 MUST document this status in their Pydantic/FastAPI `responses` parameter (`python:S8415`).
- [x] **Suitable Random Generator**: The python backend MUST use a cryptographically secure random generator or safe random source (e.g. `secrets.choice` or similar) without suppressions (`python:S2245`).
- [x] **Optional Chaining**: Frontend TypeScript files (e.g., `App.tsx`, `useGame.ts`) MUST prefer optional chaining expressions (`?.`) for concise and readable access (`typescript:S6582`).
- [x] **Stable React Keys**: Board cell/row rendering in `Board.tsx` MUST use stable keys instead of array indices to avoid React key code smells (`typescript:S6479`).
- [x] **Readable Contrast**: CSS styling in `index.css` MUST meet minimal contrast requirements for accessibility (`css:S7924`).
- [x] **Audit & Coverage**: Maintain backend XML coverage, frontend LCOV coverage, and execute dependency audits.

All checklist items have passed. No `[NEEDS CLARIFICATION]` markers exist. The specification is fully revised and ready for planning!


# REST API Contract Specification: Extend Tetris to Stage 2

This document defines the REST API contract details exposed by the Python FastAPI backend to the React/TypeScript frontend client for the Stage 2 Tetris features.

---

## Endpoint Overview

All endpoints consume and return `application/json`. Game session states are managed server-side and mapped to a unique UUID.

| Method | Endpoint | Request Body | Response Body | Description |
|--------|----------|--------------|---------------|-------------|
| `POST` | `/api/games` | *None* | `GameSession` | Creates or restarts a game session, initializing all Stage 2 variables to default. |
| `GET` | `/api/games/{id}` | *None* | `GameSession` | Retrieves the current authoritative game state of a session. |
| `POST` | `/api/games/{id}/tick` | *None* | `GameSession` | Advances gravity down by 1 row, checking for locking, line clearing, scoring, leveling, and piece respawn. |
| `POST` | `/api/games/{id}/move` | `MoveRequest` | `GameSession` | Performs a manual left, right, or down shift. |
| `POST` | `/api/games/{id}/hold` | *None* | `GameSession` | Performs a piece swap with the Hold slot (or stores the active piece). |

---

## Detailed Endpoint Definitions

### 1. Create/Restart Game Session
Initializes or resets a game session.

- **URL**: `/api/games`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Success Response (201 Created)**:
  ```json
  {
    "id": "c1f7b764-9844-48f8-b3d2-c2cb72836245",
    "board": [
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0]
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
    "next_piece": "O",
    "hold_piece": null,
    "can_hold": true
  }
  ```

---

### 2. Retrieve Game State
Fetches the current authoritative state of a game.

- **URL**: `/api/games/{id}`
- **Method**: `GET`
- **URL Path Parameters**: `id` (UUID string)
- **Success Response (200 OK)**: Returns the current `GameSession` JSON representation.
- **Error Response (404 Not Found)**:
  ```json
  {
    "detail": "Game session c1f7b764-9844-48f8-b3d2-c2cb72836245 not found"
  }
  ```

---

### 3. Gravity Tick
Advances the active piece downward by one cell, checking for contact, locking, line clears, leveling, and piece spawning.

- **URL**: `/api/games/{id}/tick`
- **Method**: `POST`
- **URL Path Parameters**: `id` (UUID string)
- **Success Response (200 OK)**: Returns the updated `GameSession` JSON.
- **Error Response (404 Not Found)**: Returned if session ID is invalid.

---

### 4. Manual Move Command
Executes horizontal shifting (left/right) or gravity speedup (soft drop down).

- **URL**: `/api/games/{id}/move`
- **Method**: `POST`
- **URL Path Parameters**: `id` (UUID string)
- **Request Body (application/json)**:
  ```json
  {
    "direction": "left"
  }
  ```
- **Success Response (200 OK)**: Returns the updated `GameSession` JSON.
- **Error Response (422 Unprocessable Entity)**:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "direction"],
        "msg": "Input should be 'left', 'right' or 'down'",
        "type": "value_error"
      }
    ]
  }
  ```

---

### 5. Piece Hold Command
Swaps the active piece with the piece in the hold slot, spawning a new piece in its place.

- **URL**: `/api/games/{id}/hold`
- **Method**: `POST`
- **URL Path Parameters**: `id` (UUID string)
- **Success Response (200 OK)**: Returns the updated `GameSession` JSON.
  - *Example response showing active piece stored in Hold slot for the first time*:
    ```json
    {
      "id": "c1f7b764-9844-48f8-b3d2-c2cb72836245",
      "board": [ ... ],
      "activePiece": {
        "type": "O",
        "cells": [[0,4], [0,5], [1,4], [1,5]],
        "origin": [0,4]
      },
      "status": "playing",
      "score": 0,
      "total_lines": 0,
      "level": 1,
      "gravity_interval_ms": 500,
      "next_piece": "T",
      "hold_piece": "I",
      "can_hold": false
    }
    ```
- **Error Response (404 Not Found)**: Returned if session ID is invalid.


# Data Model & State Transitions: Extend Tetris to Stage 2

This document details the updated schemas, validation rules, state-machine transitions, and lifecycle invariants for the Stage 2 single-player Tetris implementation.

---

## Entity Schemas

### 1. GameSession (Game State)
The primary in-memory container that represents the authoritative, server-validated state of a single-player Tetris session.

#### Python Pydantic Model (Backend)
```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class TetrominoSchema(BaseModel):
    type: str = Field(..., description="One of 'I', 'O', 'T', 'S', 'Z', 'J', 'L'")
    cells: List[List[int]] = Field(..., description="Exactly 4 coordinate pairs: [[row, col], ...]")
    origin: List[int] = Field(..., description="Pivot coordinate: [row, col]")

class GameSessionSchema(BaseModel):
    id: str = Field(..., description="Unique UUID string representing the game session")
    board: List[List[int]] = Field(..., description="20x10 grid. 0 = empty cell; 1-7 = settled piece colors")
    active_piece: Optional[TetrominoSchema] = Field(None, alias="activePiece")
    status: str = Field(..., description="Session status: 'playing' or 'game_over'")
    
    # Stage 2 Extended Properties
    score: int = Field(0, description="Cumulative score for the session")
    total_lines: int = Field(0, description="Total number of lines cleared in this session", alias="total_lines")
    level: int = Field(1, description="Current game level, starting at 1")
    gravity_interval_ms: int = Field(500, description="Tick speed interval in milliseconds, ranging from 100 to 500")
    next_piece: str = Field(..., description="The one-letter tetromino type of the next piece queued to spawn")
    hold_piece: Optional[str] = Field(None, description="The one-letter tetromino type currently stored in the Hold slot, or null")
    can_hold: bool = Field(True, description="True if the user can perform a Hold/Swap action; False if already swapped this piece")

    class Config:
        populate_by_name = True
```

#### TypeScript Interfaces (Frontend)
```typescript
export interface Tetromino {
  type: 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';
  cells: [number, number][]; // [row, col] coordinates on the 20x10 board
  origin: [number, number];   // [row, col] rotation/positional pivot
}

export interface GameSession {
  id: string;
  board: number[][]; // 20 rows x 10 columns
  activePiece: Tetromino | null;
  status: 'playing' | 'game_over';
  score: number;
  total_lines: number;
  level: number;
  gravity_interval_ms: number;
  next_piece: 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';
  hold_piece: 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L' | null;
  can_hold: boolean;
}
```

---

## Validation & Boundary Constraints

### 1. Board Structural Validation
- **Row Count**: Must contain exactly $20$ rows.
- **Column Count**: Each row must contain exactly $10$ cells.
- **Cell Range**: Each cell value must be an integer in the range $[0, 7]$ (where `0` is empty, and `1-7` map to colored tetromino blocks).

### 2. Piece Attribute Validation
- **Type**: Must be one of `{"I", "O", "T", "S", "Z", "J", "L"}`.
- **Cells**: An array containing exactly $4$ coordinate pairs `[row, col]`.
- **Coordinates boundaries**: For every cell `[row, col]`, `0 <= row <= 19` and `0 <= col <= 9`.
- **Origin**: A coordinate pair `[row, col]` representing the piece's rotation pivot, bounded within `[0, 19]` (rows) and `[0, 9]` (columns).

### 3. Extended Stage 2 Field Ranges
- **Score**: Integer, must be non-negative ($\ge 0$).
- **Total Lines**: Integer, must be non-negative ($\ge 0$).
- **Level**: Integer, must be $\ge 1$.
- **Gravity Interval**: Integer, bounded between `100` and `500` ms (inclusive).
- **Hold Piece**: Must be `null` or one of the seven valid single-letter tetromino types.

---

## State Transitions & Life-Cycle

The game session transitions through the following actions:

```
                          +------------------------+
                          |   POST /api/games      |
                          +-----------+------------+
                                      |
                                      v
                        +-------------+------------+
                        |  State: "playing"        |
                        |  score = 0, level = 1    |
                        |  active_piece & next_piece |
                        |  hold_piece = null        |
                        +---+---------+--------+---+
                            |         |        |
         POST /api/.../move |         |        | POST /api/.../hold
         (left, right, down)|         |        |
                            v         v        v
                        +-------------+------------+
                        |                          |
                        |   Game Loop / Tick       | <------+
                        |   (POST /api/.../tick)   |        |
                        |                          |        | Normal
                        +---+------------------+---+        | Gravity
                            |                  |            | Tick
                            | Collision on     | No         |
                            | Gravity Tick     | Collision  |
                            v                  v            |
                    +-------+-------+     +----+---+--------+
                    | Lock Piece &  |     | Move   |
                    | Clear Lines   |     | Down   |
                    +-------+-------+     +--------+
                            |
                     Spawn New Piece (from next_piece)
                            |
                 Is Spawning Coordinate Blocked?
                     /                  \
                    /                    \
            Yes    v                      v No
            +------+--------+     +-------+-------+
            | "game_over"   |     | Reset         |
            | activePiece=  |     | can_hold=true |
            | null          |     +---------------+
            +---------------+
```

### 1. Initialization (Create/Restart)
Triggered by `POST /api/games`.
- **Action**: Resets or initializes a session.
- **State Changes**:
  - `board` is filled with $20 \times 10$ zeros (`0`).
  - `score` is set to `0`.
  - `total_lines` is set to `0`.
  - `level` is set to `1`.
  - `gravity_interval_ms` is set to `500`.
  - `hold_piece` is set to `null`.
  - `can_hold` is set to `true`.
  - `status` is set to `"playing"`.
  - `active_piece` spawns at top-center with a randomly generated tetromino type.
  - `next_piece` is populated with a second, randomly generated tetromino type (independent of `active_piece`).

### 2. Manual Move (Left / Right / Down)
Triggered by `POST /api/games/{id}/move` with `direction = "left" | "right" | "down"`.
- **Constraint**: If `status == "game_over"` or `active_piece == null`, ignore the command.
- **Action**:
  - Computes proposed cells:
    - `"left"`: `[r, c - 1]`
    - `"right"`: `[r, c + 1]`
    - `"down"` (Soft drop): `[r + 1, c]`
  - Performs a collision check `has_collision(board, proposed_cells)`.
  - If no collision: Updates `active_piece` cells and origin coordinate.
  - If collision: Keeps current coordinates. **Note**: Manual soft drop down NEVER triggers piece locking or scoring.

### 3. Piece Swapping (Hold)
Triggered by `POST /api/games/{id}/hold`.
- **Constraint**: If `status == "game_over"` or `can_hold == false`, ignore the command and return current state.
- **Action (When Hold slot is Empty - `hold_piece == null`)**:
  - Store current `active_piece.type` in `hold_piece`.
  - Spawn a new `active_piece` at the top-center using the `next_piece` type.
  - Generate a new random tetromino type for `next_piece`.
  - Set `can_hold = false`.
- **Action (When Hold slot is Occupied - `hold_piece != null`)**:
  - Swap current `active_piece.type` with `hold_piece` (the current active piece's type is stored in `hold_piece`, and the previously held piece type is spawned as the new `active_piece` at the top-center in its initial unrotated orientation).
  - Do NOT modify or consume `next_piece`.
  - Set `can_hold = false`.
- **Edge Case**: If the newly spawned piece coordinates from a Hold action overlap with settled blocks at the top-center spawn origin, transition `status` to `"game_over"` and set `active_piece = null`.

### 4. Gravity Tick (Ticking, Locking, Line Clearing & Spawning)
Triggered by `POST /api/games/{id}/tick`.
- **Constraint**: If `status == "game_over"`, ignore and return current state.
- **Action**: Computes proposed cells shifted down by one row: `[r + 1, c]`.
- **Path A (No Collision)**:
  - Updates `active_piece` cells and origin down by one row.
- **Path B (Collision - Lock, Score & Respawn)**:
  - Write active piece colors to the board: `board[r][c] = color_id` (where color_id matches the piece type 1-7).
  - Scan the board for complete horizontal rows (all 10 cells are non-zero) and filter them out.
  - Insert empty rows of `[0] * 10` at row index 0 to replace cleared rows.
  - Let `cleared_count` be the number of rows removed.
  - If `cleared_count > 0`:
    - Add scoring points: `score += multiplier * level` (using the level active *immediately before* clearing):
      - 1 row: `100 * level`
      - 2 rows: `300 * level`
      - 3 rows: `500 * level`
      - 4 rows: `800 * level`
    - Add to total: `total_lines += cleared_count`.
    - Recalculate level: `level = 1 + floor(total_lines / 10)`.
    - Recalculate speed: `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`.
  - Reset `can_hold = true`.
  - Spawn the next piece from the queue: Create a new `active_piece` at top-center using `next_piece` type.
  - Generate a new random piece type for `next_piece`.
  - If the newly spawned piece's coordinates collide with settled blocks, set `status = "game_over"` and `active_piece = null`.


# Implementation Plan: Extend Tetris to Stage 2 - Score, Level, Hold, Next Preview

**Branch**: `002-extend-tetris-stage2` | **Date**: 2026-10-20 | **Spec**: [specs/002-extend-tetris-stage2/spec.md](spec.md)

**Input**: Feature specification from `/specs/002-extend-tetris-stage2/spec.md`

## Summary

This feature extends the browser-based single-player Tetris Core implementation (Stage 1, Option A) to Stage 2, Option A, introducing scoring, leveling, progressive gravity speed, a single-piece Hold slot, a Next Piece preview queue, and real-time frontend dashboard displays. 

Our technical approach centers on extending the existing in-memory backend Python state-machine (`GameSessionSchema` via FastAPI) to maintain and validate the newly added scoring variables, next piece generation, and hold state. The React frontend will receive these state values dynamically and reschedule its automatic tick-gravity timers based on `gravity_interval_ms`, keeping inputs snappy and synchronized while avoiding race conditions or visual jumps when handling out-of-order API responses.

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.0+

**Primary Dependencies**: FastAPI, Pydantic v2 (backend); React 18, Vite (frontend)

**Storage**: In-memory Python `active_sessions` dict mapping UUID strings to Pydantic objects.

**Testing**: Pytest (backend unit & integration tests), Vitest with `@testing-library/react` and JSDOM (frontend hooks & UI tests)

**Target Platform**: Modern standard browsers (frontend) and Windows (`win32`) Python FastAPI server (backend)

**Project Type**: Decoupled Web Application (Frontend + Backend REST API)

**Performance Goals**:
- Dynamic tick intervals rescheduling immediately upon receiving changed `gravity_interval_ms` from backend.
- Frame-rate level responsive player controls (keyboard key listeners for 'C' and UI hold action).

**Constraints**:
- Keep board size exactly 10-by-20.
- No piece rotation (preserved from Stage 1).
- No soft-drop manual movement scoring.
- Exact scoring formula: `1 row: 100 * level`, `2 rows: 300 * level`, `3 rows: 500 * level`, `4 rows: 800 * level` (where level is evaluated prior to line clearing).
- Reset all state variables on game restart.

**Scale/Scope**: Single-player local session, temporary in-memory session lifetime.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Rule 1: Library-First / Core Isolation**: The backend game state logic is fully isolated in `game_engine.py` and schema-enforced with Pydantic. No UI or networking logic leaks into the core engine. (**Passed**)
- **Rule 2: Interface-Driven Contract**: Exposes clean JSON REST endpoints. Stage 2 retains the exact snake_case JSON schemas for new properties while mapping legacy camelCase `activePiece` correctly for compatibility. (**Passed**)
- **Rule 3: Test-First (Non-Negotiable)**: Detailed unit tests will be formulated to isolate and verify the scoring formula, hold operations, line count, levels progression, and edge cases (such as immediate overlap game over upon hold) before implementation changes. (**Passed**)
- **Rule 4: Low-Complexity Architecture**: All new states are stored directly within the single in-memory `GameSessionSchema`. There is no introduction of databases, web sockets, or other heavy infrastructure, keeping system complexity to an absolute minimum. (**Passed**)

## Project Structure

### Documentation (this feature)

```text
specs/002-extend-tetris-stage2/
├── plan.md              # This file (Implementation Plan)
├── research.md          # Phase 0 output (Implementation Research)
├── data-model.md        # Phase 1 output (Data Model & State Transitions)
├── quickstart.md        # Phase 1 output (Quickstart & E2E Validation Guide)
├── contracts/
│   ├── api-contract.md  # Phase 1 output (REST API Contract Specification)
│   └── openapi.json     # Phase 1 output (OpenAPI Specification file)
└── checklists/
    └── requirements.md  # Revise checklist
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py      # REST endpoints (adds POST /api/games/{id}/hold)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Schema models (extended with Stage 2 fields)
│   ├── services/
│   │   ├── __init__.py
│   │   └── game_engine.py    # Game rules, scoring, gravity & hold mechanics
│   ├── __init__.py
│   └── main.py               # Fast API App instantiation
├── tests/
│   ├── integration/
│   │   ├── test_api_us1.py
│   │   ├── test_api_us2.py   # Adds hold, score & leveling API tests
│   │   └── test_api_us3.py   # Adds UI sync & interval tests
│   └── unit/
│       ├── test_game_engine_us1.py
│       ├── test_game_engine_us2.py # Adds engine unit tests for Hold, level & score
│       └── test_game_engine_us3.py # Adds engine unit tests for edge cases (Immediate overlap)
├── conftest.py
└── requirements.txt

frontend/
├── src/
│   ├── components/
│   │   ├── Board.tsx
│   │   ├── GameControls.tsx  # Game controls panel with Hold button
│   │   └── GameOverModal.tsx # Reset & restart modal
│   ├── hooks/
│   │   └── useGame.ts        # Dynamic interval ticking, key binds & stale responses filtering
│   ├── App.tsx               # Main UI rendering panels (Hold, Statistics, Next, Board)
│   ├── index.css
│   ├── main.tsx
│   └── types.ts              # Stage 2 TypeScript interfaces
├── tests/
│   ├── GameOverModal.test.tsx
│   └── useGame.test.ts       # Tests for useGame (Hold keys, speed timers, out-of-order responses)
├── package.json
├── tsconfig.json
└── vite.config.ts
```

**Structure Decision**: Web application layout (Option 2) matching the existing frontend and backend project structure.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(No violations. The proposed design is 100% compliant with the project constitution and constraints.)*


# Quickstart & E2E Validation Guide: Extend Tetris to Stage 2

This guide outlines instructions to set up, run, and validate the Stage 2 single-player Tetris system (Score, Level, Hold, Next Preview) once implemented. It contains runnable validation scenarios to prove that the features work end-to-end.

---

## 1. Prerequisites & Environment Setup

Verify that the following are installed:
- **Python**: Version 3.12 or higher
- **Node.js**: Version 18.0 or higher
- **PowerShell**: Version 7.x (or standard Windows PowerShell 5.1)

### Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate your virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```
   Interactive Swagger UI will be available at `http://localhost:8000/docs`.

### Frontend Setup
1. Navigate to the frontend directory in another terminal:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open the browser at `http://localhost:5173`.

---

## 2. Automated Test Execution

Once implemented, you can verify correct operation by running the test suites.

### Running Backend Tests
From the `backend` directory, execute pytest:
```bash
pytest
```
This runs all unit and integration tests (including Stage 1 and Stage 2 test files).

### Running Frontend Tests
From the `frontend` directory, execute vitest:
```bash
npm run test
```
This runs the React UI components and custom hooks tests.

---

## 3. End-to-End Manual Validation Scenarios

Follow these scenarios to verify the system behavior authoritatively using the Web UI or a REST Client.

### Scenario A: Initialization & Default State
1. **Action**: Open the browser at `http://localhost:5173` or send a `POST` request to `/api/games`.
2. **Expected Outcome**:
   - The UI dashboard displays: `Score: 0`, `Lines Cleared: 0`, `Level: 1`.
   - The "Hold Piece" slot is completely blank/empty.
   - The "Next Piece" slot renders a preview of the upcoming piece.
   - The backend timer ticks every 500 ms (as defined by `gravity_interval_ms` = 500).
   - See [api-contract.md](contracts/api-contract.md) for detail on the response structure.

### Scenario B: Clearing Rows & Level/Speed Up
1. **Action**: Play the game or simulate horizontal line fills using a test harness, so that rows lock and clear.
2. **Expected Outcome**:
   - Clearing 1 line awards `100 * Level` (100 points on Level 1).
   - Clearing 2 lines awards `300 * Level` (300 points on Level 1).
   - Clearing 3 lines awards `500 * Level` (500 points on Level 1).
   - Clearing 4 lines awards `800 * Level` (800 points on Level 1).
   - Clearing 10 total cumulative rows increases the level from 1 to 2.
   - Upon transition to Level 2:
     - The displayed level changes to `2`.
     - The automatic tick timer on the client reschedules instantly and ticks every 450 ms (`gravity_interval_ms = 500 - 50 * (2 - 1) = 450`).
   - For mathematical formula references, consult [data-model.md](data-model.md).

### Scenario C: Piece Holding & Swapping
1. **Action**: Press the **C** key or click the **Hold** button.
2. **Expected Outcome**:
   - The first press stores the current falling piece type in the "Hold" slot. The active piece is replaced by the "Next" piece, and a new "Next" piece is generated.
   - The "Hold" slot displays the held tetromino.
   - Subsequent presses of **C** before the piece locks are ignored (ignored by the server, as `can_hold` is `false`).
   - After a piece locks and settles on the board, `can_hold` is reset to `true`.
   - Pressing **C** now swaps the active piece with the held piece. The previously held piece spawns at the top-center in its initial unrotated state, and the active piece goes into the Hold slot.

### Scenario D: Immediate Overlap Game Over
1. **Action**: Swap a piece to the Hold slot. Wait for settled blocks to pile up to the top-center spawn origin. Press **C** to swap the held piece in.
2. **Expected Outcome**:
   - The swapped piece spawns at the top-center and immediately collides with the settled blocks.
   - The game status transitions to `"game_over"` instantly, the timer stops, and a game over modal appears. No subsequent movements are accepted.


# Implementation Research: Extend Tetris to Stage 2

This document records the research and domain analysis completed for the Stage 2 Tetris extension. It forms the solid engineering foundation for the design of the scoring, leveling, piece-holding, and next piece preview subsystems.

---

## Technical Research & Key Subsystems

### 1. Progressive Gravity Timer & Dynamic Intervals (Frontend)

To make Tetris progressively challenging, gravity ticks must execute faster as the player levels up. 

- **Decision**: Implement a custom React hook `useGame.ts` that dynamically schedules a `useEffect`-driven ticking loop. The tick interval is bound directly to the `gravity_interval_ms` property returned by the backend. When `gravity_interval_ms` changes, the current active timer is automatically cancelled and rescheduled with the new interval.
- **Rationale**: Standard `setInterval` cannot easily change its interval on the fly without being cleared and re-created. Wrapping standard `setTimeout` or a resettable `useEffect` interval loop ensures that changes in gravity interval are immediately applied without waiting for the previous long interval to expire or causing double-ticking.
- **Alternatives Considered**: 
  - *Fixed timer with skip frames*: Keeping a constant 100ms interval and skipping ticks based on level. This is complex to coordinate and introduces visual sluggishness.
  - *Full Frontend-Authoritative ticking*: Discarding backend interval and computing it locally. Rejected because the backend is the single source of truth for the game state machine.

### 2. State Synchronization and Filtering Out-of-Order Responses

In a web application with network latency, rapid key inputs (e.g. holding down arrow keys or spamming soft-drops and Hold commands) can lead to multiple concurrent HTTP requests in flight. If an older request's response arrives *after* a newer request's response, it could overwrite the newer state, causing the game state to "jump backward" or flicker.

- **Decision**: Introduce a client-side transaction/sequence tracker in `useGame.ts`. The client maintains a monotonically increasing `requestSequenceNumber` on the client, or uses a simple locking mechanism (`isRequestInFlight` boolean) that prevents new network commands from being dispatched until the pending server request completes. Specifically, to keep gameplay fluid, we will use a request-locking mechanism where movements or hold triggers are ignored or queued, OR we will track the latest sent request ID and only apply state updates that correspond to the latest request. Given standard Tetris, a lightweight request sequence number combined with disabling/ignoring keyboard events while a request is in flight (`isLoading`) is the most robust way to prevent state desynchronization.
- **Rationale**: A client-side request lock guarantees that actions are executed sequentially on the authoritative backend, keeping the client and server states in lockstep.
- **Alternatives Considered**:
  - *Optimistic UI Updates*: Updating the board state locally before backend confirmation. Rejected because collision, row-clearing, and line-locking rules are extremely complex and authoritatively held on the backend. Optimistic updates would cause visual flickering if the backend disagreed (e.g., due to a late lock collision).

### 3. Hold and Swapping Piece State Machine (Backend)

The "Hold" action swaps the current falling piece with a stored piece. The player can only do this once per spawned piece.

- **Decision**: Maintain two new state variables in the in-memory backend session: `hold_piece: Optional[str]` and `can_hold: bool`.
  - When the game starts or restarts, `hold_piece` is `None` and `can_hold` is `True`.
  - On a `POST /api/games/{id}/hold` request:
    - If `can_hold` is `False`, ignore the command and return the current state.
    - If `hold_piece` is empty (`None`):
      1. Store the active piece's *type* in `hold_piece`.
      2. Set the `active_piece` to a new tetromino spawned at the top-center using the current `next_piece` type.
      3. Generate a new random piece type for `next_piece`.
      4. Set `can_hold` to `False`.
    - If `hold_piece` is already occupied (not `None`):
      1. Swap the active piece's type with `hold_piece` (the current active piece's type is saved in `hold_piece`, and the previously held piece type is spawned as the new `active_piece` at the top-center in its initial unrotated orientation).
      2. Leave the `next_piece` queue completely unchanged.
      3. Set `can_hold` to `False`.
  - When an active piece collision locks onto the board (during normal gravity ticks), reset `can_hold` to `True`.
- **Rationale**: This matches the classic Tetris hold rule exactly, preventing continuous swapping of the same piece and resetting the swap ability only once a piece locks.
- **Alternatives Considered**:
  - *Client-side hold handling*: Checking `can_hold` only in the frontend. Rejected because the backend is the authoritative state machine; a client could bypass validation and spam the swap command.

### 4. Line Clearing, Leveling, and Scoring Formula (Backend)

Line clearing requires counting rows cleared, adding them to the running total, and updating the level and gravity interval accordingly.

- **Decision**: Perform state calculations inside the locking phase of `tick_session`:
  1. Determine the number of rows cleared (`cleared_count`).
  2. If `cleared_count > 0`:
     - Calculate score: `score += bonus[cleared_count] * level` (using the level active *prior* to line clearing).
     - Update lines: `total_lines += cleared_count`.
     - Update level: `level = 1 + floor(total_lines / 10)`.
     - Update gravity: `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`.
  - The scoring multipliers are:
    - 1 row: 100
    - 2 rows: 300
    - 3 rows: 500
    - 4 rows: 800
- **Rationale**: Leveling up is based on cumulative cleared lines (`total_lines`), where each 10 lines completed increases the level by 1. Basing the scoring multiplier on the level prior to line clearing prevents unfair scoring inflation at transition boundaries and aligns with standard Tetris scoring conventions.
- **Alternatives Considered**:
  - *Level-up on every 10 lines individually*: Checking if `total_lines % 10` crossed a boundary. This is less robust than using `1 + floor(total_lines / 10)`, which is self-correcting and handle multi-line clears that cross multiple boundaries.

### 5. Extended Schema Validation (Pydantic v2)

With several new numeric and string properties, the backend schema must enforce strict validation constraints to prevent illegal states.

- **Decision**: Define Pydantic fields in `GameSessionSchema` with the following rules:
  - `score`: integer, must be `>= 0` (default 0).
  - `total_lines`: integer, must be `>= 0` (default 0).
  - `level`: integer, must be `>= 1` (default 1).
  - `gravity_interval_ms`: integer, must be between `100` and `500` (default 500).
  - `next_piece`: string, must be one of `{"I", "O", "T", "S", "Z", "J", "L"}`.
  - `hold_piece`: string or null, must be one of `{"I", "O", "T", "S", "Z", "J", "L"}` or `None` (default null).
  - `can_hold`: boolean (default true).
- **Rationale**: Pydantic's automated field-level validation guarantees that malformed session states cannot be initialized or persisted, maintaining structural integrity across serialization boundaries.
- **Alternatives Considered**:
  - *Manual validation checks*: Checking fields in endpoints or service functions. Pydantic is already integrated into FastAPI and is more performant and declarative.


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

## QA Acceptance Requirements (Post-Generation QA Iteration 2)

The following strict QA acceptance requirements are added for post-generation QA iteration 2 to address remaining production defects and verification gaps:

1. **StartGame Delayed JSON-Body Race Fix (R1)**:
   - Validate generation ownership after EVERY asynchronous boundary (including `res.json()`) and immediately before applying state/active generation.
   - A stale body success, parsing error, or finally block must never affect the newest game's state, error, loading, timer, or locks.
   - Keep request identifiers (`requestSeqRef`) monotonically increasing. Do not reset `requestSeqRef` on successful starts.
   - Synchronize `gameRef` when authoritative state is applied or cleared, so that queued work does not use a stale React-effect snapshot.

2. **Isolate Mutation Scheduling by Generation (R2)**:
   - A new generation must have independent scheduling immediately. It must be able to move, tick, or Hold even while an old-generation fetch or JSON body remains unresolved.
   - Pending old queued work must never dispatch against the new game.
   - Completion or finally from old work must never release, change, or affect the new queue or its ownership.

3. **Bound Automatic Gravity Scheduling**:
   - Coalesce or skip redundant automatic ticks while one tick is pending or in flight to prevent an accumulated burst.
   - On interval change, game over, restart, or unmount, cancel the old timer and prevent obsolete queued ticks from dispatching.
   - Discard late results after unmount; do not dispatch queued old actions after disposal.
   - Preserve valid error recovery and React StrictMode behavior.

4. **Deferred-Promise Testing**:
   - Add deferred-promise tests that expose actual races:
     - (a) Start A fetch resolves and A.json remains pending, start B fully completes, then A.json resolves and B still wins.
     - (b) A.json rejects while B is pending, leaving B's loading/error ownership intact.
     - (c) An old mutation fetch/body never resolves, restart B completes and B mutations still dispatch/complete without waiting for A.
     - (d) Old queued work is discarded after restart and old completion cannot block/release B's current operation.
     - (e) Mutations before the first game or during pending restart do not dispatch.
     - (f) Test delayed automatic ticks across several intervals: no overlap, no queued burst when the request resolves; verify timer cancellation/rescheduling at 500/450/100 ms with fetch-count deltas and interval boundaries, stop on game over/unmount, and recovery after failure. Include a StrictMode mount/cleanup check if implementing disposal flags.

5. **Repair C/c Key Test Evidence**:
   - Use separate fresh/parameterized test cases for lowercase 'c' and uppercase 'C', asserting exactly one new Hold request and the expected state, without mutating the hook's returned state.
   - Assert that a rejected second Hold sends no new request.

6. **Verify Canonical Geometry for all Seven Previews**:
   - Add parameterized rendered assertions for I/O/T/S/Z/J/L by extracting filled-cell coordinates from the actual preview DOM and comparing with the normalized backend template coordinates.
   - The T must have a centered upper cell and a three-cell lower row.
   - Exercise both Next and held-piece rendering, retaining empty Hold, stats, click/disabled states, and stable coordinate keys. Do not introduce rotation or change canonical backend templates. Do not replace geometry assertions with a copied local function that is not used by rendering.

7. **Replace Tautological GET Checks**:
   - In `backend/tests/unit/test_qa_iteration1.py`, do not read the active sessions dictionary directly to assert GET behavior.
   - Use the actual FastAPI TestClient route for repeated GET calls while spying on the real `secrets.choice` source.
   - Compare complete serialized response/state snapshots, assert zero additional random draws, and expected HTTP status.
   - Preserve exact creation/lock/empty-Hold/occupied-Hold/rejection/game-over draw-count checks, full game-over immutability, and dirty restart assertions. Retain all 18 inherited backend tests and their meaningful assertions.

8. **Re-Run and Document Testing**:
   - Re-run all backend and frontend tests. Save exact command outputs and exit statuses under `docs` with `qa-iteration-2` labels (e.g. `qa-iteration-2-backend-test.txt`, `qa-iteration-2-frontend-test.txt`).
   - Save coverage reports and run Sonar Qube scanner and verification scripts.

## QA Acceptance Requirements (Post-Generation QA Iteration 3)

The following strict QA acceptance requirements are added for post-generation QA iteration 3 to address remaining production defects and verification gaps:

1. **Generation-Owned Automatic Tick Coalescing**:
   - Prevent the unowned-finally bug by using a generation/request owner token or equivalent so that the completion/cleanup of automatic ticks clears only its own pending marker.
   - Verify that older timer callbacks check their captured generation before admitting work.
   - Ensure new generations remain playable while old ones are unresolved.

2. **Deferred A/B Automatic-Tick Regression Test**:
   - Explicitly flush microtasks and assert that A's tick fetch has begun before restarting; assert B's tick fetch has begun before settling A.
   - Settle A and advance multiple B timer intervals while B is pending, proving no extra B tick request/queued burst is admitted.
   - Resolve B, flush, and verify that only the next proper interval triggers exactly one fresh tick.
   - Check that A never overwrites B.

3. **Exercise Claimed Windows in Races Tests**:
   - For creation A, resolve fetch headers, flush microtasks, and assert A.json has been called and is still unresolved before starting B. Then resolve/reject A.json after B is active/pending and assert state/loading/error ownership.
   - For old mutation A, flush/assert its fetch/body is in flight before restarting B; leave it unresolved while B's mutation dispatches/completes. Old queued work must be provably queued behind in-flight A, then suppressed after restart.

4. **Meaningful Timer and Disposal Verification**:
   - Assert request-count deltas at 499+1 ms, 449+1 ms, and 99+1 ms to prove previous intervals are cancelled.
   - Test game-over and unmount cancellation while old work is pending/queued, and verify that settling it does not write stale state or dispatch.
   - Replace the assertion-free StrictMode test with an actual React.StrictMode wrapper and assertions. Keep disposal logic StrictMode-compatible.

5. **Complete GET-State Evidence**:
   - Compare the entire real HTTP JSON state (including activePiece and board) with a serialized snapshot across repeated successful GET calls.
   - Retain actual GET-route choice spying, zero-draw counts, rejection/game-over snapshots, dirty restart, and all inherited assertions. Do not use direct dictionary access as a substitute for invoking GET.

6. **Validation, Auditing, and Documentation**:
   - Run affected frontend/backend suites with XML coverage at docs/coverage.xml, frontend LCOV/text reports, and save all outputs with qa-iteration-3 labels.

## QA Acceptance Requirements (Post-Generation QA Iteration 4)

The following strict QA acceptance requirements are added for post-generation QA iteration 4 to address minor code smells identified by Sonar:

1. **Optional Chain Expressions for Tick Tokens**:
   - Refactor `useGame.ts` to use optional chain expressions `activeToken?.gen === intervalGen` (line 230) and `pendingTickTokenRef.current?.gen === myToken.gen` (line 239) to satisfy Sonar rule `typescript:S6582`.
   - Ensure the generation and request-token identity guards are preserved exactly to not weaken generation ownership.

2. **Refactored Mutation Url Assertions**:
   - Refactor `useGame.test.ts` (lines 1247, 1260, 1279) to use `toHaveLength(1)` on `mutationUrls` assertions instead of testing length and comparing using `.toBe(1)` to satisfy Sonar rule `typescript:S5906`.
   - Maintain equivalent, fully meaningful assertions.






---
description: "Authoritative task list for Stage 2 Tetris implementation"
---

# Tasks: Extend Tetris to Stage 2 - Score, Level, Hold, Next Preview

**Input**: Design documents from `/specs/002-extend-tetris-stage2/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included as requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (i.e., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Path Conventions

- **Backend app**: `backend/app/`
- **Frontend app**: `frontend/src/`
- **Backend tests**: `backend/tests/`
- **Frontend tests**: `frontend/tests/`

---

## Phase 1: Setup & Initial Verification (Shared Infrastructure)

**Purpose**: Project initialization, baseline verification, and security audits.

- [X] T001 [P] Verify current Stage 1 baseline by running existing backend tests via `pytest` in `backend/` and frontend tests via `npm run test` in `frontend/`
- [X] T002 Run dependency security audits (`pip-audit` or `safety` for `backend/requirements.txt` and `npm audit` for `frontend/package.json`) and apply remediation fixes to lockfiles without changing application code

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure, state models, and SonarQube baseline schema updates.

**⚠️ CRITICAL**: This phase must be completed before starting any user story tasks.

- [X] T003 [P] Document 404 HTTPException responses in the OpenAPI schema/endpoints in `backend/app/api/endpoints.py` to fix SonarQube baseline code smell `python:S8415` by adding `responses={404: {"description": "Game not found"}}` to all game-retrieval and mutation endpoints
- [X] T004 Extend `GameSessionSchema` model in `backend/app/models/schemas.py` to include Stage 2 fields with strict validation: `score` (int, >= 0), `total_lines` (int, >= 0), `level` (int, >= 1), `gravity_interval_ms` (int, range [100, 500]), `next_piece` (str, one of the standard 7 shapes), `hold_piece` (Optional[str], nullable standard 7 shapes), and `can_hold` (bool, default True)
- [X] T005 [P] Extend `GameSession` TypeScript interface in `frontend/src/types.ts` to mirror Stage 2 schema properties: `score`, `total_lines`, `level`, `gravity_interval_ms`, `next_piece`, `hold_piece` (nullable string), and `can_hold`

**Checkpoint**: Foundation ready - user story implementation can now begin in priority order

---

## Phase 3: User Story 1 - Scoring, Leveling, and Progressive Gravity (Priority: P1) 🎯 MVP

**Goal**: Implement score tracking, cumulative line-clearing accounting, pre-lock level boundary checks, a minimum gravity floor (100 ms), dynamic timer rescheduling, and secure random piece queue generation.

**Independent Test**: Verify scoring formula, cumulative line counts, pre-lock levels, gravity intervals, and random choice queue count assertions using unit and integration tests.

### Tests for User Story 1

> **NOTE: Write these tests FIRST and ensure they FAIL before changing implementation**

- [X] T006 [P] [US1] Create unit tests in `backend/tests/unit/test_game_engine_us1.py` to verify:
  - Isolated 1, 2, 3, and 4-row scoring scoring rules (`100 * level`, `300 * level`, `500 * level`, `800 * level` respectively) using mock matrices
  - Level boundary calculation `1 + floor(total_lines / 10)` based on cumulative lines cleared
  - Pre-lock level scoring where score multiplier is evaluated using the level *immediately before* the lock
  - Progressive gravity calculations and the minimum gravity interval floor of 100 ms: `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`
  - Next piece queue generation where normal spawning consumes the queue piece and generates exactly one new preview piece
- [X] T007 [P] [US1] Create integration tests in `backend/tests/integration/test_api_us1.py` targeting `/api/games`, `/api/games/{id}`, `/api/games/{id}/tick`, and `/api/games/{id}/move` to verify that GET state responses read state immutably (no consumption of queued next piece) and endpoints return the correct Stage 2 schemas

### Implementation for User Story 1

- [X] T008 [US1] Refactor `create_session` and initialization in `backend/app/services/game_engine.py` to populate initial Stage 2 variables: `score=0`, `total_lines=0`, `level=1`, `gravity_interval_ms=500`, `hold_piece=None`, `can_hold=True`, and populate a secure `next_piece` randomly
- [X] T009 [US1] Update piece selection and spawning in `backend/app/services/game_engine.py` to use Python's cryptographically secure choice generator (e.g. `secrets.choice` or `random.SystemRandom`) to avoid SonarQube baseline vulnerability `python:S2245` (without suppressions) for spawning both `active_piece` and `next_piece`
- [X] T010 [US1] Refactor the row locking phase of `tick_session` in `backend/app/services/game_engine.py` to calculate score using the level *prior* to line clearing, update `total_lines` with cumulative row clears, recalculate level using `1 + floor(total_lines / 10)`, and compute `gravity_interval_ms` using `max(100, 500 - 50 * (level - 1))`
- [X] T011 [US1] Update `tick_session` spawning logic in `backend/app/services/game_engine.py` to spawn the next active piece from `next_piece`, and generate exactly one new random tetromino type for `next_piece`
- [X] T012 [US1] Refactor frontend ticking logic in `frontend/src/hooks/useGame.ts` to reschedule its automatic gravity tick timer immediately upon receiving an updated `gravity_interval_ms` from backend state responses

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Holding and Swapping Tetrominoes (Priority: P2)

**Goal**: Implement the Hold piece mechanic, enabling players to temporarily save their active piece or swap it, restricted to one use per spawned piece, with immediate collision checks and obstructed Hold spawning game overs.

**Independent Test**: Trigger hold via `/hold` endpoint or button, verifying piece swaps, immutable next previews on swaps, ignored holds, reset on lock, and immediate collision game over.

### Tests for User Story 2

> **NOTE: Write these tests FIRST and ensure they FAIL before changing implementation**

- [X] T013 [P] [US2] Create unit tests in `backend/tests/unit/test_game_engine_us2.py` verifying:
  - Hold operations: first hold consumes preview and generates exactly one new preview, storing current active piece in empty Hold slot
  - Hold swaps: swapping with an occupied Hold slot does NOT consume the next preview, but swaps the active piece type with `hold_piece` and spawns the held piece at normal spawn origin in initial orientation
  - Immutable actions: rejected holds (when `can_hold` is false), actions after game-over, and repeated state reads never mutate the game state
  - Obstructed Hold spawn: spawning a piece from Hold that overlaps with settled blocks on the board immediately transitions `status` to `"game_over"` and sets `active_piece` to null
  - Reset on lock: `can_hold` is reset to true ONLY after a piece locks into the board
- [X] T014 [P] [US2] Create integration tests in `backend/tests/integration/test_api_us2.py` to verify the `POST /api/games/{id}/hold` endpoint returns 404 for invalid game IDs, returns the same state shape on success, and returns unmodified state on rejected holds (when `can_hold` is false or status is game_over)

### Implementation for User Story 2

- [X] T015 [US2] Implement `hold_session_piece` function in `backend/app/services/game_engine.py` to handle the hold/swap rules, check spawning collisions, and transition status to `"game_over"` and `active_piece` to null if blocked
- [X] T016 [US2] Add route and handler for `POST /api/games/{id}/hold` in `backend/app/api/endpoints.py` to expose the backend Hold action
- [X] T017 [US2] Update `tick_session` locking phase in `backend/app/services/game_engine.py` to reset `can_hold` to `True` whenever a piece settles/locks onto the board
- [X] T018 [US2] Update `create_session` and restart in `backend/app/services/game_engine.py` to reset `hold_piece` to `None` and `can_hold` to `True`, while generating a fresh random `active_piece` and `next_piece`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently on the backend

---

## Phase 5: User Story 3 - Stage 2 UI Display and Sync (Priority: P3)

**Goal**: Display all Stage 2 statistics, the Next preview queue, and the Hold slot on the UI; handle keyboard 'C' / 'c' key and click triggers; implement transaction sequencing to prevent out-of-order API race conditions (especially across restarts); and visually disable the Hold button when unavailable.

**Independent Test**: Verify UI rendering, C/c keybind triggers, unclickable Hold button when `can_hold` is false or status is `"game_over"`, and out-of-order request discarding across a restart.

### Tests for User Story 3

> **NOTE: Write these tests FIRST and ensure they FAIL before changing implementation**

- [X] T019 [P] [US3] Create frontend tests in `frontend/tests/useGame.test.ts` to verify:
  - 'C' and 'c' keyboard triggers and Hold button clicks dispatch `POST /api/games/{id}/hold`
  - Stale responses are discarded to prevent out-of-order state regression (e.g. sequence tracking)
  - Stale responses across restarts are properly invalidated so that pre-restart responses never override the reset state
  - Hold button is visually disabled and unclickable when `can_hold` is false or game status is `"game_over"`
- [X] T020 [P] [US3] Create frontend tests in `frontend/tests/GameOverModal.test.tsx` verifying that restarting reset-clears the Stage 2 visual panels correctly

### Implementation for User Story 3

- [X] T021 [US3] Refactor frontend `Board.tsx` in `frontend/src/components/Board.tsx` to fix SonarQube baseline code smell `typescript:S6479` by using stable React keys (e.g., combining row/col index with cell value or a stable coordinate ID string) instead of array indices
- [X] T022 [US3] Apply optional chaining in `frontend/src/App.tsx` and `frontend/src/hooks/useGame.ts` to fix SonarQube baseline code smells `typescript:S6582` by preferring `?.` for state access (e.g., `game?.score`, `game?.activePiece`)
- [X] T023 [US3] Implement client-side transaction request sequence tracking or locking in `frontend/src/hooks/useGame.ts` to filter out stale, out-of-order responses, specifically invalidating pending responses across restart so they cannot overwrite the reset state
- [X] T024 [US3] Add `hold` API fetch function in `frontend/src/hooks/useGame.ts` to dispatch `POST /api/games/{id}/hold` requests
- [X] T025 [US3] Bind `C` and `c` keys in keydown event listener in `frontend/src/hooks/useGame.ts` to trigger the `hold` function
- [X] T026 [US3] Design and build the Stage 2 dashboard panels in `frontend/src/App.tsx`, adding styled UI panels for Score, level, total_lines statistics, Hold Piece preview rendering, Next Piece preview rendering, and a clickable Hold button that is disabled when `can_hold` is false or status is `"game_over"`

**Checkpoint**: All user stories should now be independently functional and integrated!

---

## Phase 6: Polish & Quality/Remediation (Polish)

**Purpose**: Execute code cleaning, compile production builds, run coverage outputs, and verify complete SonarQube baseline remediation.

- [X] T027 Fix SonarQube baseline code smell `css:S7924` in `frontend/src/index.css` by updating text styles to ensure foreground text has a highly readable and contrast-compliant color with its background
- [X] T028 Run backend test suite with coverage, producing a `backend/coverage.xml` XML coverage file and verify all backend assertions pass 100%
- [X] T029 Run frontend test suite with coverage, producing a frontend LCOV coverage report (`frontend/coverage/lcov.info`) and verify all frontend assertions pass 100%
- [X] T030 Build the frontend for production via `npm run build` in `frontend/` to verify absence of typescript compilation or bundling errors
- [X] T031 Execute the local SonarQube scanning/verification tool to confirm all 9 baseline issues from `docs/sonar-baseline/sonar-issues.json` are completely remediated and no new code smells or vulnerabilities are introduced
- [X] T032 Perform quickstart manual validation scenarios in `specs/002-extend-tetris-stage2/quickstart.md` to guarantee perfect game-play and input responsiveness

---

## Phase 7: Post-Generation QA Iteration 1

**Purpose**: Systematically implement all corrections and post-generation QA requirements specified in QA-01 to QA-12.

- [X] T033 [US1] Replace backend tests with production path verification, removing duplicated scoring formulas (QA-01).
- [X] T034 [US1] Patch production random choice source with deterministic sequences and assert exact draw counts (QA-02).
- [X] T035 [US2/US3] Compare deep serialized full-state snapshots for repeated GET, rejected Hold, and after game-over actions, and verify dirty-state cleanup on restart (QA-03 / QA-04).
- [X] T036 [US1] Correct mislabeled bent pieces in scoring fixtures to be real horizontal I templates (QA-05).
- [X] T037 [US3] Implement frontend restart isolation using monotonically increasing generation counter to prevent state overwrites (QA-06 / QA-09).
- [X] T038 [US3] Implement mutation request serialization via a synchronous in-flight guard / queue (QA-06).
- [X] T039 [US3] Add deferred promise tests to verify concurrency, overlap, and race condition handling (QA-06 / QA-09).
- [X] T040 [US3] Verify timer scheduling, rescheduling, and cancellation paths via fake-timer tests (QA-09).
- [X] T041 [US3] Correct T preview cell orientation and verify all 7 shapes against template coordinates in App tests (QA-07).
- [X] T042 [US3] Fix npm vulnerability dependencies in frontend package-lock.json with compatible patched versions (QA-10).
- [X] T043 Produce backend/frontend coverage reports (XML, LCOV, text summary) and execute Sonar Qube scanner and save output with qa-iteration-1 labels (QA-11 / QA-12).

---

## Phase 8: Post-Generation QA Iteration 2

**Purpose**: Fix remaining production defects and resolve all verification gaps identified in QA Iteration 2.

- [X] T044 [US3] Fix startGame delayed JSON-body race (R1) by checking generation ownership after every asynchronous boundary, keeping requestSeqRef monotonically increasing, and synchronizing gameRef.
- [X] T045 [US3] Isolate mutation scheduling by generation (R2) by providing generation-specific queues or cancelling stale generation queues.
- [X] T046 [US3] Bound automatic gravity scheduling to prevent burst replay of queued gravity ticks, and handle timer cancellation on game over, restart, or unmount.
- [X] T047 [US3] Add deferred-promise tests exposing the detailed races, including A.json vs B wins, A.json reject vs B, mutation isolation by generation, old queue discarding, and bounded automatic ticks.
- [X] T048 [US3] Repair C/c key test evidence by creating separate fresh cases for lowercase 'c' and uppercase 'C' without direct state mutation, asserting call counts, and verifying blocked holds.
- [X] T049 [US3] Verify canonical geometry of all seven preview shapes (I, O, T, S, Z, J, L) in App tests against backend template coordinates.
- [X] T050 [US1] Replace tautological GET checks in backend/tests/unit/test_qa_iteration1.py with real FastAPI TestClient GET calls with secrets.choice spying, state comparisons, and zero random draws checks.
- [X] T051 [US3] Re-run and save backend and frontend tests, coverage reports, and Sonar Qube scans with qa-iteration-2 labels.

---

## Phase 9: Post-Generation QA Iteration 3

**Purpose**: Fix automatic tick coalescing ownership defect and complete rigorous verification evidence in QA Iteration 3.

- [ ] T052 [US3] Refactor automatic tick coalescing in `useGame.ts` to use a generation-owned token/Map so completion/cleanup clears only its own pending flag, and older timers verify their captured generation.
- [ ] T053 [US3] Add deferred A/B automatic-tick regression test in `useGame.test.ts` to assert A's tick fetch has begun before restart, B's tick fetch has begun before A settles, and no extra ticks or bursts are admitted when A settles.
- [ ] T054 [US3] Make existing delayed-body and old-queue tests in `useGame.test.ts` exercise their claimed windows by asserting that A.json or A's mutation is unresolved and in flight before starting B.
- [ ] T055 [US3] Complete meaningful timer/disposal verification in `useGame.test.ts`, including 499+1 ms, 449+1 ms, and 99+1 ms interval cancellation checks, game-over/unmount cancellation, and actual React.StrictMode wrapper testing with assertions.
- [ ] T056 [US1] Fix complete GET-state evidence in `test_qa_iteration1.py` by comparing the entire real HTTP JSON state (including activePiece and board) with a serialized snapshot across repeated successful GET calls.
- [ ] T057 [US3] Re-run and save backend and frontend tests, XML/LCOV coverage reports, and Sonar Qube scans with qa-iteration-3 labels.

---

## Phase 10: Post-Generation QA Iteration 4 (Sonar Remediation)

**Purpose**: Remediate the 5 minor code smell issues identified by Sonar (S6582 and S5906) while preserving tick ownership and meaningful assertions.

- [X] T058 [US3] Refactor `useGame.ts` to use optional chain expressions for `activeToken?.gen === intervalGen` and `pendingTickTokenRef.current?.gen === myToken.gen` to satisfy `typescript:S6582`, preserving generation and request-token identity guards exactly.
- [X] T059 [US3] Refactor `useGame.test.ts` to use `toHaveLength(1)` on `mutationUrls` assertions to satisfy `typescript:S5906`, keeping equivalent meaningful assertions.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup & Audit (Phase 1)**: No dependencies - can start immediately
- **Foundational Models (Phase 2)**: Depends on Phase 1 completion - BLOCKS all subsequent user stories
- **User Stories (Phases 3 to 5)**: All depend on Foundational (Phase 2) completion
  - **User Story 1 (P1)**: Establish core gameplay MVP first
  - **User Story 2 (P2)**: Integrates with the backend state after User Story 1
  - **User Story 3 (P3)**: Integrates UI statistics, previews, and key listeners; depends on US1/US2 APIs and schemas
- **Polish & Remediation (Phase 6)**: Depends on all user stories being complete

### Parallel Opportunities

- Verification and audits (`T001` and `T002`) can run in parallel
- Model extensions (`T003` and `T005`) can run in parallel
- Test suite preparation tasks (`T006`, `T007`, `T013`, `T014`, `T019`, `T020`) can be drafted in parallel
- Once Phase 2 is complete, US1 and US2 backend implementation can be worked on in parallel by different developers:
  - Developer A: scoring, leveling, and progressive gravity timer in `game_engine.py` (`T008` to `T011`)
  - Developer B: hold/swap backend actions and hold endpoints in `game_engine.py` and `endpoints.py` (`T015` to `T018`)
- Polish tasks, LCOV reports, XML coverage reports, and production builds (`T027` to `T030`) can run in parallel once code is complete

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup & Audit
2. Complete Phase 2: Foundational (schemas and interface setups, 404 documentation)
3. Complete Phase 3: User Story 1 (Scoring, Leveling, and Gravity)
4. **STOP and VALIDATE**: Verify that rows cleared via unit tests or manual console ticks accurately level-up, score, and increase gravity tick speed
5. Deliver the first MVP increment!

### Incremental Delivery

1. Complete Setup + Foundational → Core Stage 2 structures ready
2. Add User Story 1 → Test independently → Deliver (MVP: scoring and speed)
3. Add User Story 2 → Test independently → Deliver (tactical hold option)
4. Add User Story 3 → Test independently → Deliver (full visual HUD and race-proof play)
5. Polish & Verification → Final fully-featured release

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group (upon user request in follow-up sessions)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
