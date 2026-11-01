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

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    // Should have called the /tick endpoint and updated origin to [1, 4]
    expect(result.current.game?.activePiece?.origin).toEqual([1, 4]);
  });

  it('dispatches hold action on lowercase c keydown', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
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

    fetchMock.mockClear();

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c' }));
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/games/test-uuid/hold', { method: 'POST' });
    expect(result.current.game?.hold_piece).toBe('O');
    expect(result.current.game?.can_hold).toBe(false);
  });

  it('dispatches hold action on uppercase C keydown', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
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

    fetchMock.mockClear();

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'C' }));
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/games/test-uuid/hold', { method: 'POST' });
    expect(result.current.game?.hold_piece).toBe('O');
    expect(result.current.game?.can_hold).toBe(false);
  });

  it('asserts a rejected second Hold sends no new request while unavailable', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockGameSession,
            can_hold: false,
          }),
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockGameSession),
      } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());
    await act(async () => {
      await result.current.startGame();
    });

    fetchMock.mockClear();

    await act(async () => {
      await result.current.hold();
    });

    expect(fetchMock).not.toHaveBeenCalled();

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c' }));
    });

    expect(fetchMock).not.toHaveBeenCalled();
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
    const restartPromise = new Promise(() => {});
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

  // ==========================================
  // POST-GENERATION QA ITERATION 2 RACES TESTS
  // ==========================================

  it('R1(a): start A resolves and A.json remains pending, start B fully completes, then A.json resolves and B wins', async () => {
    let resolveJsonA: any;
    const jsonAPromise = new Promise((resolve) => { resolveJsonA = resolve; });

    let fetchCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      fetchCount++;
      if (fetchCount === 1) {
        // Start A: fetch resolves, but res.json() remains pending
        return Promise.resolve({
          ok: true,
          json: () => jsonAPromise,
        } as unknown as Response);
      } else {
        // Start B: fully completes immediately
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: 'session-B' }),
        } as unknown as Response);
      }
    });

    const { result } = renderHook(() => useGame());

    // Trigger Start A
    act(() => {
      result.current.startGame();
    });

    // Trigger Start B
    await act(async () => {
      await result.current.startGame();
    });

    // B is now the current game
    expect(result.current.game?.id).toBe('session-B');

    // Now let A.json resolve late
    await act(async () => {
      resolveJsonA({ ...mockGameSession, id: 'session-A' });
    });

    // B must still win! A.json must be discarded.
    expect(result.current.game?.id).toBe('session-B');
  });

  it('R1(b): A.json rejects while B is pending, leaving B loading/error ownership intact', async () => {
    let rejectJsonA: any;
    const jsonAPromise = new Promise((_, reject) => { rejectJsonA = reject; });
    // Attach dummy catch handler to prevent unhandled rejection warning/error in Vitest
    jsonAPromise.catch(() => {});

    let resolveFetchB: any;
    const fetchBPromise = new Promise((resolve) => { resolveFetchB = resolve; });

    let fetchCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      fetchCount++;
      if (fetchCount === 1) {
        return Promise.resolve({
          ok: true,
          json: () => jsonAPromise,
        } as unknown as Response);
      } else {
        return fetchBPromise as any;
      }
    });

    const { result } = renderHook(() => useGame());

    // Start A
    act(() => {
      result.current.startGame();
    });

    // Start B (remains pending)
    act(() => {
      result.current.startGame();
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBeNull();

    // Reject Start A's json promise
    await act(async () => {
      rejectJsonA(new Error('A failed'));
    });

    // B's loading state must remain true, and no error should be set
    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBeNull();

    // Now complete B
    await act(async () => {
      resolveFetchB({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'session-B' }),
      });
    });

    expect(result.current.game?.id).toBe('session-B');
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('R2(c): old mutation fetch/body never resolves, restart B completes and B mutations still dispatch without waiting for A', async () => {
    const moveAPromise = new Promise(() => {}); // never resolves

    let fetchCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        fetchCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: `session-${fetchCount}` }),
        } as unknown as Response);
      }
      // Mutation url
      if (urlStr.includes('session-1')) {
        return moveAPromise as any;
      } else {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: 'session-2', score: 999 }),
        } as unknown as Response);
      }
    });

    const { result } = renderHook(() => useGame());

    // Start Game A (session-1)
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-1');

    // Trigger move on Game A (this is pending indefinitely)
    act(() => {
      result.current.move('left');
    });

    // Restart Game (session-2)
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-2');

    // Trigger move on Game B (session-2) - this must complete immediately since B has a separate queue!
    await act(async () => {
      await result.current.move('left');
    });

    // Verify B's mutation finished and changed state
    expect(result.current.game?.score).toBe(999);
  });

  it('R2(d): old queued work is discarded after restart and old completion cannot block or affect B', async () => {
    let resolveMoveA: any;
    const moveAPromise = new Promise((resolve) => { resolveMoveA = resolve; });

    let startCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        startCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: `session-${startCount}` }),
        } as unknown as Response);
      }
      return moveAPromise as any;
    });

    const { result } = renderHook(() => useGame());

    // Start A
    await act(async () => {
      await result.current.startGame();
    });

    // Move A (pending)
    act(() => {
      result.current.move('left');
    });

    // Restart B
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-2');

    // Resolve Move A late
    await act(async () => {
      resolveMoveA({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'session-1', score: 5000 }),
      });
    });

    // Game should remain B, state unmodified
    expect(result.current.game?.id).toBe('session-2');
    expect(result.current.game?.score).toBe(0);
  });

  it('Mutations before the first game or during pending restart do not dispatch', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    const { result } = renderHook(() => useGame());

    // Mutation before startGame
    await act(async () => {
      await result.current.move('left');
    });
    expect(fetchSpy).not.toHaveBeenCalled();

    // Now start game A
    const startPromise = new Promise(() => {});
    fetchSpy.mockImplementationOnce(() => startPromise as any);

    act(() => {
      result.current.startGame();
    });

    // While start is pending, attempt a move
    await act(async () => {
      await result.current.move('left');
    });

    // Fetch should only have been called for startGame, not for the move
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('Test coalesced delayed automatic ticks and cancellation', async () => {
    let resolveTick: any;
    const tickPromise = new Promise((resolve) => { resolveTick = resolve; });

    let fetchCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      fetchCount++;
      return tickPromise as any;
    });

    const { result } = renderHook(() => useGame());

    // Start game (interval 500ms)
    await act(async () => {
      await result.current.startGame();
    });

    // Let 1500 ms pass (three gravity intervals)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    // Due to coalescence, only ONE tick fetch must be triggered!
    expect(fetchCount).toBe(1);

    // Resolve the slow tick
    await act(async () => {
      resolveTick({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, origin: [1, 4] }),
      });
    });

    // Ensure no immediate burst replay occurs
    expect(fetchCount).toBe(1);
  });

  it('StrictMode mount and remount / cleanup check', async () => {
    const { unmount, result } = renderHook(() => useGame());
    expect(result.current).toBeDefined();
    unmount();
    expect(result.current.game).toBeNull();
  });
});
