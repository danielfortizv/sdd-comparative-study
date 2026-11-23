import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecurringPayments } from '../components/RecurringPayments';
import { RecurringSchedule, Account } from '../api/types';

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

const mockSchedules: RecurringSchedule[] = [
  {
    id: 101,
    user_id: 1,
    transfer_type: 'internal',
    from_account_id: 1,
    to_account_id: 2,
    amount: 250.0,
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
    amount: 120.0,
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

  it('allows opening schedule creation form and submitting a new recurring payment', async () => {
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
        amount: 300,
        frequency: 'weekly',
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
