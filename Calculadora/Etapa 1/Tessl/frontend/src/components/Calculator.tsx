import React, { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1/evaluate';

interface ErrorDetail {
  type: string;
  message: string;
}

export default function Calculator() {
  const [expression, setExpression] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Core actions
  const handleClear = useCallback(() => {
    setExpression('');
    setResult('');
    setError(null);
  }, []);

  const handleBackspace = useCallback(() => {
    setExpression((prev) => prev.slice(0, -1));
  }, []);

  const handleAppend = useCallback((value: string) => {
    setError(null);
    setExpression((prev) => prev + value);
  }, []);

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
        body: JSON.stringify({ operation: expression }),
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
      setResult(String(data.result));
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [expression]);

  // Listen to keyboard press events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { key } = event;

      if (key >= '0' && key <= '9') {
        handleAppend(key);
      } else if (['+', '-', '*', '/'].includes(key)) {
        handleAppend(key);
      } else if (key === '.' || key === '(' || key === ')') {
        handleAppend(key);
      } else if (key === 'Enter' || key === '=') {
        event.preventDefault();
        handleEvaluate();
      } else if (key === 'Backspace') {
        handleBackspace();
      } else if (key === 'Escape') {
        handleClear();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleAppend, handleEvaluate, handleBackspace, handleClear]);

  // UI Button rendering helper
  const renderButton = (
    label: string,
    onClick: () => void,
    bgColorClass = 'bg-slate-700 hover:bg-slate-600 text-white',
    ariaLabel = label
  ) => (
    <button
      type="button"
      onClick={onClick}
      className={`py-4 rounded-xl text-xl font-semibold transition-colors duration-150 focus:outline-none focus:ring-4 focus:ring-sky-400 active:scale-95 ${bgColorClass}`}
      aria-label={ariaLabel}
    >
      {label}
    </button>
  );

  return (
    <div className="w-full max-w-md mx-auto bg-slate-900 shadow-2xl rounded-3xl p-6 border border-slate-800">
      {/* High-Contrast Calculator Display */}
      <div 
        className="bg-slate-950 rounded-2xl p-6 mb-6 flex flex-col justify-between items-end min-h-[120px] text-right border border-slate-800"
        role="region"
        aria-live="polite"
        aria-label="Calculator screen"
      >
        <div 
          className="text-slate-400 text-lg overflow-x-auto whitespace-nowrap w-full scrollbar-none"
          aria-label="Arithmetic expression"
        >
          {expression || ' '}
        </div>
        
        <div className="w-full overflow-x-auto whitespace-nowrap scrollbar-none mt-2">
          {isLoading ? (
            <span className="text-sky-400 text-3xl font-medium animate-pulse">Evaluating...</span>
          ) : error ? (
            <span className="text-rose-500 text-lg font-medium">{error}</span>
          ) : (
            <span 
              className="text-white text-4xl font-bold"
              aria-label="Calculation result"
            >
              {result !== '' ? result : '0'}
            </span>
          )}
        </div>
      </div>

      {/* Button Grid Pad */}
      <div className="grid grid-cols-4 gap-3">
        {/* Row 1 */}
        {renderButton('C', handleClear, 'bg-rose-600 hover:bg-rose-500 text-white', 'Clear calculator')}
        {renderButton('(', () => handleAppend('('), 'bg-slate-800 hover:bg-slate-700 text-slate-200', 'Open parenthesis')}
        {renderButton(')', () => handleAppend(')'), 'bg-slate-800 hover:bg-slate-700 text-slate-200', 'Close parenthesis')}
        {renderButton('/', () => handleAppend('/'), 'bg-amber-500 hover:bg-amber-400 text-white', 'Divide')}

        {/* Row 2 */}
        {renderButton('7', () => handleAppend('7'))}
        {renderButton('8', () => handleAppend('8'))}
        {renderButton('9', () => handleAppend('9'))}
        {renderButton('*', () => handleAppend('*'), 'bg-amber-500 hover:bg-amber-400 text-white', 'Multiply')}

        {/* Row 3 */}
        {renderButton('4', () => handleAppend('4'))}
        {renderButton('5', () => handleAppend('5'))}
        {renderButton('6', () => handleAppend('6'))}
        {renderButton('-', () => handleAppend('-'), 'bg-amber-500 hover:bg-amber-400 text-white', 'Subtract')}

        {/* Row 4 */}
        {renderButton('1', () => handleAppend('1'))}
        {renderButton('2', () => handleAppend('2'))}
        {renderButton('3', () => handleAppend('3'))}
        {renderButton('+', () => handleAppend('+'), 'bg-amber-500 hover:bg-amber-400 text-white', 'Add')}

        {/* Row 5 */}
        {renderButton('0', () => handleAppend('0'))}
        {renderButton('.', () => handleAppend('.'))}
        {renderButton('⌫', handleBackspace, 'bg-slate-800 hover:bg-slate-700 text-rose-400', 'Backspace')}
        {renderButton('=', handleEvaluate, 'bg-sky-500 hover:bg-sky-400 text-white', 'Evaluate expression')}
      </div>
    </div>
  );
}
