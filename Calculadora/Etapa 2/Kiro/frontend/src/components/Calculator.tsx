/**
 * The Calculator container — the single stateful component that owns all UI state
 * for the calculator and wires together every other piece of the frontend.
 *
 * State is composed from three pure reducers, all owned exclusively here:
 * - the Stage 1 {@link calculatorReducer} — the expression string, backend result,
 *   backend error, and evaluation status (Requirement 14.1). This component computes
 *   no arithmetic of its own; every result and error it renders originates from the
 *   Backend_Service through {@link useEvaluator} (Requirements 14.1, 14.3).
 * - the {@link memoryReducer} — the single Memory_Register value (Requirement 20.x).
 * - the {@link historyReducer} — the session Calculation_History (Requirement 21.x).
 *
 * Plus a small piece of local React state: the active {@link AngleMode}
 * (Requirement 22.1), which is threaded into every evaluation (Requirement 24.7).
 *
 * Wiring:
 * - {@link ExpressionDisplay} renders `state.expression`, reflecting every input as
 *   it is entered (Requirement 7.3).
 * - {@link ResultDisplay} renders `state.result` / `state.error` (mutually exclusive).
 * - {@link MemoryIndicator} renders near the display, shown iff the register is
 *   non-zero via `isMemoryActive(memory)` (Requirements 20.6, 20.7).
 * - {@link ScientificKeypad} renders the scientific controls and HOSTS the
 *   {@link AngleModeToggle}; the container passes `angleMode` + `onToggleAngleMode`
 *   to it (so the toggle is never double-rendered) together with the four memory
 *   handlers and the token-append handler (Requirement 22.1).
 * - {@link HistoryPanel} lists entries newest-first and routes expression/result
 *   selection and clear back into the history/calculator reducers (Requirement 21.x).
 * - {@link Keypad} routes Stage 1 on-screen control activations to reducer dispatches.
 * - {@link useKeyboard} routes physical-key input to the same actions, including
 *   multi-character scientific tokens via `onAppendToken` (Requirements 8.4, 23.x).
 * - {@link useEvaluator} performs the backend call under the active angle mode and
 *   reports the outcome back into the reducer via `SET_RESULT` / `SET_ERROR`, and
 *   appends to history on success only via `onHistoryAppend` (Requirements 21.1,
 *   21.2, 21.7, 24.7).
 *
 * Avoiding stale closures: `useKeyboard` captures its callbacks once (it subscribes
 * a single window listener), and `useEvaluator.evaluate` is a stable identity. If the
 * submit handler closed over `state.expression`/`angleMode` directly it would read
 * the value from the render in which the handler was created, not the latest input.
 * To always evaluate the CURRENT expression under the CURRENT angle mode, we mirror
 * both `state.expression` and `angleMode` into refs and have the submit handler read
 * `expressionRef.current` / `angleModeRef.current`.
 *
 * Loading a history entry: `calculatorReducer` has no `SET_EXPRESSION` action, so to
 * REPLACE the entire current expression (Requirements 21.3, 21.4) without modifying
 * that reducer we dispatch `RESET` (which returns the empty initial state, clearing
 * any stale result/error — acceptable when loading an entry) followed by a single
 * `APPEND_CHAR` carrying the whole selected string. `APPEND_CHAR` concatenates
 * `action.char` onto the (now empty) expression, so the expression becomes exactly
 * the selected string.
 *
 * Requirements: 7.3, 8.4, 14.1, 14.3, 20.4, 20.6, 20.7, 20.8, 20.9, 21.1, 21.2,
 * 21.3, 21.4, 21.6, 22.1, 24.7
 */

import { useCallback, useReducer, useRef, useState } from 'react';

import { calculatorReducer, initialState } from '../state/calculatorReducer';
import {
  memoryReducer,
  initialState as memoryInitialState,
  memoryValue,
  isMemoryActive,
  isNumericResult,
} from '../state/memoryReducer';
import { historyReducer, initialHistory } from '../state/historyReducer';
import type { AngleMode } from '../api/types';
import { useKeyboard } from '../hooks/useKeyboard';
import { useEvaluator } from '../hooks/useEvaluator';
import { ExpressionDisplay } from './ExpressionDisplay';
import { ResultDisplay } from './ResultDisplay';
import { MemoryIndicator } from './MemoryIndicator';
import { ScientificKeypad } from './ScientificKeypad';
import { HistoryPanel } from './HistoryPanel';
import { Keypad } from './Keypad';

/** Maximum Expression length the backend accepts; recall must never exceed it (Requirement 20.9). */
const MAX_EXPRESSION_LENGTH = 256;

/**
 * The root calculator component. Takes no props: it is fully self-contained and is
 * mounted directly by the `App` shell (Task 12.5).
 */
export function Calculator() {
  const [state, dispatch] = useReducer(calculatorReducer, initialState);
  const [memory, dispatchMemory] = useReducer(memoryReducer, memoryInitialState);
  const [history, dispatchHistory] = useReducer(historyReducer, initialHistory);

  // Active angle unit for trigonometric evaluation (Requirement 22.1). Defaults to
  // radians (Requirements 17.9, 24.4); `onToggleAngleMode` flips it (Requirement 22.7).
  const [angleMode, setAngleMode] = useState<AngleMode>('radians');

  // Mirror the latest expression into a ref so the (captured) submit handler always
  // evaluates the CURRENT expression rather than a value captured on an earlier
  // render. `useKeyboard` subscribes its callbacks once and `evaluate` is stable, so
  // without this ref the submit path could read a stale expression.
  const expressionRef = useRef<string>(state.expression);
  expressionRef.current = state.expression;

  // Mirror the active angle mode too, for the same reason: the stable keyboard submit
  // path must forward the CURRENT mode, not the one captured when the handler was
  // created (Requirement 24.7).
  const angleModeRef = useRef<AngleMode>(angleMode);
  angleModeRef.current = angleMode;

  // Route successful backend results and errors straight into the reducer. A result
  // is only ever the backend's string (Requirement 14.3); the reducer keeps result
  // and error mutually exclusive. A history entry is appended on SUCCESS only — the
  // hook invokes `onHistoryAppend` solely on a successful backend response, never on
  // an error (Requirements 21.1, 21.2, 21.7).
  const { evaluate } = useEvaluator({
    onResult: useCallback((result: string) => {
      dispatch({ type: 'SET_RESULT', result });
    }, []),
    onError: useCallback((error: string) => {
      dispatch({ type: 'SET_ERROR', error });
    }, []),
    onHistoryAppend: useCallback(
      (entry: { expression: string; result: string }) => {
        dispatchHistory({ type: 'HISTORY_APPEND', entry });
      },
      [],
    ),
  });

  // Submit the CURRENT expression for evaluation under the CURRENT angle mode. Reads
  // the refs so it is never bound to a stale render. Marking SUBMIT keeps the status
  // in sync; `evaluate` resolves the outcome via SET_RESULT / SET_ERROR.
  const handleSubmit = useCallback((): void => {
    dispatch({ type: 'SUBMIT' });
    void evaluate(expressionRef.current, angleModeRef.current);
  }, [evaluate]);

  // Thin, stable wrappers over reducer dispatches shared by the keypad and keyboard.
  // Since APPEND_CHAR concatenates its `char` string onto the expression, the SAME
  // handler appends a single character or a multi-character scientific token
  // (e.g. `sin(`, `pi`, `^`) — the keyboard routes single chars via `onAppendChar`
  // and multi-char tokens via `onAppendToken`, both pointing here (Requirement 23.x).
  const handleAppendToken = useCallback((token: string): void => {
    dispatch({ type: 'APPEND_CHAR', char: token });
  }, []);

  const handleBackspace = useCallback((): void => {
    dispatch({ type: 'BACKSPACE' });
  }, []);

  const handleReset = useCallback((): void => {
    dispatch({ type: 'RESET' });
  }, []);

  // Flip the angle mode between radians and degrees (Requirement 22.7). The state
  // update re-renders immediately, well within the 100 ms budget (Requirement 22.7).
  const handleToggleAngleMode = useCallback((): void => {
    setAngleMode((prev) => (prev === 'radians' ? 'degrees' : 'radians'));
  }, []);

  // --- Memory controls (Requirements 20.2-20.5, 20.8, 20.9) ------------------

  // M+ / M-: aggregate the CURRENT displayed result into the register. When there is
  // no numeric result the reducer no-ops; we ADDITIONALLY surface an error indication
  // so the user learns nothing was stored (Requirement 20.8).
  const handleMemoryAdd = useCallback((): void => {
    if (!isNumericResult(state.result)) {
      dispatch({ type: 'SET_ERROR', error: 'No numeric result available to store.' });
      return;
    }
    dispatchMemory({ type: 'MEM_ADD', result: state.result });
  }, [state.result]);

  const handleMemorySubtract = useCallback((): void => {
    if (!isNumericResult(state.result)) {
      dispatch({ type: 'SET_ERROR', error: 'No numeric result available to store.' });
      return;
    }
    dispatchMemory({ type: 'MEM_SUB', result: state.result });
  }, [state.result]);

  // MR: insert the register value into the Expression (Requirement 20.4), guarded so
  // the Expression never exceeds the 256-character limit (Requirement 20.9). The
  // register value is a (multi-char) decimal string; APPEND_CHAR concatenates it in
  // one dispatch. If appending would exceed the limit we leave the Expression
  // untouched and surface an error indication instead.
  const handleMemoryRecall = useCallback((): void => {
    const value = memoryValue(memory);
    const candidate = state.expression + value;
    if (candidate.length > MAX_EXPRESSION_LENGTH) {
      dispatch({
        type: 'SET_ERROR',
        error: 'Recalling memory would exceed the maximum expression length.',
      });
      return;
    }
    dispatch({ type: 'APPEND_CHAR', char: value });
  }, [memory, state.expression]);

  // MC: zero the register (Requirement 20.5).
  const handleMemoryClear = useCallback((): void => {
    dispatchMemory({ type: 'MEM_CLEAR' });
  }, []);

  // --- History selection (Requirements 21.3, 21.4, 21.6) ---------------------

  // Replace the entire current expression with a stored string. `calculatorReducer`
  // has no SET_EXPRESSION, so RESET (→ empty initial state) then a single APPEND_CHAR
  // of the whole string yields exactly that string as the new expression. RESET also
  // clears any stale result/error, which is acceptable when loading an entry.
  const loadExpression = useCallback((text: string): void => {
    dispatch({ type: 'RESET' });
    dispatch({ type: 'APPEND_CHAR', char: text });
  }, []);

  const handleSelectExpression = useCallback(
    (expression: string): void => {
      loadExpression(expression);
    },
    [loadExpression],
  );

  const handleSelectResult = useCallback(
    (result: string): void => {
      loadExpression(result);
    },
    [loadExpression],
  );

  const handleClearHistory = useCallback((): void => {
    dispatchHistory({ type: 'HISTORY_CLEAR' });
  }, []);

  // Physical keyboard input drives the same actions as the on-screen keypads
  // (Requirement 8.4): digits/operators/parens/`^` append via `onAppendChar`,
  // constants and function openers append via `onAppendToken`, Enter/= submits,
  // Backspace deletes, Escape resets. Both append paths point at the same handler
  // since APPEND_CHAR concatenates any string (Requirements 23.1, 23.2, 23.3).
  useKeyboard({
    onAppendChar: handleAppendToken,
    onAppendToken: handleAppendToken,
    onSubmit: handleSubmit,
    onBackspace: handleBackspace,
    onReset: handleReset,
  });

  const memoryActive = isMemoryActive(memory);

  return (
    <div className="calculator" role="application" aria-label="calculator">
      <div className="calculator__display">
        <MemoryIndicator active={memoryActive} />
        <ExpressionDisplay expression={state.expression} />
        <ResultDisplay result={state.result} error={state.error} />
      </div>

      <ScientificKeypad
        onInput={handleAppendToken}
        angleMode={angleMode}
        onToggleAngleMode={handleToggleAngleMode}
        onMemoryAdd={handleMemoryAdd}
        onMemorySubtract={handleMemorySubtract}
        onMemoryRecall={handleMemoryRecall}
        onMemoryClear={handleMemoryClear}
      />

      <Keypad
        onInput={handleAppendToken}
        onEvaluate={handleSubmit}
        onReset={handleReset}
      />

      <HistoryPanel
        history={history}
        onSelectExpression={handleSelectExpression}
        onSelectResult={handleSelectResult}
        onClear={handleClearHistory}
      />
    </div>
  );
}

export default Calculator;
