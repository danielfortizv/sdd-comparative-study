// Bootstrap / mount test for the production entry point `main.tsx`
// (Requirement 18.13). main.tsx is an executable production bootstrap, not test
// glue, so it stays in the coverage denominator and is covered by a real test
// rather than hidden behind an exclusion.
//
// Importing main.tsx executes its top-level `createRoot(...).render(...)`. We
// provide the `#root` element it expects and a resolvable `createGame` so the
// mount effect settles without network, then assert the app actually rendered.

import { act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { GameState } from "./types";

function baseState(): GameState {
  return {
    id: "boot",
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
  };
}

describe("main bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("mounts the App into the #root element without throwing", async () => {
    // Keep the mount effect's create() network-free and deterministic.
    const api = await import("./api");
    vi.spyOn(api, "createGame").mockResolvedValue(baseState());
    vi.spyOn(api, "tickGame").mockReturnValue(new Promise<GameState>(() => {}));

    const root = document.createElement("div");
    root.id = "root";
    document.body.appendChild(root);

    // Importing the module runs the production bootstrap; flush the initial
    // render + mount effect inside act so React state updates are applied.
    await act(async () => {
      await expect(import("./main")).resolves.toBeDefined();
      await Promise.resolve();
      await Promise.resolve();
    });

    // The app shell rendered into #root (Stage 2 heading is present).
    expect(root.textContent).toContain("Tetris - Stage 2");
  });
});
