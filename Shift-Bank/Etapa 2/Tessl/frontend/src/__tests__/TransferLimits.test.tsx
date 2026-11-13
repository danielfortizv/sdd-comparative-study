import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TransferLimits } from '../components/TransferLimits';
import { TransferLimits as TransferLimitsType } from '../api/types';

const mockLimits: TransferLimitsType = {
  per_transaction_limit: 5000.0,
  daily_limit: 10000.0,
  current_daily_total: 2000.0,
  remaining_daily_limit: 8000.0,
};

describe('TransferLimits Component', () => {
  it('renders configured transfer limits, used total, and remaining balance', () => {
    render(
      <TransferLimits
        isOpen={true}
        limits={mockLimits}
        onClose={vi.fn()}
        onUpdateLimits={vi.fn()}
      />
    );

    expect(screen.getByTestId('daily-limit-display')).toHaveTextContent('$10000.00');
    expect(screen.getByTestId('daily-spent-display')).toHaveTextContent('$2000.00');
    expect(screen.getByTestId('daily-remaining-display')).toHaveTextContent('$8000.00');

    const perTxInput = screen.getByTestId('per-tx-limit-input') as HTMLInputElement;
    const dailyInput = screen.getByTestId('daily-limit-input') as HTMLInputElement;

    expect(perTxInput.value).toBe('5000');
    expect(dailyInput.value).toBe('10000');
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
      'Per-transaction limit cannot exceed daily limit'
    );
    expect(handleUpdate).not.toHaveBeenCalled();
  });

  it('calls onUpdateLimits with valid updated limits', async () => {
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

    expect(handleUpdate).toHaveBeenCalledWith(3000, 7000);
  });
});
