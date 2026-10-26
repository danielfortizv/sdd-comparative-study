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
  score: 0,
  total_lines: 0,
  level: 1,
  gravity_interval_ms: 500,
  next_piece: 'I',
  hold_piece: null,
  can_hold: true,
};

describe('useGame Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      if (urlStr.endsWith('/tick')) {
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
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockGameSession),
      } as unknown as Response);
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

  it('dispatches hold action on C/c keydown and hold method calls', async () => {
    const fetchMock = vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession), // starts with can_hold=true
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          ...mockGameSession,
          hold_piece: 'O',
          can_hold: false,
        }),
      } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());
    
    await act(async () => {
      await result.current.startGame();
    });

    // Trigger keyboard 'c' keydown
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c' }));
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/games/test-uuid/hold', { method: 'POST' });
    expect(result.current.game?.hold_piece).toBe('O');
    expect(result.current.game?.can_hold).toBe(false);
  });

  it('discards stale, out-of-order responses to prevent state regression', async () => {
    let resolveFirstMove: any;
    let resolveSecondMove: any;

    const firstMovePromise = new Promise((resolve) => {
      resolveFirstMove = resolve;
    });
    const secondMovePromise = new Promise((resolve) => {
      resolveSecondMove = resolve;
    });

    // Mock fetch such that first move request resolves slow, second resolves fast
    let callCount = 0;
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
      }
      callCount++;
      if (callCount === 1) {
        return firstMovePromise as any;
      } else {
        return secondMovePromise as any;
      }
    });

    const { result } = renderHook(() => useGame());
    await act(async () => {
      await result.current.startGame();
    });

    // Send first move (slow)
    act(() => {
      result.current.move('left');
    });

    // Send second move (fast)
    act(() => {
      result.current.move('left');
    });

    // Resolve second move fast (retains level 1, but sets score to 500)
    await act(async () => {
      resolveSecondMove({
        ok: true,
        json: () => Promise.resolve({
          ...mockGameSession,
          score: 500,
        }),
      });
    });

    expect(result.current.game?.score).toBe(500);

    // Resolve first move slow (has older score, e.g., 100)
    await act(async () => {
      resolveFirstMove({
        ok: true,
        json: () => Promise.resolve({
          ...mockGameSession,
          score: 100,
        }),
      });
    });

    // Score should REMAIN 500, first slow response should be ignored because it is stale!
    expect(result.current.game?.score).toBe(500);
  });

  it('discards pre-restart stale responses after starting a new game session', async () => {
    let resolveSlowMove: any;
    const slowMovePromise = new Promise((resolve) => { resolveSlowMove = resolve; });

    let startCallCount = 0;
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        startCallCount++;
        const sessionID = startCallCount === 1 ? 'test-uuid' : 'new-session-uuid';
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: sessionID }),
        } as unknown as Response);
      }
      return slowMovePromise as any;
    });

    const { result } = renderHook(() => useGame());
    
    // Start game 1
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('test-uuid');

    // Trigger a move which hangs
    act(() => {
      result.current.move('left');
    });

    // Restart game (Start game 2)
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('new-session-uuid');

    // Resolve the slow move from game 1
    await act(async () => {
      resolveSlowMove({
        ok: true,
        json: () => Promise.resolve({
          ...mockGameSession,
          id: 'test-uuid', // belongs to old session
          score: 9999,
        }),
      });
    });

    // The slow response must NOT overwrite the new session's state
    expect(result.current.game?.id).toBe('new-session-uuid');
    expect(result.current.game?.score).toBe(0);
  });
});
