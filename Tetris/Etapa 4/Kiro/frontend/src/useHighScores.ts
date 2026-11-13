// Isolated leaderboard-fetch hook (Stage 3).
//
// This hook is deliberately INDEPENDENT of the useGame generation/FIFO/tick
// machinery. It never touches the game queue, timers, or coalescing guard, so
// it cannot clear, block, or reschedule the automatic-tick scheduler or the
// manual FIFO queue (Req 9.4).
//
// Stale-response discipline (Req 9.3): the hook carries its OWN request
// generation counter. Each request captures the generation at start; the stale
// check is applied AFTER BOTH the fetch promise AND the awaited response.json()
// promise resolve, before any state is committed. A response whose captured
// generation no longer matches is discarded whether it resolved as a success
// OR as an error, so a stale error never overwrites a newer result. A cleanup
// path (restart, unmount, StrictMode teardown) bumps the generation so no
// in-flight response can commit after cleanup.
//
// Game-over refresh while the initial fetch is still pending (Req 8.6): the
// hook does NOT gate the refresh behind a naive in-flight boolean. Starting a
// refresh bumps the request generation, invalidating any still-pending request
// so the newer refresh is the one allowed to commit. The mandated game-over
// refresh therefore always runs and reflects the latest leaderboard.

import { useCallback, useEffect, useRef, useState } from "react";

import { getHighScores } from "./api";
import type { HighScoreEntry } from "./types";

export type HighScoresStatus = "loading" | "loaded" | "empty" | "error";

export interface UseHighScores {
  status: HighScoresStatus;
  entries: HighScoreEntry[];
  refresh: () => void;
  /**
   * Restart-ownership signal. Synchronously invalidates the current request
   * generation so any delayed `fetch` AND delayed `response.json()` captured
   * before the restart -- on the success, error, OR cleanup/`finally` path --
   * is discarded and cannot commit afterward, then fetches the current
   * leaderboard for the new game. It never touches the game FIFO/timers.
   */
  invalidate: () => void;
}

export function useHighScores(): UseHighScores {
  const [status, setStatus] = useState<HighScoresStatus>("loading");
  const [entries, setEntries] = useState<HighScoreEntry[]>([]);

  // Independent request-generation counter (NOT the game generation).
  const genRef = useRef(0);
  // True while the hook is mounted; cleanup flips it so late responses drop.
  const mountedRef = useRef(true);

  const load = useCallback(() => {
    // Bump the generation so any still-pending request becomes stale and the
    // newer request is the only one allowed to commit.
    const gen = ++genRef.current;
    setStatus("loading");

    void (async () => {
      try {
        const data = await getHighScores();
        // Stale check AFTER both fetch and json resolved.
        if (!mountedRef.current || gen !== genRef.current) return;
        const scores = data.scores ?? [];
        setEntries(scores);
        setStatus(scores.length === 0 ? "empty" : "loaded");
      } catch {
        // A stale error must not overwrite a newer result or current state.
        if (!mountedRef.current || gen !== genRef.current) return;
        setStatus("error");
      } finally {
        // The stale/cleanup guard above already prevents a superseded request
        // (bumped generation) from committing on ANY resolution path.
      }
    })();
  }, []);

  // Restart-ownership signal (Req 8.8, 8.9, 9.3). Bumping genRef here is
  // synchronous, so any request captured before the restart is already stale
  // when its delayed fetch/json resolves and is discarded on success, error,
  // and the cleanup path. Starting a fresh load reflects the current
  // leaderboard for the new game. This never touches the game FIFO/timers.
  const invalidate = useCallback(() => {
    load();
  }, [load]);

  // Fetch once on initial mount; invalidate the generation on cleanup so an
  // in-flight response cannot commit after unmount / StrictMode teardown.
  useEffect(() => {
    mountedRef.current = true;
    load();
    return () => {
      mountedRef.current = false;
      genRef.current += 1;
    };
  }, [load]);

  return { status, entries, refresh: load, invalidate };
}
