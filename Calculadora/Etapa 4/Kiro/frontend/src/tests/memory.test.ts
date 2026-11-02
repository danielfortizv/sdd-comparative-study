// Memory reducer tests (Property 20 + guards; tasks 34.1, 43.2).
// Feature: web-calculator, Property 20: Memory register algebra and indicator invariant
// Validates: Requirements 20.1, 20.2, 20.3, 20.5, 20.6, 20.7, 20.8, 29.2
import { describe, expect, it } from 'vitest';
import {
  add,
  initialState,
  isMemoryActive,
  isNumericResult,
  memoryReducer,
  memoryValue,
  subtract,
} from '../state/memoryReducer';

describe('memoryReducer', () => {
  it('initializes the register to canonical zero (20.1)', () => {
    expect(initialState.value).toBe('0');
    expect(isMemoryActive(initialState)).toBe(false);
  });

  it('M+ adds the displayed result with exact decimal precision (20.2)', () => {
    const s1 = memoryReducer(initialState, { type: 'MEM_ADD', result: '0.1' });
    const s2 = memoryReducer(s1, { type: 'MEM_ADD', result: '0.2' });
    // Exact decimal: 0.1 + 0.2 == 0.3 (no float error).
    expect(s2.value).toBe('0.3');
    expect(isMemoryActive(s2)).toBe(true);
  });

  it('M- subtracts the displayed result (20.3)', () => {
    const s1 = memoryReducer(initialState, { type: 'MEM_ADD', result: '5' });
    const s2 = memoryReducer(s1, { type: 'MEM_SUB', result: '3' });
    expect(s2.value).toBe('2');
  });

  it('M+ then M- of the same value restores the register exactly (Property 20)', () => {
    const start = { value: '7.25' };
    const added = memoryReducer(start, { type: 'MEM_ADD', result: '1.33' });
    const restored = memoryReducer(added, { type: 'MEM_SUB', result: '1.33' });
    expect(restored.value).toBe('7.25');
  });

  it('MC zeroes the register and hides the indicator (20.5, 20.7)', () => {
    const active = { value: '42' };
    const cleared = memoryReducer(active, { type: 'MEM_CLEAR' });
    expect(cleared.value).toBe('0');
    expect(isMemoryActive(cleared)).toBe(false);
  });

  it('indicator is shown iff the register is non-zero (20.6, 20.7)', () => {
    expect(isMemoryActive({ value: '0' })).toBe(false);
    expect(isMemoryActive({ value: '-0.0000000001' })).toBe(true);
    expect(isMemoryActive({ value: '0.00' })).toBe(false);
  });

  it('M+ / M- with no numeric result leave the register unchanged (20.8)', () => {
    const start = { value: '9' };
    expect(memoryReducer(start, { type: 'MEM_ADD', result: null }).value).toBe('9');
    expect(memoryReducer(start, { type: 'MEM_SUB', result: 'abc' }).value).toBe('9');
  });

  it('MEM_RECALL does not mutate memory state', () => {
    const start = { value: '3' };
    expect(memoryReducer(start, { type: 'MEM_RECALL' })).toBe(start);
  });

  it('memoryValue exposes the register string', () => {
    expect(memoryValue({ value: '12.5' })).toBe('12.5');
  });

  it('isNumericResult accepts plain decimals and rejects non-numeric', () => {
    expect(isNumericResult('0.3')).toBe(true);
    expect(isNumericResult('-9')).toBe(true);
    expect(isNumericResult(null)).toBe(false);
    expect(isNumericResult('1e5')).toBe(false);
    expect(isNumericResult('oops')).toBe(false);
  });

  it('exact string add/subtract never use floats', () => {
    expect(add('0.1', '0.2')).toBe('0.3');
    expect(subtract('0', '5')).toBe('-5');
    expect(add('-5', '5')).toBe('0');
    expect(subtract('1.5', '0.5')).toBe('1');
  });
});
