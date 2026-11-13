import { useState, useEffect, useRef, useCallback } from "react";
import type { GameState } from "../api";

export interface PiecePreviewProps {
  piece: string | null;
  grayscale?: boolean;
}

interface GridBoardProps {
  gameState: GameState | null;
  isDuel?: boolean;
}

// Visual layout grid representations for each Tetromino piece preview
const PIECE_MINI_GRIDS: Record<string, number[][]> = {
  I: [
    [0, 0, 0, 0],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ],
  O: [
    [1, 1],
    [1, 1],
  ],
  T: [
    [0, 1, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  J: [
    [1, 0, 0],
    [1, 1, 1],
    [0, 0, 0],
  ],
  L: [
    [0, 0, 1],
    [1, 1, 1],
    [0, 0, 0],
  ],
  S: [
    [0, 1, 1],
    [1, 1, 0],
    [0, 0, 0],
  ],
  Z: [
    [1, 1, 0],
    [0, 1, 1],
    [0, 0, 0],
  ],
};

const PIECE_COLORS: Record<string, string> = {
  I: "#00f3ff",
  O: "#ffea00",
  T: "#9d00ff",
  J: "#003cff",
  L: "#ff9100",
  S: "#00ff2b",
  Z: "#ff007f",
};

export function PiecePreview({ piece, grayscale = false }: Readonly<PiecePreviewProps>) {
  if (!piece) {
    return (
      <div className="preview-empty">
        <span>EMPTY</span>
      </div>
    );
  }

  const grid = PIECE_MINI_GRIDS[piece] || [];

  return (
    <div
      className={`piece-preview-grid preview-${piece} ${grayscale ? "cooldown" : ""}`}
      data-testid={`preview-${piece}`}
    >
      {grid.map((row, rIdx) => {
        const rowKey = `preview-row-${piece}-${rIdx}`;
        return (
          <div key={rowKey} className="preview-row">
            {row.map((cell, cIdx) => {
              const cellKey = `preview-cell-${piece}-${rIdx}-${cIdx}`;
              const cellClass = cell ? "cell-" + piece : "cell-empty";
              return (
                <div
                  key={cellKey}
                  className={`preview-cell ${cellClass}`}
                />
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

export default function GridBoard({ gameState, isDuel = false }: Readonly<GridBoardProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [contextError, setContextError] = useState(false);

  // Merge settled board blocks with active piece cells for unified rendering
  const getRenderGrid = () => {
    if (!gameState) {
      return new Array(20).fill(null).map(() => new Array(10).fill(null));
    }

    const grid = gameState.board.map((row) => [...row]);
    const active = gameState.active_piece;

    if (active && gameState.status === "playing") {
      active.cells.forEach(([r, c]) => {
        if (r >= 0 && r < 20 && c >= 0 && c < 10) {
          grid[r][c] = active.type;
        }
      });
    }
    return grid;
  };

  const renderGrid = getRenderGrid();

  // Keep rendering state stable for callbacks
  const renderGridRef = useRef(renderGrid);
  useEffect(() => {
    renderGridRef.current = renderGrid;
  }, [gameState, renderGrid]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setContextError(true);
      return;
    }

    const grid = renderGridRef.current;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.scale(dpr, dpr);

    const cellWidth = w / 10;
    const cellHeight = h / 20;

    for (let r = 0; r < 20; r++) {
      for (let c = 0; c < 10; c++) {
        const type = grid[r][c];
        const x = c * cellWidth;
        const y = r * cellHeight;

        if (type) {
          // Fill occupied cell
          ctx.fillStyle = PIECE_COLORS[type] || "#ffffff";
          ctx.fillRect(x + 1, y + 1, cellWidth - 2, cellHeight - 2);

          // Glossy highlight
          ctx.fillStyle = "rgba(255, 255, 255, 0.15)";
          ctx.fillRect(x + 2, y + 2, cellWidth - 4, (cellHeight - 4) * 0.35);

          // Subtle inner highlight border
          ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 1.5, y + 1.5, cellWidth - 3, cellHeight - 3);
        } else {
          // Empty cell
          ctx.fillStyle = "rgba(16, 18, 36, 0.6)";
          ctx.fillRect(x + 1, y + 1, cellWidth - 2, cellHeight - 2);

          // Border for empty cell
          ctx.strokeStyle = "rgba(30, 34, 70, 0.2)";
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, cellWidth - 1, cellHeight - 1);
        }
      }
    }

    ctx.restore();
  }, []);

  // ResizeObserver for canvas size adjustment and redraw
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const RO = (typeof window !== "undefined" && window.ResizeObserver) ||
               (typeof globalThis !== "undefined" && (globalThis as any).ResizeObserver) ||
               (typeof window !== "undefined" && (window as any).globalThis?.ResizeObserver);

    if (!RO) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = 304 * dpr;
      canvas.height = 624 * dpr;
      canvas.style.width = "304px";
      canvas.style.height = "624px";
      draw();
      return () => {};
    }

    const resizeObserver = new RO((entries: ResizeObserverEntry[]) => {
      if (!entries || entries.length === 0) return;
      const entry = entries[0];
      const { width, height } = entry.contentRect;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      draw();
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
    };
  }, [draw]);

  // Redraw when gameState changes
  useEffect(() => {
    draw();
  }, [gameState, draw]);

  if (isDuel) {
    return (
      <div
        ref={containerRef}
        className="grid-board"
        data-testid="grid-board"
        style={{ display: "block", position: "relative", width: "304px", height: "624px" }}
      >
        {contextError ? (
          <div
            className="context-fallback"
            data-testid="context-fallback"
            style={{
              color: "#ff0055",
              textAlign: "center",
              padding: "20px",
              fontFamily: "sans-serif",
            }}
          >
            Your browser does not support HTML5 Canvas.
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            data-testid="grid-board-canvas"
            aria-label="Tetris Game Board"
            role="img"
            style={{ display: "block", width: "100%", height: "100%" }}
          >
            Your browser does not support HTML5 Canvas. Tetris board showing 20 rows by 10 columns.
          </canvas>
        )}
      </div>
    );
  }

  const canHold = gameState ? gameState.can_hold : true;

  return (
    <div className="game-board-container">
      {/* LEFT COLUMN: Hold Preview & Stats Panel */}
      <div className="side-column left-column">
        <div className="panel side-panel hold-panel">
          <h3>HOLD</h3>
          <div
            className={`hold-container ${!canHold ? "hold-cooldown" : ""}`}
            data-testid="hold-container"
          >
            <PiecePreview piece={gameState?.hold_piece || null} grayscale={!canHold} />
            {!canHold && (
              <div className="cooldown-overlay-label">LOCKED</div>
            )}
          </div>
        </div>

        <div className="panel side-panel stats-panel">
          <h3>STATS</h3>
          <div className="stat-entry">
            <span className="stat-title">SCORE</span>
            <span className="stat-num" data-testid="score-value">
              {gameState?.score ?? 0}
            </span>
          </div>
          <div className="stat-entry">
            <span className="stat-title">LEVEL</span>
            <span className="stat-num" data-testid="level-value">
              {gameState?.level ?? 1}
            </span>
          </div>
          <div className="stat-entry">
            <span className="stat-title">LINES</span>
            <span className="stat-num" data-testid="lines-value">
              {gameState?.total_lines ?? 0}
            </span>
          </div>
        </div>
      </div>

      {/* CENTER COLUMN: The Core Grid Board */}
      <div className="board-column">
        <div
          ref={containerRef}
          className="grid-board"
          data-testid="grid-board"
          style={{ display: "block", position: "relative" }}
        >
          {contextError ? (
            <div
              className="context-fallback"
              data-testid="context-fallback"
              style={{
                color: "#ff0055",
                textAlign: "center",
                padding: "20px",
                fontFamily: "sans-serif",
              }}
            >
              Your browser does not support HTML5 Canvas.
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              data-testid="grid-board-canvas"
              aria-label="Tetris Game Board"
              role="img"
              style={{ display: "block", width: "100%", height: "100%" }}
            >
              Your browser does not support HTML5 Canvas. Tetris board showing 20 rows by 10 columns.
            </canvas>
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: Next Preview Panel */}
      <div className="side-column right-column">
        <div className="panel side-panel next-panel">
          <h3>NEXT</h3>
          <div className="next-container" data-testid="next-container">
            <PiecePreview piece={gameState?.next_piece || null} />
          </div>
        </div>
      </div>
    </div>
  );
}
