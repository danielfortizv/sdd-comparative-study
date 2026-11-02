/**
 * Pure state management for the session Calculation_History.
 *
 * This reducer owns ONLY the ordered list of completed calculations surfaced in
 * the History_Panel. It stores {@link HistoryEntry} records newest-first and
 * exposes them for rendering; it performs no arithmetic and no network I/O.
 *
 * Append-on-success only (Requirement 21.7): the reducer appends an entry solely
 * when it receives a `HISTORY_APPEND` action, and the container/`useEvaluator`
 * (tasks 33 / 35.3) is responsible for dispatching that action ONLY on a
 * successful backend result — it is never dispatched on an error response, so an
 * error leaves the history unchanged. The reducer itself stays pure and simply
 * prepends whatever entry it is handed.
 *
 * Selecting a history entry's expression or result to replace the entire current
 * expression (Requirements 21.3, 21.4) is wired in the container via the
 * `calculatorReducer`; this reducer only stores and exposes entries and MUST NOT
 * mutate any expression state.
 *
 * Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8
 */

import type { CalculationHistory, HistoryEntry } from '../api/types';

/**
 * Maximum number of entries the Calculation_History retains. When an append
 * would exceed this cap, the oldest entry (the last element, since the list is
 * newest-first) is dropped so the list never holds more than this many entries
 * (Requirements 21.1, 21.5).
 */
export const MAX_HISTORY = 100;

/**
 * The complete history state: a read-only, newest-first list of calculation
 * entries. Using {@link CalculationHistory} directly (rather than wrapping it in
 * an object) keeps the state minimal and immutable.
 *
 * Empty (`[]`) in the initial state before any successful evaluation, which the
 * History_Panel renders as an empty-state indication (Requirement 21.8).
 */
export type HistoryState = CalculationHistory;

/**
 * The initial, empty history (Requirement 21.8). No entries are present until a
 * successful evaluation is appended by the container.
 */
export const initialHistory: CalculationHistory = [];

/**
 * The set of actions the Calculation_History can dispatch.
 *
 * String literal `type` discriminants form a discriminated union so the reducer
 * can exhaustively narrow each case with no use of `any`.
 */
export type HistoryAction =
  /**
   * Prepend a completed calculation to the front of the list (newest-first,
   * Requirement 21.2), capping the list at {@link MAX_HISTORY} by dropping the
   * oldest entry (Requirements 21.1, 21.5). Dispatched by the container only on a
   * successful backend result, never on an error (Requirement 21.7).
   */
  | { type: 'HISTORY_APPEND'; entry: HistoryEntry }
  /** Clear the entire history, returning it to the empty state (Requirement 21.6). */
  | { type: 'HISTORY_CLEAR' };

/**
 * Compile-time exhaustiveness guard. If a new {@link HistoryAction} variant is
 * added without a matching `case`, the `never`-typed parameter fails to
 * type-check, flagging the missing branch. At runtime an unhandled action leaves
 * state unchanged.
 */
function assertNever(
  _action: never,
  state: CalculationHistory,
): CalculationHistory {
  return state;
}

/**
 * Pure reducer computing the next {@link HistoryState} from the current state and
 * an action. It performs no side effects and never mutates the input list —
 * every transition returns a new read-only array.
 */
export function historyReducer(
  state: CalculationHistory,
  action: HistoryAction,
): CalculationHistory {
  switch (action.type) {
    case 'HISTORY_APPEND': {
      // Prepend the new entry so the list stays newest-first (Requirement 21.2),
      // then retain at most MAX_HISTORY entries by dropping the oldest from the
      // tail (Requirements 21.1, 21.5). `slice` returns a new array, so the input
      // is never mutated.
      return [action.entry, ...state].slice(0, MAX_HISTORY);
    }

    case 'HISTORY_CLEAR':
      // Clearing returns a fresh empty list (Requirement 21.6); the shared
      // `initialHistory` constant is already an empty read-only array.
      return initialHistory;

    default: {
      // Exhaustiveness guard: if a new action type is added without a matching
      // case, this assignment fails to type-check. Unknown actions leave state
      // unchanged.
      return assertNever(action, state);
    }
  }
}

/**
 * Pure selector reporting whether the Calculation_History is empty, so the
 * History_Panel can render an empty-state indication (Requirement 21.8).
 */
export function isHistoryEmpty(history: CalculationHistory): boolean {
  return history.length === 0;
}
