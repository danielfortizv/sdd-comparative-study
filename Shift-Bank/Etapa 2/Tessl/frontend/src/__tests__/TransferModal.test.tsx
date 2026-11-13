import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TransferModal } from '../components/TransferModal';
import { Account, Beneficiary, TransferLimits } from '../api/types';

const mockAccounts: Account[] = [
  {
    id: 1,
    user_id: 1,
    account_number: 'CHK-1001',
    account_type: 'checking',
    account_name: 'Primary Checking',
    balance: 2500.0,
    currency: 'USD',
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    account_number: 'SAV-2001',
    account_type: 'savings',
    account_name: 'Standard Savings',
    balance: 10000.0,
    currency: 'USD',
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockBeneficiaries: Beneficiary[] = [
  {
    id: 1,
    user_id: 1,
    name: 'Electric Company',
    routing_number: '123456789',
    account_number: '987654321',
    bank_name: 'City Bank',
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockLimits: TransferLimits = {
  per_transaction_limit: 500.0,
  daily_limit: 1000.0,
  current_daily_total: 200.0,
  remaining_daily_limit: 800.0,
};

describe('TransferModal Component', () => {
  it('renders source and destination account selectors excluding source from destination options', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const fromSelect = screen.getByTestId('from-account-select') as HTMLSelectElement;
    const toSelect = screen.getByTestId('to-account-select') as HTMLSelectElement;

    expect(fromSelect.value).toBe('1');
    expect(toSelect.value).toBe('2');

    // toSelect should not contain account 1 when account 1 is source
    const options = Array.from(toSelect.options).map((o) => o.value);
    expect(options).not.toContain('1');
    expect(options).toContain('2');
  });

  it('validates that transfer amount cannot exceed source balance', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    // Source balance is 2500. Enter 3000
    fireEvent.change(amountInput, { target: { value: '3000' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Amount exceeds available balance ($2500.00)'
    );

    const submitBtn = screen.getByTestId('transfer-submit-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('shows sensitive transfer notice when amount is strictly over $1,000', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '1500' } });

    expect(screen.getByTestId('mfa-sensitive-notice')).toBeInTheDocument();
    expect(screen.getByTestId('transfer-submit-btn')).toHaveTextContent(
      'Continue to Verification'
    );
  });

  it('does not show MFA notice and button displays "Confirm Transfer" when amount is boundary $1,000.00', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '1000.00' } });

    expect(screen.queryByTestId('mfa-sensitive-notice')).not.toBeInTheDocument();
    expect(screen.getByTestId('transfer-submit-btn')).toHaveTextContent(
      'Confirm Transfer'
    );
  });

  it('shows MFA notice and button displays "Continue to Verification" when amount is boundary $1,000.01', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '1000.01' } });

    expect(screen.getByTestId('mfa-sensitive-notice')).toBeInTheDocument();
    expect(screen.getByTestId('transfer-submit-btn')).toHaveTextContent(
      'Continue to Verification'
    );
  });

  it('submits valid transfer payload when user clicks submit', () => {
    const onSubmit = vi.fn();
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '250.00' } });

    const descInput = screen.getByTestId('transfer-desc-input');
    fireEvent.change(descInput, { target: { value: 'Savings buffer' } });

    const submitBtn = screen.getByTestId('transfer-submit-btn');
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith({
      from_account_id: 1,
      to_account_id: 2,
      amount: 250.0,
      description: 'Savings buffer',
    });
  });

  it('calls onClose when cancel button or close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={onClose}
        onSubmit={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('transfer-cancel-btn'));
    expect(onClose).toHaveBeenCalled();
  });

  it('supports toggling to External ACH mode and submitting ACH transfer', () => {
    const onSubmitAch = vi.fn();
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        beneficiaries={mockBeneficiaries}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        onSubmitAch={onSubmitAch}
      />
    );

    // Toggle to ACH
    fireEvent.click(screen.getByTestId('tab-ach-transfer'));
    expect(screen.getByTestId('ach-recipient-section')).toBeInTheDocument();

    // Select saved beneficiary
    const benSelect = screen.getByTestId('beneficiary-select');
    fireEvent.change(benSelect, { target: { value: '1' } });

    // Enter amount
    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '150.00' } });

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    expect(onSubmitAch).toHaveBeenCalledWith({
      from_account_id: 1,
      beneficiary_id: 1,
      amount: 150.0,
      description: undefined,
    });
  });

  it('validates against dynamic transfer limits in real-time', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        limits={mockLimits}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    // Limit is $500.00 per transaction. Enter $600.00
    fireEvent.change(amountInput, { target: { value: '600' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Amount exceeds per-transaction limit ($500.00)'
    );

    expect(screen.getByTestId('transfer-submit-btn')).toBeDisabled();
  });

  it('displays real-time validation error below routing number input if not 9 digits and disables submit (DEFECT-03)', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    // Switch to ACH
    fireEvent.click(screen.getByTestId('tab-ach-transfer'));

    // Enter amount
    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '100.00' } });

    // Enter partial routing number (5 digits)
    const routingInput = screen.getByTestId('routing-number-input');
    fireEvent.change(routingInput, { target: { value: '12345' } });

    // Real-time error message displayed
    expect(screen.getByTestId('routing-number-error')).toHaveTextContent(
      'Routing number must be exactly 9 digits.'
    );
    expect(screen.getByTestId('transfer-submit-btn')).toBeDisabled();

    // Complete to 9 digits
    fireEvent.change(routingInput, { target: { value: '123456789' } });
    expect(screen.queryByTestId('routing-number-error')).not.toBeInTheDocument();
  });

  it('supports entering ad-hoc beneficiary details and toggling save beneficiary checkbox', () => {
    const onSubmitAch = vi.fn();
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        onSubmitAch={onSubmitAch}
      />
    );

    fireEvent.click(screen.getByTestId('tab-ach-transfer'));

    fireEvent.change(screen.getByTestId('recipient-name-input'), { target: { value: 'Alice Walker' } });
    fireEvent.change(screen.getByTestId('routing-number-input'), { target: { value: '123456789' } });
    fireEvent.change(screen.getByTestId('account-number-input'), { target: { value: '987654321' } });
    fireEvent.change(screen.getByTestId('bank-name-input'), { target: { value: 'Global Bank' } });

    const checkbox = screen.getByTestId('save-beneficiary-checkbox');
    fireEvent.click(checkbox);

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '200.00' } });

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    expect(onSubmitAch).toHaveBeenCalledWith({
      from_account_id: 1,
      recipient_name: 'Alice Walker',
      routing_number: '123456789',
      account_number: '987654321',
      bank_name: 'Global Bank',
      save_beneficiary: true,
      amount: 200.0,
      description: undefined,
    });
  });
});
