import { renderHook, act } from '@testing-library/react';
import { useEvaluate } from '../hooks/useEvaluate';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('useEvaluate Hook', () => {
  beforeEach(() => {
    const mockFetch = vi.fn().mockImplementation((url, options) => {
      const body = options && options.body ? JSON.parse(options.body) : {};
      const expr = body.expression || '';
      let resVal = '0';
      if (expr === '0 + (10)') resVal = '10';
      else if (expr === '10 - (10)') resVal = '0';
      else if (expr === '10 + (10)') resVal = '20';
      else if (expr === '0 + (20)') resVal = '20';
      else if (expr === '20 + (10)') resVal = '30';
      else if (expr === '10 + 5') resVal = '15';
      else if (expr === '5 + 3') resVal = '8';
      else if (expr === '2 + 3') resVal = '5';
      else if (expr === '10 / 0') {
        return Promise.resolve({
          ok: false,
          json: async () => ({ message: 'Error: Division by zero' }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ result: resVal }),
      });
    });
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should initialize with default states', () => {
    const { result } = renderHook(() => useEvaluate());

    expect(result.current.expression).toBe('');
    expect(result.current.result).toBe('0');
    expect(result.current.history).toBe('');
    expect(result.current.state).toBe('idle');
    expect(result.current.angleUnit).toBe('radians');
    expect(result.current.memory).toBe('0');
    expect(result.current.sessionHistory).toEqual([]);
  });

  it('should append tokens correctly', () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('5');
    });
    expect(result.current.expression).toBe('5');

    act(() => {
      result.current.appendToken(' + ');
    });
    expect(result.current.expression).toBe('5 + ');

    act(() => {
      result.current.appendToken('3');
    });
    expect(result.current.expression).toBe('5 + 3');
  });

  it('should trigger debounced API call for previews on balanced expression', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('5');
    });
    act(() => {
      result.current.appendToken(' + ');
    });
    act(() => {
      result.current.appendToken('3');
    });

    // At this point, "5 + 3" is balanced and doesn't end with operator.
    expect(result.current.state).toBe('active');

    // Fast-forward timers to trigger the debounce using the async variant
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(fetch).toHaveBeenCalled();
    expect(result.current.result).toBe('8');
    expect(result.current.state).toBe('preview');
    vi.useRealTimers();
  });

  it('should not trigger API call if parentheses are unbalanced', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('sin(');
    });
    act(() => {
      result.current.appendToken('5');
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(fetch).not.toHaveBeenCalled();
    expect(result.current.result).toBe('');
    vi.useRealTimers();
  });

  it('should handle final evaluation successfully', async () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('10 + 5');
    });

    await act(async () => {
      await result.current.evaluateFinal();
    });

    expect(result.current.expression).toBe('15');
    expect(result.current.result).toBe('15');
    expect(result.current.history).toBe('10 + 5 = 15');
    expect(result.current.state).toBe('evaluated');
    expect(result.current.sessionHistory).toEqual([
      { expression: '10 + 5', result: '15' },
    ]);
  });

  it('should handle evaluation errors gracefully', async () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('10 / 0');
    });

    await act(async () => {
      await result.current.evaluateFinal();
    });

    expect(result.current.state).toBe('error');
    expect(result.current.result).toBe('Error: Division by zero');
  });

  it('should clear everything when clearAll is called', () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('10 + 5');
    });
    act(() => {
      result.current.clearAll();
    });

    expect(result.current.expression).toBe('');
    expect(result.current.result).toBe('0');
    expect(result.current.history).toBe('');
    expect(result.current.state).toBe('idle');
  });

  it('should execute backspace correctly', () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('123');
    });
    expect(result.current.expression).toBe('123');

    act(() => {
      result.current.backspace();
    });
    expect(result.current.expression).toBe('12');

    // When in error state, backspace should clear all
    act(() => {
      result.current.backspace();
    });
    expect(result.current.expression).toBe('1');
  });

  it('should toggle angle unit', () => {
    const { result } = renderHook(() => useEvaluate());

    expect(result.current.angleUnit).toBe('radians');

    act(() => {
      result.current.toggleAngleUnit();
    });
    expect(result.current.angleUnit).toBe('degrees');

    act(() => {
      result.current.toggleAngleUnit();
    });
    expect(result.current.angleUnit).toBe('radians');
  });

  it('should handle memory operations correctly', async () => {
    const { result } = renderHook(() => useEvaluate());

    // Initially 0
    expect(result.current.memory).toBe('0');

    // Simulate evaluating something to have result "10"
    act(() => {
      result.current.appendToken('10');
    });

    // M+ adds to memory
    await act(async () => {
      await result.current.handleMemoryOperation('add');
    });
    expect(result.current.memory).toBe('10');

    // M- subtracts from memory
    await act(async () => {
      await result.current.handleMemoryOperation('subtract');
    });
    expect(result.current.memory).toBe('0');

    // MC clears memory
    await act(async () => {
      await result.current.handleMemoryOperation('add');
    });
    await act(async () => {
      await result.current.handleMemoryOperation('add');
    });
    expect(result.current.memory).toBe('20');

    act(() => {
      result.current.clearMemory();
    });
    expect(result.current.memory).toBe('0');

    // MR recalls memory back to display
    await act(async () => {
      await result.current.handleMemoryOperation('add'); // adds result '10' to memory
    });
    act(() => {
      result.current.clearAll();
    });
    expect(result.current.expression).toBe('');

    act(() => {
      result.current.recallMemory();
    });
    expect(result.current.expression).toBe('10');
  });

  it('should load history expressions and results', () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.loadHistoryExpression('sin(pi)');
    });
    expect(result.current.expression).toBe('sin(pi)');

    act(() => {
      result.current.loadHistoryResult('0.5');
    });
    expect(result.current.expression).toBe('0.5');
  });

  it('should clear session history', async () => {
    const { result } = renderHook(() => useEvaluate());

    act(() => {
      result.current.appendToken('2 + 3');
    });

    await act(async () => {
      await result.current.evaluateFinal();
    });

    expect(result.current.sessionHistory.length).toBe(1);

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.sessionHistory).toEqual([]);
  });
});
