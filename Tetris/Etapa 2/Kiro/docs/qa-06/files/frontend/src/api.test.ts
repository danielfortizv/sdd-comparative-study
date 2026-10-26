// API client tests: verify URL, method, and error handling via a fetch mock.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createGame, getGame, holdGame, moveGame, tickGame } from "./api";
import type { GameState } from "./types";

function okState(): GameState {
  return {
    id: "g",
    status: "playing",
    board: [],
    active_piece: null,
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
  };
}

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetch(ok: boolean, status = 200) {
    const fn = vi.fn(async () => ({
      ok,
      status,
      json: async () => okState(),
    }));
    vi.stubGlobal("fetch", fn);
    return fn;
  }

  it("createGame posts to /api/games", async () => {
    const f = mockFetch(true);
    await createGame();
    expect(f).toHaveBeenCalledWith(expect.stringContaining("/api/games"), {
      method: "POST",
    });
  });

  it("getGame fetches the game by id", async () => {
    const f = mockFetch(true);
    await getGame("abc");
    expect(f).toHaveBeenCalledWith(expect.stringContaining("/api/games/abc"));
  });

  it("tickGame posts to the tick endpoint", async () => {
    const f = mockFetch(true);
    await tickGame("abc");
    expect(f).toHaveBeenCalledWith(
      expect.stringContaining("/api/games/abc/tick"),
      { method: "POST" },
    );
  });

  it("moveGame posts the direction body", async () => {
    const f = mockFetch(true);
    await moveGame("abc", "left");
    const call = f.mock.calls[0];
    expect(call[0]).toContain("/api/games/abc/move");
    expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({
      direction: "left",
    });
  });

  it("holdGame posts to the hold endpoint", async () => {
    const f = mockFetch(true);
    await holdGame("abc");
    expect(f).toHaveBeenCalledWith(
      expect.stringContaining("/api/games/abc/hold"),
      { method: "POST" },
    );
  });

  it("throws on a non-ok response", async () => {
    mockFetch(false, 404);
    await expect(getGame("missing")).rejects.toThrow("status 404");
  });
});
