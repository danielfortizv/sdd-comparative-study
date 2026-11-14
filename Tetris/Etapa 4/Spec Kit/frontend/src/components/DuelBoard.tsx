import React, { useRef, useEffect } from 'react';
import { WSPlayerState, WSDuelRoomState } from '../hooks/useDuel';

interface DuelSingleBoardProps {
  playerState: WSPlayerState | null;
  title: string;
  isOwnSeat: boolean;
}

export const DuelSingleBoard: React.FC<DuelSingleBoardProps> = ({ playerState, title, isOwnSeat }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const cssWidth = canvas.clientWidth || 200;
      const cssHeight = canvas.clientHeight || 400;

      canvas.width = cssWidth * dpr;
      canvas.height = cssHeight * dpr;
      ctx.scale(dpr, dpr);

      // Background
      ctx.fillStyle = '#0c0c10';
      ctx.fillRect(0, 0, cssWidth, cssHeight);

      if (!playerState) {
        // Render waiting/vacant state
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Waiting for player...', cssWidth / 2, cssHeight / 2);
        return;
      }

      const { board, active_piece } = playerState;
      const cols = 10;
      const rows = 20;
      const cellWidth = cssWidth / cols;
      const cellHeight = cssHeight / rows;

      // Copy of the board to merge active piece
      const displayBoard: number[][] = board.map(row => [...row]);

      if (active_piece) {
        const { type, cells: pieceCells } = active_piece;
        const colorMap: Record<string, number> = {
          I: 1, O: 2, T: 3, S: 4, Z: 5, J: 6, L: 7
        };
        const colorIndex = colorMap[type] || 0;

        pieceCells.forEach(([row, col]) => {
          if (row >= 0 && row < 20 && col >= 0 && col < 10) {
            displayBoard[row][col] = colorIndex;
          }
        });
      }

      const colors = [
        'rgba(255, 255, 255, 0.03)', // empty (case 0)
        '#00f0f0', // I (Cyan)
        '#f0f000', // O (Yellow)
        '#a000f0', // T (Purple)
        '#00f000', // S (Green)
        '#f00000', // Z (Red)
        '#0000f0', // J (Blue)
        '#f0a000', // L (Orange)
      ];

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const cellVal = displayBoard[r][c];
          const x = c * cellWidth;
          const y = r * cellHeight;

          if (cellVal === 0) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.03)';
            ctx.fillRect(x, y, cellWidth, cellHeight);
          } else {
            ctx.fillStyle = colors[cellVal];
            ctx.fillRect(x, y, cellWidth, cellHeight);

            // Block decoration
            ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
            ctx.fillRect(x, y, cellWidth, 2);
            ctx.fillRect(x, y, 2, cellHeight);

            ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
            ctx.fillRect(x, y + cellHeight - 2, cellWidth, 2);
            ctx.fillRect(x + cellWidth - 2, y, 2, cellHeight);
          }

          // Borders
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
          ctx.lineWidth = 1;
          ctx.strokeRect(x, y, cellWidth, cellHeight);
        }
      }
    };

    draw();

    // Setup Resize and observation
    const resizeObserver = new ResizeObserver(() => {
      draw();
    });

    if (canvas.parentElement) {
      resizeObserver.observe(canvas.parentElement);
    } else {
      resizeObserver.observe(canvas);
    }

    window.addEventListener('resize', draw);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', draw);
    };
  }, [playerState]);

  return (
    <div className={`duel-board-column ${isOwnSeat ? 'own-board' : 'opponent-board'}`}>
      <h3 className="board-title" style={{ textAlign: 'center', margin: '5px 0' }}>
        {title} {isOwnSeat && <span style={{ color: '#00ff00' }}>(You)</span>}
      </h3>
      
      {playerState && (
        <div className="duel-stats-summary" style={{ display: 'flex', justifyContent: 'space-around', margin: '5px 0', fontSize: '13px' }}>
          <div>Score: <strong style={{ color: '#f0a000' }}>{playerState.score}</strong></div>
          <div>Lines: <strong style={{ color: '#00ffff' }}>{playerState.total_lines}</strong></div>
          <div>Level: <strong style={{ color: '#a000f0' }}>{playerState.level}</strong></div>
        </div>
      )}

      <div className="board-container" style={{ position: 'relative', width: '200px', height: '400px', margin: '0 auto' }}>
        <canvas
          ref={canvasRef}
          className="board-canvas"
          style={{ width: '200px', height: '400px', display: 'block', border: '2px solid #333' }}
          data-board-state={playerState ? JSON.stringify(playerState.board) : 'null'}
          data-active-piece={playerState && playerState.active_piece ? JSON.stringify(playerState.active_piece) : 'null'}
          data-seq={playerState ? playerState.last_processed_seq_num : '0'}
          data-gen={playerState ? playerState.active_piece_generation : '0'}
          aria-label={`Duel ${title}`}
          role="img"
        />
      </div>

      {playerState && (
        <div className="duel-panels-footer" style={{ display: 'flex', justifyContent: 'space-around', margin: '5px 0', fontSize: '12px' }}>
          <div>Hold: <strong style={{ color: '#00ff00' }}>{playerState.hold_piece || 'None'}</strong></div>
          <div>Next: <strong style={{ color: '#ff00ff' }}>{playerState.next_piece}</strong></div>
        </div>
      )}
    </div>
  );
};

interface DuelBoardProps {
  roomState: WSDuelRoomState;
  assignedSeat: 'seat_1' | 'seat_2';
  sendAction: (actionType: 'left' | 'right' | 'down' | 'cw' | 'ccw' | 'hold') => void;
  disconnect: () => void;
}

export const DuelBoard: React.FC<DuelBoardProps> = ({
  roomState,
  assignedSeat,
  sendAction,
  disconnect
}) => {
  const ownSeat = assignedSeat;
  const opponentSeat = assignedSeat === 'seat_1' ? 'seat_2' : 'seat_1';

  const ownState = roomState[ownSeat];
  const opponentState = roomState[opponentSeat];

  // Capture keyboard events
  useEffect(() => {
    if (roomState.status !== 'active') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Map ArrowUp -> Clockwise, Z/z -> Counterclockwise, ArrowLeft -> Left, ArrowRight -> Right, ArrowDown -> Down, C/c or Shift -> Hold
      switch (e.key) {
        case 'ArrowLeft':
          sendAction('left');
          e.preventDefault();
          break;
        case 'ArrowRight':
          sendAction('right');
          e.preventDefault();
          break;
        case 'ArrowDown':
          sendAction('down');
          e.preventDefault();
          break;
        case 'ArrowUp':
          sendAction('cw');
          e.preventDefault();
          break;
        case 'z':
        case 'Z':
          sendAction('ccw');
          e.preventDefault();
          break;
        case 'c':
        case 'C':
        case 'Shift':
          sendAction('hold');
          e.preventDefault();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [roomState.status, sendAction]);

  return (
    <div className="duel-wrapper" style={{ padding: '10px', background: '#121218', borderRadius: '8px', color: '#fff' }}>
      <div className="duel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #333', paddingBottom: '8px' }}>
        <div>
          Room ID: <code style={{ color: '#00ffff' }}>{roomState.room_id}</code>
        </div>
        <div>
          Status: <strong style={{ color: roomState.status === 'active' ? '#00ff00' : '#ff9900' }}>{roomState.status.toUpperCase()}</strong>
        </div>
        <button className="btn-exit" onClick={disconnect} style={{ background: '#ff3333', border: 'none', color: '#fff', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' }}>
          Exit Duel
        </button>
      </div>

      {roomState.status === 'waiting' && (
        <div className="waiting-lobby" style={{ textAlign: 'center', padding: '20px' }}>
          <h2 style={{ color: '#f0a000' }}>Waiting for an opponent to join...</h2>
          <p style={{ color: '#aaa' }}>Share the Room ID above with a friend to begin the real-time duel.</p>
        </div>
      )}

      {roomState.status === 'finished' && (
        <div className="game-over-panel" style={{ textAlign: 'center', padding: '20px', background: 'rgba(255, 0, 0, 0.1)', borderRadius: '6px', margin: '15px 0' }}>
          <h2 style={{ color: roomState.outcome === 'draw' ? '#aaa' : (roomState.outcome === `${ownSeat}_win` ? '#00ff00' : '#ff3333') }}>
            {roomState.outcome === 'draw' ? 'DRAW!' : (roomState.outcome === `${ownSeat}_win` ? 'VICTORY!' : 'DEFEAT!')}
          </h2>
          <p style={{ color: '#eee', fontSize: '14px' }}>{roomState.reason}</p>
        </div>
      )}

      <div className="duel-boards" style={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', marginTop: '15px' }}>
        {/* Own Seat Board */}
        <DuelSingleBoard
          playerState={ownState}
          title={ownSeat === 'seat_1' ? 'Seat 1' : 'Seat 2'}
          isOwnSeat={true}
        />

        {/* Opponent Seat Board */}
        <DuelSingleBoard
          playerState={opponentState}
          title={opponentSeat === 'seat_1' ? 'Seat 1' : 'Seat 2'}
          isOwnSeat={false}
        />
      </div>
    </div>
  );
};
