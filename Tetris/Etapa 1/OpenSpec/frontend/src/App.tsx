import { useState, useEffect, useRef } from "react";
import { createGame, moveGame, tickGame } from "./api";
import type { GameState } from "./api";
import GridBoard from "./components/GridBoard";
import GameOverModal from "./components/GameOverModal";
import "./App.css";

export default function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Store gameState in ref to prevent reset of gravity tick interval
  const gameStateRef = useRef<GameState | null>(null);

  useEffect(() => {
    gameStateRef.current = gameState;
  }, [gameState]);

  // Initialize game on load
  const startNewGame = async () => {
    setLoading(true);
    setError(null);
    try {
      const state = await createGame();
      setGameState(state);
    } catch (err) {
      setError("Unable to connect to the backend server. Make sure the FastAPI backend is running.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const init = async () => {
      await Promise.resolve();
      if (!active) return;
      startNewGame();
    };
    init();
    return () => {
      active = false;
    };
  }, []);

  // Gravity Tick Hook: triggers every 500 ms while playing (REQ-030, Task 4.4)
  useEffect(() => {
    const interval = setInterval(async () => {
      const current = gameStateRef.current;
      if (current && current.status === "playing") {
        try {
          const newState = await tickGame(current.id);
          setGameState(newState);
        } catch (err) {
          console.error("Gravity tick failed:", err);
        }
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // Keyboard Controls Hook (REQ-008, REQ-009, REQ-010, Task 4.3)
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      const current = gameStateRef.current;
      if (!current || current.status !== "playing") return;

      let direction: "left" | "right" | "down" | null = null;
      if (e.key === "ArrowLeft") {
        direction = "left";
      } else if (e.key === "ArrowRight") {
        direction = "right";
      } else if (e.key === "ArrowDown") {
        direction = "down";
      }

      if (direction) {
        e.preventDefault();
        try {
          const newState = await moveGame(current.id, direction);
          setGameState(newState);
        } catch (err) {
          console.error("Movement failed:", err);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>NEON TETRIS</h1>
        <p className="subtitle">Authoritative Backend Study (Stage 1)</p>
      </header>

      {error && (
        <div className="error-banner">
          <p>{error}</p>
          <button className="neon-button" onClick={startNewGame}>
            Try Again
          </button>
        </div>
      )}

      {loading && !gameState && (
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Connecting to backend game server...</p>
        </div>
      )}

      {gameState && (
        <main className="game-layout">
          <section className="board-section">
            <GridBoard gameState={gameState} />
          </section>

          <section className="controls-section">
            <div className="panel info-panel">
              <h3>GAME STATUS</h3>
              <div className="status-badge-container">
                <span className={`status-badge status-${gameState.status}`}>
                  {gameState.status.toUpperCase()}
                </span>
              </div>
              <div className="game-id">
                <span className="label">Session ID:</span>
                <span className="value">{gameState.id.substring(0, 8)}...</span>
              </div>
            </div>

            <div className="panel instructions-panel">
              <h3>CONTROLS</h3>
              <ul className="controls-list">
                <li>
                  <kbd>←</kbd> <span>Move Left</span>
                </li>
                <li>
                  <kbd>→</kbd> <span>Move Right</span>
                </li>
                <li>
                  <kbd>↓</kbd> <span>Soft Drop</span>
                </li>
              </ul>
            </div>

            <div className="actions-panel">
              <button className="neon-button reset-button" onClick={startNewGame}>
                RESTART GAME
              </button>
            </div>
          </section>

          <GameOverModal
            show={gameState.status === "game_over"}
            onRestart={startNewGame}
          />
        </main>
      )}
    </div>
  );
}
