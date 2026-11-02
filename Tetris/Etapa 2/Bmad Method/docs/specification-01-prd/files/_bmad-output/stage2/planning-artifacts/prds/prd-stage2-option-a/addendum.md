---
title: "PRD Addendum: Stage 2 Technical Contracts & Strategy"
status: draft
created: 2026-10-25T12:00
updated: 2026-10-25T12:00
---

# PRD Addendum: Stage 2 Technical Contracts & Strategy

This addendum records the API schema shifts, endpoints, frontend reactivity design, and automated testing architecture for Stage 2.

## 1. Updated API Contract (GameState Schema)

The state returned by all endpoints (and serialized by the backend) is extended to include Stage 2 fields.

### JSON State Payload (`GameState` model):
```json
{
  "id": "string (UUID)",
  "status": "playing" | "game_over",
  "board": [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ... (20 rows of 10 columns; 0 = empty, 1-7 = settled block color indices)
  ],
  "active_piece": {
    "shape": "I" | "J" | "L" | "O" | "S" | "T" | "Z",
    "origin": {"row": 0, "col": 3},
    "cells": [
      {"row": 0, "col": 3},
      {"row": 0, "col": 4},
      {"row": 0, "col": 5},
      {"row": 0, "col": 6}
    ]
  },
  "score": 0,
  "total_lines": 0,
  "level": 1,
  "gravity_interval_ms": 500,
  "next_piece": "I" | "J" | "L" | "O" | "S" | "T" | "Z",
  "hold_piece": "I" | "J" | "L" | "O" | "S" | "T" | "Z" | null,
  "can_hold": true
}
```

### Endpoints
1. **`POST /api/games`**
   - **Status Code:** 201 Created
   - **Behavior:** Initializes score to 0, lines to 0, level to 1, gravity_interval_ms to 500, select active and next piece randomly. Returns GameState.
2. **`GET /api/games/{id}`**
   - **Status Code:** 200 OK (or 404)
   - **Behavior:** Returns current GameState. Does NOT consume next_piece.
3. **`POST /api/games/{id}/tick`**
   - **Status Code:** 200 OK (or 404)
   - **Behavior:** Performs gravity tick.
4. **`POST /api/games/{id}/move`**
   - **Status Code:** 200 OK (or 404 / 422)
   - **Behavior:** Moves piece.
5. **`POST /api/games/{id}/hold`**
   - **Status Code:** 200 OK (or 400 Bad Request if can_hold is false / 404)
   - **Behavior:** Performs Hold swap. Swaps the current active piece and the Hold slot. Returns GameState.

---

## 2. Frontend Reactivity & Timing

To ensure robust synchronizations under React StrictMode:
- **Timer Management:** Keep a single `setInterval` ref synchronized with the authoritative server-side `gravity_interval_ms`. Recreate the interval ONLY when `gravity_interval_ms` changes or status updates.
- **Race Condition Prevention:**
  - Standard state setters should ignore responses if their ID is obsolete or if they represent an older game version.
  - Manual inputs (ArrowLeft, ArrowRight, ArrowDown) are disabled when `status === "game_over"`.
  - Hold interactions are bound to the `C` key and Hold button, disabled when `can_hold` is `false`.

---

## 3. Automated Test Strategy

To verify Stage 2 features rigorously, we will introduce automated tests covering:
1. **Scoring Scenarios (with Mock Fixtures):**
   - We will write isolated domain unit tests using board fixtures pre-completed at the bottom rows.
   - Using a standard `"O"` piece or rotation-free locks, we will trigger 1, 2, 3, and 4 completed row clears.
   - Validate that Level 1 awards 100, 300, 500, or 800 points.
   - Validate that Level 2 awards 200, 600, 1000, or 1600 points (using pre-lock level).
2. **Progression Calculations:**
   - Validate that level formula `1 + floor(total_lines / 10)` works under different values (e.g. 9 lines -> level 1, 10 lines -> level 2, 11 lines -> level 2, 20 lines -> level 3).
   - Validate that gravity interval formula computes correctly down to 100ms.
3. **Hold State Machine Transitions:**
   - Empty Hold swap: active piece gets stored in hold, next piece spawned, next piece generated. `can_hold` is set to false.
   - Occupied Hold swap: active piece swapped with hold, former hold spawns at standard origin, next piece preview is untouched. `can_hold` is set to false.
   - Lock reset: locking resets `can_hold` to true.
   - Double hold rejection: hold request fails or is ignored if `can_hold` is false before lock.
4. **Obstructed Spawn Game Over:**
   - Validate that if standard spawn coordinates are filled by settled blocks, any spawn (normal or hold retrieval) immediately triggers a `"game_over"` status.
