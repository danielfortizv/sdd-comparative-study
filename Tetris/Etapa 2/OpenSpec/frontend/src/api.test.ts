import { afterEach, describe, expect, it, vi } from "vitest";
import { createGame, getGame, holdGame, moveGame, tickGame } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("Stage 2 API client", () => {
  it("sends the expected routes and parses successful JSON responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: "game-1" }) });
    vi.stubGlobal("fetch", fetchMock);
    await createGame();
    await getGame("game-1");
    await moveGame("game-1", "left");
    await tickGame("game-1");
    await holdGame("game-1");
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "http://localhost:8000/api/games",
      "http://localhost:8000/api/games/game-1",
      "http://localhost:8000/api/games/game-1/move",
      "http://localhost:8000/api/games/game-1/tick",
      "http://localhost:8000/api/games/game-1/hold",
    ]);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({ direction: "left" });
  });

  it("surfaces HTTP errors instead of returning an invalid game state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    await expect(createGame()).rejects.toThrow("Failed to create game");
    await expect(getGame("x")).rejects.toThrow("Failed to fetch game state");
    await expect(moveGame("x", "down")).rejects.toThrow("Failed to execute move");
    await expect(tickGame("x")).rejects.toThrow("Failed to tick game");
    await expect(holdGame("x")).rejects.toThrow("Failed to execute hold");
  });
});
