import React from 'react';
import { Account } from '../api/types';
import {
  formatCurrency,
  sumMonetary,
  calculateEstimatedUsdTotal,
} from '../utils/monetary';

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
  // 1. Currency-Segregated Totals (D-10) using exact decimal-string arithmetic
  const usdAccounts = accounts.filter((a) => a.currency === 'USD');
  const eurAccounts = accounts.filter((a) => a.currency === 'EUR');
  const gbpAccounts = accounts.filter((a) => a.currency === 'GBP');

  const usdTotal = sumMonetary(usdAccounts.map((a) => a.balance));
  const eurTotal = sumMonetary(eurAccounts.map((a) => a.balance));
  const gbpTotal = sumMonetary(gbpAccounts.map((a) => a.balance));

  // 2. Indicative Estimated USD Aggregate using exact D-03 rational reference rates (D-10)
  // Accumulates unrounded equivalents across all accounts and applies ROUND_HALF_UP only once at the end
  const estimatedUsdTotal = calculateEstimatedUsdTotal(accounts);

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
          <span className="total-label">Multicurrency Portfolio Overview</span>
          <span className="account-count-badge">{accounts.length} Active Accounts</span>
        </div>

        {/* Currency-Segregated Totals (D-10) */}
        <div className="currency-totals-row" style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
          <div className="currency-total-badge" data-testid="total-usd">
            <strong>USD:</strong> {formatCurrency(usdTotal, 'USD')}
          </div>
          <div className="currency-total-badge" data-testid="total-eur">
            <strong>EUR:</strong> {formatCurrency(eurTotal, 'EUR')}
          </div>
          <div className="currency-total-badge" data-testid="total-gbp">
            <strong>GBP:</strong> {formatCurrency(gbpTotal, 'GBP')}
          </div>
        </div>

        {/* Indicative Estimated Total USD (D-10) */}
        <div style={{ marginTop: '0.75rem' }}>
          <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Estimated Total (USD Equivalent) *
          </span>
          <div className="total-amount" data-testid="total-balance">
            {formatCurrency(estimatedUsdTotal, 'USD')}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: '0.25rem 0 0 0' }}>
            * Simulated valuation based on fixed reference rates (1 USD = 0.90 EUR = 0.80 GBP). Display-only.
          </p>
        </div>

        <div className="total-footer" style={{ marginTop: '1rem' }}>
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
                <span className="badge badge-currency" style={{ marginLeft: '0.5rem', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
                  {acc.currency}
                </span>
                <span className="account-number" data-testid={`account-number-${acc.id}`} style={{ marginLeft: 'auto' }}>
                  {acc.account_number}
                </span>
              </div>

              <div className="account-card-body">
                <h3 className="account-name" data-testid={`account-name-${acc.id}`}>
                  {acc.account_name}
                </h3>
                <div className="account-balance" data-testid={`account-balance-${acc.id}`}>
                  {formatCurrency(acc.balance, acc.currency)}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                  Version: {acc.version}
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
