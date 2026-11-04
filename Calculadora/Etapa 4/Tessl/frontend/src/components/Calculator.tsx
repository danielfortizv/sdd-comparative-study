import { useState, useEffect, useCallback } from 'react';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1/evaluate';

interface ErrorDetail {
  type: string;
  message: string;
}

interface HistoryItem {
  expression: string;
  result: string;
}

// Client-side Infix to Postfix converter for live preview
function getPostfixPreview(infix: string): string {
  if (!infix.trim()) return '';
  try {
    const tokens: string[] = [];
    const pattern = /(\d*\.?\d+)|([a-zA-Z_][a-zA-Z0-9_]*)|([+\-*/()^])|(\s+)/g;
    let match;
    while ((match = pattern.exec(infix)) !== null) {
      const [_, num, word, op] = match;
      if (num) tokens.push(num);
      else if (word) tokens.push(word.toLowerCase());
      else if (op) tokens.push(op);
    }
    
    const output: string[] = [];
    const opStack: string[] = [];
    
    const precedence: Record<string, number> = {
      'sin': 6, 'cos': 6, 'tan': 6, 'asin': 6, 'acos': 6, 'atan': 6, 'ln': 6, 'log': 6, 'sqrt': 6,
      '^': 5, 'u-': 4, 'u+': 4, '*': 3, '/': 3, '+': 2, '-': 2
    };
    
    const preprocessed: string[] = [];
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      if (token === '+' || token === '-') {
        const isUnary = (i === 0) || (['+', '-', '*', '/', '^', '('].includes(tokens[i-1]));
        if (isUnary) {
          preprocessed.push(token === '-' ? 'u-' : 'u+');
        } else {
          preprocessed.push(token);
        }
      } else {
        preprocessed.push(token);
      }
    }
    
    for (const token of preprocessed) {
      if (!isNaN(Number(token)) || token === 'pi' || token === 'e') {
        output.push(token);
      } else if (['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'].includes(token)) {
        opStack.push(token);
      } else if (['+', '-', '*', '/', '^', 'u-', 'u+'].includes(token)) {
        const opPrec = precedence[token] || 0;
        const assoc = token === '^' || token.startsWith('u') ? 'right' : 'left';
        while (opStack.length > 0) {
          const top = opStack[opStack.length - 1];
          if (top === '(') break;
          const topPrec = precedence[top] || 0;
          const isFunc = ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'].includes(top);
          if (isFunc || topPrec > opPrec || (topPrec === opPrec && assoc === 'left')) {
            output.push(opStack.pop()!);
          } else {
            break;
          }
        }
        opStack.push(token);
      } else if (token === '(') {
        opStack.push(token);
      } else if (token === ')') {
        let matched = false;
        while (opStack.length > 0) {
          const top = opStack[opStack.length - 1];
          if (top === '(') {
            opStack.pop();
            matched = true;
            break;
          }
          output.push(opStack.pop()!);
        }
        if (opStack.length > 0 && ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'].includes(opStack[opStack.length - 1])) {
          output.push(opStack.pop()!);
        }
      }
    }
    while (opStack.length > 0) {
      const top = opStack.pop()!;
      if (top !== '(' && top !== ')') {
        output.push(top);
      }
    }
    
    return output.map(t => {
      if (t === 'u-') return '-';
      if (t === 'u+') return '+';
      return t;
    }).join(' ');
  } catch {
    return '';
  }
}

export default function Calculator() {
  // Calculator Mode State (Stage 4)
  const [mode, setMode] = useState<'standard' | 'rpn'>('standard');

  // Calculator Display & Expression State
  const [expression, setExpression] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Stack State for RPN mode (Stage 4)
  const [stack, setStack] = useState<string[]>([]);

  // Extended State Management (Stage 2)
  const [memory, setMemory] = useState<number>(0);
  const [angleUnit, setAngleUnit] = useState<'radians' | 'degrees'>('radians');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(true); // Collapsible panel

  // Core Actions
  const handleClear = useCallback(() => {
    setExpression('');
    setResult('');
    setError(null);
    if (mode === 'rpn') {
      setStack([]);
    }
  }, [mode]);

  const handleBackspace = useCallback(() => {
    setExpression((prev) => prev.slice(0, -1));
  }, []);

  const handleRPNBackspace = useCallback(() => {
    setError(null);
    if (expression) {
      setExpression((prev) => prev.slice(0, -1));
    } else if (stack.length > 0) {
      setStack((prev) => prev.slice(0, -1));
    }
  }, [expression, stack]);

  const handleAppend = useCallback((value: string) => {
    setError(null);
    setExpression((prev) => prev + value);
  }, []);

  // Standard evaluation
  const handleEvaluate = useCallback(async () => {
    if (!expression.trim()) return;

    setIsLoading(true);
    setError(null);
    setResult('');

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation: expression,
          angle_unit: angleUnit,
          mode: 'infix'
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const detail: ErrorDetail = errData.detail || {
          type: 'error',
          message: 'Failed to evaluate expression',
        };
        throw new Error(detail.message);
      }

      const data = await response.json();
      const evalResult = String(data.result);
      setResult(evalResult);

      setHistory((prev) => [{ expression, result: evalResult }, ...prev]);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [expression, angleUnit]);

  // RPN Push Actions
  const handleRPNEnter = useCallback(() => {
    setError(null);
    if (expression.trim()) {
      setStack((prev) => [...prev, expression.trim()]);
      setExpression('');
    } else if (stack.length > 0) {
      // Duplicate top of stack
      const top = stack[stack.length - 1];
      setStack((prev) => [...prev, top]);
    }
  }, [expression, stack]);

  // RPN Operator Execution
  const handleRPNOperator = useCallback(async (op: string) => {
    setError(null);
    let activeStack = [...stack];

    // Auto-push typing buffer
    if (expression.trim()) {
      activeStack.push(expression.trim());
      setExpression('');
    }

    const binaryOps = ['+', '-', '*', '/', '^'];
    const unaryOps = ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'];

    if (binaryOps.includes(op)) {
      if (activeStack.length < 2) {
        setError(`Insufficient operands on the stack for operator '${op}'`);
        return;
      }
      const right = activeStack.pop()!;
      const left = activeStack.pop()!;

      setIsLoading(true);
      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: `${left} ${right} ${op}`,
            angle_unit: angleUnit,
            mode: 'postfix',
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const detail = errData.detail || { message: 'Failed to evaluate' };
          throw new Error(detail.message);
        }

        const data = await response.json();
        const evalResult = String(data.result);
        setStack([...activeStack, evalResult]);
        setHistory((prev) => [{ expression: `${left} ${right} ${op}`, result: evalResult }, ...prev]);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred');
      } finally {
        setIsLoading(false);
      }
    } else if (unaryOps.includes(op)) {
      if (activeStack.length < 1) {
        setError(`Insufficient operands on the stack for function '${op}'`);
        return;
      }
      const arg = activeStack.pop()!;

      setIsLoading(true);
      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: `${arg} ${op}`,
            angle_unit: angleUnit,
            mode: 'postfix',
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const detail = errData.detail || { message: 'Failed to evaluate' };
          throw new Error(detail.message);
        }

        const data = await response.json();
        const evalResult = String(data.result);
        setStack([...activeStack, evalResult]);
        setHistory((prev) => [{ expression: `${arg} ${op}`, result: evalResult }, ...prev]);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred');
      } finally {
        setIsLoading(false);
      }
    } else if (op === 'x²') {
      if (activeStack.length < 1) {
        setError("Insufficient operands on the stack for function 'x²'");
        return;
      }
      const val = activeStack.pop()!;
      setIsLoading(true);
      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: `${val} 2 ^`,
            angle_unit: angleUnit,
            mode: 'postfix',
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const detail = errData.detail || { message: 'Failed to square value' };
          throw new Error(detail.message);
        }

        const data = await response.json();
        const evalResult = String(data.result);
        setStack([...activeStack, evalResult]);
        setHistory((prev) => [{ expression: `${val} 2 ^`, result: evalResult }, ...prev]);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred');
      } finally {
        setIsLoading(false);
      }
    } else if (op === '10^x') {
      if (activeStack.length < 1) {
        setError("Insufficient operands on the stack for function '10^x'");
        return;
      }
      const val = activeStack.pop()!;
      setIsLoading(true);
      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: `10 ${val} ^`,
            angle_unit: angleUnit,
            mode: 'postfix',
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const detail = errData.detail || { message: 'Failed power evaluation' };
          throw new Error(detail.message);
        }

        const data = await response.json();
        const evalResult = String(data.result);
        setStack([...activeStack, evalResult]);
        setHistory((prev) => [{ expression: `10 ^ ${val}`, result: evalResult }, ...prev]);
      } catch (err: any) {
        setError(err.message || 'An unexpected error occurred');
      } finally {
        setIsLoading(false);
      }
    }
  }, [stack, expression, angleUnit]);

  // Memory Operations
  const handleMemoryClear = useCallback(() => {
    setMemory(0);
  }, []);

  const handleMemoryRecall = useCallback(() => {
    setError(null);
    setExpression((prev) => prev + String(memory));
  }, [memory]);

  const handleMemoryAdd = useCallback(async () => {
    let valueToUse = 0;

    if (mode === 'rpn') {
      const topVal = stack[stack.length - 1];
      if (topVal && !isNaN(Number(topVal))) {
        valueToUse = Number(topVal);
      } else if (expression.trim() && !isNaN(Number(expression))) {
        valueToUse = Number(expression);
      } else {
        return;
      }
    } else {
      if (result && !isNaN(Number(result))) {
        valueToUse = Number(result);
      } else if (expression.trim() && !isNaN(Number(expression))) {
        valueToUse = Number(expression);
      } else if (expression.trim()) {
        setIsLoading(true);
        setError(null);
        try {
          const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operation: expression, angle_unit: angleUnit, mode: 'infix' }),
          });
          if (response.ok) {
            const data = await response.json();
            const evalResult = String(data.result);
            setResult(evalResult);
            valueToUse = Number(evalResult);
            setHistory((prev) => [{ expression, result: evalResult }, ...prev]);
          } else {
            throw new Error('Failed to evaluate for memory add');
          }
        } catch (err: any) {
          setError(err.message || 'Error evaluating for memory add');
          setIsLoading(false);
          return;
        } finally {
          setIsLoading(false);
        }
      } else {
        return;
      }
    }

    setMemory((prev) => prev + valueToUse);
  }, [mode, stack, result, expression, angleUnit]);

  const handleMemorySubtract = useCallback(async () => {
    let valueToUse = 0;

    if (mode === 'rpn') {
      const topVal = stack[stack.length - 1];
      if (topVal && !isNaN(Number(topVal))) {
        valueToUse = Number(topVal);
      } else if (expression.trim() && !isNaN(Number(expression))) {
        valueToUse = Number(expression);
      } else {
        return;
      }
    } else {
      if (result && !isNaN(Number(result))) {
        valueToUse = Number(result);
      } else if (expression.trim() && !isNaN(Number(expression))) {
        valueToUse = Number(expression);
      } else if (expression.trim()) {
        setIsLoading(true);
        setError(null);
        try {
          const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operation: expression, angle_unit: angleUnit, mode: 'infix' }),
          });
          if (response.ok) {
            const data = await response.json();
            const evalResult = String(data.result);
            setResult(evalResult);
            valueToUse = Number(evalResult);
            setHistory((prev) => [{ expression, result: evalResult }, ...prev]);
          } else {
            throw new Error('Failed to evaluate for memory subtract');
          }
        } catch (err: any) {
          setError(err.message || 'Error evaluating for memory subtract');
          setIsLoading(false);
          return;
        } finally {
          setIsLoading(false);
        }
      } else {
        return;
      }
    }

    setMemory((prev) => prev - valueToUse);
  }, [mode, stack, result, expression, angleUnit]);

  // Angle unit toggle
  const toggleAngleUnit = useCallback(() => {
    setAngleUnit((prev) => (prev === 'radians' ? 'degrees' : 'radians'));
  }, []);

  // History reload actions
  const handleReloadExpression = useCallback((histExpr: string) => {
    setError(null);
    setExpression(histExpr);
    if (mode !== 'rpn') {
      setResult('');
    }
  }, [mode]);

  const handleAppendResult = useCallback((histRes: string) => {
    setError(null);
    if (mode === 'rpn') {
      setStack((prev) => [...prev, histRes]);
    } else {
      setExpression((prev) => prev + histRes);
    }
  }, [mode]);

  const handleClearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  // Keyboard shortcut listeners
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { key } = event;
      if (key >= '0' && key <= '9') {
        handleAppend(key);
      } else if (['+', '-', '*', '/', '^'].includes(key)) {
        if (mode === 'rpn') {
          event.preventDefault();
          handleRPNOperator(key);
        } else {
          handleAppend(key);
        }
      } else if (key === '.' || key === '(' || key === ')') {
        if (mode === 'rpn' && (key === '(' || key === ')')) {
          return; // Parentheses disabled in RPN
        }
        handleAppend(key);
      } else if (key === 'Enter' || key === '=') {
        event.preventDefault();
        if (mode === 'rpn') {
          handleRPNEnter();
        } else {
          handleEvaluate();
        }
      } else if (key === 'Backspace') {
        if (mode === 'rpn') {
          handleRPNBackspace();
        } else {
          handleBackspace();
        }
      } else if (key === 'Escape') {
        handleClear();
      } else if (key.toLowerCase() === 'p') {
        handleAppend('pi');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [mode, handleAppend, handleEvaluate, handleBackspace, handleClear, handleRPNEnter, handleRPNOperator, handleRPNBackspace]);

  // Unified Button Renderer
  const renderButton = (
    label: string,
    onClick: () => void,
    bgColorClass = 'bg-slate-700 hover:bg-slate-600 text-white',
    ariaLabel = label
  ) => (
    <button
      type="button"
      onClick={onClick}
      className={`py-3.5 rounded-xl text-lg font-semibold transition-all duration-150 focus:outline-none focus:ring-4 focus:ring-sky-400 active:scale-95 ${bgColorClass}`}
      aria-label={ariaLabel}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full max-w-4xl mx-auto justify-center items-stretch p-4">
      {/* Main Scientific Calculator Module */}
      <div className="w-full max-w-lg bg-slate-900 shadow-2xl rounded-3xl p-6 border border-slate-800 flex flex-col justify-between">
        
        {/* display bar top controls */}
        <div className="flex justify-between items-center mb-3 gap-2">
          <button
            type="button"
            onClick={() => setIsHistoryOpen((prev) => !prev)}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-1.5 px-3 rounded-lg border border-slate-700 transition shrink-0"
            aria-label="Toggle history panel"
          >
            {isHistoryOpen ? 'Hide History' : 'Show History'}
          </button>
          
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {memory !== 0 && (
              <span 
                className="text-xs font-bold text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/30 tracking-wide shrink-0"
                aria-label="Memory is not empty badge"
              >
                M
              </span>
            )}
            <span 
              className="text-xs font-extrabold uppercase bg-sky-500/10 text-sky-400 px-2.5 py-1 rounded border border-sky-500/30 tracking-wide shrink-0"
              aria-label="Current angle mode badge"
            >
              {angleUnit === 'radians' ? 'Rad' : 'Deg'}
            </span>
          </div>
        </div>

        {/* Dual Mode Selector (Stage 4) */}
        <div className="flex bg-slate-950 p-1.5 rounded-2xl mb-4 border border-slate-800">
          <button
            type="button"
            onClick={() => {
              setMode('standard');
              handleClear();
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all duration-200 uppercase tracking-wider ${mode === 'standard' ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/15' : 'text-slate-400 hover:text-slate-200'}`}
            aria-label="Switch to standard infix mode"
          >
            Standard Infix
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('rpn');
              handleClear();
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all duration-200 uppercase tracking-wider ${mode === 'rpn' ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/15' : 'text-slate-400 hover:text-slate-200'}`}
            aria-label="Switch to RPN stack mode"
          >
            RPN Stack
          </button>
        </div>

        {/* High-Contrast Calculator Display */}
        <div 
          className="bg-slate-950 rounded-2xl p-5 mb-5 flex flex-col justify-between items-end min-h-[145px] text-right border border-slate-800 shadow-inner"
          role="region"
          aria-live="polite"
          aria-label="Calculator screen"
        >
          {mode === 'standard' ? (
            <>
              <div 
                className="text-slate-400 text-lg overflow-x-auto whitespace-nowrap w-full scrollbar-none tracking-wide"
                aria-label="Arithmetic expression"
              >
                {expression || ' '}
              </div>
              
              {/* Dynamic Postfix Preview */}
              {expression.trim() && (
                <div 
                  className="text-slate-500 text-xs font-mono w-full overflow-x-auto whitespace-nowrap mt-1 text-left tracking-wide select-all"
                  title="RPN Postfix equivalent"
                  aria-label="Postfix representation preview"
                >
                  RPN Preview: {getPostfixPreview(expression)}
                </div>
              )}
            </>
          ) : (
            /* Visual Stack Level Indicator */
            <div className="w-full flex flex-col gap-1 text-left mb-2 select-none">
              <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase tracking-wider border-b border-slate-900 pb-1">
                <span>Stack Register</span>
                <span>Value</span>
              </div>
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>T</span>
                <span className="text-slate-300">{stack[stack.length - 4] || '0'}</span>
              </div>
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>Z</span>
                <span className="text-slate-300">{stack[stack.length - 3] || '0'}</span>
              </div>
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>Y</span>
                <span className="text-slate-300">{stack[stack.length - 2] || '0'}</span>
              </div>
              <div className="flex justify-between text-sm font-mono text-sky-400 font-bold border-t border-slate-900/40 pt-0.5">
                <span>X (Top)</span>
                <span className="text-sky-300 font-black">{stack[stack.length - 1] || '0'}</span>
              </div>
            </div>
          )}
          
          <div className="w-full overflow-x-auto whitespace-nowrap scrollbar-none mt-2">
            {isLoading ? (
              <span className="text-sky-400 text-3xl font-medium animate-pulse">Evaluating...</span>
            ) : error ? (
              <span className="text-rose-500 text-lg font-medium">{error}</span>
            ) : (
              <span 
                className="text-white text-4xl font-bold tracking-tight"
                aria-label={mode === 'rpn' ? "Active input value" : "Calculation result"}
              >
                {mode === 'rpn' ? (expression !== '' ? expression : '0') : (result !== '' ? result : '0')}
              </span>
            )}
          </div>
        </div>

        {/* Button Grid Pad - Symmetrical 5-Column Scientific Layout */}
        <div className="grid grid-cols-5 gap-2.5">
          {/* Row 1: Memory & Angle Toggle */}
          {renderButton('MC', handleMemoryClear, 'bg-slate-800 hover:bg-slate-700 text-amber-500 border border-slate-700/50', 'Clear Memory register')}
          {renderButton('MR', handleMemoryRecall, 'bg-slate-800 hover:bg-slate-700 text-amber-500 border border-slate-700/50', 'Recall Memory register')}
          {renderButton('M+', handleMemoryAdd, 'bg-slate-800 hover:bg-slate-700 text-amber-500 border border-slate-700/50', 'Add display to memory')}
          {renderButton('M-', handleMemorySubtract, 'bg-slate-800 hover:bg-slate-700 text-amber-500 border border-slate-700/50', 'Subtract display from memory')}
          {renderButton(
            angleUnit === 'radians' ? 'Deg' : 'Rad', 
            toggleAngleUnit, 
            'bg-sky-600/20 hover:bg-sky-600/30 text-sky-400 border border-sky-500/30', 
            `Switch to ${angleUnit === 'radians' ? 'Degrees' : 'Radians'} angle unit`
          )}

          {/* Row 2: Trig Group A */}
          {renderButton('sin', mode === 'rpn' ? () => handleRPNOperator('sin') : () => handleAppend('sin('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Sine function')}
          {renderButton('cos', mode === 'rpn' ? () => handleRPNOperator('cos') : () => handleAppend('cos('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Cosine function')}
          {renderButton('tan', mode === 'rpn' ? () => handleRPNOperator('tan') : () => handleAppend('tan('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Tangent function')}
          {renderButton('pi', () => handleAppend('pi'), 'bg-slate-800 hover:bg-slate-700 text-emerald-400', 'Constant Pi')}
          {renderButton('e', () => handleAppend('e'), 'bg-slate-800 hover:bg-slate-700 text-emerald-400', 'Constant e')}

          {/* Row 3: Trig Group B & Exponents */}
          {renderButton('asin', mode === 'rpn' ? () => handleRPNOperator('asin') : () => handleAppend('asin('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Arcsine function')}
          {renderButton('acos', mode === 'rpn' ? () => handleRPNOperator('acos') : () => handleAppend('acos('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Arccosine function')}
          {renderButton('atan', mode === 'rpn' ? () => handleRPNOperator('atan') : () => handleAppend('atan('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Arctangent function')}
          {renderButton('ln', mode === 'rpn' ? () => handleRPNOperator('ln') : () => handleAppend('ln('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Natural logarithm')}
          {renderButton('log', mode === 'rpn' ? () => handleRPNOperator('log') : () => handleAppend('log('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Logarithm base 10')}

          {/* Row 4: Power and Square roots */}
          {renderButton('sqrt', mode === 'rpn' ? () => handleRPNOperator('sqrt') : () => handleAppend('sqrt('), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Square root function')}
          {renderButton('^', mode === 'rpn' ? () => handleRPNOperator('^') : () => handleAppend('^'), 'bg-slate-800 hover:bg-slate-700 text-amber-400', 'Power operator')}
          {renderButton('x²', mode === 'rpn' ? () => handleRPNOperator('x²') : () => handleAppend('^2'), 'bg-slate-800 hover:bg-slate-700 text-slate-300', 'Square exponentiation')}
          {renderButton('10^x', mode === 'rpn' ? () => handleRPNOperator('10^x') : () => handleAppend('10^'), 'bg-slate-800 hover:bg-slate-700 text-slate-300', '10 to the power of x')}
          {renderButton('⌫', mode === 'rpn' ? handleRPNBackspace : handleBackspace, 'bg-slate-800/80 hover:bg-slate-800 text-rose-400 font-bold', 'Backspace')}

          {/* Row 5: Digits Row 1 & Parenthesis */}
          {renderButton('7', () => handleAppend('7'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('8', () => handleAppend('8'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('9', () => handleAppend('9'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton(
            '(', 
            mode === 'rpn' ? () => {} : () => handleAppend('('), 
            mode === 'rpn' ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed border border-slate-800/20' : 'bg-slate-800 hover:bg-slate-700 text-slate-200', 
            'Open parenthesis'
          )}
          {renderButton(
            ')', 
            mode === 'rpn' ? () => {} : () => handleAppend(')'), 
            mode === 'rpn' ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed border border-slate-800/20' : 'bg-slate-800 hover:bg-slate-700 text-slate-200', 
            'Close parenthesis'
          )}

          {/* Row 6: Digits Row 2 & Multiplication/Division */}
          {renderButton('4', () => handleAppend('4'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('5', () => handleAppend('5'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('6', () => handleAppend('6'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('*', mode === 'rpn' ? () => handleRPNOperator('*') : () => handleAppend('*'), 'bg-amber-600 hover:bg-amber-500 text-white', 'Multiply')}
          {renderButton('/', mode === 'rpn' ? () => handleRPNOperator('/') : () => handleAppend('/'), 'bg-amber-600 hover:bg-amber-500 text-white', 'Divide')}

          {/* Row 7: Digits Row 3 & Addition/Subtraction */}
          {renderButton('1', () => handleAppend('1'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('2', () => handleAppend('2'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('3', () => handleAppend('3'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('+', mode === 'rpn' ? () => handleRPNOperator('+') : () => handleAppend('+'), 'bg-amber-600 hover:bg-amber-500 text-white', 'Add')}
          {renderButton('-', mode === 'rpn' ? () => handleRPNOperator('-') : () => handleAppend('-'), 'bg-amber-600 hover:bg-amber-500 text-white', 'Subtract')}

          {/* Row 8: Base Row */}
          {renderButton('C', handleClear, 'bg-rose-600 hover:bg-rose-500 text-white', 'Clear calculator')}
          {renderButton('0', () => handleAppend('0'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          {renderButton('.', () => handleAppend('.'), 'bg-slate-750 hover:bg-slate-700 text-white')}
          
          {/* Equal evaluate / PUSH button spans the remaining 2 columns */}
          <button
            type="button"
            onClick={mode === 'rpn' ? handleRPNEnter : handleEvaluate}
            className="col-span-2 py-3.5 rounded-xl text-lg font-bold transition-all duration-150 focus:outline-none focus:ring-4 focus:ring-sky-400 active:scale-95 bg-sky-500 hover:bg-sky-400 text-white shadow-lg shadow-sky-500/20"
            aria-label={mode === 'rpn' ? "Push value to stack" : "Evaluate expression"}
          >
            {mode === 'rpn' ? 'ENTER' : '='}
          </button>
        </div>
      </div>

      {/* Interactive Collapsible Calculation History Panel/Drawer */}
      {isHistoryOpen && (
        <div className="w-full lg:w-80 bg-slate-900 shadow-2xl rounded-3xl p-5 border border-slate-800 flex flex-col justify-between max-h-[570px] lg:max-h-none overflow-hidden transition-all duration-300">
          <div>
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-slate-200 tracking-wide uppercase">Session History</h2>
              {history.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearHistory}
                  className="text-xs text-rose-400 hover:text-rose-300 font-semibold tracking-wider hover:underline transition"
                  aria-label="Clear calculations history"
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Calculations List Container */}
            <div className="overflow-y-auto mt-4 space-y-3 h-[250px] lg:h-[400px] pr-1 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 py-8">
                  <p className="text-sm">No calculations yet in this session.</p>
                  <p className="text-xs mt-1">Evaluated operations will appear here.</p>
                </div>
              ) : (
                history.map((item, index) => (
                  <div 
                    key={index} 
                    className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 hover:border-slate-700/80 transition flex flex-col gap-1 text-right"
                  >
                    {/* Click expression to reload it */}
                    <button
                      type="button"
                      onClick={() => handleReloadExpression(item.expression)}
                      className="text-slate-400 text-sm hover:text-sky-400 font-mono tracking-wide break-all text-right hover:underline focus:outline-none focus:text-sky-400"
                      title="Click to reload this expression"
                      aria-label={`Load historical expression: ${item.expression}`}
                    >
                      {item.expression}
                    </button>
                    {/* Click result to append it */}
                    <button
                      type="button"
                      onClick={() => handleAppendResult(item.result)}
                      className="text-white text-base font-bold hover:text-amber-400 font-mono tracking-tight text-right hover:underline focus:outline-none focus:text-amber-400 mt-1"
                      title="Click to append or push this result"
                      aria-label={mode === 'rpn' ? `Push historical result: ${item.result}` : `Append historical result: ${item.result}`}
                    >
                      = {item.result}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="text-center text-[10px] text-slate-500 pt-3 border-t border-slate-800 mt-3">
            {mode === 'rpn' ? 'Click expression to type. Click result to PUSH onto stack.' : 'Click expression to reload. Click result to append.'}
          </div>
        </div>
      )}
    </div>
  );
}
