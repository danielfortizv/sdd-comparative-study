import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TransferForm, parseAmountToCents, formatCentsToUsd } from '../components/TransferForm';
import { Account } from '../types/account';

const mockAccounts: Account[] = [
  {
    id: 'CHK-1001',
    nickname: 'Primary Checking',
    type: 'CHECKING',
    account_type: 'CHECKING',
    balance_cents: 250000,
    balance_formatted: '$2,500.00',
  },
  {
    id: 'SAV-2001',
    nickname: 'High-Yield Savings',
    type: 'SAVINGS',
    account_type: 'SAVINGS',
    balance_cents: 1245075,
    balance_formatted: '$12,450.75',
  },
  {
    id: 'RSV-3001',
    nickname: 'Emergency Reserve',
    type: 'RESERVE',
    account_type: 'RESERVE',
    balance_cents: 500000,
    balance_formatted: '$5,000.00',
  },
];

describe('TransferForm Helper Functions', () => {
  it('parses decimal string to exact integer cents without float drift', () => {
    expect(parseAmountToCents('')).toBe(0);
    expect(parseAmountToCents('0.01')).toBe(1);
    expect(parseAmountToCents('0.5')).toBe(50);
    expect(parseAmountToCents('10.25')).toBe(1025);
    expect(parseAmountToCents('250')).toBe(25000);
    expect(parseAmountToCents('1000.00')).toBe(100000);
    expect(parseAmountToCents('1500.50')).toBe(150050);
  });

  it('formats cents to formatted USD string', () => {
    expect(formatCentsToUsd(1)).toBe('$0.01');
    expect(formatCentsToUsd(100)).toBe('$1.00');
    expect(formatCentsToUsd(25000)).toBe('$250.00');
    expect(formatCentsToUsd(100000)).toBe('$1,000.00');
    expect(formatCentsToUsd(150050)).toBe('$1,500.50');
  });
});

describe('Story 2.1 Acceptance Criteria: TransferForm Component', () => {
  it('AC-1: dynamically excludes the selected Source Account from Destination dropdown', () => {
    render(<TransferForm accounts={mockAccounts} defaultSourceAccountId="CHK-1001" />);

    const sourceSelect = screen.getByTestId('transfer-source-select') as HTMLSelectElement;
    const destSelect = screen.getByTestId('transfer-destination-select') as HTMLSelectElement;

    // Initially Source is Checking
    expect(sourceSelect.value).toBe('CHK-1001');

    // Destination options must contain Savings and Reserve, but NOT Checking
    const destOptions = Array.from(destSelect.options).map((o) => o.value);
    expect(destOptions).toContain('SAV-2001');
    expect(destOptions).toContain('RSV-3001');
    expect(destOptions).not.toContain('CHK-1001');

    // Switch Source to High-Yield Savings
    fireEvent.change(sourceSelect, { target: { value: 'SAV-2001' } });
    expect(sourceSelect.value).toBe('SAV-2001');

    // Destination options must now contain Checking and Reserve, but NOT Savings
    const updatedDestOptions = Array.from(destSelect.options).map((o) => o.value);
    expect(updatedDestOptions).toContain('CHK-1001');
    expect(updatedDestOptions).toContain('RSV-3001');
    expect(updatedDestOptions).not.toContain('SAV-2001');
  });

  it('AC-2: restricts amount input to positive numbers with up to 2 decimal places', () => {
    render(<TransferForm accounts={mockAccounts} defaultSourceAccountId="CHK-1001" />);

    const amountInput = screen.getByTestId('transfer-amount-input') as HTMLInputElement;

    // Valid positive 2-decimal input
    fireEvent.change(amountInput, { target: { value: '250.50' } });
    expect(amountInput.value).toBe('250.50');

    // Invalid non-numeric input should be rejected
    fireEvent.change(amountInput, { target: { value: 'abc' } });
    expect(amountInput.value).toBe('250.50'); // Retains previous valid value

    // 3 decimal places input should be rejected
    fireEvent.change(amountInput, { target: { value: '250.555' } });
    expect(amountInput.value).toBe('250.50');
  });

  it('AC-3: displays inline warning and disables submit when amount exceeds source balance', () => {
    render(<TransferForm accounts={mockAccounts} defaultSourceAccountId="CHK-1001" />);

    const amountInput = screen.getByTestId('transfer-amount-input');
    const submitBtn = screen.getByTestId('transfer-submit-btn');

    // Primary Checking has $2,500.00. Enter $3,500.00
    fireEvent.change(amountInput, { target: { value: '3500.00' } });

    // Must show inline insufficient funds warning
    const warning = screen.getByTestId('insufficient-funds-warning');
    expect(warning).toBeInTheDocument();
    expect(warning).toHaveTextContent('Insufficient funds in Primary Checking ($2,500.00 available)');

    // Submit button must be disabled
    expect(submitBtn).toBeDisabled();

    // Change amount back within balance ($1,500.00)
    fireEvent.change(amountInput, { target: { value: '1500.00' } });
    expect(screen.queryByTestId('insufficient-funds-warning')).not.toBeInTheDocument();
    expect(submitBtn).toBeEnabled();
  });

  it('AC-4: updates button label dynamically to Verify & Transfer ($X.XX) when amount > $1,000.00', () => {
    render(<TransferForm accounts={mockAccounts} defaultSourceAccountId="CHK-1001" />);

    const amountInput = screen.getByTestId('transfer-amount-input');
    const submitBtn = screen.getByTestId('transfer-submit-btn');

    // Standard transfer <= $1,000.00
    fireEvent.change(amountInput, { target: { value: '250.00' } });
    expect(submitBtn).toHaveTextContent('Transfer Funds');
    expect(screen.queryByTestId('mfa-sensitivity-hint')).not.toBeInTheDocument();

    // Exactly $1,000.00 is still standard
    fireEvent.change(amountInput, { target: { value: '1000.00' } });
    expect(submitBtn).toHaveTextContent('Transfer Funds');

    // Sensitive transfer > $1,000.00 ($1,500.00)
    fireEvent.change(amountInput, { target: { value: '1500.00' } });
    expect(submitBtn).toHaveTextContent('Verify & Transfer ($1,500.00)');
    expect(screen.getByTestId('mfa-sensitivity-hint')).toBeInTheDocument();
  });

  it('submits valid form callback with expected parameters', () => {
    const onSubmit = vi.fn();
    render(
      <TransferForm
        accounts={mockAccounts}
        defaultSourceAccountId="CHK-1001"
        onSubmitTransfer={onSubmit}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    const submitBtn = screen.getByTestId('transfer-submit-btn');

    fireEvent.change(amountInput, { target: { value: '250.00' } });
    expect(submitBtn).toBeEnabled();

    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith({
      fromAccountId: 'CHK-1001',
      toAccountId: 'SAV-2001',
      amountCents: 25000,
      amountFormatted: '$250.00',
    });
  });
});
