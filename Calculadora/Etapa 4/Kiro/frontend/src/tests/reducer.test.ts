// Calculator reducer + input-handling tests (tasks 11.3 / 29.1; Properties 8-11).
// Feature: web-calculator, Property 8: Mapped character keys append their character
// Feature: web-calculator, Property 9: Backspace removes exactly the last character
// Feature: web-calculator, Property 10: Escape resets to the empty state
// Feature: web-calculator, Property 11: Unmapped keys are no-ops
// Validates: Requirements 7.1, 7.2, 7.3, 7.6, 10.1, 10.2, 10.3, 10.5, 10.6, 10.7, 29.1
import { describe, expect, it } from 'vitest';
import {
  calculatorReducer,
  initialState,
} from '../state/calculatorReducer';
import { isError, isSuccess } from '../api/types';

describe('calculatorReducer', () => {
  it('starts empty: no expression, result, or error (7.1, 7.2)', () => {
    expect(initialState.expression).toBe('');
    expect(initialState.result).toBeNull();
    expect(initialState.error).toBeNull();
  });

  it('APPEND_CHAR appends digits, operators, decimal, and parens (10.1-10.3)', () => {
    let s = initialState;
    for (const ch of ['1', '+', '2', '.', '5', '(', ')']) {
      s = calculatorReducer(s, { type: 'APPEND_CHAR', char: ch });
    }
    expect(s.expression).toBe('1+2.5()');
  });

  it('each APPEND_CHAR increases length by exactly one (Property 8)', () => {
    let s = initialState;
    const chars = '7*3-4/2'.split('');
    chars.forEach((ch, i) => {
      s = calculatorReducer(s, { type: 'APPEND_CHAR', char: ch });
      expect(s.expression.length).toBe(i + 1);
    });
  });

  it('BACKSPACE removes exactly the last character (Property 9, 10.5)', () => {
    let s = { ...initialState, expression: '12+3' };
    s = calculatorReducer(s, { type: 'BACKSPACE' });
    expect(s.expression).toBe('12+');
  });

  it('BACKSPACE on an empty expression is a no-op (10.6)', () => {
    const s = calculatorReducer(initialState, { type: 'BACKSPACE' });
    expect(s.expression).toBe('');
    expect(s).toBe(initialState);
  });

  it('RESET returns to the initial empty state (Property 10, 10.7)', () => {
    const dirty = {
      expression: '9*9',
      result: '81',
      error: null,
      status: 'idle' as const,
    };
    expect(calculatorReducer(dirty, { type: 'RESET' })).toEqual(initialState);
  });

  it('SET_RESULT records a result and clears any error (7.6)', () => {
    const withError = { ...initialState, error: 'boom' };
    const s = calculatorReducer(withError, { type: 'SET_RESULT', result: '42' });
    expect(s.result).toBe('42');
    expect(s.error).toBeNull();
  });

  it('SET_ERROR records an error and clears any result (7.6)', () => {
    const withResult = { ...initialState, result: '42' };
    const s = calculatorReducer(withResult, { type: 'SET_ERROR', error: 'nope' });
    expect(s.error).toBe('nope');
    expect(s.result).toBeNull();
  });

  it('SUBMIT marks the evaluation in flight', () => {
    const s = calculatorReducer(initialState, { type: 'SUBMIT' });
    expect(s.status).toBe('submitting');
  });
});

describe('type guards (Property 13 support)', () => {
  it('isSuccess narrows a result-only payload', () => {
    expect(isSuccess({ result: '5' })).toBe(true);
    expect(isSuccess({ error: 'x' })).toBe(false);
    expect(isSuccess({ result: '5', error: 'x' })).toBe(false);
    expect(isSuccess(null)).toBe(false);
  });

  it('isError narrows an error-only payload', () => {
    expect(isError({ error: 'x' })).toBe(true);
    expect(isError({ result: '5' })).toBe(false);
    expect(isError(42)).toBe(false);
  });
});
