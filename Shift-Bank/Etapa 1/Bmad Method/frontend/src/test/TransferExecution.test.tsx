import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import App from '../App';
import * as apiClient from '../api/client';
import { Account } from '../types/account';

const mockAccountsInitial: Account[] = [
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

const mockAccountsAfterTransfer: Account[] = [
  {
    id: 'CHK-1001',
    nickname: 'Primary Checking',
    type: 'CHECKING',
    account_type: 'CHECKING',
    balance_cents: 225000,
    balance_formatted: '$2,250.00',
  },
  {
    id: 'SAV-2001',
    nickname: 'High-Yield Savings',
    type: 'SAVINGS',
    account_type: 'SAVINGS',
    balance_cents: 1270075,
    balance_formatted: '$12,700.75',
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

describe('Story 2.3: End-to-End Transfer Execution & View Synchronization', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('AC-1: submit button enters disabled state displaying spinner and Processing Transfer... while in-flight', async () => {
    // Mock fetchAccounts to return initial accounts
    vi.spyOn(apiClient, 'fetchAccounts').mockResolvedValue(mockAccountsInitial);

    // Mock initiateTransfer with a deferred promise so we can assert the in-flight state
    let resolveTransfer: (value: apiClient.TransferResponseData) => void;
    const transferPromise = new Promise<apiClient.TransferResponseData>((resolve) => {
      resolveTransfer = resolve;
    });
    vi.spyOn(apiClient, 'initiateTransfer').mockReturnValue(transferPromise);

    render(<App />);

    // Wait for accounts to load
    await waitFor(() => {
      expect(screen.getByTestId('account-card-CHK-1001')).toBeInTheDocument();
    });

    const amountInput = screen.getByTestId('transfer-amount-input');
    const submitBtn = screen.getByTestId('transfer-submit-btn');

    // Enter valid amount $250.00
    fireEvent.change(amountInput, { target: { value: '250.00' } });
    expect(submitBtn).toBeEnabled();

    // Submit transfer
    fireEvent.click(submitBtn);

    // AC-1: Immediately disabled with spinner and "Processing Transfer..."
    expect(submitBtn).toBeDisabled();
    expect(screen.getByTestId('submit-spinner')).toBeInTheDocument();
    expect(submitBtn).toHaveTextContent('Processing Transfer...');

    // Resolve transfer to clean up
    await act(async () => {
      resolveTransfer!({
        transfer: {
          id: 'TRF-TEST01',
          source_account_id: 'CHK-1001',
          destination_account_id: 'SAV-2001',
          amount_cents: 25000,
          amount_formatted: '$250.00',
          status: 'COMPLETED',
          created_at: '2026-10-20T14:30:00Z',
        },
        status: 'COMPLETED',
      });
    });
  });

  it('AC-2, AC-3, AC-4: displays emerald confirmation toast, resets amount, updates balances synchronously, and triggers 400ms highlight flash', async () => {
    // Mock initial fetch and subsequent refreshed fetch
    const fetchAccountsSpy = vi
      .spyOn(apiClient, 'fetchAccounts')
      .mockResolvedValueOnce(mockAccountsInitial)
      .mockResolvedValueOnce(mockAccountsAfterTransfer);

    vi.spyOn(apiClient, 'initiateTransfer').mockResolvedValue({
      transfer: {
        id: 'TRF-1082',
        source_account_id: 'CHK-1001',
        destination_account_id: 'SAV-2001',
        amount_cents: 25000,
        amount_formatted: '$250.00',
        status: 'COMPLETED',
        created_at: '2026-10-20T14:30:00Z',
      },
      status: 'COMPLETED',
    });

    render(<App />);

    // Wait for accounts to load
    await waitFor(() => {
      expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    });

    const amountInput = screen.getByTestId('transfer-amount-input') as HTMLInputElement;
    const submitBtn = screen.getByTestId('transfer-submit-btn');

    // Fill in amount $250.00
    fireEvent.change(amountInput, { target: { value: '250.00' } });
    expect(amountInput.value).toBe('250.00');

    // Click submit
    fireEvent.click(submitBtn);

    // AC-2: Emerald confirmation toast appears with transfer reference
    await waitFor(() => {
      expect(screen.getByTestId('confirmation-toast')).toBeInTheDocument();
    });
    expect(screen.getByTestId('confirmation-toast')).toHaveTextContent(
      'Transfer of $250.00 to High-Yield Savings completed. Reference: TRF-1082'
    );

    // AC-2: Amount input is reset
    expect(amountInput.value).toBe('');

    // AC-3: Balances update synchronously from backend without optimistic guessing
    await waitFor(() => {
      expect(screen.getByText('$2,250.00')).toBeInTheDocument();
      expect(screen.getByText('$12,700.75')).toBeInTheDocument();
    });
    expect(fetchAccountsSpy).toHaveBeenCalledTimes(2);

    // AC-4: Source and destination cards display highlight flash (data-highlighted="true")
    const chkCard = screen.getByTestId('account-card-CHK-1001');
    const savCard = screen.getByTestId('account-card-SAV-2001');
    const rsvCard = screen.getByTestId('account-card-RSV-3001');

    expect(chkCard.getAttribute('data-highlighted')).toBe('true');
    expect(savCard.getAttribute('data-highlighted')).toBe('true');
    expect(rsvCard.getAttribute('data-highlighted')).toBe('false');
  });
});
