/**
 * The Calculator container — the single stateful component that owns all UI state
 * for the calculator and wires together every other piece of the frontend.
 *
 * State is composed from four pure reducers, all owned exclusively here:
 * - the Stage 1 {@link calculatorReducer} — the expression string, backend result,
 *   backend error, and evaluation status (Requirement 14.1). This component computes
 *   no arithmetic of its own; every result and error it renders originates from the
 *   Backend_Service through {@link useEvaluator} (Requirements 14.1, 14.3).
 * - the {@link memoryReducer} — the single Memory_Register value (Requirement 20.x).
 * - the {@link historyReducer} — the session Calculation_History (Requirement 21.x).
 * - the Stage 4 {@link rpnReducer} — the RPN operating mode, in-progress operand
 *   entry, X/Y/Z/T Stack_Display, and RPN error (Requirements 39.x, 40.x). Like the
 *   others it computes no arithmetic: every RPN result still comes from the backend
 *   (Requirements 39.9, 43.5).
 *
 * Plus a small piece of local React state: the active {@link AngleMode}
 * (Requirement 22.1), which is threaded into every evaluation (Requirement 24.7).
 *
 * Dual-mode wiring (Stage 4, Requirement 39.3):
 * - {@link ModeToggle} is ALWAYS rendered and flips `rpn.mode` between Standard and
 *   RPN (Requirement 39.1); switching modes resets the RPN operand/stack/error via
 *   the reducer's `TOGGLE_MODE` (Requirement 39.2).
 * - When `mode === "standard"` the ENTIRE unchanged Stage 1/2 infix surface renders
 *   and is wired EXACTLY as before (displays, `ScientificKeypad`, `Keypad`,
 *   `HistoryPanel`) — no Stage 1/2 behavior regresses (Requirement 39.3).
 * - When `mode === "rpn"` the {@link StackDisplay} and the {@link RpnKeypad} render;
 *   the `Enter` control pushes the operand onto the stack (`PUSH`, Requirements
 *   39.4, 40.2) and the operator controls drive the "build infix → submit →
 *   `SET_STACK` on success" backend flow (Requirements 39.5, 40.3).
 *
 * RPN operator flow (the key integration): for a binary operator with the two
 * required stack values (`X` and `Y`) the handler builds the infix expression
 * `"${y} ${op} ${x}"` and submits it to the SAME `/api/v1/evaluate` backend via
 * {@link evaluateExpression} under the active angle mode. The frontend computes
 * NOTHING locally (Requirements 39.9, 43.5). On a CONFIRMED backend success it
 * dispatches `SET_STACK` with the single result at `X` and the consumed `X`/`Y`
 * removed (`Z→Y`, `T→Z`); on a backend Error_Response or transport failure it
 * dispatches `SET_RPN_ERROR`, leaving the Stack_Display unchanged (Requirements
 * 40.7, 43.5). With fewer than the required values it is a no-op that sets an
 * "insufficient values" error indication and makes NO backend call (Requirement
 * 39.7).
 *
 * Input parity (Requirement 39.8): both the on-screen {@link RpnKeypad} and the
 * physical keyboard (via {@link useKeyboard}, which receives `mode`/`onPush`/
 * `onOperator`) drive identical RPN reducer actions / backend flow.
 *
 * Avoiding stale closures: `useKeyboard` captures its callbacks once and
 * `useEvaluator.evaluate` is a stable identity. The stable RPN operator handler
 * must read the CURRENT stack, mode, and angle mode rather than values captured on
 * an earlier render, so those are mirrored into refs (`stackRef`, `operandRef`,
 * `modeRef`, `angleModeRef`) and the handler reads `*.current`.
 *
 * Loading a history entry: `calculatorReducer` has no `SET_EXPRESSION` action, so to
 * REPLACE the entire current expression (Requirements 21.3, 21.4) without modifying
 * that reducer we dispatch `RESET` (which returns the empty initial state, clearing
 * any stale result/error) followed by a single `APPEND_CHAR` carrying the whole
 * selected string.
 *
 * Requirements: 7.3, 8.4, 14.1, 14.3, 20.4, 20.6, 20.7, 20.8, 20.9, 21.1, 21.2,
 * 21.3, 21.4, 21.6, 22.1, 24.7, 39.1, 39.2, 39.3, 39.4, 39.5, 39.7, 39.8, 39.9,
 * 40.2, 40.3, 40.7, 43.5
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
import {
  rpnReducer,
  initialRpnState,
  type Mode,
  type StackLevels,
} from '../state/rpnReducer';
import type { AngleMode } from '../api/types';
import { evaluateExpression } from '../api/client';
import { useKeyboard } from '../hooks/useKeyboard';
import { useEvaluator } from '../hooks/useEvaluator';
import { ExpressionDisplay } from './ExpressionDisplay';
import { ResultDisplay } from './ResultDisplay';
import { MemoryIndicator } from './MemoryIndicator';
import { ScientificKeypad } from './ScientificKeypad';
import { HistoryPanel } from './HistoryPanel';
import { Keypad } from './Keypad';
import { ModeToggle } from './ModeToggle';
import { StackDisplay } from './StackDisplay';
import { RpnKeypad } from './RpnKeypad';

/** Maximum Expression length the backend accepts; recall must never exceed it (Requirement 20.9). */
const MAX_EXPRESSION_LENGTH = 256;

/** Error indication shown when an operator is activated without the two required stack values (Requirement 39.7). */
const INSUFFICIENT_VALUES_MESSAGE = 'insufficient values';

/**
 * The root calculator component. Takes no props: it is fully self-contained and is
 * mounted directly by the `App` shell (Task 12.5).
 */
export function Calculator() {
  const [state, dispatch] = useReducer(calculatorReducer, initialState);
  const [memory, dispatchMemory] = useReducer(memoryReducer, memoryInitialState);
  const [history, dispatchHistory] = useReducer(historyReducer, initialHistory);
  const [rpn, dispatchRpn] = useReducer(rpnReducer, initialRpnState);

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
  // path (and the stable RPN operator handler) must forward the CURRENT mode, not the
  // one captured when the handler was created (Requirement 24.7).
  const angleModeRef = useRef<AngleMode>(angleMode);
  angleModeRef.current = angleMode;

  // Mirror the RPN mode, stack, and in-progress operand entry so the stable keyboard
  // callbacks and the stable async RPN operator handler always read the CURRENT
  // values rather than a stale render's. The RPN operator handler is async (it awaits
  // the backend) and keyboard-reachable, so it MUST read the live stack (Requirements
  // 39.5, 40.3, 40.7).
  const modeRef = useRef<Mode>(rpn.mode);
  modeRef.current = rpn.mode;
  const stackRef = useRef<StackLevels>(rpn.stack);
  stackRef.current = rpn.stack;
  const operandRef = useRef<string>(rpn.operandEntry);
  operandRef.current = rpn.operandEntry;

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

  // --- RPN mode controls (Stage 4; Requirements 39.x, 40.x) ------------------

  // Toggle between Standard_Mode and RPN_Mode (Requirement 39.1). The reducer's
  // TOGGLE_MODE also clears the operand entry, stack, and error so nothing carries
  // across the switch (Requirement 39.2).
  const handleToggleMode = useCallback((): void => {
    dispatchRpn({ type: 'TOGGLE_MODE' });
  }, []);

  // RPN operand entry: append a character to the in-progress operand entry
  // (Requirement 39.8), driven identically by the on-screen RpnKeypad and the
  // physical keyboard.
  const handleRpnOperandChar = useCallback((char: string): void => {
    dispatchRpn({ type: 'APPEND_OPERAND_CHAR', char });
  }, []);

  // Enter_Control: push the in-progress operand entry onto the stack (Requirements
  // 39.4, 40.2). The reducer no-ops (with an error indication) on an empty entry.
  const handleRpnPush = useCallback((): void => {
    dispatchRpn({ type: 'PUSH' });
  }, []);

  // Reset the RPN operand entry, stack, and error (preserving RPN_Mode).
  const handleRpnReset = useCallback((): void => {
    dispatchRpn({ type: 'RESET' });
  }, []);

  // RPN binary operator flow. Reads the CURRENT stack and operand entry from refs
  // (the handler is stable and keyboard-reachable). An in-progress operand entry is
  // first committed to the stack so typed-but-not-yet-pushed input participates,
  // mirroring standard RPN calculator behaviour and reusing the reducer's PUSH.
  //
  // With fewer than the two required values it is a NO-OP that sets an "insufficient
  // values" error indication and makes NO backend call (Requirement 39.7). With both
  // values it builds the infix expression `"${y} ${op} ${x}"` and submits it to the
  // backend under the active angle mode; the frontend computes nothing (Requirements
  // 39.9, 43.5). On a CONFIRMED backend success it replaces the consumed X/Y with the
  // single result at X and shifts Z→Y, T→Z via SET_STACK (Requirements 39.5, 40.3);
  // on a backend Error_Response or transport failure it sets an RPN error and leaves
  // the stack unchanged (Requirements 40.7, 43.5).
  const handleRpnOperator = useCallback(
    async (operator: string): Promise<void> => {
      // Snapshot the live stack, committing any pending operand entry into X first so
      // it is not silently lost when an operator is pressed mid-entry.
      let { x, y, z, t } = stackRef.current;
      const pending = operandRef.current;
      if (pending.length > 0) {
        // Commit the pending operand as the new X, shifting the prior levels up.
        t = z;
        z = y;
        y = x;
        x = pending;
        dispatchRpn({ type: 'PUSH' });
      }

      // A binary operator needs both X and Y. Fewer than two values → no-op with an
      // error indication and NO backend call (Requirement 39.7).
      if (x === undefined || x === '' || y === undefined || y === '') {
        dispatchRpn({ type: 'SET_RPN_ERROR', error: INSUFFICIENT_VALUES_MESSAGE });
        return;
      }

      // Build the infix expression from the top stack values and submit it to the
      // backend. The client never computes a result locally (Requirements 39.9, 43.5).
      const expression = `${y} ${operator} ${x}`;
      const outcome = await evaluateExpression(expression, angleModeRef.current);

      if (outcome.ok) {
        // Replace the consumed X and Y with the single backend result at X, shifting
        // Z→Y and T→Z (Requirements 39.5, 40.3). The result is the backend's exact
        // decimal string — never computed here (Requirement 39.9).
        dispatchRpn({
          type: 'SET_STACK',
          stack: { x: outcome.result, y: z, z: t, t: undefined },
        });
      } else {
        // Backend Error_Response or transport failure: retain the pre-operation
        // Stack_Display and show no local result (Requirements 40.7, 43.5).
        dispatchRpn({ type: 'SET_RPN_ERROR', error: outcome.error });
      }
    },
    [],
  );

  // Stable wrapper so the keyboard (whose callbacks are captured once) and the
  // on-screen keypad share the exact same operator handler. `void` because the
  // callbacks are synchronous-returning.
  const handleRpnOperatorSync = useCallback(
    (operator: string): void => {
      void handleRpnOperator(operator);
    },
    [handleRpnOperator],
  );

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
  // (Requirement 8.4). In Standard_Mode: digits/operators/parens/`^` append via
  // `onAppendChar`, constants and function openers append via `onAppendToken`,
  // Enter/= submits, Backspace deletes, Escape resets — EXACTLY as before. In
  // RPN_Mode (`mode`): Enter/= drives `PUSH` and the operator keys drive the RPN
  // operator flow, while digits/`.` append to the operand entry — matching the
  // on-screen RpnKeypad (Requirements 39.3, 39.8).
  useKeyboard({
    onAppendChar: rpn.mode === 'rpn' ? handleRpnOperandChar : handleAppendToken,
    onAppendToken: handleAppendToken,
    onSubmit: handleSubmit,
    onBackspace: handleBackspace,
    onReset: rpn.mode === 'rpn' ? handleRpnReset : handleReset,
    mode: rpn.mode,
    onPush: handleRpnPush,
    onOperator: handleRpnOperatorSync,
  });

  const memoryActive = isMemoryActive(memory);
  const isRpn = rpn.mode === 'rpn';

  return (
    <div className="calculator" role="application" aria-label="calculator">
      <div className="calculator__modebar">
        <ModeToggle mode={rpn.mode} onToggle={handleToggleMode} />
      </div>

      <div className="calculator__display">
        <MemoryIndicator active={memoryActive} />
        {isRpn ? (
          <>
            <ExpressionDisplay expression={rpn.operandEntry} />
            <StackDisplay stack={rpn.stack} />
            <ResultDisplay result={null} error={rpn.error} />
          </>
        ) : (
          <>
            <ExpressionDisplay expression={state.expression} />
            <ResultDisplay result={state.result} error={state.error} />
          </>
        )}
      </div>

      {isRpn ? (
        <RpnKeypad
          onOperandChar={handleRpnOperandChar}
          onPush={handleRpnPush}
          onOperator={handleRpnOperatorSync}
          onReset={handleRpnReset}
        />
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}

export default Calculator;
