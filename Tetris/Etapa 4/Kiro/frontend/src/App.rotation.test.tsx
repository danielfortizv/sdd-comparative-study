// Real-event single-player rotation tests (Requirements 8.1, 8.2, 8.3, 8.4,
// 8.6, 9.8).
//
// Every rotation is exercised through a REAL DOM event (fireEvent.keyDown on
// window, fireEvent.click on the on-screen buttons) and asserted through the
// api.rotateGame spy, so rotation is never asserted solely through internal
// function calls.
//
// NOTE-04 correction (test-only; no product change): the keyboard cases no
// longer re-fire the key event inside waitFor until a dispatch is observed.
// Re-firing proved only that SOME event eventually dispatched, not that a
// SINGLE key-down yields exactly one request, so it could not establish
// Requirements 8.1 / 8.2. Instead each case now:
//   1. settles the initial async createGame state AND the passive keydown-
//      handler effect deterministically (await act + findByTestId("score"))
//      BEFORE firing any key, so the handler is registered against the settled
//      "playing" state and no init/effect race can swallow the first event;
//   2. isolates every API mock per case (createGame, rotateGame, AND
//      getHighScores) so no unrelated leaderboard / tick request can leak
//      across tests or race the rotateGame spy;
//   3. fires EXACTLY ONE real keyboard event OUTSIDE any waitFor / poll / retry
//      callback - the waitFor callbacks below only OBSERVE / ASSERT, never
//      dispatch;
//   4. asserts EXACTLY ONE new rotateGame call with the correct game id and
//      direction and awaits its async completion;
//   5. covers ArrowUp, lowercase z, and uppercase Z as INDEPENDENT cases, each
//      standing alone with its own fresh spy rather than reusing a satisfied
//      earlier assertion.

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { GameState } from "./types";
import * as api from "./api";

function makeState(overrides: Partial<GameState> = {}): GameState {
  return {
    id: "game-1",
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

// Render App with the initial createGame resolved AND passive effects (the
// window keydown-handler effect) flushed, so a single real key event dispatched
// afterwards is observed by a handler bound to the settled "playing" state.
// getHighScores is mocked here so the independent leaderboard fetch cannot leak
// a pending/real request into the rotation assertions.
async function renderSettledPlaying(
  stateOverrides: Partial<GameState> = {},
): Promise<ReturnType<typeof vi.spyOn>> {
  vi.spyOn(api, "createGame").mockResolvedValue(makeState(stateOverrides));
  vi.spyOn(api, "getHighScores").mockResolvedValue({ scores: [] });
  const rotateSpy = vi.spyOn(api, "rotateGame").mockResolvedValue(makeState(stateOverrides));

  await act(async () => {
    render(<App />);
  });
  // The score panel only renders once the initial game state is applied; its
  // presence confirms the keydown-handler effect has run against "playing".
  await screen.findByTestId("score");
  return rotateSpy;
}

describe("App single-player rotation controls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("dispatches exactly one clockwise rotation on a single real ArrowUp key event", async () => {
    const rotateSpy = await renderSettledPlaying();

    // Exactly ONE real key event, fired OUTSIDE any waitFor/retry callback.
    fireEvent.keyDown(window, { key: "ArrowUp" });

    // waitFor only OBSERVES the async dispatch; it never fires the event.
    await waitFor(() => expect(rotateSpy).toHaveBeenCalledTimes(1));
    expect(rotateSpy).toHaveBeenCalledWith("game-1", "cw");
    // Await the async completion so no dangling microtask leaks into the next
    // test and the single-request guarantee is verified after settling.
    await act(async () => {
      await Promise.resolve();
    });
    expect(rotateSpy).toHaveBeenCalledTimes(1);
  });

  it("dispatches exactly one counter-clockwise rotation on a single real lowercase z key event", async () => {
    const rotateSpy = await renderSettledPlaying();

    fireEvent.keyDown(window, { key: "z" });

    await waitFor(() => expect(rotateSpy).toHaveBeenCalledTimes(1));
    expect(rotateSpy).toHaveBeenCalledWith("game-1", "ccw");
    await act(async () => {
      await Promise.resolve();
    });
    expect(rotateSpy).toHaveBeenCalledTimes(1);
  });

  it("dispatches exactly one counter-clockwise rotation on a single real uppercase Z key event", async () => {
    // Independent case with its OWN fresh spy; it does NOT reuse the lowercase
    // z assertion. This is the only key event fired in this test.
    const rotateSpy = await renderSettledPlaying();

    fireEvent.keyDown(window, { key: "Z" });

    await waitFor(() => expect(rotateSpy).toHaveBeenCalledTimes(1));
    expect(rotateSpy).toHaveBeenCalledWith("game-1", "ccw");
    await act(async () => {
      await Promise.resolve();
    });
    expect(rotateSpy).toHaveBeenCalledTimes(1);
  });

  it("dispatches exactly one clockwise rotation when the on-screen CW button is clicked once", async () => {
    const rotateSpy = await renderSettledPlaying();

    fireEvent.click(screen.getByRole("button", { name: /Rotate clockwise/i }));

    await waitFor(() => expect(rotateSpy).toHaveBeenCalledTimes(1));
    expect(rotateSpy).toHaveBeenCalledWith("game-1", "cw");
    await act(async () => {
      await Promise.resolve();
    });
    expect(rotateSpy).toHaveBeenCalledTimes(1);
  });

  it("dispatches exactly one counter-clockwise rotation when the on-screen CCW button is clicked once", async () => {
    const rotateSpy = await renderSettledPlaying();

    fireEvent.click(
      screen.getByRole("button", { name: /Rotate counter-clockwise/i }),
    );

    await waitFor(() => expect(rotateSpy).toHaveBeenCalledTimes(1));
    expect(rotateSpy).toHaveBeenCalledWith("game-1", "ccw");
    await act(async () => {
      await Promise.resolve();
    });
    expect(rotateSpy).toHaveBeenCalledTimes(1);
  });

  it("issues no rotation from any entry point when the status is not playing", async () => {
    vi.spyOn(api, "createGame").mockResolvedValue(makeState({ status: "game_over" }));
    vi.spyOn(api, "getHighScores").mockResolvedValue({ scores: [] });
    const rotateSpy = vi.spyOn(api, "rotateGame").mockResolvedValue(makeState());
    await act(async () => {
      render(<App />);
    });
    await screen.findByText("Game Over");

    // Keyboard entry points: ArrowUp (cw) and z (ccw) must not dispatch.
    fireEvent.keyDown(window, { key: "ArrowUp" });
    fireEvent.keyDown(window, { key: "z" });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });
    expect(rotateSpy).not.toHaveBeenCalled();

    // On-screen rotation buttons must be disabled when not playing, so a click
    // cannot dispatch a rotation.
    expect(
      screen.getByRole("button", { name: /Rotate clockwise/i }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /Rotate counter-clockwise/i }),
    ).toBeDisabled();
  });

  it("exposes both rotation buttons as accessible, enabled controls while playing", async () => {
    await renderSettledPlaying();

    const cwButton = screen.getByRole("button", { name: /Rotate clockwise/i });
    const ccwButton = screen.getByRole("button", {
      name: /Rotate counter-clockwise/i,
    });

    expect(cwButton).toBeInTheDocument();
    expect(ccwButton).toBeInTheDocument();
    expect(cwButton).toBeEnabled();
    expect(ccwButton).toBeEnabled();
  });
});
