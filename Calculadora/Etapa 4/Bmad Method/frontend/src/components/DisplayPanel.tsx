import React from 'react';
import { DisplayState, CalculatorMode } from '../hooks/useEvaluate';

interface DisplayPanelProps {
  expression: string;
  result: string;
  history: string;
  state: DisplayState;
  angleUnit: 'radians' | 'degrees';
  memory: string;
  calcMode?: CalculatorMode;
  stack?: string[];
}

export const DisplayPanel: React.FC<DisplayPanelProps> = ({
  expression,
  result,
  history,
  state,
  angleUnit,
  memory,
  calcMode = 'standard',
  stack = [],
}) => {
  // Determine correct color styles for results based on active state
  let resultClass = 'preview';
  if (state === 'evaluated') {
    resultClass = 'final';
  } else if (state === 'error') {
    resultClass = 'error';
  }

  const isMemoryActive = memory !== '0';

  // Extract stack levels for RPN representation (T, Z, Y, X)
  const stackLen = stack.length;
  const tRegister = stackLen >= 4 ? stack[stackLen - 4] : '0';
  const zRegister = stackLen >= 3 ? stack[stackLen - 3] : '0';
  const yRegister = stackLen >= 2 ? stack[stackLen - 2] : '0';
  const xRegister = stackLen >= 1 ? stack[stackLen - 1] : '0';

  // Construct clear spoken text for screen readers (WCAG 2.1 AA)
  const getScreenReaderSpokenText = (): string => {
    let spoken = '';
    if (isMemoryActive) {
      spoken += `Memory stored: ${memory}. `;
    }
    spoken += `Angle mode: ${angleUnit}. `;
    spoken += `Mode: ${calcMode === 'rpn' ? 'RPN' : 'Standard'}. `;
    
    if (calcMode === 'rpn') {
      spoken += `Stack registers: T: ${tRegister}, Z: ${zRegister}, Y: ${yRegister}, X: ${xRegister}. `;
      spoken += `Current input: ${expression || 'empty'}. `;
      if (state === 'error') {
        spoken += `Error: ${result}`;
      }
      return spoken;
    }

    if (state === 'error') {
      return `${spoken} Error: ${result}`;
    }
    if (state === 'evaluated') {
      return `${spoken} Result: ${result}`;
    }
    return `${spoken} Expression: ${expression || 'empty'}`;
  };

  return (
    <div
      className="display-panel"
      role="region"
      aria-label="Calculator Screen"
    >
      {/* Hidden screen reader live region to polite speak result states */}
      <div 
        className="sr-only" 
        style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0 0 0 0)' }}
        aria-live="polite"
      >
        {getScreenReaderSpokenText()}
      </div>

      {/* Top Bar for Indicators (Angle Mode & Memory Badge) */}
      <div className="display-indicators-row">
        {isMemoryActive && (
          <span 
            className="indicator-badge memory-badge" 
            title={`Memory active: ${memory}`}
            aria-label={`Memory active: ${memory}`}
          >
            M
          </span>
        )}
        <span 
          className="indicator-badge angle-badge"
          title={`Angle units: ${angleUnit}`}
          aria-label={`Angle units: ${angleUnit}`}
        >
          {angleUnit === 'radians' ? 'RAD' : 'DEG'}
        </span>
        {calcMode === 'rpn' && (
          <span 
            className="indicator-badge rpn-badge"
            title="Calculator operating in Reverse Polish Notation mode"
            aria-label="RPN Mode active"
          >
            RPN
          </span>
        )}
      </div>

      {calcMode === 'rpn' ? (
        /* Real-time RPN Stack Register Visualization */
        <div className="rpn-stack-display" aria-label="RPN Stack Registers">
          <div className="stack-level" aria-label={`Stack register T: ${tRegister}`}>
            <span className="stack-label">T:</span>
            <span className="stack-value display-monospace">{tRegister}</span>
          </div>
          <div className="stack-level" aria-label={`Stack register Z: ${zRegister}`}>
            <span className="stack-label">Z:</span>
            <span className="stack-value display-monospace">{zRegister}</span>
          </div>
          <div className="stack-level" aria-label={`Stack register Y: ${yRegister}`}>
            <span className="stack-label">Y:</span>
            <span className="stack-value display-monospace">{yRegister}</span>
          </div>
          <div className="stack-level" aria-label={`Stack register X: ${xRegister}`}>
            <span className="stack-label">X:</span>
            <span className="stack-value display-monospace">{xRegister}</span>
          </div>
        </div>
      ) : (
        /* Faded History Display Slot for standard mode */
        <div className="display-monospace display-history" aria-hidden="true">
          {history}
        </div>
      )}

      {/* Primary Display - Active Input */}
      <div className="display-monospace display-input" aria-hidden="true" style={{ marginTop: calcMode === 'rpn' ? '0.5rem' : '0' }}>
        {calcMode === 'rpn' ? (expression || '0') : (expression || '0')}
      </div>

      {/* Result Display - Live/Final Output */}
      {calcMode !== 'rpn' && (
        <div className={`display-monospace display-result ${resultClass}`} aria-hidden="true">
          {result}
        </div>
      )}
    </div>
  );
};
