import { useEffect, useState, useRef } from 'react';
import { GameState, TetrominoType } from './types';
import { TetrisBoard } from './components/TetrisBoard';
import { GameStatus as GameStatusPanel } from './components/GameStatus';

const PREVIEW_SHAPES: Record<TetrominoType, [number, number][]> = {
  'I': [[0, 0], [0, 1], [0, 2], [0, 3]],
  'O': [[0, 0], [0, 1], [1, 0], [1, 1]],
  'T': [[0, 1], [1, 0], [1, 1], [1, 2]],
  'S': [[0, 1], [0, 2], [1, 0], [1, 1]],
  'Z': [[0, 0], [0, 1], [1, 1], [1, 2]],
  'J': [[0, 0], [1, 0], [1, 1], [1, 2]],
  'L': [[0, 2], [1, 0], [1, 1], [1, 2]],
};

type ActionType = 'move' | 'tick' | 'hold';
type MoveDirection = 'left' | 'right' | 'down';

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

export default function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<number>(0);

  // References to keep state highly accurate within the async FIFO promise chain
  const gameStateRef = useRef<GameState | null>(null);
  const generationIdRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Strict FIFO queue & concurrency refs
  const queuePromiseRef = useRef<Promise<void>>(Promise.resolve());
  const queuedMutationsCountRef = useRef<number>(0);

  const updateGameState = (state: GameState | null) => {
    setGameState(state);
    gameStateRef.current = state;
  };

  // Helper to schedule the next gravity tick
  const scheduleNextTick = (state: GameState, genId: number) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (state.status === 'game_over') return;
    if (generationIdRef.current !== genId) return;
    if (queuedMutationsCountRef.current > 0) return; // Schedule ONLY when mutation queue is idle

    const interval = state.gravity_interval_ms;

    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      if (generationIdRef.current !== genId) return;
      if (queuedMutationsCountRef.current > 0) return; // Ignore if busy

      // Trigger automatic tick in the FIFO queue
      queueMutation('tick');
    }, interval);
  };

  // Helper to start or restart the game
  const startNewGame = async () => {
    // Immediately cancel any existing scheduled timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    // Advance lifecycle generation to preempt/invalidate all older generations and queues
    generationIdRef.current += 1;
    const currentGen = generationIdRef.current;
    setGenerationId(currentGen);

    // Discard and replace the old promise chain
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

      // Post-Transit Ownership Check
      if (generationIdRef.current !== currentGen) return;

      if (!response.ok) {
        throw new Error('Failed to create game session');
      }

      const state = await response.json();

      // Post-JSON Parse Ownership Check
      if (generationIdRef.current !== currentGen) return;

      updateGameState(state);
      
      // Schedule the next gravity tick using the new generation context
      scheduleNextTick(state, currentGen);

    } catch (err) {
      if (generationIdRef.current !== currentGen) return;
      // Connection failure
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
    // Check generation ownership prior to network dispatch
    if (generationIdRef.current !== currentGen) return;
    if (!gameStateRef.current || gameStateRef.current.status === 'game_over') return;

    try {
      const apiId = gameStateRef.current.id;
      const updatedState = await executeMutationAndParse(apiId, actionType, direction);

      // Post-Transit and JSON Parse Ownership Check
      if (generationIdRef.current !== currentGen) return;

      updateGameState(updatedState);

    } catch (err) {
      if (generationIdRef.current !== currentGen) return;
      // Mutation failed
      const message = err instanceof Error ? err.message : String(err);
      setError(`Game operation failed: ${message}`);
    } finally {
      if (generationIdRef.current !== currentGen) return;

      // Decrement queue depth in finally block
      queuedMutationsCountRef.current = Math.max(0, queuedMutationsCountRef.current - 1);

      // Reschedule automatic gravity tick ONLY when the queue is completely idle (Req-S2-31)
      const state = gameStateRef.current;
      if (queuedMutationsCountRef.current === 0 && state && state.status !== 'game_over') {
        scheduleNextTick(state, currentGen);
      }
    }
  };

  // Queue-bound mutating operations
  const queueMutation = (actionType: ActionType, direction?: MoveDirection) => {
    const currentGen = generationIdRef.current;
    
    // Safety guard
    if (currentGen <= 0) return;
    if (!gameStateRef.current || gameStateRef.current.status === 'game_over') return;

    // Immediately cancel any exact previously scheduled timer handle (Req-S2-31)
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    // Increment queue depth synchronously to represent the newly queued manual/auto action
    queuedMutationsCountRef.current += 1;

    // Append to FIFO Promise Chain
    queuePromiseRef.current = queuePromiseRef.current.then(() => 
      processQueueMutation(currentGen, actionType, direction)
    );
  };

  // Start game on mount
  useEffect(() => {
    startNewGame();

    return () => {
      // Invalidate active generation on unmount monotonically to prevent stale callbacks
      generationIdRef.current += 1;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keyboard control listeners with StrictMode setup/cleanup safety (Req-S2-34)
  useEffect(() => {
    if (!gameState || gameState.status === 'game_over') return;

    const handleKeyDown = (event: KeyboardEvent) => {
      let direction: 'left' | 'right' | 'down' | null = null;
      let isHold = false;

      if (event.key === 'ArrowLeft') {
        direction = 'left';
      } else if (event.key === 'ArrowRight') {
        direction = 'right';
      } else if (event.key === 'ArrowDown') {
        direction = 'down';
      } else if (event.key === 'c' || event.key === 'C') {
        isHold = true;
      }

      if (!direction && !isHold) return;

      // Prevent default scrolling/browser actions
      event.preventDefault();

      if (isHold) {
        queueMutation('hold');
      } else if (direction) {
        queueMutation('move', direction);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameState?.id, generationId]);

  // Mini-grid renderer for preview and hold pieces
  const renderMiniGrid = (pieceType: TetrominoType | null) => {
    const rows = [0, 1];
    const cols = [0, 1, 2, 3];
    const cells = pieceType ? PREVIEW_SHAPES[pieceType] || [] : [];

    return (
      <div className="mini-grid">
        {rows.map(r => (
          <div key={r} className="mini-grid-row">
            {cols.map(c => {
              const isActive = cells.some(([pr, pc]) => pr === r && pc === c);
              return (
                <div
                  key={c}
                  className={`mini-grid-cell ${isActive ? 'cell-' + pieceType : 'cell-empty'}`}
                />
              );
            })}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Tetris Study Studio</h1>
        <p className="subtitle">Stage 2 — Option A (Server-Authoritative, Rotation-Free)</p>
      </header>

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
            
            <div className="status-section">
              {/* Hold Container & Button */}
              <div className="hold-panel-container">
                <p className="hold-title">Hold Piece</p>
                {renderMiniGrid(gameState.hold_piece)}
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

              {/* Next Preview Container */}
              <div className="preview-panel-container">
                <p className="preview-title">Next Piece</p>
                {renderMiniGrid(gameState.next_piece)}
              </div>

              <GameStatusPanel 
                gameState={gameState} 
                onRestart={startNewGame} 
                isLoading={loading}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
