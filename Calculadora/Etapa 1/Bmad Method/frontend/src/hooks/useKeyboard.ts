import { useEffect } from 'react';

interface UseKeyboardProps {
  appendToken: (token: string) => void;
  backspace: () => void;
  clearAll: () => void;
  evaluateFinal: () => void;
  disabled: boolean;
}

export function useKeyboard({
  appendToken,
  backspace,
  clearAll,
  evaluateFinal,
  disabled
}: UseKeyboardProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // If calculator is disabled or user is in some other input (none exist in v1, but good practice)
      if (disabled) return;

      const { key } = event;

      // Map physical keys to digits, operations, brackets
      if (/^[0-9]$/.test(key)) {
        event.preventDefault();
        appendToken(key);
      } else if (key === '.') {
        event.preventDefault();
        appendToken('.');
      } else if (key === '+') {
        event.preventDefault();
        appendToken(' + ');
      } else if (key === '-') {
        event.preventDefault();
        appendToken(' - ');
      } else if (key === '*') {
        event.preventDefault();
        appendToken(' * ');
      } else if (key === '/') {
        event.preventDefault();
        appendToken(' / ');
      } else if (key === '(') {
        event.preventDefault();
        appendToken('(');
      } else if (key === ')') {
        event.preventDefault();
        appendToken(')');
      } else if (key === 'Enter' || key === '=') {
        event.preventDefault();
        evaluateFinal();
      } else if (key === 'Backspace') {
        event.preventDefault();
        backspace();
      } else if (key === 'Escape') {
        event.preventDefault();
        clearAll();
      }
    };

    // Bind event globally to window to intercept keys even if click focus is lost
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [appendToken, backspace, clearAll, evaluateFinal, disabled]);
}
