import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Setup global fetch mock
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((_url, options) => {
    let bodyObj = { expression: '', angle_unit: 'radians' };
    if (options && options.body) {
      try {
        bodyObj = JSON.parse(options.body);
      } catch (e) {
        // ignore
      }
    }
    
    const expr = bodyObj.expression.trim();
    let result = "0";
    let ok = true;
    let detail = "";

    if (expr === "TRIGGER_REJECT") {
      return Promise.reject(new Error("Network connection failure"));
    }
    else if (expr === "2+3" || expr === "2 + 3") result = "5";
    else if (expr === "5") result = "5";
    else if (expr === "5*2" || expr === "5 * 2") result = "10";
    else if (expr === "10") result = "10";
    else if (expr === "10/0" || expr === "10 / 0" || expr === "10/(2-2)") { 
      ok = false; 
      detail = "Division by zero"; 
    }
    else if (expr === "sin(pi/2)") result = "1";
    else if (expr === "sin(90)") result = "1";
    else if (expr === "5+5" || expr === "5 + 5") result = "10";
    else if (expr === "2**4") result = "16";
    else result = expr || "0";

    if (ok) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ expression: expr, result }),
      });
    } else {
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail }),
      });
    }
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Web Calculator Frontend tests', () => {
  it('renders standard layout elements correctly', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: 'Clear all' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Left parenthesis' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Right parenthesis' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Backspace' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Equal/Evaluate' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('0');
    expect(screen.getByLabelText(/Result/)).toHaveTextContent('0');
  });

  it('handles standard keypad click interactions', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '3' }));

    const exprLine = screen.getByLabelText(/Current expression/);
    expect(exprLine).toHaveTextContent('2+3');

    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('5');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('5');
    });
  });

  it('supports clear (C) and backspace actions', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Multiply' }));
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5*2');
    
    fireEvent.click(screen.getByRole('button', { name: 'Backspace' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5*');

    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('0');
    expect(screen.getByLabelText(/Result/)).toHaveTextContent('0');
  });

  it('performs memory operations MC, MR, M+, M- and renders badge', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '1' }));
    fireEvent.click(screen.getByRole('button', { name: '0' }));
    fireEvent.click(screen.getByRole('button', { name: 'Memory add (M+)' }));
    expect(screen.getByText('M')).toBeInTheDocument();
    
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    fireEvent.click(screen.getByRole('button', { name: 'Memory recall (MR)' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('10');

    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Memory subtract (M-)' }));

    fireEvent.click(screen.getByRole('button', { name: 'Memory clear (MC)' }));
    expect(screen.queryByText('M')).not.toBeInTheDocument();
  });

  it('supports scientific layout view and angle unit toggle', () => {
    render(<App />);
    const scientificToggleBtn = screen.getByRole('button', { name: 'Toggle scientific keys' });
    fireEvent.click(scientificToggleBtn);

    expect(screen.getByRole('button', { name: 'Sine' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cosine' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Square root' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'N-th root' })).toBeInTheDocument();
    
    const angleToggleBtn = screen.getByLabelText(/Angle unit/);
    expect(angleToggleBtn).toHaveTextContent('RADIANS');
    
    fireEvent.click(angleToggleBtn);
    expect(angleToggleBtn).toHaveTextContent('DEGREES');
  });

  it('maps physical keyboard entries successfully', async () => {
    render(<App />);
    fireEvent.keyDown(window, { key: '5' });
    fireEvent.keyDown(window, { key: '+' });
    fireEvent.keyDown(window, { key: '5' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5+5');
    
    fireEvent.keyDown(window, { key: 'Enter' });
    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('10');
    });

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('0');
  });

  it('supports calculation session history panel operations', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));
    
    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('10');
    });

    const historyBtn = screen.getByRole('button', { name: 'Toggle history panel' });
    fireEvent.click(historyBtn);
    
    expect(screen.getByText('Historial de Sesión')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cargar expresión: 5+5' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cargar resultado: 10' })).toBeInTheDocument();
    
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cargar expresión: 5+5' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5+5');

    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cargar resultado: 10' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('10');

    fireEvent.click(screen.getByRole('button', { name: 'Limpiar todo el historial' }));
    expect(screen.getByText('No hay cálculos en esta sesión.')).toBeInTheDocument();
  });

  // ----------------------------------------------------
  // New Stage 3 Branch Coverage Tests
  // ----------------------------------------------------

  it('handles backend network connection failures gracefully', async () => {
    // Override fetch mock to reject for this specific test
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('Network connection failure')));

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    
    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Error:/)).toHaveTextContent('Server connection error');
    });
  });

  it('correctly handles division by zero and displays error messages on evaluation', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '1' }));
    fireEvent.click(screen.getByRole('button', { name: '0' }));
    fireEvent.click(screen.getByRole('button', { name: 'Divide' }));
    fireEvent.click(screen.getByRole('button', { name: '0' }));
    
    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Error:/)).toHaveTextContent('Division by zero');
    });
  });

  it('appends operator on top of a final result', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('5');
    });

    // Press '*' while showing final result - should append operator to result
    fireEvent.click(screen.getByRole('button', { name: 'Multiply' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5*');
  });

  it('deletes entire multicharacter words using backspace', () => {
    render(<App />);
    const scientificToggleBtn = screen.getByRole('button', { name: 'Toggle scientific keys' });
    fireEvent.click(scientificToggleBtn);

    // Type sin(
    fireEvent.click(screen.getByRole('button', { name: 'Sine' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('sin(');

    // Backspace once - should delete "sin(" entirely
    fireEvent.click(screen.getByRole('button', { name: 'Backspace' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('0');

    // Type pi
    fireEvent.click(screen.getByRole('button', { name: 'Pi constant' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('pi');

    // Backspace once - should delete "pi" entirely
    fireEvent.click(screen.getByRole('button', { name: 'Backspace' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('0');
  });

  it('supports all physical key listener mappings', () => {
    render(<App />);
    
    // test '^' for '**'
    fireEvent.keyDown(window, { key: '^' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('**');

    // test ',' for ','
    fireEvent.keyDown(window, { key: ',' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('**,');

    // test 'p' for 'pi'
    fireEvent.keyDown(window, { key: 'p' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('**,pi');

    // backspace key down
    fireEvent.keyDown(window, { key: 'Backspace' });
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('**,');
  });

  it('recalls memory directly on top of final result', async () => {
    render(<App />);
    // setup memory
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Memory add (M+)' }));

    // evaluate some calc
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    fireEvent.click(screen.getByRole('button', { name: 'Equal/Evaluate' }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Result/)).toHaveTextContent('5');
    });

    // Press MR directly - should clear final result state and load 5
    fireEvent.click(screen.getByRole('button', { name: 'Memory recall (MR)' }));
    expect(screen.getByLabelText(/Current expression/)).toHaveTextContent('5');
  });
});
