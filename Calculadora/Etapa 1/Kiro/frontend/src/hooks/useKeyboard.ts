/**
 * Global keyboard support for the calculator (Requirements 10, 23).
 *
 * This hook attaches a single `keydown` listener to `window` and maps physical
 * keys to calculator actions. It is deliberately decoupled from the reducer: rather
 * than dispatching directly, it invokes a set of caller-supplied callbacks so the
 * `Calculator` container can wire keyboard input to the same reducer actions used by
 * the on-screen keypad (Task 12.4). This keeps the hook a pure input-mapping layer
 * and preserves the separation of concerns (Requirement 14.1).
 *
 * Stage 1 key mapping (unchanged — Requirement 23.5 preserves every Stage 1 binding):
 * - digits `0`-`9`, operators `+ - * /`, decimal point `.`, and parentheses `( )`
 *   append that character to the Expression (Requirements 10.1, 10.2, 10.3).
 * - `Enter` or `=` submit the current Expression for evaluation (Requirement 10.4).
 * - `Backspace` deletes the most recent character; the reducer no-ops when the
 *   Expression is empty (Requirements 10.5, 10.6).
 * - `Escape` resets the Expression and clears the Result_Display (Requirement 10.7).
 * - any other/unmapped key is a no-op: the Expression and Result_Display are left
 *   unchanged and the event is not prevented (Requirement 10.8).
 *
 * Stage 2 scientific additions (purely additive over the Stage 1 bindings):
 * - `^` appends the exponentiation operator (Requirement 23.1).
 * - the constant keys `p` and `e` append the tokens `pi` and `e` respectively
 *   (Requirement 23.2).
 * - a key-sequence recognizer buffers letter keys and, when the buffer forms a
 *   complete function name (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `ln`,
 *   `log10`, `sqrt`, `root`), appends that function's opening token (e.g. `sin(`)
 *   (Requirement 23.3). The buffer is discarded — leaving the Expression and
 *   Result_Display unchanged — when a 1000 ms inter-key timeout elapses, when a
 *   key arrives that cannot continue any function name, or when a non-letter key
 *   is processed (Requirements 23.4, 23.6). A single unmapped letter that is
 *   neither a constant binding nor the start of a function name is therefore a
 *   no-op, preserving Requirement 10.8.
 *
 * Modifier combinations (Ctrl / Meta / Alt held) are never treated as calculator
 * input, so browser and OS shortcuts (copy, paste, reload, etc.) keep working.
 *
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8,
 * 23.1, 23.2, 23.3, 23.4, 23.5, 23.6
 */

import { useEffect, useRef } from 'react';

/**
 * Callbacks the hook invokes in response to mapped keys. The consumer supplies
 * these (typically thin wrappers over reducer dispatches) so the hook itself stays
 * free of state and arithmetic concerns.
 */
export interface KeyboardCallbacks {
  /**
   * Append a single character to the Expression. Called for digits `0`-`9`,
   * operators `+ - * /`, the decimal point `.`, parentheses `( )`, and the
   * exponentiation operator `^` (Requirements 10.1, 10.2, 10.3, 23.1). `char`
   * is always exactly one character.
   */
  onAppendChar: (char: string) => void;
  /**
   * Append a multi-character token to the Expression. Called for the constant
   * tokens `pi`/`e` and function openers such as `sin(` (Requirements 23.2,
   * 23.3). Optional: when omitted the hook falls back to calling
   * {@link onAppendChar} once per character of the token, so Stage 1 callers that
   * only provide `onAppendChar` keep working unchanged (Requirement 23.5).
   */
  onAppendToken?: (token: string) => void;
  /** Submit the current Expression for evaluation (`Enter` / `=`, Requirement 10.4). */
  onSubmit: () => void;
  /**
   * Delete the most recently entered character (`Backspace`, Requirement 10.5).
   * The consumer/reducer is expected to no-op when the Expression is empty
   * (Requirement 10.6).
   */
  onBackspace: () => void;
  /** Reset the Expression and clear the Result_Display (`Escape`, Requirement 10.7). */
  onReset: () => void;
}

/**
 * The set of single characters that are appended verbatim to the Expression when
 * their corresponding key is pressed (Requirements 10.1, 10.2, 10.3, 23.1).
 * `^` is included so the exponentiation operator is typable (Requirement 23.1).
 */
const APPENDABLE_CHARS: ReadonlySet<string> = new Set([
  '0',
  '1',
  '2',
  '3',
  '4',
  '5',
  '6',
  '7',
  '8',
  '9',
  '+',
  '-',
  '*',
  '/',
  '.',
  '(',
  ')',
  '^',
]);

/**
 * The function names recognized by the key-sequence buffer. On a full match the
 * hook appends `<name>(` (Requirement 23.3). None of these names is a prefix of
 * another (the inverse-trig names extend the single letter `a`, not a shorter
 * function name), so a complete match can be emitted immediately without waiting
 * for a possible longer name.
 */
const FUNCTION_NAMES: readonly string[] = [
  'sin',
  'cos',
  'tan',
  'asin',
  'acos',
  'atan',
  'ln',
  'log10',
  'sqrt',
  'root',
];

/**
 * Single-letter constant bindings mapping a key to the token it appends
 * (Requirement 23.2). `p` → `pi`, `e` → `e`. Neither letter begins any function
 * name (functions start with s, c, t, a, l, r), so handling them as immediate
 * constant tokens is unambiguous and never interferes with the function-name
 * recognizer.
 */
const CONSTANT_KEYS: Readonly<Record<string, string>> = {
  p: 'pi',
  e: 'e',
};

/** Inter-key timeout for the function-name recognizer, in milliseconds (Requirement 23.6). */
const SEQUENCE_TIMEOUT_MS = 1000;

/** `true` when `buffer` is a (possibly partial) prefix of some known function name. */
function isFunctionPrefix(buffer: string): boolean {
  return FUNCTION_NAMES.some((name) => name.startsWith(buffer));
}

/**
 * Attach a global `keydown` listener that maps calculator keys to the supplied
 * {@link KeyboardCallbacks}. The listener is registered once on mount and removed on
 * unmount; the latest callbacks are read through a ref so the effect never has to
 * re-subscribe when the caller passes fresh callback identities on each render.
 *
 * @param callbacks Actions to invoke for mapped keys.
 */
export function useKeyboard(callbacks: KeyboardCallbacks): void {
  // Keep the newest callbacks in a ref so the keydown handler always calls the
  // current versions without tearing down and re-adding the window listener on
  // every render (callback identities typically change each render).
  const callbacksRef = useRef<KeyboardCallbacks>(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    // The in-progress function-name buffer and its pending inter-key timeout
    // (Requirements 23.3, 23.6). Both live in the effect closure so they are
    // created once per mount and torn down on unmount with the listener.
    let sequenceBuffer = '';
    let sequenceTimer: number | null = null;

    // Append a multi-character token, preferring `onAppendToken` and falling back
    // to per-character `onAppendChar` so Stage 1 callers keep working (Requirement
    // 23.5).
    const appendToken = (token: string): void => {
      const current = callbacksRef.current;
      if (current.onAppendToken) {
        current.onAppendToken(token);
      } else {
        for (const ch of token) {
          current.onAppendChar(ch);
        }
      }
    };

    // Discard any pending function-name buffer and cancel its timeout. Leaves the
    // Expression and Result_Display untouched (Requirements 23.4, 23.6).
    const clearSequence = (): void => {
      sequenceBuffer = '';
      if (sequenceTimer !== null) {
        window.clearTimeout(sequenceTimer);
        sequenceTimer = null;
      }
    };

    // (Re)arm the inter-key timeout: if no further letter arrives within
    // SEQUENCE_TIMEOUT_MS the partial buffer is discarded (Requirement 23.6).
    const armSequenceTimer = (): void => {
      if (sequenceTimer !== null) {
        window.clearTimeout(sequenceTimer);
      }
      sequenceTimer = window.setTimeout(() => {
        sequenceBuffer = '';
        sequenceTimer = null;
      }, SEQUENCE_TIMEOUT_MS);
    };

    // Handle a single ASCII-letter key through the constant/function recognizer
    // (Requirements 23.2, 23.3, 23.4, 23.6).
    const handleLetter = (key: string): void => {
      // Constants take precedence and append immediately as a whole token. `p`
      // and `e` do not begin any function name, so this is unambiguous
      // (Requirement 23.2).
      if (key in CONSTANT_KEYS) {
        clearSequence();
        appendToken(CONSTANT_KEYS[key]);
        return;
      }

      const candidate = sequenceBuffer + key;

      // The key cannot continue (or begin) any function name: discard the buffer
      // and treat it as a no-op, leaving the Expression unchanged (Requirements
      // 23.4, 10.8).
      if (!isFunctionPrefix(candidate)) {
        clearSequence();
        return;
      }

      // The candidate is a complete function name: append `<name>(` and reset.
      // No known name is a prefix of another, so a full match is final
      // (Requirement 23.3).
      if (FUNCTION_NAMES.includes(candidate)) {
        clearSequence();
        appendToken(`${candidate}(`);
        return;
      }

      // Still a partial prefix: buffer it and (re)start the inter-key timeout so a
      // pause longer than SEQUENCE_TIMEOUT_MS discards it (Requirement 23.6).
      sequenceBuffer = candidate;
      armSequenceTimer();
    };

    const handleKeyDown = (event: KeyboardEvent): void => {
      // Let browser/OS shortcuts pass through: never treat a chord that holds a
      // Ctrl/Meta/Alt modifier as calculator input (Requirement 10.8 no-op). A
      // pending letter buffer is left intact — a modifier chord is not a
      // calculator keystroke at all.
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }

      const { key } = event;
      const current = callbacksRef.current;

      // ASCII-letter keys feed the constant/function recognizer rather than the
      // single-character append path (Requirements 23.2, 23.3). preventDefault is
      // applied so a recognized constant/function does not also type into the page;
      // an unrecognized letter is a silent no-op that still discards the buffer.
      if (key.length === 1 && /^[a-z]$/.test(key)) {
        event.preventDefault();
        handleLetter(key);
        return;
      }

      // From here on the key is a non-letter: any in-progress function-name
      // sequence is abandoned and discarded before the key is handled normally
      // (Requirement 23.6 — a non-continuing key discards the buffer).
      clearSequence();

      // Mapped single-character keys → append (Requirements 10.1, 10.2, 10.3, 23.1).
      if (key.length === 1 && APPENDABLE_CHARS.has(key)) {
        event.preventDefault();
        current.onAppendChar(key);
        return;
      }

      switch (key) {
        // `Enter` and `=` both submit the current Expression (Requirement 10.4).
        // `=` is length-1 but intentionally excluded from APPENDABLE_CHARS so it
        // maps to submit rather than being appended.
        case 'Enter':
        case '=':
          event.preventDefault();
          current.onSubmit();
          return;

        // Delete the last character; preventDefault stops Backspace from
        // triggering browser back-navigation (Requirements 10.5, 10.6).
        case 'Backspace':
          event.preventDefault();
          current.onBackspace();
          return;

        // Reset the Expression and clear the Result_Display (Requirement 10.7).
        case 'Escape':
          event.preventDefault();
          current.onReset();
          return;

        // Any other/unmapped key is a no-op: do not preventDefault and do not
        // change state (Requirement 10.8).
        default:
          return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      // Clean up a pending inter-key timeout so it never fires after unmount.
      if (sequenceTimer !== null) {
        window.clearTimeout(sequenceTimer);
        sequenceTimer = null;
      }
    };
    // Empty deps: subscribe once; latest callbacks are read via callbacksRef.
  }, []);
}
