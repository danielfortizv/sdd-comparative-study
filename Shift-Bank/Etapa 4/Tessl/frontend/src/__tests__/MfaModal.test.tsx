import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MfaModal } from '../components/MfaModal';
import { Account } from '../api/types';

const mockFromAccount: Account = {
  id: 2,
  user_id: 1,
  account_number: 'SAV-2001',
  account_type: 'savings',
  account_name: 'Standard Savings',
  balance: '10000.00',
  currency: 'USD',
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
};

const mockToAccount: Account = {
  id: 1,
  user_id: 1,
  account_number: 'CHK-1001',
  account_type: 'checking',
  account_name: 'Primary Checking',
  balance: '2500.00',
  currency: 'USD',
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
};

describe('MfaModal Component', () => {
  it('displays transfer details (source, destination, amount) awaiting authorization', () => {
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$1,500.00');
    expect(screen.getByTestId('mfa-from-account')).toHaveTextContent('Standard Savings (SAV-2001)');
    expect(screen.getByTestId('mfa-to-account')).toHaveTextContent('Primary Checking (CHK-1001)');
  });

  it('formats small and boundary decimal amounts without floating-point precision loss', () => {
    const { rerender } = render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="0.05"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$0.05');

    rerender(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1000.01"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$1,000.01');

    rerender(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="0.01"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$0.01');
  });

  it('formats amounts according to source account currency (EUR, GBP, USD)', () => {
    const eurAccount: Account = {
      ...mockFromAccount,
      currency: 'EUR',
      account_name: 'Euro Checking',
    };
    const gbpAccount: Account = {
      ...mockFromAccount,
      currency: 'GBP',
      account_name: 'British Pound Checking',
    };

    const { rerender } = render(
      <MfaModal
        isOpen={true}
        fromAccount={eurAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('€1,500.00');

    rerender(
      <MfaModal
        isOpen={true}
        fromAccount={gbpAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('£1,500.00');

    rerender(
      <MfaModal
        isOpen={true}
        fromAccount={null}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$1,500.00');
  });

  it('includes PIN input and helper text with demo PIN and remaining attempts', () => {
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={2}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByTestId('mfa-pin-input')).toBeInTheDocument();
    expect(screen.getByText(/1234/)).toBeInTheDocument();
    expect(screen.getByTestId('remaining-attempts')).toHaveTextContent('2 attempt(s) remaining');
  });

  it('displays error message when provided', () => {
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={2}
        isLocked={false}
        errorMessage="Invalid Security PIN. 2 attempt(s) remaining."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByTestId('mfa-error-message')).toHaveTextContent(
      'Invalid Security PIN. 2 attempt(s) remaining.'
    );
  });

  it('disables PIN submission and displays account lockout banner when isLocked is true', () => {
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={0}
        isLocked={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByTestId('mfa-lockout-alert')).toBeInTheDocument();
    expect(screen.queryByTestId('mfa-pin-input')).not.toBeInTheDocument();
    expect(screen.getByTestId('mfa-close-locked-btn')).toBeInTheDocument();
  });

  it('submits PIN when valid 4-digit code is entered', () => {
    const onConfirm = vi.fn();
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );

    const pinInput = screen.getByTestId('mfa-pin-input');
    const submitBtn = screen.getByTestId('mfa-submit-btn');

    expect(submitBtn).toBeDisabled();

    fireEvent.change(pinInput, { target: { value: '1234' } });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);
    expect(onConfirm).toHaveBeenCalledWith('1234');
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn();
    render(
      <MfaModal
        isOpen={true}
        fromAccount={mockFromAccount}
        toAccount={mockToAccount}
        amount="1500.00"
        remainingAttempts={3}
        isLocked={false}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );

    fireEvent.click(screen.getByTestId('mfa-cancel-btn'));
    expect(onCancel).toHaveBeenCalled();
  });
});
