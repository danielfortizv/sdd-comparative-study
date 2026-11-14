import React from 'react';
import { Account } from '../api/types';

interface AccountSummaryProps {
  accounts: Account[];
  selectedAccountId: number | null;
  onSelectAccount: (accountId: number | null) => void;
  isLoading?: boolean;
  error?: string | null;
}

export const AccountSummary: React.FC<AccountSummaryProps> = ({
  accounts,
  selectedAccountId,
  onSelectAccount,
  isLoading = false,
  error = null,
}) => {
  const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val);
  };

  if (isLoading) {
    return (
      <section className="summary-section" aria-busy="true">
        <div className="skeleton-loader" data-testid="accounts-loading">
          Loading bank accounts...
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="summary-section">
        <div className="error-banner" role="alert" data-testid="accounts-error">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      </section>
    );
  }

  return (
    <section className="summary-section" aria-label="Accounts and Balances Overview">
      <div className="total-balance-card">
        <div className="total-header">
          <span className="total-label">Total Net Balance</span>
          <span className="account-count-badge">{accounts.length} Active Accounts</span>
        </div>
        <div className="total-amount" data-testid="total-balance">
          {formatCurrency(totalBalance)}
        </div>
        <div className="total-footer">
          <button
            className={`btn-filter-all ${selectedAccountId === null ? 'active' : ''}`}
            onClick={() => onSelectAccount(null)}
            data-testid="filter-all-accounts"
          >
            Show All Movements
          </button>
        </div>
      </div>

      <div className="accounts-grid" data-testid="accounts-grid">
        {accounts.map((acc) => {
          const isSelected = selectedAccountId === acc.id;
          return (
            <div
              key={acc.id}
              className={`account-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectAccount(isSelected ? null : acc.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelectAccount(isSelected ? null : acc.id);
                }
              }}
              data-testid={`account-card-${acc.id}`}
              aria-pressed={isSelected}
            >
              <div className="account-card-header">
                <span className={`badge badge-${acc.account_type}`}>
                  {acc.account_type.toUpperCase()}
                </span>
                <span className="account-number" data-testid={`account-number-${acc.id}`}>
                  {acc.account_number}
                </span>
              </div>

              <div className="account-card-body">
                <h3 className="account-name" data-testid={`account-name-${acc.id}`}>
                  {acc.account_name}
                </h3>
                <div className="account-balance" data-testid={`account-balance-${acc.id}`}>
                  {formatCurrency(acc.balance)}
                </div>
              </div>

              <div className="account-card-footer">
                <span className="view-movements-link">
                  {isSelected ? '✓ Viewing Movements' : 'Click to filter movements →'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
