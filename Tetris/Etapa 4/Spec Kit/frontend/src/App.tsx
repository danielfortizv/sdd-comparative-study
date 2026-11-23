import { useEffect, useState } from 'react';
import { useGame } from './hooks/useGame';
import { useDuel } from './hooks/useDuel';
import { Board } from './components/Board';
import { DuelBoard } from './components/DuelBoard';
import { GameControls } from './components/GameControls';
import { GameOverModal } from './components/GameOverModal';
import { HighScoresPanel } from './components/HighScoresPanel';

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
  const [mode, setMode] = useState<'solo' | 'duel'>('solo');
  const [inputRoomId, setInputRoomId] = useState('');

  const {
    game,
    loading,
    error,
    startGame,
    move,
    hold,
    highScores,
    scoresLoading,
    scoresError
  } = useGame();

  const {
    assignedSeat,
    roomState,
    error: duelError,
    loading: duelLoading,
    connect: connectDuel,
    disconnect: disconnectDuel,
    sendAction: sendDuelAction
  } = useDuel();

  // Keyboard controls listener for manual movement (Solo only)
  useEffect(() => {
    if (mode !== 'solo') return;
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
        case 'ArrowUp':
          e.preventDefault();
          move('cw');
          break;
        case 'z':
        case 'Z':
          e.preventDefault();
          move('ccw');
          break;
        case 'c':
        case 'C':
          e.preventDefault();
          hold();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mode, game, move, hold]);

  const handleCreateRoom = () => {
    connectDuel();
  };

  const handleJoinRoom = () => {
    if (inputRoomId.trim()) {
      connectDuel(inputRoomId.trim());
    }
  };

  return (
    <div className="app-container">
      <header className="game-header">
        <h1>FastAPI-React Tetris</h1>
        <div className="mode-selector" style={{ display: 'flex', justifyContent: 'center', gap: '20px', margin: '15px 0' }}>
          <button
            onClick={() => { setMode('solo'); disconnectDuel(); }}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
              background: mode === 'solo' ? '#00ffff' : '#333',
              color: mode === 'solo' ? '#000' : '#fff'
            }}
          >
            Solo Play
          </button>
          <button
            onClick={() => setMode('duel')}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
              background: mode === 'duel' ? '#ff00ff' : '#333',
              color: mode === 'duel' ? '#000' : '#fff'
            }}
          >
            Real-Time Duel
          </button>
        </div>
      </header>

      <main className="game-body">
        {mode === 'solo' ? (
          <>
            {error && <div className="error-message">Error: {error}</div>}

            {!game ? (
              <div className="start-screen-layout" style={{ display: 'flex', gap: '40px', justifyContent: 'center', alignItems: 'flex-start', flexWrap: 'wrap', width: '100%' }}>
                <div className="start-screen" style={{ maxWidth: '400px', flex: '1' }}>
                  <p>Welcome to Tetris study game core!</p>
                  <button className="restart-btn" onClick={startGame} disabled={loading}>
                    {loading ? 'Starting...' : 'Start New Game'}
                  </button>
                </div>
                <div className="side-panel leaderboard-start" style={{ width: '320px', padding: '15px', background: '#1e1e1e', borderRadius: '8px' }}>
                  <HighScoresPanel scores={highScores} loading={scoresLoading} error={scoresError} />
                </div>
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

                  <div className="status-panel" style={{ marginBottom: '15px' }}>
                    <h3>Game Session</h3>
                    <p>ID: <span className="session-id">{game?.id?.slice(0, 8)}...</span></p>
                    <p>Status: <strong className={`status-${game?.status}`}>{game?.status?.toUpperCase()}</strong></p>
                  </div>

                  <div className="leaderboard-panel-in-game" style={{ padding: '15px', background: '#1e1e1e', borderRadius: '8px', marginBottom: '15px' }}>
                    <HighScoresPanel scores={highScores} loading={scoresLoading} error={scoresError} />
                  </div>

                  <GameControls onRestart={startGame} status={game?.status} />
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="duel-mode-layout" style={{ width: '100%', maxWidth: '900px', margin: '0 auto' }}>
            {duelError && <div className="error-message" style={{ background: 'rgba(255,0,0,0.2)', border: '1px solid red', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>Error: {duelError}</div>}

            {!roomState ? (
              <div className="duel-lobby-controls" style={{ textAlign: 'center', background: '#1e1e24', padding: '30px', borderRadius: '8px' }}>
                <h2>Two-Player Real-Time Duel</h2>
                <p style={{ color: '#aaa', marginBottom: '25px' }}>Engage in a competitive Tetris match using WebSockets. Both players share the same random tetromino stream!</p>
                
                <div className="lobby-actions" style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '360px', margin: '0 auto' }}>
                  <button
                    className="restart-btn"
                    onClick={handleCreateRoom}
                    disabled={duelLoading}
                    style={{ background: '#ff00ff', color: '#fff', fontSize: '16px', padding: '12px' }}
                  >
                    {duelLoading ? 'Connecting...' : 'Create New Duel Room'}
                  </button>

                  <div className="divider" style={{ borderTop: '1px solid #333', margin: '10px 0' }}>OR</div>

                  <div className="join-group" style={{ display: 'flex', gap: '10px' }}>
                    <input
                      type="text"
                      placeholder="Enter Room ID"
                      value={inputRoomId}
                      onChange={(e) => setInputRoomId(e.target.value)}
                      style={{ flex: '1', padding: '10px', borderRadius: '4px', border: '1px solid #555', background: '#0a0a0f', color: '#fff' }}
                    />
                    <button
                      onClick={handleJoinRoom}
                      disabled={duelLoading || !inputRoomId.trim()}
                      style={{ padding: '10px 20px', borderRadius: '4px', border: 'none', background: '#00ffff', color: '#000', fontWeight: 'bold', cursor: 'pointer' }}
                    >
                      Join
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <DuelBoard
                roomState={roomState}
                assignedSeat={assignedSeat!}
                sendAction={sendDuelAction}
                disconnect={disconnectDuel}
              />
            )}
          </div>
        )}
      </main>

      {mode === 'solo' && (
        <GameOverModal
          show={game?.status === 'game_over'}
          onRestart={startGame}
        />
      )}
    </div>
  );
}

export default App;
