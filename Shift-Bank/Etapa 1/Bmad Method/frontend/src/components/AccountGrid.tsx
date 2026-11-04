import React from 'react';
import { Account } from '../types/account';
import { AccountCard } from './AccountCard';

interface AccountGridProps {
  accounts: Account[];
  selectedAccountId: string | null;
  highlightedAccountIds?: string[];
  onSelectAccount: (id: string) => void;
  loading?: boolean;
  error?: string | null;
}

export const AccountGrid: React.FC<AccountGridProps> = ({
  accounts,
  selectedAccountId,
  highlightedAccountIds = [],
  onSelectAccount,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-xl)',
        }}
        data-testid="account-grid-loading"
      >
        {[1, 2, 3].map((idx) => (
          <div
            key={idx}
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--rounded-lg)',
              padding: 'var(--spacing-lg)',
              height: '140px',
              animation: 'pulse 1.5s infinite ease-in-out',
            }}
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          backgroundColor: 'var(--color-destructive-surface)',
          color: 'var(--color-destructive-foreground)',
          border: '1px solid var(--color-destructive)',
          borderRadius: 'var(--rounded-lg)',
          padding: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-xl)',
        }}
        role="alert"
      >
        <strong>Failed to load accounts:</strong> {error}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 'var(--spacing-md)',
        marginBottom: 'var(--spacing-xl)',
      }}
      data-testid="account-grid"
    >
      {accounts.map((account) => (
        <AccountCard
          key={account.id}
          account={account}
          isSelected={account.id === selectedAccountId}
          isHighlighted={highlightedAccountIds.includes(account.id)}
          onSelect={onSelectAccount}
        />
      ))}
    </div>
  );
};
