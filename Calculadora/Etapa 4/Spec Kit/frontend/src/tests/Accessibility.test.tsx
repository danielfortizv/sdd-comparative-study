import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { Calculator } from '../components/Calculator';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

// ARIA Accessibility Verification Tests
describe('Calculator Screen Reader Accessibility', () => {
  beforeEach(() => {
    // Mock fetch for keydown trigger calls to evaluate
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ expression: '2+3', result: '5' }),
      })
    ) as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('verifies ARIA polite live announcement updates on results', async () => {
    render(<Calculator />);
    
    // Check polite live announcement elements exist
    const displayResult = document.getElementById('display-result');
    expect(displayResult).toBeInTheDocument();
    expect(displayResult?.getAttribute('aria-live')).toBe('polite');

    // Trigger evaluate
    fireEvent.click(screen.getByLabelText('Number two'));
    fireEvent.click(screen.getByLabelText('Add operator'));
    fireEvent.click(screen.getByLabelText('Number three'));
    fireEvent.click(screen.getByLabelText('Evaluate arithmetic expression'));

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });

  test('verifies each button contains a descriptive aria-label', () => {
    render(<Calculator />);
    
    // Check that important buttons have rich accessible descriptions
    expect(screen.getByLabelText('Number seven')).toBeInTheDocument();
    expect(screen.getByLabelText('Divide operator')).toBeInTheDocument();
    expect(screen.getByLabelText('Clear all entries and reset calculator')).toBeInTheDocument();
    expect(screen.getByLabelText('Evaluate arithmetic expression')).toBeInTheDocument();
  });

  test('verifies keyboard keydown events', () => {
    render(<Calculator />);
    const displayExpression = screen.getByLabelText(/Typed formula expression:/);

    // Number keys
    fireEvent.keyDown(document, { key: '1' });
    fireEvent.keyDown(document, { key: '2' });
    expect(displayExpression).toHaveTextContent('12');

    // Operator keys
    fireEvent.keyDown(document, { key: '+' });
    expect(displayExpression).toHaveTextContent('12+');

    // Constant p -> pi
    fireEvent.keyDown(document, { key: 'p' });
    expect(displayExpression).toHaveTextContent('12+pi');

    // Parentheses
    fireEvent.keyDown(document, { key: '(' });
    expect(displayExpression).toHaveTextContent('12+pi(');

    // Decimal
    fireEvent.keyDown(document, { key: '.' });
    expect(displayExpression).toHaveTextContent('12+pi(.');

    // Backspace
    fireEvent.keyDown(document, { key: 'Backspace' });
    expect(displayExpression).toHaveTextContent('12+pi(');

    // Escape (Reset)
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(displayExpression).toHaveTextContent('0');
  });

  test('verifies keyboard equals and enter trigger handleEvaluate', async () => {
    render(<Calculator />);
    
    fireEvent.keyDown(document, { key: '2' });
    fireEvent.keyDown(document, { key: '+' });
    fireEvent.keyDown(document, { key: '3' });
    
    // Press Enter to evaluate
    fireEvent.keyDown(document, { key: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });
});
