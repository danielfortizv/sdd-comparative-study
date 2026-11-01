// React hook owning game state, generation-scoped request ordering, and a
// coalesced dynamic-interval gravity scheduler.
//
// Design goals (Stage 2, Requirements 15 and 16, including the R1/R2/R3
// production-race corrections in 16.10-16.24):
//  - Schedule automatic ticks from the backend `gravity_interval_ms`, not a
//    fixed constant, and reschedule when the interval changes (Req 15).
//  - Never apply a stale response (from a previous game generation) that would
//    reverse the visible state; validate the generation both after `fetch`
//    resolves and after `response.json()` resolves (Req 16.1, 16.4).
//  - R1: Invalidate the previous game identity IMMEDIATELY on create/restart
//    (clear `idRef` before the create request resolves) so a mutating action
//    triggered while creation is in flight cannot dispatch against the old
//    game's id under the new generation. Isolate the new generation's queue,
//    guard, and timer from the previous generation (Req 16.10-16.15).
//  - R2: Serialize ALL mutations - manual moves/holds AND automatic ticks -
//    through one per-generation FIFO queue, so an automatic tick can never
//    bypass pending manual work and reverse authoritative state. Cancel the
//    exact pending tick timeout at manual DISPATCH time, not after the manual
//    request completes (Req 16.16-16.20).
//  - R3: The automatic-tick coalescing guard is owned solely by the tick that
//    set it; a manual completion never clears it, and a stale (previous-gen)
//    completion never clears the current generation's guard or timer. At most
//    one automatic tick is queued or in flight per generation - no catch-up
//    bursts (Req 16.21-16.24).
//  - Remain correct under React StrictMode mount -> unmount -> remount, on
//    game over, and on unmount (Req 16.8, 16.9, 16.23).

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
  // Latest game id for the current generation. Set to null immediately when a
  // create/restart begins (R1) so no action dispatches against a stale id.
  const idRef = useRef<string | null>(null);
  // Per-generation FIFO promise chain serializing EVERY mutation (manual and
  // automatic ticks) in submission order (R2).
  const queueRef = useRef<Promise<unknown>>(Promise.resolve());
  // The single pending automatic-tick timeout handle for the current gen.
  const timeoutRef = useRef<number | null>(null);
  // Latest applied interval, used to (re)schedule the next tick.
  const intervalRef = useRef<number>(500);
  // Whether an automatic tick is currently queued or in flight (coalescing
  // guard). Owned exclusively by the automatic-tick path (R3): only the tick
  // that set it clears it; manual and stale completions must not touch it.
  const tickBusyRef = useRef(false);

  // Cancel the exact pending tick timeout, if any. Does NOT clear the
  // coalescing guard - guard ownership stays with the tick that holds it.
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
  // The tick body is enqueued onto the shared FIFO so it cannot bypass pending
  // manual work (R2). The coalescing guard (tickBusyRef) is taken when the tick
  // is enqueued and released only by this same tick path (R3).
  const scheduleTick = useCallback(
    (gen: number) => {
      // Only the current generation may schedule; never double-schedule and
      // never schedule a second tick while one is queued/in flight (R3/16.22).
      if (gen !== generationRef.current) return;
      if (timeoutRef.current !== null) return;
      if (tickBusyRef.current) return;

      timeoutRef.current = window.setTimeout(() => {
        timeoutRef.current = null;
        if (gen !== generationRef.current) return;
        // Take ownership of the coalescing guard for this automatic tick.
        tickBusyRef.current = true;

        const task = queueRef.current
          .catch(() => undefined) // isolate prior failures; keep the chain flowing
          .then(async () => {
            // Stale generation: release nothing of the current gen; just drop.
            if (gen !== generationRef.current) return;
            const id = idRef.current;
            if (!id) {
              // Identity was invalidated (e.g. restart in flight). Release the
              // guard we own for this generation and stop.
              if (gen === generationRef.current) tickBusyRef.current = false;
              return;
            }
            try {
              const next = await tickGame(id);
              // Re-validate after fetch + json resolves (Req 16.4).
              if (gen !== generationRef.current) return;
              const applied = applyIfCurrent(gen, next);
              // Release the guard we own, then (if still playing) schedule the
              // single next tick. Only this tick path clears tickBusyRef (R3).
              tickBusyRef.current = false;
              if (applied && next.status === "playing") {
                scheduleTick(gen);
              }
            } catch (e) {
              // Stale error must not clear the current gen's guard/timer (R3).
              if (gen !== generationRef.current) return;
              tickBusyRef.current = false;
              setError((e as Error).message);
            }
          });
        queueRef.current = task;
      }, intervalRef.current);
    },
    [applyIfCurrent],
  );

  // Enqueue a manual mutating request onto the current generation's FIFO chain.
  // The pending automatic tick timeout is cancelled at DISPATCH time (below in
  // move/hold), not here, so an automatic tick cannot fire between dispatch and
  // execution (R2/16.19).
  const enqueue = useCallback(
    (gen: number, run: (id: string) => Promise<GameState>) => {
      const task = queueRef.current
        .catch(() => undefined) // isolate failures so the chain keeps flowing
        .then(async () => {
          if (gen !== generationRef.current) return; // stale: drop before work
          const id = idRef.current;
          if (!id) return; // identity invalidated (R1): do not dispatch
          try {
            const next = await run(id);
            if (gen !== generationRef.current) return; // stale after await (R1)
            const applied = applyIfCurrent(gen, next);
            // A manual completion must NOT clear the automatic-tick guard (R3).
            // Reschedule the single automatic tick off the fresh state.
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
    [applyIfCurrent, scheduleTick],
  );

  const move = useCallback(
    async (direction: Direction) => {
      const gen = generationRef.current;
      if (!idRef.current) return;
      // Cancel the exact pending automatic tick at dispatch time (R2/16.19).
      cancelTick();
      await enqueue(gen, (id) => moveGame(id, direction));
    },
    [enqueue, cancelTick],
  );

  const hold = useCallback(async () => {
    const gen = generationRef.current;
    if (!idRef.current) return;
    cancelTick();
    await enqueue(gen, (id) => holdGame(id));
  }, [enqueue, cancelTick]);

  const restart = useCallback(async () => {
    // Bump the generation FIRST so any in-flight old request is abandoned and
    // cannot adopt the new id or block the new queue (R1/16.10, 16.14).
    const gen = ++generationRef.current;
    // Invalidate the previous game identity IMMEDIATELY, before create resolves,
    // so no action dispatches against the old id under the new gen (R1/16.10).
    idRef.current = null;
    cancelTick();
    // Release the coalescing guard and start a FRESH, isolated queue for the
    // new generation (R1/16.14, R3/16.23).
    tickBusyRef.current = false;
    queueRef.current = Promise.resolve();
    try {
      const next = await createGame();
      if (gen !== generationRef.current) return; // superseded mid-flight (R1)
      idRef.current = next.id;
      setError(null);
      const applied = applyIfCurrent(gen, next);
      if (applied && next.status === "playing") {
        scheduleTick(gen);
      }
    } catch (e) {
      // Surface the error for the current generation only; leave no orphan
      // timer or guard from the failed attempt (R1/16.15).
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
      idRef.current = null;
      cancelTick();
      tickBusyRef.current = false;
    };
  }, [restart, cancelTick]);

  return { state, error, move, hold, restart };
}