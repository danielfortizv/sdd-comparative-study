import { useState, useEffect, useCallback, useRef } from 'react'

interface Cell {
  row: number
  col: number
}

interface ActivePiece {
  shape: "I" | "J" | "L" | "O" | "S" | "T" | "Z"
  origin: Cell
  cells: Cell[]
}

interface GameState {
  id: string
  status: "playing" | "game_over"
  board: number[][]
  active_piece: ActivePiece | null
  score: number
  total_lines: number
  level: number
  gravity_interval_ms: number
  next_piece: string
  hold_piece: string | null
  can_hold: boolean
}

const SHAPE_INDICES: Record<string, number> = {
  I: 1, J: 2, L: 3, O: 4, S: 5, T: 6, Z: 7
}

const MINI_PREVIEWS: Record<string, Cell[]> = {
  I: [{ row: 1, col: 0 }, { row: 1, col: 1 }, { row: 1, col: 2 }, { row: 1, col: 3 }],
  J: [{ row: 0, col: 0 }, { row: 1, col: 0 }, { row: 1, col: 1 }, { row: 1, col: 2 }],
  L: [{ row: 0, col: 2 }, { row: 1, col: 0 }, { row: 1, col: 1 }, { row: 1, col: 2 }],
  O: [{ row: 0, col: 1 }, { row: 0, col: 2 }, { row: 1, col: 1 }, { row: 1, col: 2 }],
  S: [{ row: 0, col: 1 }, { row: 0, col: 2 }, { row: 1, col: 0 }, { row: 1, col: 1 }],
  T: [{ row: 0, col: 1 }, { row: 1, col: 0 }, { row: 1, col: 1 }, { row: 1, col: 2 }],
  Z: [{ row: 0, col: 0 }, { row: 0, col: 1 }, { row: 1, col: 1 }, { row: 1, col: 2 }],
};

function MiniGrid({ shape }: { shape: string | null }) {
  if (!shape) {
    return (
      <div className="mini-grid">
        {Array.from({ length: 2 }).map((_, r) => (
          <div key={r} className="mini-row">
            {Array.from({ length: 4 }).map((_, c) => (
              <div key={c} className="mini-cell empty" />
            ))}
          </div>
        ))}
      </div>
    );
  }
  
  const cells = MINI_PREVIEWS[shape] || [];
  const colorIdx = SHAPE_INDICES[shape] || 0;
  
  return (
    <div className="mini-grid">
      {Array.from({ length: 2 }).map((_, r) => (
        <div key={r} className="mini-row">
          {Array.from({ length: 4 }).map((_, c) => {
            const isFilled = cells.some(cell => cell.row === r && cell.col === c);
            return (
              <div
                key={c}
                className={`mini-cell ${isFilled ? `color-${colorIdx}` : 'empty'}`}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [game, setGameState] = useState<GameState | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const sessionGenRef = useRef(0)
  const queueRef = useRef<Promise<void>>(Promise.resolve())
  const timerRef = useRef<number | null>(null)
  const pendingCountRef = useRef(0)
  const gameRef = useRef<GameState | null>(null)

  const updateGameState = (newState: GameState | null) => {
    setGameState(newState)
    gameRef.current = newState
  }

  // Reschedules gravity timer from the server's authoritative interval when the queue is idle
  const scheduleNextGravityTimer = useCallback(() => {
    const currentGen = sessionGenRef.current

    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }

    const currentGame = gameRef.current
    if (!currentGame || currentGame.status !== "playing" || currentGen !== sessionGenRef.current) {
      return
    }

    const interval = currentGame.gravity_interval_ms
    timerRef.current = window.setTimeout(() => {
      if (currentGen !== sessionGenRef.current) return

      enqueueAction(async () => {
        const g = gameRef.current
        if (g && g.status === "playing") {
          await tickGame(g.id)
        }
      })
    }, interval)
  }, [])

  // Sequences async mutations to guarantee zero overlapping requests and proper timer scheduling
  const enqueueAction = useCallback((actionFn: () => Promise<void>) => {
    const currentGen = sessionGenRef.current

    // Cancel timer immediately upon enqueuing
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }

    pendingCountRef.current += 1

    queueRef.current = queueRef.current.then(async () => {
      if (currentGen !== sessionGenRef.current) {
        pendingCountRef.current -= 1
        return
      }

      try {
        await actionFn()
      } catch (err) {
        console.error("Action execution failed:", err)
      } finally {
        pendingCountRef.current -= 1

        // Reschedule only if the session hasn't changed and queue is idle
        if (currentGen === sessionGenRef.current && pendingCountRef.current === 0) {
          scheduleNextGravityTimer()
        }
      }
    })
  }, [scheduleNextGravityTimer])

  // Starts or restarts a game session on the backend
  const startGame = async () => {
    sessionGenRef.current += 1
    const currentGen = sessionGenRef.current

    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    pendingCountRef.current = 0
    queueRef.current = Promise.resolve()

    updateGameState(null)
    setError(null)

    try {
      const response = await fetch('/api/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (currentGen !== sessionGenRef.current) return

      if (!response.ok) {
        throw new Error('Failed to create game session')
      }
      const data: GameState = await response.json()
      if (currentGen !== sessionGenRef.current) return

      if (data) {
        updateGameState(data)
        scheduleNextGravityTimer()
      }
    } catch (err: any) {
      if (currentGen === sessionGenRef.current) {
        setError(err.message || 'Error communicating with server')
      }
    }
  }

  // Shifts the active piece in the specified direction
  const movePiece = async (direction: "left" | "right" | "down") => {
    const currentGen = sessionGenRef.current
    const currentGame = gameRef.current
    if (!currentGame || currentGame.status === "game_over") return

    try {
      const response = await fetch(`/api/games/${currentGame.id}/move`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ direction })
      })
      if (currentGen !== sessionGenRef.current) return

      if (response.ok) {
        const data: GameState = await response.json()
        if (currentGen !== sessionGenRef.current) return
        if (data) {
          updateGameState(data)
        }
      }
    } catch (err) {
      console.error('Movement request failed:', err)
    }
  }

  // Triggers standard automatic gravity ticks on the backend
  const tickGame = async (gameId: string) => {
    const currentGen = sessionGenRef.current
    try {
      const response = await fetch(`/api/games/${gameId}/tick`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (currentGen !== sessionGenRef.current) return

      if (response.ok) {
        const data: GameState = await response.json()
        if (currentGen !== sessionGenRef.current) return
        if (data) {
          updateGameState(data)
        }
      }
    } catch (err) {
      console.error('Tick request failed:', err)
    }
  }

  // Triggers hold swap on the backend
  const holdPiece = async () => {
    const currentGen = sessionGenRef.current
    const currentGame = gameRef.current
    if (!currentGame || currentGame.status === "game_over" || !currentGame.can_hold) return

    try {
      const response = await fetch(`/api/games/${currentGame.id}/hold`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (currentGen !== sessionGenRef.current) return

      if (response.ok) {
        const data: GameState = await response.json()
        if (currentGen !== sessionGenRef.current) return
        if (data) {
          updateGameState(data)
        }
      }
    } catch (err) {
      console.error('Hold request failed:', err)
    }
  }

  // Set up keyboard event listeners for movement and hold
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const currentGame = gameRef.current
      if (!currentGame || currentGame.status === "game_over") return

      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault()
        enqueueAction(holdPiece)
        return
      }

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          enqueueAction(() => movePiece('left'))
          break
        case 'ArrowRight':
          e.preventDefault()
          enqueueAction(() => movePiece('right'))
          break
        case 'ArrowDown':
          e.preventDefault()
          enqueueAction(() => movePiece('down'))
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [enqueueAction])

  // Safely cleanup timers on unmount and React StrictMode transitions
  useEffect(() => {
    return () => {
      sessionGenRef.current += 1
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [])

  // Identifies if coordinates belong to the falling piece
  const getActivePieceCellIndex = (r: number, c: number): number | null => {
    const currentGame = gameRef.current
    if (!currentGame || !currentGame.active_piece) return null
    const isActive = currentGame.active_piece.cells.some(cell => cell.row === r && cell.col === c)
    return isActive ? SHAPE_INDICES[currentGame.active_piece.shape] : null
  }

  return (
    <div className="app-container">
      <header>
        <h1>DECOUPLED TETRIS STUDY</h1>
        <div className="subtitle">Authoritative FastAPI Backend & Stateless React Frontend</div>
      </header>

      {error && <div style={{ color: '#f00000', marginBottom: '1rem', fontWeight: 'bold' }}>{error}</div>}

      <div className="game-layout">
        {/* Sidebar Controls and Session Panel */}
        <div className="sidebar">
          <div className="panel">
            <h3>SESSION STATUS</h3>
            <div className="status-row">
              <span className="status-label">Status:</span>
              <span className={`status-value ${game ? `status-${game.status}` : 'status-no_session'}`}>
                {game ? game.status.replace('_', ' ') : 'No Session'}
              </span>
            </div>
            {game && (
              <div className="status-row">
                <span className="status-label">Game ID:</span>
                <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#aaa' }}>
                  {game.id.substring(0, 8)}...
                </span>
              </div>
            )}
          </div>

          {/* NEXT PREVIEW PANEL */}
          <div className="panel">
            <h3>NEXT PIECE</h3>
            <MiniGrid shape={game ? game.next_piece : null} />
          </div>

          {/* HOLD SLOT PANEL */}
          <div className="panel">
            <h3>HOLD SLOT</h3>
            <MiniGrid shape={game ? game.hold_piece : null} />
            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '0.5rem' }}
              onClick={() => enqueueAction(holdPiece)}
              disabled={!game || game.status === "game_over" || !game.can_hold}
            >
              Hold Piece (C)
            </button>
          </div>

          {/* SCORE & PROGRESSION HUD PANEL */}
          <div className="panel">
            <h3>PROGRESSION</h3>
            <div className="hud-panel">
              <div className="hud-row">
                <span className="hud-label">Score:</span>
                <span className="hud-value">{game ? game.score : 0}</span>
              </div>
              <div className="hud-row">
                <span className="hud-label">Lines:</span>
                <span className="hud-value">{game ? game.total_lines : 0}</span>
              </div>
              <div className="hud-row">
                <span className="hud-label">Level:</span>
                <span className="hud-value">{game ? game.level : 1}</span>
              </div>
              <div className="hud-row">
                <span className="hud-label">Interval:</span>
                <span className="hud-value">{game ? `${game.gravity_interval_ms}ms` : '500ms'}</span>
              </div>
            </div>
          </div>

          <div className="panel">
            <h3>CONTROLS</h3>
            <div className="control-list">
              <div className="control-item">
                <span className="control-desc">Move Left</span>
                <span className="control-key">◀ ArrowLeft</span>
              </div>
              <div className="control-item">
                <span className="control-desc">Move Right</span>
                <span className="control-key">ArrowRight ▶</span>
              </div>
              <div className="control-item">
                <span className="control-desc">Soft Drop</span>
                <span className="control-key">▼ ArrowDown</span>
              </div>
              <div className="control-item">
                <span className="control-desc">Hold Piece</span>
                <span className="control-key">C</span>
              </div>
            </div>
          </div>

          <button className="btn btn-primary btn-reset-block" onClick={startGame}>
            {game ? 'Restart Session' : 'Start Session'}
          </button>
        </div>

        {/* Center Minimalist Board Rendering */}
        <div className="board-container">
          {!game ? (
            <div className="board" style={{ position: 'relative' }}>
              <div className="overlay">
                <h2 style={{ color: '#fff', textShadow: '0 0 10px rgba(255,255,255,0.2)' }}>TETRIS STUDY</h2>
                <button className="btn" onClick={startGame}>Start New Game</button>
              </div>
              {Array.from({ length: 20 }).map((_, r) => (
                Array.from({ length: 10 }).map((_, c) => (
                  <div key={`${r}-${c}`} className="cell color-0" />
                ))
              ))}
            </div>
          ) : (
            <div className="board">
              {Array.from({ length: 20 }).map((_, r) => (
                Array.from({ length: 10 }).map((_, c) => {
                  const activeIndex = getActivePieceCellIndex(r, c)
                  if (activeIndex !== null) {
                    return (
                      <div
                        key={`${r}-${c}`}
                        className={`cell color-${activeIndex} cell-active`}
                        style={{ color: activeIndex === 1 ? '#00f0f0' : activeIndex === 2 ? '#0018f0' : activeIndex === 3 ? '#f0a000' : activeIndex === 4 ? '#f0f000' : activeIndex === 5 ? '#00f000' : activeIndex === 6 ? '#a000f0' : '#f00000' }}
                      />
                    )
                  }
                  const settledValue = game.board[r][c]
                  return (
                    <div
                      key={`${r}-${c}`}
                      className={`cell color-${settledValue}`}
                    />
                  )
                })
              ))}

              {game.status === "game_over" && (
                <div className="overlay">
                  <h2>GAME OVER</h2>
                  <button className="btn" onClick={startGame}>Play Again</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}