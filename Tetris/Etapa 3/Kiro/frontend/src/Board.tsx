// Renders the 20x10 grid from authoritative API state.
// This component performs no game logic; it only displays cells.

import type { GameState } from "./types";

const ROWS = 20;
const COLS = 10;

// Color per block type code (1..7); index 0 (empty) is transparent.
const COLORS: Record<number, string> = {
  0: "#111827",
  1: "#22d3ee", // I
  2: "#facc15", // O
  3: "#a855f7", // T
  4: "#22c55e", // S
  5: "#ef4444", // Z
  6: "#3b82f6", // J
  7: "#f97316", // L
};

// Numeric code used to color the active piece (reuses its type code).
const TYPE_CODE: Record<string, number> = {
  I: 1,
  O: 2,
  T: 3,
  S: 4,
  Z: 5,
  J: 6,
  L: 7,
};

interface BoardProps {
  state: GameState;
}

export function Board({ state }: BoardProps) {
  // Build a display grid by copying the settled board, then overlaying the
  // active piece cells on top so the falling piece is visible.
  const grid: number[][] = state.board.map((row) => row.slice());

  if (state.active_piece) {
    const code = TYPE_CODE[state.active_piece.type];
    for (const [r, c] of state.active_piece.cells) {
      if (r >= 0 && r < ROWS && c >= 0 && c < COLS) {
        grid[r][c] = code;
      }
    }
  }

  return (
    <div
      className="board"
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${COLS}, 24px)`,
        gridTemplateRows: `repeat(${ROWS}, 24px)`,
        gap: "1px",
        background: "#1f2937",
        padding: "4px",
        width: "fit-content",
      }}
    >
      {grid.flatMap((row, r) =>
        row.map((code, c) => (
          <div
            key={`${r}-${c}`}
            style={{
              width: 24,
              height: 24,
              background: COLORS[code] ?? COLORS[0],
              borderRadius: 2,
            }}
          />
        )),
      )}
    </div>
  );
}
