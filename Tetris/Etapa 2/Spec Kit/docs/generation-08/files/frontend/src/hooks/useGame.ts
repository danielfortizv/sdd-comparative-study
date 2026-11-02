import { useState, useEffect, useRef, useCallback } from 'react';
import { GameSession } from '../types';

export function useGame() {
  const [game, setGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sequence and session tracking refs to prevent race conditions and regressions
  const currentSessionIdRef = useRef<string | null>(null);
  const requestSeqRef = useRef<number>(0);
  const appliedSeqRef = useRef<number>(0);

  // Use a ref to always keep the latest game state accessible in the timer
  const gameRef = useRef<GameSession | null>(null);
  useEffect(() => {
    gameRef.current = game;
  }, [game]);

  const processResponse = useCallback((data: GameSession, seq: number, sessionEpoch: string | null) => {
    if (sessionEpoch !== currentSessionIdRef.current && sessionEpoch !== null) {
      // Stale request from a previous session! Discard.
      return;
    }
    if (seq < appliedSeqRef.current) {
      // Out-of-order stale response! Discard.
      return;
    }
    appliedSeqRef.current = seq;
    if (sessionEpoch === null) {
      currentSessionIdRef.current = data.id;
    }
    setGame(data);
  }, []);

  const startGame = async () => {
    setLoading(true);
    setError(null);
    // Invalidate everything on restart
    currentSessionIdRef.current = null;
    requestSeqRef.current = 0;
    appliedSeqRef.current = 0;

    const seq = ++requestSeqRef.current;
    const sessionEpoch = currentSessionIdRef.current;

    try {
      const res = await fetch('/api/games', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to start game');
      const data: GameSession = await res.json();
      processResponse(data, seq, sessionEpoch);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const move = async (direction: 'left' | 'right' | 'down') => {
    const currentGame = gameRef.current;
    if (currentGame?.status === 'game_over') return;
    const seq = ++requestSeqRef.current;
    const sessionEpoch = currentSessionIdRef.current;

    try {
      const res = await fetch(`/api/games/${currentGame?.id}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction }),
      });
      if (res.ok) {
        const data: GameSession = await res.json();
        processResponse(data, seq, sessionEpoch);
      }
    } catch (err) {
      console.error('Failed to move piece', err);
    }
  };

  const tick = async () => {
    const currentGame = gameRef.current;
    if (currentGame?.status === 'game_over') return;
    const seq = ++requestSeqRef.current;
    const sessionEpoch = currentSessionIdRef.current;

    try {
      const res = await fetch(`/api/games/${currentGame?.id}/tick`, {
        method: 'POST',
      });
      if (res.ok) {
        const data: GameSession = await res.json();
        processResponse(data, seq, sessionEpoch);
      }
    } catch (err) {
      console.error('Failed to tick game', err);
    }
  };

  const hold = async () => {
    const currentGame = gameRef.current;
    if (currentGame?.status === 'game_over' || !currentGame?.can_hold) return;
    const seq = ++requestSeqRef.current;
    const sessionEpoch = currentSessionIdRef.current;

    try {
      const res = await fetch(`/api/games/${currentGame?.id}/hold`, {
        method: 'POST',
      });
      if (res.ok) {
        const data: GameSession = await res.json();
        processResponse(data, seq, sessionEpoch);
      }
    } catch (err) {
      console.error('Failed to hold piece', err);
    }
  };

  // Keyboard binding for Hold ('c'/'C')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const currentGame = gameRef.current;
      if (currentGame?.status !== 'playing') return;
      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        hold();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Set up gravity tick interval dynamically from gravity_interval_ms when playing
  const gravityInterval = game?.gravity_interval_ms ?? 500;
  useEffect(() => {
    if (game?.status !== 'playing') return;

    const interval = setInterval(() => {
      tick();
    }, gravityInterval);

    return () => clearInterval(interval);
  }, [game?.id, game?.status, gravityInterval]);

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
