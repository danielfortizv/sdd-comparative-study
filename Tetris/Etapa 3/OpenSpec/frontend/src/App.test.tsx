import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import type { GameState } from "./api";

const api = vi.hoisted(() => ({
  createGame: vi.fn(),
  moveGame: vi.fn(),
  tickGame: vi.fn(),
  holdGame: vi.fn(),
  getHighScores: vi.fn(),
}));

vi.mock("./api", () => api);

function game(patch: Partial<GameState> = {}): GameState {
  return {
    id: "test-session-1",
    board: Array.from({ length: 20 }, () => Array<string | null>(10).fill(null)),
    active_piece: { type: "O", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]] },
    status: "playing",
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "T",
    hold_piece: null,
    can_hold: true,
    ...patch,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

async function mount() {
  render(<App />);
  await waitFor(() => expect(screen.getByTestId("score-value").textContent).toBe("0"));
}

beforeEach(() => {
  vi.clearAllMocks();
  api.createGame.mockResolvedValue(game());
  api.tickGame.mockResolvedValue(game());
  api.holdGame.mockResolvedValue(game({ hold_piece: "O", can_hold: false, active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]] } }));
  api.getHighScores.mockResolvedValue({ scores: [] });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Stage 2 client coordination", () => {
  it("reschedules gravity when the authoritative level changes", async () => {
    vi.useFakeTimers();
    await act(async () => { render(<App />); await Promise.resolve(); });
    expect(screen.getByTestId("score-value").textContent).toBe("0");
    api.tickGame.mockResolvedValue(game({ score: 100, total_lines: 10, level: 2, gravity_interval_ms: 450 }));
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(api.tickGame).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("level-value").textContent).toBe("2");
    await act(async () => { await vi.advanceTimersByTimeAsync(449); });
    expect(api.tickGame).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(api.tickGame).toHaveBeenCalledTimes(2);
  });

  it("keeps the newer response when move requests complete out of order", async () => {
    await mount();
    const first = deferred<GameState>();
    const second = deferred<GameState>();
    api.moveGame.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(api.moveGame).toHaveBeenCalledTimes(2);
    await act(async () => { second.resolve(game({ score: 200 })); await second.promise; });
    expect(screen.getByTestId("score-value").textContent).toBe("200");
    await act(async () => { first.resolve(game({ score: 100 })); await first.promise; });
    expect(screen.getByTestId("score-value").textContent).toBe("200");
  });

  it("supports Hold by button and C key with the cooldown shown", async () => {
    await mount();
    fireEvent.click(screen.getByRole("button", { name: /HOLD PIECE/ }));
    await waitFor(() => expect(screen.getByTestId("hold-container").className).toContain("hold-cooldown"));
    expect(api.holdGame).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /HOLD PIECE/ }).hasAttribute("disabled")).toBe(true);

    api.createGame.mockResolvedValueOnce(game({ id: "test-session-2" }));
    fireEvent.click(screen.getByRole("button", { name: /RESTART GAME/ }));
    await waitFor(() => expect(screen.getByTestId("hold-container").className).not.toContain("hold-cooldown"));
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect(api.holdGame).toHaveBeenCalledTimes(2));
  });
});

describe("Stage 3 High Scores panel and API", () => {
  it("renders the empty state when there are no high scores", async () => {
    api.getHighScores.mockResolvedValueOnce({ scores: [] });
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("leaderboard-empty")).toBeDefined());
    expect(api.getHighScores).toHaveBeenCalledTimes(1);
  });

  it("renders the high scores list correctly", async () => {
    const mockScores = [
      { game_id: "g1", score: 5000, total_lines: 45, level: 5, completed_at: "2026-10-28T12:00:00Z" },
      { game_id: "g2", score: 3000, total_lines: 20, level: 3, completed_at: "2026-10-28T12:05:00Z" },
    ];
    api.getHighScores.mockResolvedValueOnce({ scores: mockScores });
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("leaderboard-list")).toBeDefined());
    expect(screen.getByText("5000")).toBeDefined();
    expect(screen.getByText("3000")).toBeDefined();
    expect(screen.getByText("Lines: 45")).toBeDefined();
    expect(screen.getByText("Lv: 5")).toBeDefined();
  });

  it("renders the error state when leaderboard fetch fails", async () => {
    api.getHighScores.mockRejectedValueOnce(new Error("Failed to fetch"));
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("leaderboard-error")).toBeDefined());
    expect(screen.getByText("Storage service unavailable")).toBeDefined();
  });

  it("refetches high scores immediately on game over", async () => {
    // 1. Mount with real timers first to let initialization finish cleanly
    render(<App />);
    await waitFor(() => expect(api.getHighScores).toHaveBeenCalledTimes(1));

    // 2. Switch to fake timers
    vi.useFakeTimers();
    api.tickGame.mockResolvedValueOnce(game({ status: "game_over" }));
    
    // 3. Advance timers by gravity interval to trigger the tickGame action
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    // 4. Restore real timers before calling waitFor so it runs without timeout clashing
    vi.useRealTimers();
    await waitFor(() => expect(api.getHighScores).toHaveBeenCalledTimes(2));
  });
});
