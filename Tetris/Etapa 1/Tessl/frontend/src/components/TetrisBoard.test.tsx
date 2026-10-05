import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TetrisBoard } from './TetrisBoard';
import { GameState } from '../types';

describe('TetrisBoard Component', () => {
  const mockGameState: GameState = {
    id: 'test-uuid',
    board: Array.from({ length: 20 }, () => Array(10).fill(null)),
    active_piece: {
      type: 'I',
      origin: [0, 3],
      cells: [[0, 3], [0, 4], [0, 5], [0, 6]],
    },
    status: 'playing',
  };

  test('renders 20x10 board cell grid correctly', () => {
    const { container } = render(<TetrisBoard gameState={mockGameState} />);
    const board = container.querySelector('.tetris-board');
    expect(board).not.toBeNull();

    const cells = container.querySelectorAll('.board-cell');
    expect(cells.length).toBe(200); // 20 * 10
  });

  test('correctly overlays the active piece on the board cells', () => {
    const { container } = render(<TetrisBoard gameState={mockGameState} />);
    
    // Check cell (0, 3) which is part of active piece
    const activeCell = container.querySelector('[data-row="0"][data-col="3"]');
    expect(activeCell).not.toBeNull();
    expect(activeCell?.classList.contains('cell-I')).toBe(true);
    expect(activeCell?.classList.contains('cell-active')).toBe(true);

    // Check empty cell (5, 5)
    const emptyCell = container.querySelector('[data-row="5"][data-col="5"]');
    expect(emptyCell).not.toBeNull();
    expect(emptyCell?.classList.contains('cell-empty')).toBe(true);
  });
});
