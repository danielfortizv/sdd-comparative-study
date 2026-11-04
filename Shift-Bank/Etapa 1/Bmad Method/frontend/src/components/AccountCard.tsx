import React from 'react';
import { Account } from '../types/account';

interface AccountCardProps {
  account: Account;
  isSelected: boolean;
  isHighlighted?: boolean;
  onSelect: (id: string) => void;
}

export function maskAccountNumber(id: string): string {
  const parts = id.split('-');
  const lastPart = parts.length > 1 ? parts[parts.length - 1] : id;
  return `•••• ${lastPart}`;
}

export const AccountCard: React.FC<AccountCardProps> = ({
  account,
  isSelected,
  isHighlighted = false,
  onSelect,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(account.id);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`${account.nickname}, ${maskAccountNumber(account.id)}, Balance: ${account.balance_formatted}`}
      onClick={() => onSelect(account.id)}
      onKeyDown={handleKeyDown}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: isSelected
          ? '2px solid var(--color-border-active-card)'
          : '1px solid var(--color-border)',
        borderRadius: 'var(--rounded-lg)',
        padding: 'var(--spacing-lg)',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: isHighlighted
          ? '0 0 0 3px var(--color-accent)'
          : isSelected
          ? 'var(--shadow-md)'
          : 'var(--shadow-sm)',
        transition: 'all 0.4s ease',
        outline: 'none',
      }}
      className="account-card-focus-target"
      data-testid={`account-card-${account.id}`}
      data-highlighted={isHighlighted ? 'true' : 'false'}
    >
      {/* Active Indicator Dot */}
      {isSelected && (
        <span
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: '14px',
            right: '14px',
            width: '8px',
            height: '8px',
            borderRadius: 'var(--rounded-full)',
            backgroundColor: 'var(--color-accent)',
          }}
        />
      )}

      {/* Card Header: Type Badge & Masked ID */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--spacing-sm)',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            padding: '3px 8px',
            borderRadius: 'var(--rounded-sm)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            backgroundColor: isSelected
              ? 'rgba(10, 37, 64, 0.08)'
              : 'var(--color-muted-surface)',
            color: isSelected ? 'var(--color-primary)' : 'var(--color-muted)',
          }}
        >
          {account.type}
        </span>
        <span
          style={{
            fontSize: '12px',
            fontFamily: 'var(--font-family-mono)',
            color: 'var(--color-muted)',
          }}
        >
          {maskAccountNumber(account.id)}
        </span>
      </div>

      {/* Account Nickname */}
      <div
        style={{
          fontSize: '16px',
          fontWeight: 600,
          color: 'var(--color-foreground)',
          marginBottom: 'var(--spacing-sm)',
        }}
      >
        {account.nickname}
      </div>

      {/* Monetary Balance */}
      <div
        className="tabular-nums"
        style={{
          fontSize: '26px',
          fontWeight: 700,
          color: 'var(--color-foreground)',
          letterSpacing: '-0.02em',
        }}
      >
        {account.balance_formatted}
      </div>
    </div>
  );
};
