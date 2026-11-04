import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from './api/client';
import { Account, Transaction, TransferRequest, MfaStatus } from './api/types';
import { Navbar } from './components/Navbar';
import { AccountSummary } from './components/AccountSummary';
import { TransactionHistory } from './components/TransactionHistory';
import { TransferModal } from './components/TransferModal';
import { MfaModal } from './components/MfaModal';

export const App: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState<boolean>(true);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState<boolean>(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);

  // Transfer and MFA modal states
  const [isTransferOpen, setIsTransferOpen] = useState<boolean>(false);
  const [isMfaOpen, setIsMfaOpen] = useState<boolean>(false);
  const [pendingTransfer, setPendingTransfer] = useState<TransferRequest | null>(null);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [isSubmittingTransfer, setIsSubmittingTransfer] = useState<boolean>(false);
  const [mfaStatus, setMfaStatus] = useState<MfaStatus>({
    threshold: 1000.0,
    locked: false,
    remaining_attempts: 3,
  });

  // Success toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadAccounts = useCallback(async () => {
    setIsLoadingAccounts(true);
    setAccountsError(null);
    try {
      const data = await api.getAccounts();
      setAccounts(data);
    } catch (err: any) {
      setAccountsError(err.message || 'Failed to load bank accounts');
    } finally {
      setIsLoadingAccounts(false);
    }
  }, []);

  const loadTransactions = useCallback(async (accountId?: number | null) => {
    setIsLoadingTransactions(true);
    try {
      const data = await api.getTransactions(accountId || undefined);
      setTransactions(data);
    } catch (err: any) {
      console.error('Failed to load transactions:', err);
    } finally {
      setIsLoadingTransactions(false);
    }
  }, []);

  const loadMfaStatus = useCallback(async () => {
    try {
      const status = await api.getMfaStatus();
      setMfaStatus(status);
    } catch (err) {
      console.error('Failed to load MFA status:', err);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
    loadTransactions();
    loadMfaStatus();
  }, [loadAccounts, loadTransactions, loadMfaStatus]);

  const handleSelectAccount = (accId: number | null) => {
    setSelectedAccountId(accId);
    loadTransactions(accId);
  };

  // Called from TransferModal
  const handleInitiateTransfer = async (transferData: TransferRequest) => {
    setTransferError(null);

    // If amount is > 1000, trigger MFA modal directly
    if (transferData.amount > mfaStatus.threshold) {
      setPendingTransfer(transferData);
      setIsTransferOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    // Direct transfer (<= 1000)
    setIsSubmittingTransfer(true);
    try {
      await api.executeTransfer(transferData);
      setIsTransferOpen(false);
      showToast(`Successfully transferred $${transferData.amount.toFixed(2)}`);
      // Refresh balances & movements
      await Promise.all([loadAccounts(), loadTransactions(selectedAccountId)]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        // Backend requested MFA
        setPendingTransfer(transferData);
        setIsTransferOpen(false);
        setIsMfaOpen(true);
      } else {
        setTransferError(err.message || 'Transfer failed');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // Called from MfaModal with PIN
  const handleConfirmMfa = async (pin: string) => {
    if (!pendingTransfer) return;

    setMfaError(null);
    setIsSubmittingTransfer(true);

    try {
      await api.executeTransfer({
        ...pendingTransfer,
        pin,
      });

      setIsMfaOpen(false);
      showToast(`Successfully transferred $${pendingTransfer.amount.toFixed(2)} with MFA authorization`);
      setPendingTransfer(null);

      // Refresh data
      await Promise.all([
        loadAccounts(),
        loadTransactions(selectedAccountId),
        loadMfaStatus(),
      ]);
    } catch (err: any) {
      await loadMfaStatus();
      setMfaError(err.message || 'Invalid Security PIN');
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  const pendingFromAccount = accounts.find((a) => a.id === pendingTransfer?.from_account_id) || null;
  const pendingToAccount = accounts.find((a) => a.id === pendingTransfer?.to_account_id) || null;

  return (
    <div className="app-container">
      <Navbar
        onOpenTransfer={() => {
          setTransferError(null);
          setIsTransferOpen(true);
        }}
        isMfaLocked={mfaStatus.locked}
      />

      <main className="main-content">
        <AccountSummary
          accounts={accounts}
          selectedAccountId={selectedAccountId}
          onSelectAccount={handleSelectAccount}
          isLoading={isLoadingAccounts}
          error={accountsError}
        />

        <TransactionHistory
          transactions={transactions}
          accounts={accounts}
          selectedAccountId={selectedAccountId}
          onSelectAccount={handleSelectAccount}
          isLoading={isLoadingTransactions}
        />
      </main>

      {/* Transfer Modal */}
      <TransferModal
        isOpen={isTransferOpen}
        accounts={accounts}
        isSubmitting={isSubmittingTransfer}
        errorMessage={transferError}
        onClose={() => setIsTransferOpen(false)}
        onSubmit={handleInitiateTransfer}
      />

      {/* MFA Security PIN Modal */}
      <MfaModal
        isOpen={isMfaOpen}
        fromAccount={pendingFromAccount}
        toAccount={pendingToAccount}
        amount={pendingTransfer?.amount || 0}
        remainingAttempts={mfaStatus.remaining_attempts}
        isLocked={mfaStatus.locked}
        errorMessage={mfaError}
        isSubmitting={isSubmittingTransfer}
        onConfirm={handleConfirmMfa}
        onCancel={() => {
          setIsMfaOpen(false);
          setPendingTransfer(null);
          setMfaError(null);
        }}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast" role="status" aria-live="polite">
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
};
