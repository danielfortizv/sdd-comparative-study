import React from 'react';
import { CalculatorButton } from './CalculatorButton';

interface ButtonGridProps {
  appendToken: (token: string) => void;
  clearAll: () => void;
  backspace: () => void;
  evaluateFinal: () => void;
  disableEvaluate: boolean;
}

export const ButtonGrid: React.FC<ButtonGridProps> = ({
  appendToken,
  clearAll,
  backspace,
  evaluateFinal,
  disableEvaluate,
}) => {
  return (
    <div className="button-grid">
      {/* Row 1 */}
      <CalculatorButton label="(" onClick={() => appendToken('(')} ariaLabel="Open parenthesis" variant="command" />
      <CalculatorButton label=")" onClick={() => appendToken(')')} ariaLabel="Close parenthesis" variant="command" />
      <CalculatorButton label="⌫" onClick={backspace} ariaLabel="Backspace" variant="command" />
      <CalculatorButton label="AC" onClick={clearAll} ariaLabel="Clear all" variant="command" />

      {/* Row 2 */}
      <CalculatorButton label="7" onClick={() => appendToken('7')} ariaLabel="Number 7" />
      <CalculatorButton label="8" onClick={() => appendToken('8')} ariaLabel="Number 8" />
      <CalculatorButton label="9" onClick={() => appendToken('9')} ariaLabel="Number 9" />
      <CalculatorButton label="÷" onClick={() => appendToken(' / ')} ariaLabel="Divide" variant="operator" />

      {/* Row 3 */}
      <CalculatorButton label="4" onClick={() => appendToken('4')} ariaLabel="Number 4" />
      <CalculatorButton label="5" onClick={() => appendToken('5')} ariaLabel="Number 5" />
      <CalculatorButton label="6" onClick={() => appendToken('6')} ariaLabel="Number 6" />
      <CalculatorButton label="×" onClick={() => appendToken(' * ')} ariaLabel="Multiply" variant="operator" />

      {/* Row 4 */}
      <CalculatorButton label="1" onClick={() => appendToken('1')} ariaLabel="Number 1" />
      <CalculatorButton label="2" onClick={() => appendToken('2')} ariaLabel="Number 2" />
      <CalculatorButton label="3" onClick={() => appendToken('3')} ariaLabel="Number 3" />
      <CalculatorButton label="-" onClick={() => appendToken(' - ')} ariaLabel="Subtract" variant="operator" />

      {/* Row 5 */}
      <CalculatorButton label="0" onClick={() => appendToken('0')} ariaLabel="Number 0" />
      <CalculatorButton label="." onClick={() => appendToken('.')} ariaLabel="Decimal point" />
      <CalculatorButton label="=" onClick={evaluateFinal} ariaLabel="Calculate result" variant="equals" disabled={disableEvaluate} />
      <CalculatorButton label="+" onClick={() => appendToken(' + ')} ariaLabel="Add" variant="operator" />
    </div>
  );
};
