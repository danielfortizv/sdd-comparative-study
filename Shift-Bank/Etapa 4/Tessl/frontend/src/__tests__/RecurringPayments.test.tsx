import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecurringPayments } from '../components/RecurringPayments';
import { RecurringSchedule, Account, Beneficiary } from '../api/types';

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
    version: 1,
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
    version: 1,
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
    bank_name: 'City Power Bank',
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockSchedules: RecurringSchedule[] = [
  {
    id: 101,
    user_id: 1,
    transfer_type: 'internal',
    from_account_id: 1,
    to_account_id: 2,
    amount: '250.00',
    currency: 'USD',
    frequency: 'monthly',
    status: 'active',
    description: 'Monthly savings',
    next_execution_date: '2026-12-01T00:00:00Z',
    created_at: '2026-11-01T00:00:00Z',
  },
  {
    id: 102,
    user_id: 1,
    transfer_type: 'ach',
    from_account_id: 1,
    recipient_name: 'Electric Utility',
    routing_number: '123456789',
    account_number: '11223344',
    bank_name: 'City Power Bank',
    amount: '120.00',
    currency: 'USD',
    frequency: 'monthly',
    status: 'paused',
    description: 'Power bill',
    next_execution_date: '2026-12-05T00:00:00Z',
    created_at: '2026-11-01T00:00:00Z',
  },
];

describe('RecurringPayments Component', () => {
  it('renders existing recurring payment schedules with status badges and details', () => {
    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    expect(screen.getByTestId('schedule-item-101')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-item-102')).toBeInTheDocument();

    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('PAUSED')).toBeInTheDocument();
    expect(screen.getByText('$250.00 / monthly')).toBeInTheDocument();
  });

  it('triggers onPauseSchedule and onResumeSchedule action handlers', () => {
    const handlePause = vi.fn();
    const handleResume = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={handlePause}
        onResumeSchedule={handleResume}
        onCancelSchedule={vi.fn()}
      />
    );

    // Schedule 101 is active -> has pause button
    const pauseBtn = screen.getByTestId('pause-schedule-btn-101');
    fireEvent.click(pauseBtn);
    expect(handlePause).toHaveBeenCalledWith(101);

    // Schedule 102 is paused -> has resume button
    const resumeBtn = screen.getByTestId('resume-schedule-btn-102');
    fireEvent.click(resumeBtn);
    expect(handleResume).toHaveBeenCalledWith(102);
  });

  it('allows opening schedule creation form and submitting a new recurring payment with canonical decimal string', async () => {
    const handleCreate = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={handleCreate}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    // Open creation form
    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));
    expect(screen.getByTestId('create-schedule-form')).toBeInTheDocument();

    // Fill amount and frequency
    const amountInput = screen.getByTestId('schedule-amount-input');
    const freqSelect = screen.getByTestId('schedule-frequency-select');
    fireEvent.change(amountInput, { target: { value: '300' } });
    fireEvent.change(freqSelect, { target: { value: 'weekly' } });

    // Submit form
    fireEvent.click(screen.getByTestId('submit-schedule-btn'));

    expect(handleCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        transfer_type: 'internal',
        from_account_id: 1,
        to_account_id: 2,
        amount: '300.00',
        frequency: 'weekly',
      })
    );
  });

  it('strictly rejects invalid precision with excess decimal places', async () => {
    const handleCreate = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={handleCreate}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    const amountInput = screen.getByTestId('schedule-amount-input');
    fireEvent.change(amountInput, { target: { value: '300.255' } });

    fireEvent.click(screen.getByTestId('submit-schedule-btn'));

    expect(screen.getByTestId('schedule-error-message')).toHaveTextContent(
      'Please enter a valid amount with at most 2 decimal places.'
    );
    expect(handleCreate).not.toHaveBeenCalled();
  });

  it('strictly rejects zero or negative amounts', async () => {
    const handleCreate = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={handleCreate}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    const amountInput = screen.getByTestId('schedule-amount-input');
    fireEvent.change(amountInput, { target: { value: '0.00' } });

    fireEvent.click(screen.getByTestId('submit-schedule-btn'));

    expect(screen.getByTestId('schedule-error-message')).toHaveTextContent(
      'Please enter a valid amount greater than zero.'
    );
    expect(handleCreate).not.toHaveBeenCalled();
  });

  it('enforces same-currency restriction for internal recurring schedules', () => {
    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    // Source is Account 1 (USD). Destination options must contain Account 2 (USD), NOT Account 3 (EUR)
    const toSelect = screen.getByTestId('schedule-to-account') as HTMLSelectElement;
    const destOptions = Array.from(toSelect.options).map((o) => o.value);
    expect(destOptions).toContain('2');
    expect(destOptions).not.toContain('3');
  });

  it('enforces USD-only restriction for ACH recurring schedules', () => {
    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    // Select Euro Checking (Account 3, EUR) as source
    const fromSelect = screen.getByTestId('schedule-from-account');
    fireEvent.change(fromSelect, { target: { value: '3' } });

    // Switch to ACH tab
    fireEvent.click(screen.getByTestId('tab-ach-schedule'));

    // Warning is displayed
    expect(screen.getByTestId('ach-currency-warning')).toHaveTextContent(
      'Recurring ACH transfers are only permitted from USD accounts. Selected source account is EUR.'
    );

    // Submit button is disabled
    expect(screen.getByTestId('submit-schedule-btn')).toBeDisabled();
  });

  it('enforces exact MFA Security PIN boundary at $1,000.00 USD equivalent', () => {
    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    const amountInput = screen.getByTestId('schedule-amount-input');

    // Exactly $1,000.00 USD does NOT require MFA (> $1,000 required)
    fireEvent.change(amountInput, { target: { value: '1000.00' } });
    expect(screen.queryByTestId('mfa-sensitive-notice')).not.toBeInTheDocument();
    expect(screen.queryByTestId('schedule-pin-input')).not.toBeInTheDocument();

    // $1,000.01 USD DOES require MFA
    fireEvent.change(amountInput, { target: { value: '1000.01' } });
    expect(screen.getByTestId('mfa-sensitive-notice')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-pin-input')).toBeInTheDocument();

    // Switch to Euro Account: base factor 10/9 -> exactly 900.00 EUR == 1000.00 USD
    const fromSelect = screen.getByTestId('schedule-from-account');
    fireEvent.change(fromSelect, { target: { value: '3' } });

    fireEvent.change(amountInput, { target: { value: '900.00' } });
    expect(screen.queryByTestId('mfa-sensitive-notice')).not.toBeInTheDocument();

    fireEvent.change(amountInput, { target: { value: '900.01' } });
    expect(screen.getByTestId('mfa-sensitive-notice')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-pin-input')).toBeInTheDocument();
  });

  it('submits recurring schedule with PIN when amount exceeds $1,000.00 USD', async () => {
    const handleCreate = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={handleCreate}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));

    const amountInput = screen.getByTestId('schedule-amount-input');
    fireEvent.change(amountInput, { target: { value: '1500.00' } });

    expect(screen.getByTestId('schedule-pin-input')).toBeInTheDocument();

    // Submit without PIN -> error
    fireEvent.click(screen.getByTestId('submit-schedule-btn'));
    expect(screen.getByTestId('schedule-error-message')).toHaveTextContent(
      'Security PIN is required for recurring payments exceeding $1,000 USD equivalent.'
    );
    expect(handleCreate).not.toHaveBeenCalled();

    // Enter PIN and submit
    fireEvent.change(screen.getByTestId('schedule-pin-input'), { target: { value: '1234' } });
    fireEvent.click(screen.getByTestId('submit-schedule-btn'));

    expect(handleCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: '1500.00',
        pin: '1234',
      })
    );
  });

  it('submits ACH recurring schedule with saved beneficiary and canonical amount', async () => {
    const handleCreate = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={mockBeneficiaries}
        onClose={vi.fn()}
        onCreateSchedule={handleCreate}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('open-create-schedule-btn'));
    fireEvent.click(screen.getByTestId('tab-ach-schedule'));

    const benSelect = screen.getByLabelText(/Saved Beneficiary/i);
    fireEvent.change(benSelect, { target: { value: '1' } });

    const amountInput = screen.getByTestId('schedule-amount-input');
    fireEvent.change(amountInput, { target: { value: '120.00' } });

    fireEvent.click(screen.getByTestId('submit-schedule-btn'));

    expect(handleCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        transfer_type: 'ach',
        from_account_id: 1,
        beneficiary_id: 1,
        amount: '120.00',
      })
    );
  });

  it('triggers onCancelSchedule when cancel button is clicked', () => {
    const handleCancel = vi.fn();

    render(
      <RecurringPayments
        isOpen={true}
        schedules={mockSchedules}
        accounts={mockAccounts}
        beneficiaries={[]}
        onClose={vi.fn()}
        onCreateSchedule={vi.fn()}
        onPauseSchedule={vi.fn()}
        onResumeSchedule={vi.fn()}
        onCancelSchedule={handleCancel}
      />
    );

    const cancelBtn = screen.getByTestId('cancel-schedule-btn-101');
    fireEvent.click(cancelBtn);
    expect(handleCancel).toHaveBeenCalledWith(101);
  });
});
