import { useState, useEffect, useRef, useCallback } from 'react';
import { GameSession } from '../types';

export function useGame() {
  const [game, setGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generation of the restart/start requests
  const generationRef = useRef<number>(0);
  // The generation of the currently active/loaded game session
  const activeGenerationRef = useRef<number>(0);

  const requestSeqRef = useRef<number>(0);
  const appliedSeqRef = useRef<number>(0);

  const gameRef = useRef<GameSession | null>(null);
  useEffect(() => {
    gameRef.current = game;
  }, [game]);

  const disposedRef = useRef<boolean>(false);
  useEffect(() => {
    disposedRef.current = false;
    return () => {
      disposedRef.current = true;
    };
  }, []);

  const isTickPendingRef = useRef<boolean>(false);

  // Map of synchronous/promise-based queues to serialize mutations by generation
  const mutationQueuesRef = useRef<Map<number, Promise<any>>>(new Map());

  // Handle a successful response from a game mutation/status query
  const processResponse = useCallback((data: GameSession, seq: number, gen: number) => {
    if (disposedRef.current) {
      return;
    }
    // Only process if this matches the current active generation
    if (gen !== generationRef.current || gen !== activeGenerationRef.current) {
      return;
    }
    if (seq < appliedSeqRef.current) {
      return;
    }
    appliedSeqRef.current = seq;
    setGame(data);
    gameRef.current = data;
  }, []);

  const startGame = async () => {
    const thisGen = ++generationRef.current;
    setLoading(true);
    setError(null);
    isTickPendingRef.current = false;

    // Cancel old timer immediately by clearing game state
    setGame(null);
    gameRef.current = null;

    // Initialize the queue for this generation immediately
    mutationQueuesRef.current.set(thisGen, Promise.resolve());

    try {
      const res = await fetch('/api/games', { method: 'POST' });
      if (disposedRef.current) return;
      if (thisGen !== generationRef.current) {
        // Stale start: a newer start is already pending! Discard.
        return;
      }
      if (!res.ok) throw new Error('Failed to start game');
      const data: GameSession = await res.json();
      
      if (disposedRef.current) return;
      if (thisGen !== generationRef.current) {
        // Stale start: a newer start is already pending! Discard.
        return;
      }

      // Setup successful generation
      activeGenerationRef.current = thisGen;
      // Keep requestSeqRef monotonically increasing; do not reset it here.
      setGame(data);
      gameRef.current = data;
    } catch (err: any) {
      if (disposedRef.current) return;
      if (thisGen === generationRef.current) {
        setError(err.message || 'An error occurred');
      }
    } finally {
      if (disposedRef.current) return;
      if (thisGen === generationRef.current) {
        setLoading(false);
      }
    }
  };

  const executeMutation = useCallback((action: string, method: string = 'POST', body: any = null) => {
    if (disposedRef.current) {
      return Promise.resolve();
    }

    const currentGame = gameRef.current;
    if (!currentGame || currentGame.status === 'game_over') {
      return Promise.resolve();
    }

    const thisGen = generationRef.current;
    // Prevent old-game commands from dispatching if a restart is pending
    if (thisGen !== activeGenerationRef.current) {
      return Promise.resolve();
    }

    const seq = ++requestSeqRef.current;

    let queue = mutationQueuesRef.current.get(thisGen);
    if (!queue) {
      queue = Promise.resolve();
      mutationQueuesRef.current.set(thisGen, queue);
    }

    // Serialize mutation using the promise chain for this generation
    const promise = queue.then(async () => {
      if (disposedRef.current) return;

      // Re-verify conditions when this job actually runs
      const latestGame = gameRef.current;
      if (
        generationRef.current !== thisGen ||
        activeGenerationRef.current !== thisGen ||
        !latestGame ||
        latestGame.status === 'game_over'
      ) {
        return;
      }

      try {
        const options: RequestInit = { method };
        if (body) {
          options.headers = { 'Content-Type': 'application/json' };
          options.body = JSON.stringify(body);
        }
        const res = await fetch(`/api/games/${latestGame.id}/${action}`, options);
        if (disposedRef.current) return;

        if (
          generationRef.current !== thisGen ||
          activeGenerationRef.current !== thisGen
        ) {
          return;
        }

        if (res.ok) {
          const data: GameSession = await res.json();
          if (disposedRef.current) return;

          if (
            generationRef.current !== thisGen ||
            activeGenerationRef.current !== thisGen
          ) {
            return;
          }

          processResponse(data, seq, thisGen);
        }
      } catch (err) {
        console.error(`Failed to execute mutation: ${action}`, err);
      }
    });

    mutationQueuesRef.current.set(thisGen, promise);
    return promise;
  }, [processResponse]);

  const move = useCallback((direction: 'left' | 'right' | 'down') => {
    return executeMutation('move', 'POST', { direction });
  }, [executeMutation]);

  const tick = useCallback(() => {
    return executeMutation('tick', 'POST');
  }, [executeMutation]);

  const hold = useCallback(() => {
    if (disposedRef.current) return Promise.resolve();
    const currentGame = gameRef.current;
    if (!currentGame?.can_hold) return Promise.resolve();
    return executeMutation('hold', 'POST');
  }, [executeMutation]);

  // Keyboard binding for Hold ('c'/'C')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (disposedRef.current) return;
      if (e.key === 'c' || e.key === 'C') {
        const currentGame = gameRef.current;
        if (currentGame?.status !== 'playing' || !currentGame?.can_hold) return;
        // Avoid dispatching hold if a restart is currently in progress
        if (generationRef.current !== activeGenerationRef.current) return;
        e.preventDefault();
        hold();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hold]);

  // Set up gravity tick interval dynamically from gravity_interval_ms when playing
  const gravityInterval = game?.gravity_interval_ms ?? 500;
  useEffect(() => {
    if (disposedRef.current) return;
    if (game?.status !== 'playing') return;
    // Suppress if restart is pending
    if (generationRef.current !== activeGenerationRef.current) return;

    const interval = setInterval(() => {
      if (disposedRef.current) {
        clearInterval(interval);
        return;
      }
      if (isTickPendingRef.current) {
        // Coalesce / skip redundant automatic ticks
        return;
      }
      isTickPendingRef.current = true;
      tick().finally(() => {
        isTickPendingRef.current = false;
      });
    }, gravityInterval);

    return () => clearInterval(interval);
  }, [game?.id, game?.status, gravityInterval, tick]);

  return {
    game,
    loading,
    error,
    startGame,
    move,
    tick,
    hold,
  };
}
