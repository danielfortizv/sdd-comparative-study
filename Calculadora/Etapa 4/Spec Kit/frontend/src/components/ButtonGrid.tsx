import React from 'react';

interface ButtonGridProps {
  onKeyPress: (value: string) => void;
  onClear: () => void;
  onBackspace: () => void;
  onEvaluate: () => void;
  mode?: 'standard' | 'rpn';
}

interface CalcButton {
  label: string;
  value: string;
  type: 'number' | 'operator' | 'action' | 'equals';
  ariaLabel: string;
  disabledInRpn?: boolean;
}

export const ButtonGrid: React.FC<ButtonGridProps> = ({
  onKeyPress,
  onClear,
  onBackspace,
  onEvaluate,
  mode = 'standard',
}) => {
  const isRpn = mode === 'rpn';

  const buttons: CalcButton[] = [
    { label: 'AC', value: 'clear', type: 'action', ariaLabel: 'Clear all entries and reset calculator' },
    { label: '⌫', value: 'backspace', type: 'action', ariaLabel: 'Delete last character' },
    { label: '(', value: '(', type: 'operator', ariaLabel: 'Open parenthesis', disabledInRpn: true },
    { label: ')', value: ')', type: 'operator', ariaLabel: 'Close parenthesis', disabledInRpn: true },

    { label: '7', value: '7', type: 'number', ariaLabel: 'Number seven' },
    { label: '8', value: '8', type: 'number', ariaLabel: 'Number eight' },
    { label: '9', value: '9', type: 'number', ariaLabel: 'Number nine' },
    { label: '÷', value: '/', type: 'operator', ariaLabel: 'Divide operator' },

    { label: '4', value: '4', type: 'number', ariaLabel: 'Number four' },
    { label: '5', value: '5', type: 'number', ariaLabel: 'Number five' },
    { label: '6', value: '6', type: 'number', ariaLabel: 'Number six' },
    { label: '×', value: '*', type: 'operator', ariaLabel: 'Multiply operator' },

    { label: '1', value: '1', type: 'number', ariaLabel: 'Number one' },
    { label: '2', value: '2', type: 'number', ariaLabel: 'Number two' },
    { label: '3', value: '3', type: 'number', ariaLabel: 'Number three' },
    { label: '-', value: '-', type: 'operator', ariaLabel: 'Subtract operator' },

    { label: '0', value: '0', type: 'number', ariaLabel: 'Number zero' },
    { label: '.', value: '.', type: 'number', ariaLabel: 'Decimal point' },
    { label: isRpn ? 'ENTER' : '=', value: 'equals', type: isRpn ? 'action' : 'equals', ariaLabel: isRpn ? 'Push current value onto stack' : 'Evaluate arithmetic expression' },
    { label: '+', value: '+', type: 'operator', ariaLabel: 'Add operator' },
  ];

  return (
    <div className="calculator-button-grid" role="grid" aria-label="Calculator button keys">
      {buttons.map((btn, index) => {
        const isDisabled = isRpn && btn.disabledInRpn;
        
        const handleClick = () => {
          if (isDisabled) return;
          if (btn.value === 'clear') {
            onClear();
          } else if (btn.value === 'backspace') {
            onBackspace();
          } else if (btn.value === 'equals') {
            onEvaluate();
          } else {
            onKeyPress(btn.value);
          }
        };

        return (
          <button
            key={index}
            type="button"
            className={`calc-btn btn-${btn.type} ${isDisabled ? 'disabled-key' : ''}`}
            onClick={handleClick}
            aria-label={btn.ariaLabel}
            disabled={isDisabled}
          >
            {btn.label}
          </button>
        );
      })}
    </div>
  );
};
