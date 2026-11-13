import { useState, useEffect, useRef } from "react";
import { createGame, moveGame, tickGame, holdGame, getHighScores } from "./api";
import type { GameState, HighScoreEntry } from "./api";
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

  // High scores tracking state
  const [highScores, setHighScores] = useState<HighScoreEntry[]>([]);
  const [scoresLoading, setScoresLoading] = useState<boolean>(false);
  const [scoresError, setScoresError] = useState<string | null>(null);

  // Leaderboard request sequence tracking to protect against out-of-order stale responses
  const nextLeaderboardRequestIdRef = useRef<number>(0);
  const lastProcessedLeaderboardIdRef = useRef<number>(0);

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

  const fetchScores = async () => {
    setScoresLoading(true);
    setScoresError(null);
    const reqId = ++nextLeaderboardRequestIdRef.current;
    try {
      const data = await getHighScores();
      if (reqId > lastProcessedLeaderboardIdRef.current) {
        lastProcessedLeaderboardIdRef.current = reqId;
        setHighScores(data.scores);
      } else {
        console.warn(`Stale leaderboard response discarded. Request ID: ${reqId}, Last Processed: ${lastProcessedLeaderboardIdRef.current}`);
      }
    } catch (err) {
      console.error("Failed to fetch high scores:", err);
      setScoresError("Storage service unavailable");
    } finally {
      setScoresLoading(false);
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
      fetchScores();
    };
    init();
    return () => {
      active = false;
    };
  }, []);

  // Fetch leaderboard automatically when transitioning to game_over
  useEffect(() => {
    if (gameState?.status === "game_over") {
      fetchScores();
    }
  }, [gameState?.id, gameState?.status]);

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
        <p className="subtitle">Authoritative Backend Study (Stage 3)</p>
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

          <section className="leaderboard-section">
            <div className="panel leaderboard-panel">
              <h3>HIGH SCORES</h3>
              {scoresLoading && (
                <div className="loading-state" data-testid="leaderboard-loading">
                  <div className="spinner mini-spinner"></div>
                  <p>Loading scores...</p>
                </div>
              )}
              {scoresError && (
                <div className="error-state" data-testid="leaderboard-error">
                  <p className="error-text">{scoresError}</p>
                </div>
              )}
              {!scoresLoading && !scoresError && highScores.length === 0 && (
                <div className="empty-state" data-testid="leaderboard-empty">
                  <p>No scores yet.<br />Play a game to set one!</p>
                </div>
              )}
              {!scoresLoading && !scoresError && highScores.length > 0 && (
                <div className="scores-list" data-testid="leaderboard-list">
                  {highScores.map((entry, index) => (
                    <div key={entry.game_id} className="score-row">
                      <span className="score-rank">#{index + 1}</span>
                      <div className="score-details">
                        <div className="score-main">
                          <span className="score-value">{entry.score}</span>
                          <span className="score-date">
                            {new Date(entry.completed_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                            })}
                          </span>
                        </div>
                        <div className="score-sub">
                          <span>Lines: {entry.total_lines}</span>
                          <span>Lv: {entry.level}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
