import "./CalcButton.css";

/**
 * Semantic grouping for a calculator control, used to hook variant-specific
 * styling (e.g., color-coding operators vs. digits). Styling itself is the
 * responsibility of the theme task; this component only exposes the class hook.
 */
export type CalcButtonVariant = "digit" | "operator" | "action";

/**
 * Props for {@link CalcButton}.
 *
 * The component renders a native `<button>`, so keyboard operability and the
 * implicit `role="button"` are inherent (Requirement 12.2 — no explicit role is
 * needed on a native button). Focus is never suppressed.
 */
export interface CalcButtonProps {
  /**
   * Visible text identifying the button's function, e.g. `"7"`, `"+"`, `"="`.
   * Rendered inside the button so every control carries a visible label
   * (Requirement 11.6).
   */
  label: string;
  /**
   * Accessible label describing the button's function in words (e.g. `"plus"`,
   * `"divide"`, `"equals"`, `"clear"`) rather than only the symbol. It must
   * correspond to the visible function (Requirement 12.1). When omitted, it
   * falls back to {@link CalcButtonProps.label} so the accessible name always
   * matches the visible label.
   */
  ariaLabel?: string;
  /** Invoked when the button is activated by click, touch, or keyboard. */
  onActivate: () => void;
  /** Optional additional class names appended to the button's class list. */
  className?: string;
  /** Semantic grouping used as a styling hook. Defaults to `"digit"`. */
  variant?: CalcButtonVariant;
}

/**
 * A single calculator key rendered as a native `<button>`.
 *
 * - Shows a visible label identifying its function (Requirement 11.6).
 * - Exposes an `aria-label` matching that function, describing it in words
 *   (Requirement 12.1); as a native button its `role="button"` is implicit
 *   (Requirement 12.2).
 * - Indicates its pressed/active state visually. The active-state indication is
 *   driven by CSS `:active` / `:focus-visible` hooks in `CalcButton.css`
 *   (Requirement 11.5); focus is left intact for keyboard operation.
 */
export function CalcButton({
  label,
  ariaLabel,
  onActivate,
  className,
  variant = "digit",
}: CalcButtonProps) {
  const classes = ["calc-button", `calc-button--${variant}`];
  if (className) {
    classes.push(className);
  }

  return (
    <button
      type="button"
      className={classes.join(" ")}
      aria-label={ariaLabel ?? label}
      onClick={onActivate}
    >
      {label}
    </button>
  );
}

export default CalcButton;
