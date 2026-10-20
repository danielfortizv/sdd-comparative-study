import React from 'react';
import { DisplayState } from '../hooks/useEvaluate';

interface DisplayPanelProps {
  expression: string;
  result: string;
  history: string;
  state: DisplayState;
  angleUnit: 'radians' | 'degrees';
  memory: string;
}

export const DisplayPanel: React.FC<DisplayPanelProps> = ({
  expression,
  result,
  history,
  state,
  angleUnit,
  memory,
}) => {
  // Determine correct color styles for results based on active state
  let resultClass = 'preview';
  if (state === 'evaluated') {
    resultClass = 'final';
  } else if (state === 'error') {
    resultClass = 'error';
  }

  const isMemoryActive = memory !== '0';

  // Construct clear spoken text for screen readers (WCAG 2.1 AA)
  const getScreenReaderSpokenText = (): string => {
    let spoken = '';
    if (isMemoryActive) {
      spoken += `Memory stored: ${memory}. `;
    }
    spoken += `Angle mode: ${angleUnit}. `;
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
      </div>

      {/* Faded History Display Slot */}
      <div className="display-monospace display-history" aria-hidden="true">
        {history}
      </div>

      {/* Primary Display - Active Input */}
      <div className="display-monospace display-input" aria-hidden="true">
        {expression || '0'}
      </div>

      {/* Result Display - Live/Final Output */}
      <div className={`display-monospace display-result ${resultClass}`} aria-hidden="true">
        {result}
      </div>
    </div>
  );
};
