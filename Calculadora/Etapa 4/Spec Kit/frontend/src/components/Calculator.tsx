import React, { useState, useEffect } from 'react';
import { Display } from './Display';
import { ButtonGrid } from './ButtonGrid';
import { StackVisualizer } from './StackVisualizer';
import { evaluateExpression } from '../services/api';
import { HistoryItem } from '../types/calculator';

export const Calculator: React.FC = () => {
  const [expression, setExpression] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Stage 4 Mode and Stack States
  const [mode, setMode] = useState<'standard' | 'rpn'>('standard');
  const [stack, setStack] = useState<string[]>([]);

  // Stage 2 Extended States
  const [angleUnit, setAngleUnit] = useState<'radians' | 'degrees'>('radians');
  const [memoryRegister, setMemoryRegister] = useState<string>('0');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showScientific, setShowScientific] = useState<boolean>(true);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  const handleKeyPress = async (value: string) => {
    setError('');
    
    if (mode === 'rpn') {
      // In RPN mode, clicking an operator (binary or scientific function) evaluates the stack
      const isOperator = ['+', '-', '*', '/'].includes(value);
      const isScientificFunc = ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sqrt', 'ln', 'log10', 'root', '^', '^2', '10^'].includes(value);
      
      if (isOperator || isScientificFunc) {
        await handleRpnOperator(value);
      } else {
        // Just appending numbers, decimals, or constants to current entry display
        setExpression((prev) => {
          if (value === '.') {
            if (prev.includes('.')) return prev;
          }
          if (value === 'pi' || value === 'e') {
            return value; // Constants overwrite empty or existing digits
          }
          return prev + value;
        });
      }
    } else {
      // Standard Infix mode character press
      setExpression((prev) => {
        if (value === '.') {
          const tokens = prev.split(/[+\-*/]/);
          const lastToken = tokens[tokens.length - 1];
          if (lastToken.includes('.')) return prev;
        }
        return prev + value;
      });
    }
  };

  const handleClear = () => {
    setExpression('');
    setResult('');
    setError('');
    if (mode === 'rpn') {
      setStack([]);
    }
  };

  const handleBackspace = () => {
    setError('');
    setExpression((prev) => (prev.length > 0 ? prev.slice(0, -1) : ''));
  };

  const handleRpnOperator = async (operatorToken: string) => {
    setLoading(true);
    setError('');
    
    // Build active operational stack representation
    let currentStack = [...stack];
    if (expression !== '') {
      currentStack.push(expression);
    }
    
    if (currentStack.length === 0) {
      setError('Evaluation stack is empty.');
      setLoading(false);
      return;
    }
    
    // Map visual shortcuts to core math function tokens
    let op = operatorToken;
    if (op === '^') op = '**';
    else if (op === '^2') op = '2 **';
    else if (op === '10^') op = '10 swap **';  // backend handles general powers; in RPN 10^x is "10 x **"
    
    // Construct space-separated postfix string
    let rpnExpr = currentStack.join(' ') + ' ' + op;
    if (operatorToken === '10^') {
      // RPN representation for base 10 power of top of stack:
      // pop x, push 10, push x, pow
      const x = currentStack.pop() || '0';
      rpnExpr = [...currentStack, '10', x, '**'].join(' ');
    } else if (operatorToken === '^2') {
      // pop x, push 2, pow
      const x = currentStack.pop() || '0';
      rpnExpr = [...currentStack, x, '2', '**'].join(' ');
    } else if (operatorToken === 'sin(' || operatorToken === 'sin') {
      rpnExpr = currentStack.join(' ') + ' sin';
    } else if (operatorToken === 'cos(' || operatorToken === 'cos') {
      rpnExpr = currentStack.join(' ') + ' cos';
    } else if (operatorToken === 'tan(' || operatorToken === 'tan') {
      rpnExpr = currentStack.join(' ') + ' tan';
    } else if (operatorToken === 'asin(' || operatorToken === 'asin') {
      rpnExpr = currentStack.join(' ') + ' asin';
    } else if (operatorToken === 'acos(' || operatorToken === 'acos') {
      rpnExpr = currentStack.join(' ') + ' acos';
    } else if (operatorToken === 'atan(' || operatorToken === 'atan') {
      rpnExpr = currentStack.join(' ') + ' atan';
    } else if (operatorToken === 'sqrt(' || operatorToken === 'sqrt') {
      rpnExpr = currentStack.join(' ') + ' sqrt';
    } else if (operatorToken === 'root(' || operatorToken === 'root') {
      rpnExpr = currentStack.join(' ') + ' root';
    } else if (operatorToken === 'ln(' || operatorToken === 'ln') {
      rpnExpr = currentStack.join(' ') + ' ln';
    } else if (operatorToken === 'log10(' || operatorToken === 'log10') {
      rpnExpr = currentStack.join(' ') + ' log10';
    }

    try {
      const response = await evaluateExpression(rpnExpr, angleUnit, 'rpn');
      setResult(response.result);
      setStack(response.stack || []);
      setExpression('');

      // Add calculation to session history list
      const newHistoryItem: HistoryItem = {
        id: Math.random().toString(36).substr(2, 9),
        expression: rpnExpr,
        result: response.result,
      };
      setHistory((prev) => [newHistoryItem, ...prev]);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Error evaluating stack operation.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    if (mode === 'rpn') {
      // In RPN mode, the '=' / 'ENTER' key commits current expression buffer onto the stack
      if (!expression) return;
      setStack((prev) => [...prev, expression]);
      setExpression('');
      setError('');
    } else {
      // Standard Infix Mode Evaluate
      if (!expression) return;
      setLoading(true);
      setError('');
      try {
        const response = await evaluateExpression(expression, angleUnit, 'standard');
        setResult(response.result);

        // Append calculation to history drawer
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
    }
  };

  // Stage 2 Memory Actions
  const handleMemoryAdd = () => {
    const valueToAdd = parseFloat(result || expression || '0');
    if (isNaN(valueToAdd)) return;
    setError('');
    setMemoryRegister((prev) => {
      const sum = parseFloat(prev) + valueToAdd;
      return parseFloat(sum.toFixed(14)).toString();
    });
  };

  const handleMemorySubtract = () => {
    const valueToSub = parseFloat(result || expression || '0');
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
    if (mode === 'rpn') {
      // For RPN, history results are pushed straight to active stack
      if (part === 'result') {
        setStack((prev) => [...prev, item.result]);
      } else {
        // Parse individual items of the history RPN path and append
        const tokens = item.expression.split(' ');
        const numericalTokens = tokens.filter(tok => !isNaN(parseFloat(tok)) || tok === 'pi' || tok === 'e');
        setStack((prev) => [...prev, ...numericalTokens]);
      }
    } else {
      if (part === 'expression') {
        setExpression(item.expression);
      } else {
        setExpression(item.result);
      }
    }
  };

  // Keyboard accessibility listeners (T019)
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
      // Constants shortcut
      else if (key.toLowerCase() === 'p') {
        event.preventDefault();
        handleKeyPress('pi');
      }
      // Parentheses and Decimals
      else if (['(', ')', '.'].includes(key)) {
        if (mode === 'rpn' && ['(', ')'].includes(key)) return; // Parentheses disabled in RPN
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
  }, [expression, stack, angleUnit, mode]); // Re-bind effect when expression, stack or mode changes

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

        {/* RPN Stack Visualizer Panel */}
        {mode === 'rpn' && <StackVisualizer stack={stack} />}

        {/* State Control Indicators Row */}
        <div className="calculator-controls-row">
          <div className="control-badge-group">
            {isMemoryActive && (
              <span className="badge-m" aria-label={`Memory register active: value ${memoryRegister}`}>M</span>
            )}
            <span className="badge-angle" aria-label={`Angle mode: ${angleUnit}`}>{angleUnit === 'radians' ? 'Rad' : 'Deg'}</span>
            <span className="badge-mode" aria-label={`Active calculator mode: ${mode}`}>{mode === 'standard' ? 'Standard' : 'RPN'}</span>
          </div>
          <div className="control-badge-group">
            <button 
              type="button" 
              className={`btn-control-toggle ${mode === 'rpn' ? 'active' : ''}`}
              onClick={() => {
                setMode(mode === 'standard' ? 'rpn' : 'standard');
                setError('');
                setExpression('');
                setResult('');
              }}
              aria-label={`Switch calculator mode. Currently: ${mode}`}
            >
              {mode === 'standard' ? 'RPN Mode' : 'Standard Mode'}
            </button>
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
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'sqrt' : 'sqrt(')} aria-label="Square root">√x</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'root' : 'root(')} aria-label="Y-th root of X">ʸ√x</button>
            
            {/* Logs */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'ln' : 'ln(')} aria-label="Natural logarithm">ln</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'log10' : 'log10(')} aria-label="Logarithm base 10">log₁₀</button>

            {/* Trigonometry */}
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'sin' : 'sin(')} aria-label="Sine function">sin</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'cos' : 'cos(')} aria-label="Cosine function">cos</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'tan' : 'tan(')} aria-label="Tangent function">tan</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'asin' : 'asin(')} aria-label="Arc-sine inverse function">asin</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'acos' : 'acos(')} aria-label="Arc-cosine inverse function">acos</button>
            <button type="button" className="calc-btn btn-scientific" onClick={() => handleKeyPress(mode === 'rpn' ? 'atan' : 'atan(')} aria-label="Arc-tangent inverse function">atan</button>
          </div>
        )}

        {/* Standard Calculator Button Keys Grid */}
        <ButtonGrid 
          onKeyPress={handleKeyPress}
          onClear={handleClear}
          onBackspace={handleBackspace}
          onEvaluate={handleEvaluate}
          mode={mode}
        />

        {/* Screen Reader Announcements */}
        <div className="sr-only" aria-live="polite">
          {loading ? 'Evaluating expression...' : ''}
          {result ? `Evaluation result is ${result}` : ''}
          {error ? `Error: ${error}` : ''}
          {angleUnit ? `Angle measurement set to ${angleUnit}` : ''}
          {mode ? `Evaluation mode set to ${mode}` : ''}
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
