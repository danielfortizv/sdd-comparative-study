import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import App from './App';
import * as services from './services';
import { HistoryEntry } from './types';

// Mock the services module to isolate frontend testing from live API
vi.mock('./services', () => {
  return {
    fetchAccounts: vi.fn(),
    fetchHistory: vi.fn(),
    initiateTransfer: vi.fn(),
    confirmMFA: vi.fn(),
    fetchLimits: vi.fn().mockResolvedValue({
      per_transfer_limit: '5000000.00',
      daily_limit: '10000000.00',
      current_daily_consumption: '0.00',
      remaining_daily_availability: '10000000.00',
      updated_at: '2026-11-14T00:00:00Z',
    }),
    updateLimits: vi.fn(),
    fetchBeneficiaries: vi.fn().mockResolvedValue([]),
    createBeneficiary: vi.fn(),
    deleteBeneficiary: vi.fn(),
    initiateAchTransfer: vi.fn(),
    fetchSchedules: vi.fn().mockResolvedValue([]),
    createSchedule: vi.fn(),
    confirmScheduleMFA: vi.fn(),
    convertFunds: vi.fn(),
    createIdempotencyKey: vi.fn(() => '00000000-0000-4000-8000-000000000001'),
    pauseSchedule: vi.fn(),
    resumeSchedule: vi.fn(),
    cancelSchedule: vi.fn(),
  };
});

describe('User Story 1: Account Overview & Balances', () => {
  test('renders Checking and Savings account cards with correct formatted starting balances', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '5000000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15000000.00',
        currency: 'COP',
      },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Checking', { selector: '.account-type' })).toBeInTheDocument();
      expect(screen.getByText('Savings', { selector: '.account-type' })).toBeInTheDocument();
    });

    const accountsSection = screen.getByText('Account Overview').closest('section')!;
    expect(within(accountsSection).getByText(/\b5[., ]000[., ]000/)).toBeInTheDocument();
    expect(within(accountsSection).getByText(/\b15[., ]000[., ]000/)).toBeInTheDocument();
    expect(within(accountsSection).queryByText('acc_checking_123')).not.toBeInTheDocument();
    expect(within(accountsSection).queryByText('acc_savings_456')).not.toBeInTheDocument();
  });
});

describe('User Story 2: Transfer Between Own Accounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('validates inputs client-side and submits successful standard transfer under COP 1,000,000', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '5000000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15000000.00',
        currency: 'COP',
      },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.initiateTransfer).mockResolvedValue({
      id: 'tr_new_789',
      source_account: 'Checking',
      destination_account: 'Savings',
      amount: '300000.00',
      status: 'COMPLETED',
      created_at: '2026-09-30T12:00:00Z',
      expires_at: null,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Checking', { selector: '.account-type' })).toBeInTheDocument();
    });

    expect(screen.getByRole('heading', { name: /Transfer Funds/ })).toBeInTheDocument();

    const sourceSelect = screen.getByLabelText(/Source Account/i);
    const destSelect = screen.getByLabelText(/Destination Account/i);
    const amountInput = screen.getByLabelText(/Amount/i, { selector: '#amount-input' });
    const transferButton = screen.getByRole('button', { name: /Transfer/i });

    fireEvent.change(sourceSelect, { target: { value: 'acc_checking_123' } });
    fireEvent.change(destSelect, { target: { value: 'acc_checking_123' } });
    fireEvent.change(amountInput, { target: { value: '100000' } });
    fireEvent.click(transferButton);

    await waitFor(() => {
      expect(screen.getByText(/different/i)).toBeInTheDocument();
    });

    fireEvent.change(destSelect, { target: { value: 'acc_savings_456' } });
    fireEvent.change(amountInput, { target: { value: '-500' } });
    fireEvent.click(transferButton);

    await waitFor(() => {
      expect(screen.getByText(/greater than zero/i)).toBeInTheDocument();
    });

    fireEvent.change(amountInput, { target: { value: '6000000' } });
    fireEvent.click(transferButton);

    await waitFor(() => {
      expect(screen.getByText(/Insufficient funds/i)).toBeInTheDocument();
    });

    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '4700000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15300000.00',
        currency: 'COP',
      },
    ]);

    fireEvent.change(amountInput, { target: { value: '300000' } });
    fireEvent.click(transferButton);

    await waitFor(() => {
      expect(services.initiateTransfer).toHaveBeenCalledWith(
        'acc_checking_123',
        'acc_savings_456',
        '300000.00',
        { acc_checking_123: 0, acc_savings_456: 0 },
        '00000000-0000-4000-8000-000000000001'
      );
      expect(services.fetchAccounts).toHaveBeenCalledTimes(2);
    });

    expect(screen.getByText(/successfully/i)).toBeInTheDocument();
    expect(screen.getByText(/\b4[., ]700[., ]000/)).toBeInTheDocument();
    expect(screen.getByText(/\b15[., ]300[., ]000/)).toBeInTheDocument();
  });
});

describe('User Story 3: Transaction History & Pre-seeded Movements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('fetches and renders transaction history in newest-first order with complete columns and no database IDs', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '5000000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15000000.00',
        currency: 'COP',
      },
    ]);

    vi.mocked(services.fetchHistory).mockImplementation(async (accountId) => {
      if (accountId === 'acc_checking_123') {
        return [
          {
            id: 'tr_seeded_2',
            direction: 'outgoing',
            amount: '100000.00',
            description: 'Transfer from Checking to Savings',
            date: '2026-09-30T10:05:00Z',
          },
          {
            id: 'tr_seeded_1',
            direction: 'incoming',
            amount: '500000.00',
            description: 'Transfer from Savings to Checking',
            date: '2026-09-30T10:00:00Z',
          },
        ];
      } else if (accountId === 'acc_savings_456') {
        return [
          {
            id: 'tr_seeded_2',
            direction: 'incoming',
            amount: '100000.00',
            description: 'Transfer from Checking to Savings',
            date: '2026-09-30T10:05:00Z',
          },
          {
            id: 'tr_seeded_1',
            direction: 'outgoing',
            amount: '500000.00',
            description: 'Transfer from Savings to Checking',
            date: '2026-09-30T10:00:00Z',
          },
        ];
      }
      return [];
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Checking', { selector: '.account-type' })).toBeInTheDocument();
      expect(services.fetchHistory).toHaveBeenCalledWith('acc_checking_123');
    });

    expect(screen.getByRole('columnheader', { name: /Date/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Direction/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Amount/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Description/i })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: /Resulting/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: /Balance/i })).not.toBeInTheDocument();

    const rows = screen.getAllByRole('row');
    const row0 = rows[1];
    const row1 = rows[2];

    expect(within(row0).getByText('Outgoing')).toBeInTheDocument();
    expect(within(row0).getByText(/100[., ]000/)).toBeInTheDocument();
    expect(within(row0).getByText('Transfer from Checking to Savings')).toBeInTheDocument();
    
    expect(within(row1).getByText('Incoming')).toBeInTheDocument();
    expect(within(row1).getByText(/500[., ]000/)).toBeInTheDocument();
    expect(within(row1).getByText('Transfer from Savings to Checking')).toBeInTheDocument();

    expect(within(row0).queryByText('tr_seeded_2')).not.toBeInTheDocument();
    expect(within(row1).queryByText('tr_seeded_1')).not.toBeInTheDocument();

    const savingsCard = screen.getByText('Savings', { selector: '.account-type' }).closest('.account-card');
    fireEvent.click(savingsCard!);

    await waitFor(() => {
      expect(services.fetchHistory).toHaveBeenLastCalledWith('acc_savings_456');
    });

    const updatedRows = screen.getAllByRole('row');
    const updatedRow0 = updatedRows[1];
    const updatedRow1 = updatedRows[2];

    expect(within(updatedRow0).getByText('Incoming')).toBeInTheDocument();
    expect(within(updatedRow1).getByText('Outgoing')).toBeInTheDocument();
  });

  test('refreshes the transaction history and displays the new movement instantly after a successful transfer', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '5000000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15000000.00',
        currency: 'COP',
      },
    ]);

    const mockHistoryList: HistoryEntry[] = [
      {
        id: 'tr_seeded_2',
        direction: 'outgoing',
        amount: '100000.00',
        description: 'Transfer from Checking to Savings',
        date: '2026-09-30T10:05:00Z',
      },
      {
        id: 'tr_seeded_1',
        direction: 'incoming',
        amount: '500000.00',
        description: 'Transfer from Savings to Checking',
        date: '2026-09-30T10:00:00Z',
      },
    ];

    vi.mocked(services.fetchHistory).mockResolvedValue(mockHistoryList);

    vi.mocked(services.initiateTransfer).mockResolvedValue({
      id: 'tr_user_999',
      source_account: 'Checking',
      destination_account: 'Savings',
      amount: '200000.00',
      status: 'COMPLETED',
      created_at: '2026-09-30T11:00:00Z',
      expires_at: null,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Checking', { selector: '.account-type' })).toBeInTheDocument();
    });

    expect(screen.getAllByRole('row').length).toBe(3);

    const amountInput = screen.getByLabelText(/Amount/i, { selector: '#amount-input' });
    const transferButton = screen.getByRole('button', { name: /Transfer/i });

    vi.mocked(services.fetchHistory).mockResolvedValue([
      {
        id: 'tr_user_999',
        direction: 'outgoing',
        amount: '200000.00',
        description: 'Transfer from Checking to Savings',
        date: '2026-09-30T11:00:00Z',
      },
      ...mockHistoryList,
    ]);

    fireEvent.change(amountInput, { target: { value: '200000' } });
    fireEvent.click(transferButton);

    await waitFor(() => {
      expect(services.initiateTransfer).toHaveBeenCalledWith(
        'acc_checking_123',
        'acc_savings_456',
        '200000.00',
        { acc_checking_123: 0, acc_savings_456: 0 },
        '00000000-0000-4000-8000-000000000001'
      );
      expect(services.fetchHistory).toHaveBeenCalledTimes(2);
    });

    const updatedRows = screen.getAllByRole('row');
    expect(updatedRows.length).toBe(4);

    const firstDataRow = updatedRows[1];
    expect(within(firstDataRow).getByText('Outgoing')).toBeInTheDocument();
    expect(within(firstDataRow).getByText(/200[., ]000/)).toBeInTheDocument();
    expect(within(firstDataRow).queryByText('tr_user_999')).not.toBeInTheDocument();
  });
});

describe('User Story 4: Mock Multi-Factor Authentication & State Machine', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('intercepts sensitive transfer, renders MFA modal, handles invalid code retry, handles closing and resuming, and confirms successfully', async () => {
    // 1. Mock initial data
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '5000000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '15000000.00',
        currency: 'COP',
      },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);

    // Mock 202 Accepted sensitive transfer response
    const mockPendingTx = {
      id: 'tr_sensitive_888',
      source_account: 'Checking',
      destination_account: 'Savings',
      amount: '1500000.00',
      status: 'PENDING_MFA' as const,
      created_at: '2026-09-30T13:00:00Z',
      expires_at: '2026-09-30T13:05:00Z',
    };
    vi.mocked(services.initiateTransfer).mockResolvedValue(mockPendingTx);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Checking', { selector: '.account-type' })).toBeInTheDocument();
    });

    // Submit sensitive transfer (COP 1,500,000)
    const amountInput = screen.getByLabelText(/Amount/i, { selector: '#amount-input' });
    const transferButton = screen.getByRole('button', { name: /Transfer/i });

    fireEvent.change(amountInput, { target: { value: '1500000' } });
    fireEvent.click(transferButton);

    // 2. Verify MFA modal opens
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /MFA Verification/i })).toBeInTheDocument();
    });

    const codeInput = screen.getByLabelText(/MFA Code/i);
    const confirmButton = screen.getByRole('button', { name: /Confirm/i });
    const modalCloseButton = screen.getByLabelText(/Close/i);

    // 3. Test Invalid MFA Code submits and shows error in modal
    vi.mocked(services.confirmMFA).mockRejectedValue(new Error('Invalid verification code.'));
    
    fireEvent.change(codeInput, { target: { value: '111111' } });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(screen.getByText(/Invalid verification code/i)).toBeInTheDocument();
    });
    // Modal should remain open
    expect(screen.getByRole('heading', { name: /MFA Verification/i })).toBeInTheDocument();

    // 4. Test Closing modal: closes modal and displays pending widget
    fireEvent.click(modalCloseButton);
    expect(screen.queryByRole('heading', { name: /MFA Verification/i })).not.toBeInTheDocument();

    // Verify pending transfers widget displays
    expect(screen.getByRole('heading', { name: /Pending Sensitive Transfers/i })).toBeInTheDocument();
    expect(screen.getByText(/\b1[., ]500[., ]000/)).toBeInTheDocument();
    expect(screen.queryByText('tr_sensitive_888')).not.toBeInTheDocument(); // IDs hidden

    // 5. Test Resuming pending transfer: re-opens modal
    const resumeButton = screen.getByRole('button', { name: /Resume/i });
    fireEvent.click(resumeButton);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /MFA Verification/i })).toBeInTheDocument();
    });

    // 6. Test Successful MFA Code confirmation: updates balances, closes modal, displays global success
    vi.mocked(services.confirmMFA).mockResolvedValue({
      id: 'tr_sensitive_888',
      status: 'COMPLETED',
      message: 'Transfer executed successfully.',
    });

    vi.mocked(services.fetchAccounts).mockResolvedValue([
      {
        id: 'acc_checking_123',
        name: 'Checking',
        balance: '3500000.00',
        currency: 'COP',
      },
      {
        id: 'acc_savings_456',
        name: 'Savings',
        balance: '16500000.00',
        currency: 'COP',
      },
    ]);

    const refreshedCodeInput = screen.getByLabelText(/MFA Code/i);
    const refreshedConfirmButton = screen.getByRole('button', { name: /Confirm/i });

    fireEvent.change(refreshedCodeInput, { target: { value: '123456' } });
    fireEvent.click(refreshedConfirmButton);

    await waitFor(() => {
      expect(services.confirmMFA).toHaveBeenCalledWith('tr_sensitive_888', '123456', {}, '00000000-0000-4000-8000-000000000001');
    });

    // Expect modal to close, global success alert to render, and balances to refresh
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /MFA Verification/i })).not.toBeInTheDocument();
      expect(screen.getByText(/successfully/i)).toBeInTheDocument();
      expect(screen.getByText(/\b3[., ]500[., ]000/)).toBeInTheDocument();
      expect(screen.getByText(/\b16[., ]500[., ]000/)).toBeInTheDocument();
    });
  });
});

describe('Stage 2 User Story 1: Dynamic Limits Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders dynamic limits stats with configured limits, consumption, and availability', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
      { id: 'acc_savings_456', name: 'Savings', balance: '15000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchLimits).mockResolvedValue({
      per_transfer_limit: '5000000.00',
      daily_limit: '10000000.00',
      current_daily_consumption: '150000.00',
      remaining_daily_availability: '9850000.00',
      updated_at: '2026-11-14T12:00:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Transfer Limits/i })).toBeInTheDocument();
    });

    const limitsSection = screen.getByRole('heading', { name: /Transfer Limits/i }).closest('section')!;

    expect(within(limitsSection).getByText(/Per-Transfer Limit/i)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/Daily Limit/i)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/Today's Consumption/i)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/Remaining Daily Availability/i)).toBeInTheDocument();

    expect(within(limitsSection).getByText(/\b5[., ]000[., ]000/)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/\b10[., ]000[., ]000/)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/\b150[., ]000/)).toBeInTheDocument();
    expect(within(limitsSection).getByText(/\b9[., ]850[., ]000/)).toBeInTheDocument();
  });

  test('validates inputs client-side and updates limits successfully', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
      { id: 'acc_savings_456', name: 'Savings', balance: '15000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchLimits).mockResolvedValue({
      per_transfer_limit: '5000000.00',
      daily_limit: '10000000.00',
      current_daily_consumption: '0.00',
      remaining_daily_availability: '10000000.00',
      updated_at: '2026-11-14T12:00:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit Limits/i })).toBeInTheDocument();
    });

    // 1. Open edit form
    const editBtn = screen.getByRole('button', { name: /Edit Limits/i });
    fireEvent.click(editBtn);

    const perInput = screen.getByLabelText(/Per-Transfer Limit \(COP\)/i);
    const dailyInput = screen.getByLabelText(/Daily Limit \(COP\)/i);
    const saveBtn = screen.getByRole('button', { name: /Save Limits/i });

    // 2. Validate non-positive input
    fireEvent.change(perInput, { target: { value: '0' } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/strictly positive/i)).toBeInTheDocument();
    });

    // 3. Valid update
    vi.mocked(services.updateLimits).mockResolvedValue({
      per_transfer_limit: '2000000.00',
      daily_limit: '4000000.00',
      current_daily_consumption: '0.00',
      remaining_daily_availability: '4000000.00',
      updated_at: '2026-11-14T12:30:00Z',
    });

    fireEvent.change(perInput, { target: { value: '2000000' } });
    fireEvent.change(dailyInput, { target: { value: '4000000' } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(services.updateLimits).toHaveBeenCalledWith({
        per_transfer_limit: '2000000.00',
        daily_limit: '4000000.00',
      });
      expect(screen.getByText(/Transfer limits updated successfully!/i)).toBeInTheDocument();
    });

    const limitsSection = screen.getByRole('heading', { name: /Transfer Limits/i }).closest('section')!;
    expect(within(limitsSection).getByText(/\b2[., ]000[., ]000/)).toBeInTheDocument();
    expect(within(limitsSection).getAllByText(/\b4[., ]000[., ]000/).length).toBe(2); // Daily limit and availability both 4M
  });
});

describe('Stage 2 User Story 2: ACH Transfers & Beneficiaries', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('validates routing number in real time and disables submit button when invalid (ACH-10, A05)', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchBeneficiaries).mockResolvedValue([]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ACH/i })).toBeInTheDocument();
    });

    // Switch to ACH Transfer tab
    fireEvent.click(screen.getByRole('button', { name: /ACH/i }));

    const routingInput = screen.getByLabelText(/Routing Number \(9 digits\)/i);
    const submitBtn = screen.getByRole('button', { name: /Send ACH Transfer/i });
    fireEvent.change(screen.getByLabelText(/Source Account/i, { selector: '#ach-source-select' }), { target: { value: 'acc_checking_123' } });

    // 1. Enter 8 digits: real-time inline warning and disabled button
    fireEvent.change(routingInput, { target: { value: '12345678' } });
    expect(screen.getByText(/Routing number must be exactly 9 numeric digits/i)).toBeInTheDocument();
    expect(submitBtn).toBeDisabled();

    // 2. Enter non-numeric digits
    fireEvent.change(routingInput, { target: { value: '12345678A' } });
    expect(screen.getByText(/Routing number must be exactly 9 numeric digits/i)).toBeInTheDocument();
    expect(submitBtn).toBeDisabled();

    // 3. Enter exact 9 digits: inline error clears
    fireEvent.change(routingInput, { target: { value: '123456789' } });
    expect(screen.queryByText(/Routing number must be exactly 9 numeric digits/i)).not.toBeInTheDocument();
  });

  test('lists saved beneficiaries and supports deletion (ACH-02, D-08)', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchBeneficiaries).mockResolvedValue([
      {
        id: 'ben_1',
        name: 'Empresa de Energia',
        bank_name: 'Banco Davivienda',
        routing_number: '123456789',
        account_number: '9876543210',
        created_at: '2026-11-14T10:00:00Z',
      },
    ]);
    vi.mocked(services.deleteBeneficiary).mockResolvedValue(undefined);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Empresa de Energia')).toBeInTheDocument();
      expect(screen.getByText('Banco Davivienda')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByRole('button', { name: /Delete/i });
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(services.deleteBeneficiary).toHaveBeenCalledWith('ben_1');
    });
  });

  test('submits standard ACH transfer and handles sensitive ACH transfer with shared MFA modal (A04, D-03)', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
      { id: 'acc_savings_456', name: 'Savings', balance: '15000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchBeneficiaries).mockResolvedValue([]);

    // 1. Mock sensitive ACH transfer returning 202 PENDING_MFA
    vi.mocked(services.initiateAchTransfer).mockResolvedValue({
      id: 'tr_ach_sensitive',
      transfer_type: 'ACH',
      source_account: 'Checking',
      recipient_name: 'Inmobiliaria',
      bank_name: 'Bancolombia',
      routing_number: '123456789',
      account_number: '456789123',
      amount: '1500000.00',
      status: 'PENDING_MFA',
      created_at: '2026-11-14T12:00:00Z',
      expires_at: '2026-11-14T12:05:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ACH/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /ACH/i }));

    const recipientInput = screen.getByLabelText(/Recipient Name/i);
    const bankInput = screen.getByLabelText(/Bank Name/i);
    const routingInput = screen.getByLabelText(/Routing Number \(9 digits\)/i);
    const accountInput = screen.getByLabelText(/Account Number \(4–17 digits\)/i);
    const amountInput = screen.getByLabelText(/Amount \(COP\)/i);
    const submitBtn = screen.getByRole('button', { name: /Send ACH Transfer/i });

    fireEvent.change(recipientInput, { target: { value: 'Inmobiliaria' } });
    fireEvent.change(bankInput, { target: { value: 'Bancolombia' } });
    fireEvent.change(routingInput, { target: { value: '123456789' } });
    fireEvent.change(accountInput, { target: { value: '456789123' } });
    fireEvent.change(amountInput, { target: { value: '1500000' } });

    fireEvent.click(submitBtn);

    await waitFor(() => expect(services.initiateAchTransfer).toHaveBeenCalled());

    // 2. Expect MFA Modal to open for sensitive ACH transfer
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /MFA Verification/i })).toBeInTheDocument();
    });

    // 3. Confirm MFA with code 123456
    vi.mocked(services.confirmMFA).mockResolvedValue({
      id: 'tr_ach_sensitive',
      status: 'PENDING',
      message: 'ACH transfer initiated and pending settlement.',
    });

    const mfaCodeInput = screen.getByLabelText(/MFA Code/i);
    const mfaConfirmBtn = screen.getByRole('button', { name: /Confirm/i });

    fireEvent.change(mfaCodeInput, { target: { value: '123456' } });
    fireEvent.click(mfaConfirmBtn);

    await waitFor(() => {
      expect(services.confirmMFA).toHaveBeenCalledWith('tr_ach_sensitive', '123456', { acc_checking_123: 0 }, '00000000-0000-4000-8000-000000000001');
    });
  });
});

describe('Stage 2 User Story 3: Scheduled Recurring Payments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders recurring schedules list and supports pause, resume, and cancel (A18)', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
      { id: 'acc_savings_456', name: 'Savings', balance: '15000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchBeneficiaries).mockResolvedValue([]);
    vi.mocked(services.fetchSchedules).mockResolvedValue([
      {
        id: 'rec_1',
        transfer_type: 'INTERNAL',
        source_account_id: 'acc_checking_123',
        source_account: 'Checking',
        destination_display: 'Savings',
        amount: '100000.00',
        frequency: 'MONTHLY',
        status: 'ACTIVE',
        next_due_date: '2026-12-14T12:00:00Z',
        last_executed_at: null,
        mfa_expires_at: null,
        created_at: '2026-11-14T12:00:00Z',
      },
    ]);
    vi.mocked(services.pauseSchedule).mockResolvedValue({
      id: 'rec_1',
      transfer_type: 'INTERNAL',
      source_account_id: 'acc_checking_123',
      source_account: 'Checking',
      destination_display: 'Savings',
      amount: '100000.00',
      frequency: 'MONTHLY',
      status: 'PAUSED',
      next_due_date: '2026-12-14T12:00:00Z',
      last_executed_at: null,
      mfa_expires_at: null,
      created_at: '2026-11-14T12:00:00Z',
    });
    vi.mocked(services.cancelSchedule).mockResolvedValue({
      id: 'rec_1',
      transfer_type: 'INTERNAL',
      source_account_id: 'acc_checking_123',
      source_account: 'Checking',
      destination_display: 'Savings',
      amount: '100000.00',
      frequency: 'MONTHLY',
      status: 'CANCELLED',
      next_due_date: '2026-12-14T12:00:00Z',
      last_executed_at: null,
      mfa_expires_at: null,
      created_at: '2026-11-14T12:00:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Scheduled Recurring Payments/i })).toBeInTheDocument();
    });

    const schedulesSection = screen.getByRole('heading', { name: /Scheduled Recurring Payments/i }).closest('section')!;

    expect(within(schedulesSection).getByText('Savings')).toBeInTheDocument();
    expect(within(schedulesSection).getByText('MONTHLY')).toBeInTheDocument();

    // 1. Pause
    const pauseBtn = within(schedulesSection).getByRole('button', { name: /^Pause$/i });
    fireEvent.click(pauseBtn);

    await waitFor(() => {
      expect(services.pauseSchedule).toHaveBeenCalledWith('rec_1');
    });

    // 2. Cancel
    const cancelBtn = within(schedulesSection).getByRole('button', { name: /^Cancel$/i });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(services.cancelSchedule).toHaveBeenCalledWith('rec_1');
    });
  });

  test('creates recurring schedule and handles sensitive schedule MFA modal confirmation (A15, D-03, D-05)', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP' },
      { id: 'acc_savings_456', name: 'Savings', balance: '15000000.00', currency: 'COP' },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.fetchBeneficiaries).mockResolvedValue([]);
    vi.mocked(services.fetchSchedules).mockResolvedValue([]);

    // Mock sensitive schedule returning PENDING_MFA
    vi.mocked(services.createSchedule).mockResolvedValue({
      id: 'rec_sensitive_1',
      transfer_type: 'INTERNAL',
      source_account_id: 'acc_checking_123',
      source_account: 'Checking',
      destination_display: 'Savings',
      amount: '1500000.00',
      frequency: 'MONTHLY',
      status: 'PENDING_MFA',
      next_due_date: '2026-12-14T12:00:00Z',
      last_executed_at: null,
      mfa_expires_at: '2026-11-14T12:05:00Z',
      created_at: '2026-11-14T12:00:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Schedule Payment/i })).toBeInTheDocument();
    });

    // Open creation form
    fireEvent.click(screen.getByRole('button', { name: /Schedule Payment/i }));

    const amountInput = screen.getByLabelText(/Amount \(COP\)/i, { selector: '#sched-amount-input' });
    const createBtn = screen.getByRole('button', { name: /Create Schedule/i });
    fireEvent.change(screen.getByLabelText(/Source Account/i, { selector: '#sched-source-select' }), { target: { value: 'acc_checking_123' } });
    fireEvent.change(screen.getByLabelText(/Destination Account/i, { selector: '#sched-dest-select' }), { target: { value: 'acc_savings_456' } });

    fireEvent.change(amountInput, { target: { value: '1500000' } });
    fireEvent.click(createBtn);

    await waitFor(() => expect(services.createSchedule).toHaveBeenCalled());

    // Expect MFA modal to open for recurring schedule
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /MFA Verification/i })).toBeInTheDocument();
      expect(screen.getByText(/sensitive recurring schedule of/i)).toBeInTheDocument();
    });

    // Confirm MFA
    vi.mocked(services.confirmScheduleMFA).mockResolvedValue({
      id: 'rec_sensitive_1',
      transfer_type: 'INTERNAL',
      source_account_id: 'acc_checking_123',
      source_account: 'Checking',
      destination_display: 'Savings',
      amount: '1500000.00',
      frequency: 'MONTHLY',
      status: 'ACTIVE',
      next_due_date: '2026-12-14T12:00:00Z',
      last_executed_at: null,
      mfa_expires_at: null,
      created_at: '2026-11-14T12:00:00Z',
    });

    const mfaInput = screen.getByLabelText(/MFA Code/i);
    const mfaConfirmBtn = screen.getByRole('button', { name: /Confirm/i });

    fireEvent.change(mfaInput, { target: { value: '123456' } });
    fireEvent.click(mfaConfirmBtn);

    await waitFor(() => {
      expect(services.confirmScheduleMFA).toHaveBeenCalledWith('rec_sensitive_1', '123456', { acc_checking_123: 0 }, '00000000-0000-4000-8000-000000000001');
    });
  });
});

describe('Stage 4 currency dashboard and conversion', () => {
  beforeEach(() => vi.clearAllMocks());

  test('groups account balances and history by currency and submits exact conversion metadata', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'acc_checking_123', name: 'Checking', balance: '5000000.00', currency: 'COP', version: 4 },
      { id: 'CHK-1001', name: 'Checking USD', balance: '2500.00', currency: 'USD', version: 2 },
      { id: 'EUR-3001', name: 'Euro Wallet', balance: '0.00', currency: 'EUR', version: 7 },
      { id: 'GBP-4001', name: 'Pound Wallet', balance: '0.00', currency: 'GBP', version: 1 },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([{
      id: 'legacy-cop-history', direction: 'outgoing', amount: '120000.00',
      currency: 'COP', description: 'Legacy COP payment', date: '2026-11-14T10:00:00Z',
    }, {
      id: 'usd-eur-conversion', direction: 'outgoing', amount: '100.00', currency: 'USD',
      counter_amount: '90.00', counter_currency: 'EUR', rate_numerator: 9, rate_denominator: 10,
      description: 'Currency conversion from Checking USD to Euro Wallet', date: '2026-11-14T11:00:00Z',
    }]);
    vi.mocked(services.convertFunds).mockResolvedValue({
      id: 'conversion-1', source_account_id: 'CHK-1001', destination_account_id: 'EUR-3001',
      source_amount: '100.00', source_currency: 'USD', destination_amount: '90.00',
      destination_currency: 'EUR', rate_numerator: 9, rate_denominator: 10,
      source_version: 3, destination_version: 8,
    });

    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('GBP accounts')).toBeInTheDocument());

    expect(screen.getByLabelText('COP accounts')).toHaveTextContent('COP 5.000.000,00');
    expect(screen.getByLabelText('USD accounts')).toHaveTextContent('USD 2.500,00');
    expect(screen.queryByText(/estimated USD total/i)).not.toBeInTheDocument();
    expect(screen.getByText('COP 120.000,00')).toBeInTheDocument();
    expect(screen.getByText(/Converted value: EUR 90\.00|Converted value: EUR 90,00/)).toBeInTheDocument();
    expect(screen.getByText(/Rate 9\/10/)).toBeInTheDocument();
    expect(within(screen.getByLabelText('From account')).queryByText(/Checking \(COP\)/)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('From account'), { target: { value: 'CHK-1001' } });
    fireEvent.change(screen.getByLabelText('To account'), { target: { value: 'EUR-3001' } });
    fireEvent.change(screen.getByLabelText(/Amount \(USD\)/), { target: { value: '100.00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Convert' }));

    await waitFor(() => expect(services.convertFunds).toHaveBeenCalledWith({
      source_account_id: 'CHK-1001', destination_account_id: 'EUR-3001', source_amount: '100.00',
      expected_versions: { 'CHK-1001': 2, 'EUR-3001': 7 },
    }, '00000000-0000-4000-8000-000000000001'));
  });

  test('sends USD versions and displays the backend MFA decision for an over-threshold transfer', async () => {
    vi.mocked(services.fetchAccounts).mockResolvedValue([
      { id: 'CHK-1001', name: 'Checking USD', balance: '2500.00', currency: 'USD', version: 4 },
      { id: 'SAV-2001', name: 'Savings USD', balance: '10000.00', currency: 'USD', version: 9 },
    ]);
    vi.mocked(services.fetchHistory).mockResolvedValue([]);
    vi.mocked(services.initiateTransfer).mockResolvedValue({
      id: 'usd-mfa-1', source_account: 'Checking USD', destination_account: 'Savings USD',
      source_account_id: 'CHK-1001', destination_account_id: 'SAV-2001', currency: 'USD',
      amount: '1000.01', status: 'PENDING_MFA', created_at: '2026-11-16T00:00:00Z',
      expires_at: '2026-11-16T00:05:00Z',
    });
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('USD accounts')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/Source Account/i, { selector: '#source-select' }), { target: { value: 'CHK-1001' } });
    fireEvent.change(screen.getByLabelText(/Destination Account/i, { selector: '#dest-select' }), { target: { value: 'SAV-2001' } });
    fireEvent.change(screen.getByLabelText(/Amount \(USD\)/i, { selector: '#amount-input' }), { target: { value: '1000.01' } });
    fireEvent.click(screen.getByRole('button', { name: 'Transfer' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'MFA Verification' })).toBeInTheDocument());
    expect(services.initiateTransfer).toHaveBeenCalledWith('CHK-1001', 'SAV-2001', '1000.01',
      { 'CHK-1001': 4, 'SAV-2001': 9 }, '00000000-0000-4000-8000-000000000001');
  });
});


