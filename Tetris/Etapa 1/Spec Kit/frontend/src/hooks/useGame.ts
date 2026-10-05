import { useState, useEffect, useRef } from 'react';
import { GameSession } from '../types';

export function useGame() {
  const [game, setGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use a ref to always keep the latest game state accessible in the timer
  const gameRef = useRef<GameSession | null>(null);
  useEffect(() => {
    gameRef.current = game;
  }, [game]);

  const startGame = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/games', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to start game');
      const data: GameSession = await res.json();
      setGame(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const move = async (direction: 'left' | 'right' | 'down') => {
    if (!game || game.status === 'game_over') return;
    try {
      const res = await fetch(`/api/games/${game.id}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction }),
      });
      if (res.ok) {
        const data: GameSession = await res.json();
        setGame(data);
      }
    } catch (err) {
      console.error('Failed to move piece', err);
    }
  };

  const tick = async () => {
    const currentGame = gameRef.current;
    if (!currentGame || currentGame.status === 'game_over') return;
    try {
      const res = await fetch(`/api/games/${currentGame.id}/tick`, {
        method: 'POST',
      });
      if (res.ok) {
        const data: GameSession = await res.json();
        setGame(data);
      }
    } catch (err) {
      console.error('Failed to tick game', err);
    }
  };

  // Set up gravity tick interval of 500ms when playing
  useEffect(() => {
    if (!game || game.status !== 'playing') return;

    const interval = setInterval(() => {
      tick();
    }, 500);

    return () => clearInterval(interval);
  }, [game?.id, game?.status]); // Reset timer when session ID or status transitions

  return {
    game,
    loading,
    error,
    startGame,
    move,
    tick,
  };
}
