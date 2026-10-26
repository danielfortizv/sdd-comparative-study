import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import type { GameState } from "./api";

const api = vi.hoisted(() => ({
  createGame: vi.fn(),
  moveGame: vi.fn(),
  tickGame: vi.fn(),
  holdGame: vi.fn(),
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
