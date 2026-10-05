import { useTetris } from './useTetris';

export default function App() {
  const { gameState, error, loading, startNewGame } = useTetris();

  // Construct the visible board by overlaying the active piece onto the settled board
  const renderBoard = () => {
    if (!gameState) return Array(20).fill(null).map(() => Array(10).fill(null));

    // Clone settled board
    const visibleBoard = gameState.board.map(row => [...row]);

    // Superimpose active piece cells
    if (gameState.active_piece) {
      const { type, cells } = gameState.active_piece;
      cells.forEach(cell => {
        if (cell.row >= 0 && cell.row < 20 && cell.col >= 0 && cell.col < 10) {
          visibleBoard[cell.row][cell.col] = type;
        }
      });
    }

    return visibleBoard;
  };

  const board = renderBoard();

  return (
    <div className="app-container">
      <header className="header">
        <h1>Tetris Study <span>Stage 1</span></h1>
        <p className="subtitle">Option A: Decoupled Backend-Authoritative Greenfield Prototype</p>
      </header>

      {error && (
        <div className="error-banner">
          <p><strong>Error:</strong> {error}</p>
          <button onClick={startNewGame}>Retry Connection</button>
        </div>
      )}

      <main className="main-content">
        <div className="game-area">
          <div className="grid-container">
            {board.map((row, rIdx) => (
              <div key={`row-${rIdx}`} className="grid-row">
                {row.map((cell, cIdx) => (
                  <div
                    key={`cell-${rIdx}-${cIdx}`}
                    className={`grid-cell ${cell ? `cell-${cell}` : 'cell-empty'}`}
                    title={`Row ${rIdx}, Col ${cIdx}`}
                  />
                ))}
              </div>
            ))}

            {gameState?.status === 'game_over' && (
              <div className="game-over-overlay">
                <div className="game-over-content">
                  <h2>GAME OVER</h2>
                  <p>The falling tetromino immediately collided with settled blocks at spawn.</p>
                  <button className="restart-btn primary" onClick={startNewGame}>
                    Play Again
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <aside className="sidebar">
          <div className="card status-card">
            <h3>Session Status</h3>
            <div className="status-item">
              <span className="label">Status:</span>
              <span className={`value status-${gameState?.status || 'connecting'}`}>
                {gameState?.status ? gameState.status.toUpperCase() : 'CONNECTING...'}
              </span>
            </div>
            <div className="status-item">
              <span className="label">Session ID:</span>
              <span className="value session-id" title={gameState?.game_id || 'N/A'}>
                {gameState?.game_id ? `${gameState.game_id.substring(0, 8)}...` : 'N/A'}
              </span>
            </div>
          </div>

          <div className="card controls-card">
            <h3>Controls</h3>
            <div className="control-list">
              <div className="control-item">
                <kbd>←</kbd> or <kbd>A</kbd>
                <span>Move Left</span>
              </div>
              <div className="control-item">
                <kbd>→</kbd> or <kbd>D</kbd>
                <span>Move Right</span>
              </div>
              <div className="control-item">
                <kbd>↓</kbd> or <kbd>S</kbd>
                <span>Soft Drop</span>
              </div>
            </div>
            <div className="gravity-notice">
              <div className="ticker-light animated"></div>
              <span>Gravity tick frequency: <strong>500 ms</strong></span>
            </div>
          </div>

          <button className="restart-btn" disabled={loading} onClick={startNewGame}>
            {loading ? 'Starting...' : 'Restart Game'}
          </button>
        </aside>
      </main>

      <footer className="footer">
        <p>Tetris Study Greenfield Project &bull; Created using BMad Specification Contract</p>
      </footer>
    </div>
  );
}
