import { useState, useEffect, useCallback, useRef } from 'react';

export interface Position {
  row: number;
  col: number;
}

export interface ActivePiece {
  type: string;
  origin: Position;
  cells: Position[];
}

export interface GameState {
  game_id: string;
  board: (string | null)[][];
  active_piece: ActivePiece | null;
  status: 'playing' | 'game_over';
}

const API_BASE = 'http://localhost:8000';

export function useTetris() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  
  // Keep the current game ID in a ref so useEffect or handlers can access the latest
  const gameIdRef = useRef<string | null>(null);

  // Initialize a new game session or restart
  const startNewGame = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/games`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to initialize a new game session.');
      }
      const data: GameState = await response.json();
      setGameState(data);
      gameIdRef.current = data.game_id;
    } catch (err: any) {
      setError(err.message || 'Unknown network error.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Trigger one gravity tick on the backend
  const triggerTick = useCallback(async () => {
    const id = gameIdRef.current;
    if (!id || !gameState || gameState.status === 'game_over') return;

    try {
      const response = await fetch(`${API_BASE}/api/games/${id}/tick`, {
        method: 'POST',
      });
      if (response.ok) {
        const data: GameState = await response.json();
        setGameState(data);
        if (data.status === 'game_over') {
          gameIdRef.current = null;
        }
      }
    } catch (err: any) {
      console.error('Gravity tick error:', err);
    }
  }, [gameState]);

  // Request move from the backend
  const movePiece = useCallback(async (direction: 'left' | 'right' | 'down') => {
    const id = gameIdRef.current;
    if (!id || !gameState || gameState.status === 'game_over') return;

    try {
      const response = await fetch(`${API_BASE}/api/games/${id}/move`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ direction }),
      });
      if (response.ok) {
        const data: GameState = await response.json();
        setGameState(data);
      }
    } catch (err: any) {
      console.error('Movement error:', err);
    }
  }, [gameState]);

  // Handle keyboard inputs
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!gameState || gameState.status === 'game_over') return;

      switch (e.key) {
        case 'ArrowLeft':
        case 'a':
        case 'A':
          e.preventDefault();
          movePiece('left');
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          e.preventDefault();
          movePiece('right');
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          e.preventDefault();
          movePiece('down');
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [gameState, movePiece]);

  // Automatic gravity ticker loop: fixed 500 ms gravity interval
  useEffect(() => {
    if (!gameState || gameState.status !== 'playing') return;

    const interval = setInterval(() => {
      triggerTick();
    }, 500);

    return () => {
      clearInterval(interval);
    };
  }, [gameState, triggerTick]);

  // Auto-start on mount
  useEffect(() => {
    startNewGame();
  }, [startNewGame]);

  return {
    gameState,
    error,
    loading,
    startNewGame,
    movePiece,
  };
}
