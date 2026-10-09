import React from 'react';
import { DisplayState } from '../hooks/useEvaluate';

interface DisplayPanelProps {
  expression: string;
  result: string;
  history: string;
  state: DisplayState;
}

export const DisplayPanel: React.FC<DisplayPanelProps> = ({
  expression,
  result,
  history,
  state,
}) => {
  // Determine correct color styles for results based on active state
  let resultClass = 'preview';
  if (state === 'evaluated') {
    resultClass = 'final';
  } else if (state === 'error') {
    resultClass = 'error';
  }

  // Construct clear spoken text for screen readers (WCAG 2.1 AA)
  const getScreenReaderSpokenText = (): string => {
    if (state === 'error') {
      return `Error: ${result}`;
    }
    if (state === 'evaluated') {
      return `Result: ${result}`;
    }
    return `Expression: ${expression || 'empty'}`;
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
