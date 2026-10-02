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

    expect(screen.getByText(/\b5[., ]000[., ]000/)).toBeInTheDocument();
    expect(screen.getByText(/\b15[., ]000[., ]000/)).toBeInTheDocument();
    expect(screen.queryByText('acc_checking_123')).not.toBeInTheDocument();
    expect(screen.queryByText('acc_savings_456')).not.toBeInTheDocument();
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
    const amountInput = screen.getByLabelText(/Amount/i);
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
        '300000.00'
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

    const amountInput = screen.getByLabelText(/Amount/i);
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
        '200000.00'
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
    const amountInput = screen.getByLabelText(/Amount/i);
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
      expect(services.confirmMFA).toHaveBeenCalledWith('tr_sensitive_888', '123456');
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
