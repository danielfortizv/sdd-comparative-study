import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError, generateIdempotencyKey } from './api/client';
import {
  Account,
  Transaction,
  TransferRequest,
  ConversionResponse,
  MfaStatus,
  Beneficiary,
  AchTransferRequest,
  RecurringSchedule,
  RecurringScheduleCreateRequest,
  TransferLimits as TransferLimitsType,
} from './api/types';
import {
  formatCurrency,
  isUsdEquivalentExceedingThreshold,
  SupportedCurrency,
} from './utils/monetary';
import { Navbar } from './components/Navbar';
import { AccountSummary } from './components/AccountSummary';
import { TransactionHistory } from './components/TransactionHistory';
import { TransferModal } from './components/TransferModal';
import { ConversionModal } from './components/ConversionModal';
import { MfaModal } from './components/MfaModal';
import { TransferLimits } from './components/TransferLimits';
import { RecurringPayments } from './components/RecurringPayments';

interface ActiveOperation {
  payloadKey: string;
  idempotencyKey: string;
}

type PendingAction =
  | { type: 'internal'; data: TransferRequest; idempotencyKey?: string }
  | { type: 'ach'; data: AchTransferRequest; idempotencyKey?: string }
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
  const [isConversionOpen, setIsConversionOpen] = useState<boolean>(false);
  const [isMfaOpen, setIsMfaOpen] = useState<boolean>(false);
  const [isLimitsOpen, setIsLimitsOpen] = useState<boolean>(false);
  const [isRecurringOpen, setIsRecurringOpen] = useState<boolean>(false);

  // Active and pending operation state
  const [activeTransferOperation, setActiveTransferOperation] = useState<ActiveOperation | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [isSubmittingTransfer, setIsSubmittingTransfer] = useState<boolean>(false);

  const [mfaStatus, setMfaStatus] = useState<MfaStatus>({
    threshold: '1000.00',
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
    if (isSubmittingTransfer) return;
    setTransferError(null);

    const fromAcc = accounts.find((a) => a.id === transferData.from_account_id);
    const sourceCurrency = (fromAcc?.currency || 'USD') as SupportedCurrency;

    // Stable D-13 operation identity: compute fingerprint from canonical payload
    const payloadKey = JSON.stringify({
      type: 'internal',
      from_account_id: transferData.from_account_id,
      to_account_id: transferData.to_account_id,
      amount: transferData.amount,
      expected_from_version: transferData.expected_from_version,
      expected_to_version: transferData.expected_to_version,
      description: transferData.description,
    });

    let idempotencyKey: string;
    if (activeTransferOperation && activeTransferOperation.payloadKey === payloadKey) {
      idempotencyKey = activeTransferOperation.idempotencyKey;
    } else {
      idempotencyKey = generateIdempotencyKey();
      setActiveTransferOperation({ payloadKey, idempotencyKey });
    }

    if (
      isUsdEquivalentExceedingThreshold(
        transferData.amount,
        sourceCurrency,
        mfaStatus.threshold
      )
    ) {
      setPendingAction({ type: 'internal', data: transferData, idempotencyKey });
      setIsTransferOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    setIsSubmittingTransfer(true);
    try {
      await api.executeTransfer(transferData, idempotencyKey);
      setIsTransferOpen(false);
      setActiveTransferOperation(null);
      showToast(
        `Successfully transferred ${formatCurrency(transferData.amount, sourceCurrency)}`
      );
      await Promise.all([loadAccounts(), loadTransactions(selectedAccountId), loadLimits()]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        setPendingAction({ type: 'internal', data: transferData, idempotencyKey });
        setIsTransferOpen(false);
        setIsMfaOpen(true);
      } else if (err instanceof ApiError && err.status === 409) {
        if (err.code === 'ACCOUNT_VERSION_CONFLICT') {
          setActiveTransferOperation(null);
          setTransferError(
            err.message || 'Account version conflict detected: Account balances have changed. Refreshing accounts...'
          );
          loadAccounts();
        } else if (err.code === 'IDEMPOTENCY_KEY_REUSE' || err.code === 'IDEMPOTENCY_KEY_CONFLICT') {
          setTransferError(
            err.message || 'Idempotency conflict: Key was previously submitted with different parameters.'
          );
        } else {
          setActiveTransferOperation(null);
          setTransferError(err.message || 'Conflict occurred during transfer.');
        }
      } else {
        setTransferError(err.message || 'Transfer failed');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // ACH Transfer submission
  const handleInitiateAchTransfer = async (achData: AchTransferRequest) => {
    if (isSubmittingTransfer) return;
    setTransferError(null);

    const fromAcc = accounts.find((a) => a.id === achData.from_account_id);
    const sourceCurrency = (fromAcc?.currency || 'USD') as SupportedCurrency;

    // Stable D-13 operation identity: compute fingerprint from canonical payload
    const payloadKey = JSON.stringify({
      type: 'ach',
      from_account_id: achData.from_account_id,
      beneficiary_id: achData.beneficiary_id,
      recipient_name: achData.recipient_name,
      routing_number: achData.routing_number,
      account_number: achData.account_number,
      bank_name: achData.bank_name,
      amount: achData.amount,
      expected_from_version: achData.expected_from_version,
      description: achData.description,
      save_beneficiary: achData.save_beneficiary,
    });

    let idempotencyKey: string;
    if (activeTransferOperation && activeTransferOperation.payloadKey === payloadKey) {
      idempotencyKey = activeTransferOperation.idempotencyKey;
    } else {
      idempotencyKey = generateIdempotencyKey();
      setActiveTransferOperation({ payloadKey, idempotencyKey });
    }

    if (
      isUsdEquivalentExceedingThreshold(
        achData.amount,
        sourceCurrency,
        mfaStatus.threshold
      )
    ) {
      setPendingAction({ type: 'ach', data: achData, idempotencyKey });
      setIsTransferOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    setIsSubmittingTransfer(true);
    try {
      await api.executeAchTransfer(achData, idempotencyKey);
      setIsTransferOpen(false);
      setActiveTransferOperation(null);
      showToast(
        `ACH Transfer of ${formatCurrency(achData.amount, sourceCurrency)} initiated in pending status`
      );
      await Promise.all([
        loadAccounts(),
        loadTransactions(selectedAccountId),
        loadBeneficiaries(),
        loadLimits(),
      ]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 428) {
        setPendingAction({ type: 'ach', data: achData, idempotencyKey });
        setIsTransferOpen(false);
        setIsMfaOpen(true);
      } else if (err instanceof ApiError && err.status === 409) {
        if (err.code === 'ACCOUNT_VERSION_CONFLICT') {
          setActiveTransferOperation(null);
          setTransferError(
            err.message || 'Account version conflict detected: Account balances have changed. Refreshing accounts...'
          );
          loadAccounts();
        } else if (err.code === 'IDEMPOTENCY_KEY_REUSE' || err.code === 'IDEMPOTENCY_KEY_CONFLICT') {
          setTransferError(
            err.message || 'Idempotency conflict: Key was previously submitted with different parameters.'
          );
        } else {
          setActiveTransferOperation(null);
          setTransferError(err.message || 'Conflict occurred during ACH transfer.');
        }
      } else {
        setTransferError(err.message || 'ACH Transfer failed');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // Conversion Success Handler
  const handleConversionSuccess = (res: ConversionResponse) => {
    showToast(
      `Converted ${formatCurrency(res.source_amount, res.source_currency)} → ${formatCurrency(res.destination_amount, res.destination_currency)}`
    );
    Promise.all([
      loadAccounts(),
      loadTransactions(selectedAccountId),
      loadLimits(),
    ]);
  };

  // Recurring Schedule Creation
  const handleCreateRecurringSchedule = async (scheduleData: RecurringScheduleCreateRequest) => {
    const fromAcc = accounts.find((a) => a.id === scheduleData.from_account_id);
    const sourceCurrency = (fromAcc?.currency || 'USD') as SupportedCurrency;

    if (
      isUsdEquivalentExceedingThreshold(
        scheduleData.amount,
        sourceCurrency,
        mfaStatus.threshold
      ) &&
      !scheduleData.pin
    ) {
      setPendingAction({ type: 'recurring', data: scheduleData });
      setIsRecurringOpen(false);
      setIsMfaOpen(true);
      setMfaError(null);
      return;
    }

    try {
      await api.createRecurringSchedule(scheduleData);
      showToast(
        `Successfully configured ${scheduleData.frequency} recurring payment of ${formatCurrency(scheduleData.amount, sourceCurrency)}`
      );
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
  const handleUpdateLimits = async (perTx: string, daily: string) => {
    const updated = await api.updateLimits({
      per_transaction_limit: perTx,
      daily_limit: daily,
    });
    setLimits(updated);
    setIsLimitsOpen(false);
    const refCurrency = updated.reference_currency || limits?.reference_currency || 'USD';
    showToast(
      `Transfer limits updated: ${formatCurrency(perTx, refCurrency)} / tx, ${formatCurrency(daily, refCurrency)} / day`
    );
  };

  // MFA Confirmation
  const handleConfirmMfa = async (pin: string) => {
    if (!pendingAction || isSubmittingTransfer) return;

    setMfaError(null);
    setIsSubmittingTransfer(true);

    try {
      const fromAcc = accounts.find((a) => a.id === pendingAction.data.from_account_id);
      const sourceCurrency = (fromAcc?.currency || 'USD') as SupportedCurrency;
      const formattedAmount = formatCurrency(pendingAction.data.amount, sourceCurrency);

      if (pendingAction.type === 'internal') {
        await api.executeTransfer({ ...pendingAction.data, pin }, pendingAction.idempotencyKey);
        showToast(`Successfully transferred ${formattedAmount} with MFA authorization`);
      } else if (pendingAction.type === 'ach') {
        await api.executeAchTransfer({ ...pendingAction.data, pin }, pendingAction.idempotencyKey);
        showToast(`ACH Transfer of ${formattedAmount} authorized with MFA`);
      } else if (pendingAction.type === 'recurring') {
        await api.createRecurringSchedule({ ...pendingAction.data, pin });
        showToast(`Recurring schedule authorized and active (${formattedAmount})`);
      }

      setIsMfaOpen(false);
      setPendingAction(null);
      setActiveTransferOperation(null);

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
      if (err instanceof ApiError && err.status === 409) {
        setIsMfaOpen(false);
        setPendingAction(null);
        setActiveTransferOperation(null);
        setTransferError('Account version conflict detected: Account balances have changed. Refreshing accounts...');
        loadAccounts();
      } else {
        await loadMfaStatus();
        setMfaError(err.message || 'Invalid Security PIN');
      }
    } finally {
      setIsSubmittingTransfer(false);
    }
  };

  // Resolve pending accounts for MFA modal display
  let pendingFromAccount: Account | null = null;
  let pendingToAccount: Account | null = null;
  let pendingAmount = '0.00';

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
          setActiveTransferOperation(null);
          setIsTransferOpen(true);
        }}
        onOpenConversion={() => {
          setIsConversionOpen(true);
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

      {/* Transfer Modal (Internal Same-Currency & External ACH) */}
      <TransferModal
        isOpen={isTransferOpen}
        accounts={accounts}
        beneficiaries={beneficiaries}
        limits={limits}
        isSubmitting={isSubmittingTransfer}
        errorMessage={transferError}
        onClose={() => {
          setIsTransferOpen(false);
          setTransferError(null);
          setActiveTransferOperation(null);
        }}
        onSubmit={handleInitiateTransfer}
        onSubmitAch={handleInitiateAchTransfer}
      />

      {/* Simulated Currency Conversion Modal (D-04, D-10) */}
      <ConversionModal
        isOpen={isConversionOpen}
        onClose={() => setIsConversionOpen(false)}
        accounts={accounts}
        onConversionSuccess={handleConversionSuccess}
        onRefreshAccounts={loadAccounts}
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
          setActiveTransferOperation(null);
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
