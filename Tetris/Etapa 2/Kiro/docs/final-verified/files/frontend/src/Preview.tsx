// Renders a single piece type as a small mini-grid, used for the next-piece
// preview and the hold slot. Rendering only; no game-rule logic.

import type { PieceType } from "./types";

// Canonical unrotated offsets, mirroring the backend shapes.
const SHAPES: Record<PieceType, Array<[number, number]>> = {
  I: [[0, 0], [0, 1], [0, 2], [0, 3]],
  O: [[0, 0], [0, 1], [1, 0], [1, 1]],
  T: [[0, 1], [1, 0], [1, 1], [1, 2]],
  S: [[0, 1], [0, 2], [1, 0], [1, 1]],
  Z: [[0, 0], [0, 1], [1, 1], [1, 2]],
  J: [[0, 0], [1, 0], [1, 1], [1, 2]],
  L: [[0, 2], [1, 0], [1, 1], [1, 2]],
};

const COLORS: Record<PieceType, string> = {
  I: "#22d3ee",
  O: "#facc15",
  T: "#a855f7",
  S: "#22c55e",
  Z: "#ef4444",
  J: "#3b82f6",
  L: "#f97316",
};

const PREVIEW_ROWS = 2;
const PREVIEW_COLS = 4;

interface PreviewProps {
  // The piece type to render, or null for an empty slot.
  piece: PieceType | null;
  // Accessible label describing the slot (e.g. "Next piece", "Hold piece").
  label: string;
}

export function Preview({ piece, label }: Readonly<PreviewProps>) {
  const grid: Array<Array<PieceType | null>> = Array.from(
    { length: PREVIEW_ROWS },
    () => Array.from({ length: PREVIEW_COLS }, () => null as PieceType | null),
  );

  if (piece) {
    for (const [r, c] of SHAPES[piece]) {
      if (r < PREVIEW_ROWS && c < PREVIEW_COLS) {
        grid[r][c] = piece;
      }
    }
  }

  return (
    <div
      role="img"
      aria-label={piece ? `${label}: ${piece}` : `${label}: empty`}
      data-testid={`preview-${label.toLowerCase().replace(/\s+/g, "-")}`}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${PREVIEW_COLS}, 16px)`,
        gridTemplateRows: `repeat(${PREVIEW_ROWS}, 16px)`,
        gap: "1px",
        background: "#1f2937",
        padding: "3px",
        width: "fit-content",
      }}
    >
      {grid.flatMap((row, r) =>
        row.map((cell, c) => (
          <div
            key={`${r}-${c}`}
            style={{
              width: 16,
              height: 16,
              background: cell ? COLORS[cell] : "#111827",
              borderRadius: 2,
            }}
          />
        )),
      )}
    </div>
  );
}
