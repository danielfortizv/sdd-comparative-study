import { useEffect, useState, useRef } from 'react';
import { GameState } from './types';
import { TetrisBoard } from './components/TetrisBoard';
import { GameStatus as GameStatusPanel } from './components/GameStatus';
import { HighScoresPanel } from './components/HighScoresPanel';
import { DuelGame } from './components/DuelGame';
import { PiecePreview } from './components/PiecePreview';

type ActionType = 'move' | 'tick' | 'hold' | 'rotate';
type MoveDirection = 'left' | 'right' | 'down' | 'cw' | 'ccw';

const dispatchMutationRequest = (apiId: string, actionType: ActionType, direction?: MoveDirection): Promise<Response> => {
  if (actionType === 'move') {
    return fetch(`/api/games/${apiId}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ direction }),
    });
  }
  if (actionType === 'tick') {
    return fetch(`/api/games/${apiId}/tick`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
  }
  if (actionType === 'rotate') {
    return fetch(`/api/games/${apiId}/rotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ direction }),
    });
  }
  return fetch(`/api/games/${apiId}/hold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
};

const executeMutationAndParse = async (apiId: string, actionType: ActionType, direction?: MoveDirection): Promise<any> => {
  const response = await dispatchMutationRequest(apiId, actionType, direction);
  if (!response.ok) {
    throw new Error('Mutation request failed');
  }
  return response.json();
};

function SoloGame() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<number>(0);
  const [highScoresTrigger, setHighScoresTrigger] = useState<number>(0);

  const gameStateRef = useRef<GameState | null>(null);
  const generationIdRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const queuePromiseRef = useRef<Promise<void>>(Promise.resolve());
  const queuedMutationsCountRef = useRef<number>(0);

  const updateGameState = (state: GameState | null) => {
    const previousStatus = gameStateRef.current?.status;
    setGameState(state);
    gameStateRef.current = state;
    if (state?.status === 'game_over' && previousStatus !== 'game_over') {
      setHighScoresTrigger(prev => prev + 1);
    }
  };

  const scheduleNextTick = (state: GameState, genId: number) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (state.status === 'game_over') return;
    if (generationIdRef.current !== genId) return;
    if (queuedMutationsCountRef.current > 0) return;

    const interval = state.gravity_interval_ms;

    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      if (generationIdRef.current !== genId) return;
      if (queuedMutationsCountRef.current > 0) return;

      queueMutation('tick');
    }, interval);
  };

  const startNewGame = async () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    generationIdRef.current += 1;
    const currentGen = generationIdRef.current;
    setGenerationId(currentGen);

    queuePromiseRef.current = Promise.resolve();
    queuedMutationsCountRef.current = 0;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (generationIdRef.current !== currentGen) return;

      if (!response.ok) {
        throw new Error('Failed to create game session');
      }

      const state = await response.json();

      if (generationIdRef.current !== currentGen) return;

      updateGameState(state);
      scheduleNextTick(state, currentGen);

    } catch (err) {
      if (generationIdRef.current !== currentGen) return;
      const message = err instanceof Error ? err.message : String(err);
      setError(`Could not connect to the Tetris API. Make sure the backend server is running. (${message})`);
    } finally {
      if (generationIdRef.current !== currentGen) return;
      setLoading(false);
    }
  };

  const processQueueMutation = async (
    currentGen: number,
    actionType: ActionType,
    direction?: MoveDirection
  ) => {
    if (generationIdRef.current !== currentGen) return;
    if (!gameStateRef.current || gameStateRef.current.status === 'game_over') return;

    try {
      const apiId = gameStateRef.current.id;
      const updatedState = await executeMutationAndParse(apiId, actionType, direction);

      if (generationIdRef.current !== currentGen) return;

      updateGameState(updatedState);

    } catch (err) {
      if (generationIdRef.current !== currentGen) return;
      const message = err instanceof Error ? err.message : String(err);
      setError(`Game operation failed: ${message}`);
    } finally {
      if (generationIdRef.current !== currentGen) return;

      queuedMutationsCountRef.current = Math.max(0, queuedMutationsCountRef.current - 1);

      const state = gameStateRef.current;
      if (queuedMutationsCountRef.current === 0 && state && state.status !== 'game_over') {
        scheduleNextTick(state, currentGen);
      }
    }
  };

  const queueMutation = (actionType: ActionType, direction?: MoveDirection) => {
    const currentGen = generationIdRef.current;

    if (currentGen <= 0) return;
    if (!gameStateRef.current || gameStateRef.current.status === 'game_over') return;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    queuedMutationsCountRef.current += 1;

    queuePromiseRef.current = queuePromiseRef.current.then(() =>
      processQueueMutation(currentGen, actionType, direction)
    );
  };

  useEffect(() => {
    startNewGame();

    return () => {
      generationIdRef.current += 1;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!gameState || gameState.status === 'game_over') return;

    const handleKeyDown = (event: KeyboardEvent) => {
      let direction: 'left' | 'right' | 'down' | null = null;
      let isHold = false;
      let rotateDir: 'cw' | 'ccw' | null = null;

      if (event.key === 'ArrowLeft') {
        direction = 'left';
      } else if (event.key === 'ArrowRight') {
        direction = 'right';
      } else if (event.key === 'ArrowDown') {
        direction = 'down';
      } else if (event.key === 'ArrowUp') {
        rotateDir = 'cw';
      } else if (event.key === 'z' || event.key === 'Z') {
        rotateDir = 'ccw';
      } else if (event.key === 'c' || event.key === 'C') {
        isHold = true;
      }

      if (!direction && !isHold && !rotateDir) return;

      event.preventDefault();

      if (isHold) {
        queueMutation('hold');
      } else if (direction) {
        queueMutation('move', direction);
      } else if (rotateDir) {
        queueMutation('rotate', rotateDir);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameState?.id, generationId]);

  return (
    <main className="game-container">
      {loading && !gameState && (
        <div className="panel loading-panel">
          <p>Initializing Tetris Session...</p>
        </div>
      )}

      {error && (
        <div className="panel error-panel">
          <p className="error-message">{error}</p>
          <button onClick={startNewGame} className="btn-retry">
            Retry Connection
          </button>
        </div>
      )}

      {gameState && (
        <>
          <div className="board-section">
            <TetrisBoard gameState={gameState} />
          </div>

          <div className="control-section">
            <div className="hold-panel-container">
              <p className="hold-title">Hold Piece</p>
              <PiecePreview pieceType={gameState.hold_piece} />
              <span className={`can-hold-indicator ${gameState.can_hold ? 'available' : 'used'}`}>
                {gameState.can_hold ? 'AVAILABLE' : 'USED'}
              </span>
              <button
                onClick={() => queueMutation('hold')}
                disabled={!gameState.can_hold || gameState.status === 'game_over'}
                className="btn-hold"
              >
                Hold Piece
              </button>
            </div>

            <div className="preview-panel-container">
              <p className="preview-title">Next Piece</p>
              <PiecePreview pieceType={gameState.next_piece} />
            </div>

            <div className="rotation-panel-container">
              <p className="rotation-title">Rotate Piece</p>
              <div className="rotation-buttons">
                <button
                  onClick={() => queueMutation('rotate', 'ccw')}
                  disabled={gameState.status === 'game_over'}
                  className="btn-rotate btn-rotate-ccw"
                >
                  Rotate CCW (Z)
                </button>
                <button
                  onClick={() => queueMutation('rotate', 'cw')}
                  disabled={gameState.status === 'game_over'}
                  className="btn-rotate btn-rotate-cw"
                >
                  Rotate CW (ArrowUp)
                </button>
              </div>
            </div>
          </div>

          <div className="status-section">
            <GameStatusPanel
              gameState={gameState}
              onRestart={startNewGame}
              isLoading={loading}
            />

            <HighScoresPanel trigger={highScoresTrigger} />
          </div>
        </>
      )}
    </main>
  );
}

export default function App() {
  const [mode, setMode] = useState<'solo' | 'duel'>('solo');

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Tetris Study Studio</h1>
        <p className="subtitle">Stage 4 — Option A (Tetromino Rotation, Canvas 2D & Real-time Duel WebSockets)</p>
        <div className="mode-selector" style={{ display: 'flex', gap: '1rem', justifyContent: 'center', margin: '0.5rem 0' }}>
          <button
            onClick={() => setMode('solo')}
            className={`btn-mode ${mode === 'solo' ? 'active' : ''}`}
            style={{
              background: mode === 'solo' ? '#a000f0' : '#1e222f',
              color: '#fff',
              border: '1px solid #2f364d',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              transition: 'background 0.2s',
              fontSize: '0.85rem'
            }}
          >
            Solo Mode
          </button>
          <button
            onClick={() => setMode('duel')}
            className={`btn-mode ${mode === 'duel' ? 'active' : ''}`}
            style={{
              background: mode === 'duel' ? '#a000f0' : '#1e222f',
              color: '#fff',
              border: '1px solid #2f364d',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              transition: 'background 0.2s',
              fontSize: '0.85rem'
            }}
            data-testid="btn-mode-duel"
          >
            Duel Mode
          </button>
        </div>
      </header>

      {mode === 'solo' ? (
        <SoloGame />
      ) : (
        <DuelGame onReturnSolo={() => setMode('solo')} />
      )}
    </div>
  );
}
