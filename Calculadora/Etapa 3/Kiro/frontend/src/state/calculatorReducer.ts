/**
 * Pure state management for the calculator's expression / result / error UI state.
 *
 * This reducer owns ONLY the Frontend_Client's input and rendering state. It never
 * computes any arithmetic result of an Expression — all evaluation is delegated to
 * the Backend_Service via the Evaluate_Endpoint (Requirement 14.1). The reducer's
 * job is limited to editing the expression string and recording results/errors that
 * the backend has already produced.
 *
 * Result and error are mutually exclusive: setting a result clears any error and
 * setting an error clears any result (Requirement 7.6).
 *
 * Requirements: 7.1, 7.2, 7.3, 7.6, 10.1, 10.2, 10.3, 10.5, 10.7, 14.1
 */

/**
 * The lifecycle status of an evaluation request.
 * - `'idle'`: no evaluation in flight.
 * - `'submitting'`: an evaluation request has been dispatched to the backend and
 *   the client is awaiting a response.
 */
export type CalculatorStatus = 'idle' | 'submitting';

/**
 * The complete UI state owned by the calculator.
 *
 * - `expression`: the full input Expression string. Empty (`''`) in the initial
 *   state before any input is entered (Requirement 7.1).
 * - `result`: the calculated result string returned by the backend, or `null` when
 *   no result is displayed. Empty/`null` in the initial state (Requirement 7.2).
 * - `error`: the error message returned by the backend, or `null` when no error is
 *   displayed. `result` and `error` are never both non-null (Requirement 7.6).
 * - `status`: the evaluation lifecycle status.
 */
export interface CalculatorState {
  expression: string;
  result: string | null;
  error: string | null;
  status: CalculatorStatus;
}

/**
 * The initial, empty state: empty expression, no result, no error, idle
 * (Requirements 7.1, 7.2).
 */
export const initialState: CalculatorState = {
  expression: '',
  result: null,
  error: null,
  status: 'idle',
};

/**
 * The set of actions the calculator UI can dispatch.
 *
 * String literal `type` discriminants form a discriminated union so the reducer can
 * exhaustively narrow each case with no use of `any`.
 */
export type CalculatorAction =
  /** Append a single character to the expression (Requirements 10.1, 10.2, 10.3). */
  | { type: 'APPEND_CHAR'; char: string }
  /** Remove the last character from the expression; no-op when empty (Requirement 10.5). */
  | { type: 'BACKSPACE' }
  /** Reset to the initial empty state (Requirement 10.7). */
  | { type: 'RESET' }
  /** Mark an evaluation as in flight. */
  | { type: 'SUBMIT' }
  /** Record a backend result, clearing any error (Requirements 7.6). */
  | { type: 'SET_RESULT'; result: string }
  /** Record a backend error, clearing any result (Requirements 7.6). */
  | { type: 'SET_ERROR'; error: string };

/**
 * Compile-time exhaustiveness guard. If a new {@link CalculatorAction} variant is
 * added without a matching `case`, the `never`-typed parameter fails to type-check,
 * flagging the missing branch. At runtime an unhandled action leaves state unchanged.
 */
function assertNever(_action: never, state: CalculatorState): CalculatorState {
  return state;
}

/**
 * Pure reducer computing the next {@link CalculatorState} from the current state and
 * an action. It performs no side effects and no arithmetic (Requirement 14.1).
 */
export function calculatorReducer(
  state: CalculatorState,
  action: CalculatorAction,
): CalculatorState {
  switch (action.type) {
    case 'APPEND_CHAR':
      // Appending input reflects the current expression on each modification
      // (Requirement 7.3). Only the expression changes here.
      return {
        ...state,
        expression: state.expression + action.char,
      };

    case 'BACKSPACE':
      // Remove the most recently entered character (Requirement 10.5); leave the
      // expression unchanged when it is already empty (Requirement 10.6 no-op).
      if (state.expression.length === 0) {
        return state;
      }
      return {
        ...state,
        expression: state.expression.slice(0, -1),
      };

    case 'RESET':
      // Escape/reset returns to the initial empty state, clearing the expression
      // and the result/error display (Requirement 10.7).
      return initialState;

    case 'SUBMIT':
      // Mark an evaluation request as in flight. The result/error are resolved by a
      // subsequent SET_RESULT or SET_ERROR action driven by the backend response.
      return {
        ...state,
        status: 'submitting',
      };

    case 'SET_RESULT':
      // Displaying a result clears any previously displayed error (Requirement 7.6).
      return {
        ...state,
        result: action.result,
        error: null,
        status: 'idle',
      };

    case 'SET_ERROR':
      // Displaying an error clears any previously displayed result (Requirement 7.6).
      return {
        ...state,
        result: null,
        error: action.error,
        status: 'idle',
      };

    default: {
      // Exhaustiveness guard: if a new action type is added without a matching case,
      // this assignment fails to type-check. Unknown actions leave state unchanged.
      return assertNever(action, state);
    }
  }
}
