import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AccountCard, maskAccountNumber } from '../components/AccountCard';
import { AccountGrid } from '../components/AccountGrid';
import { Navbar } from '../components/Navbar';
import { Account } from '../types/account';

const mockAccounts: Account[] = [
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

describe('AccountCard & Masking', () => {
  it('masks account number correctly', () => {
    expect(maskAccountNumber('CHK-1001')).toBe('•••• 1001');
    expect(maskAccountNumber('SAV-2001')).toBe('•••• 2001');
    expect(maskAccountNumber('RSV-3001')).toBe('•••• 3001');
  });

  it('renders account details with tabular balance formatting', () => {
    const onSelect = vi.fn();
    render(<AccountCard account={mockAccounts[0]} isSelected={false} onSelect={onSelect} />);

    expect(screen.getByText('Primary Checking')).toBeInTheDocument();
    expect(screen.getByText('•••• 1001')).toBeInTheDocument();
    expect(screen.getByText('CHECKING')).toBeInTheDocument();
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
  });

  it('triggers onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<AccountCard account={mockAccounts[0]} isSelected={false} onSelect={onSelect} />);

    const card = screen.getByRole('button');
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith('CHK-1001');
  });

  it('triggers onSelect on Enter or Space key', () => {
    const onSelect = vi.fn();
    render(<AccountCard account={mockAccounts[0]} isSelected={false} onSelect={onSelect} />);

    const card = screen.getByRole('button');
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith('CHK-1001');

    fireEvent.keyDown(card, { key: ' ' });
    expect(onSelect).toHaveBeenCalledTimes(2);
  });
});

describe('AccountGrid', () => {
  it('renders all 3 account cards', () => {
    const onSelect = vi.fn();
    render(
      <AccountGrid
        accounts={mockAccounts}
        selectedAccountId="CHK-1001"
        onSelectAccount={onSelect}
      />
    );

    expect(screen.getByText('Primary Checking')).toBeInTheDocument();
    expect(screen.getByText('High-Yield Savings')).toBeInTheDocument();
    expect(screen.getByText('Emergency Reserve')).toBeInTheDocument();
  });

  it('renders loading state when loading is true', () => {
    render(
      <AccountGrid
        accounts={[]}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
        loading={true}
      />
    );

    expect(screen.getByTestId('account-grid-loading')).toBeInTheDocument();
  });

  it('renders error notice when error is provided', () => {
    render(
      <AccountGrid
        accounts={[]}
        selectedAccountId={null}
        onSelectAccount={vi.fn()}
        error="Network error"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Network error');
  });
});

describe('Navbar', () => {
  it('renders brand and customer identity Alex Morgan', () => {
    render(<Navbar />);

    expect(screen.getByText('Shift Bank')).toBeInTheDocument();
    expect(screen.getByText('Stage 1 Sandbox')).toBeInTheDocument();
    expect(screen.getByText('Alex Morgan')).toBeInTheDocument();
    expect(screen.getByText('cust_mock_001')).toBeInTheDocument();
    expect(screen.getByText('AM')).toBeInTheDocument();
  });
});
