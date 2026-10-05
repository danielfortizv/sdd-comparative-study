import { useEffect, useState, useRef } from 'react';
import { GameState } from './types';
import { createGame, tickGame, moveGame } from './api';
import { TetrisBoard } from './components/TetrisBoard';
import { GameStatus } from './components/GameStatus';

export default function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Semaphore / Lock to prevent overlapping async API calls and race conditions
  const pendingRequest = useRef<boolean>(false);

  // Helper to start or restart the game
  const startNewGame = async () => {
    if (pendingRequest.current) return;
    pendingRequest.current = true;
    setLoading(true);
    setError(null);
    try {
      const state = await createGame();
      setGameState(state);
    } catch (err) {
      console.error(err);
      setError('Could not connect to the Tetris API. Make sure the backend server is running.');
    } finally {
      setLoading(false);
      pendingRequest.current = false;
    }
  };

  // Start game on mount
  useEffect(() => {
    startNewGame();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Set up the automatic gravity tick (Req-31) every 500 ms
  useEffect(() => {
    if (!gameState || gameState.status === 'game_over') return;

    const intervalId = setInterval(async () => {
      // Skip this tick if another request is currently in flight
      if (pendingRequest.current) return;

      pendingRequest.current = true;
      try {
        const updatedState = await tickGame(gameState.id);
        setGameState(updatedState);
      } catch (err) {
        console.error('Gravity tick failed:', err);
      } finally {
        pendingRequest.current = false;
      }
    }, 500);

    return () => clearInterval(intervalId);
  }, [gameState]);

  // Set up keyboard control listeners (Req-32) with throttle check (Req-33)
  useEffect(() => {
    if (!gameState || gameState.status === 'game_over') return;

    const handleKeyDown = async (event: KeyboardEvent) => {
      let direction: 'left' | 'right' | 'down' | null = null;

      if (event.key === 'ArrowLeft') {
        direction = 'left';
      } else if (event.key === 'ArrowRight') {
        direction = 'right';
      } else if (event.key === 'ArrowDown') {
        direction = 'down';
      }

      if (!direction) return;

      // Prevent default scrolling behavior for arrow keys
      event.preventDefault();

      // Skip input if another request is currently in flight (Req-33)
      if (pendingRequest.current) return;

      pendingRequest.current = true;
      try {
        const updatedState = await moveGame(gameState.id, direction);
        setGameState(updatedState);
      } catch (err) {
        console.error('Movement failed:', err);
      } finally {
        pendingRequest.current = false;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameState]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Tetris Study Studio</h1>
        <p className="subtitle">Stage 1 — Option A (Server-Authoritative, Rotation-Free)</p>
      </header>

      <main className="game-container">
        {loading && !gameState && (
          <div className="panel loading-panel">
            <p>Initializing Tetris Session...</p>
          </div>
        )}

        {error && (
          <div className="panel error-panel">
            <p className="error-message">{error}</p>
            <button onClick={startNewGame} className="btn-retry">
              Retry Connection
            </button>
          </div>
        )}

        {gameState && (
          <>
            <div className="board-section">
              <TetrisBoard gameState={gameState} />
            </div>
            <div className="status-section">
              <GameStatus 
                gameState={gameState} 
                onRestart={startNewGame} 
                isLoading={loading}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
