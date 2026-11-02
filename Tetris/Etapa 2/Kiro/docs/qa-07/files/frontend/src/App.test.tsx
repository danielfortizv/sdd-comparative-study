// Rendering and control tests (Requirements 13, 14, 17): score/lines/level,
// next preview, hold display, disabled Hold button per can_hold, C/c key and
// Hold button dispatch, preserved controls, and English visible text.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { GameState } from "./types";
import * as api from "./api";

function makeState(overrides: Partial<GameState> = {}): GameState {
  return {
    id: "game-1",
    status: "playing",
    board: Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => 0)),
    active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]] },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
    ...overrides,
  };
}

describe("App rendering and controls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders score, lines, and level from backend state", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(
      makeState({ score: 1200, total_lines: 13, level: 2 }),
    );
    render(<App />);
    expect(await screen.findByTestId("score")).toHaveTextContent("Score: 1200");
    expect(screen.getByTestId("lines")).toHaveTextContent("Lines: 13");
    expect(screen.getByTestId("level")).toHaveTextContent("Level: 2");
  });

  it("renders the next-piece preview from state", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ next_piece: "L" }));
    render(<App />);
    const next = await screen.findByTestId("preview-next-piece");
    expect(next).toHaveAttribute("aria-label", "Next piece: L");
  });

  it("shows an empty hold slot when hold_piece is null", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ hold_piece: null }));
    render(<App />);
    const hold = await screen.findByTestId("preview-hold-piece");
    expect(hold).toHaveAttribute("aria-label", "Hold piece: empty");
    expect(screen.getByText("Empty")).toBeInTheDocument();
  });

  it("shows the held piece when hold_piece is set", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ hold_piece: "Z" }));
    render(<App />);
    const hold = await screen.findByTestId("preview-hold-piece");
    expect(hold).toHaveAttribute("aria-label", "Hold piece: Z");
  });

  it("disables the Hold button when can_hold is false", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ can_hold: false }));
    render(<App />);
    await screen.findByTestId("score");
    expect(screen.getByRole("button", { name: "Hold" })).toBeDisabled();
  });

  it("enables the Hold button when can_hold is true and playing", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ can_hold: true }));
    render(<App />);
    await screen.findByTestId("score");
    expect(screen.getByRole("button", { name: "Hold" })).toBeEnabled();
  });

  it("dispatches a hold request when the Hold button is clicked", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    const holdSpy = vi
      .spyOn(api, "holdGame")
      .mockResolvedValue(makeState({ hold_piece: "T", can_hold: false }));
    render(<App />);
    await screen.findByTestId("score");
    fireEvent.click(screen.getByRole("button", { name: "Hold" }));
    await waitFor(() => expect(holdSpy).toHaveBeenCalledWith("game-1"));
  });

  it("dispatches a hold request on the C key and the c key", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    // Keep can_hold true so both key presses are allowed to dispatch.
    const holdSpy = vi
      .spyOn(api, "holdGame")
      .mockResolvedValue(makeState({ hold_piece: "T", can_hold: true }));
    render(<App />);
    await screen.findByTestId("score");
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect(holdSpy).toHaveBeenCalledTimes(1));
    fireEvent.keyDown(window, { key: "C" });
    await waitFor(() => expect(holdSpy).toHaveBeenCalledTimes(2));
  });

  it("does not dispatch hold via key when can_hold is false", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ can_hold: false }));
    const holdSpy = vi.spyOn(api, "holdGame").mockResolvedValue(makeState());
    render(<App />);
    await screen.findByTestId("score");
    fireEvent.keyDown(window, { key: "c" });
    await new Promise((r) => setTimeout(r, 10));
    expect(holdSpy).not.toHaveBeenCalled();
  });

  it("keeps the existing move controls working", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    const moveSpy = vi.spyOn(api, "moveGame").mockResolvedValue(makeState());
    render(<App />);
    await screen.findByTestId("score");
    fireEvent.click(screen.getByRole("button", { name: "Left" }));
    fireEvent.click(screen.getByRole("button", { name: "Right" }));
    fireEvent.click(screen.getByRole("button", { name: "Soft Drop" }));
    await waitFor(() => {
      expect(moveSpy).toHaveBeenCalledWith("game-1", "left");
      expect(moveSpy).toHaveBeenCalledWith("game-1", "right");
      expect(moveSpy).toHaveBeenCalledWith("game-1", "down");
    });
  });

  it("dispatches moves on arrow keys while playing", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    const moveSpy = vi.spyOn(api, "moveGame").mockResolvedValue(makeState());
    render(<App />);
    await screen.findByTestId("score");
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowDown" });
    await waitFor(() => {
      expect(moveSpy).toHaveBeenCalledWith("game-1", "left");
      expect(moveSpy).toHaveBeenCalledWith("game-1", "right");
      expect(moveSpy).toHaveBeenCalledWith("game-1", "down");
    });
  });

  it("ignores keyboard input after game over", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ status: "game_over" }));
    const moveSpy = vi.spyOn(api, "moveGame").mockResolvedValue(makeState());
    const holdSpy = vi.spyOn(api, "holdGame").mockResolvedValue(makeState());
    render(<App />);
    await screen.findByText("Game Over");
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "c" });
    await new Promise((r) => setTimeout(r, 10));
    expect(moveSpy).not.toHaveBeenCalled();
    expect(holdSpy).not.toHaveBeenCalled();
  });

  it("shows the Game Over message when status is game_over", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ status: "game_over" }));
    render(<App />);
    expect(await screen.findByText("Game Over")).toBeInTheDocument();
  });

  it("renders the Stage 2 title and English control hints", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    render(<App />);
    expect(await screen.findByText("Tetris - Stage 2")).toBeInTheDocument();
    expect(
      screen.getByText(/Use Left \/ Right arrows to move/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/C key \(or Hold button\) to hold/i)).toBeInTheDocument();
  });
});
