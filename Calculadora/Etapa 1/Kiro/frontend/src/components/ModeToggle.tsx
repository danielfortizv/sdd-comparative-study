import type { Mode } from "../state/rpnReducer";
import CalcButton from "./CalcButton";

/**
 * Props for {@link ModeToggle}.
 *
 * Presentational component: the Calculator container (task 59.3) owns the RPN
 * `mode` state (via `rpnReducer`) and the toggle logic. This control only
 * DISPLAYS the active mode (Requirement 39.1) and calls `onToggle` on activation
 * to request a switch to the other mode.
 */
export interface ModeToggleProps {
  /**
   * The currently active calculator mode. Defaults to `'standard'` at the
   * container level so the Stage 1/2 infix workflow is active until the user
   * opts in to RPN_Mode (Requirement 39.1).
   */
  mode: Mode;
  /**
   * Requests a switch to the other mode. The container toggles the mode in React
   * state; that update is synchronous on click and re-renders immediately, so the
   * displayed mode updates right away.
   */
  onToggle: () => void;
}

/**
 * A toggle control that displays the active calculator mode and switches it on
 * activation.
 *
 * - Displays the active mode as a short visible label — `STD` for Standard_Mode,
 *   `RPN` for RPN_Mode (Requirement 39.1).
 * - On activation it calls {@link ModeToggleProps.onToggle}; the container updates
 *   state immediately, so the displayed mode updates right away.
 * - Reuses the Stage 1 {@link CalcButton} accessibility pattern (native
 *   `<button>`, visible label + matching `aria-label`, inherited focus/pressed
 *   state). The accessible name communicates both the current mode and that
 *   activating switches it (e.g. "Calculator mode: standard. Activate to switch to
 *   RPN."). Uses the `action` variant.
 */
export function ModeToggle({ mode, onToggle }: ModeToggleProps) {
  const isStandard = mode === "standard";
  const label = isStandard ? "STD" : "RPN";
  const currentName = isStandard ? "standard" : "RPN";
  const otherName = isStandard ? "RPN" : "standard";
  const ariaLabel = `Calculator mode: ${currentName}. Activate to switch to ${otherName}.`;

  return (
    <CalcButton
      label={label}
      ariaLabel={ariaLabel}
      onActivate={onToggle}
      variant="action"
      className="mode-toggle"
    />
  );
}

export default ModeToggle;
