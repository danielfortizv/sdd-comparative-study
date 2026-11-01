// React hook owning game state, generation-scoped request ordering, and a
// coalesced dynamic-interval gravity scheduler.
//
// Design goals (Stage 2, Requirements 15 and 16):
//  - Schedule automatic ticks from the backend `gravity_interval_ms`, not a
//    fixed constant, and reschedule when the interval changes.
//  - Never apply a stale response (from a previous game generation) that would
//    reverse the visible state; validate the generation both after `fetch`
//    resolves and after `response.json()` resolves.
//  - Serialize manual mutating requests FIFO per generation; isolate queues
//    across generations so a new game's actions are never blocked by an old
//    game's pending request.
//  - Coalesce automatic ticks to at most one queued/in-flight tick so ticks do
//    not burst after a slow network call.
//  - Cancel the exact pending tick timeout on manual input, restart, interval
//    change, game over, and unmount; remain correct under React StrictMode's
//    mount -> unmount -> remount.

import { useCallback, useEffect, useRef, useState } from "react";

import { createGame, holdGame, moveGame, tickGame } from "./api";
import type { Direction, GameState } from "./types";

export interface UseGame {
  state: GameState | null;
  error: string | null;
  move: (direction: Direction) => Promise<void>;
  hold: () => Promise<void>;
  restart: () => Promise<void>;
}

export function useGame(): UseGame {
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Monotonic generation token. Bumped on every create/restart and on unmount
  // disposal. Every async op captures the generation at dispatch and compares
  // it against generationRef.current after each await.
  const generationRef = useRef(0);
  // Latest game id for the current generation.
  const idRef = useRef<string | null>(null);
  // Per-generation FIFO promise chain for manual mutating requests.
  const queueRef = useRef<Promise<unknown>>(Promise.resolve());
  // The single pending automatic-tick timeout handle for the current gen.
  const timeoutRef = useRef<number | null>(null);
  // Latest applied interval, used to (re)schedule the next tick.
  const intervalRef = useRef<number>(500);
  // Whether a tick is currently queued or in flight (coalescing guard).
  const tickBusyRef = useRef(false);

  // Cancel the exact pending tick timeout, if any.
  const cancelTick = useCallback(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Apply a state result only if it belongs to the current generation.
  const applyIfCurrent = useCallback((gen: number, next: GameState): boolean => {
    if (gen !== generationRef.current) {
      return false;
    }
    setState(next);
    intervalRef.current = next.gravity_interval_ms;
    return true;
  }, []);

  // Schedule a single automatic tick for `gen` using the latest interval.
  const scheduleTick = useCallback(
    (gen: number) => {
      // Only the current generation may schedule; never double-schedule.
      if (gen !== generationRef.current) return;
      if (timeoutRef.current !== null) return;
      if (tickBusyRef.current) return;

      timeoutRef.current = window.setTimeout(() => {
        timeoutRef.current = null;
        const id = idRef.current;
        if (gen !== generationRef.current || !id) return;
        tickBusyRef.current = true;
        tickGame(id)
          .then((next) => {
            // Guard after fetch+json resolves; stale completions drop out and
            // must not clear the current guard/timer.
            if (gen !== generationRef.current) return;
            const applied = applyIfCurrent(gen, next);
            if (applied && next.status === "playing") {
              tickBusyRef.current = false;
              scheduleTick(gen);
            } else {
              tickBusyRef.current = false;
            }
          })
          .catch((e: Error) => {
            if (gen !== generationRef.current) return;
            tickBusyRef.current = false;
            setError(e.message);
          });
      }, intervalRef.current);
    },
    [applyIfCurrent],
  );

  // Enqueue a manual mutating request onto the current generation's FIFO chain.
  const enqueue = useCallback(
    (gen: number, run: () => Promise<GameState>) => {
      const task = queueRef.current
        .catch(() => undefined) // isolate failures so the chain keeps flowing
        .then(async () => {
          if (gen !== generationRef.current) return; // stale: drop before work
          try {
            const next = await run();
            if (gen !== generationRef.current) return; // stale after await
            // Manual input cancels the pending tick; reschedule off new state.
            cancelTick();
            tickBusyRef.current = false;
            const applied = applyIfCurrent(gen, next);
            if (applied && next.status === "playing") {
              scheduleTick(gen);
            }
          } catch (e) {
            if (gen !== generationRef.current) return; // stale error: ignore
            setError((e as Error).message);
          }
        });
      queueRef.current = task;
      return task;
    },
    [applyIfCurrent, cancelTick, scheduleTick],
  );

  const move = useCallback(
    async (direction: Direction) => {
      const gen = generationRef.current;
      const id = idRef.current;
      if (!id) return;
      await enqueue(gen, () => moveGame(id, direction));
    },
    [enqueue],
  );

  const hold = useCallback(async () => {
    const gen = generationRef.current;
    const id = idRef.current;
    if (!id) return;
    await enqueue(gen, () => holdGame(id));
  }, [enqueue]);

  const restart = useCallback(async () => {
    // Bump the generation first so any in-flight old request is abandoned and
    // cannot adopt the new id or block the new queue.
    const gen = ++generationRef.current;
    cancelTick();
    tickBusyRef.current = false;
    queueRef.current = Promise.resolve();
    try {
      const next = await createGame();
      if (gen !== generationRef.current) return; // superseded mid-flight
      idRef.current = next.id;
      setError(null);
      const applied = applyIfCurrent(gen, next);
      if (applied && next.status === "playing") {
        scheduleTick(gen);
      }
    } catch (e) {
      if (gen !== generationRef.current) return;
      setError((e as Error).message);
    }
  }, [applyIfCurrent, cancelTick, scheduleTick]);

  // Create the first game on mount; dispose (bump generation) on unmount so a
  // late response from this mount is discarded. StrictMode runs this twice.
  useEffect(() => {
    void restart();
    return () => {
      generationRef.current += 1; // invalidate this mount's generation
      cancelTick();
      tickBusyRef.current = false;
    };
  }, [restart, cancelTick]);

  return { state, error, move, hold, restart };
}
