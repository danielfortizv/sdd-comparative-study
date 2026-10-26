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

  // Synchronous/promise-based queue to serialize all mutations
  const mutationQueueRef = useRef<Promise<any>>(Promise.resolve());

  // Handle a successful response from a game mutation/status query
  const processResponse = useCallback((data: GameSession, seq: number, gen: number) => {
    // Only process if this matches the current active generation
    if (gen !== generationRef.current || gen !== activeGenerationRef.current) {
      return;
    }
    if (seq < appliedSeqRef.current) {
      return;
    }
    appliedSeqRef.current = seq;
    setGame(data);
  }, []);

  const startGame = async () => {
    const thisGen = ++generationRef.current;
    setLoading(true);
    setError(null);

    // Cancel old timer immediately by clearing game state
    setGame(null);

    try {
      const res = await fetch('/api/games', { method: 'POST' });
      if (thisGen < generationRef.current) {
        // Stale start: a newer start is already pending! Discard.
        return;
      }
      if (!res.ok) throw new Error('Failed to start game');
      const data: GameSession = await res.json();
      
      // Setup successful generation
      activeGenerationRef.current = thisGen;
      requestSeqRef.current = 0;
      appliedSeqRef.current = 0;
      setGame(data);
    } catch (err: any) {
      if (thisGen === generationRef.current) {
        setError(err.message || 'An error occurred');
      }
    } finally {
      if (thisGen === generationRef.current) {
        setLoading(false);
      }
    }
  };

  const executeMutation = useCallback((action: string, method: string = 'POST', body: any = null) => {
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

    // Serialize mutation using the promise chain
    const promise = mutationQueueRef.current.then(async () => {
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
        if (res.ok) {
          const data: GameSession = await res.json();
          processResponse(data, seq, thisGen);
        }
      } catch (err) {
        console.error(`Failed to execute mutation: ${action}`, err);
      }
    });

    mutationQueueRef.current = promise;
    return promise;
  }, [processResponse]);

  const move = useCallback((direction: 'left' | 'right' | 'down') => {
    return executeMutation('move', 'POST', { direction });
  }, [executeMutation]);

  const tick = useCallback(() => {
    return executeMutation('tick', 'POST');
  }, [executeMutation]);

  const hold = useCallback(() => {
    const currentGame = gameRef.current;
    if (!currentGame?.can_hold) return Promise.resolve();
    return executeMutation('hold', 'POST');
  }, [executeMutation]);

  // Keyboard binding for Hold ('c'/'C')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
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
    if (game?.status !== 'playing') return;
    // Suppress if restart is pending
    if (generationRef.current !== activeGenerationRef.current) return;

    const interval = setInterval(() => {
      tick();
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
