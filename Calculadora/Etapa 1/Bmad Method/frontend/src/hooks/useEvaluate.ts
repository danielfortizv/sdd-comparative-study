import { useState, useEffect, useRef } from 'react';
import { EvaluateResponse, ErrorResponse } from '../types/api';

const API_BASE_URL = 'http://localhost:8000';

export type DisplayState = 'idle' | 'active' | 'preview' | 'evaluated' | 'error';

export function useEvaluate() {
  const [expression, setExpression] = useState('');
  const [result, setResult] = useState('0');
  const [history, setHistory] = useState('');
  const [state, setState] = useState<DisplayState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Use a ref to store active debounce timers
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Helper function to check if parentheses are balanced before sending network preview requests
  const isParenthesesBalanced = (expr: string): boolean => {
    let count = 0;
    for (const char of expr) {
      if (char === '(') count++;
      if (char === ')') count--;
      if (count < 0) return false; // Closing bracket appears before open
    }
    return count === 0;
  };

  // Helper function to execute REST API queries
  const fetchEvaluation = async (expr: string): Promise<string> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression: expr }),
      });

      if (response.ok) {
        const data: EvaluateResponse = await response.json();
        return data.result;
      } else {
        const data: ErrorResponse = await response.json();
        throw new Error(data.message || 'Error: Evaluation failed');
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        throw err;
      }
      throw new Error('Error: Network connection failed');
    }
  };

  // Debounced live calculations for previews
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const trimmed = expression.trim();
    if (!trimmed) {
      setResult('0');
      setState('idle');
      setErrorMessage('');
      return;
    }

    // Set active typing state
    setState('active');
    setErrorMessage('');

    // Only fetch live preview if brackets are fully balanced and does not end with an operator
    const endsWithOperator = /[\+\-\*\/]$/.test(trimmed);
    if (!isParenthesesBalanced(trimmed) || endsWithOperator) {
      setResult('');
      return;
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        const previewVal = await fetchEvaluation(trimmed);
        setResult(previewVal);
        setState('preview');
      } catch (err: unknown) {
        // Suppress errors during typing previews so it doesn't lock the UI
        setResult('');
      }
    }, 300); // 300ms debounce

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [expression]);

  // Enforces final submission evaluation on `=` or `Enter`
  const evaluateFinal = async () => {
    const trimmed = expression.trim();
    if (!trimmed) return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    setState('active');
    try {
      const finalVal = await fetchEvaluation(trimmed);
      setHistory(`${trimmed} = ${finalVal}`);
      setExpression(finalVal); // Chained calculations: evaluated result becomes starting operand
      setResult(finalVal);
      setState('evaluated');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error: Evaluation failed';
      setErrorMessage(msg);
      setResult(msg);
      setState('error');
    }
  };

  // State utility clearing actions (equivalent to clicking AC)
  const clearAll = () => {
    setExpression('');
    setResult('0');
    setHistory('');
    setState('idle');
    setErrorMessage('');
  };

  // State single character backspace clearing
  const backspace = () => {
    if (state === 'error' || state === 'evaluated') {
      clearAll();
      return;
    }
    setExpression((prev) => {
      const next = prev.trimEnd();
      return next.slice(0, -1);
    });
  };

  const appendToken = (token: string) => {
    if (state === 'error') {
      // Clear error immediately on new input
      clearAll();
    }
    setExpression((prev) => {
      // If we just evaluated, a new digit should start fresh, while an operator should chain
      const isOperator = /[\+\-\*\/]/.test(token);
      if (state === 'evaluated' && !isOperator) {
        return token;
      }
      return prev + token;
    });
  };

  return {
    expression,
    result,
    history,
    state,
    errorMessage,
    appendToken,
    clearAll,
    backspace,
    evaluateFinal,
  };
}
