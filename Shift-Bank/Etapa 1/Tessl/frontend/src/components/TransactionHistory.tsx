import React from 'react';
import { Transaction, Account } from '../api/types';

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
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val);
  };

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
              {acc.account_name}
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
                return (
                  <tr key={tx.id} data-testid={`transaction-row-${tx.id}`}>
                    <td className="tx-date">{formatDate(tx.created_at)}</td>
                    <td className="tx-desc">
                      <div className="tx-desc-title">{tx.description}</div>
                      {tx.reference && (
                        <div className="tx-ref" data-testid={`tx-ref-${tx.id}`}>
                          Ref: {tx.reference}
                        </div>
                      )}
                    </td>
                    <td className="tx-account">
                      <span className="badge badge-outline">
                        {tx.account_name || `Account #${tx.account_id}`}
                      </span>
                    </td>
                    <td className={`tx-amount text-right ${isCredit ? 'credit' : 'debit'}`}>
                      <span data-testid={`tx-amount-${tx.id}`}>
                        {isCredit ? `+${formatCurrency(tx.amount)}` : `-${formatCurrency(tx.amount)}`}
                      </span>
                    </td>
                    <td className="tx-balance text-right" data-testid={`tx-balance-after-${tx.id}`}>
                      {formatCurrency(tx.balance_after)}
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
