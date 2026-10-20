import { useId, useState } from "react";
import type { AngleMode } from "../api/types";
import { CalcButton } from "./CalcButton";
import { AngleModeToggle } from "./AngleModeToggle";
import "./ScientificKeypad.css";

/**
 * Props for {@link ScientificKeypad}.
 *
 * Like the Stage 1 {@link import("./Keypad").Keypad}, the ScientificKeypad is
 * presentational: it renders every scientific control and routes activations to
 * the callbacks the Calculator container (task 35.3) supplies. It computes no
 * arithmetic and owns no app/calculation state (Requirement 14.1). The only
 * local state it holds is the purely-visual `collapsed` flag for its mobile
 * collapse/expand affordance (Requirements 22.2, 22.8).
 */
export interface ScientificKeypadProps {
  /**
   * Appends a token to the current expression. For functions the token is the
   * opener form matching the keyboard/engine grammar (e.g. `"sin("`, `"ln("`,
   * `"sqrt("`, `"root("`); for constants it is `"pi"` / `"e"` (Requirements
   * 19.3, 19.4); for the power operator it is `"^"`. Tokens are emitted
   * deterministically — the same control always contributes the same text
   * (Requirement 19.5).
   */
  onInput: (token: string) => void;
  /** The currently active angle unit, passed through to the hosted toggle. */
  angleMode: AngleMode;
  /** Requests an angle-mode flip; passed through to the hosted toggle (Requirements 22.1, 22.7). */
  onToggleAngleMode: () => void;
  /** Adds the current value to the Memory_Register (M+). */
  onMemoryAdd: () => void;
  /** Subtracts the current value from the Memory_Register (M-). */
  onMemorySubtract: () => void;
  /** Recalls the Memory_Register into the expression (MR). */
  onMemoryRecall: () => void;
  /** Clears the Memory_Register (MC). */
  onMemoryClear: () => void;
}

/**
 * Describes a single token-emitting control rendered in the scientific keypad.
 */
interface SciKeyDef {
  /** Visible label shown inside the button (Requirement 11.6). */
  label: string;
  /** Spoken accessible label describing the control's function (Requirements 12.1, 12.2). */
  ariaLabel: string;
  /** The deterministic token text appended to the expression (Requirement 19.5). */
  token: string;
  /** `grid-area` name assigned to this control in `ScientificKeypad.css`. */
  area: string;
}

/**
 * Trigonometric functions. Each appends its opener form so the engine grammar
 * sees e.g. `sin(` (Requirements 17.1, 19.5).
 */
const TRIG_KEYS: readonly SciKeyDef[] = [
  { label: "sin", ariaLabel: "sine", token: "sin(", area: "sin" },
  { label: "cos", ariaLabel: "cosine", token: "cos(", area: "cos" },
  { label: "tan", ariaLabel: "tangent", token: "tan(", area: "tan" },
];

/**
 * Inverse trigonometric functions. Visible labels use the conventional
 * superscript-inverse notation; accessible labels spell the function out
 * (Requirement 12.1).
 */
const INVERSE_TRIG_KEYS: readonly SciKeyDef[] = [
  { label: "sin⁻¹", ariaLabel: "inverse sine", token: "asin(", area: "asin" },
  { label: "cos⁻¹", ariaLabel: "inverse cosine", token: "acos(", area: "acos" },
  { label: "tan⁻¹", ariaLabel: "inverse tangent", token: "atan(", area: "atan" },
];

/** Logarithm, root, power and constant controls. */
const FUNCTION_KEYS: readonly SciKeyDef[] = [
  { label: "ln", ariaLabel: "natural logarithm", token: "ln(", area: "ln" },
  { label: "log", ariaLabel: "base-10 logarithm", token: "log10(", area: "log10" },
  { label: "√", ariaLabel: "square root", token: "sqrt(", area: "sqrt" },
  { label: "ʸ√x", ariaLabel: "nth root", token: "root(", area: "root" },
  { label: "xʸ", ariaLabel: "power exponent", token: "^", area: "pow" },
  { label: "π", ariaLabel: "pi constant", token: "pi", area: "pi" },
  { label: "e", ariaLabel: "e constant", token: "e", area: "e" },
];

/**
 * Describes a single memory control, wired to its own callback rather than a
 * token (Requirement 22.1 — the keypad renders the memory CONTROLS; the badge
 * indicator lives near the display and is the container's call).
 */
interface MemoryKeyDef {
  label: string;
  ariaLabel: string;
  area: string;
}

const MEMORY_KEYS: readonly MemoryKeyDef[] = [
  { label: "M+", ariaLabel: "memory add", area: "madd" },
  { label: "M-", ariaLabel: "memory subtract", area: "msub" },
  { label: "MR", ariaLabel: "memory recall", area: "mrecall" },
  { label: "MC", ariaLabel: "memory clear", area: "mclear" },
];

/**
 * The scientific-functions keypad.
 *
 * Renders, via the shared {@link CalcButton}, the trig / inverse-trig
 * functions, `ln`/`log10`, `sqrt`/`root`, the power operator, the `pi`/`e`
 * constants, and the M+/M-/MR/MC memory controls (Requirements 17.x, 18.x,
 * 19.3-19.5, 22.1). It also HOSTS the {@link AngleModeToggle}, passing through
 * the `angleMode`/`onToggleAngleMode` props (Requirement 22.1).
 *
 * The panel is collapsible so it can be hidden on narrow viewports (Requirements
 * 22.2, 22.8). A dedicated collapse/expand control carries `aria-expanded`
 * reflecting the current state and `aria-controls` referencing the controls
 * region; when collapsed the region is removed from the accessibility tree and
 * layout via the native `hidden` attribute. The `collapsed` flag is purely
 * visual UI state held locally with `useState` — it is not app/calculation
 * state. The responsive rule that makes the collapse affordance apply only at
 * mobile widths (Requirement 22.2) plus the >=44px touch targets (22.5) and
 * contrast (11.x) are finalized by the styling task (task 36); this component
 * provides the collapse control, `aria-expanded`, and a `.scientific-keypad`
 * class hook.
 */
export function ScientificKeypad({
  onInput,
  angleMode,
  onToggleAngleMode,
  onMemoryAdd,
  onMemorySubtract,
  onMemoryRecall,
  onMemoryClear,
}: ScientificKeypadProps) {
  const [collapsed, setCollapsed] = useState(false);
  // Stable id so the collapse control's `aria-controls` references the region.
  const regionId = useId();

  const memoryHandlers: Record<string, () => void> = {
    madd: onMemoryAdd,
    msub: onMemorySubtract,
    mrecall: onMemoryRecall,
    mclear: onMemoryClear,
  };

  return (
    <div className="scientific-keypad" role="group" aria-label="scientific functions">
      <div className="scientific-keypad__header">
        <AngleModeToggle angleMode={angleMode} onToggle={onToggleAngleMode} />
        {/*
         * Native <button> (not CalcButton) because the collapse affordance must
         * expose `aria-expanded` and `aria-controls`, which the Stage 1
         * CalcButton API does not forward. It still mirrors CalcButton's pattern
         * (native button, visible label + matching aria-label, inherited
         * focus/pressed CSS via the shared `calc-button` class) so focus/pressed
         * states are inherited (Requirements 11.5, 11.6, 12.1, 12.2).
         */}
        <button
          type="button"
          className="calc-button calc-button--action scientific-keypad__collapse"
          aria-label="Scientific functions"
          aria-expanded={!collapsed}
          aria-controls={regionId}
          onClick={() => setCollapsed((prev) => !prev)}
        >
          {collapsed ? "Show ▸" : "Hide ▾"}
        </button>
      </div>

      <div
        id={regionId}
        className="scientific-keypad__controls"
        hidden={collapsed}
      >
        {[...TRIG_KEYS, ...INVERSE_TRIG_KEYS, ...FUNCTION_KEYS].map((key) => (
          <CalcButton
            key={key.area}
            label={key.label}
            ariaLabel={key.ariaLabel}
            variant="action"
            className={`scientific-keypad__key scientific-keypad__key--${key.area}`}
            onActivate={() => onInput(key.token)}
          />
        ))}

        {MEMORY_KEYS.map((key) => (
          <CalcButton
            key={key.area}
            label={key.label}
            ariaLabel={key.ariaLabel}
            variant="action"
            className={`scientific-keypad__key scientific-keypad__key--${key.area}`}
            onActivate={memoryHandlers[key.area]}
          />
        ))}
      </div>
    </div>
  );
}

export default ScientificKeypad;
