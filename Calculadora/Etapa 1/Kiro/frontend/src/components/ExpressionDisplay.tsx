/**
 * Renders the current input Expression entered by the User.
 *
 * The Expression_Display shows the full input Expression and is empty in the
 * initial state before any input is entered (Requirements 7.1, 7.3). The region is
 * marked `aria-live="polite"` so a screen reader announces each change to the
 * expression as the User edits it (Requirement 12.3).
 */

/**
 * Props for {@link ExpressionDisplay}.
 */
export interface ExpressionDisplayProps {
  /**
   * The full input Expression string to display. An empty string (`''`) renders an
   * empty display, which is the initial state before any input (Requirement 7.1).
   */
  expression: string;
}

/**
 * The Expression_Display region.
 *
 * - Shows the current expression string, or nothing when empty (Requirements 7.1, 7.3).
 * - `aria-live="polite"` announces expression changes to assistive technology
 *   without interrupting (Requirement 12.3).
 */
export function ExpressionDisplay({ expression }: ExpressionDisplayProps) {
  return (
    <div
      className="expression-display"
      aria-live="polite"
      aria-atomic="true"
      aria-label="Expression"
    >
      {expression}
    </div>
  );
}

export default ExpressionDisplay;
