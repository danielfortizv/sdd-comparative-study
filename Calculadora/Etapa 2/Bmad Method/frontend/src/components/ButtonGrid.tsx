import React from 'react';
import { CalculatorButton } from './CalculatorButton';

interface ButtonGridProps {
  appendToken: (token: string) => void;
  clearAll: () => void;
  backspace: () => void;
  evaluateFinal: () => void;
  disableEvaluate: boolean;
  // Stage 2 Additions
  showScientific: boolean;
  angleUnit: 'radians' | 'degrees';
  toggleAngleUnit: () => void;
  handleMemoryOperation: (op: 'add' | 'subtract') => void;
  clearMemory: () => void;
  recallMemory: () => void;
}

export const ButtonGrid: React.FC<ButtonGridProps> = ({
  appendToken,
  clearAll,
  backspace,
  evaluateFinal,
  disableEvaluate,
  showScientific,
  angleUnit,
  toggleAngleUnit,
  handleMemoryOperation,
  clearMemory,
  recallMemory,
}) => {
  return (
    <div className="keypad-wrapper">
      {/* Scientific Keypad Section - Renders conditionally with an expanded grid */}
      {showScientific && (
        <div className="button-grid scientific-grid" aria-label="Scientific keypad controls">
          {/* Row 1: Memory & Angle Units toggle */}
          <CalculatorButton 
            label={angleUnit === 'radians' ? 'DEG' : 'RAD'} 
            onClick={toggleAngleUnit} 
            ariaLabel={`Switch to ${angleUnit === 'radians' ? 'degrees' : 'radians'}`} 
            variant="command" 
          />
          <CalculatorButton label="MC" onClick={clearMemory} ariaLabel="Clear memory register" variant="command" />
          <CalculatorButton label="MR" onClick={recallMemory} ariaLabel="Recall memory register" variant="command" />
          <CalculatorButton label="M+" onClick={() => handleMemoryOperation('add')} ariaLabel="Add display value to memory" variant="command" />

          {/* Row 2: Memory minus & Primary Trigonometry */}
          <CalculatorButton label="M-" onClick={() => handleMemoryOperation('subtract')} ariaLabel="Subtract display value from memory" variant="command" />
          <CalculatorButton label="sin" onClick={() => appendToken('sin(')} ariaLabel="Sine function" variant="command" />
          <CalculatorButton label="cos" onClick={() => appendToken('cos(')} ariaLabel="Cosine function" variant="command" />
          <CalculatorButton label="tan" onClick={() => appendToken('tan(')} ariaLabel="Tangent function" variant="command" />

          {/* Row 3: Inverse Trigonometry & Constants */}
          <CalculatorButton label="asin" onClick={() => appendToken('asin(')} ariaLabel="Arc sine function" variant="command" />
          <CalculatorButton label="acos" onClick={() => appendToken('acos(')} ariaLabel="Arc cosine function" variant="command" />
          <CalculatorButton label="atan" onClick={() => appendToken('atan(')} ariaLabel="Arc tangent function" variant="command" />
          <CalculatorButton label="π" onClick={() => appendToken('pi')} ariaLabel="Archimedes constant pi" variant="command" />

          {/* Row 4: Constants, Exponents & Roots */}
          <CalculatorButton label="e" onClick={() => appendToken('e')} ariaLabel="Euler constant e" variant="command" />
          <CalculatorButton label="xʸ" onClick={() => appendToken(' ** ')} ariaLabel="Power function" variant="command" />
          <CalculatorButton label="x²" onClick={() => appendToken(' ** 2')} ariaLabel="Squared function" variant="command" />
          <CalculatorButton label="√" onClick={() => appendToken('sqrt(')} ariaLabel="Square root function" variant="command" />

          {/* Row 5: Logarithms & Extra Brackets */}
          <CalculatorButton label="ln" onClick={() => appendToken('ln(')} ariaLabel="Natural logarithm" variant="command" />
          <CalculatorButton label="log" onClick={() => appendToken('log10(')} ariaLabel="Common logarithm base 10" variant="command" />
          <CalculatorButton label="10ˣ" onClick={() => appendToken('10 ** ')} ariaLabel="Ten raised to the power" variant="command" />
          <CalculatorButton label="^" onClick={() => appendToken(' ** ')} ariaLabel="Exponent power operator" variant="command" />
        </div>
      )}

      {/* Standard Basic Core Keypad Section */}
      <div className="button-grid basic-grid" aria-label="Standard arithmetic keypad controls">
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
    </div>
  );
};
