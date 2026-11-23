import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TransactionHistory } from '../components/TransactionHistory';
import { Transaction, Account } from '../api/types';

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
  {
    id: 4,
    user_id: 1,
    account_number: 'GBP-4001',
    account_type: 'checking',
    account_name: 'British Pound Checking',
    balance: '400.00',
    currency: 'GBP',
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockTransactions: Transaction[] = [
  {
    id: 101,
    account_id: 1,
    account_name: 'Primary Checking',
    transfer_id: null,
    transaction_type: 'credit',
    amount: '3000.00',
    balance_after: '3000.00',
    currency: 'USD',
    description: 'Payroll Direct Deposit',
    reference: 'PAY-88210',
    status: 'completed',
    created_at: '2026-01-15T12:00:00Z',
  },
  {
    id: 102,
    account_id: 1,
    account_name: 'Primary Checking',
    transfer_id: null,
    transaction_type: 'debit',
    amount: '500.00',
    balance_after: '2500.00',
    currency: 'USD',
    description: 'Utility Bill Payment',
    reference: 'UTL-44912',
    status: 'completed',
    created_at: '2026-01-20T14:30:00Z',
  },
  {
    id: 103,
    account_id: 2,
    account_name: 'Standard Savings',
    transfer_id: null,
    transaction_type: 'credit',
    amount: '10000.00',
    balance_after: '10000.00',
    currency: 'USD',
    description: 'Initial Savings Deposit',
    reference: 'DEP-10001',
    status: 'completed',
    created_at: '2026-01-01T09:00:00Z',
  },
];

describe('TransactionHistory Component', () => {
  it('renders all transactions when selectedAccountId is null', () => {
    render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('transaction-row-101')).toBeInTheDocument();
    expect(screen.getByTestId('transaction-row-102')).toBeInTheDocument();
    expect(screen.getByTestId('transaction-row-103')).toBeInTheDocument();
    expect(screen.getByTestId('tx-count-badge')).toHaveTextContent('3 movements');
  });

  it('renders credits with + and debits with - prefix using exact decimal currency formatting', () => {
    render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    const creditAmount = screen.getByTestId('tx-amount-101');
    const debitAmount = screen.getByTestId('tx-amount-102');
    const creditRow = creditAmount.closest('td');
    const debitRow = debitAmount.closest('td');

    expect(creditAmount).toHaveTextContent('+$3,000.00');
    expect(creditRow).toHaveClass('credit');
    expect(debitAmount).toHaveTextContent('-$500.00');
    expect(debitRow).toHaveClass('debit');

    expect(screen.getByTestId('tx-balance-after-101')).toHaveTextContent('$3,000.00');
    expect(screen.getByTestId('tx-balance-after-102')).toHaveTextContent('$2,500.00');
  });

  it('renders multicurrency transactions with correct currency labels and symbols (USD, EUR, GBP)', () => {
    const multiCurrencyTxs: Transaction[] = [
      {
        id: 201,
        account_id: 1,
        account_name: 'Primary Checking',
        transaction_type: 'credit',
        amount: '1250.00',
        balance_after: '3750.00',
        currency: 'USD',
        description: 'USD Deposit',
        status: 'completed',
        created_at: '2026-02-01T10:00:00Z',
      },
      {
        id: 202,
        account_id: 3,
        account_name: 'Euro Checking',
        transaction_type: 'credit',
        amount: '90.00',
        balance_after: '590.00',
        currency: 'EUR',
        description: 'EUR Inflow',
        status: 'completed',
        created_at: '2026-02-01T11:00:00Z',
      },
      {
        id: 203,
        account_id: 4,
        account_name: 'British Pound Checking',
        transaction_type: 'debit',
        amount: '80.00',
        balance_after: '320.00',
        currency: 'GBP',
        description: 'GBP Outflow',
        status: 'completed',
        created_at: '2026-02-01T12:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={multiCurrencyTxs}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // USD
    expect(screen.getByTestId('tx-amount-201')).toHaveTextContent('+$1,250.00');
    expect(screen.getByTestId('tx-balance-after-201')).toHaveTextContent('$3,750.00');
    expect(screen.getByTestId('tx-account-201')).toHaveTextContent('Primary Checking (USD)');

    // EUR
    expect(screen.getByTestId('tx-amount-202')).toHaveTextContent('+€90.00');
    expect(screen.getByTestId('tx-balance-after-202')).toHaveTextContent('€590.00');
    expect(screen.getByTestId('tx-account-202')).toHaveTextContent('Euro Checking (EUR)');

    // GBP
    expect(screen.getByTestId('tx-amount-203')).toHaveTextContent('-£80.00');
    expect(screen.getByTestId('tx-balance-after-203')).toHaveTextContent('£320.00');
    expect(screen.getByTestId('tx-account-203')).toHaveTextContent('British Pound Checking (GBP)');
  });

  it('renders small monetary amounts without floating-point precision loss', () => {
    const smallAmountTxs: Transaction[] = [
      {
        id: 301,
        account_id: 1,
        account_name: 'Primary Checking',
        transaction_type: 'credit',
        amount: '0.05',
        balance_after: '0.05',
        currency: 'USD',
        description: 'Micro Dividend',
        status: 'completed',
        created_at: '2026-02-02T10:00:00Z',
      },
      {
        id: 302,
        account_id: 4,
        account_name: 'British Pound Checking',
        transaction_type: 'debit',
        amount: '0.02',
        balance_after: '399.98',
        currency: 'GBP',
        description: 'Micro Fee',
        status: 'completed',
        created_at: '2026-02-02T11:00:00Z',
      },
      {
        id: 303,
        account_id: 3,
        account_name: 'Euro Checking',
        transaction_type: 'debit',
        amount: '0.10',
        balance_after: '499.90',
        currency: 'EUR',
        description: 'Ten Cent Charge',
        status: 'completed',
        created_at: '2026-02-02T12:00:00Z',
      },
      {
        id: 304,
        account_id: 1,
        account_name: 'Primary Checking',
        transaction_type: 'credit',
        amount: '0.01',
        balance_after: '0.06',
        currency: 'USD',
        description: 'One Cent Credit',
        status: 'completed',
        created_at: '2026-02-02T13:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={smallAmountTxs}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('tx-amount-301')).toHaveTextContent('+$0.05');
    expect(screen.getByTestId('tx-balance-after-301')).toHaveTextContent('$0.05');

    expect(screen.getByTestId('tx-amount-302')).toHaveTextContent('-£0.02');
    expect(screen.getByTestId('tx-balance-after-302')).toHaveTextContent('£399.98');

    expect(screen.getByTestId('tx-amount-303')).toHaveTextContent('-€0.10');
    expect(screen.getByTestId('tx-balance-after-303')).toHaveTextContent('€499.90');

    expect(screen.getByTestId('tx-amount-304')).toHaveTextContent('+$0.01');
    expect(screen.getByTestId('tx-balance-after-304')).toHaveTextContent('$0.06');
  });

  it('renders currency conversion details with exact source/destination amounts and higher-precision exchange rates', () => {
    const conversionTransactions: Transaction[] = [
      {
        id: 401,
        account_id: 1,
        account_name: 'Primary Checking',
        conversion_id: 12,
        transaction_type: 'debit',
        amount: '100.00',
        balance_after: '2400.00',
        currency: 'USD',
        description: 'Converted to Euro Checking (EUR)',
        reference: 'CNV-00012-OUT',
        source_amount: '100.00',
        source_currency: 'USD',
        destination_amount: '90.00',
        destination_currency: 'EUR',
        exchange_rate_display: '0.9000000000',
        status: 'completed',
        created_at: '2026-02-03T10:00:00Z',
      },
      {
        id: 402,
        account_id: 3,
        account_name: 'Euro Checking',
        conversion_id: 12,
        transaction_type: 'credit',
        amount: '90.00',
        balance_after: '590.00',
        currency: 'EUR',
        description: 'Converted from Primary Checking (USD)',
        reference: 'CNV-00012-IN',
        source_amount: '100.00',
        source_currency: 'USD',
        destination_amount: '90.00',
        destination_currency: 'EUR',
        exchange_rate_display: '0.9000000000',
        status: 'completed',
        created_at: '2026-02-03T10:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={conversionTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // Debit side
    expect(screen.getByTestId('tx-conversion-badge-401')).toHaveTextContent('FX Conversion');
    expect(screen.getByTestId('tx-amount-401')).toHaveTextContent('-$100.00');
    expect(screen.getByTestId('tx-source-amount-401')).toHaveTextContent('$100.00');
    expect(screen.getByTestId('tx-destination-amount-401')).toHaveTextContent('€90.00');
    expect(screen.getByTestId('tx-exchange-rate-401')).toHaveTextContent('Rate: 1 USD = 0.9000000000 EUR');

    // Credit side
    expect(screen.getByTestId('tx-conversion-badge-402')).toHaveTextContent('FX Conversion');
    expect(screen.getByTestId('tx-amount-402')).toHaveTextContent('+€90.00');
    expect(screen.getByTestId('tx-source-amount-402')).toHaveTextContent('$100.00');
    expect(screen.getByTestId('tx-destination-amount-402')).toHaveTextContent('€90.00');
    expect(screen.getByTestId('tx-exchange-rate-402')).toHaveTextContent('Rate: 1 USD = 0.9000000000 EUR');
  });

  it('preserves exchange rates as higher-precision decimal strings without quantizing to two decimal places', () => {
    const highPrecisionRateTxs: Transaction[] = [
      {
        id: 403,
        account_id: 3,
        account_name: 'Euro Checking',
        conversion_id: 15,
        transaction_type: 'debit',
        amount: '90.00',
        balance_after: '410.00',
        currency: 'EUR',
        description: 'Converted to Primary Checking (USD)',
        reference: 'CNV-00015-OUT',
        source_amount: '90.00',
        source_currency: 'EUR',
        destination_amount: '100.00',
        destination_currency: 'USD',
        exchange_rate_display: '1.1111111111',
        status: 'completed',
        created_at: '2026-02-04T12:00:00Z',
      },
      {
        id: 404,
        account_id: 3,
        account_name: 'Euro Checking',
        conversion_id: 16,
        transaction_type: 'debit',
        amount: '90.00',
        balance_after: '320.00',
        currency: 'EUR',
        description: 'Converted to British Pound Checking (GBP)',
        reference: 'CNV-00016-OUT',
        source_amount: '90.00',
        source_currency: 'EUR',
        destination_amount: '80.00',
        destination_currency: 'GBP',
        exchange_rate_display: '0.8888888889',
        status: 'completed',
        created_at: '2026-02-04T13:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={highPrecisionRateTxs}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // Checks that high-precision strings are preserved without being truncated or rounded to two decimals
    expect(screen.getByTestId('tx-exchange-rate-403')).toHaveTextContent('Rate: 1 EUR = 1.1111111111 USD');
    expect(screen.getByTestId('tx-exchange-rate-404')).toHaveTextContent('Rate: 1 EUR = 0.8888888889 GBP');
  });

  it('renders small amount conversion details with exact two-decimal formatting', () => {
    const smallConversionTxs: Transaction[] = [
      {
        id: 405,
        account_id: 1,
        account_name: 'Primary Checking',
        conversion_id: 17,
        transaction_type: 'debit',
        amount: '0.05',
        balance_after: '2499.95',
        currency: 'USD',
        description: 'Micro Conversion to EUR',
        reference: 'CNV-00017-OUT',
        source_amount: '0.05',
        source_currency: 'USD',
        destination_amount: '0.05',
        destination_currency: 'EUR',
        exchange_rate_display: '0.9000000000',
        status: 'completed',
        created_at: '2026-02-05T14:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={smallConversionTxs}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('tx-amount-405')).toHaveTextContent('-$0.05');
    expect(screen.getByTestId('tx-source-amount-405')).toHaveTextContent('$0.05');
    expect(screen.getByTestId('tx-destination-amount-405')).toHaveTextContent('€0.05');
    expect(screen.getByTestId('tx-conversion-amounts-405')).toHaveTextContent('Conversion: $0.05 → €0.05');
  });

  it('renders transaction balances and status badges for pending, completed, and failed transactions', () => {
    const statusTransactions: Transaction[] = [
      {
        id: 501,
        account_id: 1,
        account_name: 'Primary Checking',
        transaction_type: 'credit',
        amount: '1000.00',
        balance_after: '3500.00',
        currency: 'USD',
        description: 'Completed Direct Deposit',
        status: 'completed',
        created_at: '2026-02-06T10:00:00Z',
      },
      {
        id: 502,
        account_id: 1,
        account_name: 'Primary Checking',
        transfer_id: 8,
        transaction_type: 'debit',
        amount: '200.00',
        balance_after: '3300.00',
        currency: 'USD',
        description: 'Pending ACH Transfer',
        status: 'pending',
        created_at: '2026-02-06T11:00:00Z',
      },
      {
        id: 503,
        account_id: 1,
        account_name: 'Primary Checking',
        transfer_id: 9,
        transaction_type: 'debit',
        amount: '150.00',
        balance_after: '3300.00',
        currency: 'USD',
        description: 'Failed ACH Transfer',
        status: 'failed',
        created_at: '2026-02-06T12:00:00Z',
      },
      {
        id: 504,
        account_id: 1,
        account_name: 'Primary Checking',
        transaction_type: 'debit',
        amount: '10.50',
        balance_after: '-10.50',
        currency: 'USD',
        description: 'Overdraft Fee',
        status: 'completed',
        created_at: '2026-02-06T13:00:00Z',
      },
    ];

    render(
      <TransactionHistory
        transactions={statusTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // Completed status
    expect(screen.getByTestId('tx-completed-badge-501')).toHaveTextContent('Completed');
    expect(screen.getByTestId('tx-balance-after-501')).toHaveTextContent('$3,500.00');

    // Pending status
    expect(screen.getByTestId('tx-pending-badge-502')).toHaveTextContent('Pending');
    expect(screen.getByTestId('tx-balance-after-502')).toHaveTextContent('$3,300.00');

    // Failed status
    expect(screen.getByTestId('tx-failed-badge-503')).toHaveTextContent('Failed');
    expect(screen.getByTestId('tx-balance-after-503')).toHaveTextContent('$3,300.00');

    // Negative balance formatting
    expect(screen.getByTestId('tx-balance-after-504')).toHaveTextContent('-$10.50');
  });

  it('filters transactions when an account is selected', () => {
    const { rerender } = render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('transaction-row-101')).toBeInTheDocument();
    expect(screen.getByTestId('transaction-row-102')).toBeInTheDocument();
    expect(screen.getByTestId('transaction-row-103')).toBeInTheDocument();

    // Selected account 2 (Savings)
    rerender(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={2}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.queryByTestId('transaction-row-101')).not.toBeInTheDocument();
    expect(screen.queryByTestId('transaction-row-102')).not.toBeInTheDocument();
    expect(screen.getByTestId('transaction-row-103')).toBeInTheDocument();
    expect(screen.getByTestId('tx-count-badge')).toHaveTextContent('1 movements');
  });

  it('allows clicking account filter tabs to switch views', () => {
    const onSelect = vi.fn();
    render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={onSelect}
      />
    );

    const checkingTab = screen.getByTestId('tab-account-1');
    fireEvent.click(checkingTab);
    expect(onSelect).toHaveBeenCalledWith(1);

    const eurTab = screen.getByTestId('tab-account-3');
    fireEvent.click(eurTab);
    expect(onSelect).toHaveBeenCalledWith(3);

    const allTab = screen.getByTestId('tab-all-accounts');
    fireEvent.click(allTab);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it('displays empty state when filtered account has no transactions', () => {
    render(
      <TransactionHistory
        transactions={[]}
        accounts={mockAccounts}
        selectedAccountId={1}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('empty-transactions-state')).toBeInTheDocument();
    expect(screen.getByText('No transactions found')).toBeInTheDocument();
  });

  it('displays loading skeleton when isLoading is true', () => {
    render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
        isLoading={true}
      />
    );

    expect(screen.getByTestId('transactions-loading')).toBeInTheDocument();
    expect(screen.queryByTestId('transaction-row-101')).not.toBeInTheDocument();
  });

  it('displays description and reference correctly', () => {
    render(
      <TransactionHistory
        transactions={mockTransactions}
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByText('Payroll Direct Deposit')).toBeInTheDocument();
    expect(screen.getByTestId('tx-ref-101')).toHaveTextContent('Ref: PAY-88210');
  });
});
