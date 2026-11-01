// React hook owning the game state and the fixed 500 ms gravity loop.

import { useCallback, useEffect, useRef, useState } from "react";

import { createGame, moveGame, tickGame } from "./api";
import type { Direction, GameState } from "./types";

// Fixed gravity interval in milliseconds while the game is playing.
export const GRAVITY_INTERVAL_MS = 500;

export interface UseGame {
  state: GameState | null;
  error: string | null;
  move: (direction: Direction) => Promise<void>;
  restart: () => Promise<void>;
}

export function useGame(): UseGame {
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Hold the latest game id for the interval callback without re-subscribing.
  const idRef = useRef<string | null>(null);

  const restart = useCallback(async () => {
    try {
      const next = await createGame();
      idRef.current = next.id;
      setState(next);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const move = useCallback(async (direction: Direction) => {
    if (!idRef.current) {
      return;
    }
    try {
      const next = await moveGame(idRef.current, direction);
      setState(next);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  // Create the first game on mount.
  useEffect(() => {
    void restart();
  }, [restart]);

  // Drive gravity: tick every 500 ms while playing; stop on game over.
  useEffect(() => {
    if (!state || state.status !== "playing") {
      return;
    }
    const timer = window.setInterval(() => {
      if (!idRef.current) {
        return;
      }
      tickGame(idRef.current)
        .then(setState)
        .catch((e: Error) => setError(e.message));
    }, GRAVITY_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [state?.status]);

  return { state, error, move, restart };
}
