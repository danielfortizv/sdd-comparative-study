import { describe, test, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { TetrisBoard } from './TetrisBoard';
import { GameState } from '../types';

describe('TetrisBoard Component (Canvas 2D)', () => {
  const mockGameState: GameState = {
    id: 'test-uuid',
    board: Array.from({ length: 20 }, () => Array(10).fill(null)),
    active_piece: {
      type: 'I',
      origin: [0, 3],
      cells: [[0, 3], [0, 4], [0, 5], [0, 6]],
      orientation: 0,
    },
    status: 'playing',
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: 'O',
    hold_piece: null,
    can_hold: true,
    board_revision: 1,
  };

  /**
   * SUPERSEDED DOM GRID CELL ASSERTIONS (Stage 3):
   * - Checking `.board-cell` elements (200 expected) is superseded by Canvas 2D rendering.
   * - Checking specific cells via dataset row/col attributes like container.querySelector('[data-row="0"][data-col="3"]')
   *   is superseded by canvas drawing assertions, canvas state testability data attributes (data-board-hash, data-status,
   *   data-active-piece-type, and data-active-piece-orientation).
   */

  test('renders the <canvas> element and sets correct testability attributes', () => {
    const { container } = render(<TetrisBoard gameState={mockGameState} />);
    const canvas = container.querySelector('canvas.tetris-board') as HTMLCanvasElement;
    expect(canvas).not.toBeNull();
    
    // Check status data attribute
    expect(canvas.getAttribute('data-status')).toBe('playing');
    
    // Check active piece type data attribute
    expect(canvas.getAttribute('data-active-piece-type')).toBe('I');
    
    // Check active piece orientation data attribute
    expect(canvas.getAttribute('data-active-piece-orientation')).toBe('0');

    // Check data-board-hash attribute contains board grid and active piece info
    const hash = canvas.getAttribute('data-board-hash');
    expect(hash).toContain('..........');
    expect(hash).toContain('+I@0:0,3;0,4;0,5;0,6');
  });

  test('exercises Canvas 2D rendering methods on mount and state change', () => {
    // Mock the 2D canvas context to track rendering calls
    const mockContext = {
      fillRect: vi.fn(),
      strokeRect: vi.fn(),
      resetTransform: vi.fn(),
      scale: vi.fn(),
      fillStyle: '',
      strokeStyle: '',
      lineWidth: 0,
    };

    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(mockContext);

    try {
      const { rerender } = render(<TetrisBoard gameState={mockGameState} />);

      // Verify that scaling and transformation methods were called
      expect(mockContext.resetTransform).toHaveBeenCalled();
      expect(mockContext.scale).toHaveBeenCalled();

      // Verify that background clearing occurred
      expect(mockContext.fillRect).toHaveBeenCalled();

      // Clear the mock calls to test state change
      mockContext.fillRect.mockClear();

      const updatedGameState: GameState = {
        ...mockGameState,
        board: Array.from({ length: 20 }, (_, r) => 
          Array.from({ length: 10 }, () => (r === 19 ? 'T' : null))
        ),
      };

      rerender(<TetrisBoard gameState={updatedGameState} />);

      // Verify that state updates trigger canvas rerendering
      expect(mockContext.fillRect).toHaveBeenCalled();
    } finally {
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  });
});
