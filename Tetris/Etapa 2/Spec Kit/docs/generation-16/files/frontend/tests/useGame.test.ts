import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
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

  it('reschedules and ticks according to progressive gravity intervals with precise deltas', async () => {
    let tickCount = 0;
    let nextInterval = 450;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      if (urlStr.endsWith('/tick')) {
        tickCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, gravity_interval_ms: nextInterval }),
        } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());
    
    // Start at level 1 (500 ms)
    await act(async () => {
      await result.current.startGame();
    });

    expect(tickCount).toBe(0);

    // Advance 499 ms (just before 500ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(499);
    });
    expect(tickCount).toBe(0);

    // Advance 1 ms (reaches 500ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(tickCount).toBe(1);
    expect(result.current.game?.gravity_interval_ms).toBe(450);

    // Next tick will return 100ms interval
    nextInterval = 100;

    // Advance 449 ms (just before 450ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(449);
    });
    expect(tickCount).toBe(1); // Still 1

    // Advance 1 ms (reaches 450ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(tickCount).toBe(2);
    expect(result.current.game?.gravity_interval_ms).toBe(100);

    // Advance 99 ms (just before 100ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(99);
    });
    expect(tickCount).toBe(2);

    // Advance 1 ms (reaches 100ms)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(tickCount).toBe(3);
  });

  // ==========================================
  // POST-GENERATION QA ITERATION 3 RACES TESTS
  // ==========================================

  it('R1(a): start A resolves and A.json remains pending, start B fully completes, then A.json resolves and B wins', async () => {
    let jsonACalled = false;
    let resolveJsonA: any;
    const jsonAPromise = new Promise((resolve) => {
      resolveJsonA = resolve;
    });

    let fetchCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      fetchCount++;
      if (fetchCount === 1) {
        // Start A: fetch resolves, but res.json() remains pending
        return Promise.resolve({
          ok: true,
          json: () => {
            jsonACalled = true;
            return jsonAPromise;
          },
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

    // Explicitly flush microtasks
    await act(async () => {
      await Promise.resolve();
    });

    // Assert A.json has actually been called and is still unresolved BEFORE starting B
    expect(jsonACalled).toBe(true);
    expect(result.current.game).toBeNull();

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
    let jsonACalled = false;
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
          json: () => {
            jsonACalled = true;
            return jsonAPromise;
          },
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

    // Flush microtasks
    await act(async () => {
      await Promise.resolve();
    });

    // Assert A's json has been called and remains unresolved
    expect(jsonACalled).toBe(true);

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
    let moveAFetchCalled = 0;
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
        moveAFetchCalled++;
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

    // Trigger move A1 on Game A (this is pending indefinitely)
    act(() => {
      result.current.move('left');
    });

    // Queue another move A2 on Game A (which must be queued behind in-flight A1)
    act(() => {
      result.current.move('down');
    });

    // Flush microtasks to dispatch the first fetch
    await act(async () => {
      await Promise.resolve();
    });

    // Assert that A's first mutation fetch/body is actually in-flight, but the second is NOT yet (since it is queued)
    expect(moveAFetchCalled).toBe(1);

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
    let startCount = 0;
    let session1MutationCalls = 0;
    let session2MutationCalls = 0;
    let resolveMoveA1: any;
    const moveA1Promise = new Promise((resolve) => { resolveMoveA1 = resolve; });

    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        startCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: `session-${startCount}` }),
        } as unknown as Response);
      }
      
      if (urlStr.includes('session-1')) {
        session1MutationCalls++;
        return moveA1Promise as any;
      } else {
        session2MutationCalls++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: 'session-2', score: 999 }),
        } as unknown as Response);
      }
    });

    const { result } = renderHook(() => useGame());

    // Start A
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-1');

    // Move A1 (pending)
    act(() => {
      result.current.move('left');
    });

    // Flush microtasks to prove A1 fetch/body is actually pending
    await act(async () => {
      await Promise.resolve();
    });

    // Assert A1 is in flight before triggering A2
    expect(session1MutationCalls).toBe(1);

    // Queue A2 behind A1 after proving A1 fetch/body actually pending
    act(() => {
      result.current.move('down');
    });

    // Flush microtasks - A2 should not be dispatched yet since A1 is pending
    await act(async () => {
      await Promise.resolve();
    });
    expect(session1MutationCalls).toBe(1);

    // Restart B
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-2');

    // Prove B mutation completes while A1 is pending
    await act(async () => {
      await result.current.move('left');
    });
    expect(result.current.game?.id).toBe('session-2');
    expect(result.current.game?.score).toBe(999);
    expect(session2MutationCalls).toBe(1);

    // Resolve A1 late
    await act(async () => {
      resolveMoveA1({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'session-1', score: 5000 }),
      });
    });

    // Flush to allow A1 resolution to propagate
    await act(async () => {
      await Promise.resolve();
    });

    // Game should remain B, state unmodified by either resolved A1 or suppressed A2
    expect(result.current.game?.id).toBe('session-2');
    expect(result.current.game?.score).toBe(999);

    // Assert A2 never dispatches
    expect(session1MutationCalls).toBe(1);
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

  it('Deferred A/B automatic-tick regression test', async () => {
    let resolveTickA: any;
    const tickAPromise = new Promise((resolve) => { resolveTickA = resolve; });

    let resolveTickB: any;
    const tickBPromise = new Promise((resolve) => { resolveTickB = resolve; });

    let startCount = 0;
    let tickCountA = 0;
    let tickCountB = 0;

    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        startCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, id: `session-${startCount}` }),
        } as unknown as Response);
      }
      if (urlStr.includes('session-1/tick')) {
        tickCountA++;
        return tickAPromise as any;
      }
      if (urlStr.includes('session-2/tick')) {
        tickCountB++;
        return tickBPromise as any;
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());

    // 1. Start game A
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-1');

    // Advance 500 ms to trigger A's tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    // Flush microtasks and assert A's tick fetch has begun before restarting
    await act(async () => {
      await Promise.resolve();
    });
    expect(tickCountA).toBe(1);

    // 2. Restart and start B successfully
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.id).toBe('session-2');

    // Advance 500 ms to trigger B's tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });

    // Flush microtasks and assert B's tick fetch has begun before settling A
    await act(async () => {
      await Promise.resolve();
    });
    expect(tickCountB).toBe(1);

    // 3. Settle A while B remains pending
    await act(async () => {
      resolveTickA({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'session-1', score: 100 }),
      });
    });

    // Flush microtasks
    await act(async () => {
      await Promise.resolve();
    });

    // Verify A never overwrites B (B remains active, A's state is discarded)
    expect(result.current.game?.id).toBe('session-2');

    // 4. Advance multiple B timer intervals while B's tick is still pending.
    // In an unowned-finally implementation, A's tick settling cleared B's pending flag.
    // So advancing B's interval would queue another B tick.
    // With proper generation-owned coalescing, B's pending token is still active, so no extra ticks are queued.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500); // 3 more intervals
    });

    // Prove no extra B tick request/queued burst is admitted
    expect(tickCountB).toBe(1);

    // 5. Resolve B's tick
    await act(async () => {
      resolveTickB({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, id: 'session-2', score: 200 }),
      });
    });

    await act(async () => {
      await Promise.resolve();
    });

    // Check that we got the updated score from B's tick
    expect(result.current.game?.score).toBe(200);

    // Only one B tick was ever triggered so far
    expect(tickCountB).toBe(1);

    // 6. Verify only the next proper interval triggers exactly one fresh tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    // This should trigger the second tick for B
    expect(tickCountB).toBe(2);
  });

  it('stops automatic tick immediately when status becomes game_over', async () => {
    let tickCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      if (urlStr.endsWith('/tick')) {
        tickCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, status: 'game_over' }),
        } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());

    // Start game
    await act(async () => {
      await result.current.startGame();
    });

    // Trigger tick which returns game_over
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickCount).toBe(1);
    expect(result.current.game?.status).toBe('game_over');

    // Advance timer by 2000 ms and check that no more ticks are scheduled/dispatched
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(tickCount).toBe(1);
  });

  it('cancels timer on game-over or unmount while old work is pending/queued, and settling does not write stale state', async () => {
    let resolveTick: any;
    const tickPromise = new Promise((resolve) => { resolveTick = resolve; });

    let tickCount = 0;
    let moveCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      if (urlStr.endsWith('/tick')) {
        tickCount++;
        return tickPromise as any;
      }
      if (urlStr.endsWith('/move')) {
        moveCount++;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockGameSession) } as unknown as Response);
    });

    const { unmount, result } = renderHook(() => useGame());

    // Start game
    await act(async () => {
      await result.current.startGame();
    });

    // Advance 500 ms to trigger tick (tickCount becomes 1, and is pending/queued)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(tickCount).toBe(1);

    // Queue a mutation (should be queued behind in-flight tick)
    act(() => {
      result.current.move('left');
    });

    // Assert that the queued work hasn't dispatched yet
    expect(moveCount).toBe(0);

    // Save the pre-unmount snapshot of the game
    const preUnmountGame = result.current.game;
    expect(preUnmountGame).not.toBeNull();

    // Unmount hook
    unmount();

    // Now resolve the pending tick
    await act(async () => {
      resolveTick({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 9999 }),
      });
    });

    // Advance timers by 2000 ms
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // Prove that queued work never dispatches
    expect(moveCount).toBe(0);
    // Explicit tickCount unchanged after post-unmount timer advance
    expect(tickCount).toBe(1);

    // Verify last rendered snapshot remains unchanged and retains pre-unmount state
    expect(result.current.game).toBe(preUnmountGame);
    expect(result.current.game?.score).toBe(0); // Tick resolving with score 9999 did not write to state
  });

  it('Terminal game-over-with-queued-work evidence: accepted action yields game_over while a subsequent action is queued; assert queued work suppressed and timer stops', async () => {
    let resolveAction1: any;
    const action1Promise = new Promise((resolve) => { resolveAction1 = resolve; });

    let fetchCount = 0;
    let tickCount = 0;
    let mutationUrls: string[] = [];

    vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      fetchCount++;
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, status: 'playing' }),
        } as unknown as Response);
      }
      if (urlStr.endsWith('/tick')) {
        tickCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockGameSession, status: 'playing' }),
        } as unknown as Response);
      }
      
      // Track mutation URL
      mutationUrls.push(urlStr);
      if (mutationUrls.length === 1) {
        return action1Promise as any;
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, status: 'game_over' }),
      } as unknown as Response);
    });

    const { result } = renderHook(() => useGame());

    // Start game
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game?.status).toBe('playing');

    // Trigger action 1 (A1) -> will be pending, tracking url `/move`
    act(() => {
      result.current.move('left');
    });

    // Flush microtasks to dispatch the first fetch
    await act(async () => {
      await Promise.resolve();
    });

    // Assert that A1 fetch is actually pending/dispatched (mutationUrls has 1 item)
    expect(mutationUrls.length).toBe(1);
    expect(mutationUrls[0]).toContain('/move');

    // Queue a subsequent action A2 while A1 is pending
    act(() => {
      result.current.move('down');
    });

    // Flush microtasks to show queue barrier
    await act(async () => {
      await Promise.resolve();
    });
    // A2 should not be dispatched yet
    expect(mutationUrls.length).toBe(1);

    // Now resolve action A1 with status: 'game_over'
    await act(async () => {
      resolveAction1({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, status: 'game_over' }),
      });
    });

    // State should now be game_over
    expect(result.current.game?.status).toBe('game_over');

    // Settle microtasks / advance timers to ensure A2 has a chance to run if it weren't suppressed
    await act(async () => {
      await Promise.resolve();
    });

    // Assert that subsequent action A2 is suppressed/never dispatched (mutationUrls length remains 1)
    expect(mutationUrls.length).toBe(1);

    // Reset tick count to track if timer stops
    tickCount = 0;

    // Advance timers by 2000 ms to prove timer stops (no ticks dispatched)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(tickCount).toBe(0);
  });

  it('StrictMode mount, remount, start, play, and unmount', async () => {
    let resolveMutationA1: any;
    const mutationA1Promise = new Promise((resolve) => { resolveMutationA1 = resolve; });

    let mutationCalls = 0;
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url: any) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.endsWith('/api/games')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGameSession),
        } as unknown as Response);
      }
      
      mutationCalls++;
      if (mutationCalls === 1) {
        return mutationA1Promise as any;
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 8888 }),
      } as unknown as Response);
    });

    const { unmount, result } = renderHook(() => useGame(), {
      wrapper: ({ children }) => React.createElement(React.StrictMode, null, children),
    });

    expect(result.current.game).toBeNull();

    // Start game works inside StrictMode
    await act(async () => {
      await result.current.startGame();
    });
    expect(result.current.game).not.toBeNull();
    expect(result.current.game?.status).toBe('playing');

    // Play/Move works (this will trigger our first deferred mutation A1)
    fetchSpy.mockClear();
    act(() => {
      result.current.move('left');
    });

    // Flush microtasks to dispatch the first fetch
    await act(async () => {
      await Promise.resolve();
    });

    // Assert first mutation A1 is in-flight
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    // Queue a second mutation A2 behind A1
    act(() => {
      result.current.move('down');
    });

    // Flush microtasks - since A1 is pending, A2 must not be dispatched
    await act(async () => {
      await Promise.resolve();
    });

    // Prove queue barrier (fetchSpy still has only 1 call)
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const preUnmountGame = result.current.game;

    // Unmount hook
    unmount();

    // Now settle deferred work (resolve first mutation A1)
    await act(async () => {
      resolveMutationA1({
        ok: true,
        json: () => Promise.resolve({ ...mockGameSession, score: 7777 }),
      });
    });

    // Advance timers by 2000 ms to make sure no scheduled timers or queues fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // Prove no second mutation dispatch (A2 never dispatched)
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    // Prove no stale state written (A1's resolution did not update the state, remains preUnmountGame)
    expect(result.current.game).toBe(preUnmountGame);
    expect(result.current.game?.score).toBe(0); // the score was 0, it wasn't written to 7777 or 8888
  });
});
