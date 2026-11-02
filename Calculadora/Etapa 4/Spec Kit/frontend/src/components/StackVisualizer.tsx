import React from 'react';

interface StackVisualizerProps {
  stack: string[];
}

export const StackVisualizer: React.FC<StackVisualizerProps> = ({ stack }) => {
  // Extract values for levels X, Y, Z, T (last 4 items of the stack)
  // stack[stack.length - 1] is Level X (top of stack)
  // stack[stack.length - 2] is Level Y
  // stack[stack.length - 3] is Level Z
  // stack[stack.length - 4] is Level T
  const getStackLevelValue = (offsetFromTop: number): string => {
    const idx = stack.length - 1 - offsetFromTop;
    return idx >= 0 ? stack[idx] : '0';
  };

  const levelX = getStackLevelValue(0);
  const levelY = getStackLevelValue(1);
  const levelZ = getStackLevelValue(2);
  const levelT = getStackLevelValue(3);

  return (
    <div 
      className="rpn-stack-container" 
      role="region" 
      aria-label="RPN evaluation stack levels"
    >
      <h2 className="rpn-stack-title">Evaluation Stack</h2>
      <div className="rpn-stack-grid">
        <div className="rpn-stack-row" role="row" aria-label={`Stack level T, value is ${levelT}`}>
          <span className="rpn-stack-label" aria-hidden="true">T:</span>
          <span className="rpn-stack-value" data-testid="stack-t">{levelT}</span>
        </div>
        <div className="rpn-stack-row" role="row" aria-label={`Stack level Z, value is ${levelZ}`}>
          <span className="rpn-stack-label" aria-hidden="true">Z:</span>
          <span className="rpn-stack-value" data-testid="stack-z">{levelZ}</span>
        </div>
        <div className="rpn-stack-row" role="row" aria-label={`Stack level Y, value is ${levelY}`}>
          <span className="rpn-stack-label" aria-hidden="true">Y:</span>
          <span className="rpn-stack-value" data-testid="stack-y">{levelY}</span>
        </div>
        <div className="rpn-stack-row active-level" role="row" aria-label={`Stack level X, active level, value is ${levelX}`}>
          <span className="rpn-stack-label" aria-hidden="true">X (top):</span>
          <span className="rpn-stack-value" data-testid="stack-x">{levelX}</span>
        </div>
      </div>
      <div className="rpn-stack-footer">
        <span className="rpn-stack-size-indicator" aria-live="polite">
          Stack Size: {stack.length} item(s)
        </span>
      </div>
    </div>
  );
};
