// Stage 3: configurable API base and getHighScores client tests (Req 10.1, 10.2).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getHighScores, createGame } from "./api";

describe("api base and high-scores client", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  function mockFetch(payload: unknown, ok = true, status = 200) {
    const fn = vi.fn(async () => ({ ok, status, json: async () => payload }));
    vi.stubGlobal("fetch", fn);
    return fn;
  }

  it("defaults to the same-origin /api base and never hardcodes localhost", async () => {
    const f = mockFetch({ scores: [] });
    await getHighScores();
    const url = f.mock.calls[0][0] as string;
    expect(url).toBe("/api/high-scores");
    expect(url).not.toContain("localhost");
    expect(url).not.toContain("http://");
  });

  it("game calls are rebased onto the same /api prefix", async () => {
    const f = mockFetch({ id: "g", status: "playing", board: [], active_piece: null, score: 0, total_lines: 0, level: 1, gravity_interval_ms: 500, next_piece: "I", hold_piece: null, can_hold: true });
    await createGame();
    const url = f.mock.calls[0][0] as string;
    expect(url).toBe("/api/games");
    expect(url).not.toContain("localhost");
  });

  it("getHighScores throws on a non-ok response", async () => {
    mockFetch({}, false, 503);
    await expect(getHighScores()).rejects.toThrow("status 503");
  });
});
