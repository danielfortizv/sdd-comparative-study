import React from 'react';
import { Transaction, Account } from '../api/types';
import { formatCurrency } from '../utils/monetary';

interface TransactionHistoryProps {
  transactions: Transaction[];
  accounts: Account[];
  selectedAccountId: number | null;
  onSelectAccount: (accountId: number | null) => void;
  isLoading?: boolean;
}

export const TransactionHistory: React.FC<TransactionHistoryProps> = ({
  transactions,
  accounts,
  selectedAccountId,
  onSelectAccount,
  isLoading = false,
}) => {
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const filteredTransactions = selectedAccountId === null
    ? transactions
    : transactions.filter((t) => t.account_id === selectedAccountId);

  return (
    <section className="transactions-section" aria-label="Transaction History">
      <div className="section-header">
        <div className="section-title-group">
          <h2 className="section-title">Transaction History</h2>
          <span className="tx-count-badge" data-testid="tx-count-badge">
            {filteredTransactions.length} movements
          </span>
        </div>

        {/* Account Tabs Filter */}
        <div className="account-filter-tabs" role="tablist" aria-label="Filter transactions by account">
          <button
            role="tab"
            aria-selected={selectedAccountId === null}
            className={`tab-btn ${selectedAccountId === null ? 'active' : ''}`}
            onClick={() => onSelectAccount(null)}
            data-testid="tab-all-accounts"
          >
            All Accounts
          </button>
          {accounts.map((acc) => (
            <button
              key={acc.id}
              role="tab"
              aria-selected={selectedAccountId === acc.id}
              className={`tab-btn ${selectedAccountId === acc.id ? 'active' : ''}`}
              onClick={() => onSelectAccount(acc.id)}
              data-testid={`tab-account-${acc.id}`}
            >
              {acc.account_name} ({acc.currency})
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="skeleton-loader" data-testid="transactions-loading">
          Loading movements...
        </div>
      ) : filteredTransactions.length === 0 ? (
        <div className="empty-state" data-testid="empty-transactions-state">
          <span className="empty-icon">📂</span>
          <h3>No transactions found</h3>
          <p>No recorded movements for the selected account filter.</p>
        </div>
      ) : (
        <div className="transactions-table-container">
          <table className="transactions-table" aria-label="Movements List">
            <thead>
              <tr>
                <th scope="col">Date & Time</th>
                <th scope="col">Description / Reference</th>
                <th scope="col">Account</th>
                <th scope="col" className="text-right">Amount</th>
                <th scope="col" className="text-right">Balance After</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map((tx) => {
                const isCredit = tx.transaction_type === 'credit';
                const txCurrency = tx.currency || 'USD';
                const absAmount = tx.amount.startsWith('-') ? tx.amount.slice(1) : tx.amount;
                const formattedAmount = formatCurrency(absAmount, txCurrency);

                return (
                  <tr key={tx.id} data-testid={`transaction-row-${tx.id}`}>
                    <td className="tx-date">{formatDate(tx.created_at)}</td>
                    <td className="tx-desc">
                      <div className="tx-desc-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{tx.description}</span>
                        {(tx.conversion_id || (tx.source_amount && tx.destination_amount)) && (
                          <span
                            className="badge badge-info"
                            data-testid={`tx-conversion-badge-${tx.id}`}
                            style={{ fontSize: '0.7rem', padding: '2px 6px', background: '#dbeafe', color: '#1e40af', borderRadius: '4px' }}
                          >
                            FX Conversion
                          </span>
                        )}
                        {tx.status === 'pending' && (
                          <span
                            className="badge badge-warning"
                            data-testid={`tx-pending-badge-${tx.id}`}
                            style={{ fontSize: '0.7rem', padding: '2px 6px' }}
                          >
                            Pending
                          </span>
                        )}
                        {tx.status === 'failed' && (
                          <span
                            className="badge badge-danger"
                            data-testid={`tx-failed-badge-${tx.id}`}
                            style={{ fontSize: '0.7rem', padding: '2px 6px' }}
                          >
                            Failed
                          </span>
                        )}
                        {tx.status === 'completed' && (
                          <span
                            className="badge badge-success"
                            data-testid={`tx-completed-badge-${tx.id}`}
                            style={{ fontSize: '0.7rem', padding: '2px 6px', background: '#dcfce7', color: '#166534', borderRadius: '4px' }}
                          >
                            Completed
                          </span>
                        )}
                      </div>
                      {tx.reference && (
                        <div className="tx-ref" data-testid={`tx-ref-${tx.id}`}>
                          Ref: {tx.reference}
                        </div>
                      )}
                      {tx.source_amount && tx.destination_amount && (
                        <div
                          className="tx-conversion-amounts"
                          data-testid={`tx-conversion-amounts-${tx.id}`}
                          style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}
                        >
                          <span>
                            Conversion:{' '}
                            <span data-testid={`tx-source-amount-${tx.id}`}>
                              {formatCurrency(tx.source_amount, tx.source_currency || 'USD')}
                            </span>
                            {' → '}
                            <span data-testid={`tx-destination-amount-${tx.id}`}>
                              {formatCurrency(tx.destination_amount, tx.destination_currency || 'USD')}
                            </span>
                          </span>
                        </div>
                      )}
                      {tx.exchange_rate_display && tx.source_currency && tx.destination_currency && (
                        <div
                          className="tx-exchange-rate"
                          data-testid={`tx-exchange-rate-${tx.id}`}
                          style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}
                        >
                          Rate: 1 {tx.source_currency} = {tx.exchange_rate_display} {tx.destination_currency}
                        </div>
                      )}
                    </td>
                    <td className="tx-account">
                      <span className="badge badge-outline" data-testid={`tx-account-${tx.id}`}>
                        {tx.account_name || `Account #${tx.account_id}`} ({txCurrency})
                      </span>
                    </td>
                    <td className={`tx-amount text-right ${isCredit ? 'credit' : 'debit'}`}>
                      <span data-testid={`tx-amount-${tx.id}`}>
                        {isCredit ? `+${formattedAmount}` : `-${formattedAmount}`}
                      </span>
                    </td>
                    <td className="tx-balance text-right" data-testid={`tx-balance-after-${tx.id}`}>
                      {formatCurrency(tx.balance_after, txCurrency)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
