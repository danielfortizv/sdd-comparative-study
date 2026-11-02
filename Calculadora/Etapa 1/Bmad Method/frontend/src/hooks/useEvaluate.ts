import { useState, useEffect, useRef } from 'react';
import { EvaluateResponse, ErrorResponse } from '../types/api';

const API_BASE_URL = 'http://localhost:8000';

export type DisplayState = 'idle' | 'active' | 'preview' | 'evaluated' | 'error';
export type CalculatorMode = 'standard' | 'rpn';

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

  // Dual Mode and Stack States
  const [calcMode, setCalcMode] = useState<CalculatorMode>('standard');
  const [stack, setStack] = useState<string[]>([]);

  // Stage 2 Core States
  const [angleUnit, setAngleUnit] = useState<'radians' | 'degrees'>('radians');
  const [memory, setMemory] = useState('0');
  const [sessionHistory, setSessionHistory] = useState<HistoryItem[]>([]);

  // Use a ref to store active debounce timers
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Toggle calculator mode
  const toggleCalcMode = () => {
    setCalcMode((prev) => (prev === 'standard' ? 'rpn' : 'standard'));
    clearAll();
  };

  // Helper function to check if parentheses are balanced before sending network preview requests
  const isParenthesesBalanced = (expr: string): boolean => {
    let count = 0;
    for (const char of expr) {
      if (char === '(') count++;
      if (char === ')') count--;
      if (count < 0) return false;
    }
    return count === 0;
  };

  // Helper function to execute REST API queries
  const fetchEvaluation = async (
    expr: string, 
    currentStack: string[] = [], 
    format: 'infix' | 'postfix' = 'infix'
  ): Promise<EvaluateResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          expression: expr, 
          angle_unit: angleUnit,
          stack: currentStack,
          expr_format: format
        }),
      });

      if (response.ok) {
        const data: EvaluateResponse = await response.json();
        return data;
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

  // Debounced live calculations for standard mode previews
  useEffect(() => {
    if (calcMode !== 'standard') return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const trimmed = expression.trim();
    if (state === 'evaluated' && trimmed === result) {
      return;
    }
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
    const hasSciStart = /[a-zA-Z]$/.test(trimmed);
    if (!isParenthesesBalanced(trimmed) || endsWithOperator || hasSciStart) {
      setResult('');
      return;
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        const data = await fetchEvaluation(trimmed, [], 'infix');
        setResult(data.result);
        setState('preview');
      } catch (err: unknown) {
        setResult('');
      }
    }, 300);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [expression, angleUnit, calcMode]);

  // Enforces final submission evaluation on `=` or `Enter`
  const evaluateFinal = async () => {
    if (calcMode === 'rpn') {
      // ENTER behavior in RPN: Pushes the active input to the stack
      if (expression) {
        setStack((prev) => [...prev, expression]);
        setResult(expression);
        setExpression('');
        setState('evaluated');
      } else if (stack.length > 0) {
        // If expression is empty, duplicate the top item of the stack
        const top = stack[stack.length - 1];
        setStack((prev) => [...prev, top]);
        setResult(top);
        setState('evaluated');
      }
      return;
    }

    // Standard Infix Mode Final Evaluation
    const trimmed = expression.trim();
    if (!trimmed) return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    setState('active');
    try {
      const data = await fetchEvaluation(trimmed, [], 'infix');
      setHistory(`${trimmed} = ${data.result}`);
      
      // Update local history cache for the drawer
      setSessionHistory((prev) => [{ expression: trimmed, result: data.result }, ...prev]);
      
      setExpression(data.result);
      setResult(data.result);
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
    setStack([]);
    setResult('0');
    setHistory('');
    setState('idle');
    setErrorMessage('');
  };

  // State single character backspace clearing
  const backspace = () => {
    if (state === 'error' || (calcMode === 'standard' && state === 'evaluated')) {
      clearAll();
      return;
    }
    
    if (calcMode === 'rpn' && !expression) {
      // In RPN mode, backspacing when active input is empty drops the top stack element
      setStack((prev) => {
        const next = prev.slice(0, -1);
        const top = next[next.length - 1];
        setResult(top || '0');
        return next;
      });
      return;
    }

    setExpression((prev) => {
      const next = prev.trimEnd();
      const match = next.match(/(asin\(|acos\(|atan\(|sqrt\(|log10\(|sin\(|cos\(|tan\(|ln\(|log\()$/);
      if (match) {
          return next.slice(0, -match[0].length);
      }
      return next.slice(0, -1);
    });
  };

  const appendToken = async (token: string) => {
    if (state === 'error') {
      clearAll();
    }

    const trimmedToken = token.trim();
    
    // Check if token is an operator or scientific function
    const isOperator = /[\+\-\*\/]/.test(trimmedToken) || trimmedToken === '**' || trimmedToken === '^';
    const isFunc = /^[a-zA-Z]/.test(trimmedToken) && trimmedToken !== 'pi' && trimmedToken !== 'e';

    if (calcMode === 'rpn') {
      if (isOperator || isFunc) {
        // Execute postfix operator or function on stack immediately
        const nextStack = expression ? [...stack, expression] : [...stack];
        setExpression('');
        setState('active');
        
        try {
          const mappedOp = trimmedToken === '^' ? '**' : trimmedToken;
          const data = await fetchEvaluation(mappedOp, nextStack, 'postfix');
          setStack(data.stack || []);
          setResult(data.result);
          setState('evaluated');
          
          const historyExpr = `${nextStack.join(' ')} ${mappedOp}`;
          setHistory(`${historyExpr} = ${data.result}`);
          setSessionHistory((prev) => [{ expression: historyExpr, result: data.result }, ...prev]);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : 'Error: Evaluation failed';
          setErrorMessage(msg);
          setResult(msg);
          setState('error');
        }
      } else if (trimmedToken === 'pi' || trimmedToken === 'e') {
        // Constants in RPN are pushed directly onto the stack
        const val = trimmedToken === 'pi' ? '3.141592653589793238462643383' : '2.718281828459045235360287471';
        setStack((prev) => [...prev, val]);
        setResult(val);
        setState('evaluated');
      } else {
        // Standard digit or decimal point appending to active input
        setExpression((prev) => {
          if (state === 'evaluated') {
            return trimmedToken; // start fresh
          }
          return prev + trimmedToken;
        });
      }
      return;
    }

    // Standard Infix mode token appending
    setExpression((prev) => {
      const isOp = /[\+\-\*\/]/.test(token);
      const isWord = /^[a-zA-Z]/.test(token);
      if (state === 'evaluated' && !isOp && !isWord) {
        return token;
      }
      return prev + token;
    });
  };

  // Stage 2 Memory Handlers
  const handleMemoryOperation = async (op: 'add' | 'subtract') => {
    const valueToOperate = state === 'error' ? '0' : (
      calcMode === 'rpn'
        ? (expression || (stack.length > 0 ? stack[stack.length - 1] : '0'))
        : (((state === 'evaluated' || state === 'preview') && result) ? result : (expression || '0'))
    );
    
    const cleanedValue = valueToOperate.replace(/[^\d\.\-eE]/g, '');
    if (!cleanedValue || isNaN(Number(cleanedValue))) return;

    const opSymbol = op === 'add' ? '+' : '-';
    const evaluateExpr = `${memory} ${opSymbol} (${cleanedValue})`;

    try {
      const data = await fetchEvaluation(evaluateExpr, [], 'infix');
      setMemory(data.result);
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
    if (calcMode === 'rpn') {
      // In RPN, recalling memory pushes it directly as a stack item or sets active expression
      setExpression(memory);
      setResult(memory);
      setState('active');
    } else {
      appendToken(memory);
    }
  };

  // Stage 2 Angle Handlers
  const toggleAngleUnit = () => {
    setAngleUnit((prev) => (prev === 'radians' ? 'degrees' : 'radians'));
  };

  // Stage 2 History Handlers
  const loadHistoryExpression = (expr: string) => {
    if (calcMode === 'rpn') {
      // For RPN, parse history expression (which is space-separated postfix) into stack
      const tokens = expr.split(' ');
      setStack(tokens);
      if (tokens.length > 0) {
        setResult(tokens[tokens.length - 1]);
      }
      setState('evaluated');
    } else {
      setExpression(expr);
      setState('active');
    }
  };

  const loadHistoryResult = (res: string) => {
    if (calcMode === 'rpn') {
      setStack([res]);
      setResult(res);
      setState('evaluated');
    } else {
      setExpression(res);
      setState('evaluated');
      setResult(res);
    }
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
    // Dual Mode & Stack
    calcMode,
    toggleCalcMode,
    stack,
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
