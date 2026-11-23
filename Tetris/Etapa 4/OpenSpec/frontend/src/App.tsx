import { useState, useEffect, useRef } from "react";
import { createGame, moveGame, tickGame, holdGame, getHighScores } from "./api";
import type { GameState, HighScoreEntry } from "./api";
import GridBoard, { PiecePreview } from "./components/GridBoard";
import GameOverModal from "./components/GameOverModal";
import "./App.css";

export default function App() {
  const [mode, setMode] = useState<"solo" | "duel">("solo");

  // --- Solo Mode State & Refs ---
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const nextRequestIdRef = useRef<number>(0);
  const lastProcessedIdRef = useRef<number>(0);
  const gameStateRef = useRef<GameState | null>(null);

  // --- Leaderboard ---
  const [highScores, setHighScores] = useState<HighScoreEntry[]>([]);
  const [scoresLoading, setScoresLoading] = useState<boolean>(false);
  const [scoresError, setScoresError] = useState<string | null>(null);
  const nextLeaderboardRequestIdRef = useRef<number>(0);
  const lastProcessedLeaderboardIdRef = useRef<number>(0);

  // --- Duel Mode State & Refs ---
  const [roomIdInput, setRoomIdInput] = useState<string>("");
  const [playerIdInput, setPlayerIdInput] = useState<string>("");
  const [roomId, setRoomId] = useState<string>("");
  const [playerId, setPlayerId] = useState<string>("");
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [wsError, setWsError] = useState<string | null>(null);
  const [roomStatus, setRoomStatus] = useState<string>("waiting"); // waiting, playing, finished
  const [localSeat, setLocalSeat] = useState<number | null>(null);
  
  const [localState, setLocalState] = useState<GameState | null>(null);
  const [opponentState, setOpponentState] = useState<GameState | null>(null);
  const [duelOutcome, setDuelOutcome] = useState<{
    winner_id: string | null;
    loser_id: string | null;
    is_draw: boolean;
    reason: string;
  } | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const localStateRef = useRef<GameState | null>(null);
  const opponentStateRef = useRef<GameState | null>(null);
  const wsSeqRef = useRef<number>(0);
  const highestRevisionRef = useRef<{ [seat: number]: number }>({ 1: -1, 2: -1 });

  useEffect(() => {
    gameStateRef.current = gameState;
  }, [gameState]);

  useEffect(() => {
    localStateRef.current = localState;
  }, [localState]);

  useEffect(() => {
    opponentStateRef.current = opponentState;
  }, [opponentState]);

  // Safe Solo State update
  const updateGameStateIfFresh = (newState: GameState, reqId: number) => {
    if (reqId > lastProcessedIdRef.current) {
      lastProcessedIdRef.current = reqId;
      setGameState(newState);
    } else {
      console.warn(`Stale response discarded. Request ID: ${reqId}, Last Processed: ${lastProcessedIdRef.current}`);
    }
  };

  // Safe Leaderboard update
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

  // Initialize/Restart Solo Game
  const startNewSoloGame = async () => {
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

  // Solo mode initialization
  useEffect(() => {
    if (mode === "solo") {
      startNewSoloGame();
      fetchScores();
    }
  }, [mode]);

  // Fetch scores on solo game over
  useEffect(() => {
    if (mode === "solo" && gameState?.status === "game_over") {
      fetchScores();
    }
  }, [gameState?.id, gameState?.status, mode]);

  // Gravity Loop for Solo Mode
  useEffect(() => {
    if (mode !== "solo" || gameState?.status !== "playing") return;

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
  }, [gameState?.id, gameState?.status, gameState?.gravity_interval_ms, mode]);

  // Solo Hold Button
  const triggerSoloHold = async () => {
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

  // Solo Mode Keyboard Controls
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      if (mode !== "solo") return;
      const current = gameStateRef.current;
      if (current?.status !== "playing") return;

      let direction: "left" | "right" | "down" | "clockwise" | "counterclockwise" | null = null;
      if (e.key === "ArrowLeft") {
        direction = "left";
      } else if (e.key === "ArrowRight") {
        direction = "right";
      } else if (e.key === "ArrowDown") {
        direction = "down";
      } else if (e.key === "ArrowUp") {
        direction = "clockwise";
      } else if (e.key === "z" || e.key === "Z") {
        direction = "counterclockwise";
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
  }, [mode]);

  // --- Duel Mode Handlers ---
  const joinDuelRoom = () => {
    if (!roomIdInput.trim() || !playerIdInput.trim()) {
      setWsError("Room ID and Player ID are required.");
      return;
    }

    // Clean IDs
    const rId = roomIdInput.trim().replace(/[^a-zA-Z0-9_-]/g, "");
    const pId = playerIdInput.trim().replace(/[^a-zA-Z0-9_-]/g, "");

    setRoomId(rId);
    setPlayerId(pId);
    setWsError(null);
    setRoomStatus("waiting");
    setLocalState(null);
    setOpponentState(null);
    setDuelOutcome(null);
    setLocalSeat(null);
    wsSeqRef.current = 0;
    highestRevisionRef.current = { 1: -1, 2: -1 };

    // Old-socket cleanup
    if (socketRef.current) {
      socketRef.current.onmessage = null;
      socketRef.current.onclose = null;
      socketRef.current.onerror = null;
      socketRef.current.close();
    }

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/ws/duel/${rId}?player_id=${pId}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      if (socketRef.current !== ws) return;
      setWsConnected(true);
      setWsError(null);
    };

    ws.onmessage = (event) => {
      if (socketRef.current !== ws) return;
      try {
        const msg = JSON.parse(event.data);
        if (msg.v !== 1) return;

        if (msg.type === "start") {
          if (msg.payload.room_id !== rId) {
            console.warn(`Start message discarded due to room mismatch: expected ${rId}, got ${msg.payload.room_id}`);
            return;
          }
          setRoomStatus("playing");
          setDuelOutcome(null);
        } else if (msg.type === "state") {
          const payload = msg.payload;
          if (payload.room_id !== rId) {
            console.warn(`Foreign room state discarded: expected ${rId}, got ${payload.room_id}`);
            return;
          }
          const seat = payload.seat;
          const rev = payload.revision;

          // Out-of-order protection: discard lower revisions per seat
          if (rev < highestRevisionRef.current[seat]) {
            console.warn(`Stale S2C revision discarded for seat ${seat}. Revision: ${rev}`);
            return;
          }
          highestRevisionRef.current[seat] = rev;

          const mappedState: GameState = {
            id: payload.player_id,
            board: payload.board,
            active_piece: payload.active_piece,
            status: payload.status,
            score: payload.score,
            total_lines: payload.total_lines,
            level: payload.level,
            gravity_interval_ms: payload.gravity_interval_ms,
            next_piece: payload.next_piece,
            hold_piece: payload.hold_piece,
            can_hold: payload.can_hold,
            generation: payload.generation,
          };

          if (payload.player_id === pId) {
            setLocalSeat(seat);
            setLocalState(mappedState);
          } else {
            setOpponentState(mappedState);
          }
        } else if (msg.type === "outcome") {
          if (msg.payload.room_id !== rId) {
            console.warn(`Outcome message discarded due to room mismatch: expected ${rId}, got ${msg.payload.room_id}`);
            return;
          }
          setRoomStatus("finished");
          setDuelOutcome(msg.payload);
        } else if (msg.type === "error") {
          setWsError(msg.payload.message);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onerror = () => {
      if (socketRef.current !== ws) return;
      setWsError("WebSocket connection error.");
    };

    ws.onclose = (event) => {
      if (socketRef.current !== ws) return;
      setWsConnected(false);
      if (event.code === 4001) {
        setWsError("Room Full");
      } else {
        setWsError(`Disconnected: ${event.reason || "Unknown reason"}`);
      }
    };
  };

  // Keyboard controls routing for Duel Mode
  useEffect(() => {
    const handleWSKeyDown = (e: KeyboardEvent) => {
      if (mode !== "duel" || roomStatus !== "playing" || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

      let action: string | null = null;
      if (e.key === "ArrowLeft") {
        action = "move_left";
      } else if (e.key === "ArrowRight") {
        action = "move_right";
      } else if (e.key === "ArrowDown") {
        action = "soft_drop";
      } else if (e.key === "ArrowUp") {
        action = "rotate_clockwise";
      } else if (e.key === "z" || e.key === "Z") {
        action = "rotate_counterclockwise";
      } else if (e.key === "c" || e.key === "C") {
        action = "hold";
      } else if (e.key === " ") {
        action = "hard_drop";
      }

      if (action) {
        e.preventDefault();
        const curLocal = localStateRef.current;
        const payload = {
          action,
          seq: wsSeqRef.current++,
          room_id: roomId,
          player_id: playerId,
          generation: (curLocal as any)?.generation || 0
        };
        const envelope = {
          v: 1,
          type: "action",
          timestamp: new Date().toISOString(),
          seq: payload.seq,
          payload
        };
        socketRef.current.send(JSON.stringify(envelope));
      }
    };

    window.addEventListener("keydown", handleWSKeyDown);
    return () => window.removeEventListener("keydown", handleWSKeyDown);
  }, [mode, roomStatus, roomId, playerId]);

  // Clean up WS on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.onmessage = null;
        socketRef.current.onclose = null;
        socketRef.current.onerror = null;
        socketRef.current.close();
      }
    };
  }, []);

  const handleDuelAction = (actionName: string) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    const curLocal = localStateRef.current;
    const payload = {
      action: actionName,
      seq: wsSeqRef.current++,
      room_id: roomId,
      player_id: playerId,
      generation: (curLocal as any)?.generation || 0
    };
    const envelope = {
      v: 1,
      type: "action",
      timestamp: new Date().toISOString(),
      seq: payload.seq,
      payload
    };
    socketRef.current.send(JSON.stringify(envelope));
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>NEON TETRIS</h1>
        <p className="subtitle">Authoritative Backend Study (Stage 4)</p>
        <div className="mode-toggle">
          <button
            className={`toggle-button ${mode === "solo" ? "active" : ""}`}
            onClick={() => setMode("solo")}
            data-testid="mode-toggle-solo"
          >
            SOLO PLAY
          </button>
          <button
            className={`toggle-button ${mode === "duel" ? "active" : ""}`}
            onClick={() => setMode("duel")}
            data-testid="mode-toggle-duel"
          >
            TWO-PLAYER DUEL
          </button>
        </div>
      </header>

      {/* --- SOLO PLAY MODE --- */}
      {mode === "solo" && (
        <>
          {error && (
            <div className="error-banner">
              <p>{error}</p>
              <button className="neon-button" onClick={startNewSoloGame}>
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
                    <li><kbd>←</kbd> <span>Move Left</span></li>
                    <li><kbd>→</kbd> <span>Move Right</span></li>
                    <li><kbd>↓</kbd> <span>Soft Drop</span></li>
                    <li><kbd>↑</kbd> <span>Rotate CW</span></li>
                    <li><kbd>Z</kbd> <span>Rotate CCW</span></li>
                    <li><kbd>C</kbd> <span>Hold Piece</span></li>
                  </ul>
                </div>

                <div className="actions-panel">
                  <button
                    className="neon-button hold-button"
                    onClick={triggerSoloHold}
                    disabled={gameState.status !== "playing" || !gameState.can_hold}
                    style={{ marginBottom: "1rem" }}
                  >
                    HOLD PIECE (C)
                  </button>
                  <button className="neon-button reset-button" onClick={startNewSoloGame}>
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
                onRestart={startNewSoloGame}
              />
            </main>
          )}
        </>
      )}

      {/* --- TWO-PLAYER DUEL MODE --- */}
      {mode === "duel" && (
        <div className="duel-layout-container" style={{ width: "100%", maxWidth: "1200px" }}>
          {!wsConnected && (
            <div className="panel room-entry-panel" style={{ maxWidth: "500px", margin: "0 auto", padding: "2rem" }}>
              <h3 style={{ textAlign: "center", marginBottom: "1.5rem" }}>JOIN DUEL ROOM</h3>
              {wsError && (
                <div className="error-banner" data-testid="duel-error" style={{ marginBottom: "1rem", background: "#ff005515", border: "1px solid #ff0055", padding: "0.8rem", borderRadius: "4px" }}>
                  <p style={{ color: "#ff0055", margin: 0 }}>{wsError}</p>
                </div>
              )}
              <div className="form-group" style={{ marginBottom: "1rem" }}>
                <label htmlFor="roomId" style={{ display: "block", marginBottom: "0.5rem" }}>Room ID:</label>
                <input
                  id="roomId"
                  type="text"
                  className="neon-input"
                  placeholder="e.g. room-123"
                  value={roomIdInput}
                  onChange={(e) => setRoomIdInput(e.target.value)}
                  style={{ width: "100%", padding: "0.8rem", background: "#0b0c16", border: "1px solid var(--panel-border)", color: "#fff", borderRadius: "4px" }}
                />
              </div>
              <div className="form-group" style={{ marginBottom: "1.5rem" }}>
                <label htmlFor="playerId" style={{ display: "block", marginBottom: "0.5rem" }}>Player ID:</label>
                <input
                  id="playerId"
                  type="text"
                  className="neon-input"
                  placeholder="e.g. player-abc"
                  value={playerIdInput}
                  onChange={(e) => setPlayerIdInput(e.target.value)}
                  style={{ width: "100%", padding: "0.8rem", background: "#0b0c16", border: "1px solid var(--panel-border)", color: "#fff", borderRadius: "4px" }}
                />
              </div>
              <button className="neon-button" style={{ width: "100%" }} onClick={joinDuelRoom} data-testid="join-duel-button">
                JOIN DUEL
              </button>
            </div>
          )}

          {wsConnected && (
            <main className="duel-gameplay-layout">
              {wsError && (
                <div className="error-banner" data-testid="duel-game-error" style={{ background: "#ff005515", border: "1px solid #ff0055", padding: "0.8rem", borderRadius: "4px", marginBottom: "1.5rem", textAlign: "center" }}>
                  <p style={{ color: "#ff0055", margin: 0 }}>{wsError}</p>
                </div>
              )}

              <div className="duel-header-status" style={{ textAlign: "center", marginBottom: "2rem" }}>
                <div className="panel status-panel" style={{ display: "inline-block", padding: "1rem 2rem" }}>
                  <span style={{ color: "var(--text-secondary)", marginRight: "1rem" }}>Room ID: <strong style={{ color: "#fff" }}>{roomId}</strong></span>
                  <span style={{ color: "var(--text-secondary)", marginRight: "1rem" }}>Your Seat: <strong style={{ color: "#fff" }}>Seat {localSeat}</strong></span>
                  <span style={{ color: "var(--text-secondary)" }}>Match Status: </span>
                  <span className={`status-badge status-${roomStatus}`} style={{ marginLeft: "0.5rem" }}>
                    {roomStatus.toUpperCase()}
                  </span>
                </div>
              </div>

              {roomStatus === "waiting" && (
                <div className="panel waiting-lobby" style={{ textAlign: "center", padding: "3rem 1rem", maxWidth: "600px", margin: "0 auto" }}>
                  <div className="spinner" style={{ margin: "0 auto 1.5rem" }}></div>
                  <h3>WAITING FOR OPPONENT...</h3>
                  <p style={{ color: "var(--text-secondary)" }}>Share Room ID <strong>{roomId}</strong> with another player to start the duel.</p>
                </div>
              )}

              {roomStatus === "finished" && duelOutcome && (
                <div className="panel finished-outcome" style={{ textAlign: "center", padding: "3rem 1rem", maxWidth: "600px", margin: "0 auto", border: "2px solid var(--neon-pink)" }}>
                  <h2 style={{ fontFamily: "Orbitron, sans-serif", letterSpacing: "2px", color: "var(--neon-pink)" }}>MATCH FINISHED</h2>
                  {duelOutcome.is_draw ? (
                    <h3 style={{ fontSize: "2rem", margin: "1.5rem 0" }}>IT'S A DRAW!</h3>
                  ) : (
                    <h3 style={{ fontSize: "2.2rem", margin: "1.5rem 0", textShadow: "0 0 10px #00f3ff" }}>
                      {duelOutcome.winner_id === playerId ? "🏆 VICTORY!" : "❌ DEFEAT"}
                    </h3>
                  )}
                  <p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
                    Reason: {duelOutcome.reason.toUpperCase()}
                  </p>
                  <button className="neon-button" onClick={() => {
                    if (socketRef.current) socketRef.current.close();
                    setWsConnected(false);
                  }}>
                    LOBBY
                  </button>
                </div>
              )}

              {/* Side-by-side Dual Canvas Rendering */}
              {(roomStatus === "playing" || roomStatus === "finished") && (
                <div className="duel-boards-side-by-side" style={{ display: "flex", gap: "2rem", justifyContent: "center", flexWrap: "nowrap" }}>
                  {/* Left Side: Local Board */}
                  <div className="duel-seat local-seat" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <h3 style={{ fontFamily: "Orbitron, sans-serif", color: "var(--neon-blue)", letterSpacing: "1px", marginBottom: "0.8rem" }}>
                      YOUR BOARD {localSeat ? `(Seat ${localSeat})` : ""}
                    </h3>
                    {localState ? (
                      <div className="duel-seat-container" style={{ display: "flex", gap: "1.2rem", alignItems: "flex-start" }}>
                        <GridBoard gameState={localState} isDuel={true} />
                        <div className="panel seat-stats" style={{ width: "150px", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                          <h4 style={{ margin: "0 0 0.4rem", fontFamily: "Orbitron, sans-serif", fontSize: "0.9rem" }}>YOUR STATS</h4>
                          
                          <div className="mini-preview-group" style={{ display: "flex", gap: "0.4rem", marginBottom: "0.4rem" }}>
                            <div style={{ flex: 1 }}>
                              <span style={{ color: "var(--text-secondary)", fontSize: "0.7rem", display: "block" }}>HOLD</span>
                              <div style={{ background: "rgba(0,0,0,0.3)", padding: "4px", borderRadius: "4px", height: "50px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <PiecePreview piece={localState.hold_piece} grayscale={!localState.can_hold} />
                              </div>
                            </div>
                            <div style={{ flex: 1 }}>
                              <span style={{ color: "var(--text-secondary)", fontSize: "0.7rem", display: "block" }}>NEXT</span>
                              <div style={{ background: "rgba(0,0,0,0.3)", padding: "4px", borderRadius: "4px", height: "50px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <PiecePreview piece={localState.next_piece} />
                              </div>
                            </div>
                          </div>

                          <div style={{ marginBottom: "0.3rem" }}><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>SCORE:</span><div data-testid="score-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{localState.score}</div></div>
                          <div style={{ marginBottom: "0.3rem" }}><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>LINES:</span><div data-testid="lines-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{localState.total_lines}</div></div>
                          <div style={{ marginBottom: "0.3rem" }}><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>LEVEL:</span><div data-testid="level-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{localState.level}</div></div>
                          <button
                            className="neon-button"
                            onClick={() => handleDuelAction("hold")}
                            disabled={!localState.can_hold || localState.status === "game_over" || roomStatus !== "playing"}
                            style={{ width: "100%", padding: "0.4rem", fontSize: "0.8rem" }}
                          >
                            HOLD (C)
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="panel" style={{ width: "320px", height: "640px", display: "flex", alignItems: "center", justifyContent: "center" }}>Initializing Board...</div>
                    )}
                  </div>

                  {/* Right Side: Opponent Board */}
                  <div className="duel-seat opponent-seat" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <h3 style={{ fontFamily: "Orbitron, sans-serif", color: "var(--neon-pink)", letterSpacing: "1px", marginBottom: "0.8rem" }}>
                      OPPONENT'S BOARD
                    </h3>
                    {opponentState ? (
                      <div className="duel-seat-container" style={{ display: "flex", gap: "1.2rem", alignItems: "flex-start" }}>
                        <GridBoard gameState={opponentState} isDuel={true} />
                        <div className="panel seat-stats" style={{ width: "150px", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                          <h4 style={{ margin: "0 0 0.4rem", fontFamily: "Orbitron, sans-serif", fontSize: "0.9rem" }}>STATS</h4>
                          
                          <div className="mini-preview-group" style={{ display: "flex", gap: "0.4rem", marginBottom: "0.4rem" }}>
                            <div style={{ flex: 1 }}>
                              <span style={{ color: "var(--text-secondary)", fontSize: "0.7rem", display: "block" }}>HOLD</span>
                              <div style={{ background: "rgba(0,0,0,0.3)", padding: "4px", borderRadius: "4px", height: "50px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <PiecePreview piece={opponentState.hold_piece} grayscale={!opponentState.can_hold} />
                              </div>
                            </div>
                            <div style={{ flex: 1 }}>
                              <span style={{ color: "var(--text-secondary)", fontSize: "0.7rem", display: "block" }}>NEXT</span>
                              <div style={{ background: "rgba(0,0,0,0.3)", padding: "4px", borderRadius: "4px", height: "50px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <PiecePreview piece={opponentState.next_piece} />
                              </div>
                            </div>
                          </div>

                          <div style={{ marginBottom: "0.3rem" }}><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>SCORE:</span><div data-testid="opponent-score-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{opponentState.score}</div></div>
                          <div style={{ marginBottom: "0.3rem" }}><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>LINES:</span><div data-testid="opponent-lines-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{opponentState.total_lines}</div></div>
                          <div><span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>LEVEL:</span><div data-testid="opponent-level-value" style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{opponentState.level}</div></div>
                        </div>
                      </div>
                    ) : (
                      <div className="panel" style={{ width: "320px", height: "640px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}>
                        Waiting for Opponent to Connect...
                      </div>
                    )}
                  </div>
                </div>
              )}
            </main>
          )}
        </div>
      )}
    </div>
  );
}
