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

const mockTransactions: Transaction[] = [
  {
    id: 101,
    account_id: 1,
    account_name: 'Primary Checking',
    transfer_id: null,
    transaction_type: 'credit',
    amount: 3000.0,
    balance_after: 3000.0,
    description: 'Payroll Direct Deposit',
    reference: 'PAY-88210',
    created_at: '2026-01-15T12:00:00Z',
  },
  {
    id: 102,
    account_id: 1,
    account_name: 'Primary Checking',
    transfer_id: null,
    transaction_type: 'debit',
    amount: 500.0,
    balance_after: 2500.0,
    description: 'Utility Bill Payment',
    reference: 'UTL-44912',
    created_at: '2026-01-20T14:30:00Z',
  },
  {
    id: 103,
    account_id: 2,
    account_name: 'Standard Savings',
    transfer_id: null,
    transaction_type: 'credit',
    amount: 10000.0,
    balance_after: 10000.0,
    description: 'Initial Savings Deposit',
    reference: 'DEP-10001',
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
  });

  it('renders credits with + and debits with - prefix', () => {
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

    expect(creditAmount).toHaveTextContent('+$3,000.00');
    expect(debitAmount).toHaveTextContent('-$500.00');
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
  });
});
