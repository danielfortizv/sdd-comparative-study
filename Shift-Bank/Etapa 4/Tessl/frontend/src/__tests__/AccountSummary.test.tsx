import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AccountSummary } from '../components/AccountSummary';
import { Account } from '../api/types';

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
    account_name: 'Euro Account',
    balance: '90.00',
    currency: 'EUR',
    version: 3,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 4,
    user_id: 1,
    account_number: 'GBP-4001',
    account_type: 'savings',
    account_name: 'British Pound Account',
    balance: '80.00',
    currency: 'GBP',
    version: 4,
    created_at: '2026-01-01T00:00:00Z',
  },
];

describe('AccountSummary Component', () => {
  it('renders account cards with name, account number, badge, balance, and version', () => {
    const onSelect = vi.fn();
    render(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={onSelect}
      />
    );

    // USD Checking account
    expect(screen.getByTestId('account-name-1')).toHaveTextContent('Primary Checking');
    expect(screen.getByTestId('account-number-1')).toHaveTextContent('CHK-1001');
    expect(screen.getByTestId('account-balance-1')).toHaveTextContent('$2,500.00');

    // USD Savings account
    expect(screen.getByTestId('account-name-2')).toHaveTextContent('Standard Savings');
    expect(screen.getByTestId('account-number-2')).toHaveTextContent('SAV-2001');
    expect(screen.getByTestId('account-balance-2')).toHaveTextContent('$10,000.00');

    // EUR account
    expect(screen.getByTestId('account-name-3')).toHaveTextContent('Euro Account');
    expect(screen.getByTestId('account-balance-3')).toHaveTextContent('€90.00');

    // GBP account
    expect(screen.getByTestId('account-name-4')).toHaveTextContent('British Pound Account');
    expect(screen.getByTestId('account-balance-4')).toHaveTextContent('£80.00');

    // Versions
    expect(screen.getByTestId('account-card-1')).toHaveTextContent('Version: 1');
    expect(screen.getByTestId('account-card-2')).toHaveTextContent('Version: 2');
    expect(screen.getByTestId('account-card-3')).toHaveTextContent('Version: 3');
    expect(screen.getByTestId('account-card-4')).toHaveTextContent('Version: 4');
  });

  it('displays currency-segregated totals and indicative estimated USD total (D-10)', () => {
    render(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // USD: 2500.00 + 10000.00 = 12,500.00
    expect(screen.getByTestId('total-usd')).toHaveTextContent('USD: $12,500.00');
    // EUR: 90.00
    expect(screen.getByTestId('total-eur')).toHaveTextContent('EUR: €90.00');
    // GBP: 80.00
    expect(screen.getByTestId('total-gbp')).toHaveTextContent('GBP: £80.00');

    // Estimated Total USD: 12500.00 + (90 * 10 / 9 = 100.00) + (80 * 10 / 8 = 100.00) = $12,700.00
    expect(screen.getByTestId('total-balance')).toHaveTextContent('$12,700.00');
  });

  it('formats small amounts with exact currency symbols without floating-point drift', () => {
    const smallAccounts: Account[] = [
      {
        id: 10,
        user_id: 1,
        account_number: 'USD-SMALL',
        account_type: 'checking',
        account_name: 'Small USD',
        balance: '0.05',
        currency: 'USD',
        version: 1,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 11,
        user_id: 1,
        account_number: 'EUR-SMALL',
        account_type: 'checking',
        account_name: 'Small EUR',
        balance: '0.10',
        currency: 'EUR',
        version: 1,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 12,
        user_id: 1,
        account_number: 'GBP-SMALL',
        account_type: 'savings',
        account_name: 'Small GBP',
        balance: '0.02',
        currency: 'GBP',
        version: 1,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(
      <AccountSummary
        accounts={smallAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('account-balance-10')).toHaveTextContent('$0.05');
    expect(screen.getByTestId('account-balance-11')).toHaveTextContent('€0.10');
    expect(screen.getByTestId('account-balance-12')).toHaveTextContent('£0.02');
  });

  it('correctly aggregates multiple accounts in the same currency and applies ROUND_HALF_UP only once to Estimated Total (USD)', () => {
    // Critical D-03 / D-10 test case:
    // Two GBP accounts each containing 0.02 GBP:
    // Rate 10/8: unrounded USD equivalent is 2 * 10 / 8 = 2.5 cents per account.
    // If rounded independently: 2.5 -> 3 cents ($0.03 USD) each => sum = 6 cents ($0.06 USD).
    // If unrounded equivalents are accumulated first: 2.5 + 2.5 = 5.0 cents => rounds to 5 cents ($0.05 USD).
    const twoGbpAccounts: Account[] = [
      {
        id: 20,
        user_id: 1,
        account_number: 'GBP-1',
        account_type: 'checking',
        account_name: 'Pound Account A',
        balance: '0.02',
        currency: 'GBP',
        version: 5,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 21,
        user_id: 1,
        account_number: 'GBP-2',
        account_type: 'savings',
        account_name: 'Pound Account B',
        balance: '0.02',
        currency: 'GBP',
        version: 8,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(
      <AccountSummary
        accounts={twoGbpAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // Segregated GBP total: 0.02 + 0.02 = 0.04 GBP
    expect(screen.getByTestId('total-gbp')).toHaveTextContent('GBP: £0.04');

    // Single final ROUND_HALF_UP: combined USD equivalent is $0.05, NOT $0.06
    expect(screen.getByTestId('total-balance')).toHaveTextContent('$0.05');
  });

  it('preserves authoritative account versions across all account cards', () => {
    const versionedAccounts: Account[] = [
      {
        id: 30,
        user_id: 1,
        account_number: 'ACC-V42',
        account_type: 'checking',
        account_name: 'Versioned Account',
        balance: '150.00',
        currency: 'USD',
        version: 42,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(
      <AccountSummary
        accounts={versionedAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('account-card-30')).toHaveTextContent('Version: 42');
  });

  it('validates API contract requiring string balance and integer version', () => {
    for (const acc of mockAccounts) {
      expect(typeof acc.balance).toBe('string');
      expect(acc.balance).toMatch(/^-?\d+(\.\d{1,2})?$/);
      expect(typeof acc.version).toBe('number');
      expect(Number.isInteger(acc.version)).toBe(true);
      expect(acc.version).toBeGreaterThan(0);
    }
  });

  it('highlights the selected account and invokes onSelectAccount when clicked', () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={onSelect}
      />
    );

    const card1 = screen.getByTestId('account-card-1');
    expect(card1).not.toHaveClass('selected');

    fireEvent.click(card1);
    expect(onSelect).toHaveBeenCalledWith(1);

    // Re-render with account 1 selected
    rerender(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={1}
        onSelectAccount={onSelect}
      />
    );

    expect(screen.getByTestId('account-card-1')).toHaveClass('selected');

    // Clicking active filter button clears selection
    const filterAllBtn = screen.getByTestId('filter-all-accounts');
    fireEvent.click(filterAllBtn);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it('displays loading indicator when isLoading is true', () => {
    render(
      <AccountSummary
        accounts={[]}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
        isLoading={true}
      />
    );

    expect(screen.getByTestId('accounts-loading')).toBeInTheDocument();
  });

  it('displays error banner when error prop is provided', () => {
    render(
      <AccountSummary
        accounts={[]}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
        error="Network connection failed"
      />
    );

    expect(screen.getByTestId('accounts-error')).toHaveTextContent('Network connection failed');
  });

  it('handles empty accounts list gracefully', () => {
    render(
      <AccountSummary
        accounts={[]}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    expect(screen.getByTestId('total-usd')).toHaveTextContent('USD: $0.00');
    expect(screen.getByTestId('total-eur')).toHaveTextContent('EUR: €0.00');
    expect(screen.getByTestId('total-gbp')).toHaveTextContent('GBP: £0.00');
    expect(screen.getByTestId('total-balance')).toHaveTextContent('$0.00');
  });
});
