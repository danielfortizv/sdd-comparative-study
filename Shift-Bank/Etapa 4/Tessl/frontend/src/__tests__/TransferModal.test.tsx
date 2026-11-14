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
    balance: '2500.00',
    currency: 'USD',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    account_number: 'SAV-2001',
    account_type: 'savings',
    account_name: 'Standard Savings',
    balance: '10000.00',
    currency: 'USD',
    version: 2,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 3,
    user_id: 1,
    account_number: 'EUR-3001',
    account_type: 'checking',
    account_name: 'Euro Checking',
    balance: '900.00',
    currency: 'EUR',
    version: 4,
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
  per_transaction_limit: '500.00',
  daily_limit: '1000.00',
  current_daily_total: '200.00',
  remaining_daily_limit: '800.00',
  reference_currency: 'USD',
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
    // Source balance is 2500.00. Enter 3000
    fireEvent.change(amountInput, { target: { value: '3000' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Amount exceeds available balance ($2,500.00)'
    );

    const submitBtn = screen.getByTestId('transfer-submit-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('rejects invalid inputs with excess decimal places', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '250.555' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Please enter a valid transfer amount with at most 2 decimal places.'
    );

    const submitBtn = screen.getByTestId('transfer-submit-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('rejects zero or negative transfer amounts', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    fireEvent.change(amountInput, { target: { value: '0.00' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Please enter a valid transfer amount greater than zero.'
    );

    const submitBtn = screen.getByTestId('transfer-submit-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('enforces same-currency restriction for internal transfers', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const fromSelect = screen.getByTestId('from-account-select');
    const toSelect = screen.getByTestId('to-account-select');

    // Account 1 is USD. Destination options must only contain Account 2 (USD), NOT Account 3 (EUR)
    expect(fromSelect).toHaveValue('1');
    const destOptionValues = Array.from((toSelect as HTMLSelectElement).options).map((o) => o.value);
    expect(destOptionValues).toContain('2');
    expect(destOptionValues).not.toContain('3');
  });

  it('enforces USD-only restriction for ACH transfers', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    // Select Euro Checking (Account 3, EUR) as source
    const fromSelect = screen.getByTestId('from-account-select');
    fireEvent.change(fromSelect, { target: { value: '3' } });

    // Switch to ACH transfer tab
    fireEvent.click(screen.getByTestId('tab-ach-transfer'));

    // Warning message displayed
    expect(screen.getByTestId('ach-currency-warning')).toHaveTextContent(
      'ACH transfers are only supported from USD accounts. Selected source account is EUR.'
    );

    // Submit button is disabled
    expect(screen.getByTestId('transfer-submit-btn')).toBeDisabled();
  });

  it('validates against dynamic per-transaction transfer limits in real-time', () => {
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

  it('validates against dynamic remaining daily transfer limits in real-time', () => {
    const higherPerTxLimits: TransferLimits = {
      per_transaction_limit: '1000.00',
      daily_limit: '1000.00',
      current_daily_total: '200.00',
      remaining_daily_limit: '800.00',
      reference_currency: 'USD',
    };

    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        limits={higherPerTxLimits}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    const amountInput = screen.getByTestId('transfer-amount-input');
    // Per-tx limit is $1000.00, but remaining daily is $800.00. Enter $850.00
    fireEvent.change(amountInput, { target: { value: '850.00' } });

    expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
      'Amount exceeds remaining daily limit ($800.00)'
    );

    expect(screen.getByTestId('transfer-submit-btn')).toBeDisabled();
  });

  it('does not show MFA notice and button displays "Confirm Transfer" at exact boundary $1,000.00 USD', () => {
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
    expect(screen.getByTestId('transfer-submit-btn')).toHaveTextContent('Confirm Transfer');
  });

  it('shows MFA notice and button displays "Continue to Verification" at boundary $1,000.01 USD', () => {
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
    expect(screen.getByTestId('transfer-submit-btn')).toHaveTextContent('Continue to Verification');
  });

  it('evaluates exact MFA boundary in foreign currency using unrounded USD equivalent (EUR base factor 10/9)', () => {
    render(
      <TransferModal
        isOpen={true}
        accounts={mockAccounts}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    // Select Euro Checking (Account 3, EUR)
    const fromSelect = screen.getByTestId('from-account-select');
    fireEvent.change(fromSelect, { target: { value: '3' } });

    const amountInput = screen.getByTestId('transfer-amount-input');

    // 900.00 EUR * 10 / 9 = exactly $1,000.00 USD (boundary <= 1000 does NOT require MFA)
    fireEvent.change(amountInput, { target: { value: '900.00' } });
    expect(screen.queryByTestId('mfa-sensitive-notice')).not.toBeInTheDocument();

    // 900.01 EUR * 10 / 9 > $1,000.00 USD (DOES require MFA)
    fireEvent.change(amountInput, { target: { value: '900.01' } });
    expect(screen.getByTestId('mfa-sensitive-notice')).toBeInTheDocument();
  });

  it('submits valid transfer payload with canonical decimal string and D-14 expected versions', () => {
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
      amount: '250.00',
      expected_from_version: 1,
      expected_to_version: 2,
      description: 'Savings buffer',
    });
  });

  it('calls onClose when cancel button is clicked', () => {
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

  it('supports toggling to External ACH mode and submitting ACH transfer with saved beneficiary', () => {
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
      amount: '150.00',
      expected_from_version: 1,
      description: undefined,
    });
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
      amount: '200.00',
      expected_from_version: 1,
      description: undefined,
    });
  });
});
