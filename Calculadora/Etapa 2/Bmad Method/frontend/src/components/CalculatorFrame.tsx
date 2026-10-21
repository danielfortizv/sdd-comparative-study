import React, { useState } from 'react';
import { useEvaluate } from '../hooks/useEvaluate';
import { useKeyboard } from '../hooks/useKeyboard';
import { DisplayPanel } from './DisplayPanel';
import { ButtonGrid } from './ButtonGrid';

export const CalculatorFrame: React.FC = () => {
  const {
    expression,
    result,
    history,
    state,
    appendToken,
    clearAll,
    backspace,
    evaluateFinal,
    // Stage 2 Hooks
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
  } = useEvaluate();

  // Component Panel Toggles
  const [showScientific, setShowScientific] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Connect global window keyboard capture event intercepts
  useKeyboard({
    appendToken,
    backspace,
    clearAll,
    evaluateFinal,
    disabled: false,
  });

  return (
    <div className="calculator-layout-wrapper">
      {/* Outermost container for Calculator Box */}
      <div
        className="calculator-container"
        tabIndex={0} // Ensure container itself is keyboard focusable
        role="application"
        aria-label="Scientific High Precision Decimal Calculator"
      >
        {/* Top Toggles Bar */}
        <div className="calculator-header-toggles">
          <button 
            className={`toggle-btn ${showScientific ? 'active' : ''}`}
            onClick={() => setShowScientific(!showScientific)}
            aria-label={showScientific ? "Hide scientific keypad" : "Show scientific keypad"}
            aria-pressed={showScientific}
          >
            {showScientific ? 'Standard' : 'Scientific'}
          </button>
          
          <button 
            className={`toggle-btn ${showHistory ? 'active' : ''}`}
            onClick={() => setShowHistory(!showHistory)}
            aria-label={showHistory ? "Hide calculation history" : "Show calculation history"}
            aria-pressed={showHistory}
          >
            History ({sessionHistory.length})
          </button>
        </div>

        <DisplayPanel
          expression={expression}
          result={result}
          history={history}
          state={state}
          angleUnit={angleUnit}
          memory={memory}
        />
        
        <ButtonGrid
          appendToken={appendToken}
          clearAll={clearAll}
          backspace={backspace}
          evaluateFinal={evaluateFinal}
          disableEvaluate={state === 'error'}
          showScientific={showScientific}
          angleUnit={angleUnit}
          toggleAngleUnit={toggleAngleUnit}
          handleMemoryOperation={handleMemoryOperation}
          clearMemory={clearMemory}
          recallMemory={recallMemory}
        />
      </div>

      {/* Slide-out Session History Side Panel */}
      {showHistory && (
        <aside 
          className="history-drawer-panel"
          role="complementary"
          aria-label="Session Calculation History Panel"
        >
          <div className="drawer-header">
            <h3>Calculation History</h3>
            <button 
              className="drawer-close-btn"
              onClick={() => setShowHistory(false)}
              aria-label="Close history drawer"
            >
              ×
            </button>
          </div>

          <div className="drawer-body">
            {sessionHistory.length === 0 ? (
              <p className="no-history-msg">No calculations in this session yet.</p>
            ) : (
              <ul className="history-list">
                {sessionHistory.map((item, index) => (
                  <li key={index} className="history-item-row">
                    <div className="history-expr-preview">{item.expression}</div>
                    <div className="history-res-preview">= {item.result}</div>
                    
                    {/* Action submenus to reload expressions or results back to display */}
                    <div className="history-item-actions">
                      <button 
                        onClick={() => loadHistoryExpression(item.expression)}
                        aria-label="Load full expression back into display"
                        title="Load expression"
                      >
                        Use Expr
                      </button>
                      <button 
                        onClick={() => loadHistoryResult(item.result)}
                        aria-label="Load result back into display"
                        title="Use final result"
                      >
                        Use Result
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {sessionHistory.length > 0 && (
            <div className="drawer-footer">
              <button 
                className="clear-history-btn"
                onClick={clearHistory}
                aria-label="Clear all session history"
              >
                Clear History
              </button>
            </div>
          )}
        </aside>
      )}
    </div>
  );
};
