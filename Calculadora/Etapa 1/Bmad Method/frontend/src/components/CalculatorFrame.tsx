import React from 'react';
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
  } = useEvaluate();

  // Connect global window keyboard capture event intercepts
  useKeyboard({
    appendToken,
    backspace,
    clearAll,
    evaluateFinal,
    disabled: false,
  });

  return (
    <div
      className="calculator-container"
      tabIndex={0} // Ensure container itself is keyboard focusable
      role="application"
      aria-label="High Precision Decimal Calculator"
    >
      <DisplayPanel
        expression={expression}
        result={result}
        history={history}
        state={state}
      />
      <ButtonGrid
        appendToken={appendToken}
        clearAll={clearAll}
        backspace={backspace}
        evaluateFinal={evaluateFinal}
        disableEvaluate={state === 'error'}
      />
    </div>
  );
};
