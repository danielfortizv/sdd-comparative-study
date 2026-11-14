// Stage 4 Canvas palette + expected-mask oracle (task 20.1).
//
// This module mirrors the FROZEN production Canvas renderer
// (frontend/src/CanvasBoard.tsx) so the harness can compute the EXACT expected
// per-cell color an authoritative game state would paint on the real Canvas,
// and compare it to a SINGLE actual Canvas image-buffer read sampled at 200
// cell centers (design.md "Pixel oracle"; Req 27.1, 27.2, 27.3). It replaces
// the OBSOLETE Stage 3 DOM-cell MutationObserver approach entirely: there is no
// DOM-cell signature here, only real Canvas RGBA.
//
// This module is PURE and side-effect free. Importing it launches no browser,
// spawns no process, and reads no file. It only exports constants and pure
// functions, so it is safe to import from both the harness driver and the
// non-timing self-checks.

// Board geometry (10 wide x 20 tall = 200 cells), identical to the production
// renderer's ROWS/COLS.
export const BOARD_COLS = 10;
export const BOARD_ROWS = 20;
export const BOARD_CELLS = BOARD_COLS * BOARD_ROWS; // 200

// Per-type colors preserved VERBATIM from the frozen CanvasBoard.tsx `COLORS`.
// Index 0 (empty) is the board background; codes 1..7 are the piece-type colors.
// These MUST stay byte-identical to the production palette; the harness never
// edits the frozen frontend, it only mirrors it here for the pixel oracle.
export const COLORS = Object.freeze({
  0: "#111827",
  1: "#22d3ee", // I
  2: "#facc15", // O
  3: "#a855f7", // T
  4: "#22c55e", // S
  5: "#ef4444", // Z
  6: "#3b82f6", // J
  7: "#f97316", // L
});

// Piece-type letter -> numeric code, preserved VERBATIM from the frozen
// CanvasBoard.tsx `TYPE_CODE`. The active piece is drawn in its type color.
export const TYPE_CODE = Object.freeze({
  I: 1,
  O: 2,
  T: 3,
  S: 4,
  Z: 5,
  J: 6,
  L: 7,
});

// Parse a "#rrggbb" (or "#rgb") hex string to an {r,g,b} byte triple. Returns
// null for anything that is not a recognizable opaque hex color so a caller can
// treat an unknown field as null (never as a zeroed black pixel).
export function hexToRgb(hex) {
  if (typeof hex !== "string") return null;
  let v = hex.trim().toLowerCase();
  const short = v.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])$/);
  if (short) {
    v = "#" + short[1] + short[1] + short[2] + short[2] + short[3] + short[3];
  }
  const m = v.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/);
  if (!m) return null;
  return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) };
}

// The empty-board code grid used as a base. 0 everywhere (background).
function emptyCodeGrid() {
  const grid = new Array(BOARD_ROWS);
  for (let r = 0; r < BOARD_ROWS; r += 1) {
    grid[r] = new Array(BOARD_COLS).fill(0);
  }
  return grid;
}

// Compute the EXACTLY-rendered per-cell numeric code grid (row-major, 20x10)
// that the production Canvas would paint for a given authoritative state: copy
// the settled board, then overlay the active piece's occupied cells with its
// type code, exactly as CanvasBoard.draw does (settled cells first, active
// piece overlaid on top). Returns null when the state is not a usable 20x10
// board, so the caller records the sample as unknown rather than inventing a
// zeroed board.
export function codeGridFromState(state) {
  if (!state || !Array.isArray(state.board) || state.board.length !== BOARD_ROWS) {
    return null;
  }
  const grid = emptyCodeGrid();
  for (let r = 0; r < BOARD_ROWS; r += 1) {
    const row = state.board[r];
    if (!Array.isArray(row) || row.length !== BOARD_COLS) return null;
    for (let c = 0; c < BOARD_COLS; c += 1) {
      const code = row[c];
      grid[r][c] = typeof code === "number" && COLORS[code] != null ? code : 0;
    }
  }
  const active = state.active_piece;
  if (active && Array.isArray(active.cells) && TYPE_CODE[active.type] != null) {
    const code = TYPE_CODE[active.type];
    for (const pair of active.cells) {
      if (!Array.isArray(pair) || pair.length < 2) continue;
      const r = pair[0];
      const c = pair[1];
      if (r >= 0 && r < BOARD_ROWS && c >= 0 && c < BOARD_COLS) grid[r][c] = code;
    }
  }
  return grid;
}

// Expected per-cell RGB mask (row-major, 200 entries of {r,g,b}) that the
// production Canvas would paint for a state. Returns null if the state is not a
// usable board. This is the EXPECTED half of the pixel oracle; the OBSERVED
// half is a single real Canvas image-buffer read sampled at the same 200 cell
// centers (see maskFromImageData).
export function expectedRgbMaskFromState(state) {
  const grid = codeGridFromState(state);
  if (!grid) return null;
  const mask = new Array(BOARD_CELLS);
  let i = 0;
  for (let r = 0; r < BOARD_ROWS; r += 1) {
    for (let c = 0; c < BOARD_COLS; c += 1) {
      const rgb = hexToRgb(COLORS[grid[r][c]] ?? COLORS[0]);
      mask[i] = rgb; // never null for a known code
      i += 1;
    }
  }
  return mask;
}

// The 200 cell-center sample points, in device pixels, for a backing store of
// the given width/height. The production renderer paints cell (r,c) over the
// rectangle [c*cellW, r*cellH, cellW, cellH] in CSS pixels under a DPR scale;
// the backing store is round(cssW*dpr) x round(cssH*dpr). Sampling the CENTER
// of each cell in device pixels is robust to the DPR scale. Returns an array of
// 200 {r, c, x, y} in row-major order. Caller reads these 200 pixels from a
// SINGLE image-buffer read (never 200 separate GPU reads).
export function cellCenterPoints(backingWidth, backingHeight) {
  const pts = new Array(BOARD_CELLS);
  const cellW = backingWidth / BOARD_COLS;
  const cellH = backingHeight / BOARD_ROWS;
  let i = 0;
  for (let r = 0; r < BOARD_ROWS; r += 1) {
    for (let c = 0; c < BOARD_COLS; c += 1) {
      pts[i] = {
        r,
        c,
        x: Math.min(backingWidth - 1, Math.max(0, Math.round((c + 0.5) * cellW))),
        y: Math.min(backingHeight - 1, Math.max(0, Math.round((r + 0.5) * cellH))),
      };
      i += 1;
    }
  }
  return pts;
}

// Build the OBSERVED 200-cell RGB mask from a flat RGBA byte buffer (as a plain
// array of numbers, length 200*4, in the SAME row-major cell-center order as
// cellCenterPoints produced). Alpha is dropped (the board is opaque). Returns
// null if the buffer length is wrong, so an unreadable buffer is recorded as
// unknown rather than zeroed.
export function maskFromCenterRgba(flatRgba) {
  if (!Array.isArray(flatRgba) || flatRgba.length !== BOARD_CELLS * 4) return null;
  const mask = new Array(BOARD_CELLS);
  for (let i = 0; i < BOARD_CELLS; i += 1) {
    mask[i] = { r: flatRgba[i * 4], g: flatRgba[i * 4 + 1], b: flatRgba[i * 4 + 2] };
  }
  return mask;
}

// Compare two RGB masks for exact per-cell equality. Returns an object with the
// match flag and, when they differ, the first differing cell index (never a
// fabricated "close enough"). A null mask never matches.
export function masksEqual(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) {
    return { equal: false, firstDiffIndex: 0 };
  }
  for (let i = 0; i < a.length; i += 1) {
    const x = a[i];
    const y = b[i];
    if (!x || !y || x.r !== y.r || x.g !== y.g || x.b !== y.b) {
      return { equal: false, firstDiffIndex: i };
    }
  }
  return { equal: true, firstDiffIndex: null };
}

// Count how many cells of a mask are a non-background color. Used to detect a
// genuinely changed (piece-bearing) board versus an all-empty placeholder; the
// background color is COLORS[0].
export function nonBackgroundCellCount(mask) {
  const bg = hexToRgb(COLORS[0]);
  if (!Array.isArray(mask) || !bg) return null;
  let n = 0;
  for (const cell of mask) {
    if (cell && (cell.r !== bg.r || cell.g !== bg.g || cell.b !== bg.b)) n += 1;
  }
  return n;
}
