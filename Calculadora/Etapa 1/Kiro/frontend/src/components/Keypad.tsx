import { CalcButton } from "./CalcButton";
import "./Keypad.css";

/**
 * Props for {@link Keypad}.
 *
 * The Keypad is presentational: it renders every calculator control and routes
 * activations to the callbacks the Calculator container supplies. It holds no
 * state and computes no arithmetic (Requirement 14.1).
 */
export interface KeypadProps {
  /**
   * Called with the character a control contributes to the expression when a
   * digit (`0`-`9`), the decimal point (`.`), an operator (`+ - * /`), or a
   * parenthesis (`( )`) is activated (Requirements 8.1, 10.1-10.3).
   */
  onInput: (char: string) => void;
  /** Called when the evaluate control (`=`) is activated (Requirement 8.1). */
  onEvaluate: () => void;
  /** Called when the reset control (`C`) is activated (Requirement 8.1). */
  onReset: () => void;
}

/**
 * Describes a single control rendered in the keypad grid.
 * `area` maps the control onto a named cell in the CSS Grid template.
 */
interface KeyDef {
  /** Visible label shown inside the button (Requirement 11.6). */
  label: string;
  /** Spoken accessible label describing the control's function (Requirement 12.1). */
  ariaLabel: string;
  /** `grid-area` name assigned to this control in `Keypad.css`. */
  area: string;
}

/**
 * Digit controls 1-9. Rendered in a three-column-by-three-row block ordered
 * 7-8-9 (top), 4-5-6 (middle), 1-2-3 (bottom) via their grid areas
 * (Requirement 8.2).
 */
const DIGIT_KEYS: readonly KeyDef[] = [
  { label: "7", ariaLabel: "seven", area: "k7" },
  { label: "8", ariaLabel: "eight", area: "k8" },
  { label: "9", ariaLabel: "nine", area: "k9" },
  { label: "4", ariaLabel: "four", area: "k4" },
  { label: "5", ariaLabel: "five", area: "k5" },
  { label: "6", ariaLabel: "six", area: "k6" },
  { label: "1", ariaLabel: "one", area: "k1" },
  { label: "2", ariaLabel: "two", area: "k2" },
  { label: "3", ariaLabel: "three", area: "k3" },
];

/** Operator controls, grouped in a dedicated region separate from the digits (Requirement 8.3). */
const OPERATOR_KEYS: readonly KeyDef[] = [
  { label: "/", ariaLabel: "divide", area: "kdiv" },
  { label: "*", ariaLabel: "multiply", area: "kmul" },
  { label: "-", ariaLabel: "minus", area: "ksub" },
  { label: "+", ariaLabel: "plus", area: "kadd" },
];

/** Parenthesis controls (Requirement 8.1). */
const PAREN_KEYS: readonly KeyDef[] = [
  { label: "(", ariaLabel: "open parenthesis", area: "klparen" },
  { label: ")", ariaLabel: "close parenthesis", area: "krparen" },
];

/**
 * The physical-calculator keypad.
 *
 * Lays every control out on a CSS Grid using named `grid-template-areas`
 * (see `Keypad.css`): digits 1-9 form a 3x3 block (7-8-9 / 4-5-6 / 1-2-3), the
 * `0` sits in the row below that block, and the operators occupy their own
 * dedicated column to the right of the digit keypad (Requirements 8.1-8.3).
 * Full contrast/responsive theming is delivered by the styling task (Task 13).
 */
export function Keypad({ onInput, onEvaluate, onReset }: KeypadProps) {
  return (
    <div className="keypad" role="group" aria-label="calculator keypad">
      {DIGIT_KEYS.map((key) => (
        <CalcButton
          key={key.area}
          label={key.label}
          ariaLabel={key.ariaLabel}
          variant="digit"
          className={`keypad__key keypad__key--${key.area}`}
          onActivate={() => onInput(key.label)}
        />
      ))}

      <CalcButton
        label="0"
        ariaLabel="zero"
        variant="digit"
        className="keypad__key keypad__key--k0"
        onActivate={() => onInput("0")}
      />

      <CalcButton
        label="."
        ariaLabel="decimal point"
        variant="digit"
        className="keypad__key keypad__key--kdot"
        onActivate={() => onInput(".")}
      />

      {PAREN_KEYS.map((key) => (
        <CalcButton
          key={key.area}
          label={key.label}
          ariaLabel={key.ariaLabel}
          variant="action"
          className={`keypad__key keypad__key--${key.area}`}
          onActivate={() => onInput(key.label)}
        />
      ))}

      {OPERATOR_KEYS.map((key) => (
        <CalcButton
          key={key.area}
          label={key.label}
          ariaLabel={key.ariaLabel}
          variant="operator"
          className={`keypad__key keypad__key--${key.area}`}
          onActivate={() => onInput(key.label)}
        />
      ))}

      <CalcButton
        label="C"
        ariaLabel="clear"
        variant="action"
        className="keypad__key keypad__key--kclear"
        onActivate={onReset}
      />

      <CalcButton
        label="="
        ariaLabel="equals"
        variant="action"
        className="keypad__key keypad__key--kequals"
        onActivate={onEvaluate}
      />
    </div>
  );
}

export default Keypad;
