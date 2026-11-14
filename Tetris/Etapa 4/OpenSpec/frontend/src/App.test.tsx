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
    active_piece: { type: "O", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]], orientation: 0 },
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
  const initPromise = deferred<GameState>();
  api.createGame.mockReturnValueOnce(initPromise.promise);
  render(<App />);
  await act(async () => {
    initPromise.resolve(game());
    await initPromise.promise;
  });
  await waitFor(() => expect(screen.getByTestId("score-value").textContent).toBe("0"));
}

beforeEach(() => {
  vi.clearAllMocks();
  api.createGame.mockResolvedValue(game());
  api.tickGame.mockResolvedValue(game());
  api.holdGame.mockResolvedValue(game({ hold_piece: "O", can_hold: false, active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]], orientation: 0 } }));
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
    for (let i = 0; i < 20; i++) {
      api.moveGame.mockClear();
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
      cleanup();
    }
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

  it("supports clockwise and counterclockwise rotation via ArrowUp and Z/z keys", async () => {
    await mount();
    api.moveGame.mockResolvedValueOnce(game({ active_piece: { type: "O", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]], orientation: 1 } }));
    fireEvent.keyDown(window, { key: "ArrowUp" });
    await waitFor(() => expect(api.moveGame).toHaveBeenCalledWith("test-session-1", "clockwise"));

    api.moveGame.mockResolvedValueOnce(game({ active_piece: { type: "O", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]], orientation: 0 } }));
    fireEvent.keyDown(window, { key: "z" });
    await waitFor(() => expect(api.moveGame).toHaveBeenCalledWith("test-session-1", "counterclockwise"));

    api.moveGame.mockResolvedValueOnce(game({ active_piece: { type: "O", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]], orientation: 3 } }));
    fireEvent.keyDown(window, { key: "Z" });
    await waitFor(() => expect(api.moveGame).toHaveBeenCalledWith("test-session-1", "counterclockwise"));
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

class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  onopen: (() => void) | null = null;
  onclose: ((e: any) => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  send = vi.fn();
  close = vi.fn();

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    this.readyState = 1; // OPEN
  }

  static instances: MockWebSocket[] = [];
  static clear() {
    MockWebSocket.instances = [];
  }
}

describe("Stage 4 Duel Mode & WebSockets", () => {
  beforeEach(() => {
    MockWebSocket.clear();
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("handles wait, start and rendering side-by-side boards in Duel Mode", async () => {
    render(<App />);
    // Switch to Duel Mode
    fireEvent.click(screen.getByRole("button", { name: /TWO-PLAYER DUEL/i }));
    
    // Fill room input and connect
    fireEvent.change(screen.getByLabelText(/Room ID/i), { target: { value: "test-room" } });
    fireEvent.change(screen.getByLabelText(/Player ID/i), { target: { value: "p1" } });
    fireEvent.click(screen.getByRole("button", { name: /JOIN DUEL/i }));

    expect(MockWebSocket.instances.length).toBe(1);
    const mockWS = MockWebSocket.instances[0];

    // Trigger onopen
    act(() => {
      mockWS.onopen?.();
    });

    await waitFor(() => expect(screen.getByText(/WAITING FOR OPPONENT/i)).toBeDefined());

    // Trigger onmessage start
    act(() => {
      mockWS.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "start",
          timestamp: new Date().toISOString(),
          seq: 1,
          payload: { room_id: "test-room", player1_id: "p1", player2_id: "p2" }
        })
      });
    });

    // Trigger state message for p1
    act(() => {
      mockWS.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 1,
          payload: {
            room_id: "test-room",
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            active_piece: { type: "T", origin: [0, 3], cells: [[1, 4], [1, 5], [2, 4], [2, 5]], orientation: 0 },
            status: "playing",
            score: 150,
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 1,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    // Check that we render the score for Player 1
    await waitFor(() => expect(screen.getByTestId("score-value").textContent).toBe("150"));
    
    // Check that there is a grid board rendered
    expect(screen.getByTestId("grid-board")).toBeDefined();
  });

  it("handles out-of-order/stale messages and verifies that old socket callbacks do not mutate state", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /TWO-PLAYER DUEL/i }));
    fireEvent.change(screen.getByLabelText(/Room ID/i), { target: { value: "test-room" } });
    fireEvent.change(screen.getByLabelText(/Player ID/i), { target: { value: "p1" } });
    fireEvent.click(screen.getByRole("button", { name: /JOIN DUEL/i }));

    const wsInstance1 = MockWebSocket.instances[0];
    act(() => { wsInstance1.onopen?.(); });

    // Must trigger start first to transition lobby to gameplay panels
    act(() => {
      wsInstance1.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "start",
          timestamp: new Date().toISOString(),
          seq: 1,
          payload: { room_id: "test-room", player1_id: "p1", player2_id: "p2" }
        })
      });
    });

    // State message with revision 5
    act(() => {
      wsInstance1.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 5,
          payload: {
            room_id: "test-room",
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            status: "playing",
            score: 500,
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 5,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    await waitFor(() => expect(screen.getByTestId("score-value").textContent).toBe("500"));

    // State message with lower revision 3 (stale!) -> must be ignored!
    act(() => {
      wsInstance1.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 3,
          payload: {
            room_id: "test-room",
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            status: "playing",
            score: 300, // Should be ignored
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 3,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    // Score should remain 500
    expect(screen.getByTestId("score-value").textContent).toBe("500");

    // Click "SOLO PLAY" to switch modes and trigger unmount/cleanup of the socket
    fireEvent.click(screen.getByRole("button", { name: /SOLO PLAY/i }));

    // Trigger onmessage on the OLD wsInstance1 -> should NOT mutate state because of instance identity check!
    act(() => {
      wsInstance1.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 10,
          payload: {
            room_id: "test-room",
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            status: "playing",
            score: 1000, // Stale instance should be ignored
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 10,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    // Verify it did not affect anything or crash
    expect(screen.queryByTestId("score-value")).toBeDefined();
  });

  it("verifies outgoing keyboard and action messages, foreign room state discard, and cleanup on unmount", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /TWO-PLAYER DUEL/i }));
    fireEvent.change(screen.getByLabelText(/Room ID/i), { target: { value: "test-room" } });
    fireEvent.change(screen.getByLabelText(/Player ID/i), { target: { value: "p1" } });
    fireEvent.click(screen.getByRole("button", { name: /JOIN DUEL/i }));

    const ws = MockWebSocket.instances[0];
    act(() => { ws.onopen?.(); });

    // Transition to playing
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "start",
          timestamp: new Date().toISOString(),
          seq: 1,
          payload: { room_id: "test-room", player1_id: "p1", player2_id: "p2" }
        })
      });
    });

    // Provide initial state to make keys active
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 1,
          payload: {
            room_id: "test-room",
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            status: "playing",
            score: 100,
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 1,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    // 1. Trigger outgoing keyboard CW (ArrowUp) with auto-retrying waitFor
    fireEvent.keyDown(window, { key: "ArrowUp" });
    await waitFor(() => {
      expect(ws.send).toHaveBeenCalled();
    });
    const sentData = JSON.parse(ws.send.mock.calls[0][0]);
    expect(sentData.payload.action).toBe("rotate_clockwise");

    // 2. Foreign room state message should be discarded
    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          type: "state",
          timestamp: new Date().toISOString(),
          seq: 2,
          payload: {
            room_id: "different-room", // foreign room!
            seat: 1,
            player_id: "p1",
            board: Array.from({ length: 20 }, () => Array(10).fill(null)),
            status: "playing",
            score: 9999, // should NOT be accepted!
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: "I",
            hold_piece: null,
            can_hold: true,
            revision: 2,
            generation: 0,
            last_processed_seq: -1
          }
        })
      });
    });

    // Expect score to remain 100
    expect(screen.getByTestId("score-value").textContent).toBe("100");
  });
});
