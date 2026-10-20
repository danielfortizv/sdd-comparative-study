import React, { useState, useEffect } from 'react';
import { Display } from './Display';
import { ButtonGrid } from './ButtonGrid';
import { evaluateExpression } from '../services/api';
import { HistoryItem } from '../types/calculator';

export const Calculator: React.FC = () => {
  const [expression, setExpression] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Stage 2 Extended States
  const [angleUnit, setAngleUnit] = useState<'radians' | 'degrees'>('radians');
  const [memoryRegister, setMemoryRegister] = useState<string>('0');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showScientific, setShowScientific] = useState<boolean>(true);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  const handleKeyPress = (value: string) => {
    setError('');
    setExpression((prev) => {
      // Prevent multiple trailing decimals in a single token
      if (value === '.') {
        const tokens = prev.split(/[+\-*/]/);
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
      const response = await evaluateExpression(expression, angleUnit);
      setResult(response.result);

      // Append success calculation to history drawer
      const newHistoryItem: HistoryItem = {
        id: Math.random().toString(36).substr(2, 9),
        expression: expression,
        result: response.result,
      };
      setHistory((prev) => [newHistoryItem, ...prev]);
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

  // Stage 2 Memory Actions
  const handleMemoryAdd = () => {
    const valueToAdd = parseFloat(result || '0');
    if (isNaN(valueToAdd)) return;
    setError('');
    setMemoryRegister((prev) => {
      const sum = parseFloat(prev) + valueToAdd;
      // High-precision decimal clean round to strip representation noise
      return parseFloat(sum.toFixed(14)).toString();
    });
  };

  const handleMemorySubtract = () => {
    const valueToSub = parseFloat(result || '0');
    if (isNaN(valueToSub)) return;
    setError('');
    setMemoryRegister((prev) => {
      const diff = parseFloat(prev) - valueToSub;
      return parseFloat(diff.toFixed(14)).toString();
    });
  };

  const handleMemoryRecall = () => {
    setError('');
    setExpression((prev) => prev + memoryRegister);
  };

  const handleMemoryClear = () => {
    setMemoryRegister('0');
  };

  const toggleAngleUnit = () => {
    setAngleUnit((prev) => (prev === 'radians' ? 'degrees' : 'radians'));
  };

  const clearAllHistory = () => {
    setHistory([]);
  };

  const handleLoadHistory = (item: HistoryItem, part: 'expression' | 'result') => {
    setError('');
    if (part === 'expression') {
      setExpression(item.expression);
    } else {
      setExpression(item.result);
    }
  };

  // Keyboard accessibility listeners (T028 / FR-011)
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
      // Caret / Exponent
      else if (key === '^') {
        event.preventDefault();
        handleKeyPress('^');
      }
      // Constants shortcut (p -> pi, e -> e)
      else if (key.toLowerCase() === 'p') {
        event.preventDefault();
        handleKeyPress('pi');
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expression, angleUnit]); // Re-bind effect when expression or mode changes

  const isMemoryActive = parseFloat(memoryRegister) !== 0;

  return (
    <div className="app-layout-wrapper">
      {/* Main Calculator */}
      <div 
        className={`calculator-container ${showScientific ? 'scientific-active' : ''}`} 
        role="application" 
        aria-label="High precision scientific web calculator"
      >
        <h1 className="calculator-title">Scientific Calculator</h1>

        {/* Dynamic Display */}
        <Display 
          expression={expression} 
          result={result} 
          error={loading ? 'Calculating...' : error} 
        />

        {/* State Control Indicators Row (FR-007, FR-012) */}
        <div className="calculator-controls-row">
          <div className="control-badge-group">
            {isMemoryActive && (
              <span className="badge-m" aria-label={`Memory register active: value ${memoryRegister}`}>M</span>
            )}
            <span className="badge-angle" aria-label={`Angle mode: ${angleUnit}`}>{angleUnit === 'radians' ? 'Rad' : 'Deg'}</span>
          </div>
          <div className="control-badge-group">
            <button 
              type="button" 
              className={`btn-control-toggle ${angleUnit === 'degrees' ? 'active' : ''}`}
              onClick={toggleAngleUnit}
              aria-label={`Toggle angle measurement unit, currently ${angleUnit}`}
            >
              {angleUnit === 'radians' ? 'Deg Mode' : 'Rad Mode'}
            </button>
            <button 
              type="button" 
              className={`btn-control-toggle ${showScientific ? 'active' : ''}`}
              onClick={() => setShowScientific(!showScientific)}
              aria-label="Toggle scientific mathematical operations keyboard panel"
            >
              Sci Keypad
            </button>
            <button 
              type="button" 
              className={`btn-control-toggle ${showHistory ? 'active' : ''}`}
              onClick={() => setShowHistory(!showHistory)}
              aria-label="Toggle calculation history panel"
            >
              History ({history.length})
            </button>
          </div>
        </div>

        {/* Collapsible Scientific Buttons Layout Panel */}
        {showScientific && (
          <div className="scientific-grid-container" role="grid" aria-label="Scientific keys keypad">
            {/* Memory operations */}
            <button type="button" className="calc-btn btn-memory" onClick={handleMemoryAdd} aria-label="Memory plus: Add current displayed result to memory">M+</button>
            <button type="button" className="calc-btn btn-memory" onClick={handleMemorySubtract} aria-label="Memory minus: Subtract current displayed result from memory">M-</button>
            <button type="button" className="calc-btn btn-memory" onClick={handleMemoryRecall} aria-label="Memory recall: Insert stored memory value into formula">MR</button>
            <button type="button" className="calc-btn btn-memory" onClick={handleMemoryClear} aria-label="Memory clear: Reset memory register value back to zero">MC</button>

            {/* Constants */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('pi')} aria-label="Mathematical constant Pi">π</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('e')} aria-label="Euler constant e">e</button>

            {/* Powers and Roots */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('^')} aria-label="Power: raising to exponent power">x^y</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('^2')} aria-label="Power: square of number">x²</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('10^')} aria-label="Power: base 10 power">10^x</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('sqrt(')} aria-label="Square root">√x</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('root(')} aria-label="Y-th root of X">ʸ√x</button>
            
            {/* Logs */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('ln(')} aria-label="Natural logarithm">ln</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('log10(')} aria-label="Logarithm base 10">log₁₀</button>

            {/* Trigonometry */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('sin(')} aria-label="Sine function">sin</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('cos(')} aria-label="Cosine function">cos</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('tan(')} aria-label="Tangent function">tan</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('asin(')} aria-label="Arc-sine inverse function">asin</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('acos(')} aria-label="Arc-cosine inverse function">acos</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress('atan(')} aria-label="Arc-tangent inverse function">atan</button>
          </div>
        )}

        {/* Standard Calculator Button Keys Grid */}
        <ButtonGrid 
          onKeyPress={handleKeyPress}
          onClear={handleClear}
          onBackspace={handleBackspace}
          onEvaluate={handleEvaluate}
        />

        {/* Screen Reader Announcements */}
        <div className="sr-only" aria-live="polite">
          {loading ? 'Evaluating expression...' : ''}
          {result ? `Evaluation result is ${result}` : ''}
          {error ? `Error: ${error}` : ''}
          {angleUnit ? `Angle measurement set to ${angleUnit}` : ''}
        </div>
      </div>

      {/* Collapsible Sidebar Session Calculation History Panel */}
      {showHistory && (
        <aside className="history-drawer-panel" aria-label="Session evaluation history drawer">
          <div className="history-drawer-header">
            <h2 className="history-drawer-title">History Logs</h2>
            {history.length > 0 && (
              <button 
                type="button" 
                className="btn-clear-history" 
                onClick={clearAllHistory}
                aria-label="Clear all session calculation history entries"
              >
                Clear History
              </button>
            )}
          </div>

          <div className="history-items-list" role="log" aria-label="List of previous calculations">
            {history.length === 0 ? (
              <p className="history-empty-text">No previous calculations in this session.</p>
            ) : (
              history.map((item) => (
                <div 
                  key={item.id} 
                  className="history-item-row"
                  tabIndex={0}
                  role="button"
                  aria-label={`Recall formula ${item.expression} with result ${item.result}`}
                >
                  <span 
                    className="history-item-expr" 
                    onClick={() => handleLoadHistory(item, 'expression')}
                    title="Click to load this mathematical expression"
                  >
                    {item.expression}
                  </span>
                  <span 
                    className="history-item-res" 
                    onClick={() => handleLoadHistory(item, 'result')}
                    title="Click to load this numerical result"
                  >
                    = {item.result}
                  </span>
                </div>
              ))
            )}
          </div>
        </aside>
      )}
    </div>
  );
};
