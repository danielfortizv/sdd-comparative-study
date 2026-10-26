// Scheduling, ordering, and lifecycle tests for useGame (Requirements 15, 16).
// Assertions observe requests/state/timer timing, not implementation internals.
//
// Automatic ticks self-reschedule while playing, so tests either make the tick
// stay in flight (deferred) or return a game_over state to halt the loop; this
// keeps the fake-timer clock from looping indefinitely.

import { act, render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useGame } from "./useGame";
import type { Direction, GameState } from "./types";
import * as api from "./api";

function makeState(overrides: Partial<GameState> = {}): GameState {
  return {
    id: "g1",
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

interface Harness {
  current: ReturnType<typeof useGame> | null;
}

function Probe({ sink }: { sink: Harness }) {
  sink.current = useGame();
  return null;
}

function StrictProbe({ sink }: { sink: Harness }) {
  return (
    <StrictMode>
      <Probe sink={sink} />
    </StrictMode>
  );
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useGame scheduling and lifecycle", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  async function mountAndSettle(sink: Harness, strict = false) {
    render(strict ? <StrictProbe sink={sink} /> : <Probe sink={sink} />);
    // Flush the mount effect's create() microtasks.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  it("schedules automatic ticks using gravity_interval_ms, not a fixed 500", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ gravity_interval_ms: 300 }));
    // First tick stays in flight so no further ticks are scheduled.
    const d = deferred<GameState>();
    const tickSpy = vi.spyOn(api, "tickGame").mockReturnValue(d.promise);
    const sink: Harness = { current: null };
    await mountAndSettle(sink);
    expect(sink.current?.state?.gravity_interval_ms).toBe(300);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(299);
    });
    expect(tickSpy).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);
  });

  it("reschedules to the new interval when it changes (500 -> 450)", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ gravity_interval_ms: 500 }));
    const second = deferred<GameState>();
    const tickSpy = vi
      .spyOn(api, "tickGame")
      // First tick resolves with a leveled-up 450 ms state.
      .mockResolvedValueOnce(makeState({ gravity_interval_ms: 450, level: 2 }))
      // Second tick stays in flight to stop the loop.
      .mockReturnValue(second.promise);
    const sink: Harness = { current: null };
    await mountAndSettle(sink);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);
    expect(sink.current?.state?.gravity_interval_ms).toBe(450);

    // Next tick uses 450 ms: nothing at 449, fires at 450.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(449);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(tickSpy).toHaveBeenCalledTimes(2);
  });

  it("stops automatic ticks on game over", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    const tickSpy = vi
      .spyOn(api, "tickGame")
      .mockResolvedValue(makeState({ status: "game_over" }));
    const sink: Harness = { current: null };
    await mountAndSettle(sink);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);
  });

  it("coalesces ticks: a slow tick does not cause a burst", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    const d = deferred<GameState>();
    const tickSpy = vi
      .spyOn(api, "tickGame")
      .mockReturnValueOnce(d.promise)
      .mockReturnValue(deferred<GameState>().promise);
    const sink: Harness = { current: null };
    await mountAndSettle(sink);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);

    // While the first tick is in flight, time passing does not queue more.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(tickSpy).toHaveBeenCalledTimes(1);

    // Resolve the in-flight tick; exactly one next tick is scheduled.
    await act(async () => {
      d.resolve(makeState());
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickSpy).toHaveBeenCalledTimes(2);
  });

  it("serializes manual actions FIFO within a generation", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    vi.spyOn(api, "tickGame").mockReturnValue(deferred<GameState>().promise);
    const order: Direction[] = [];
    vi.spyOn(api, "moveGame").mockImplementation(async (_id, dir) => {
      order.push(dir);
      return makeState();
    });
    const sink: Harness = { current: null };
    await mountAndSettle(sink);

    await act(async () => {
      void sink.current!.move("left");
      void sink.current!.move("right");
      void sink.current!.move("down");
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(order).toEqual(["left", "right", "down"]);
  });

  it("does not apply a stale response from a previous generation after restart", async () => {
    const first = deferred<GameState>();
    const createSpy = vi
      .spyOn(api, "createGame")
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(makeState({ id: "g2", score: 42 }));
    vi.spyOn(api, "tickGame").mockReturnValue(deferred<GameState>().promise);
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Restart supersedes the first (still-pending) create.
    await act(async () => {
      void sink.current!.restart();
      await Promise.resolve();
      await Promise.resolve();
    });
    // Resolve the stale first create; it must not become the state.
    await act(async () => {
      first.resolve(makeState({ id: "g1", score: 999 }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(createSpy).toHaveBeenCalledTimes(2);
    expect(sink.current?.state?.id).toBe("g2");
    expect(sink.current?.state?.score).toBe(42);
  });

  it("lets a new game's action proceed while an old request is pending (old-vs-new)", async () => {
    vi.spyOn(api, "createGame")
      .mockResolvedValueOnce(makeState({ id: "g1" }))
      .mockResolvedValueOnce(makeState({ id: "g2" }));
    vi.spyOn(api, "tickGame").mockReturnValue(deferred<GameState>().promise);
    const oldHold = deferred<GameState>();
    const holdSpy = vi
      .spyOn(api, "holdGame")
      .mockReturnValueOnce(oldHold.promise) // old generation hold, pending
      .mockResolvedValueOnce(makeState({ id: "g2", hold_piece: "T" }));
    const sink: Harness = { current: null };
    await mountAndSettle(sink);
    expect(sink.current?.state?.id).toBe("g1");

    await act(async () => {
      void sink.current!.hold();
      await Promise.resolve();
    });
    expect(holdSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      await sink.current!.restart();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(sink.current?.state?.id).toBe("g2");

    await act(async () => {
      await sink.current!.hold();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(holdSpy).toHaveBeenCalledTimes(2);
    expect(sink.current?.state?.id).toBe("g2");
  });

  it("remains correct through StrictMode mount/cleanup/remount", async () => {
    const createSpy = vi.spyOn(api, "createGame").mockResolvedValue(makeState());
    vi.spyOn(api, "tickGame").mockReturnValue(deferred<GameState>().promise);
    const sink: Harness = { current: null };
    const { unmount } = render(<StrictProbe sink={sink} />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(createSpy).toHaveBeenCalled();
    expect(sink.current?.error).toBeNull();
    expect(sink.current?.state).not.toBeNull();

    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
  });
});
