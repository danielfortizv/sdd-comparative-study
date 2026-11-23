import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../src/App';
import { useGame } from '../src/hooks/useGame';

// Mock the global ResizeObserver for headless JSDOM test environment
globalThis.ResizeObserver = vi.fn().mockImplementation(function() {
  return {
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  };
});

// Mock HTMLCanvasElement.prototype.getContext to prevent not-implemented JSDOM errors
HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextId) => {
  if (contextId === '2d') {
    return {
      fillRect: vi.fn(),
      clearRect: vi.fn(),
      strokeRect: vi.fn(),
      scale: vi.fn(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
      fill: vi.fn(),
    };
  }
  return null;
});

// Mock the useGame hook
vi.mock('../src/hooks/useGame', () => ({
  useGame: vi.fn(),
}));

// Normalized backend template coordinates for preview templates (2x4 grid)
const EXPECTED_PREVIEW_COORDINATES: Record<string, [number, number][]> = {
  I: [[0, 0], [0, 1], [0, 2], [0, 3]],
  O: [[0, 1], [0, 2], [1, 1], [1, 2]],
  T: [[0, 1], [1, 0], [1, 1], [1, 2]],
  S: [[0, 1], [0, 2], [1, 0], [1, 1]],
  Z: [[0, 0], [0, 1], [1, 1], [1, 2]],
  J: [[0, 0], [1, 0], [1, 1], [1, 2]],
  L: [[0, 2], [1, 0], [1, 1], [1, 2]],
};

describe('App Component Stage 2 HUD and Previews', () => {
  const mockStartGame = vi.fn();
  const mockMove = vi.fn();
  const mockHold = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders start screen when game state is null', () => {
    vi.mocked(useGame).mockReturnValue({
      game: null,
      loading: false,
      error: null,
      startGame: mockStartGame,
      move: mockMove,
      tick: vi.fn(),
      hold: mockHold,
    });

    render(<App />);
    expect(screen.getByText('Welcome to Tetris study game core!')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Start New Game' })).not.toBeNull();
  });

  it('renders stats, next piece preview, and hold slot from game state', () => {
    vi.mocked(useGame).mockReturnValue({
      game: {
        id: 'test-session-id',
        board: Array(20).fill(null).map(() => Array(10).fill(0)),
        activePiece: {
          type: 'O',
          cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
          origin: [0, 4],
        },
        status: 'playing',
        score: 1250,
        total_lines: 15,
        level: 2,
        gravity_interval_ms: 450,
        next_piece: 'T',
        hold_piece: 'I',
        can_hold: true,
      },
      loading: false,
      error: null,
      startGame: mockStartGame,
      move: mockMove,
      tick: vi.fn(),
      hold: mockHold,
    });

    render(<App />);

    // Verify statistics HUD
    expect(screen.getByText('Score:')).not.toBeNull();
    expect(screen.getByText('1250')).not.toBeNull();
    expect(screen.getByText('Lines:')).not.toBeNull();
    expect(screen.getByText('15')).not.toBeNull();
    expect(screen.getByText('Level:')).not.toBeNull();
    expect(screen.getByText('2')).not.toBeNull();
    expect(screen.getByText('Gravity:')).not.toBeNull();
    expect(screen.getByText('450 ms')).not.toBeNull();

    // Verify Next Piece and Hold panels
    expect(screen.getByText('Next Piece')).not.toBeNull();
    expect(screen.getByText('Hold Piece')).not.toBeNull();

    // Hold button should be enabled
    const holdBtn = screen.getByRole('button', { name: 'Hold (C Key)' });
    expect((holdBtn as HTMLButtonElement).disabled).toBe(false);

    // Trigger hold click
    fireEvent.click(holdBtn);
    expect(mockHold).toHaveBeenCalledTimes(1);
  });

  it('renders "EMPTY" placeholder when hold slot is unoccupied', () => {
    vi.mocked(useGame).mockReturnValue({
      game: {
        id: 'test-session-id',
        board: Array(20).fill(null).map(() => Array(10).fill(0)),
        activePiece: {
          type: 'O',
          cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
          origin: [0, 4],
        },
        status: 'playing',
        score: 0,
        total_lines: 0,
        level: 1,
        gravity_interval_ms: 500,
        next_piece: 'O',
        hold_piece: null,
        can_hold: true,
      },
      loading: false,
      error: null,
      startGame: mockStartGame,
      move: mockMove,
      tick: vi.fn(),
      hold: mockHold,
    });

    render(<App />);
    expect(screen.getByText('EMPTY')).not.toBeNull();
  });

  it('disables the Hold button when can_hold is false', () => {
    vi.mocked(useGame).mockReturnValue({
      game: {
        id: 'test-session-id',
        board: Array(20).fill(null).map(() => Array(10).fill(0)),
        activePiece: {
          type: 'O',
          cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
          origin: [0, 4],
        },
        status: 'playing',
        score: 0,
        total_lines: 0,
        level: 1,
        gravity_interval_ms: 500,
        next_piece: 'O',
        hold_piece: 'I',
        can_hold: false,
      },
      loading: false,
      error: null,
      startGame: mockStartGame,
      move: mockMove,
      tick: vi.fn(),
      hold: mockHold,
    });

    render(<App />);
    const holdBtn = screen.getByRole('button', { name: 'Hold (C Key)' });
    expect((holdBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('disables the Hold button when status is game_over', () => {
    vi.mocked(useGame).mockReturnValue({
      game: {
        id: 'test-session-id',
        board: Array(20).fill(null).map(() => Array(10).fill(0)),
        activePiece: {
          type: 'O',
          cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
          origin: [0, 4],
        },
        status: 'game_over',
        score: 0,
        total_lines: 0,
        level: 1,
        gravity_interval_ms: 500,
        next_piece: 'O',
        hold_piece: 'I',
        can_hold: true,
      },
      loading: false,
      error: null,
      startGame: mockStartGame,
      move: mockMove,
      tick: vi.fn(),
      hold: mockHold,
    });

    render(<App />);
    const holdBtn = screen.getByRole('button', { name: 'Hold (C Key)' });
    expect((holdBtn as HTMLButtonElement).disabled).toBe(true);
  });

  // Parameterized rendered assertions for I/O/T/S/Z/J/L previews and geometry
  describe('Canonical Geometry of all seven preview shapes (I, O, T, S, Z, J, L)', () => {
    const shapes = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];

    shapes.forEach((shape) => {
      it(`verifies the geometry of ${shape} in both Next Piece and Hold Piece slots`, () => {
        vi.mocked(useGame).mockReturnValue({
          game: {
            id: 'test-session-id',
            board: Array(20).fill(null).map(() => Array(10).fill(0)),
            activePiece: {
              type: 'O',
              cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
              origin: [0, 4],
            },
            status: 'playing',
            score: 0,
            total_lines: 0,
            level: 1,
            gravity_interval_ms: 500,
            next_piece: shape,
            hold_piece: shape,
            can_hold: true,
          },
          loading: false,
          error: null,
          startGame: mockStartGame,
          move: mockMove,
          tick: vi.fn(),
          hold: mockHold,
        });

        const { container } = render(<App />);

        // Helper to extract filled cell coordinates from a panel container element
        const getFilledCoordinates = (panelSelector: string): [number, number][] => {
          const panel = container.querySelector(panelSelector);
          if (!panel) return [];

          const cells = panel.querySelectorAll('.cell');
          const coordinates: [number, number][] = [];

          cells.forEach((cell, index) => {
            const isFilled = cell.className.includes('cell-') && !cell.className.includes('cell-empty');
            if (isFilled) {
              const r = Math.floor(index / 4);
              const c = index % 4;
              coordinates.push([r, c]);
            }
          });

          return coordinates;
        };

        const expectedCoords = EXPECTED_PREVIEW_COORDINATES[shape];

        // 1. Verify Next Piece Slot Geometry
        const nextCoords = getFilledCoordinates('.preview-panel');
        expect(nextCoords).toEqual(expectedCoords);

        // 2. Verify Hold Piece Slot Geometry
        const holdCoords = getFilledCoordinates('.hold-panel');
        expect(holdCoords).toEqual(expectedCoords);
      });
    });
  });

  describe('Canvas Board rendering and resizing', () => {
    it('mounts the canvas element and commits board and active piece state to data attributes', () => {
      const mockBoard = Array(20).fill(null).map(() => Array(10).fill(0));
      mockBoard[19][0] = 1; // Locked I piece block at bottom left
      
      vi.mocked(useGame).mockReturnValue({
        game: {
          id: 'test-session-id',
          board: mockBoard,
          activePiece: {
            type: 'T',
            cells: [[0, 4], [1, 3], [1, 4], [1, 5]],
            origin: [1, 4],
          },
          status: 'playing',
          score: 120,
          total_lines: 1,
          level: 1,
          gravity_interval_ms: 500,
          next_piece: 'O',
          hold_piece: null,
          can_hold: true,
        },
        loading: false,
        error: null,
        startGame: mockStartGame,
        move: mockMove,
        tick: vi.fn(),
        hold: mockHold,
      });

      const { container } = render(<App />);
      
      // Canvas should be rendered inside the board container
      const canvas = container.querySelector('.board-canvas') as HTMLCanvasElement;
      expect(canvas).not.toBeNull();
      expect(canvas.tagName.toLowerCase()).toBe('canvas');

      // Verify the committed-state pixel geometry encoded in attributes
      const boardState = JSON.parse(canvas.getAttribute('data-board-state') || '[]');
      expect(boardState[19][0]).toBe(1);

      const activePieceState = JSON.parse(canvas.getAttribute('data-active-piece') || '{}');
      expect(activePieceState.type).toBe('T');
      expect(activePieceState.cells).toEqual([[0, 4], [1, 3], [1, 4], [1, 5]]);
    });

    it('successfully handles window resize and triggers canvas resize observer without crashing', () => {
      vi.mocked(useGame).mockReturnValue({
        game: {
          id: 'test-session-id',
          board: Array(20).fill(null).map(() => Array(10).fill(0)),
          activePiece: {
            type: 'O',
            cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
            origin: [0, 4],
          },
          status: 'playing',
          score: 0,
          total_lines: 0,
          level: 1,
          gravity_interval_ms: 500,
          next_piece: 'I',
          hold_piece: null,
          can_hold: true,
        },
        loading: false,
        error: null,
        startGame: mockStartGame,
        move: mockMove,
        tick: vi.fn(),
        hold: mockHold,
      });

      render(<App />);

      // Trigger standard resize event on the window to verify stable drawing lifecycle triggers
      expect(() => {
        window.dispatchEvent(new Event('resize'));
      }).not.toThrow();
    });
  });
});
