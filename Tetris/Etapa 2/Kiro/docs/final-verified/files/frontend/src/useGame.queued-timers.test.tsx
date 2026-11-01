// R4 / R5 queued-manual gravity-timeout tests (Requirements 16.25-16.31, 18.17).
//
// These tests drive the REAL `useGame` hook and the REAL `api` client. Nothing
// in the hook or api module is mocked. Only the transport `fetch` is replaced
// with a controllable fake whose HEADERS (the fetch promise) and BODY
// (`response.json()`) resolve INDEPENDENTLY. Fake timers force the precise
// automatic-tick gravity boundary.
//
// Shared scenario for both defects: two manual mutating operations are already
// QUEUED in FIFO order before either completes. The predecessor completes at
// t0 with gravity_interval_ms 500 and schedules a gravity timeout; the second
// manual operation completes at t100. The fix must reconcile the exact pending
// gravity timeout against the SECOND (fresh) authoritative result - replacing
// the predecessor's stale 500 ms timeout (R4) or cancelling it entirely on a
// terminal result (R5) - while preserving FIFO ordering and the one-owned-tick
// coalescing guard.

import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useGame } from "./useGame";
import type { GameState } from "./types";

interface Pending {
  url: string;
  method: string;
  resolveHeaders: (status?: number) => void;
  resolveBody: (body: GameState) => void;
}

function installFetch() {
  const pendings: Pending[] = [];

  const fetchImpl = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();

    let resolveHeadersFn!: (status: number) => void;
    const headersPromise = new Promise<number>((res) => {
      resolveHeadersFn = res;
    });

    let resolveBodyFn!: (body: GameState) => void;
    const bodyPromise = new Promise<GameState>((res) => {
      resolveBodyFn = res;
    });

    const fetchPromise = headersPromise.then((status) => {
      const response = {
        ok: status >= 200 && status < 300,
        status,
        json: () => bodyPromise,
      };
      return response as unknown as Response;
    });

    pendings.push({
      url,
      method,
      resolveHeaders: (status = 200) => resolveHeadersFn(status),
      resolveBody: (body) => resolveBodyFn(body),
    });

    return fetchPromise;
  });

  vi.stubGlobal("fetch", fetchImpl);

  return {
    pendings,
    last(matchUrl: string, method = "POST"): Pending {
      for (let i = pendings.length - 1; i >= 0; i--) {
        const p = pendings[i];
        if (p.url.includes(matchUrl) && p.method === method) return p;
      }
      throw new Error(`no pending ${method} request matching ${matchUrl}`);
    },
    count(matchUrl: string, method = "POST"): number {
      return pendings.filter((p) => p.url.includes(matchUrl) && p.method === method).length;
    },
  };
}

function makeState(overrides: Partial<GameState> = {}): GameState {
  return {
    id: "A",
    status: "playing",
    board: Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => 0)),
    active_piece: { type: "O", origin: [18, 3], cells: [[18, 3], [18, 4], [19, 3], [19, 4]] },
    score: 0,
    total_lines: 9,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "O",
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

async function flush() {
  await act(async () => {
    for (let n = 0; n < 16; n++) await Promise.resolve();
  });
}

async function complete(net: ReturnType<typeof installFetch>, p: Pending, body: GameState) {
  await act(async () => {
    p.resolveHeaders(200);
    await flush();
    p.resolveBody(body);
    await flush();
  });
}

// Load game A, then queue two manual ops (left, then down) BEFORE either
// completes, proving the second really waits for the first (FIFO). Complete the
// first at t0 with gravity_interval_ms 500, advance 100 ms, then complete the
// second with the supplied `second` snapshot.
async function queued(
  net: ReturnType<typeof installFetch>,
  sink: Harness,
  first: GameState,
  second: GameState,
) {
  // Resolve the initial mount create -> game A.
  await complete(net, net.last("/api/games"), makeState({ id: "A" }));
  expect(sink.current?.state?.id).toBe("A");

  // Cancel the automatic tick scheduled off the initial load so it cannot
  // interfere; the two manual dispatches below each cancel at dispatch time.
  act(() => {
    void sink.current!.move("left");
    void sink.current!.move("down");
  });
  await flush();

  // FIFO: only the first manual request is in flight; the second waits.
  expect(net.count("/api/games/A/move")).toBe(1);

  // Complete the predecessor (left) at t0 with the 500 ms state. This applies,
  // reconciles the timeout, and schedules a 500 ms gravity timeout.
  await complete(net, net.last("/api/games/A/move"), first);

  // Now the second manual request (down) is dispatched.
  expect(net.count("/api/games/A/move")).toBe(2);

  // Advance 100 ms (t100) with the second request still pending.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(100);
  });

  // Complete the second (down) at t100 with the fresh snapshot.
  await complete(net, net.last("/api/games/A/move"), second);
}

describe("useGame queued-manual gravity-timeout reconciliation (R4/R5)", () => {
  let net: ReturnType<typeof installFetch>;
  let sink: Harness;

  beforeEach(() => {
    vi.useFakeTimers();
    net = installFetch();
    sink = { current: null };
    render(<Probe sink={sink} />);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("R4: the second queued completion replaces the predecessor's timer with a fresh 450 ms period", async () => {
    const first = makeState({ id: "A", gravity_interval_ms: 500 });
    const second = makeState({
      id: "A",
      score: 100,
      total_lines: 10,
      level: 2,
      gravity_interval_ms: 450,
      next_piece: "I",
      active_piece: { type: "O", origin: [0, 3], cells: [[0, 3], [0, 4], [1, 3], [1, 4]] },
    });

    await queued(net, sink, first, second);
    expect(sink.current?.state?.gravity_interval_ms).toBe(450);

    // The predecessor's stale 500 ms deadline (relative to t0) is gone; the
    // fresh 450 ms period runs from t100. No tick before the full 450 ms.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(449);
    });
    expect(net.count("/api/games/A/tick")).toBe(0);

    // One more millisecond completes the fresh 450 ms period -> exactly one tick.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);
  });

  it("R5: the second queued game-over completion cancels the predecessor's timer (no tick after terminal)", async () => {
    const first = makeState({ id: "A", gravity_interval_ms: 500 });
    const second = makeState({
      id: "A",
      status: "game_over",
      score: 100,
      total_lines: 10,
      level: 2,
      gravity_interval_ms: 450,
      next_piece: "I",
      active_piece: null,
    });

    await queued(net, sink, first, second);
    expect(sink.current?.state?.status).toBe("game_over");

    // The predecessor's timer must have been cancelled; no tick fires after
    // terminal state no matter how far time advances.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(net.count("/api/games/A/tick")).toBe(0);
  });
});