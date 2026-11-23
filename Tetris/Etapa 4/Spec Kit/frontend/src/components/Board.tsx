import React, { useRef, useEffect } from 'react';
import { GameSession } from '../types';

interface BoardProps {
  game: GameSession;
}

export const Board: React.FC<BoardProps> = ({ game }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { board, activePiece } = game;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const cssWidth = canvas.clientWidth || 240;
      const cssHeight = canvas.clientHeight || 480;

      // Programmatic backing store scaling:
      canvas.width = cssWidth * dpr;
      canvas.height = cssHeight * dpr;

      // Scale context to automatically handle standard coordinates at device resolution
      ctx.scale(dpr, dpr);

      // Clear the canvas using background color
      ctx.fillStyle = '#0c0c10';
      ctx.fillRect(0, 0, cssWidth, cssHeight);

      const cols = 10;
      const rows = 20;
      const cellWidth = cssWidth / cols;
      const cellHeight = cssHeight / rows;

      // Copy of the board to merge active piece state
      const displayBoard: number[][] = board.map(row => [...row]);

      if (activePiece) {
        const { type, cells: pieceCells } = activePiece;
        const colorMap: Record<string, number> = {
          I: 1,
          O: 2,
          T: 3,
          S: 4,
          Z: 5,
          J: 6,
          L: 7,
        };
        const colorIndex = colorMap[type] || 0;

        pieceCells.forEach(([row, col]) => {
          if (row >= 0 && row < 20 && col >= 0 && col < 10) {
            displayBoard[row][col] = colorIndex;
          }
        });
      }

      // Colors matching CSS variables
      const colors = [
        'rgba(255, 255, 255, 0.03)', // empty (case 0) - matches cell-empty
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

            // Add highlights and shadows for professional block look
            ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
            ctx.fillRect(x, y, cellWidth, 2);
            ctx.fillRect(x, y, 2, cellHeight);

            ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
            ctx.fillRect(x, y + cellHeight - 2, cellWidth, 2);
            ctx.fillRect(x + cellWidth - 2, y, 2, cellHeight);
          }

          // Draw grid borders
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
          ctx.lineWidth = 1;
          ctx.strokeRect(x, y, cellWidth, cellHeight);
        }
      }
    };

    // Draw immediately
    draw();

    // Setup ResizeObserver to trigger redraw when container/parent changes size
    const resizeObserver = new ResizeObserver(() => {
      draw();
    });

    if (canvas.parentElement) {
      resizeObserver.observe(canvas.parentElement);
    } else {
      resizeObserver.observe(canvas);
    }

    // Window resize event listener to trigger redraw on browser resize or DPI changes
    window.addEventListener('resize', draw);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', draw);
    };
  }, [board, activePiece]);

  return (
    <div className="board-container">
      <canvas
        ref={canvasRef}
        className="board-canvas"
        style={{ width: '240px', height: '480px', display: 'block' }}
        data-board-state={JSON.stringify(board)}
        data-active-piece={JSON.stringify(activePiece)}
        aria-label={`Tetris Board, game status is ${game.status}`}
        role="img"
      />
    </div>
  );
};
