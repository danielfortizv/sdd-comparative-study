import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGame } from '../src/hooks/useGame';

// Setup fake timer and fetch mock
vi.useFakeTimers();

const mockGameSession = {
  id: 'test-uuid',
  board: Array(20).fill(null).map(() => Array(10).fill(0)),
  activePiece: {
    type: 'O',
    cells: [[0, 4], [0, 5], [1, 4], [1, 5]],
    origin: [0, 4],
  },
  status: 'playing',
};

describe('useGame Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        });
      }
      if (url.endsWith('/tick')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockGameSession,
            activePiece: {
              ...mockGameSession.activePiece,
              origin: [1, 4],
              cells: [[1, 4], [1, 5], [2, 4], [2, 5]],
            },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockGameSession),
      });
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('starts a new game session and sets game state', async () => {
    const { result } = renderHook(() => useGame());
    
    await act(async () => {
      await result.current.startGame();
    });

    expect(result.current.game).not.toBeNull();
    expect(result.current.game?.id).toBe('test-uuid');
    expect(result.current.game?.status).toBe('playing');
  });

  it('automatically triggers a tick every 500 ms when playing', async () => {
    const { result } = renderHook(() => useGame());
    
    await act(async () => {
      await result.current.startGame();
    });

    expect(result.current.game?.activePiece?.origin).toEqual([0, 4]);

    // Advance fake timers by 500ms
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    // It should have called the /tick endpoint and updated origin to [1, 4]
    expect(result.current.game?.activePiece?.origin).toEqual([1, 4]);
  });
});
