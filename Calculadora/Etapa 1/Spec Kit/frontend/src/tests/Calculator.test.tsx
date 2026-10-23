import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { Calculator } from '../components/Calculator';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

// Document-level React Event Verification Tests
describe('Calculator Key Events and Mouse Clicks', () => {
  beforeEach(() => {
    // Mock the global fetch
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ expression: '0.1 + 0.2', result: '0.3' }),
      })
    ) as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('renders desktop calculator title and display fields', () => {
    render(<Calculator />);
    expect(screen.getByText('Scientific Calculator')).toBeInTheDocument();
    expect(screen.getByLabelText('Calculator screen display')).toBeInTheDocument();
  });

  test('validates clicking standard numeric buttons', () => {
    render(<Calculator />);
    
    // Click numbers
    fireEvent.click(screen.getByLabelText('Number seven'));
    fireEvent.click(screen.getByLabelText('Number eight'));
    fireEvent.click(screen.getByLabelText('Number nine'));
    
    const displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('789');
  });

  test('validates decimal checks', () => {
    render(<Calculator />);
    
    fireEvent.click(screen.getByLabelText('Number one'));
    fireEvent.click(screen.getByLabelText('Decimal point'));
    fireEvent.click(screen.getByLabelText('Number two'));
    fireEvent.click(screen.getByLabelText('Decimal point')); // Should be ignored
    fireEvent.click(screen.getByLabelText('Number three'));
    
    const displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('1.23');
  });

  test('validates operators, clear, and backspace click actions', () => {
    render(<Calculator />);
    
    // Add numbers and operator
    fireEvent.click(screen.getByLabelText('Number five'));
    fireEvent.click(screen.getByLabelText('Add operator'));
    fireEvent.click(screen.getByLabelText('Number six'));
    
    let displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('5+6');
    
    // Backspace
    fireEvent.click(screen.getByLabelText('Delete last character'));
    expect(displayExpression).toHaveTextContent('5+');
    
    // Clear AC
    fireEvent.click(screen.getByLabelText('Clear all entries and reset calculator'));
    expect(displayExpression).toHaveTextContent('0');
  });

  test('validates memory state operations', () => {
    render(<Calculator />);
    
    // Memory recall empty memory
    fireEvent.click(screen.getByLabelText('Memory recall: Insert stored memory value into formula'));
    let displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('0'); // appends memoryRegister "0"

    // Simulate result being "10" then add to memory
    fireEvent.click(screen.getByLabelText('Number five'));
    fireEvent.click(screen.getByLabelText('Evaluate arithmetic expression'));
    
    // Wait for mock fetch response (result: '0.3')
    waitFor(() => {
      expect(screen.getByText('0.3')).toBeInTheDocument();
    });

    // Add to memory
    fireEvent.click(screen.getByLabelText('Memory plus: Add current displayed result to memory'));
    
    // Subtract from memory
    fireEvent.click(screen.getByLabelText('Memory minus: Subtract current displayed result from memory'));

    // Clear memory
    fireEvent.click(screen.getByLabelText('Memory clear: Reset memory register value back to zero'));
  });

  test('validates scientific constant clicks and scientific toggles', () => {
    render(<Calculator />);
    
    // Constant Pi
    fireEvent.click(screen.getByLabelText('Mathematical constant Pi'));
    // Constant Euler e
    fireEvent.click(screen.getByLabelText('Euler constant e'));

    const displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('pie');

    // Toggle Scientific keys panel
    const sciToggleBtn = screen.getByLabelText('Toggle scientific mathematical operations keyboard panel');
    fireEvent.click(sciToggleBtn); // hide
    expect(screen.queryByLabelText('Scientific keys keypad')).not.toBeInTheDocument();
    fireEvent.click(sciToggleBtn); // show
    expect(screen.getByLabelText('Scientific keys keypad')).toBeInTheDocument();
  });

  test('validates scientific function inputs', () => {
    render(<Calculator />);
    
    fireEvent.click(screen.getByLabelText('Square root'));
    fireEvent.click(screen.getByLabelText('Natural logarithm'));
    fireEvent.click(screen.getByLabelText('Sine function'));

    const displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('sqrt(ln(sin(');
  });

  test('validates angle measurement toggles', () => {
    render(<Calculator />);
    
    const angleToggleBtn = screen.getByLabelText(/Toggle angle measurement unit/);
    expect(screen.getByLabelText('Angle mode: radians')).toBeInTheDocument();
    
    fireEvent.click(angleToggleBtn);
    expect(screen.getByLabelText('Angle mode: degrees')).toBeInTheDocument();
    
    fireEvent.click(angleToggleBtn);
    expect(screen.getByLabelText('Angle mode: radians')).toBeInTheDocument();
  });

  test('validates history side drawer state and recall operations', async () => {
    render(<Calculator />);
    
    const historyToggleBtn = screen.getByLabelText('Toggle calculation history panel');
    fireEvent.click(historyToggleBtn); // Open history drawer
    
    expect(screen.getByText('No previous calculations in this session.')).toBeInTheDocument();

    // Trigger evaluate to populate history
    fireEvent.click(screen.getByLabelText('Number five'));
    fireEvent.click(screen.getByLabelText('Evaluate arithmetic expression'));

    await waitFor(() => {
      expect(screen.getByText('0.3')).toBeInTheDocument();
    });

    // Verify item in history list using query selectors to avoid text conflicts
    const historyExpr = document.querySelector('.history-item-expr');
    const historyRes = document.querySelector('.history-item-res');
    expect(historyExpr).toHaveTextContent('5');
    expect(historyRes).toHaveTextContent('= 0.3');

    // Click on history expression to load it
    fireEvent.click(historyExpr!);
    expect(screen.getByLabelText(/Typed formula expression:/)).toHaveTextContent('5');

    // Click on history result to load it
    fireEvent.click(historyRes!);
    expect(screen.getByLabelText(/Typed formula expression:/)).toHaveTextContent('0.3');

    // Clear history
    fireEvent.click(screen.getByLabelText('Clear all session calculation history entries'));
    expect(screen.getByText('No previous calculations in this session.')).toBeInTheDocument();
  });

  test('handles API evaluation errors gracefully', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: 'DOMAIN_ERROR', details: 'Trigonometric domain error.' }),
      })
    ) as any;

    render(<Calculator />);
    
    fireEvent.click(screen.getByLabelText('Number nine'));
    fireEvent.click(screen.getByLabelText('Evaluate arithmetic expression'));

    await waitFor(() => {
      expect(screen.getByText('Trigonometric domain error.')).toBeInTheDocument();
    });
  });

  test('handles API general network error gracefully', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.reject(new Error('Network failure'))
    ) as any;

    render(<Calculator />);
    
    fireEvent.click(screen.getByLabelText('Number nine'));
    fireEvent.click(screen.getByLabelText('Evaluate arithmetic expression'));

    await waitFor(() => {
      expect(screen.getByText('Network failure')).toBeInTheDocument();
    });
  });
});
