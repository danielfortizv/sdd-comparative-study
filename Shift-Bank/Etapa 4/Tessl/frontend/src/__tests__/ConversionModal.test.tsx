import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversionModal } from '../components/ConversionModal';
import { Account } from '../api/types';
import { api, ApiError } from '../api/client';

vi.mock('../api/client', () => ({
  generateIdempotencyKey: () => 'mock-idempotency-key-uuid',
  api: {
    executeConversion: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    data: any;
    code: string;
    constructor(status: number, message: string, data?: any, code?: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.data = data;
      this.code =
        code ||
        (data?.code
          ? String(data.code)
          : status === 409 && message.toLowerCase().includes('version')
          ? 'ACCOUNT_VERSION_CONFLICT'
          : 'ERROR');
    }
  },
}));

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
    account_number: 'EUR-3001',
    account_type: 'checking',
    account_name: 'Euro Account',
    balance: '100.00',
    currency: 'EUR',
    version: 3,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 3,
    user_id: 1,
    account_number: 'GBP-4001',
    account_type: 'savings',
    account_name: 'British Pound Account',
    balance: '80.00',
    currency: 'GBP',
    version: 5,
    created_at: '2026-01-01T00:00:00Z',
  },
];

describe('ConversionModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders modal when open and filters destination accounts to different currencies', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    expect(screen.getByTestId('conversion-modal')).toBeInTheDocument();
    expect(screen.getByText('Simulated Currency Conversion')).toBeInTheDocument();

    const destSelect = screen.getByLabelText(/Destination Account/i);
    expect(destSelect).toBeInTheDocument();
    // Destination options must not contain USD accounts when source is USD (CHK-1001)
    expect(destSelect).not.toHaveTextContent('Primary Checking');
    expect(destSelect).toHaveTextContent('Euro Account');
    expect(destSelect).toHaveTextContent('British Pound Account');
  });

  it('calculates live destination amount preview using D-03 reference rates', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    // Enter 100.00 USD -> EUR at 0.9000 rate gives EUR 90.00
    fireEvent.change(amountInput, { target: { value: '100' } });

    expect(screen.getByTestId('preview-destination-amount')).toHaveTextContent('EUR 90.00');
    expect(screen.getByText(/1 USD = 0.9000 EUR/i)).toBeInTheDocument();
    expect(screen.getByText(/Estimated USD Equivalent: \$100.00 USD/i)).toBeInTheDocument();
  });

  it('calculates live preview respecting single ROUND_HALF_UP rounding boundaries', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    // Select Euro Account as source (EUR -> USD rate 10/9)
    const sourceSelect = screen.getByLabelText(/Source Account/i);
    fireEvent.change(sourceSelect, { target: { value: '2' } });

    const amountInput = screen.getByLabelText(/Source Amount/i);

    // 0.04 EUR * 10 / 9 = 0.0444... rounds down to 0.04 USD
    fireEvent.change(amountInput, { target: { value: '0.04' } });
    expect(screen.getByTestId('preview-destination-amount')).toHaveTextContent('USD 0.04');

    // 0.05 EUR * 10 / 9 = 0.0555... rounds up to 0.06 USD
    fireEvent.change(amountInput, { target: { value: '0.05' } });
    expect(screen.getByTestId('preview-destination-amount')).toHaveTextContent('USD 0.06');

    // Select British Pound Account as source (GBP -> EUR rate 9/8)
    fireEvent.change(sourceSelect, { target: { value: '3' } });
    // Destination defaults to Euro Account (EUR)
    // 0.04 GBP * 9 / 8 = 0.045000... exact half boundary rounds UP to 0.05 EUR
    fireEvent.change(amountInput, { target: { value: '0.04' } });
    expect(screen.getByTestId('preview-destination-amount')).toHaveTextContent('EUR 0.05');
  });

  it('strictly validates precision and rejects amounts with excess decimal places', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '10.255' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('conversion-error')).toHaveTextContent(
      'Invalid monetary amount. Please provide a positive amount with at most 2 decimal places.'
    );
    expect(api.executeConversion).not.toHaveBeenCalled();
  });

  it('strictly rejects zero or negative conversion amounts', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '0.00' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('conversion-error')).toHaveTextContent(
      'Conversion amount must be strictly positive.'
    );
    expect(api.executeConversion).not.toHaveBeenCalled();
  });

  it('strictly rejects conversion when source account has insufficient funds', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    // Primary Checking has balance "2500.00" USD -> request 2500.01
    fireEvent.change(amountInput, { target: { value: '2500.01' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('conversion-error')).toHaveTextContent(
      'Insufficient funds in Primary Checking. Available: $2,500.00'
    );
    expect(api.executeConversion).not.toHaveBeenCalled();
  });

  it('enforces exact MFA Security PIN boundary at $1,000.00 USD equivalent', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);

    // Exactly $1,000.00 USD does NOT require MFA (> $1,000 required)
    fireEvent.change(amountInput, { target: { value: '1000.00' } });
    expect(screen.queryByLabelText(/Security PIN Required/i)).not.toBeInTheDocument();

    // $1,000.01 USD DOES require MFA
    fireEvent.change(amountInput, { target: { value: '1000.01' } });
    expect(screen.getByLabelText(/Security PIN Required/i)).toBeInTheDocument();

    // Switch to Euro Account: base factor 10/9 -> exactly 900.00 EUR == 1000.00 USD
    const sourceSelect = screen.getByLabelText(/Source Account/i);
    fireEvent.change(sourceSelect, { target: { value: '2' } });

    fireEvent.change(amountInput, { target: { value: '900.00' } });
    expect(screen.queryByLabelText(/Security PIN Required/i)).not.toBeInTheDocument();

    fireEvent.change(amountInput, { target: { value: '900.01' } });
    expect(screen.getByLabelText(/Security PIN Required/i)).toBeInTheDocument();
  });

  it('rejects submission when MFA PIN is required but omitted', () => {
    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '1500.00' } });

    expect(screen.getByLabelText(/Security PIN Required/i)).toBeInTheDocument();

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('conversion-error')).toHaveTextContent(
      'Security PIN is required for conversions exceeding $1,000 USD equivalent.'
    );
    expect(api.executeConversion).not.toHaveBeenCalled();
  });

  it('submits conversion with canonical decimal string and D-14 expected versions', async () => {
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    (api.executeConversion as any).mockResolvedValueOnce({
      id: 1,
      operation_id: 'test-uuid-1234',
      from_account_id: 1,
      to_account_id: 2,
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
      to_account_version: 4,
      status: 'completed',
      created_at: '2026-01-01T00:00:00Z',
    });

    render(
      <ConversionModal
        isOpen={true}
        onClose={onClose}
        accounts={mockAccounts}
        onConversionSuccess={onSuccess}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '100' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledWith(
        {
          from_account_id: 1,
          to_account_id: 2,
          source_amount: '100.00',
          expected_from_version: 1,
          expected_to_version: 3,
          description: undefined,
          pin: undefined,
        },
        expect.any(String)
      );
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('submits conversion with PIN when MFA is required', async () => {
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    (api.executeConversion as any).mockResolvedValueOnce({
      id: 2,
      operation_id: 'test-uuid-5678',
      from_account_id: 1,
      to_account_id: 2,
      source_currency: 'USD',
      destination_currency: 'EUR',
      source_amount: '1500.00',
      destination_amount: '1350.00',
      exchange_rate_display: '0.9000',
      rate_numerator: 9,
      rate_denominator: 10,
      rate_version: 'v1.0-simulated',
      rounding_residual: '0.00',
      from_account_version: 2,
      to_account_version: 4,
      status: 'completed',
      created_at: '2026-01-01T00:00:00Z',
    });

    render(
      <ConversionModal
        isOpen={true}
        onClose={onClose}
        accounts={mockAccounts}
        onConversionSuccess={onSuccess}
        onRefreshAccounts={vi.fn()}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '1500.00' } });

    const pinInput = screen.getByLabelText(/Security PIN Required/i);
    fireEvent.change(pinInput, { target: { value: '1234' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.executeConversion).toHaveBeenCalledWith(
        {
          from_account_id: 1,
          to_account_id: 2,
          source_amount: '1500.00',
          expected_from_version: 1,
          expected_to_version: 3,
          description: undefined,
          pin: '1234',
        },
        expect.any(String)
      );
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('handles account version conflict (HTTP 409) and invokes onRefreshAccounts', async () => {
    const onRefresh = vi.fn();

    (api.executeConversion as any).mockRejectedValueOnce(
      new ApiError(409, 'Conflict: Account version mismatch')
    );

    render(
      <ConversionModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onConversionSuccess={vi.fn()}
        onRefreshAccounts={onRefresh}
      />
    );

    const amountInput = screen.getByLabelText(/Source Amount/i);
    fireEvent.change(amountInput, { target: { value: '100' } });

    const submitBtn = screen.getByTestId('submit-conversion-btn');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('conversion-error')).toHaveTextContent(
        'Account version conflict detected: Account balances have changed. Refreshing accounts...'
      );
      expect(onRefresh).toHaveBeenCalled();
    });
  });
});
