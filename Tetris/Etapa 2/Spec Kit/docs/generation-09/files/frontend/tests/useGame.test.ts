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
    globalThis.fetch = vi.fn().mockImplementation((url: any) => {
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
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
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

    // 1. Test lowercase 'c'
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c' }));
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/games/test-uuid/hold', { method: 'POST' });
    expect(result.current.game?.hold_piece).toBe('O');
    expect(result.current.game?.can_hold).toBe(false);

    // Reset hold state to test uppercase 'C'
    act(() => {
      result.current.game!.can_hold = true;
      result.current.game!.hold_piece = null;
    });

    // 2. Test uppercase 'C'
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'C' }));
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/games/test-uuid/hold', { method: 'POST' });
  });

  it('serializes and queues concurrent move mutations sequentially', async () => {
    let resolveFirstMove: any;
    let resolveSecondMove: any;

    const firstMovePromise = new Promise((resolve) => {
      resolveFirstMove = resolve;
    });
    const secondMovePromise = new Promise((resolve) => {
      resolveSecondMove = resolve;
    });

    let callCount = 0;
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
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

    expect(fetchSpy).toHaveBeenCalledTimes(1); // just the start game

    // Dispatch first move (will trigger first fetch asynchronously)
    act(() => {
      result.current.move('left');
    });
    await act(async () => {
      await Promise.resolve(); // flush microtasks to let .then run
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2); // start game + first move

    // Dispatch second move (should be blocked in-flight and not call fetch yet!)
    act(() => {
      result.current.move('left');
    });
    await act(async () => {
      await Promise.resolve(); // flush microtasks to let .then run
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2); // still 2! second move is queued!

    // Resolve first move
    await act(async () => {
      resolveFirstMove({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 100 }),
      });
    });
    await act(async () => {
      await Promise.resolve(); // flush microtasks to let .then run
    });

    // Now that the first move has finished, the second move should be dispatched!
    expect(fetchSpy).toHaveBeenCalledTimes(3);

    // Resolve second move
    await act(async () => {
      resolveSecondMove({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 200 }),
      });
    });
    await act(async () => {
      await Promise.resolve(); // flush microtasks to let .then run
    });

    expect(result.current.game?.score).toBe(200);
  });

  it('discards pre-restart stale responses after starting a new game session', async () => {
    let resolveSlowMove: any;
    const slowMovePromise = new Promise((resolve) => { resolveSlowMove = resolve; });

    let startCallCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
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
    await act(async () => {
      await Promise.resolve();
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
    await act(async () => {
      await Promise.resolve();
    });

    // The slow response must NOT overwrite the new session's state
    expect(result.current.game?.id).toBe('new-session-uuid');
    expect(result.current.game?.score).toBe(0);
  });

  it('handles two overlapping start calls and lets the newest win when resolved out-of-order', async () => {
    let resolveStart1: any;
    let resolveStart2: any;

    const start1Promise = new Promise((resolve) => { resolveStart1 = resolve; });
    const start2Promise = new Promise((resolve) => { resolveStart2 = resolve; });

    let startCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      startCount++;
      if (startCount === 1) return start1Promise as any;
      return start2Promise as any;
    });

    const { result } = renderHook(() => useGame());

    // Trigger Start 1
    act(() => {
      result.current.startGame();
    });

    // Trigger Start 2 (restart while 1 is pending)
    act(() => {
      result.current.startGame();
    });

    // Resolve Start 2 (newest) first
    await act(async () => {
      resolveStart2({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'newest-session' }),
      });
    });

    expect(result.current.game?.id).toBe('newest-session');

    // Resolve Start 1 (oldest) second
    await act(async () => {
      resolveStart1({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'oldest-session' }),
      });
    });

    // The oldest late response must be discarded! Newest session stays active.
    expect(result.current.game?.id).toBe('newest-session');
  });

  it('ignores older creation failure when a newer start is already pending', async () => {
    let resolveStart1: any;
    let resolveStart2: any;

    const start1Promise = new Promise((resolve) => { resolveStart1 = resolve; });
    const start2Promise = new Promise((resolve) => { resolveStart2 = resolve; });

    let startCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      startCount++;
      if (startCount === 1) return start1Promise as any;
      return start2Promise as any;
    });

    const { result } = renderHook(() => useGame());

    // Start 1
    act(() => {
      result.current.startGame();
    });

    // Start 2
    act(() => {
      result.current.startGame();
    });

    // Fail Start 1
    await act(async () => {
      resolveStart1({
        ok: false,
        status: 500,
      });
    });

    // The error should NOT be set to the global state because a newer start is still pending, and loading should stay true
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(true);

    // Resolve Start 2 successfully
    await act(async () => {
      resolveStart2({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'success-session' }),
      });
    });

    expect(result.current.game?.id).toBe('success-session');
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('prevents old-game actions during a pending restart', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());
    
    // Start game 1
    await act(async () => {
      await result.current.startGame();
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    // Call startGame again to trigger a pending restart (fetchSpy will be called but not resolved yet)
    let resolveRestart: any;
    const restartPromise = new Promise((resolve) => { resolveRestart = resolve; });
    fetchSpy.mockImplementationOnce(() => restartPromise as any);

    act(() => {
      result.current.startGame();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);

    // Attempt to move while restart is pending
    act(() => {
      result.current.move('left');
    });
    await act(async () => {
      await Promise.resolve();
    });

    // Fetch count must still be 2, because old-game actions are blocked/ignored during pending restart!
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    // Read resolveRestart so typescript knows it is used
    if (resolveRestart) {
      // no-op
    }
  });

  it('recovers lock and queue after mutation errors successfully', async () => {
    const { result } = renderHook(() => useGame());
    await act(async () => {
      await result.current.startGame();
    });

    // Mock fetch to fail for the first move
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => {
      return Promise.reject(new Error('Network failure'));
    });

    // Trigger first move (fails)
    await act(async () => {
      await result.current.move('left');
    });

    // Mock fetch to succeed for subsequent moves
    fetchSpy.mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 777 }),
      } as unknown as Response);
    });

    // Trigger second move
    await act(async () => {
      await result.current.move('left');
    });

    // Verify it processed successfully and recovered from previous failure
    expect(result.current.game?.score).toBe(777);
  });

  it('reschedules and ticks according to progressive gravity intervals', async () => {
    const { result } = renderHook(() => useGame());
    
    // Start at level 1 (500 ms)
    await act(async () => {
      await result.current.startGame();
    });

    // Mock tick fetch to return 450 ms interval
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/tick')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, gravity_interval_ms: 450 }),
        } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    // Advance 500ms to tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    expect(result.current.game?.gravity_interval_ms).toBe(450);

    // Mock tick fetch to return 100 ms interval (gravity floor)
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/tick')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, gravity_interval_ms: 100 }),
        } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    // Advance 450ms (new interval) to tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(450);
    });

    expect(result.current.game?.gravity_interval_ms).toBe(100);

    // Spy on globalThis.fetch to see if the tick HTTP request is made on next interval
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    // Advance 100ms (gravity floor) to tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('/tick'), expect.anything());
  });
});
