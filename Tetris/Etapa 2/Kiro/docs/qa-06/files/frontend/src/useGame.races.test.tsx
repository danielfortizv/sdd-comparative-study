// R1 / R2 / R3 production-path race tests (Requirements 16.10-16.24, 18.16).
//
// These tests drive the REAL `useGame` hook and the REAL `api` client. Nothing
// in the hook or api module is mocked. Only the transport `fetch` is replaced
// with a controllable fake that resolves its HEADERS (the fetch promise) and
// its BODY (`response.json()`) INDEPENDENTLY, so a response can have its
// headers resolved while its JSON body is still pending - the exact boundary
// the production-hook races were observed at. Fake timers force the precise
// automatic-tick gravity boundary.
//
// Each test asserts an externally observable guarantee (visible state, the URL
// a request was sent to, or the number of in-flight transport calls), not any
// private hook internal.

import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useGame } from "./useGame";
import type { GameState } from "./types";

// ---- Controllable transport -------------------------------------------------

interface Pending {
  url: string;
  method: string;
  // Resolve the fetch() promise (headers available).
  resolveHeaders: (status?: number) => void;
  // Resolve response.json() (body available).
  resolveBody: (body: GameState) => void;
  // True once response.json() has actually been invoked by production code.
  jsonCalled: () => boolean;
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
    let jsonWasCalled = false;

    const fetchPromise = headersPromise.then((status) => {
      const response = {
        ok: status >= 200 && status < 300,
        status,
        json: () => {
          jsonWasCalled = true;
          return bodyPromise;
        },
      };
      return response as unknown as Response;
    });

    pendings.push({
      url,
      method,
      resolveHeaders: (status = 200) => resolveHeadersFn(status),
      resolveBody: (body) => resolveBodyFn(body),
      jsonCalled: () => jsonWasCalled,
    });

    return fetchPromise;
  });

  vi.stubGlobal("fetch", fetchImpl);

  return {
    fetchImpl,
    pendings,
    // Find the most recent pending request whose URL matches and method matches.
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
    active_piece: { type: "I", origin: [0, 3], cells: [[0, 3], [0, 4], [0, 5], [0, 6]] },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "O",
    hold_piece: null,
    can_hold: true,
    ...overrides,
  };
}

// Put the active I piece on a specific row so a test can observe row regression.
function stateAtRow(id: string, row: number, overrides: Partial<GameState> = {}): GameState {
  return makeState({
    id,
    active_piece: {
      type: "I",
      origin: [row, 3],
      cells: [[row, 3], [row, 4], [row, 5], [row, 6]],
    },
    ...overrides,
  });
}

interface Harness {
  current: ReturnType<typeof useGame> | null;
}

function Probe({ sink }: { sink: Harness }) {
  sink.current = useGame();
  return null;
}

async function flush() {
  // Flush microtasks so promise continuations in the hook run.
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("useGame production races (R1/R2/R3) at the real transport boundary", () => {
  let net: ReturnType<typeof installFetch>;

  beforeEach(() => {
    vi.useFakeTimers();
    net = installFetch();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  // --- R1 -------------------------------------------------------------------
  it("R1: a Hold triggered during a pending restart never targets the old game and never overwrites the new game", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Resolve the initial mount create -> game A, fully loaded.
    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(makeState({ id: "A" }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("A");

    // Begin restart for game B; keep its create pending (headers unresolved).
    await act(async () => {
      void sink.current!.restart();
      await flush();
    });
    const createB = net.last("/api/games");

    // Trigger Hold BEFORE B arrives. It must NOT dispatch against A's id.
    await act(async () => {
      void sink.current!.hold();
      await flush();
    });
    expect(net.count("/api/games/A/hold")).toBe(0);

    // Resolve creation B; visible game becomes B.
    await act(async () => {
      createB.resolveHeaders(200);
      await flush();
      createB.resolveBody(makeState({ id: "B", score: 7 }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("B");

    // There is no stale A Hold to resolve (it was never dispatched). The
    // visible identity stays B.
    expect(sink.current?.state?.id).toBe("B");
    expect(sink.current?.state?.score).toBe(7);
  });

  it("R1: a delayed game-A response resolving after restart never overwrites game B", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Load A.
    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(makeState({ id: "A" }));
      await flush();
    });

    // Dispatch a move on A but keep BOTH its headers and body pending.
    await act(async () => {
      void sink.current!.move("left");
      await flush();
    });
    const moveA = net.last("/api/games/A/move");

    // Restart to B and fully resolve it.
    await act(async () => {
      void sink.current!.restart();
      await flush();
      const createB = net.last("/api/games");
      createB.resolveHeaders(200);
      await flush();
      createB.resolveBody(makeState({ id: "B", score: 99 }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("B");

    // Now resolve the stale A move - headers first, then body. Neither may be
    // applied to game B (Req 16.12, 16.13).
    await act(async () => {
      moveA.resolveHeaders(200);
      await flush();
      moveA.resolveBody(makeState({ id: "A", score: -1 }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("B");
    expect(sink.current?.state?.score).toBe(99);
  });

  // --- R2 -------------------------------------------------------------------
  it("R2: an automatic tick does not bypass a pending manual request or reverse visible state", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Load A with the I piece at row 0, interval 500.
    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(stateAtRow("A", 0));
      await flush();
    });

    // Manual soft drop: resolve its HEADERS but keep its JSON body pending.
    await act(async () => {
      void sink.current!.move("down");
      await flush();
    });
    const manual = net.last("/api/games/A/move");
    await act(async () => {
      manual.resolveHeaders(200);
      await flush();
    });
    expect(manual.jsonCalled()).toBe(true); // body is pending, not yet resolved

    // Advance exactly 500 ms. A correct implementation cancelled the pending
    // tick at manual dispatch, so NO concurrent tick request is created.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/A/tick")).toBe(0);

    // Resolve the manual body at row 1. This is the authoritative visible row.
    await act(async () => {
      manual.resolveBody(stateAtRow("A", 1));
      await flush();
    });
    expect(sink.current?.state?.active_piece?.origin[0]).toBe(1);

    // After the manual mutation completes, exactly one next tick is scheduled.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);

    // Resolve that tick at row 2; state advances forward, never backward.
    await act(async () => {
      const tick = net.last("/api/games/A/tick");
      tick.resolveHeaders(200);
      await flush();
      tick.resolveBody(stateAtRow("A", 2));
      await flush();
    });
    expect(sink.current?.state?.active_piece?.origin[0]).toBe(2);
  });

  it("R2: interval transitions (500 -> 450) are honored with fresh timing after a mutation", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(makeState({ id: "A", gravity_interval_ms: 500 }));
      await flush();
    });

    // First automatic tick at 500 ms returns a leveled-up 450 ms state.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);
    await act(async () => {
      const t1 = net.last("/api/games/A/tick");
      t1.resolveHeaders(200);
      await flush();
      t1.resolveBody(makeState({ id: "A", level: 2, gravity_interval_ms: 450 }));
      await flush();
    });
    expect(sink.current?.state?.gravity_interval_ms).toBe(450);

    // The next tick must honor 450 ms: nothing at 449, exactly one at 450.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(449);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(net.count("/api/games/A/tick")).toBe(2);
  });

  // --- R3 -------------------------------------------------------------------
  it("R3: a manual completion does not clear an in-flight tick's guard (no second concurrent tick)", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Load A.
    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(stateAtRow("A", 0));
      await flush();
    });

    // Dispatch a manual left; keep its body pending. (Dispatch cancels the
    // currently pending tick timeout.)
    await act(async () => {
      void sink.current!.move("left");
      await flush();
    });
    const manual = net.last("/api/games/A/move");

    // Resolve the manual mutation fully at column 2. This completion must NOT
    // clear any automatic-tick guard, because no tick owns it yet.
    await act(async () => {
      manual.resolveHeaders(200);
      await flush();
      manual.resolveBody(
        makeState({
          id: "A",
          active_piece: { type: "I", origin: [0, 2], cells: [[0, 2], [0, 3], [0, 4], [0, 5]] },
        }),
      );
      await flush();
    });

    // One tick is scheduled post-mutation. Advance 500 ms -> exactly one tick.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);

    // Resolve ONLY the tick headers (its json body stays pending); the tick
    // still owns the coalescing guard.
    const tick1 = net.last("/api/games/A/tick");
    await act(async () => {
      tick1.resolveHeaders(200);
      await flush();
    });

    // Advance another 500 ms with the first tick body still unresolved. At most
    // one automatic tick may be in flight (Req 16.22): no second tick request.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/A/tick")).toBe(1);
  });

  it("R3: a stale previous-generation completion does not clear the current generation's guard or timer", async () => {
    const sink: Harness = { current: null };
    render(<Probe sink={sink} />);

    // Load A.
    await act(async () => {
      net.last("/api/games").resolveHeaders(200);
      await flush();
      net.last("/api/games").resolveBody(stateAtRow("A", 0));
      await flush();
    });

    // Start an automatic tick for A and resolve only its headers (body pending).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    const tickA = net.last("/api/games/A/tick");
    await act(async () => {
      tickA.resolveHeaders(200);
      await flush();
    });

    // Restart to B (new generation) and fully load B.
    await act(async () => {
      void sink.current!.restart();
      await flush();
      const createB = net.last("/api/games");
      createB.resolveHeaders(200);
      await flush();
      createB.resolveBody(makeState({ id: "B", gravity_interval_ms: 500 }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("B");

    const tickCountBeforeStale = net.count("/api/games/A/tick");

    // Now resolve the stale A tick body. It must not touch B's state, guard,
    // or timer (Req 16.24). B's own scheduling keeps working.
    await act(async () => {
      tickA.resolveBody(stateAtRow("A", 1, { id: "A" }));
      await flush();
    });
    expect(sink.current?.state?.id).toBe("B");
    // No extra A tick was spawned by the stale completion.
    expect(net.count("/api/games/A/tick")).toBe(tickCountBeforeStale);

    // B still schedules its single next tick at its interval.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(net.count("/api/games/B/tick")).toBe(1);
  });
});
