// History reducer tests (Property 21 + empty state; tasks 34.2, 43.4).
// Feature: web-calculator, Property 21: Calculation history invariants
// Validates: Requirements 21.1, 21.2, 21.5, 21.6, 21.7, 21.8, 29.4
import { describe, expect, it } from 'vitest';
import {
  MAX_HISTORY,
  historyReducer,
  initialHistory,
  isHistoryEmpty,
} from '../state/historyReducer';
import type { HistoryEntry } from '../api/types';

const entry = (expression: string, result: string): HistoryEntry => ({
  expression,
  result,
});

describe('historyReducer', () => {
  it('starts empty and reports the empty state (21.8)', () => {
    expect(initialHistory).toEqual([]);
    expect(isHistoryEmpty(initialHistory)).toBe(true);
  });

  it('prepends appended entries newest-first (21.1, 21.2)', () => {
    let state = historyReducer(initialHistory, {
      type: 'HISTORY_APPEND',
      entry: entry('1+1', '2'),
    });
    state = historyReducer(state, {
      type: 'HISTORY_APPEND',
      entry: entry('2+2', '4'),
    });
    expect(state[0]).toEqual(entry('2+2', '4'));
    expect(state[1]).toEqual(entry('1+1', '2'));
    expect(isHistoryEmpty(state)).toBe(false);
  });

  it('caps the list at MAX_HISTORY dropping the oldest (21.1, 21.5)', () => {
    let state = initialHistory;
    for (let i = 0; i < MAX_HISTORY + 5; i += 1) {
      state = historyReducer(state, {
        type: 'HISTORY_APPEND',
        entry: entry(`${i}`, `${i}`),
      });
    }
    expect(state.length).toBe(MAX_HISTORY);
    // Newest is the last appended; oldest surviving is index MAX_HISTORY+4 - 99.
    expect(state[0]).toEqual(entry(`${MAX_HISTORY + 4}`, `${MAX_HISTORY + 4}`));
    expect(state[state.length - 1]).toEqual(entry('5', '5'));
  });

  it('clearing empties the history (21.6)', () => {
    let state = historyReducer(initialHistory, {
      type: 'HISTORY_APPEND',
      entry: entry('9', '9'),
    });
    state = historyReducer(state, { type: 'HISTORY_CLEAR' });
    expect(state).toEqual([]);
    expect(isHistoryEmpty(state)).toBe(true);
  });

  it('does not mutate the input array (purity)', () => {
    const before = initialHistory;
    historyReducer(before, { type: 'HISTORY_APPEND', entry: entry('1', '1') });
    expect(before).toEqual([]);
  });
});
