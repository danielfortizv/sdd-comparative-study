import { useState, useEffect, useRef } from "react";
import { createGame, moveGame, tickGame, holdGame } from "./api";
import type { GameState } from "./api";
import GridBoard from "./components/GridBoard";
import GameOverModal from "./components/GameOverModal";
import "./App.css";

export default function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Request sequence tracking refs to protect against out-of-order stale responses
  const nextRequestIdRef = useRef<number>(0);
  const lastProcessedIdRef = useRef<number>(0);

  // Store gameState in ref to prevent keydown handlers from operating on stale closures
  const gameStateRef = useRef<GameState | null>(null);

  useEffect(() => {
    gameStateRef.current = gameState;
  }, [gameState]);

  // Helper to apply state updates safely ensuring sequence freshness
  const updateGameStateIfFresh = (newState: GameState, reqId: number) => {
    if (reqId > lastProcessedIdRef.current) {
      lastProcessedIdRef.current = reqId;
      setGameState(newState);
    } else {
      console.warn(`Stale response discarded. Request ID: ${reqId}, Last Processed: ${lastProcessedIdRef.current}`);
    }
  };

  // Initialize game on load or reset
  const startNewGame = async () => {
    setLoading(true);
    setError(null);
    const reqId = ++nextRequestIdRef.current;
    try {
      const state = await createGame();
      updateGameStateIfFresh(state, reqId);
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

  // Gravity Tick Hook: dynamically schedules based on the received gravity_interval_ms
  useEffect(() => {
    if (gameState?.status !== "playing") return;

    const interval = setInterval(async () => {
      const current = gameStateRef.current;
      if (current?.status === "playing") {
        const reqId = ++nextRequestIdRef.current;
        try {
          const newState = await tickGame(current.id);
          updateGameStateIfFresh(newState, reqId);
        } catch (err) {
          console.error("Gravity tick failed:", err);
        }
      }
    }, gameState.gravity_interval_ms);

    return () => clearInterval(interval);
  }, [gameState?.id, gameState?.status, gameState?.gravity_interval_ms]);

  // Hold Action dispatcher
  const triggerHold = async () => {
    const current = gameStateRef.current;
    if (current?.status !== "playing" || !current?.can_hold) return;

    const reqId = ++nextRequestIdRef.current;
    try {
      const newState = await holdGame(current.id);
      updateGameStateIfFresh(newState, reqId);
    } catch (err) {
      console.error("Hold operation failed:", err);
    }
  };

  // Keyboard Controls Hook (Arrows for movement, C for Hold)
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      const current = gameStateRef.current;
      if (current?.status !== "playing") return;

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
        const reqId = ++nextRequestIdRef.current;
        try {
          const newState = await moveGame(current.id, direction);
          updateGameStateIfFresh(newState, reqId);
        } catch (err) {
          console.error("Movement failed:", err);
        }
      } else if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        if (current.can_hold) {
          const reqId = ++nextRequestIdRef.current;
          try {
            const newState = await holdGame(current.id);
            updateGameStateIfFresh(newState, reqId);
          } catch (err) {
            console.error("Hold key pressed, but hold failed:", err);
          }
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
        <p className="subtitle">Authoritative Backend Study (Stage 2)</p>
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
                <li>
                  <kbd>C</kbd> <span>Hold Piece</span>
                </li>
              </ul>
            </div>

            <div className="actions-panel">
              <button
                className="neon-button hold-button"
                onClick={triggerHold}
                disabled={gameState.status !== "playing" || !gameState.can_hold}
                style={{ marginBottom: "1rem" }}
              >
                HOLD PIECE (C)
              </button>
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
