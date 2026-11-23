import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TransferLimits } from '../components/TransferLimits';
import { TransferLimits as TransferLimitsType } from '../api/types';

const mockLimits: TransferLimitsType = {
  per_transaction_limit: '5000.00',
  daily_limit: '10000.00',
  current_daily_total: '2000.00',
  remaining_daily_limit: '8000.00',
  reference_currency: 'USD',
};

describe('TransferLimits Component', () => {
  it('renders configured transfer limits, used total, remaining balance, and gauge percentage', () => {
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={vi.fn()}
      />
    );

    expect(screen.getByTestId('daily-limit-display')).toHaveTextContent('$10,000.00');
    expect(screen.getByTestId('daily-spent-display')).toHaveTextContent('$2,000.00');
    expect(screen.getByTestId('daily-remaining-display')).toHaveTextContent('$8,000.00');

    // Gauge container title shows exact 20% calculation (2000 / 10000 * 100)
    expect(screen.getByTitle('20% of daily limit used')).toBeInTheDocument();

    const perTxInput = screen.getByTestId('per-tx-limit-input') as HTMLInputElement;
    const dailyInput = screen.getByTestId('daily-limit-input') as HTMLInputElement;

    expect(perTxInput.value).toBe('5000.00');
    expect(dailyInput.value).toBe('10000.00');
  });

  it('validates that per-transaction limit cannot exceed daily limit', async () => {
    const handleUpdate = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={handleUpdate}
      />
    );

    const perTxInput = screen.getByTestId('per-tx-limit-input');
    const dailyInput = screen.getByTestId('daily-limit-input');
    const saveBtn = screen.getByTestId('save-limits-btn');

    // Enter perTx 8000, daily 5000 (invalid)
    fireEvent.change(perTxInput, { target: { value: '8000' } });
    fireEvent.change(dailyInput, { target: { value: '5000' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Per-transaction limit cannot exceed daily limit.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();
  });

  it('allows per-transaction limit to equal daily limit (boundary condition)', async () => {
    const handleUpdate = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={handleUpdate}
      />
    );

    const perTxInput = screen.getByTestId('per-tx-limit-input');
    const dailyInput = screen.getByTestId('daily-limit-input');
    const saveBtn = screen.getByTestId('save-limits-btn');

    // Enter perTx 5000, daily 5000 (valid boundary: perTx == daily)
    fireEvent.change(perTxInput, { target: { value: '5000' } });
    fireEvent.change(dailyInput, { target: { value: '5000' } });
    fireEvent.click(saveBtn);

    expect(handleUpdate).toHaveBeenCalledWith('5000.00', '5000.00');
  });

  it('rejects invalid inputs with excess decimal places', async () => {
    const handleUpdate = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={handleUpdate}
      />
    );

    const perTxInput = screen.getByTestId('per-tx-limit-input');
    const dailyInput = screen.getByTestId('daily-limit-input');
    const saveBtn = screen.getByTestId('save-limits-btn');

    // Invalid perTx decimals
    fireEvent.change(perTxInput, { target: { value: '3000.255' } });
    fireEvent.change(dailyInput, { target: { value: '7000.00' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Per-transaction limit must be a valid positive amount with at most 2 decimal places.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();

    // Invalid daily decimals
    fireEvent.change(perTxInput, { target: { value: '3000.00' } });
    fireEvent.change(dailyInput, { target: { value: '7000.123' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Daily transfer limit must be a valid positive amount with at most 2 decimal places.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();
  });

  it('rejects zero or negative limit values', async () => {
    const handleUpdate = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={handleUpdate}
      />
    );

    const perTxInput = screen.getByTestId('per-tx-limit-input');
    const dailyInput = screen.getByTestId('daily-limit-input');
    const saveBtn = screen.getByTestId('save-limits-btn');

    // Zero perTx
    fireEvent.change(perTxInput, { target: { value: '0.00' } });
    fireEvent.change(dailyInput, { target: { value: '5000.00' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Per-transaction limit must be strictly positive.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();

    // Negative perTx
    fireEvent.change(perTxInput, { target: { value: '-100.00' } });
    fireEvent.change(dailyInput, { target: { value: '5000.00' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Per-transaction limit must be strictly positive.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();

    // Zero daily
    fireEvent.change(perTxInput, { target: { value: '1000.00' } });
    fireEvent.change(dailyInput, { target: { value: '0.00' } });
    fireEvent.click(saveBtn);

    expect(screen.getByTestId('limits-error-message')).toHaveTextContent(
      'Daily transfer limit must be strictly positive.'
    );
    expect(handleUpdate).not.toHaveBeenCalled();
  });

  it('calls onUpdateLimits with canonical decimal strings for valid updated limits', async () => {
    const handleUpdate = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={handleUpdate}
      />
    );

    const perTxInput = screen.getByTestId('per-tx-limit-input');
    const dailyInput = screen.getByTestId('daily-limit-input');
    const saveBtn = screen.getByTestId('save-limits-btn');

    fireEvent.change(perTxInput, { target: { value: '3000' } });
    fireEvent.change(dailyInput, { target: { value: '7000' } });
    fireEvent.click(saveBtn);

    expect(handleUpdate).toHaveBeenCalledWith('3000.00', '7000.00');
  });

  it('handles null limits gracefully', () => {
    render(
      <TransferLimits
        isOpen={true}
        limits={null}
        onClose={vi.fn()}
        onUpdateLimits={vi.fn()}
      />
    );

    expect(screen.queryByTestId('limits-summary-gauge')).not.toBeInTheDocument();
    expect(screen.getByTestId('per-tx-limit-input')).toBeInTheDocument();
    expect(screen.getByTestId('daily-limit-input')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={onClose}
        onUpdateLimits={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });
});
