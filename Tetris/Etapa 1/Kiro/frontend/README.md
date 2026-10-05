# Frontend - Tetris Stage 1 (Option A)

React + TypeScript client (Vite) that renders authoritative game state from the
backend API and forwards player controls. It performs no game logic locally.

## Structure

- `src/types.ts` — types mirroring the API payload.
- `src/api.ts` — typed fetch client for the four endpoints.
- `src/useGame.ts` — game-state hook with the fixed 500 ms gravity loop.
- `src/Board.tsx` — renders the 20x10 grid and overlays the active piece.
- `src/App.tsx` — layout, keyboard controls, Restart button, game-over message.

## Setup

```
npm install
```

## Run (development)

```
npm run dev
```

Opens on `http://localhost:5173`. The backend is expected at
`http://localhost:8000`; override with the `VITE_API_BASE` environment variable.

## Build (production)

```
npm run build
```

Type-checks with `tsc` and bundles with Vite into `dist/`.

## Controls

- Left arrow: move left
- Right arrow: move right
- Down arrow: soft drop
- Restart button: start a new game

Gravity advances every 500 ms while the game is playing and stops on game over,
which displays a clear "Game Over" message.
