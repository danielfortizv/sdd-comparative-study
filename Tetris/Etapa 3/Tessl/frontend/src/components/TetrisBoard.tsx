import React from 'react';
import { GameState } from '../types';

interface TetrisBoardProps {
  gameState: GameState;
}

export const TetrisBoard: React.FC<TetrisBoardProps> = ({ gameState }) => {
  const { board, active_piece } = gameState;

  // Render a 20x10 grid.
  // We can map over the rows and columns.
  return (
    <div className="tetris-board" data-status={gameState.status}>
      {board.map((row, rIndex) => (
        <div key={rIndex} className="board-row">
          {row.map((cell, cIndex) => {
            // Check if this cell is occupied by the active piece
            const isActiveCell = active_piece
              ? active_piece.cells.some(
                  ([cellRow, cellCol]) => cellRow === rIndex && cellCol === cIndex
                )
              : false;

            // Determine the tetromino type/color of this cell
            const cellType = cell || (isActiveCell && active_piece ? active_piece.type : null);

            return (
              <div
                key={cIndex}
                className={`board-cell ${cellType ? `cell-${cellType}` : 'cell-empty'} ${
                  isActiveCell ? 'cell-active' : ''
                }`}
                data-row={rIndex}
                data-col={cIndex}
                data-type={cellType || 'empty'}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
};
