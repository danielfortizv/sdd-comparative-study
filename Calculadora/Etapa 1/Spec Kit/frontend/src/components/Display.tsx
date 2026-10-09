import React from 'react';

interface DisplayProps {
  expression: string;
  result: string;
  error: string;
}

export const Display: React.FC<DisplayProps> = ({ expression, result, error }) => {
  return (
    <div className="calculator-display" aria-label="Calculator screen display">
      {/* Formula Area (Expression typed so far) */}
      <div 
        className="display-expression" 
        id="display-expression"
        aria-label={`Typed formula expression: ${expression || 'empty'}`}
      >
        {expression || '0'}
      </div>
      
      {/* Result or Error Area (Output) */}
      <div 
        className={`display-output ${error ? 'display-error' : ''}`}
        id="display-result"
        aria-live="polite"
        aria-atomic="true"
        role="status"
        aria-label={error ? `Error: ${error}` : `Result: ${result || '0'}`}
      >
        {error ? error : (result || '0')}
      </div>
    </div>
  );
};
