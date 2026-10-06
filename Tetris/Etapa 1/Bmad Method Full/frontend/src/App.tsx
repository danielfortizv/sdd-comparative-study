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
  active_piece: ActivePiece
}

const SHAPE_INDICES: Record<string, number> = {
  I: 1, J: 2, L: 3, O: 4, S: 5, T: 6, Z: 7
}

export default function App() {
  const [game, setGameState] = useState<GameState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<number | null>(null)

  // Starts or restarts a game session on the backend
  const startGame = async () => {
    try {
      setError(null)
      const response = await fetch('/api/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (!response.ok) {
        throw new Error('Failed to create game session')
      }
      const data: GameState = await response.json()
      setGameState(data)
    } catch (err: any) {
      setError(err.message || 'Error communicating with server')
    }
  }

  // Shifts the active piece in the specified direction
  const movePiece = useCallback(async (direction: "left" | "right" | "down") => {
    if (!game || game.status === "game_over") return

    try {
      const response = await fetch(`/api/games/${game.id}/move`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ direction })
      })
      if (response.ok) {
        const data: GameState = await response.json()
        setGameState(data)
      }
    } catch (err) {
      console.error('Movement request failed:', err)
    }
  }, [game])

  // Triggers standard automatic gravity ticks on the backend
  const tickGame = useCallback(async (gameId: string) => {
    try {
      const response = await fetch(`/api/games/${gameId}/tick`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        const data: GameState = await response.json()
        setGameState(data)
      }
    } catch (err) {
      console.error('Tick request failed:', err)
    }
  }, [])

  // Set up manual movement keyboard event listeners
  useEffect(() => {
    if (!game || game.status === "game_over") return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          movePiece('left')
          break
        case 'ArrowRight':
          e.preventDefault()
          movePiece('right')
          break
        case 'ArrowDown':
          e.preventDefault()
          movePiece('down')
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [game, movePiece])

  // Setup client-side gravity timer (approximately every 500ms)
  useEffect(() => {
    if (!game || game.status === "game_over") {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      return
    }

    const gameId = game.id
    timerRef.current = window.setInterval(() => {
      tickGame(gameId)
    }, 500)

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [game?.id, game?.status, tickGame])

  // Identifies if coordinates belong to the falling piece
  const getActivePieceCellIndex = (r: number, c: number): number | null => {
    if (!game || !game.active_piece) return null
    const isActive = game.active_piece.cells.some(cell => cell.row === r && cell.col === c)
    return isActive ? SHAPE_INDICES[game.active_piece.shape] : null
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
