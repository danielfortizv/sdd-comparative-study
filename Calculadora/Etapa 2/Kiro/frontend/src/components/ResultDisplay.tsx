/**
 * Renders either the calculated result or the error message returned by the
 * Backend_Service.
 *
 * The Result_Display is empty in the initial state before any result is returned
 * (Requirement 7.2). It shows the calculated result when the backend returns one
 * (Requirement 7.4) and shows the error message text when the backend returns an
 * Error_Response (Requirement 7.5). Result and error are mutually exclusive in the
 * display (Requirement 7.6): the reducer never sets both, and this component renders
 * the result when present, the error when present, and nothing when both are `null`.
 *
 * Accessibility:
 * - The result region is `aria-live="polite"` so successful results are announced
 *   without interrupting (Requirement 12.3).
 * - The error region is `aria-live="assertive"` so errors are announced promptly
 *   (Requirement 12.4).
 * - Both live regions remain mounted so that transitioning to the empty state (a
 *   reset) is itself announced as a change to empty content (Requirement 12.5).
 */

/**
 * Props for {@link ResultDisplay}.
 *
 * The prop shape mirrors the reducer's {@link CalculatorState}: `result` and `error`
 * are each either a string or `null`, and are never both non-null (Requirement 7.6).
 */
export interface ResultDisplayProps {
  /**
   * The calculated result string returned by the backend, or `null` when no result
   * is displayed (Requirements 7.2, 7.4).
   */
  result: string | null;
  /**
   * The error message returned by the backend, or `null` when no error is displayed
   * (Requirements 7.5).
   */
  error: string | null;
}

/**
 * The Result_Display region.
 *
 * Renders the result (polite live region) and the error (assertive live region) as
 * two mutually exclusive slots. When both are `null` — the initial and reset state —
 * both regions render empty (Requirements 7.2, 7.6, 12.5).
 */
export function ResultDisplay({ result, error }: ResultDisplayProps) {
  return (
    <div className="result-display">
      <div
        className="result-display__result"
        aria-live="polite"
        aria-atomic="true"
        aria-label="Result"
      >
        {result ?? ''}
      </div>
      <div
        className="result-display__error"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        aria-label="Error"
      >
        {error ?? ''}
      </div>
    </div>
  );
}

export default ResultDisplay;
