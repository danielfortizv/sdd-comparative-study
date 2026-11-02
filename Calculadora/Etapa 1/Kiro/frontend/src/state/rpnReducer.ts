/**
 * Pure state management for the calculator's RPN (Reverse Polish Notation) mode.
 *
 * This reducer owns ONLY the Frontend_Client's RPN input and Stack_Display state:
 * the active mode (Standard vs RPN), the in-progress operand entry, the X/Y/Z/T
 * operand stack, and an RPN error indication. Like the Stage 1/2 calculator
 * reducer, it NEVER computes any arithmetic result of an Expression — every result
 * is produced by the Backend_Service via the Evaluate_Endpoint (Requirement 39.9).
 * The reducer's job is limited to editing the operand entry and recording the
 * confirmed backend-driven stack / errors.
 *
 * Result and error are mutually exclusive: a confirmed stack update clears any
 * error, and an error leaves the stack unchanged and shows no computed result
 * (Requirements 39.7, 40.7).
 *
 * Requirements: 39.1, 39.2, 39.4, 39.6, 39.9, 40.2, 40.7
 */

/**
 * The calculator operating mode.
 * - `'standard'`: the unchanged Stage 1/2 infix workflow (default, Requirement 39.1).
 * - `'rpn'`: the postfix / stack workflow with an X/Y/Z/T Stack_Display.
 */
export type Mode = 'standard' | 'rpn';

/**
 * The four visible levels of the RPN operand stack, bottom-visible-first.
 *
 * Each level holds a Decimal operand **string** (never a `number`) so exact
 * precision carries through from the backend without float coercion. A level is
 * `undefined` when the stack does not currently hold a value at that position
 * (Requirements 40.1, 40.6).
 */
export interface StackLevels {
  x?: string;
  y?: string;
  z?: string;
  t?: string;
}

/**
 * The complete RPN UI state owned by the reducer.
 *
 * - `mode`: the active calculator mode. Defaults to `'standard'` so RPN state is
 *   fully isolated until the user opts in (Requirement 39.1).
 * - `operandEntry`: the in-progress operand string being typed before it is pushed
 *   onto the stack. Empty (`''`) when no operand is being entered.
 * - `stack`: the X/Y/Z/T operand stack of Decimal strings (Requirement 40.1).
 * - `error`: the RPN error indication, or `null` when none is displayed. The
 *   reducer never holds a locally computed result, so `error` is mutually exclusive
 *   with any backend-confirmed stack update (Requirements 39.7, 40.7).
 */
export interface RpnState {
  mode: Mode;
  operandEntry: string;
  stack: StackLevels;
  error: string | null;
}

/**
 * The initial, empty state: Standard_Mode, no operand entry, an empty stack, and no
 * error (Requirement 39.1).
 */
export const initialRpnState: RpnState = {
  mode: 'standard',
  operandEntry: '',
  stack: {},
  error: null,
};

/**
 * The set of actions the RPN UI can dispatch.
 *
 * String literal `type` discriminants form a discriminated union so the reducer can
 * exhaustively narrow each case with no use of `any`.
 */
export type RpnAction =
  /** Switch mode, clearing the operand entry, stack, and error (Requirement 39.2). */
  | { type: 'TOGGLE_MODE' }
  /** Append a single character to the in-progress operand entry. */
  | { type: 'APPEND_OPERAND_CHAR'; char: string }
  /** Enter_Control: push the operand entry onto the stack (Requirements 39.4, 40.2). */
  | { type: 'PUSH' }
  /** Replace the stack from a confirmed backend success, clearing any error (Requirement 40.3). */
  | { type: 'SET_STACK'; stack: StackLevels }
  /** Record an RPN error, leaving the stack unchanged (Requirements 39.6, 39.7, 40.7). */
  | { type: 'SET_RPN_ERROR'; error: string }
  /** Reset to the initial empty state, preserving the current mode. */
  | { type: 'RESET' };

/**
 * Compile-time exhaustiveness guard. If a new {@link RpnAction} variant is added
 * without a matching `case`, the `never`-typed parameter fails to type-check,
 * flagging the missing branch. At runtime an unhandled action leaves state unchanged.
 */
function assertNever(_action: never, state: RpnState): RpnState {
  return state;
}

/**
 * Pure reducer computing the next {@link RpnState} from the current state and an
 * action. It performs no side effects and no arithmetic (Requirement 39.9).
 */
export function rpnReducer(state: RpnState, action: RpnAction): RpnState {
  switch (action.type) {
    case 'TOGGLE_MODE':
      // Switching mode clears the operand entry, the stack, and the result/error so
      // no value carries across the switch (Requirement 39.2).
      return {
        mode: state.mode === 'standard' ? 'rpn' : 'standard',
        operandEntry: '',
        stack: {},
        error: null,
      };

    case 'APPEND_OPERAND_CHAR':
      // Build up the in-progress operand one character at a time. Any prior error
      // indication is cleared as the user resumes entering input.
      return {
        ...state,
        operandEntry: state.operandEntry + action.char,
        error: null,
      };

    case 'PUSH':
      // Enter_Control. With an empty operand entry this is a no-op that surfaces an
      // error indication rather than pushing nothing (Requirement 39.6).
      if (state.operandEntry.length === 0) {
        return {
          ...state,
          error: 'no operand to push',
        };
      }
      // With a non-empty operand entry, place it at X and shift X->Y->Z->T, dropping
      // the previous T when the stack is full; then clear the operand entry
      // (Requirements 39.4, 40.2).
      return {
        ...state,
        operandEntry: '',
        error: null,
        stack: {
          x: state.operandEntry,
          y: state.stack.x,
          z: state.stack.y,
          t: state.stack.z,
        },
      };

    case 'SET_STACK':
      // A confirmed backend success replaces the stack with the new levels and
      // clears any error, keeping result and error mutually exclusive
      // (Requirements 40.3, 39.7).
      return {
        ...state,
        stack: action.stack,
        error: null,
      };

    case 'SET_RPN_ERROR':
      // A guard rejection, backend Error_Response, or transport failure records an
      // error indication, leaves the stack unchanged, and shows no computed result
      // (Requirements 39.6, 39.7, 40.7).
      return {
        ...state,
        error: action.error,
      };

    case 'RESET':
      // Reset clears the operand entry, stack, and error but preserves the current
      // mode so a reset within RPN_Mode stays in RPN_Mode.
      return {
        ...initialRpnState,
        mode: state.mode,
      };

    default: {
      // Exhaustiveness guard: if a new action type is added without a matching case,
      // this assignment fails to type-check. Unknown actions leave state unchanged.
      return assertNever(action, state);
    }
  }
}
