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

describe('AccountSummary Component', () => {
  it('renders account cards with name, account number, badge, and balance', () => {
    const onSelect = vi.fn();
    render(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={onSelect}
      />
    );

    expect(screen.getByTestId('account-name-1')).toHaveTextContent('Primary Checking');
    expect(screen.getByTestId('account-number-1')).toHaveTextContent('CHK-1001');
    expect(screen.getByTestId('account-balance-1')).toHaveTextContent('$2,500.00');

    expect(screen.getByTestId('account-name-2')).toHaveTextContent('Standard Savings');
    expect(screen.getByTestId('account-number-2')).toHaveTextContent('SAV-2001');
    expect(screen.getByTestId('account-balance-2')).toHaveTextContent('$10,000.00');
  });

  it('displays the total aggregate net balance across all user accounts', () => {
    render(
      <AccountSummary
        accounts={mockAccounts}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
      />
    );

    // 2500 + 10000 = 12500
    expect(screen.getByTestId('total-balance')).toHaveTextContent('$12,500.00');
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
});
