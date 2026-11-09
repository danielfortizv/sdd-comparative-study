import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { AccountGrid } from './components/AccountGrid';
import { TransferForm } from './components/TransferForm';
import { Toast } from './components/Toast';
import { useAccounts } from './hooks/useAccounts';
import { initiateTransfer, ApiError } from './api/client';

export const App: React.FC = () => {
  const {
    accounts,
    selectedAccountId,
    selectedAccount,
    loading,
    error: accountsError,
    selectAccount,
    refreshAccounts,
  } = useAccounts();

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [resetKey, setResetKey] = useState<number>(0);
  const [highlightedAccountIds, setHighlightedAccountIds] = useState<string[]>([]);

  const handleTransferSubmit = async (data: {
    fromAccountId: string;
    toAccountId: string;
    amountCents: number;
    amountFormatted: string;
  }) => {
    setIsSubmitting(true);
    setTransferError(null);

    try {
      const response = await initiateTransfer(
        data.fromAccountId,
        data.toAccountId,
        data.amountCents
      );

      if (response.status === 'COMPLETED') {
        const destAcc = accounts.find((a) => a.id === data.toAccountId);
        const destName = destAcc ? destAcc.nickname : data.toAccountId;

        // 1. Toast Notification (FR-6, EXPERIENCE.md)
        setToastMessage(
          `Transfer of ${response.transfer.amount_formatted} to ${destName} completed. Reference: ${response.transfer.id}`
        );

        // 2. Reset Form Amount (FR-6)
        setResetKey((prev) => prev + 1);

        // 3. Synchronous View Refresh without optimistic guessing (AD-9, NFR-4)
        await refreshAccounts();

        // 4. Subtle 400ms accent highlight flash (EXPERIENCE.md)
        setHighlightedAccountIds([data.fromAccountId, data.toAccountId]);
        setTimeout(() => {
          setHighlightedAccountIds([]);
        }, 400);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setTransferError(err.message);
      } else {
        setTransferError('Transfer failed. Please check connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Bar with brand and Alex Morgan customer badge */}
      <Navbar />

      {/* Emerald Confirmation Toast */}
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />

      {/* Main Content Dashboard */}
      <main
        style={{
          flex: 1,
          maxWidth: '1280px',
          margin: '0 auto',
          width: '100%',
          padding: 'var(--spacing-xl) var(--spacing-lg)',
        }}
      >
        {/* Account Summary Portfolio Section */}
        <section aria-labelledby="portfolio-heading" style={{ marginBottom: 'var(--spacing-xl)' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: 'var(--spacing-md)',
            }}
          >
            <h2
              id="portfolio-heading"
              style={{
                fontSize: '20px',
                fontWeight: 600,
                color: 'var(--color-primary)',
              }}
            >
              Account Portfolio
            </h2>
            {selectedAccount && (
              <span
                style={{
                  fontSize: '13px',
                  color: 'var(--color-muted)',
                }}
                data-testid="selected-account-indicator"
              >
                Active Account: <strong>{selectedAccount.nickname}</strong> ({selectedAccount.balance_formatted})
              </span>
            )}
          </div>

          <AccountGrid
            accounts={accounts}
            selectedAccountId={selectedAccountId}
            highlightedAccountIds={highlightedAccountIds}
            onSelectAccount={selectAccount}
            loading={loading}
            error={accountsError}
          />
        </section>

        {/* Global Transfer Error Notice if any */}
        {transferError && (
          <div
            role="alert"
            style={{
              backgroundColor: 'var(--color-destructive-surface)',
              color: 'var(--color-destructive-foreground)',
              border: '1px solid var(--color-destructive)',
              borderRadius: 'var(--rounded-md)',
              padding: '12px 16px',
              marginBottom: 'var(--spacing-lg)',
              fontSize: '14px',
            }}
            data-testid="transfer-error-banner"
          >
            <strong>Transfer Error:</strong> {transferError}
          </div>
        )}

        {/* 2-Column Core Workspace (Left: Transfer Form, Right: Activity Placeholder) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(340px, 400px) 1fr',
            gap: 'var(--spacing-lg)',
            alignItems: 'start',
          }}
          data-testid="workspace-grid"
        >
          {/* Left Column: Transfer Action Panel */}
          <TransferForm
            accounts={accounts}
            defaultSourceAccountId={selectedAccountId}
            resetKey={resetKey}
            onSubmitTransfer={handleTransferSubmit}
            isSubmitting={isSubmitting}
          />

          {/* Right Column: Account Activity Panel Placeholder (Epic 4) */}
          <section
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--rounded-lg)',
              padding: 'var(--spacing-lg)',
              boxShadow: 'var(--shadow-sm)',
              minHeight: '360px',
            }}
            data-testid="ledger-placeholder-panel"
          >
            <div
              style={{
                borderBottom: '1px solid var(--color-border)',
                paddingBottom: 'var(--spacing-md)',
                marginBottom: 'var(--spacing-md)',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-primary)' }}>
                {selectedAccount ? `${selectedAccount.nickname} Activity` : 'Account Activity'}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-muted)', marginTop: '4px' }}>
                Transaction history and movement audit ledger.
              </p>
            </div>
            <p
              style={{
                fontSize: '14px',
                color: 'var(--color-muted)',
                padding: 'var(--spacing-xl) 0',
                textAlign: 'center',
              }}
            >
              Select an account to view details or formulate a transfer on the left.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
};

export default App;
