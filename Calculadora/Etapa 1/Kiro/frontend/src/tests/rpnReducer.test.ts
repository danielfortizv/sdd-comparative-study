// RPN reducer unit + property tests (task 62.1; Properties 31, 33).
// Feature: web-calculator, Property 31: RPN push places the operand at X and shifts prior levels
// Feature: web-calculator, Property 33: Switching mode resets all transient state
// Validates: Requirements 39.2, 39.4, 39.6, 40.2, 40.3, 40.7
import { describe, expect, it } from 'vitest';
import {
  rpnReducer,
  initialRpnState,
  type RpnState,
  type StackLevels,
} from '../state/rpnReducer';

describe('rpnReducer', () => {
  it('starts in standard mode with no operand, empty stack, and no error (39.1)', () => {
    expect(initialRpnState.mode).toBe('standard');
    expect(initialRpnState.operandEntry).toBe('');
    expect(initialRpnState.stack).toEqual({});
    expect(initialRpnState.error).toBeNull();
  });

  describe('TOGGLE_MODE (39.2)', () => {
    it('flips standard -> rpn and clears operand, stack, and error', () => {
      const dirty: RpnState = {
        mode: 'standard',
        operandEntry: '42',
        stack: { x: '1', y: '2', z: '3', t: '4' },
        error: 'boom',
      };
      const next = rpnReducer(dirty, { type: 'TOGGLE_MODE' });
      expect(next.mode).toBe('rpn');
      expect(next.operandEntry).toBe('');
      expect(next.stack).toEqual({});
      expect(next.error).toBeNull();
    });

    it('flips rpn -> standard and clears all transient state (Property 33)', () => {
      const dirty: RpnState = {
        mode: 'rpn',
        operandEntry: '7',
        stack: { x: '9' },
        error: null,
      };
      const next = rpnReducer(dirty, { type: 'TOGGLE_MODE' });
      expect(next.mode).toBe('standard');
      expect(next.operandEntry).toBe('');
      expect(next.stack).toEqual({});
      expect(next.error).toBeNull();
    });

    // Property 33: regardless of the prior transient state, switching mode always
    // yields the empty transient state in the opposite mode.
    it('resets all transient state across a table of starting states (Property 33)', () => {
      const cases: RpnState[] = [
        { mode: 'standard', operandEntry: '', stack: {}, error: null },
        { mode: 'standard', operandEntry: '1', stack: { x: '2' }, error: 'e' },
        { mode: 'rpn', operandEntry: '3.14', stack: { x: '1', y: '2', z: '3', t: '4' }, error: null },
        { mode: 'rpn', operandEntry: '', stack: { x: '5' }, error: 'oops' },
      ];
      for (const start of cases) {
        const next = rpnReducer(start, { type: 'TOGGLE_MODE' });
        expect(next.mode).toBe(start.mode === 'standard' ? 'rpn' : 'standard');
        expect(next.operandEntry).toBe('');
        expect(next.stack).toEqual({});
        expect(next.error).toBeNull();
      }
    });
  });

  describe('APPEND_OPERAND_CHAR', () => {
    it('appends characters one at a time to the operand entry', () => {
      let s: RpnState = { ...initialRpnState, mode: 'rpn' };
      for (const ch of ['1', '2', '.', '5']) {
        s = rpnReducer(s, { type: 'APPEND_OPERAND_CHAR', char: ch });
      }
      expect(s.operandEntry).toBe('12.5');
    });

    it('clears any prior error when the user resumes typing', () => {
      const withError: RpnState = { ...initialRpnState, mode: 'rpn', error: 'no operand to push' };
      const s = rpnReducer(withError, { type: 'APPEND_OPERAND_CHAR', char: '9' });
      expect(s.operandEntry).toBe('9');
      expect(s.error).toBeNull();
    });
  });

  describe('PUSH (39.4, 39.6, 40.2)', () => {
    it('pushes a non-empty entry to X, shifting X->Y->Z->T, and clears the entry (39.4, 40.2)', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '5',
        stack: { x: '1', y: '2', z: '3' },
        error: null,
      };
      const next = rpnReducer(start, { type: 'PUSH' });
      expect(next.stack).toEqual({ x: '5', y: '1', z: '2', t: '3' });
      expect(next.operandEntry).toBe('');
      expect(next.error).toBeNull();
    });

    it('drops the previous T when the stack is already full', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '9',
        stack: { x: '1', y: '2', z: '3', t: '4' },
        error: null,
      };
      const next = rpnReducer(start, { type: 'PUSH' });
      expect(next.stack).toEqual({ x: '9', y: '1', z: '2', t: '3' });
    });

    it('with an empty entry is a no-op that surfaces an error and leaves the stack unchanged (39.6)', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '',
        stack: { x: '1' },
        error: null,
      };
      const next = rpnReducer(start, { type: 'PUSH' });
      expect(next.error).toBe('no operand to push');
      expect(next.stack).toEqual({ x: '1' });
      expect(next.operandEntry).toBe('');
    });

    // Property 31: for a non-empty entry, the pushed value always lands at X and the
    // prior X/Y/Z shift down to Y/Z/T across a range of stack fill levels.
    it('always places the operand at X and shifts prior levels down (Property 31)', () => {
      const stacks: StackLevels[] = [
        {},
        { x: '1' },
        { x: '1', y: '2' },
        { x: '1', y: '2', z: '3' },
        { x: '1', y: '2', z: '3', t: '4' },
      ];
      for (const stack of stacks) {
        const start: RpnState = { mode: 'rpn', operandEntry: '42', stack, error: null };
        const next = rpnReducer(start, { type: 'PUSH' });
        expect(next.stack.x).toBe('42');
        expect(next.stack.y).toBe(stack.x);
        expect(next.stack.z).toBe(stack.y);
        expect(next.stack.t).toBe(stack.z);
        expect(next.operandEntry).toBe('');
      }
    });
  });

  describe('SET_STACK (40.3)', () => {
    it('replaces the stack with the backend-confirmed levels and clears any error', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '',
        stack: { x: '1', y: '2' },
        error: 'stale error',
      };
      const next = rpnReducer(start, { type: 'SET_STACK', stack: { x: '3' } });
      expect(next.stack).toEqual({ x: '3' });
      expect(next.error).toBeNull();
    });
  });

  describe('SET_RPN_ERROR (39.7, 40.7)', () => {
    it('records the error and leaves the stack unchanged', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '',
        stack: { x: '1', y: '2' },
        error: null,
      };
      const next = rpnReducer(start, { type: 'SET_RPN_ERROR', error: 'insufficient values' });
      expect(next.error).toBe('insufficient values');
      expect(next.stack).toEqual({ x: '1', y: '2' });
    });
  });

  describe('RESET', () => {
    it('clears operand, stack, and error but preserves the current mode', () => {
      const start: RpnState = {
        mode: 'rpn',
        operandEntry: '7',
        stack: { x: '9' },
        error: 'boom',
      };
      const next = rpnReducer(start, { type: 'RESET' });
      expect(next.mode).toBe('rpn');
      expect(next.operandEntry).toBe('');
      expect(next.stack).toEqual({});
      expect(next.error).toBeNull();
    });
  });
});
