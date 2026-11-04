/**
 * Pure state management for the calculator's Memory_Register.
 *
 * This reducer owns ONLY the single memory register value. It never evaluates an
 * Expression — M+ / M- aggregate values the Backend_Service has ALREADY computed
 * (the string currently shown in the Result_Display) into the register, which the
 * design classifies as local aggregation of backend truth rather than expression
 * evaluation (permitted client-side per the memory decision note; Requirement 24.7
 * is not violated because no scientific function/power/root/log/conversion is
 * performed here).
 *
 * To preserve the full decimal value with Decimal_Precision (Requirements 20.2,
 * 20.3) the aggregation is performed on decimal STRINGS via the arbitrary-precision
 * helpers below. JavaScript `number`/`float` is NEVER used for arithmetic or the
 * zero-check — doing so would silently lose precision for values like
 * `0.1 + 0.2` or long non-terminating backend results.
 *
 * The register is held as a decimal string, initialized `"0"` (Requirement 20.1).
 * The Memory_Indicator is DERIVED state: it is shown iff the register is non-zero
 * (Requirements 20.6, 20.7) — exposed here via the {@link isMemoryActive} selector.
 *
 * MR (recall) inserts the register value into the Expression. The actual insertion
 * and the 256-character length guard (Requirements 20.4, 20.9) live in the
 * Calculator container (task 35.3) operating on the `calculatorReducer`, because the
 * Expression is owned there — not by this reducer. This file exposes the register
 * value (via {@link memoryValue}) and the helpers the container needs; the
 * `MEM_RECALL` action is defined for symmetry but never mutates memory state.
 *
 * Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.9
 */

import type { MemoryState } from '../api/types';

/* -------------------------------------------------------------------------- */
/* Arbitrary-precision decimal-string helpers                                 */
/* -------------------------------------------------------------------------- */

/**
 * Matches a plain decimal string: an optional leading `-`, one or more integer
 * digits, and an optional single fractional part. Scientific notation is NOT
 * accepted — the Backend_Service returns plain decimal strings only (e.g. `"0.3"`,
 * `"-9"`, `"1024"`, `"0.3333333333"`).
 */
const DECIMAL_PATTERN = /^-?\d+(\.\d+)?$/;

/**
 * Validates that a candidate Result_Display value is a storable numeric result
 * (Requirement 20.8). Returns `true` only for a non-null, plain decimal string
 * (optional sign, digits, optional single fractional part). A regex is used rather
 * than `parseFloat`/`Number` so no float ever enters the validation path.
 */
export function isNumericResult(result: string | null): boolean {
  return result !== null && DECIMAL_PATTERN.test(result);
}

/**
 * Splits a validated decimal string into its sign and its zero-padded integer and
 * fraction magnitude parts. Assumes the input already matches {@link DECIMAL_PATTERN}.
 */
function decompose(value: string): {
  negative: boolean;
  intPart: string;
  fracPart: string;
} {
  const negative = value.startsWith('-');
  const unsigned = negative ? value.slice(1) : value;
  const dot = unsigned.indexOf('.');
  if (dot === -1) {
    return { negative, intPart: unsigned, fracPart: '' };
  }
  return {
    negative,
    intPart: unsigned.slice(0, dot),
    fracPart: unsigned.slice(dot + 1),
  };
}

/**
 * Produces a canonical decimal string: no superfluous leading integer zeros, no
 * trailing fractional zeros, and a single canonical `"0"` for zero (never `"-0"`).
 */
function normalize(negative: boolean, intPart: string, fracPart: string): string {
  let int = intPart.replace(/^0+/, '');
  if (int === '') {
    int = '0';
  }
  const frac = fracPart.replace(/0+$/, '');
  const magnitude = frac === '' ? int : `${int}.${frac}`;
  if (int === '0' && frac === '') {
    // Zero is always canonical and unsigned.
    return '0';
  }
  return negative ? `-${magnitude}` : magnitude;
}

/**
 * Adds two unsigned magnitude strings (integer/fraction pairs), returning the
 * normalized unsigned sum. Operates digit-by-digit so precision is never bounded by
 * the IEEE-754 double range.
 */
function addMagnitudes(
  aInt: string,
  aFrac: string,
  bInt: string,
  bFrac: string,
): { intPart: string; fracPart: string } {
  const fracLen = Math.max(aFrac.length, bFrac.length);
  const af = aFrac.padEnd(fracLen, '0');
  const bf = bFrac.padEnd(fracLen, '0');

  const intLen = Math.max(aInt.length, bInt.length);
  const ai = aInt.padStart(intLen, '0');
  const bi = bInt.padStart(intLen, '0');

  const aDigits = `${ai}${af}`;
  const bDigits = `${bi}${bf}`;

  let carry = 0;
  let sum = '';
  for (let i = aDigits.length - 1; i >= 0; i -= 1) {
    const d = Number(aDigits[i]) + Number(bDigits[i]) + carry;
    sum = String(d % 10) + sum;
    carry = d >= 10 ? 1 : 0;
  }
  if (carry > 0) {
    sum = '1' + sum;
  }

  const totalFracLen = fracLen;
  const fracPart = sum.slice(sum.length - totalFracLen);
  const intPart = sum.slice(0, sum.length - totalFracLen);
  return { intPart: intPart === '' ? '0' : intPart, fracPart };
}

/**
 * Compares two unsigned magnitudes. Returns `1` if a > b, `-1` if a < b, `0` if
 * equal. Operates on padded digit strings, never on floats.
 */
function compareMagnitudes(
  aInt: string,
  aFrac: string,
  bInt: string,
  bFrac: string,
): number {
  const fracLen = Math.max(aFrac.length, bFrac.length);
  const af = aFrac.padEnd(fracLen, '0');
  const bf = bFrac.padEnd(fracLen, '0');
  const intLen = Math.max(aInt.length, bInt.length);
  const ai = aInt.padStart(intLen, '0');
  const bi = bInt.padStart(intLen, '0');
  const a = `${ai}${af}`;
  const b = `${bi}${bf}`;
  if (a === b) {
    return 0;
  }
  return a > b ? 1 : -1;
}

/**
 * Subtracts unsigned magnitude `b` from unsigned magnitude `a`, requiring a >= b.
 * Returns the normalized unsigned difference as integer/fraction parts.
 */
function subMagnitudes(
  aInt: string,
  aFrac: string,
  bInt: string,
  bFrac: string,
): { intPart: string; fracPart: string } {
  const fracLen = Math.max(aFrac.length, bFrac.length);
  const af = aFrac.padEnd(fracLen, '0');
  const bf = bFrac.padEnd(fracLen, '0');
  const intLen = Math.max(aInt.length, bInt.length);
  const ai = aInt.padStart(intLen, '0');
  const bi = bInt.padStart(intLen, '0');

  const aDigits = `${ai}${af}`;
  const bDigits = `${bi}${bf}`;

  let borrow = 0;
  let diff = '';
  for (let i = aDigits.length - 1; i >= 0; i -= 1) {
    let d = Number(aDigits[i]) - Number(bDigits[i]) - borrow;
    if (d < 0) {
      d += 10;
      borrow = 1;
    } else {
      borrow = 0;
    }
    diff = String(d) + diff;
  }

  const fracPart = diff.slice(diff.length - fracLen);
  const intPart = diff.slice(0, diff.length - fracLen);
  return { intPart: intPart === '' ? '0' : intPart, fracPart };
}

/**
 * Adds two plain decimal strings exactly, returning the normalized decimal-string
 * sum. Signs are handled explicitly by delegating to magnitude add/subtract so no
 * float is ever involved (Requirement 20.2). Inputs must be plain decimal strings.
 */
export function add(a: string, b: string): string {
  const x = decompose(a);
  const y = decompose(b);

  if (x.negative === y.negative) {
    // Same sign: add magnitudes, keep the shared sign.
    const { intPart, fracPart } = addMagnitudes(
      x.intPart,
      x.fracPart,
      y.intPart,
      y.fracPart,
    );
    return normalize(x.negative, intPart, fracPart);
  }

  // Differing signs: subtract the smaller magnitude from the larger.
  const cmp = compareMagnitudes(x.intPart, x.fracPart, y.intPart, y.fracPart);
  if (cmp === 0) {
    return '0';
  }
  if (cmp > 0) {
    const { intPart, fracPart } = subMagnitudes(
      x.intPart,
      x.fracPart,
      y.intPart,
      y.fracPart,
    );
    return normalize(x.negative, intPart, fracPart);
  }
  const { intPart, fracPart } = subMagnitudes(
    y.intPart,
    y.fracPart,
    x.intPart,
    x.fracPart,
  );
  return normalize(y.negative, intPart, fracPart);
}

/**
 * Subtracts plain decimal string `b` from plain decimal string `a` exactly,
 * returning the normalized decimal-string difference (Requirement 20.3). Implemented
 * as `a + (-b)` by flipping the sign of `b`, so the exact signed-add path above is
 * reused. Inputs must be plain decimal strings.
 */
export function subtract(a: string, b: string): string {
  if (b === '0') {
    return normalize(
      decompose(a).negative,
      decompose(a).intPart,
      decompose(a).fracPart,
    );
  }
  const negatedB = b.startsWith('-') ? b.slice(1) : `-${b}`;
  return add(a, negatedB);
}

/**
 * Exact zero-check for a plain decimal string. Delegates to {@link normalize} so any
 * representation of zero (`"0"`, `"-0"`, `"0.0"`, `"0.00"`) collapses to canonical
 * `"0"`. Never uses `parseFloat`/`Number` (Requirements 20.6, 20.7).
 */
export function isZero(value: string): boolean {
  const { negative, intPart, fracPart } = decompose(value);
  return normalize(negative, intPart, fracPart) === '0';
}

/* -------------------------------------------------------------------------- */
/* Reducer state, actions, and transitions                                    */
/* -------------------------------------------------------------------------- */

/**
 * The initial Memory_Register state: the register holds canonical zero before any
 * memory operation (Requirement 20.1).
 */
export const initialState: MemoryState = {
  value: '0',
};

/**
 * The set of actions the Memory_Register can process.
 *
 * String literal `type` discriminants form a discriminated union so the reducer can
 * exhaustively narrow each case with no use of `any`.
 *
 * `MEM_ADD`/`MEM_SUB` carry the current Result_Display value as a nullable string:
 * `null` (or a non-numeric string) represents "no numeric result available", which
 * the reducer treats as a guarded no-op (Requirement 20.8); the caller surfaces the
 * error indication.
 */
export type MemoryAction =
  /** Add the current Result_Display value to the register (Requirements 20.2, 20.8). */
  | { type: 'MEM_ADD'; result: string | null }
  /** Subtract the current Result_Display value from the register (Requirements 20.3, 20.8). */
  | { type: 'MEM_SUB'; result: string | null }
  /**
   * Recall the register value into the Expression. This never mutates memory state;
   * the insertion and 256-character guard (Requirements 20.4, 20.9) are wired in the
   * Calculator container (task 35.3) against the `calculatorReducer`. Defined here
   * for action-set symmetry only.
   */
  | { type: 'MEM_RECALL' }
  /** Zero the register (Requirement 20.5). */
  | { type: 'MEM_CLEAR' };

/**
 * Compile-time exhaustiveness guard. If a new {@link MemoryAction} variant is added
 * without a matching `case`, the `never`-typed parameter fails to type-check,
 * flagging the missing branch. At runtime an unhandled action leaves state unchanged.
 */
function assertNever(_action: never, state: MemoryState): MemoryState {
  return state;
}

/**
 * Pure reducer computing the next {@link MemoryState} from the current state and an
 * action. It performs no side effects and no float arithmetic — all aggregation uses
 * the exact decimal-string {@link add}/{@link subtract} helpers (Requirements 20.2,
 * 20.3).
 */
export function memoryReducer(
  state: MemoryState,
  action: MemoryAction,
): MemoryState {
  switch (action.type) {
    case 'MEM_ADD':
      // Guard: with no numeric Result_Display value, leave the register unchanged
      // (Requirement 20.8). The container presents the error indication.
      if (!isNumericResult(action.result)) {
        return state;
      }
      return {
        value: add(state.value, action.result as string),
      };

    case 'MEM_SUB':
      // Guard mirrors MEM_ADD (Requirement 20.8).
      if (!isNumericResult(action.result)) {
        return state;
      }
      return {
        value: subtract(state.value, action.result as string),
      };

    case 'MEM_RECALL':
      // Recall does not change memory state; the Expression insertion and the
      // 256-char guard live in the Calculator container (Requirements 20.4, 20.9).
      return state;

    case 'MEM_CLEAR':
      // Zero the register (Requirement 20.5).
      return { value: '0' };

    default: {
      // Exhaustiveness guard: adding a new action type without a matching case fails
      // to type-check. Unknown actions leave state unchanged.
      return assertNever(action, state);
    }
  }
}

/* -------------------------------------------------------------------------- */
/* Derived-state selectors                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Exposes the current register value for MR (recall). The container reads this,
 * applies the 256-character length guard, and inserts it into the Expression via the
 * `calculatorReducer` (Requirements 20.4, 20.9).
 */
export function memoryValue(state: MemoryState): string {
  return state.value;
}

/**
 * Derived Memory_Indicator state: `true` iff the register is non-zero (Requirements
 * 20.6, 20.7). Uses the exact decimal-string {@link isZero} check rather than
 * `parseFloat`, so a register like `"0.0000000001"` is correctly reported active.
 */
export function isMemoryActive(state: MemoryState): boolean {
  return !isZero(state.value);
}
