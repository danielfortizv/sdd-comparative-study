import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

describe('Calculator Frontend Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the physical-style scientific calculator with a high-contrast display and history panel', () => {
    render(<App />);
    
    // Check main headings
    expect(screen.getByText('Scientific Web Calculator')).toBeInTheDocument();
    
    // Check key calculator screen region
    const screenRegion = screen.getByRole('region', { name: 'Calculator screen' });
    expect(screenRegion).toBeInTheDocument();
    
    // Check default display state (starts with 0)
    expect(screen.getByLabelText('Calculation result')).toHaveTextContent('0');
    
    // Check key control and operator buttons
    expect(screen.getByRole('button', { name: 'Clear calculator' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Evaluate expression' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Divide' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Multiply' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Subtract' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument();

    // Check newly introduced scientific & memory buttons
    expect(screen.getByRole('button', { name: 'Sine function' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cosine function' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tangent function' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Power operator' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Constant Pi' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Constant e' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear Memory register' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Recall Memory register' })).toBeInTheDocument();

    // Check history drawer heading
    expect(screen.getByText('Session History')).toBeInTheDocument();
  });

  it('handles button clicks to append values and clear them', () => {
    render(<App />);
    
    const btn1 = screen.getByRole('button', { name: '1' });
    const btn2 = screen.getByRole('button', { name: '2' });
    const btnPlus = screen.getByRole('button', { name: 'Add' });
    const clearBtn = screen.getByRole('button', { name: 'Clear calculator' });
    
    // Type "1+2"
    fireEvent.click(btn1);
    fireEvent.click(btnPlus);
    fireEvent.click(btn2);
    
    // The expression display should show "1+2"
    expect(screen.getByText('1+2')).toBeInTheDocument();
    
    // Click Backspace
    const backspaceBtn = screen.getByRole('button', { name: 'Backspace' });
    fireEvent.click(backspaceBtn);
    expect(screen.getByText('1+')).toBeInTheDocument();
    
    // Click Clear
    fireEvent.click(clearBtn);
    expect(screen.queryByText('1+')).not.toBeInTheDocument();
  });

  it('calls the evaluate API and displays the result on success', async () => {
    const mockResponse = { result: 16.25 };
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<App />);
    
    // Type "12.5+3"
    fireEvent.click(screen.getByRole('button', { name: '1' }));
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: '.' }));
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    
    // Click Evaluate
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));
    
    // Verify loading state is shown
    expect(screen.getByText('Evaluating...')).toBeInTheDocument();
    
    // Verify result is displayed
    await waitFor(() => {
      expect(screen.getByText('16.25')).toBeInTheDocument();
    });
    
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: '12.5+3', angle_unit: 'radians' }),
      })
    );
  });

  it('displays user-friendly error messages on API error', async () => {
    const mockErrorDetail = {
      detail: {
        type: 'math error',
        message: 'Division by zero is not allowed',
      },
    };
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      json: async () => mockErrorDetail,
    } as Response);

    render(<App />);
    
    // Type "5/0"
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Divide' }));
    fireEvent.click(screen.getByRole('button', { name: '0' }));
    
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));
    
    await waitFor(() => {
      expect(screen.getByText('Division by zero is not allowed')).toBeInTheDocument();
    });
  });

  it('supports full keyboard event mappings', async () => {
    const mockResponse = { result: 8 };
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<App />);
    
    // Trigger keyboard down events for '5', '+', '3', and 'Enter'
    fireEvent.keyDown(window, { key: '5' });
    fireEvent.keyDown(window, { key: '+' });
    fireEvent.keyDown(window, { key: '3' });
    
    expect(screen.getByText('5+3')).toBeInTheDocument();
    
    fireEvent.keyDown(window, { key: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('8')).toBeInTheDocument();
    });
    
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  // ==========================================
  // STAGE 2 FRONTEND COMPONENT TESTS
  // ==========================================

  it('supports toggling the angle unit and updates the query parameters', async () => {
    const mockResponse = { result: 1 };
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<App />);

    // Default angle unit badge
    expect(screen.getByLabelText('Current angle mode badge')).toHaveTextContent('Rad');

    // Click the Deg toggle button
    const toggleBtn = screen.getByRole('button', { name: 'Switch to Degrees angle unit' });
    fireEvent.click(toggleBtn);

    // Badge should update to Deg
    expect(screen.getByLabelText('Current angle mode badge')).toHaveTextContent('Deg');

    // Perform an evaluation and assert Degrees is transmitted
    fireEvent.click(screen.getByRole('button', { name: 'Sine function' }));
    fireEvent.click(screen.getByRole('button', { name: '9' }));
    fireEvent.click(screen.getByRole('button', { name: '0' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close parenthesis' }));
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ operation: 'sin(90)', angle_unit: 'degrees' }),
      })
    );
  });

  it('implements the Memory Register system and shows the memory badge', async () => {
    render(<App />);

    // Starts with no memory badge
    expect(screen.queryByLabelText('Memory is not empty badge')).not.toBeInTheDocument();

    // Set a simple number in expression and click M+
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '2' }));

    // Mock successful eval for memory operations
    const mockResponse = { result: 7 };
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    fireEvent.click(screen.getByRole('button', { name: 'Add display to memory' }));

    await waitFor(() => {
      // Memory badge should appear
      expect(screen.getByLabelText('Memory is not empty badge')).toBeInTheDocument();
    });

    // Clear display
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));

    // Recall memory should append '7' to the display
    fireEvent.click(screen.getByRole('button', { name: 'Recall Memory register' }));
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('7');

    // Clear memory
    fireEvent.click(screen.getByRole('button', { name: 'Clear Memory register' }));
    expect(screen.queryByLabelText('Memory is not empty badge')).not.toBeInTheDocument();
  });

  it('records successful evaluations in session history and allows reloading', async () => {
    const mockResponse = { result: 0.5 };
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<App />);

    // Type "sin(pi/6)"
    fireEvent.click(screen.getByRole('button', { name: 'Sine function' }));
    fireEvent.click(screen.getByRole('button', { name: 'Constant Pi' }));
    fireEvent.click(screen.getByRole('button', { name: 'Divide' }));
    fireEvent.click(screen.getByRole('button', { name: '6' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close parenthesis' }));
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));

    await waitFor(() => {
      expect(screen.getByText('0.5')).toBeInTheDocument();
    });

    // The session history panel should display the item
    expect(screen.getByRole('button', { name: 'Load historical expression: sin(pi/6)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Append historical result: 0.5' })).toBeInTheDocument();

    // Clear calculator display - the display should be blank/empty
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('');

    // Click historical expression to reload it
    fireEvent.click(screen.getByRole('button', { name: 'Load historical expression: sin(pi/6)' }));
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('sin(pi/6)');
  });

  it('handles advanced memory operations including M- and single number memory add', async () => {
    render(<App />);

    // 1. M+ with a single number (should not trigger API fetch)
    fireEvent.click(screen.getByRole('button', { name: '9' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add display to memory' }));
    
    // Memory badge should appear, meaning memory is now 9
    expect(screen.getByLabelText('Memory is not empty badge')).toBeInTheDocument();
    
    // Clear calculator
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));

    // 2. M- with an unevaluated expression (triggers API fetch)
    fireEvent.click(screen.getByRole('button', { name: '4' }));
    fireEvent.click(screen.getByRole('button', { name: 'Subtract' }));
    fireEvent.click(screen.getByRole('button', { name: '1' })); // "4-1" -> evaluates to 3

    const mockResponse = { result: 3 };
    const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    fireEvent.click(screen.getByRole('button', { name: 'Subtract display from memory' }));

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    // Memory is 9 - 3 = 6. Recall memory to check it's 6
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));
    fireEvent.click(screen.getByRole('button', { name: 'Recall Memory register' }));
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('6');

    // 3. M+ or M- on empty expression (should do nothing)
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));
    fetchSpy.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'Add display to memory' }));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('handles clicking historical results and clearing history', async () => {
    const mockResponse = { result: 0.5 };
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    render(<App />);

    // Add something to history
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));

    await waitFor(() => {
      expect(screen.getByText('0.5')).toBeInTheDocument();
    });

    // We have "Append historical result: 0.5" in document. Let's append it
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculator' }));
    fireEvent.click(screen.getByRole('button', { name: '1' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: 'Append historical result: 0.5' }));

    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('1+0.5');

    // Clear history drawer
    fireEvent.click(screen.getByRole('button', { name: 'Clear calculations history' }));
    expect(screen.queryByRole('button', { name: 'Clear calculations history' })).not.toBeInTheDocument();
  });

  it('handles advanced keyboard shortcuts for Backspace, Escape, and p key', () => {
    render(<App />);

    // Press 'p' to input 'pi'
    fireEvent.keyDown(window, { key: 'p' });
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('pi');

    // Press Backspace
    fireEvent.keyDown(window, { key: 'Backspace' });
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('p');

    // Press Escape
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.getByLabelText('Arithmetic expression')).toHaveTextContent('');
  });

  it('handles API errors in memory operations gracefully', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: {
          type: 'error',
          message: 'Failed to evaluate for memory add',
        }
      }),
    } as Response);

    render(<App />);

    // Add complex expression and click M+
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add display to memory' }));

    await waitFor(() => {
      expect(screen.getByText('Failed to evaluate for memory add')).toBeInTheDocument();
    });
    
    // Same for M-
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: {
          type: 'error',
          message: 'Failed to evaluate for memory subtract',
        }
      }),
    } as Response);

    fireEvent.click(screen.getByRole('button', { name: 'Subtract display from memory' }));

    await waitFor(() => {
      expect(screen.getByText('Failed to evaluate for memory subtract')).toBeInTheDocument();
    });
  });

  it('handles unexpected json parsing errors in API responses', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      json: async () => { throw new Error('Bad JSON'); },
    } as Response);

    render(<App />);

    // Evaluate
    fireEvent.click(screen.getByRole('button', { name: '5' }));
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate expression' }));

    await waitFor(() => {
      expect(screen.getByText('Failed to evaluate expression')).toBeInTheDocument();
    });
  });
});
