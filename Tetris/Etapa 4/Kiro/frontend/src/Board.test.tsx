// Board rendering tests: overlays the active piece onto the settled grid.
//
// =============================================================================
// SUPERSEDED-BY-CANVAS NOTICE (Task 8.4, Req 14.5) — READ BEFORE TRUSTING THESE
// ASSERTIONS AS MAIN-BOARD COVERAGE.
// -----------------------------------------------------------------------------
// `Board.tsx` (the per-cell DOM grid these tests exercise) is NO LONGER the
// renderer of the MAIN game board. As of the M2 Canvas migration, `App.tsx`
// renders `<CanvasBoard state={state} />` (a real Canvas 2D surface), not the
// `Board` DOM grid. `Board.tsx` and this test file are RETAINED (not deleted)
// so the file still compiles and these assertions still run green against the
// component that remains on disk — but their role as MAIN-board coverage is
// intentionally SUPERSEDED. They are kept, not silently removed, so the
// supersession and its replacement mapping stay visible in source control.
//
// The two inherited DOM-cell assertions below and their exact Canvas semantic
// replacements (from design.md, "Superseded DOM-cell assertions and pixel
// evidence (Req 14.*)"):
//
//   (1) "renders a 20x10 grid of cells" — `.board` has exactly 200 children.
//       Covered: the board is drawn as 200 positioned cells.
//       Canvas replacement: the renderer issues one fill per board cell (200
//       cells) plus the active-piece overlay against the live 2D context —
//       covered by the BEHAVIORAL draw-call assertions in
//       `CanvasBoard.test.tsx` (counts of `fillRect`, the single `clearRect` /
//       `setTransform` / `scale`). The correct per-type COLORS at the correct
//       board POSITIONS are confirmed only by INDEPENDENT production-bundle
//       PIXEL evidence (Task 8.3 / the independent researcher, captured AFTER
//       this milestone closes), not by anything in this repo's test suite.
//
//   (2) "renders with a null active piece (settled board only)" — the same
//       200-child DOM grid with no active piece.
//       Covered: settled cells render with no active overlay.
//       Canvas replacement: with `active_piece === null` the renderer draws the
//       200 settled cells and issues NO active-piece overlay — covered by the
//       behavioral draw-call assertions in `CanvasBoard.test.tsx` plus the same
//       independent production-bundle pixel evidence.
//
// HONESTY BOUNDARY: the Canvas draw-call assertions are BEHAVIORAL ONLY. A spy
// recording that `fillRect` was called with some coordinates does NOT prove any
// pixel of any color was painted at any screen position. Pixel proof (correct
// per-type colors at correct positions) is EXCLUSIVELY the independent
// production-bundle pixel evidence of Task 8.3 and is NOT asserted here or in
// `CanvasBoard.test.tsx`. Nothing in this file may be cited as pixel evidence.
// =============================================================================

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Board } from "./Board";
import type { GameState } from "./types";

function baseState(): GameState {
  return {
    id: "g",
    status: "playing",
    board: Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => 0)),
    active_piece: { type: "O", origin: [0, 0], cells: [[0, 0], [0, 1], [1, 0], [1, 1]] },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
  };
}

describe("Board (SUPERSEDED as main-board coverage by the Canvas migration)", () => {
  // SUPERSEDED (Req 14.5): this assertion's main-board semantic coverage is
  // replaced by CanvasBoard's behavioral draw-call count (200 fills + overlay)
  // plus independent production-bundle pixel evidence (Task 8.3). It still runs
  // green here only because Board.tsx is retained on disk; App no longer uses it.
  it("renders a 20x10 grid of cells", () => {
    const { container } = render(<Board state={baseState()} />);
    const board = container.querySelector(".board");
    expect(board?.children.length).toBe(200);
  });

  // SUPERSEDED (Req 14.5): the "settled board only" (null active piece) coverage
  // is replaced by CanvasBoard drawing exactly 200 settled fills and NO overlay
  // when active_piece === null, confirmed for pixels by the same independent
  // production-bundle pixel evidence (Task 8.3).
  it("renders with a null active piece (settled board only)", () => {
    const state = baseState();
    state.active_piece = null;
    state.board[19][0] = 1;
    const { container } = render(<Board state={state} />);
    expect(container.querySelector(".board")?.children.length).toBe(200);
  });
});
