# Backend - Tetris Stage 1 (Option A)

Python FastAPI backend that owns the authoritative Tetris game state and rules.
State is held in memory only; there is no database and no authentication.

## Structure

- `app/domain/models.py` — plain domain models (Board, ActivePiece, Game).
- `app/rules/pieces.py` — tetromino definitions and the seeded 7-bag generator.
- `app/rules/engine.py` — pure game rules (spawn, move, tick, lock, clear, game over).
- `app/api/schemas.py` — request/response models and serialization.
- `app/api/games.py` — HTTP controllers (routers).
- `app/store.py` — in-memory game repository.
- `app/main.py` — FastAPI app wiring and CORS.
- `tests/` — pytest rule tests and API tests.

The rules layer has no FastAPI dependency, so it is exercised directly in
`tests/test_rules.py` without the HTTP layer.

## Setup

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

## Run

```
uvicorn app.main:app --reload
```

## Test

```
pytest
```

## API

- `POST /api/games` — create or restart a game; returns state.
- `GET /api/games/{id}` — read state; 404 if unknown.
- `POST /api/games/{id}/tick` — advance one gravity tick.
- `POST /api/games/{id}/move` — body `{ "direction": "left" | "right" | "down" }`;
  invalid direction returns 422, unknown id returns 404.

State shape:

```json
{
  "id": "string",
  "status": "playing | game_over",
  "board": [[0, 1, ...], ...],
  "active_piece": { "type": "T", "origin": [0, 3], "cells": [[0,4],[1,3],[1,4],[1,5]] }
}
```

Board cells use integer codes: `0` empty, `I=1, O=2, T=3, S=4, Z=5, J=6, L=7`.
`active_piece` is `null` when the status is `game_over`.

The piece sequence is deterministic under the fixed seed defined in `app/store.py`.
