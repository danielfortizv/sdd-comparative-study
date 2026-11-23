// Canvas 2D board renderer (M2). Replaces the per-cell DOM grid of Board.tsx.
//
// This component draws the authoritative 10x20 board on a real Canvas 2D
// surface via `getContext("2d")` and `fillRect`. It NEVER renders the main
// board as a grid of per-cell React DOM elements and NEVER uses data-attributes
// standing in for pixels.
//
// Task 7.1 established the drawing authority and the component skeleton.
// Task 7.2 (this revision) adds the device-pixel-ratio sizing and the
// ResizeObserver-driven redraw triggers:
//   - A `useEffect` keyed on the authoritative `state` redraws from the new
//     state so a rotate, move, tick, lock, line clear, and restart each
//     trigger exactly one redraw (useGame produces a new GameState object per
//     applied change, so keying on `state` suffices).
//   - A `ResizeObserver` watches the canvas layout box and, only on a
//     MEANINGFUL resize (measured pixel width OR height changed from its
//     previous value), recomputes the backing store as
//     `round(cssW * dpr)` by `round(cssH * dpr)`, resets the transform,
//     re-applies the DPR scale, and redraws.

import { useEffect, useRef } from "react";
import type { GameState } from "./types";

const ROWS = 20;
const COLS = 10;

// Aspect ratio of the board (width : height). The CSS box is driven by the
// real responsive layout (see the `aspect-ratio` style below); the measured
// content box is what the ResizeObserver reports and what sizes the backing
// store. There is intentionally no fixed pixel geometry here: a fixed-size
// canvas could never receive a meaningful content-box resize.
const BOARD_ASPECT = `${COLS} / ${ROWS}`;

// Fallback CSS dimensions used only when the layout box cannot be measured
// (e.g. ResizeObserver unavailable, or a zero initial measurement in a
// non-layout test environment). These preserve the inherited 24px cell
// footprint so the board still renders at a sensible size.
const FALLBACK_CELL_PX = 24;
const FALLBACK_CSS_WIDTH = FALLBACK_CELL_PX * COLS;
const FALLBACK_CSS_HEIGHT = FALLBACK_CELL_PX * ROWS;

// Inherited per-type colors preserved from Board.tsx as the Canvas palette.
// Index 0 (empty) is the board background color; codes 1..7 are type colors.
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

export interface CanvasBoardProps {
  state: GameState;
}

// Pure drawing routine. Draws the authoritative board for a single frame.
//
// `cssWidth`/`cssHeight` are the logical (CSS-pixel) dimensions of the board,
// and `dpr` is the device pixel ratio. The backing store is assumed to be
// sized `round(cssWidth * dpr)` by `round(cssHeight * dpr)` by the caller;
// this routine owns the per-frame reset, clear, and scale so no residual
// pixels from a prior state survive and the scale never compounds across
// redraws.
export function draw(
  ctx: CanvasRenderingContext2D,
  state: GameState,
  cssWidth: number,
  cssHeight: number,
  dpr: number,
): void {
  // 1) Reset the transform to identity so a prior frame's scale never
  //    compounds across redraws.
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  // 2) Clear the ENTIRE backing store (in device pixels, under the identity
  //    transform) so no residual pixels from a prior state survive.
  const backingWidth = Math.round(cssWidth * dpr);
  const backingHeight = Math.round(cssHeight * dpr);
  ctx.clearRect(0, 0, backingWidth, backingHeight);

  // 3) Re-apply the DPR scale so one logical cell maps to the same CSS area
  //    regardless of DPR. After this, all drawing uses CSS-pixel coordinates.
  ctx.scale(dpr, dpr);

  const cellW = cssWidth / COLS;
  const cellH = cssHeight / ROWS;

  // Draw exactly the 200 settled cells. Code 0 draws the background color so
  // the whole board area is painted (empty cells are visible background), and
  // codes 1..7 draw their inherited per-type color.
  for (let r = 0; r < ROWS; r += 1) {
    const row = state.board[r] ?? [];
    for (let c = 0; c < COLS; c += 1) {
      const code = row[c] ?? 0;
      ctx.fillStyle = COLORS[code] ?? COLORS[0];
      ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
    }
  }

  // Overlay the active piece's rotated occupied cells at its current origin in
  // its type color so active and settled blocks are visually distinguishable.
  const active = state.active_piece;
  if (active) {
    const code = TYPE_CODE[active.type] ?? 0;
    ctx.fillStyle = COLORS[code] ?? COLORS[0];
    for (const [r, c] of active.cells) {
      if (r >= 0 && r < ROWS && c >= 0 && c < COLS) {
        ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
      }
    }
  }
}

// Resolve the CSS (logical) size of the board from a measured layout box,
// falling back to the inherited footprint when the measurement is unusable
// (zero or non-finite, as can happen before first layout or in a non-layout
// test environment).
function resolveCssSize(measuredWidth: number, measuredHeight: number): {
  cssWidth: number;
  cssHeight: number;
} {
  const cssWidth =
    Number.isFinite(measuredWidth) && measuredWidth > 0
      ? measuredWidth
      : FALLBACK_CSS_WIDTH;
  const cssHeight =
    Number.isFinite(measuredHeight) && measuredHeight > 0
      ? measuredHeight
      : FALLBACK_CSS_HEIGHT;
  return { cssWidth, cssHeight };
}

// Size the backing store from the CSS size and DPR, then draw. The CSS box is
// left to the layout (the `style` width/height stay at 100%); only the backing
// store (`canvas.width` / `canvas.height`) is recomputed here so the board is
// crisp at DPR 1 and DPR 2 without stretching or clipping.
function sizeAndDraw(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  state: GameState,
  cssWidth: number,
  cssHeight: number,
): void {
  const dpr =
    typeof window !== "undefined" && Number.isFinite(window.devicePixelRatio)
      ? window.devicePixelRatio
      : 1;
  const effectiveDpr = dpr > 0 ? dpr : 1;

  const backingWidth = Math.round(cssWidth * effectiveDpr);
  const backingHeight = Math.round(cssHeight * effectiveDpr);

  // Only assign when changed to avoid needless backing-store reallocation
  // (assigning canvas.width/height clears the surface even with the same
  // value). The values equal rounded actual CSS content dimensions * DPR.
  if (canvas.width !== backingWidth) {
    canvas.width = backingWidth;
  }
  if (canvas.height !== backingHeight) {
    canvas.height = backingHeight;
  }

  draw(ctx, state, cssWidth, cssHeight, effectiveDpr);
}

export function CanvasBoard({ state }: CanvasBoardProps) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  // Latest authoritative state, read by the ResizeObserver callback so a
  // resize always redraws from the current state (not the state captured when
  // the observer was created).
  const stateRef = useRef<GameState>(state);
  stateRef.current = state;

  // Previously measured content-box pixel size. Used to distinguish a
  // MEANINGFUL resize (width or height changed) from an unchanged
  // ResizeObserver event so a fixed-size canvas receiving an unchanged event
  // does not force a backing-store resize.
  const measuredRef = useRef<{ width: number; height: number } | null>(null);

  // Set to true on unmount so no queued ResizeObserver callback draws after
  // the component has been torn down (no after-unmount draw).
  const unmountedRef = useRef(false);

  // Redraw on every authoritative state change. useGame produces a new
  // GameState object per applied change (rotate, move, tick, lock, line clear,
  // restart), so keying this effect on `state` yields exactly one redraw per
  // applied change. This effect also performs the initial draw on mount.
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    // Null 2D context is handled safely: the canvas element still renders and
    // drawing is skipped without throwing.
    if (!ctx) {
      return;
    }

    // Use the last measured layout box when available; otherwise measure now
    // (getBoundingClientRect), and fall back to the inherited footprint if the
    // measurement is unusable.
    const measured = measuredRef.current;
    let cssWidth: number;
    let cssHeight: number;
    if (measured) {
      ({ cssWidth, cssHeight } = resolveCssSize(measured.width, measured.height));
    } else {
      const rect = canvas.getBoundingClientRect();
      ({ cssWidth, cssHeight } = resolveCssSize(rect.width, rect.height));
      measuredRef.current = { width: rect.width, height: rect.height };
    }

    sizeAndDraw(canvas, ctx, stateRef.current, cssWidth, cssHeight);
  }, [state]);

  // Subscribe to layout-box resizes. Separate from the state effect so the
  // observer is created once (on mount) and torn down once (on unmount),
  // independent of state churn.
  useEffect(() => {
    unmountedRef.current = false;
    const canvas = ref.current;

    // If ResizeObserver is unavailable in the environment, still draw from
    // state on every state change (the state effect above handles that) and
    // simply do not subscribe to resizes. Do not throw and do not fall back to
    // a DOM cell grid.
    if (!canvas || typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      // Guard against a callback that fires after unmount.
      if (unmountedRef.current) {
        return;
      }
      const currentCanvas = ref.current;
      if (!currentCanvas) {
        return;
      }
      const ctx = currentCanvas.getContext("2d");
      if (!ctx) {
        return;
      }

      // Read the measured content-box pixel size from the entry.
      const entry = entries[0];
      const measuredWidth = entry
        ? entry.contentRect.width
        : currentCanvas.getBoundingClientRect().width;
      const measuredHeight = entry
        ? entry.contentRect.height
        : currentCanvas.getBoundingClientRect().height;

      // MEANINGFUL-resize guard: only act when the measured pixel width OR
      // height changed from its previously measured value. An unchanged
      // measurement must NOT force a resize-driven backing-store resize.
      const prev = measuredRef.current;
      if (
        prev &&
        prev.width === measuredWidth &&
        prev.height === measuredHeight
      ) {
        return;
      }
      measuredRef.current = { width: measuredWidth, height: measuredHeight };

      const { cssWidth, cssHeight } = resolveCssSize(
        measuredWidth,
        measuredHeight,
      );
      sizeAndDraw(currentCanvas, ctx, stateRef.current, cssWidth, cssHeight);
    });

    observer.observe(canvas);

    return () => {
      // On unmount: mark unmounted so no queued callback draws, and disconnect
      // the observer so it never fires again (no leaked observer, no
      // after-unmount draw).
      unmountedRef.current = true;
      observer.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="board"
      // The CSS box is driven by the responsive layout: the width fills the
      // available layout box and the height follows the board aspect ratio.
      // This makes the canvas able to receive a MEANINGFUL content-box resize
      // (it is not a fixed-pixel canvas that can never change size). The
      // backing store (canvas.width/height) is recomputed from the measured
      // box and DPR by the effects above.
      style={{
        width: "100%",
        maxWidth: `${FALLBACK_CELL_PX * COLS}px`,
        aspectRatio: BOARD_ASPECT,
        display: "block",
      }}
      role="img"
      aria-label="Tetris board"
    />
  );
}
