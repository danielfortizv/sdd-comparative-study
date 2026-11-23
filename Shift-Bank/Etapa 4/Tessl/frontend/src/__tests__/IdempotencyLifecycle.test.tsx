import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { ConversionModal } from '../components/ConversionModal';
import { api, ApiError } from '../api/client';
import { Account, TransferLimits, MfaStatus } from '../api/types';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<any>('../api/client');
  return {
    ...actual,
    api: {
      getAccounts: vi.fn(),
      getTransactions: vi.fn(),
      getMfaStatus: vi.fn(),
      getBeneficiaries: vi.fn(),
      getRecurringSchedules: vi.fn(),
      getLimits: vi.fn(),
      executeTransfer: vi.fn(),
      executeAchTransfer: vi.fn(),
      executeConversion: vi.fn(),
      createRecurringSchedule: vi.fn(),
      pauseRecurringSchedule: vi.fn(),
      resumeRecurringSchedule: vi.fn(),
      cancelRecurringSchedule: vi.fn(),
      updateLimits: vi.fn(),
    },
  };
});

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
    balance: '500.00',
    currency: 'EUR',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockLimits: TransferLimits = {
  per_transaction_limit: '5000.00',
  daily_limit: '10000.00',
  current_daily_total: '0.00',
  remaining_daily_limit: '10000.00',
  reference_currency: 'USD',
};

const mockMfaStatus: MfaStatus = {
  threshold: '1000.00',
  locked: false,
  remaining_attempts: 3,
};

describe('Frontend D-13 Idempotency Key Lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getAccounts).mockResolvedValue(mockAccounts);
    vi.mocked(api.getTransactions).mockResolvedValue([]);
    vi.mocked(api.getMfaStatus).mockResolvedValue(mockMfaStatus);
    vi.mocked(api.getBeneficiaries).mockResolvedValue([]);
    vi.mocked(api.getRecurringSchedules).mockResolvedValue([]);
    vi.mocked(api.getLimits).mockResolvedValue(mockLimits);
  });

  it('internal transfer retry preserves the exact same Idempotency-Key and payload after transport error', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    // Open transfer modal
    fireEvent.click(screen.getByTestId('nav-transfer-btn'));
    expect(screen.getByTestId('transfer-modal')).toBeInTheDocument();

    // Fill form: 100.00 from account 1 to account 2
    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '100.00' } });
    fireEvent.change(screen.getByTestId('transfer-desc-input'), { target: { value: 'Rent buffer' } });

    // Mock first attempt fails with transport error (status 0 / timeout)
    vi.mocked(api.executeTransfer).mockRejectedValueOnce(
      new ApiError(0, 'Network timeout connecting to bank server')
    );

    // Submit first attempt
    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    const [firstPayload, firstKey] = vi.mocked(api.executeTransfer).mock.calls[0];
    expect(firstKey).toBeDefined();
    expect(typeof firstKey).toBe('string');
    expect(firstKey?.length).toBeGreaterThan(10);
    expect(firstPayload.amount).toBe('100.00');
    expect(firstPayload.expected_from_version).toBe(1);

    // Error is displayed to the user in modal
    await waitFor(() => {
      expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
        'Network timeout connecting to bank server'
      );
    });

    // Mock second attempt succeeds
    vi.mocked(api.executeTransfer).mockResolvedValueOnce({
      id: 99,
      operation_id: 'op-99',
      from_account_id: 1,
      to_account_id: 2,
      amount: '100.00',
      currency: 'USD',
      status: 'completed',
      created_at: new Date().toISOString(),
    });

    // User clicks retry with the SAME form payload
    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(2);
    });

    const [secondPayload, secondKey] = vi.mocked(api.executeTransfer).mock.calls[1];

    // D-13 Requirement: exactly the SAME Idempotency-Key and payload on retry
    expect(secondKey).toBe(firstKey);
    expect(secondPayload).toEqual(firstPayload);
  });

  it('internal transfer generates a fresh Idempotency-Key when form parameters change', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '100.00' } });

    vi.mocked(api.executeTransfer).mockRejectedValueOnce(new ApiError(500, 'Server error'));

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    const [, firstKey] = vi.mocked(api.executeTransfer).mock.calls[0];

    // User changes amount from 100.00 to 150.00
    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '150.00' } });

    vi.mocked(api.executeTransfer).mockResolvedValueOnce({
      id: 100,
      operation_id: 'op-100',
      from_account_id: 1,
      to_account_id: 2,
      amount: '150.00',
      currency: 'USD',
      status: 'completed',
      created_at: new Date().toISOString(),
    });

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(2);
    });

    const [secondPayload, secondKey] = vi.mocked(api.executeTransfer).mock.calls[1];

    // D-13 Requirement: Changed payload MUST receive a new key
    expect(secondKey).not.toBe(firstKey);
    expect(secondPayload.amount).toBe('150.00');
  });

  it('rapid multiple clicks do not dispatch duplicate pending transfer requests', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '50.00' } });

    // Mock slow response
    let resolveCall: any;
    vi.mocked(api.executeTransfer).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCall = resolve;
        })
    );

    const submitBtn = screen.getByTestId('transfer-submit-btn');

    // Rapid double-click
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    expect(api.executeTransfer).toHaveBeenCalledTimes(1);

    // Complete the call
    resolveCall({
      id: 101,
      from_account_id: 1,
      to_account_id: 2,
      amount: '50.00',
      status: 'completed',
      created_at: new Date().toISOString(),
    });
  });

  it('preserves the operation Idempotency-Key through the MFA verification flow', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    // Amount > $1000 requires MFA
    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '1500.00' } });

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    // TransferModal closes and MfaModal opens without calling API yet
    expect(api.executeTransfer).not.toHaveBeenCalled();
    expect(screen.getByTestId('mfa-modal')).toBeInTheDocument();
    expect(screen.getByTestId('mfa-amount')).toHaveTextContent('$1,500.00');

    // First attempt with incorrect PIN
    vi.mocked(api.executeTransfer).mockRejectedValueOnce(
      new ApiError(400, 'Invalid Security PIN', { remaining_attempts: 2 })
    );

    fireEvent.change(screen.getByTestId('mfa-pin-input'), { target: { value: '0000' } });
    fireEvent.click(screen.getByTestId('mfa-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    const [firstCallPayload, firstKey] = vi.mocked(api.executeTransfer).mock.calls[0];
    expect(firstCallPayload.pin).toBe('0000');
    expect(firstCallPayload.amount).toBe('1500.00');
    expect(firstKey).toBeDefined();

    // Error is shown, modal remains open
    await waitFor(() => {
      expect(screen.getByTestId('mfa-error-message')).toHaveTextContent('Invalid Security PIN');
    });

    // User enters correct PIN "1234" and submits
    vi.mocked(api.executeTransfer).mockResolvedValueOnce({
      id: 102,
      operation_id: 'op-102',
      from_account_id: 1,
      to_account_id: 2,
      amount: '1500.00',
      currency: 'USD',
      status: 'completed',
      created_at: new Date().toISOString(),
    });

    fireEvent.change(screen.getByTestId('mfa-pin-input'), { target: { value: '1234' } });
    fireEvent.click(screen.getByTestId('mfa-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(2);
    });

    const [secondCallPayload, secondKey] = vi.mocked(api.executeTransfer).mock.calls[1];

    // Preserves the operation's idempotency key
    expect(secondKey).toBe(firstKey);
    expect(secondCallPayload.pin).toBe('1234');
    expect(secondCallPayload.amount).toBe('1500.00');
  });

  it('ACH transfer retry preserves Idempotency-Key and payload after transport failure', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    // Switch to ACH tab
    fireEvent.click(screen.getByTestId('tab-ach-transfer'));

    fireEvent.change(screen.getByTestId('recipient-name-input'), { target: { value: 'Acme Corp' } });
    fireEvent.change(screen.getByTestId('routing-number-input'), { target: { value: '123456789' } });
    fireEvent.change(screen.getByTestId('account-number-input'), { target: { value: '987654321' } });
    fireEvent.change(screen.getByTestId('bank-name-input'), { target: { value: 'First National Bank' } });
    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '250.00' } });

    vi.mocked(api.executeAchTransfer).mockRejectedValueOnce(
      new ApiError(0, 'Network connection reset by peer')
    );

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeAchTransfer).toHaveBeenCalledTimes(1);
    });

    const [firstAchPayload, firstAchKey] = vi.mocked(api.executeAchTransfer).mock.calls[0];
    expect(firstAchKey).toBeDefined();

    vi.mocked(api.executeAchTransfer).mockResolvedValueOnce({
      id: 201,
      from_account_id: 1,
      recipient_name: 'Acme Corp',
      routing_number: '123456789',
      account_number: '987654321',
      bank_name: 'First National Bank',
      amount: '250.00',
      status: 'pending',
      created_at: new Date().toISOString(),
    });

    // Retry submission with identical inputs
    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeAchTransfer).toHaveBeenCalledTimes(2);
    });

    const [secondAchPayload, secondAchKey] = vi.mocked(api.executeAchTransfer).mock.calls[1];

    expect(secondAchKey).toBe(firstAchKey);
    expect(secondAchPayload).toEqual(firstAchPayload);
  });

  it('ConversionModal FX conversion retry preserves Idempotency-Key and payload', async () => {
    const handleSuccess = vi.fn();
    const handleRefresh = vi.fn();
    const handleClose = vi.fn();

    render(
      <ConversionModal
        isOpen={true}
        onClose={handleClose}
        accounts={mockAccounts}
        onConversionSuccess={handleSuccess}
        onRefreshAccounts={handleRefresh}
      />
    );

    fireEvent.change(screen.getByLabelText(/Source Amount/i), { target: { value: '100.00' } });

    vi.mocked(api.executeConversion).mockRejectedValueOnce(
      new ApiError(0, 'Failed to fetch currency conversion')
    );

    fireEvent.click(screen.getByTestId('submit-conversion-btn'));

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledTimes(1);
    });

    const [firstConvPayload, firstConvKey] = vi.mocked(api.executeConversion).mock.calls[0];
    expect(firstConvKey).toBeDefined();

    await waitFor(() => {
      expect(screen.getByTestId('conversion-error')).toHaveTextContent(
        'Failed to fetch currency conversion'
      );
    });

    vi.mocked(api.executeConversion).mockResolvedValueOnce({
      id: 301,
      operation_id: 'conv-301',
      from_account_id: 1,
      to_account_id: 3,
      source_currency: 'USD',
      destination_currency: 'EUR',
      source_amount: '100.00',
      destination_amount: '90.00',
      exchange_rate_display: '0.9000',
      rate_numerator: 9,
      rate_denominator: 10,
      rate_version: 'v1.0-simulated',
      rounding_residual: '0.00',
      from_account_version: 2,
      to_account_version: 2,
      status: 'completed',
      created_at: new Date().toISOString(),
    });

    // Retry with unchanged amount
    fireEvent.click(screen.getByTestId('submit-conversion-btn'));

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledTimes(2);
    });

    const [secondConvPayload, secondConvKey] = vi.mocked(api.executeConversion).mock.calls[1];

    expect(secondConvKey).toBe(firstConvKey);
    expect(secondConvPayload).toEqual(firstConvPayload);
    expect(handleSuccess).toHaveBeenCalledTimes(1);
  });

  it('ConversionModal generates a fresh Idempotency-Key when amount changes', async () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    fireEvent.change(screen.getByLabelText(/Source Amount/i), { target: { value: '100.00' } });

    vi.mocked(api.executeConversion).mockRejectedValueOnce(new ApiError(500, 'Server conversion fault'));

    fireEvent.click(screen.getByTestId('submit-conversion-btn'));

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledTimes(1);
    });

    const [, firstKey] = vi.mocked(api.executeConversion).mock.calls[0];

    // Change amount to 200.00
    fireEvent.change(screen.getByLabelText(/Source Amount/i), { target: { value: '200.00' } });

    vi.mocked(api.executeConversion).mockResolvedValueOnce({
      id: 302,
      operation_id: 'conv-302',
      from_account_id: 1,
      to_account_id: 3,
      source_currency: 'USD',
      destination_currency: 'EUR',
      source_amount: '200.00',
      destination_amount: '180.00',
      exchange_rate_display: '0.9000',
      rate_numerator: 9,
      rate_denominator: 10,
      rate_version: 'v1.0-simulated',
      rounding_residual: '0.00',
      from_account_version: 2,
      to_account_version: 2,
      status: 'completed',
      created_at: new Date().toISOString(),
    });

    fireEvent.click(screen.getByTestId('submit-conversion-btn'));

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledTimes(2);
    });

    const [secondPayload, secondKey] = vi.mocked(api.executeConversion).mock.calls[1];

    expect(secondKey).not.toBe(firstKey);
    expect(secondPayload.source_amount).toBe('200.00');
  });

  it('HTTP 409 ACCOUNT_VERSION_CONFLICT refreshes accounts and resets operation state without auto-retry', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '80.00' } });

    vi.mocked(api.executeTransfer).mockRejectedValueOnce(
      new ApiError(
        409,
        'Account version mismatch. Expected 1, found 2',
        {
          code: 'ACCOUNT_VERSION_CONFLICT',
          message: 'Account version mismatch. Expected 1, found 2',
        },
        'ACCOUNT_VERSION_CONFLICT'
      )
    );

    // Initial getAccounts called on mount
    expect(api.getAccounts).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    // On 409 ACCOUNT_VERSION_CONFLICT, App.tsx refreshes accounts immediately
    await waitFor(() => {
      expect(api.getAccounts).toHaveBeenCalledTimes(2);
    });

    // Error message indicates conflict and refresh
    await waitFor(() => {
      expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
        'Account version mismatch. Expected 1, found 2'
      );
    });

    // Crucial: No automatic resubmission occurred!
    expect(api.executeTransfer).toHaveBeenCalledTimes(1);
  });

  it('HTTP 409 IDEMPOTENCY_KEY_REUSE displays idempotency conflict message without refreshing accounts or auto-retrying', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '80.00' } });

    vi.mocked(api.executeTransfer).mockRejectedValueOnce(
      new ApiError(
        409,
        'Idempotency key was previously committed with different request parameters',
        {
          code: 'IDEMPOTENCY_KEY_REUSE',
          message: 'Idempotency key was previously committed with different request parameters',
        },
        'IDEMPOTENCY_KEY_REUSE'
      )
    );

    expect(api.getAccounts).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    // Crucial: IDEMPOTENCY_KEY_REUSE must NOT be treated as a version conflict and must NOT refresh accounts
    expect(api.getAccounts).toHaveBeenCalledTimes(1);

    // Displays clear idempotency conflict message
    await waitFor(() => {
      expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
        'Idempotency key was previously committed with different request parameters'
      );
    });

    // No auto-resubmission
    expect(api.executeTransfer).toHaveBeenCalledTimes(1);
  });

  it('Unknown HTTP 409 error displays generic message without assuming account version conflict', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('Primary Checking')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('nav-transfer-btn'));

    fireEvent.change(screen.getByTestId('transfer-amount-input'), { target: { value: '80.00' } });

    vi.mocked(api.executeTransfer).mockRejectedValueOnce(
      new ApiError(
        409,
        'Custom transaction conflict occurred on backend',
        { code: 'GENERIC_CONFLICT' },
        'GENERIC_CONFLICT'
      )
    );

    expect(api.getAccounts).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('transfer-submit-btn'));

    await waitFor(() => {
      expect(api.executeTransfer).toHaveBeenCalledTimes(1);
    });

    // Does NOT trigger account reload
    expect(api.getAccounts).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByTestId('transfer-error-message')).toHaveTextContent(
        'Custom transaction conflict occurred on backend'
      );
    });
  });
});
