import React from 'react';
import { TetrominoType } from '../types';

const PREVIEW_SHAPES: Record<TetrominoType, [number, number][]> = {
  'I': [[0, 0], [0, 1], [0, 2], [0, 3]],
  'O': [[0, 0], [0, 1], [1, 0], [1, 1]],
  'T': [[0, 1], [1, 0], [1, 1], [1, 2]],
  'S': [[0, 1], [0, 2], [1, 0], [1, 1]],
  'Z': [[0, 0], [0, 1], [1, 1], [1, 2]],
  'J': [[0, 0], [1, 0], [1, 1], [1, 2]],
  'L': [[0, 2], [1, 0], [1, 1], [1, 2]],
};

interface PiecePreviewProps {
  pieceType: string | null;
}

export const PiecePreview: React.FC<PiecePreviewProps> = ({ pieceType }) => {
  const rows = [0, 1];
  const cols = [0, 1, 2, 3];
  const cells = pieceType ? (PREVIEW_SHAPES[pieceType as TetrominoType] || []) : [];

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
