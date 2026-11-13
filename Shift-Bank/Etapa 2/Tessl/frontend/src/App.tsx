import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from './api/client';
import {
  Account,
  Transaction,
  TransferRequest,
  MfaStatus,
  Beneficiary,
  AchTransferRequest,
  RecurringSchedule,
  RecurringScheduleCreateRequest,
  TransferLimits as TransferLimitsType,
} from './api/types';
import { Navbar } from './components/Navbar';
import { AccountSummary } from './components/AccountSummary';
import { TransactionHistory } from './components/TransactionHistory';
import { TransferModal } from './components/TransferModal';
import { MfaModal } from './components/MfaModal';
import { TransferLimits } from './components/TransferLimits';
import { RecurringPayments } from './components/RecurringPayments';

type PendingAction =
  | { type: 'internal'; data: TransferRequest }
  | { type: 'ach'; data: AchTransferRequest }
  | { type: 'recurring'; data: RecurringScheduleCreateRequest };

export const App: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [recurringSchedules, setRecurringSchedules] = useState<RecurringSchedule[]>([]);
  const [limits, setLimits] = useState<TransferLimitsType | null>(null);

  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState<boolean>(true);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState<boolean>(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);

  // Modal display states
  const [isTransferOpen, setIsTransferOpen] = useState<boolean>(false);
  const [isMfaOpen, setIsMfaOpen] = useState<boolean>(false);
  const [isLimitsOpen, setIsLimitsOpen] = useState<boolean>(false);
  const [isRecurringOpen, setIsRecurringOpen] = useState<boolean>(false);

  // Pending MFA action state
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
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

  const loadBeneficiaries = useCallback(async () => {
    try {
      const data = await api.getBeneficiaries();
      setBeneficiaries(data);
    } catch (err) {
      console.error('Failed to load beneficiaries:', err);
    }
  }, []);

  const loadRecurringSchedules = useCallback(async () => {
    try {
      const data = await api.getRecurringSchedules();
      setRecurringSchedules(data);
    } catch (err) {
      console.error('Failed to load recurring schedules:', err);
    }
  }, []);

  const loadLimits = useCallback(async () => {
    try {
      const data = await api.getLimits();
      setLimits(data);
    } catch (err) {
      console.error('Failed to load transfer limits:', err);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
    loadTransactions();
    loadMfaStatus();
    loadBeneficiaries();
    loadRecurringSchedules();
    loadLimits();
  }, [loadAccounts, loadTransactions, loadMfaStatus, loadBeneficiaries, loadRecurringSchedules, loadLimits]);

  const handleSelectAccount = (accId: number | null) => {
    setSelectedAccountId(accId);
    loadTransactions(accId);
  };

  // Internal Transfer submission
  const handleInitiateTransfer = async (transferData: TransferRequest) => {
    setTransferError(null);

    if (transferData.amount > mfaStatus.threshold) {
      setPendingAction({ type: 'internal', data: transferData });
      setIsTransferOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    setIsSubmittingTransfer(true);
    try {
      await api.executeTransfer(transferData);
      setIsTransferOpen(false);
      showToast(`Successfully transferred $${transferData.amount.toFixed(2)}`);
      await Promise.all([loadAccounts(), loadTransactions(selectedAccountId), loadLimits()]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        setPendingAction({ type: 'internal', data: transferData });
        setIsTransferOpen(false);
        setIsMfaOpen(true);
      } else {
        setTransferError(err.message || 'Transfer failed');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // ACH Transfer submission
  const handleInitiateAchTransfer = async (achData: AchTransferRequest) => {
    setTransferError(null);

    if (achData.amount > mfaStatus.threshold) {
      setPendingAction({ type: 'ach', data: achData });
      setIsTransferOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    setIsSubmittingTransfer(true);
    try {
      await api.executeAchTransfer(achData);
      setIsTransferOpen(false);
      showToast(`ACH Transfer of $${achData.amount.toFixed(2)} initiated in pending status`);
      await Promise.all([
        loadAccounts(),
        loadTransactions(selectedAccountId),
        loadBeneficiaries(),
        loadLimits(),
      ]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        setPendingAction({ type: 'ach', data: achData });
        setIsTransferOpen(false);
        setIsMfaOpen(true);
      } else {
        setTransferError(err.message || 'ACH Transfer failed');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // Recurring Schedule Creation
  const handleCreateRecurringSchedule = async (scheduleData: RecurringScheduleCreateRequest) => {
    if (scheduleData.amount > mfaStatus.threshold) {
      setPendingAction({ type: 'recurring', data: scheduleData });
      setIsRecurringOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    try {
      await api.createRecurringSchedule(scheduleData);
      showToast(`Successfully configured ${scheduleData.frequency} recurring payment of $${scheduleData.amount.toFixed(2)}`);
      await loadRecurringSchedules();
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        setPendingAction({ type: 'recurring', data: scheduleData });
        setIsRecurringOpen(false);
        setIsMfaOpen(true);
      } else {
        throw err;
      }
    }
  };

  // Recurring Actions
  const handlePauseRecurringSchedule = async (id: number) => {
    await api.pauseRecurringSchedule(id);
    showToast('Recurring schedule paused');
    await loadRecurringSchedules();
  };

  const handleResumeRecurringSchedule = async (id: number) => {
    await api.resumeRecurringSchedule(id);
    showToast('Recurring schedule resumed');
    await loadRecurringSchedules();
  };

  const handleCancelRecurringSchedule = async (id: number) => {
    await api.cancelRecurringSchedule(id);
    showToast('Recurring schedule cancelled');
    await loadRecurringSchedules();
  };

  // Update Limits
  const handleUpdateLimits = async (perTx: number, daily: number) => {
    const updated = await api.updateLimits({
      per_transaction_limit: perTx,
      daily_limit: daily,
    });
    setLimits(updated);
    setIsLimitsOpen(false);
    showToast(`Transfer limits updated: $${perTx.toFixed(2)} / tx, $${daily.toFixed(2)} / day`);
  };

  // MFA Confirmation
  const handleConfirmMfa = async (pin: string) => {
    if (!pendingAction) return;

    setMfaError(null);
    setIsSubmittingTransfer(true);

    try {
      if (pendingAction.type === 'internal') {
        await api.executeTransfer({ ...pendingAction.data, pin });
        showToast(`Successfully transferred $${pendingAction.data.amount.toFixed(2)} with MFA authorization`);
      } else if (pendingAction.type === 'ach') {
        await api.executeAchTransfer({ ...pendingAction.data, pin });
        showToast(`ACH Transfer of $${pendingAction.data.amount.toFixed(2)} authorized with MFA`);
      } else if (pendingAction.type === 'recurring') {
        await api.createRecurringSchedule({ ...pendingAction.data, pin });
        showToast(`Recurring schedule authorized and active ($${pendingAction.data.amount.toFixed(2)})`);
      }

      setIsMfaOpen(false);
      setPendingAction(null);

      // Refresh all related data
      await Promise.all([
        loadAccounts(),
        loadTransactions(selectedAccountId),
        loadMfaStatus(),
        loadBeneficiaries(),
        loadRecurringSchedules(),
        loadLimits(),
      ]);
    } catch (err: any) {
      await loadMfaStatus();
      setMfaError(err.message || 'Invalid Security PIN');
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // Resolve pending accounts for MFA modal display
  let pendingFromAccount: Account | null = null;
  let pendingToAccount: Account | null = null;
  let pendingAmount = 0;

  if (pendingAction) {
    pendingFromAccount = accounts.find((a) => a.id === pendingAction.data.from_account_id) || null;
    pendingAmount = pendingAction.data.amount;
    if (pendingAction.type === 'internal') {
      pendingToAccount = accounts.find((a) => a.id === pendingAction.data.to_account_id) || null;
    } else if (pendingAction.type === 'recurring' && pendingAction.data.to_account_id) {
      pendingToAccount = accounts.find((a) => a.id === pendingAction.data.to_account_id) || null;
    }
  }

  return (
    <div className="app-container">
      <Navbar
        onOpenTransfer={() => {
          setTransferError(null);
          setIsTransferOpen(true);
        }}
        onOpenRecurring={() => setIsRecurringOpen(true)}
        onOpenLimits={() => setIsLimitsOpen(true)}
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

      {/* Transfer Modal (Internal & External ACH) */}
      <TransferModal
        isOpen={isTransferOpen}
        accounts={accounts}
        beneficiaries={beneficiaries}
        limits={limits}
        isSubmitting={isSubmittingTransfer}
        errorMessage={transferError}
        onClose={() => setIsTransferOpen(false)}
        onSubmit={handleInitiateTransfer}
        onSubmitAch={handleInitiateAchTransfer}
      />

      {/* Dynamic Transfer Limits Modal */}
      <TransferLimits
        isOpen={isLimitsOpen}
        limits={limits}
        onClose={() => setIsLimitsOpen(false)}
        onUpdateLimits={handleUpdateLimits}
      />

      {/* Recurring Payments Modal */}
      <RecurringPayments
        isOpen={isRecurringOpen}
        schedules={recurringSchedules}
        accounts={accounts}
        beneficiaries={beneficiaries}
        onClose={() => setIsRecurringOpen(false)}
        onCreateSchedule={handleCreateRecurringSchedule}
        onPauseSchedule={handlePauseRecurringSchedule}
        onResumeSchedule={handleResumeRecurringSchedule}
        onCancelSchedule={handleCancelRecurringSchedule}
      />

      {/* MFA Security PIN Modal */}
      <MfaModal
        isOpen={isMfaOpen}
        fromAccount={pendingFromAccount}
        toAccount={pendingToAccount}
        amount={pendingAmount}
        remainingAttempts={mfaStatus.remaining_attempts}
        isLocked={mfaStatus.locked}
        errorMessage={mfaError}
        isSubmitting={isSubmittingTransfer}
        onConfirm={handleConfirmMfa}
        onCancel={() => {
          setIsMfaOpen(false);
          setPendingAction(null);
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
