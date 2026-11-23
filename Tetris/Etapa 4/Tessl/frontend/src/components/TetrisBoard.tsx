import React, { useRef, useEffect, useState } from 'react';
import { GameState } from '../types';

// Safe global fallback for environments like JSDOM without native canvas implementation (Req-S4-38)
if (typeof window !== 'undefined' && typeof HTMLCanvasElement !== 'undefined') {
  const isJSDOM = typeof navigator !== 'undefined' && navigator.userAgent && navigator.userAgent.toLowerCase().includes('jsdom');
  if (isJSDOM) {
    HTMLCanvasElement.prototype.getContext = function (contextId: string) {
      if (contextId === '2d') {
        return {
          fillRect: () => {},
          strokeRect: () => {},
          resetTransform: () => {},
          scale: () => {},
          clearRect: () => {},
          fillStyle: '',
          strokeStyle: '',
          lineWidth: 0,
        } as any;
      }
      return null;
    };
  }
}

interface TetrisBoardProps {
  gameState: GameState;
}

const colors: Record<string, string> = {
  I: '#00f0f0',
  O: '#f0f000',
  T: '#a000f0',
  S: '#00f000',
  Z: '#f00000',
  J: '#0000f0',
  L: '#f0a000',
};

export const TetrisBoard: React.FC<TetrisBoardProps> = ({ gameState }) => {
  const { board, active_piece } = gameState;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [resizeTrigger, setResizeTrigger] = useState(0);

  // Expose a serialized board hash for state testability (Req-S4-20)
  const boardHash = board
    .map((row) => row.map((cell) => cell || '.').join(''))
    .join('|') + (active_piece ? `+${active_piece.type}@${active_piece.orientation}:${active_piece.cells.map(c => c.join(',')).join(';')}` : '');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext('2d');
    } catch (e) {
      // JSDOM throws a "Not implemented" error when the canvas npm package is not installed.
      // We handle this gracefully (Req-S4-38, Req-S4-20) without throwing or crashing the application.
      return;
    }
    if (!ctx) return; // JSDOM safe handle for absentContext

    const dpr = window.devicePixelRatio || 1;
    
    // Scale the back-buffer based on canvas content dimensions and DPR
    const cssWidth = canvas.clientWidth || 300;
    const cssHeight = canvas.clientHeight || 600;

    canvas.width = cssWidth * dpr;
    canvas.height = cssHeight * dpr;

    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    // Clear board background
    ctx.fillStyle = '#151824';
    ctx.fillRect(0, 0, cssWidth, cssHeight);

    const cols = 10;
    const rows = 20;
    const cellStepX = cssWidth / cols;
    const cellStepY = cssHeight / rows;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const isActiveCell = active_piece
          ? active_piece.cells.some(
              ([cellRow, cellCol]) => cellRow === r && cellCol === c
            )
          : false;

        const cellType = board[r]?.[c] || (isActiveCell && active_piece ? active_piece.type : null);

        // Calculate positions with 1px margin around each cell
        const x = c * cellStepX + 1;
        const y = r * cellStepY + 1;
        const cellSizeX = cellStepX - 2;
        const cellSizeY = cellStepY - 2;

        if (cellType) {
          ctx.fillStyle = colors[cellType] || '#ffffff';
          ctx.fillRect(x, y, cellSizeX, cellSizeY);

          // Subtle shadow border
          ctx.strokeStyle = 'rgba(0, 0, 0, 0.4)';
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, cellSizeX - 1, cellSizeY - 1);
        } else {
          // Empty cell representation
          ctx.fillStyle = 'rgba(255, 255, 255, 0.03)';
          ctx.fillRect(x, y, cellSizeX, cellSizeY);

          ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, cellSizeX - 1, cellSizeY - 1);
        }
      }
    }
  }, [board, active_piece, resizeTrigger]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleResize = () => {
      setResizeTrigger((prev) => prev + 1);
    };

    window.addEventListener('resize', handleResize);

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(handleResize);
      observer.observe(canvas);
      return () => {
        window.removeEventListener('resize', handleResize);
        observer.disconnect();
      };
    }

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="tetris-board"
      data-status={gameState.status}
      data-active-piece-type={active_piece ? active_piece.type : 'none'}
      data-active-piece-orientation={active_piece && active_piece.orientation !== undefined ? active_piece.orientation : 'none'}
      data-board-hash={boardHash}
    />
  );
};
