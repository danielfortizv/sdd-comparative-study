import type { GameState } from "../api";

interface GridBoardProps {
  gameState: GameState | null;
}

export default function GridBoard({ gameState }: GridBoardProps) {
  // Merge settled board blocks with active piece cells for unified rendering
  const getRenderGrid = () => {
    if (!gameState) {
      return Array(20).fill(null).map(() => Array(10).fill(null));
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

  return (
    <div className="grid-board" data-testid="grid-board">
      {renderGrid.map((row, rIndex) => (
        <div key={rIndex} className="grid-row">
          {row.map((cell, cIndex) => (
            <div
              key={cIndex}
              className={`grid-cell ${cell ? `cell-${cell}` : "cell-empty"}`}
              title={`Row ${rIndex}, Col ${cIndex}`}
              data-testid={`cell-${rIndex}-${cIndex}`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
