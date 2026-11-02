import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { Calculator } from '../components/Calculator';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

describe('Calculator RPN Mode and Stack Operations', () => {
  beforeEach(() => {
    // Mock the global fetch
    global.fetch = vi.fn().mockImplementation((url, options) => {
      const body = JSON.parse(options.body);
      if (body.expression === "10 20 +") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ expression: '10 20 +', result: '30', stack: ['30'] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ expression: body.expression, result: '42', stack: ['42'] }),
      });
    }) as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('validates toggling standard and RPN modes', () => {
    render(<Calculator />);
    
    // Default is Standard Mode
    expect(screen.getByLabelText('Active calculator mode: standard')).toBeInTheDocument();
    expect(screen.queryByText('Evaluation Stack')).not.toBeInTheDocument();

    // Switch to RPN Mode
    const toggleBtn = screen.getByLabelText('Switch calculator mode. Currently: standard');
    fireEvent.click(toggleBtn);

    expect(screen.getByLabelText('Active calculator mode: rpn')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Stack')).toBeInTheDocument();
    expect(screen.getByTestId('stack-x')).toHaveTextContent('0');

    // Switch back to Standard Mode
    fireEvent.click(screen.getByLabelText('Switch calculator mode. Currently: rpn'));
    expect(screen.getByLabelText('Active calculator mode: standard')).toBeInTheDocument();
    expect(screen.queryByText('Evaluation Stack')).not.toBeInTheDocument();
  });

  test('validates pushing a number onto the RPN evaluation stack', () => {
    render(<Calculator />);
    
    // Switch to RPN Mode
    fireEvent.click(screen.getByLabelText('Switch calculator mode. Currently: standard'));

    // Input "12.5"
    fireEvent.click(screen.getByLabelText('Number one'));
    fireEvent.click(screen.getByLabelText('Number two'));
    fireEvent.click(screen.getByLabelText('Decimal point'));
    fireEvent.click(screen.getByLabelText('Number five'));

    const displayExpression = screen.getByLabelText(/Typed formula expression:/);
    expect(displayExpression).toHaveTextContent('12.5');

    // Press ENTER button (labeled 'ENTER' in RPN)
    fireEvent.click(screen.getByLabelText('Push current value onto stack'));

    // Display should be cleared, and "12.5" should be in stack X (and state stack has ["12.5"])
    expect(displayExpression).toHaveTextContent('0');
    expect(screen.getByTestId('stack-x')).toHaveTextContent('12.5');
  });

  test('validates executing RPN operations via operator buttons', async () => {
    render(<Calculator />);
    
    // Switch to RPN Mode
    fireEvent.click(screen.getByLabelText('Switch calculator mode. Currently: standard'));

    // Push 10
    fireEvent.click(screen.getByLabelText('Number one'));
    fireEvent.click(screen.getByLabelText('Number zero'));
    fireEvent.click(screen.getByLabelText('Push current value onto stack'));

    // Push 20
    fireEvent.click(screen.getByLabelText('Number two'));
    fireEvent.click(screen.getByLabelText('Number zero'));
    fireEvent.click(screen.getByLabelText('Push current value onto stack'));

    expect(screen.getByTestId('stack-x')).toHaveTextContent('20');
    expect(screen.getByTestId('stack-y')).toHaveTextContent('10');

    // Click "+" operator to trigger evaluation
    fireEvent.click(screen.getByLabelText('Add operator'));

    await waitFor(() => {
      expect(screen.getByTestId('stack-x')).toHaveTextContent('30');
      expect(screen.getByText(/Evaluation result is 30/)).toBeInTheDocument();
    });
  });
});
