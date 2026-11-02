# Tetris - Stage 1 (Option A)

A browser-based Tetris study, Stage 1, Option A. The Python FastAPI backend owns
the authoritative game state and rules; the React + TypeScript frontend renders
that state and forwards player controls.

Specifications were authored first as Kiro native spec artifacts under
`.kiro/specs/tetris-stage1-option-a/` (`requirements.md`, `design.md`,
`tasks.md`), and the implementation follows those artifacts.

## Scope

Included: 10x20 grid, seven standard tetrominoes in initial orientation, gravity,
left/right/soft-drop movement, side/bottom/stack collisions, locking, single and
multiple line clears, subsequent spawning, game over, and restart.

Excluded (later stages): rotation, wall kicks, line counter, score, speed
progression, hold, preview, ghost piece, configurable controls, persistence,
multiplayer, database, and authentication.

## Layout

- `backend/` — FastAPI backend (domain models, game rules, HTTP controllers).
- `frontend/` — React + TypeScript client (Vite).
- `.kiro/specs/tetris-stage1-option-a/` — spec artifacts.

## Backend

From `backend/`:

```
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Run the API (in-memory state, no database):

```
uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`. Endpoints:

- `POST /api/games` — create or restart a game.
- `GET /api/games/{id}` — read the game state.
- `POST /api/games/{id}/tick` — advance one gravity tick.
- `POST /api/games/{id}/move` — body `{ "direction": "left" | "right" | "down" }`.

Run the rule and API tests:

```
pytest
```

The piece sequence is reproducible under a fixed seed (`DEFAULT_SEED = 20260929`
in `app/store.py`).

## Frontend

From `frontend/`:

```
npm install
npm run dev      # development server on http://localhost:5173
npm run build    # type-check + production build into dist/
```

Set `VITE_API_BASE` to point at a non-default backend URL if needed (defaults to
`http://localhost:8000`).

Controls: Left / Right arrows move the piece; Down arrow soft-drops; the Restart
button starts a new game. Gravity advances every 500 ms while playing, and a
"Game Over" message appears when the game ends.
