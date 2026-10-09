/**
 * Global keyboard support for the calculator (Requirement 10).
 *
 * This hook attaches a single `keydown` listener to `window` and maps physical
 * keys to calculator actions. It is deliberately decoupled from the reducer: rather
 * than dispatching directly, it invokes a set of caller-supplied callbacks so the
 * `Calculator` container can wire keyboard input to the same reducer actions used by
 * the on-screen keypad (Task 12.4). This keeps the hook a pure input-mapping layer
 * and preserves the separation of concerns (Requirement 14.1).
 *
 * Key mapping:
 * - digits `0`-`9`, operators `+ - * /`, decimal point `.`, and parentheses `( )`
 *   append that character to the Expression (Requirements 10.1, 10.2, 10.3).
 * - `Enter` or `=` submit the current Expression for evaluation (Requirement 10.4).
 * - `Backspace` deletes the most recent character; the reducer no-ops when the
 *   Expression is empty (Requirements 10.5, 10.6).
 * - `Escape` resets the Expression and clears the Result_Display (Requirement 10.7).
 * - any other/unmapped key is a no-op: the Expression and Result_Display are left
 *   unchanged and the event is not prevented (Requirement 10.8).
 *
 * Modifier combinations (Ctrl / Meta / Alt held) are never treated as calculator
 * input, so browser and OS shortcuts (copy, paste, reload, etc.) keep working.
 *
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8
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
   * operators `+ - * /`, the decimal point `.`, and parentheses `( )`
   * (Requirements 10.1, 10.2, 10.3). `char` is always exactly one character.
   */
  onAppendChar: (char: string) => void;
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
 * their corresponding key is pressed (Requirements 10.1, 10.2, 10.3).
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
]);

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
    const handleKeyDown = (event: KeyboardEvent): void => {
      // Let browser/OS shortcuts pass through: never treat a chord that holds a
      // Ctrl/Meta/Alt modifier as calculator input (Requirement 10.8 no-op).
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }

      const { key } = event;
      const current = callbacksRef.current;

      // Mapped single-character keys → append (Requirements 10.1, 10.2, 10.3).
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
    };
    // Empty deps: subscribe once; latest callbacks are read via callbacksRef.
  }, []);
}
