import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import React from 'react';

describe('Calculator Frontend Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the physical-style calculator with a high-contrast display', () => {
    render(<App />);
    
    // Check main headings
    expect(screen.getByText('High-Precision Calculator')).toBeInTheDocument();
    
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
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
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
        body: JSON.stringify({ operation: '12.5+3' }),
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
    vi.spyOn(global, 'fetch').mockResolvedValue({
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
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
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
});
