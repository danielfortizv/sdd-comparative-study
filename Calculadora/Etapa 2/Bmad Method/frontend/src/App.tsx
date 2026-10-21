import React from 'react';
import { CalculatorFrame } from './components/CalculatorFrame';

const App: React.FC = () => {
  return (
    <main style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
      <CalculatorFrame />
    </main>
  );
};

export default App;
