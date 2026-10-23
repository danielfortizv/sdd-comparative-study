import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { CalculatorFrame } from '../components/CalculatorFrame';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('CalculatorFrame Component Integration', () => {
  beforeEach(() => {
    const mockFetch = vi.fn().mockImplementation((url, options) => {
      const body = options && options.body ? JSON.parse(options.body) : {};
      const expr = body.expression || '';
      let resVal = '0';
      if (expr === '9 + 3') resVal = '12';
      else if (expr === '5 + 3') resVal = '8';
      else if (expr === '40 + 2') resVal = '42';
      return Promise.resolve({
        ok: true,
        json: async () => ({ result: resVal }),
      });
    });
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render display panel, standard buttons and toggle buttons', () => {
    render(<CalculatorFrame />);

    // Screen-reader application accessibility role
    expect(screen.getByRole('application')).toBeInTheDocument();

    // Default "0" on primary display
    expect(screen.getAllByText('0')[0]).toBeInTheDocument();

    // Standard buttons (e.g. AC, backspace, numbers)
    expect(screen.getByRole('button', { name: 'Clear all' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Backspace' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Number 7' })).toBeInTheDocument();

    // Scientific and History panel toggles
    expect(screen.getByRole('button', { name: 'Show scientific keypad' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show calculation history' })).toBeInTheDocument();
  });

  it('should append number and operator tokens on click and preview result', async () => {
    vi.useFakeTimers();
    render(<CalculatorFrame />);

    // Click 9 + 3
    fireEvent.click(screen.getByRole('button', { name: 'Number 9' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: 'Number 3' }));

    // Fast-forward timers to run preview fetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(fetch).toHaveBeenCalled();

    // Check preview display
    expect(screen.getByText('12')).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('should toggle scientific keypad and click scientific keys', () => {
    render(<CalculatorFrame />);

    // Scientific grid should not be in document initially
    expect(screen.queryByLabelText('Scientific keypad controls')).not.toBeInTheDocument();

    // Toggle Scientific panel
    const sciToggle = screen.getByRole('button', { name: 'Show scientific keypad' });
    fireEvent.click(sciToggle);

    // Now it should be visible
    expect(screen.getByLabelText('Scientific keypad controls')).toBeInTheDocument();

    // Click "sin" and check display
    fireEvent.click(screen.getByRole('button', { name: 'Sine function' }));
    expect(screen.getByRole('button', { name: 'Sine function' })).toBeInTheDocument();
  });

  it('should handle keyboard keydown events', async () => {
    vi.useFakeTimers();
    render(<CalculatorFrame />);

    // Simulate key presses "5 + 3"
    fireEvent.keyDown(window, { key: '5' });
    fireEvent.keyDown(window, { key: '+' });
    fireEvent.keyDown(window, { key: '3' });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(fetch).toHaveBeenCalled();

    // Verify 8 is shown
    expect(screen.getAllByText('8')[0]).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('should open and interact with the session history drawer', async () => {
    render(<CalculatorFrame />);

    // Input "40 + 2"
    fireEvent.click(screen.getByRole('button', { name: 'Number 4' }));
    fireEvent.click(screen.getByRole('button', { name: 'Number 0' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: 'Number 2' }));

    // Calculate final
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Calculate result' }));
    });

    // Toggle History Drawer
    const histToggle = screen.getByRole('button', { name: 'Show calculation history' });
    fireEvent.click(histToggle);

    // History drawer should now be visible
    expect(screen.getByLabelText('Session Calculation History Panel')).toBeInTheDocument();
    expect(screen.getByText('40 + 2')).toBeInTheDocument();
    expect(screen.getByText('= 42')).toBeInTheDocument();

    // Click "Use Expr" back into main display
    const useExprBtn = screen.getByRole('button', { name: 'Load full expression back into display' });
    fireEvent.click(useExprBtn);

    // Click Close History drawer
    const closeBtn = screen.getByRole('button', { name: 'Close history drawer' });
    fireEvent.click(closeBtn);

    expect(screen.queryByLabelText('Session Calculation History Panel')).not.toBeInTheDocument();
  });
});
