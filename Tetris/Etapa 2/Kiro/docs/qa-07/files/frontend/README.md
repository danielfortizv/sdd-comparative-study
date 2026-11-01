# Frontend - Tetris Stage 2 (Option A)

React + TypeScript client (Vite) that renders authoritative game state from the
backend API and forwards player controls. It performs no game logic locally;
score, lines, level, gravity, hold, and preview all come from backend state.

## Structure

- `src/types.ts` - types mirroring the API payload (adds the seven Stage 2 fields).
- `src/api.ts` - typed fetch client, including `holdGame`.
- `src/useGame.ts` - game-state hook with a generation-scoped FIFO queue serializing EVERY mutation (manual moves/holds and automatic ticks), immediate old-identity invalidation on create/restart, a coalesced per-generation tick scheduler driven by the backend `gravity_interval_ms`, exact timeout cancellation at manual dispatch time, strict guard ownership, and StrictMode-safe cleanup.
- `src/Board.tsx` - renders the 20x10 grid and overlays the active piece.
- `src/Preview.tsx` - renders a single piece type as a mini-grid (next and hold).
- `src/App.tsx` - layout, keyboard controls (arrows + C/c), Hold/Restart buttons, the score/lines/level sidebar, and the game-over message.
- `src/main.tsx` - production bootstrap that mounts `App` into `#root`.

## Setup

```
npm install
```

## Run (development)

```
npm run dev
```

Opens on `http://localhost:5173`. The backend is expected at `http://localhost:8000`; override with the `VITE_API_BASE` environment variable.

## Build (production)

```
npm run build
```

Type-checks with `tsc` and bundles with Vite into `dist/`.

## Test and coverage

Tests use Vitest + Testing Library with the `@vitest/coverage-v8` provider. They live under `src/**/*.test.ts(x)` and emit an LCOV report at `coverage/lcov.info`.

```
npm run test                 # run once
npm run test -- --coverage   # with coverage -> coverage/lcov.info
```

### Coverage scope (denominator)

The LCOV report covers the full executable production `src` tree with no production exclusions: `api.ts`, `App.tsx`, `Board.tsx`, `Preview.tsx`, `main.tsx`, `types.ts`, and `useGame.ts`. In particular `src/main.tsx` is an executable production bootstrap and is kept in the denominator (covered by a real mount test in `src/main.test.tsx`), not excluded. Only genuine non-production glue is excluded: test files (`src/**/*.test.ts(x)`), the test setup (`src/test-setup.ts`), and the declaration-only environment type (`src/vite-env.d.ts`). The latest run is 47 tests passing with overall coverage of about 89% statements / 94% lines over that production denominator.

The R1/R2/R3 production request-ordering/lifecycle guarantees are covered by `src/useGame.races.test.tsx`, which drives the real `useGame` hook and real `api` client through a controllable `fetch` whose response headers and `response.json()` body resolve independently, under fake timers, with no mocking of the hook.

## Audit (security)

```
npm audit --json             # authoritative full dependency tree
npm audit --omit=dev --json  # production-only tree
```

The authoritative signal is the full-tree audit (not `--omit=dev`), because the build/test toolchain (Vite, Vitest) are `devDependencies`. After the documented remediation both the full-tree and production-only audits report 0 vulnerabilities (exit 0).

### Remediated versions (Node 25.6.1 environment)

The Stage 1 dev toolchain had vulnerable pins. There is no hard restriction to preserve Vite 5, so the following mutually compatible, patched versions are pinned (React 18 and TypeScript behavior preserved):

- `vite` `8.3.5` (clears the vite / esbuild / source-map-js advisories)
- `vitest` `4.1.12` (engines allow Node 25; peer `vite ^6 || ^7 || ^8`)
- `@vitest/coverage-v8` `4.1.12` (peer `vitest 4.1.12`)
- `@vitejs/plugin-react` `6.1.2` (peer `vite ^8`)

Vitest 5.x was not selected because its `engines` (`^22.12 || ^24 || >=26`) do not include the installed Node 25.6.1; Vitest 4.1.12 is the highest line whose engines accept Node 25 while still clearing every advisory.

## Controls

- Left arrow / Left button: move left
- Right arrow / Right button: move right
- Down arrow / Soft Drop button: soft drop (no score)
- C key / Hold button: hold or swap the active piece (once per piece)
- Restart button: start a new game

Gravity advances using the backend `gravity_interval_ms` while playing, reschedules when the interval changes (for example 500 -> 450 ms on the first level-up), and stops on game over, which displays a clear "Game Over" message.
