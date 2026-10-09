/**
 * The Calculator container — the single stateful component that owns all UI state
 * for the calculator and wires together every other piece of the frontend.
 *
 * State is owned exclusively here via `useReducer(calculatorReducer, initialState)`:
 * the expression string, the backend result, the backend error, and the evaluation
 * status all live in one reducer (Requirement 14.1). This component computes no
 * arithmetic of its own; every result and error it renders originates from the
 * Backend_Service through {@link useEvaluator} (Requirements 14.1, 14.3).
 *
 * Wiring:
 * - {@link ExpressionDisplay} renders `state.expression`, reflecting every input as
 *   it is entered (Requirement 7.3).
 * - {@link ResultDisplay} renders `state.result` / `state.error` (mutually exclusive).
 * - {@link Keypad} routes on-screen control activations to reducer dispatches:
 *   `onInput` → `APPEND_CHAR`, `onEvaluate` → submit, `onReset` → `RESET`.
 * - {@link useKeyboard} routes physical-key input to the same actions so the keyboard
 *   and the keypad drive identical behavior (Requirement 8.4 parity of input paths).
 * - {@link useEvaluator} performs the backend call and reports the outcome back into
 *   the reducer via `SET_RESULT` / `SET_ERROR`.
 *
 * Avoiding stale closures: `useKeyboard` captures its callbacks once (it subscribes
 * a single window listener), and `useEvaluator.evaluate` is a stable identity. If the
 * submit handler closed over `state.expression` directly it would read the value from
 * the render in which the handler was created, not the latest keystrokes. To always
 * evaluate the CURRENT expression, we mirror `state.expression` into a ref and have
 * the submit handler read `expressionRef.current`.
 *
 * Requirements: 7.3, 8.4, 14.1, 14.3
 */

import { useCallback, useReducer, useRef } from 'react';

import { calculatorReducer, initialState } from '../state/calculatorReducer';
import { useKeyboard } from '../hooks/useKeyboard';
import { useEvaluator } from '../hooks/useEvaluator';
import { ExpressionDisplay } from './ExpressionDisplay';
import { ResultDisplay } from './ResultDisplay';
import { Keypad } from './Keypad';

/**
 * The root calculator component. Takes no props: it is fully self-contained and is
 * mounted directly by the `App` shell (Task 12.5).
 */
export function Calculator() {
  const [state, dispatch] = useReducer(calculatorReducer, initialState);

  // Mirror the latest expression into a ref so the (captured) submit handler always
  // evaluates the CURRENT expression rather than a value captured on an earlier
  // render. `useKeyboard` subscribes its callbacks once and `evaluate` is stable, so
  // without this ref the submit path could read a stale expression.
  const expressionRef = useRef<string>(state.expression);
  expressionRef.current = state.expression;

  // Route successful backend results and errors straight into the reducer. A result
  // is only ever the backend's string (Requirement 14.3); the reducer keeps result
  // and error mutually exclusive.
  const { evaluate } = useEvaluator({
    onResult: useCallback((result: string) => {
      dispatch({ type: 'SET_RESULT', result });
    }, []),
    onError: useCallback((error: string) => {
      dispatch({ type: 'SET_ERROR', error });
    }, []),
  });

  // Submit the CURRENT expression for evaluation. Reads `expressionRef.current` so it
  // is never bound to a stale render's expression. Marking SUBMIT keeps the status in
  // sync; `evaluate` resolves the outcome via SET_RESULT / SET_ERROR.
  const handleSubmit = useCallback((): void => {
    dispatch({ type: 'SUBMIT' });
    void evaluate(expressionRef.current);
  }, [evaluate]);

  // Thin, stable wrappers over reducer dispatches shared by the keypad and keyboard.
  const handleAppendChar = useCallback((char: string): void => {
    dispatch({ type: 'APPEND_CHAR', char });
  }, []);

  const handleBackspace = useCallback((): void => {
    dispatch({ type: 'BACKSPACE' });
  }, []);

  const handleReset = useCallback((): void => {
    dispatch({ type: 'RESET' });
  }, []);

  // Physical keyboard input drives the same actions as the on-screen keypad
  // (Requirement 8.4): digits/operators/parens append, Enter/= submits, Backspace
  // deletes, Escape resets.
  useKeyboard({
    onAppendChar: handleAppendChar,
    onSubmit: handleSubmit,
    onBackspace: handleBackspace,
    onReset: handleReset,
  });

  return (
    <div className="calculator" role="application" aria-label="calculator">
      <ExpressionDisplay expression={state.expression} />
      <ResultDisplay result={state.result} error={state.error} />
      <Keypad
        onInput={handleAppendChar}
        onEvaluate={handleSubmit}
        onReset={handleReset}
      />
    </div>
  );
}

export default Calculator;
