import type { GameState } from "../api";

interface PiecePreviewProps {
  piece: string | null;
  grayscale?: boolean;
}

interface GridBoardProps {
  gameState: GameState | null;
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

function PiecePreview({ piece, grayscale = false }: Readonly<PiecePreviewProps>) {
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

export default function GridBoard({ gameState }: Readonly<GridBoardProps>) {
  // Merge settled board blocks with active piece cells for unified rendering
  const getRenderGrid = () => {
    if (!gameState) {
      return new Array(20).fill(null).map(() => new Array(10).fill(null));
    }

    const grid = gameState.board.map((row) => [...row]);
    const active = gameState.active_piece;

    if (active && gameState.status === "playing") {
      active.cells.forEach(([r, c]) => {
        if (r >= 0 && r < 20 && c >= 10) {
          // Keep bounds in check
        } else if (r >= 0 && r < 20 && c >= 0 && c < 10) {
          grid[r][c] = active.type;
        }
      });
    }
    return grid;
  };

  const renderGrid = getRenderGrid();
  const canHold = gameState ? gameState.can_hold : true;
  const gameIdStr = gameState?.id || "init";

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
        <div className="grid-board" data-testid="grid-board">
          {renderGrid.map((row, rIndex) => {
            const rowKey = `board-row-${gameIdStr}-${rIndex}`;
            return (
              <div key={rowKey} className="grid-row">
                {row.map((cell, cIndex) => {
                  const cellKey = `board-cell-${gameIdStr}-${rIndex}-${cIndex}`;
                  const cellClass = cell ? "cell-" + cell : "cell-empty";
                  return (
                    <div
                      key={cellKey}
                      className={`grid-cell ${cellClass}`}
                      title={`Row ${rIndex}, Col ${cIndex}`}
                      data-testid={`cell-${rIndex}-${cIndex}`}
                    />
                  );
                })}
              </div>
            );
          })}
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
