import { useEffect } from 'react';
import { useGame } from './hooks/useGame';
import { Board } from './components/Board';
import { GameControls } from './components/GameControls';
import { GameOverModal } from './components/GameOverModal';

const PREVIEW_TEMPLATES: Record<string, number[][]> = {
  I: [[1, 1, 1, 1], [0, 0, 0, 0]],
  O: [[0, 2, 2, 0], [0, 2, 2, 0]],
  T: [[0, 3, 0, 0], [3, 3, 3, 0]],
  S: [[0, 4, 4, 0], [4, 4, 0, 0]],
  Z: [[5, 5, 0, 0], [0, 5, 5, 0]],
  J: [[6, 0, 0, 0], [6, 6, 6, 0]],
  L: [[0, 0, 7, 0], [7, 7, 7, 0]],
};

function PiecePreview({ type }: { readonly type: string | null | undefined }) {
  if (!type) {
    return <div className="preview-empty">EMPTY</div>;
  }
  const grid = PREVIEW_TEMPLATES[type] || [[0, 0, 0, 0], [0, 0, 0, 0]];
  const getClassForPreviewCell = (val: number): string => {
    switch (val) {
      case 1: return 'cell cell-i';
      case 2: return 'cell cell-o';
      case 3: return 'cell cell-t';
      case 4: return 'cell cell-s';
      case 5: return 'cell cell-z';
      case 6: return 'cell cell-j';
      case 7: return 'cell cell-l';
      default: return 'cell cell-empty';
    }
  };
  return (
    <div className="preview-grid">
      {grid.map((row, r) => {
        const rowKey = r === 0 ? 'prev-row-top' : 'prev-row-bottom';
        return (
          <div key={rowKey} className="preview-row">
            {row.map((cell, c) => (
              <div key={`prev-cell-${rowKey}-${c}`} className={getClassForPreviewCell(cell)} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

function App() {
  const { game, loading, error, startGame, move, hold } = useGame();

  // Keyboard controls listener for manual movement
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (game?.status !== 'playing') return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          move('left');
          break;
        case 'ArrowRight':
          e.preventDefault();
          move('right');
          break;
        case 'ArrowDown':
          e.preventDefault();
          move('down');
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [game, move]);

  return (
    <div className="app-container">
      <header className="game-header">
        <h1>FastAPI-React Tetris</h1>
      </header>

      <main className="game-body">
        {error && <div className="error-message">Error: {error}</div>}

        {!game ? (
          <div className="start-screen">
            <p>Welcome to Tetris study game core!</p>
            <button className="restart-btn" onClick={startGame} disabled={loading}>
              {loading ? 'Starting...' : 'Start New Game'}
            </button>
          </div>
        ) : (
          <div className="game-layout">
            <Board game={game} />
            <div className="side-panel">
              <div className="stats-panel">
                <h3>Statistics</h3>
                <p>Score: <span className="stat-value">{game?.score ?? 0}</span></p>
                <p>Lines: <span className="stat-value">{game?.total_lines ?? 0}</span></p>
                <p>Level: <span className="stat-value">{game?.level ?? 1}</span></p>
                <p>Gravity: <span className="stat-value">{game?.gravity_interval_ms ?? 500} ms</span></p>
              </div>

              <div className="preview-panel">
                <h3>Next Piece</h3>
                <PiecePreview type={game?.next_piece} />
              </div>

              <div className="hold-panel">
                <h3>Hold Piece</h3>
                <PiecePreview type={game?.hold_piece} />
                <button
                  className="hold-btn"
                  onClick={hold}
                  disabled={!game?.can_hold || game?.status === 'game_over'}
                >
                  Hold (C Key)
                </button>
              </div>

              <div className="status-panel">
                <h3>Game Session</h3>
                <p>ID: <span className="session-id">{game?.id?.slice(0, 8)}...</span></p>
                <p>Status: <strong className={`status-${game?.status}`}>{game?.status?.toUpperCase()}</strong></p>
              </div>
              <GameControls onRestart={startGame} status={game?.status} />
            </div>
          </div>
        )}
      </main>

      <GameOverModal
        show={game?.status === 'game_over'}
        onRestart={startGame}
      />
    </div>
  );
}

export default App;
