/**
 * Evaluation orchestration hook (Requirements 14.3, 14.4).
 *
 * `useEvaluator` is the single bridge between the calculator UI and the backend
 * math oracle. It owns the transport lifecycle of an evaluation request: it calls
 * the typed API client's {@link evaluateExpression}, tracks whether a request is in
 * flight, and reports the outcome back to the caller through callbacks.
 *
 * It deliberately holds no arithmetic and produces no result of its own. A result
 * is only ever the string returned by a successful backend response (Requirement
 * 14.3); the client already collapses transport failures and non-conforming payloads
 * into an error message, and this hook simply routes that message to `onError`
 * (Requirement 14.4). This preserves the hard separation of concerns: the frontend
 * is an input/rendering surface and the backend is the only source of computed truth.
 *
 * Like {@link useKeyboard}, the hook accepts caller-supplied callbacks (typically thin
 * wrappers over the reducer's `SET_RESULT` / `SET_ERROR` dispatches) so the
 * `Calculator` container can wire evaluation into the same state (Task 12.4). The
 * latest callbacks are read through a ref so `evaluate` keeps a stable identity and
 * never invokes a stale closure.
 *
 * Requirements: 14.3, 14.4
 */

import { useCallback, useRef, useState } from "react";

import { evaluateExpression } from "../api/client";

/**
 * Callbacks the hook invokes when an evaluation resolves. The consumer supplies
 * these so the hook stays free of state and arithmetic concerns.
 */
export interface EvaluatorCallbacks {
  /**
   * Report a successful backend result. `result` is the exact decimal string
   * produced by the backend — never computed locally (Requirement 14.3). The
   * consumer typically dispatches `SET_RESULT`.
   */
  onResult: (result: string) => void;
  /**
   * Report an evaluation failure. `error` is a human-readable message: a backend
   * error (e.g. division by zero, invalid syntax) or the client's
   * service-unavailable message on transport failure (Requirement 14.4). The
   * consumer typically dispatches `SET_ERROR`.
   */
  onError: (error: string) => void;
}

/**
 * The value returned by {@link useEvaluator}.
 */
export interface UseEvaluatorResult {
  /**
   * Submit an Expression to the backend for evaluation. Resolves once the outcome
   * has been reported via the appropriate callback. Overlapping calls are guarded:
   * while a request is in flight, further calls resolve immediately without
   * dispatching a second request.
   */
  evaluate: (expression: string) => Promise<void>;
  /** `true` while an evaluation request is in flight, `false` otherwise. */
  isSubmitting: boolean;
}

/**
 * Manage backend evaluation for the calculator.
 *
 * @param callbacks Actions to invoke when an evaluation resolves.
 * @returns An `evaluate` function and the `isSubmitting` flag.
 */
export function useEvaluator(callbacks: EvaluatorCallbacks): UseEvaluatorResult {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Keep the newest callbacks in a ref so `evaluate` can stay stable (empty deps)
  // while always invoking the current callbacks — no stale closures.
  const callbacksRef = useRef<EvaluatorCallbacks>(callbacks);
  callbacksRef.current = callbacks;

  // A ref mirror of the in-flight state so the overlap guard reads the live value
  // synchronously, independent of the (batched) `isSubmitting` state update.
  const inFlightRef = useRef<boolean>(false);

  const evaluate = useCallback(async (expression: string): Promise<void> => {
    // Guard against overlapping submits: while a request is in flight, ignore
    // further calls so we never dispatch a second request or race the callbacks.
    if (inFlightRef.current) {
      return;
    }

    inFlightRef.current = true;
    setIsSubmitting(true);

    try {
      // Delegate to the backend for every expression, including empty/whitespace
      // input: the backend owns validation (it maps empty input to an error), which
      // keeps arithmetic and validation as a single source of truth (Requirement
      // 14.3) rather than duplicating rules in the client.
      const outcome = await evaluateExpression(expression);

      if (outcome.ok) {
        // A result is only ever the backend's exact decimal string (Requirement 14.3).
        callbacksRef.current.onResult(outcome.result);
      } else {
        // Backend error or the client's service-unavailable message on transport
        // failure — surfaced verbatim (Requirement 14.4).
        callbacksRef.current.onError(outcome.error);
      }
    } finally {
      inFlightRef.current = false;
      setIsSubmitting(false);
    }
  }, []);

  return { evaluate, isSubmitting };
}
