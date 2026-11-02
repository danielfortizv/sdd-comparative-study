import { CalcButton } from "./CalcButton";
import "./RpnKeypad.css";

/**
 * Props for {@link RpnKeypad}.
 *
 * The RPN keypad is presentational: it renders the on-screen controls used in
 * RPN_Mode and routes activations to the callbacks the Calculator container
 * supplies. It holds no state and computes no arithmetic (Requirements 14.1,
 * 39.9). Every control drives the SAME reducer action / backend flow its
 * physical-keyboard counterpart drives, so keypad and keyboard produce
 * identical RPN state changes (Requirement 39.8).
 */
export interface RpnKeypadProps {
  /**
   * Append a single character to the in-progress operand entry. Called for the
   * digits `0`-`9` and the decimal point `.` (Requirement 39.8). The container
   * wires this to the `APPEND_OPERAND_CHAR` reducer action.
   */
  onOperandChar: (char: string) => void;
  /**
   * Enter_Control: push the in-progress operand entry onto the stack
   * (Requirements 39.4, 40.2). The container wires this to the `PUSH` action —
   * the identical action the physical `Enter` key drives (Requirement 39.8).
   */
  onPush: () => void;
  /**
   * Operator activation: drive the "build infix → submit → SET_STACK on success"
   * backend flow for the binary operators `+ - * /` and `^` (Requirements 39.5,
   * 40.3). The container wires this to the same handler the operator keyboard
   * keys drive (Requirement 39.8).
   */
  onOperator: (operator: string) => void;
  /** Reset the RPN operand entry, stack, and error (Requirement 39.2 reset path). */
  onReset: () => void;
}

/** Digit controls, ordered 7-8-9 / 4-5-6 / 1-2-3 to match the Stage 1 keypad (Requirement 8.2). */
const DIGIT_KEYS: readonly { label: string; ariaLabel: string; area: string }[] = [
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

/** Binary operator controls (Requirement 39.5); grouped in a dedicated column (Requirement 8.3). */
const OPERATOR_KEYS: readonly { label: string; ariaLabel: string; area: string }[] = [
  { label: "/", ariaLabel: "divide", area: "kdiv" },
  { label: "*", ariaLabel: "multiply", area: "kmul" },
  { label: "-", ariaLabel: "minus", area: "ksub" },
  { label: "+", ariaLabel: "plus", area: "kadd" },
  { label: "^", ariaLabel: "power", area: "kpow" },
];

/**
 * The on-screen keypad for RPN_Mode.
 *
 * Mirrors the Stage 1 keypad layout (digits 7-8-9 / 4-5-6 / 1-2-3 with `0` and
 * `.` below, operators in a dedicated region) so the two modes feel consistent,
 * but routes activations through the RPN reducer / backend flow:
 * - digits and `.` append to the in-progress operand entry (Requirement 39.8);
 * - the `Enter` control pushes that operand onto the stack (Requirements 39.4,
 *   40.2);
 * - the operator controls drive the "build infix → submit → SET_STACK on
 *   success" backend flow (Requirements 39.5, 40.3).
 *
 * These are exactly the same actions the physical keyboard drives in RPN_Mode,
 * satisfying input parity (Requirement 39.8).
 */
export function RpnKeypad({ onOperandChar, onPush, onOperator, onReset }: RpnKeypadProps) {
  return (
    <div className="rpn-keypad" role="group" aria-label="RPN keypad">
      {DIGIT_KEYS.map((key) => (
        <CalcButton
          key={key.area}
          label={key.label}
          ariaLabel={key.ariaLabel}
          variant="digit"
          className={`rpn-keypad__key rpn-keypad__key--${key.area}`}
          onActivate={() => onOperandChar(key.label)}
        />
      ))}

      <CalcButton
        label="0"
        ariaLabel="zero"
        variant="digit"
        className="rpn-keypad__key rpn-keypad__key--k0"
        onActivate={() => onOperandChar("0")}
      />

      <CalcButton
        label="."
        ariaLabel="decimal point"
        variant="digit"
        className="rpn-keypad__key rpn-keypad__key--kdot"
        onActivate={() => onOperandChar(".")}
      />

      {OPERATOR_KEYS.map((key) => (
        <CalcButton
          key={key.area}
          label={key.label}
          ariaLabel={key.ariaLabel}
          variant="operator"
          className={`rpn-keypad__key rpn-keypad__key--${key.area}`}
          onActivate={() => onOperator(key.label)}
        />
      ))}

      <CalcButton
        label="C"
        ariaLabel="clear"
        variant="action"
        className="rpn-keypad__key rpn-keypad__key--kclear"
        onActivate={onReset}
      />

      <CalcButton
        label="Enter"
        ariaLabel="enter, push operand onto the stack"
        variant="action"
        className="rpn-keypad__key rpn-keypad__key--kenter"
        onActivate={onPush}
      />
    </div>
  );
}

export default RpnKeypad;
