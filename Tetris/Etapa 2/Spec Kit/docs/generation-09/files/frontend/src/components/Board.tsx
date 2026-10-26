import React from 'react';
import { GameSession } from '../types';

interface BoardProps {
  game: GameSession;
}

export const Board: React.FC<BoardProps> = ({ game }) => {
  const { board, activePiece } = game;

  // Pre-generate row and cell objects with pre-populated stable coordinate IDs
  const displayBoard = board.map((row, r) => ({
    id: `row-coord-${r}`,
    rIdx: r,
    cells: row.map((cell, c) => ({
      id: `cell-coord-${r}-${c}`,
      cIdx: c,
      value: cell,
    })),
  }));

  if (activePiece) {
    const { type, cells } = activePiece;
    // Map piece type to color index (1 to 7)
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

    cells.forEach(([row, col]) => {
      if (row >= 0 && row < 20 && col >= 0 && col < 10) {
        displayBoard[row].cells[col].value = colorIndex;
      }
    });
  }

  // Map color index to tetromino class/name for visual design
  const getClassForCell = (val: number): string => {
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
    <div className="board-container">
      <div className="board-grid">
        {displayBoard.map((row) => (
          <React.Fragment key={row.id}>
            {row.cells.map((cell) => (
              <div
                key={cell.id}
                className={getClassForCell(cell.value)}
                data-row={row.rIdx}
                data-col={cell.cIdx}
              />
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
