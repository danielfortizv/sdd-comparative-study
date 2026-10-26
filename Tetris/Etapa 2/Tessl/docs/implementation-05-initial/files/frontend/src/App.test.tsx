import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import App from './App';
import { GameState } from './types';

describe('App Component Stage 2 UI and Concurrency', () => {
  const initialMockState: GameState = {
    id: 'game-uuid-1',
    board: Array.from({ length: 20 }, () => Array(10).fill(null)),
    active_piece: {
      type: 'I',
      origin: [0, 3],
      cells: [[0, 3], [0, 4], [0, 5], [0, 6]],
    },
    status: 'playing',
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 999999, // Set to a very high interval to prevent background tick interference!
    next_piece: 'O',
    hold_piece: null,
    can_hold: true,
  };

  test('renders Stage 2 HUD and Next/Hold panels correctly', async () => {
    vi.spyOn(globalThis, 'fetch');
    try {
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => initialMockState,
      });

      const { container } = render(<App />);

      await waitFor(() => {
        expect(screen.queryByText('Initializing Tetris Session...')).toBeNull();
      });

      expect(screen.getByText('Score:')).toBeDefined();
      expect(container.querySelector('.score-value')?.textContent).toBe('0');

      expect(screen.getByText('Lines:')).toBeDefined();
      expect(container.querySelector('.lines-value')?.textContent).toBe('0');

      expect(screen.getByText('Level:')).toBeDefined();
      expect(container.querySelector('.level-value')?.textContent).toBe('1');

      expect(screen.getByText('Gravity:')).toBeDefined();
      expect(container.querySelector('.gravity-value')?.textContent).toBe('999999 ms');

      expect(container.querySelector('.hold-title')?.textContent).toBe('Hold Piece');
      expect(container.querySelector('.preview-title')?.textContent).toBe('Next Piece');
      expect(screen.getByText('AVAILABLE')).toBeDefined();
    } finally {
      vi.restoreAllMocks();
    }
  });

  test('FIFO queue serializes rapid manual movements correctly', async () => {
    vi.spyOn(globalThis, 'fetch');
    try {
      let resolveFirstFetch: any;
      let resolveSecondFetch: any;

      const firstFetchPromise = new Promise<any>((resolve) => {
        resolveFirstFetch = resolve;
      });
      const secondFetchPromise = new Promise<any>((resolve) => {
        resolveSecondFetch = resolve;
      });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => initialMockState,
      });

      (globalThis.fetch as any).mockImplementationOnce(() => firstFetchPromise);
      (globalThis.fetch as any).mockImplementationOnce(() => secondFetchPromise);

      const { container } = render(<App />);

      await waitFor(() => {
        expect(screen.queryByText('Initializing Tetris Session...')).toBeNull();
      });

      expect(globalThis.fetch).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      fireEvent.keyDown(window, { key: 'ArrowLeft' });

      await act(async () => {
        await Promise.resolve();
      });

      expect(globalThis.fetch).toHaveBeenCalledTimes(2);

      const firstMoveState: GameState = {
        ...initialMockState,
        active_piece: {
          type: 'I',
          origin: [0, 2],
          cells: [[0, 2], [0, 3], [0, 4], [0, 5]],
        },
      };

      await act(async () => {
        resolveFirstFetch({
          ok: true,
          json: async () => firstMoveState,
        });
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(globalThis.fetch).toHaveBeenCalledTimes(3);

      const secondMoveState: GameState = {
        ...initialMockState,
        active_piece: {
          type: 'I',
          origin: [0, 1],
          cells: [[0, 1], [0, 2], [0, 3], [0, 4]],
        },
      };

      await act(async () => {
        resolveSecondFetch({
          ok: true,
          json: async () => secondMoveState,
        });
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(container.querySelector('.active-piece-type')?.textContent).toBe('I');
    } finally {
      vi.restoreAllMocks();
    }
  });

  test('Restart immediately preempts and discards pending/stale older generation completions', async () => {
    vi.spyOn(globalThis, 'fetch');
    try {
      let resolveStaleMove: any;
      const staleMovePromise = new Promise<any>((resolve) => {
        resolveStaleMove = resolve;
      });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => initialMockState,
      });

      (globalThis.fetch as any).mockImplementationOnce(() => staleMovePromise);

      const restartedMockState: GameState = {
        ...initialMockState,
        id: 'game-uuid-restarted-2',
        score: 500,
      };
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => restartedMockState,
      });

      const { container } = render(<App />);

      await waitFor(() => {
        expect(screen.queryByText('Initializing Tetris Session...')).toBeNull();
      });

      fireEvent.keyDown(window, { key: 'ArrowLeft' });

      await act(async () => {
        await Promise.resolve();
      });

      expect(globalThis.fetch).toHaveBeenCalledTimes(2);

      const restartBtn = screen.getByRole('button', { name: 'Start New Game' });
      await act(async () => {
        fireEvent.click(restartBtn);
      });

      expect(globalThis.fetch).toHaveBeenCalledTimes(3);

      const staleState: GameState = {
        ...initialMockState,
        score: 99999,
      };

      await act(async () => {
        resolveStaleMove({
          ok: true,
          json: async () => staleState,
        });
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(container.querySelector('.score-value')?.textContent).not.toBe('99999');
      expect(container.querySelector('.score-value')?.textContent).toBe('500');
    } finally {
      vi.restoreAllMocks();
    }
  });

  test('Double ownership verification (post-fetch and post-parse) discards stale json parsing', async () => {
    vi.spyOn(globalThis, 'fetch');
    try {
      let resolveJsonParse: any;
      const jsonParsePromise = new Promise<any>((resolve) => {
        resolveJsonParse = resolve;
      });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => initialMockState,
      });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: () => jsonParsePromise,
      });

      const restartedState: GameState = {
        ...initialMockState,
        id: 'restarted-3',
        score: 42,
      };
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => restartedState,
      });

      const { container } = render(<App />);

      await waitFor(() => {
        expect(screen.queryByText('Initializing Tetris Session...')).toBeNull();
      });

      fireEvent.keyDown(window, { key: 'ArrowLeft' });

      await act(async () => {
        await Promise.resolve();
      });

      const restartBtn = screen.getByRole('button', { name: 'Start New Game' });
      await act(async () => {
        fireEvent.click(restartBtn);
      });

      const staleState: GameState = {
        ...initialMockState,
        score: 1337,
      };
      await act(async () => {
        resolveJsonParse(staleState);
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(container.querySelector('.score-value')?.textContent).toBe('42');
    } finally {
      vi.restoreAllMocks();
    }
  });

  test('Timer safety: manual moves cancel scheduled automatic tick timers', async () => {
    vi.spyOn(globalThis, 'fetch');
    vi.useFakeTimers();
    try {
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => initialMockState,
      });

      render(<App />);

      await act(async () => {
        await vi.runOnlyPendingTimersAsync();
      });

      const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout');

      fireEvent.keyDown(window, { key: 'ArrowLeft' });

      expect(clearTimeoutSpy).toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
      vi.restoreAllMocks();
    }
  });
});
