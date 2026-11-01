// Board rendering tests: overlays the active piece onto the settled grid.

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

describe("Board", () => {
  it("renders a 20x10 grid of cells", () => {
    const { container } = render(<Board state={baseState()} />);
    const board = container.querySelector(".board");
    expect(board?.children.length).toBe(200);
  });

  it("renders with a null active piece (settled board only)", () => {
    const state = baseState();
    state.active_piece = null;
    state.board[19][0] = 1;
    const { container } = render(<Board state={state} />);
    expect(container.querySelector(".board")?.children.length).toBe(200);
  });
});
