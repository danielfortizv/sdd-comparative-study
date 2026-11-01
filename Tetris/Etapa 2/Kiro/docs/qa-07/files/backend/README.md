# Backend - Tetris Stage 2 (Option A)

Python FastAPI backend that owns the authoritative Tetris game state and rules.
State is held in memory only; there is no database and no authentication.

Stage 2 extends Stage 1 with score, cumulative cleared-line count, level,
progressive gravity, a one-piece Hold, and a one-piece next-piece preview. The
backend owns the queued next piece and all scoring/leveling/gravity rules.

## Structure

- `app/domain/models.py` — plain domain models (Board, ActivePiece, Game). The
  `Game` dataclass carries the Stage 2 fields: `score`, `total_lines`, `level`,
  `gravity_interval_ms`, `next_type`, `hold_type`, `can_hold`.
- `app/rules/pieces.py` — tetromino definitions and the seeded 7-bag generator
  (unchanged from Stage 1).
- `app/rules/scoring.py` — pure scoring/level/gravity formulas (Stage 2).
- `app/rules/engine.py` — pure game rules (spawn, move, tick, lock, clear, game
  over) extended with the preview queue, scoring/leveling, and `hold`.
- `app/api/schemas.py` — request/response models and serialization (adds the
  seven Stage 2 fields; board stays integer-coded, active piece stays under
  `active_piece`).
- `app/api/games.py` — HTTP controllers, including `POST /api/games/{id}/hold`.
- `app/store.py` — in-memory game repository.
- `app/main.py` — FastAPI app wiring and CORS.
- `tests/` — pytest rule, scoring, engine, and API tests.

The rules layer has no FastAPI dependency, so it is exercised directly in the
rule/scoring/engine tests without the HTTP layer. The 3- and 4-row clear rules
are verified through the real `engine.lock`/`clear_lines` path using explicitly
labeled isolated-domain fixtures (crafted boards with prefilled complete rows);
no rotated or custom gameplay pieces are introduced.

## Setup

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

The runtime pins in `requirements.txt` are unchanged from Stage 1.

## Run

```
uvicorn app.main:app --reload
```

## Test

```
pytest
```

## Coverage

Coverage uses a dev-only dependency (`pytest-cov`) declared in
`requirements-dev.txt`, which includes the runtime pins via `-r requirements.txt`
and adds `pytest-cov==6.0.0` (compatible with `pytest==8.3.4`). Install it
BEFORE using the `--cov` flag; the runtime pins stay unchanged.

```
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=xml:../docs/coverage.xml
```

This writes `docs/coverage.xml`. If the dev install is skipped, the `--cov`
flag is unavailable with the baseline runtime pins; use the stdlib `coverage`
run form instead (`python -m coverage run -m pytest && python -m coverage xml`).

## API

- `POST /api/games` — create or restart a game; returns state (HTTP 200).
- `GET /api/games/{id}` — read state (side-effect free, no generator draw);
  404 if unknown.
- `POST /api/games/{id}/tick` — advance one gravity tick; applies Stage 2
  scoring/leveling on any resulting clear.
- `POST /api/games/{id}/move` — body `{ "direction": "left" | "right" | "down" }`;
  invalid direction returns 422, unknown id returns 404. Soft drop adds no score.
- `POST /api/games/{id}/hold` — hold or swap the active piece; same state shape;
  404 if unknown; no-op when `can_hold` is false or the game is over.

State shape:

```json
{
  "id": "string",
  "status": "playing | game_over",
  "board": [[0, 1, ...], ...],
  "active_piece": { "type": "T", "origin": [0, 3], "cells": [[0,4],[1,3],[1,4],[1,5]] },
  "score": 0,
  "total_lines": 0,
  "level": 1,
  "gravity_interval_ms": 500,
  "next_piece": "I",
  "hold_piece": null,
  "can_hold": true
}
```

Board cells use integer codes: `0` empty, `I=1, O=2, T=3, S=4, Z=5, J=6, L=7`.
`active_piece` is `null` when the status is `game_over`.

Scoring/leveling/gravity controls:

- Line award by rows cleared, multiplied by the pre-lock level:
  1/2/3/4 rows -> 100/300/500/800 * level; 0 rows -> 0.
- `total_lines` increases by the cleared-row count after scoring.
- `level = 1 + floor(total_lines / 10)`.
- `gravity_interval_ms = max(100, 500 - 50 * (level - 1))`.

The piece sequence is deterministic under the fixed seed defined in
`app/store.py`.
