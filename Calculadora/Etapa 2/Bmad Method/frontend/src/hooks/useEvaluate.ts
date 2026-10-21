import { useState, useEffect, useRef } from 'react';
import { EvaluateResponse, ErrorResponse } from '../types/api';

const API_BASE_URL = 'http://localhost:8000';

export type DisplayState = 'idle' | 'active' | 'preview' | 'evaluated' | 'error';

export interface HistoryItem {
  expression: string;
  result: string;
}

export function useEvaluate() {
  const [expression, setExpression] = useState('');
  const [result, setResult] = useState('0');
  const [history, setHistory] = useState('');
  const [state, setState] = useState<DisplayState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Stage 2 Core States
  const [angleUnit, setAngleUnit] = useState<'radians' | 'degrees'>('radians');
  const [memory, setMemory] = useState('0');
  const [sessionHistory, setSessionHistory] = useState<HistoryItem[]>([]);

  // Use a ref to store active debounce timers
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        body: JSON.stringify({ expression: expr, angle_unit: angleUnit }),
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
    const hasSciStart = /[a-zA-Z]$/.test(trimmed); // Typing scientific characters shouldn't trigger direct previews yet
    if (!isParenthesesBalanced(trimmed) || endsWithOperator || hasSciStart) {
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
  }, [expression, angleUnit]);

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
      
      // Update local history cache for the drawer (keeps newer calculations at top)
      setSessionHistory((prev) => [{ expression: trimmed, result: finalVal }, ...prev]);
      
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
      
      // If we are deleting a scientific word (like 'sin(', 'cos(', 'tan(', 'asin(', etc.)
      // let's do a smart deletes.
      const match = next.match(/(asin\(|acos\(|atan\(|sqrt\(|log10\(|sin\(|cos\(|tan\(|ln\(|log\()$/);
      if (match) {
          return next.slice(0, -match[0].length);
      }
      return next.slice(0, -1);
    });
  };

  const appendToken = (token: string) => {
    if (state === 'error') {
      // Clear error immediately on new input
      clearAll();
    }
    setExpression((prev) => {
      // If we just evaluated, a new digit or function should start fresh, while an operator should chain
      const isOperator = /[\+\-\*\/]/.test(token);
      const isWord = /^[a-zA-Z]/.test(token);
      if (state === 'evaluated' && !isOperator && !isWord) {
        return token;
      }
      return prev + token;
    });
  };

  // Stage 2 Memory Handlers
  const handleMemoryOperation = async (op: 'add' | 'subtract') => {
    // Current display/result value to accumulate
    const valueToOperate = state === 'error' ? '0' : (result && state !== 'idle' ? result : (expression || '0'));
    
    // Extract only standard float digits
    const cleanedValue = valueToOperate.replace(/[^\d\.\-eE]/g, '');
    if (!cleanedValue || isNaN(Number(cleanedValue))) return;

    const opSymbol = op === 'add' ? '+' : '-';
    const evaluateExpr = `${memory} ${opSymbol} (${cleanedValue})`;

    try {
      const newMemoryVal = await fetchEvaluation(evaluateExpr);
      setMemory(newMemoryVal);
    } catch (err) {
      console.error("Memory high-precision math failed; falling back to JS float arithmetic.", err);
      const m = Number(memory);
      const v = Number(cleanedValue);
      const res = op === 'add' ? m + v : m - v;
      setMemory(String(res));
    }
  };

  const clearMemory = () => setMemory('0');

  const recallMemory = () => {
    appendToken(memory);
  };

  // Stage 2 Angle Handlers
  const toggleAngleUnit = () => {
    setAngleUnit((prev) => (prev === 'radians' ? 'degrees' : 'radians'));
  };

  // Stage 2 History Handlers
  const loadHistoryExpression = (expr: string) => {
    setExpression(expr);
    setState('active');
  };

  const loadHistoryResult = (res: string) => {
    setExpression(res);
    setState('evaluated');
    setResult(res);
  };

  const clearHistory = () => {
    setSessionHistory([]);
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
    // Stage 2 Exports
    angleUnit,
    toggleAngleUnit,
    memory,
    handleMemoryOperation,
    clearMemory,
    recallMemory,
    sessionHistory,
    loadHistoryExpression,
    loadHistoryResult,
    clearHistory,
  };
}
