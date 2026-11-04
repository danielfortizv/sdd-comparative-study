import type { StackLevels } from "../state/rpnReducer";
import "./StackDisplay.css";

/**
 * Props for {@link StackDisplay}.
 *
 * Presentational component: the Calculator container (task 59.3) owns the RPN
 * stack state (via `rpnReducer`) and passes the confirmed X/Y/Z/T levels down.
 * This display holds no state and performs no arithmetic — it only renders the
 * levels it is handed (Requirement 40.1).
 */
export interface StackDisplayProps {
  /**
   * The four visible RPN stack levels (X/Y/Z/T). A level is `undefined` when the
   * stack holds no value at that position (Requirements 40.1, 40.6).
   */
  stack: StackLevels;
}

/**
 * The ordered X/Y/Z/T levels of the RPN operand stack, top-visible-first.
 *
 * The visible/stored order is T (top, deepest) down to X (bottom, the value most
 * recently pushed and next to be consumed). Rendering T→X puts X closest to the
 * input area, matching the convention that operations act on X (and Y).
 */
const LEVELS: ReadonlyArray<{ key: keyof StackLevels; label: string }> = [
  { key: "t", label: "T" },
  { key: "z", label: "Z" },
  { key: "y", label: "Y" },
  { key: "x", label: "X" },
];

/**
 * A text placeholder shown for a level that currently holds no value
 * (Requirements 40.4, 40.6).
 */
const EMPTY_PLACEHOLDER = "—";

/**
 * Renders the X/Y/Z/T levels of the RPN operand stack (Requirement 40.1).
 *
 * - Each level carries a visible identifying label (X/Y/Z/T) alongside its value
 *   so the user can read which operand sits at which position (Requirement 40.1).
 * - A level with no value shows an empty-state indication rather than a blank
 *   cell; when the whole stack is empty every level shows the empty indication
 *   (Requirements 40.4, 40.6).
 * - The whole display is wrapped in an `aria-live="polite"` region (with
 *   `role="status"`) so changes to the stack are announced to assistive
 *   technologies without interrupting, reusing the Stage 1 display-announcement
 *   pattern (Requirement 40.5).
 * - Each level's value carries an `aria-label` that pairs its identifying label
 *   with its value (or "empty"), matching the visible label and reusing the
 *   Stage 1 accessibility pattern (Requirements 11, 12).
 */
export function StackDisplay({ stack }: StackDisplayProps) {
  return (
    <div
      className="stack-display"
      role="status"
      aria-live="polite"
      aria-label="RPN stack"
    >
      <ol className="stack-display__list">
        {LEVELS.map(({ key, label }) => {
          const value = stack[key];
          const hasValue = value !== undefined && value !== "";
          const display = hasValue ? value : EMPTY_PLACEHOLDER;
          const ariaLabel = hasValue
            ? `Stack level ${label}: ${value}`
            : `Stack level ${label}: empty`;

          return (
            <li key={key} className="stack-display__level">
              <span className="stack-display__label" aria-hidden="true">
                {label}
              </span>
              <span
                className={
                  hasValue
                    ? "stack-display__value"
                    : "stack-display__value stack-display__value--empty"
                }
                aria-label={ariaLabel}
              >
                {display}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default StackDisplay;
