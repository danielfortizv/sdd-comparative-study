import React from 'react';

interface CalculatorButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'operand' | 'operator' | 'command' | 'equals';
  ariaLabel: string;
  disabled?: boolean;
}

export const CalculatorButton: React.FC<CalculatorButtonProps> = ({
  label,
  onClick,
  variant = 'operand',
  ariaLabel,
  disabled = false,
}) => {
  return (
    <button
      className={`calc-button ${variant}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      tabIndex={-1} // Block browser-native Tab focus leakage (WCAG 2.1 AA)
    >
      {label}
    </button>
  );
};
