import type { AngleMode } from "../api/types";
import CalcButton from "./CalcButton";

/**
 * Props for {@link AngleModeToggle}.
 *
 * Presentational component: the Calculator container (task 35.3) owns the
 * `angleMode` state and the flip logic. This control only DISPLAYS the active
 * mode (Requirement 22.6) and calls `onToggle` on activation to request a flip
 * (Requirement 22.7).
 */
export interface AngleModeToggleProps {
  /** The currently active angle unit for trigonometric evaluation. */
  angleMode: AngleMode;
  /**
   * Requests a flip to the other angle mode. The container flips the mode in
   * React state; that update is synchronous on click and re-renders immediately,
   * well within the 100 ms update budget (Requirement 22.7), so simply invoking
   * this callback satisfies the timing requirement.
   */
  onToggle: () => void;
}

/**
 * A toggle control that displays the active angle mode and flips it on
 * activation.
 *
 * - Displays the active mode as a short visible label — `RAD` for radians,
 *   `DEG` for degrees (Requirement 22.6).
 * - On activation it calls {@link AngleModeToggleProps.onToggle}; the container
 *   updates state immediately, so the displayed mode updates within 100 ms
 *   (Requirement 22.7).
 * - Reuses the Stage 1 {@link CalcButton} accessibility pattern (native
 *   `<button>`, visible label + matching `aria-label`, inherited focus/pressed
 *   state). The accessible name communicates both the current mode and that
 *   activating switches it (e.g. "Angle mode: radians. Activate to switch to
 *   degrees."). Uses the `action` variant.
 */
export function AngleModeToggle({ angleMode, onToggle }: AngleModeToggleProps) {
  const isRadians = angleMode === "radians";
  const label = isRadians ? "RAD" : "DEG";
  const otherMode = isRadians ? "degrees" : "radians";
  const ariaLabel = `Angle mode: ${angleMode}. Activate to switch to ${otherMode}.`;

  return (
    <CalcButton
      label={label}
      ariaLabel={ariaLabel}
      onActivate={onToggle}
      variant="action"
      className="angle-mode-toggle"
    />
  );
}

export default AngleModeToggle;
