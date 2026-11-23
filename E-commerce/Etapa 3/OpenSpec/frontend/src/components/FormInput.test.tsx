import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FormInput } from './FormInput';
import '@testing-library/jest-dom';

describe('FormInput Component', () => {
  test('renders input with label and placeholder', () => {
    const handleChange = vi.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Input"
        value=""
        onChange={handleChange}
        placeholder="Enter text..."
      />
    );

    expect(screen.getByLabelText('Test Input')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter text...')).toBeInTheDocument();
  });

  test('calls onChange when typing', () => {
    const handleChange = vi.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Input"
        value=""
        onChange={handleChange}
      />
    );

    const input = screen.getByLabelText('Test Input');
    fireEvent.change(input, { target: { value: 'Hello' } });
    expect(handleChange).toHaveBeenCalledWith('Hello');
  });

  test('renders error message and sets aria-invalid', () => {
    const handleChange = vi.fn();
    render(
      <FormInput
        id="test-input"
        label="Test Input"
        value=""
        onChange={handleChange}
        error="This is an error"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('This is an error');
    expect(screen.getByLabelText('Test Input')).toHaveAttribute('aria-invalid', 'true');
  });
});
