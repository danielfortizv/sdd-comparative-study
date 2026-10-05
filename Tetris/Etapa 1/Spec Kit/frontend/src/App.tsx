import { useEffect } from 'react';
import { useGame } from './hooks/useGame';
import { Board } from './components/Board';
import { GameControls } from './components/GameControls';
import { GameOverModal } from './components/GameOverModal';

function App() {
  const { game, loading, error, startGame, move } = useGame();

  // Keyboard controls listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!game || game.status !== 'playing') return;

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
              <div className="status-panel">
                <h3>Game Session</h3>
                <p>ID: <span className="session-id">{game.id.slice(0, 8)}...</span></p>
                <p>Status: <strong className={`status-${game.status}`}>{game.status.toUpperCase()}</strong></p>
              </div>
              <GameControls onRestart={startGame} status={game.status} />
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
