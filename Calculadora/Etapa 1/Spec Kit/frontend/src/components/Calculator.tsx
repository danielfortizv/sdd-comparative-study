import React, { useState, useEffect } from 'react';
import { Display } from './Display';
import { ButtonGrid } from './ButtonGrid';
import { evaluateExpression } from '../services/api';

export const Calculator: React.FC = () => {
  const [expression, setExpression] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleKeyPress = (value: string) => {
    setError('');
    setExpression((prev) => {
      // Prevent multiple trailing decimals in a single token
      if (value === '.') {
        const tokens = prev.split(/[\+\-\*\/]/);
        const lastToken = tokens[tokens.length - 1];
        if (lastToken.includes('.')) return prev;
      }
      return prev + value;
    });
  };

  const handleClear = () => {
    setExpression('');
    setResult('');
    setError('');
  };

  const handleBackspace = () => {
    setError('');
    setExpression((prev) => (prev.length > 0 ? prev.slice(0, -1) : ''));
  };

  const handleEvaluate = async () => {
    if (!expression) return;
    setLoading(true);
    setError('');
    try {
      const response = await evaluateExpression(expression);
      setResult(response.result);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Error evaluating expression.');
      }
      setResult('');
    } finally {
      setLoading(false);
    }
  };

  // Global document keydown listeners (T022 / FR-005)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { key } = event;

      // Numbers
      if (/^[0-9]$/.test(key)) {
        event.preventDefault();
        handleKeyPress(key);
      }
      // Operators
      else if (['+', '-', '*', '/'].includes(key)) {
        event.preventDefault();
        handleKeyPress(key);
      }
      // Parentheses and Decimals
      else if (['(', ')', '.'].includes(key)) {
        event.preventDefault();
        handleKeyPress(key);
      }
      // Evaluate (Enter or Equal)
      else if (key === 'Enter' || key === '=') {
        event.preventDefault();
        handleEvaluate();
      }
      // Clear last character (Backspace)
      else if (key === 'Backspace') {
        event.preventDefault();
        handleBackspace();
      }
      // Clear / Reset all (Escape)
      else if (key === 'Escape') {
        event.preventDefault();
        handleClear();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [expression]); // Re-bind effect when expression state changes to keep reference active

  return (
    <div className="calculator-container" role="application" aria-label="High precision arithmetic web calculator">
      <h1 className="calculator-title">Daily Calculator</h1>
      
      <Display 
        expression={expression} 
        result={result} 
        error={loading ? 'Calculating...' : error} 
      />
      
      <ButtonGrid 
        onKeyPress={handleKeyPress}
        onClear={handleClear}
        onBackspace={handleBackspace}
        onEvaluate={handleEvaluate}
      />
      
      <div className="sr-only" aria-live="polite">
        {loading ? 'Calculating arithmetic formula...' : ''}
        {result ? `Calculated result is ${result}` : ''}
        {error ? `Calculation error: ${error}` : ''}
      </div>
    </div>
  );
};
