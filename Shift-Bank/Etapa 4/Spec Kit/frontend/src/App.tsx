import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Account,
  Transfer,
  HistoryEntry,
  LimitResponse,
  Beneficiary,
  RecurringSchedule,
  RecurringScheduleCreate,
  RecurringFrequency,
} from './types';
import {
  fetchAccounts,
  fetchHistory,
  initiateTransfer,
  confirmMFA,
  fetchLimits,
  updateLimits,
  fetchBeneficiaries,
  createBeneficiary,
  deleteBeneficiary,
  initiateAchTransfer,
  fetchSchedules,
  createSchedule,
  confirmScheduleMFA,
  pauseSchedule,
  resumeSchedule,
  cancelSchedule,
} from './services';

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // Stage 2: Dynamic Limits States (User Story 1, T014)
  const [limits, setLimits] = useState<LimitResponse | null>(null);
  const [showLimitsEdit, setShowLimitsEdit] = useState<boolean>(false);
  const [perTransferInput, setPerTransferInput] = useState<string>('');
  const [dailyLimitInput, setDailyLimitInput] = useState<string>('');
  const [limitsError, setLimitsError] = useState<string | null>(null);
  const [limitsSuccess, setLimitsSuccess] = useState<string | null>(null);
  const [limitsSubmitting, setLimitsSubmitting] = useState<boolean>(false);

  // Stage 2: ACH & Beneficiaries States (User Story 2, T025)
  const [transferTab, setTransferTab] = useState<'internal' | 'ach'>('internal');
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [achSourceAccountId, setAchSourceAccountId] = useState<string>('');
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState<string>('new');
  const [achRecipientName, setAchRecipientName] = useState<string>('');
  const [achBankName, setAchBankName] = useState<string>('');
  const [achRoutingNumber, setAchRoutingNumber] = useState<string>('');
  const [achAccountNumber, setAchAccountNumber] = useState<string>('');
  const [achAmount, setAchAmount] = useState<string>('');
  const [achSaveBeneficiary, setAchSaveBeneficiary] = useState<boolean>(false);
  const [achRoutingError, setAchRoutingError] = useState<string | null>(null);
  const [achAccountError, setAchAccountError] = useState<string | null>(null);
  const [achFormError, setAchFormError] = useState<string | null>(null);
  const [achSubmitting, setAchSubmitting] = useState<boolean>(false);

  // Beneficiary Management States
  const [showAddBeneficiary, setShowAddBeneficiary] = useState<boolean>(false);
  const [newBenName, setNewBenName] = useState<string>('');
  const [newBenBank, setNewBenBank] = useState<string>('');
  const [newBenRouting, setNewBenRouting] = useState<string>('');
  const [newBenAccount, setNewBenAccount] = useState<string>('');
  const [newBenRoutingError, setNewBenRoutingError] = useState<string | null>(null);
  const [benError, setBenError] = useState<string | null>(null);
  const [benSubmitting, setBenSubmitting] = useState<boolean>(false);

  // Stage 2: Recurring Payments States (User Story 3, T036)
  const [schedules, setSchedules] = useState<RecurringSchedule[]>([]);
  const [showAddSchedule, setShowAddSchedule] = useState<boolean>(false);
  const [schedType, setSchedType] = useState<'INTERNAL' | 'ACH'>('INTERNAL');
  const [schedSourceAccountId, setSchedSourceAccountId] = useState<string>('');
  const [schedDestAccountId, setSchedDestAccountId] = useState<string>('');
  const [schedBeneficiaryId, setSchedBeneficiaryId] = useState<string>('new');
  const [schedRecipientName, setSchedRecipientName] = useState<string>('');
  const [schedBankName, setSchedBankName] = useState<string>('');
  const [schedRouting, setSchedRouting] = useState<string>('');
  const [schedAccount, setSchedAccount] = useState<string>('');
  const [schedAmount, setSchedAmount] = useState<string>('');
  const [schedFrequency, setSchedFrequency] = useState<RecurringFrequency>('MONTHLY');
  const [schedStartDate, setSchedStartDate] = useState<string>('');
  const [schedRoutingError, setSchedRoutingError] = useState<string | null>(null);
  const [schedFormError, setSchedFormError] = useState<string | null>(null);
  const [schedSubmitting, setSchedSubmitting] = useState<boolean>(false);
  const [pendingMfaSchedule, setPendingMfaSchedule] = useState<RecurringSchedule | null>(null);
  
  // Loading and global alert states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Transfer Form States (User Story 2)
  const [sourceAccountId, setSourceAccountId] = useState<string>('');
  const [destinationAccountId, setDestinationAccountId] = useState<string>('');
  const [transferAmount, setTransferAmount] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);

  // MFA State Machine (User Story 4)
  const [showMfaModal, setShowMfaModal] = useState<boolean>(false);
  const [pendingTransfer, setPendingTransfer] = useState<Transfer | null>(null);
  const [pendingTransfersList, setPendingTransfersList] = useState<Transfer[]>([]);
  const [mfaCode, setMfaCode] = useState<string>('');
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [mfaSubmitting, setMfaSubmitting] = useState<boolean>(false);
  
  // Timer for MFA Expiration
  const [timeLeft, setTimeLeft] = useState<number>(300); // 5 minutes in seconds
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load history function
  const loadHistoryData = useCallback(async (accountId: string) => {
    try {
      const historyData = await fetchHistory(accountId);
      setHistory(historyData);
    } catch (err: any) {
      setError(err.message || 'Failed to load transaction history.');
    }
  }, []);

  // Load limits function (User Story 1, T014)
  const loadLimitsData = useCallback(async () => {
    try {
      const data = await fetchLimits();
      setLimits(data);
      setPerTransferInput(data.per_transfer_limit);
      setDailyLimitInput(data.daily_limit);
    } catch {
      // Non-blocking error for limits display
    }
  }, []);

  // Limits update submit handler (User Story 1, T014)
  const handleLimitsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLimitsError(null);
    setLimitsSuccess(null);

    const isValidDecimal = (val: string) => {
      const trimmed = val.trim();
      if (!trimmed) return false;
      const parts = trimmed.split('.');
      if (parts.length > 2) return false;
      if (parts.length === 2 && parts[1].length > 2) return false;
      const num = parseFloat(trimmed);
      return !isNaN(num) && num > 0;
    };

    if (!isValidDecimal(perTransferInput) || !isValidDecimal(dailyLimitInput)) {
      setLimitsError("Limits must be strictly positive amounts with at most 2 decimal places.");
      return;
    }

    const perNum = parseFloat(perTransferInput);
    const dailyNum = parseFloat(dailyLimitInput);

    try {
      setLimitsSubmitting(true);
      const updated = await updateLimits({
        per_transfer_limit: perNum.toFixed(2),
        daily_limit: dailyNum.toFixed(2),
      });
      setLimits(updated);
      setLimitsSuccess("Transfer limits updated successfully!");
      setShowLimitsEdit(false);
    } catch (err: any) {
      setLimitsError(err.message || "Failed to update transfer limits.");
    } finally {
      setLimitsSubmitting(false);
    }
  };

  // Load beneficiaries function (User Story 2, T025)
  const loadBeneficiariesData = useCallback(async () => {
    try {
      const data = await fetchBeneficiaries();
      setBeneficiaries(data);
    } catch {
      // Non-blocking for initial load
    }
  }, []);

  // Real-time routing number change handler (ACH-10, A05)
  const handleAchRoutingChange = (val: string) => {
    setAchRoutingNumber(val);
    const trimmed = val.trim();
    if (!trimmed) {
      setAchRoutingError(null);
    } else if (trimmed.length !== 9 || !/^\d+$/.test(trimmed)) {
      setAchRoutingError("Routing number must be exactly 9 numeric digits.");
    } else {
      setAchRoutingError(null);
    }
  };

  // Real-time account number change handler (A06)
  const handleAchAccountChange = (val: string) => {
    setAchAccountNumber(val);
    const trimmed = val.trim();
    if (!trimmed) {
      setAchAccountError(null);
    } else if (trimmed.length < 4 || trimmed.length > 17 || !/^\d+$/.test(trimmed)) {
      setAchAccountError("Account number must be between 4 and 17 numeric digits.");
    } else {
      setAchAccountError(null);
    }
  };

  // Beneficiary dropdown selector handler
  const handleBeneficiarySelect = (benId: string) => {
    setSelectedBeneficiaryId(benId);
    setAchRoutingError(null);
    setAchAccountError(null);
    if (benId === 'new') {
      setAchRecipientName('');
      setAchBankName('');
      setAchRoutingNumber('');
      setAchAccountNumber('');
      setAchSaveBeneficiary(false);
    } else {
      const ben = beneficiaries.find(b => b.id === benId);
      if (ben) {
        setAchRecipientName(ben.name);
        setAchBankName(ben.bank_name);
        setAchRoutingNumber(ben.routing_number);
        setAchAccountNumber(ben.account_number);
        setAchSaveBeneficiary(false);
      }
    }
  };

  // Create new beneficiary handler
  const handleCreateBeneficiary = async (e: React.FormEvent) => {
    e.preventDefault();
    setBenError(null);

    const routing = newBenRouting.trim();
    const account = newBenAccount.trim();

    if (routing.length !== 9 || !/^\d+$/.test(routing)) {
      setNewBenRoutingError("Routing number must be exactly 9 numeric digits.");
      return;
    }
    if (account.length < 4 || account.length > 17 || !/^\d+$/.test(account)) {
      setBenError("Account number must be between 4 and 17 numeric digits.");
      return;
    }

    try {
      setBenSubmitting(true);
      await createBeneficiary({
        name: newBenName.trim(),
        bank_name: newBenBank.trim(),
        routing_number: routing,
        account_number: account,
      });
      setSuccess(`Beneficiary "${newBenName.trim()}" saved successfully!`);
      setNewBenName('');
      setNewBenBank('');
      setNewBenRouting('');
      setNewBenAccount('');
      setShowAddBeneficiary(false);
      await loadBeneficiariesData();
    } catch (err: any) {
      setBenError(err.message || "Failed to save beneficiary.");
    } finally {
      setBenSubmitting(false);
    }
  };

  // Delete beneficiary handler (D-08, REC-11)
  const handleDeleteBeneficiary = async (id: string) => {
    try {
      await deleteBeneficiary(id);
      setSuccess("Beneficiary deleted successfully.");
      await loadBeneficiariesData();
    } catch (err: any) {
      setError(err.message || "Failed to delete beneficiary.");
    }
  };

  // Decimal precision validator helper (Requirement 10)
  const isValidAmountDecimal = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return false;
    const parts = trimmed.split('.');
    if (parts.length > 2) return false;
    if (parts.length === 2 && parts[1].length > 2) return false;
    const num = parseFloat(trimmed);
    return !isNaN(num) && num > 0;
  };

  // ACH Transfer Submit Handler (User Story 2, T025)
  const handleAchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAchFormError(null);
    setSuccess(null);
    setError(null);

    const routing = achRoutingNumber.trim();
    const account = achAccountNumber.trim();

    if (routing.length !== 9 || !/^\d+$/.test(routing)) {
      setAchFormError("Routing number must be exactly 9 numeric digits.");
      return;
    }

    if (account.length < 4 || account.length > 17 || !/^\d+$/.test(account)) {
      setAchFormError("Account number must be between 4 and 17 numeric digits.");
      return;
    }

    if (!isValidAmountDecimal(achAmount)) {
      setAchFormError("Amount must be greater than zero, with at most 2 decimal places.");
      return;
    }

    const amt = parseFloat(achAmount);
    const srcAccount = accounts.find(a => a.id === achSourceAccountId);
    if (srcAccount && amt > parseFloat(srcAccount.balance)) {
      setAchFormError("Insufficient funds.");
      return;
    }

    try {
      setAchSubmitting(true);
      const formattedAmountStr = amt.toFixed(2);

      const result = await initiateAchTransfer({
        source_account_id: achSourceAccountId || (accounts[0] ? accounts[0].id : ''),
        amount: formattedAmountStr,
        recipient_name: achRecipientName.trim(),
        bank_name: achBankName.trim(),
        routing_number: routing,
        account_number: account,
        save_beneficiary: achSaveBeneficiary,
      });

      if (result.status === 'PENDING_MFA') {
        // Trigger shared MFA modal for sensitive ACH transfer
        setPendingTransfer({
          id: result.id,
          source_account: result.source_account,
          destination_account: `${result.recipient_name} (${result.bank_name})`,
          amount: result.amount,
          status: 'PENDING_MFA',
          created_at: result.created_at,
          expires_at: result.expires_at || null,
        });
        setPendingMfaSchedule(null);
        setTimeLeft(300);
        setShowMfaModal(true);
      } else {
        setSuccess(`ACH Transfer of ${formatCurrency(formattedAmountStr)} to ${result.recipient_name} initiated successfully (Pending settlement).`);
        setAchAmount('');
        if (selectedBeneficiaryId === 'new') {
          setAchRecipientName('');
          setAchBankName('');
          setAchRoutingNumber('');
          setAchAccountNumber('');
        }
        await loadAccountsData(selectedAccountId || achSourceAccountId);
        await loadBeneficiariesData();
      }
    } catch (err: any) {
      setAchFormError(err.message || "Failed to initiate ACH transfer.");
    } finally {
      setAchSubmitting(false);
    }
  };

  // Load recurring schedules function (User Story 3, T036)
  const loadSchedulesData = useCallback(async () => {
    try {
      const data = await fetchSchedules();
      setSchedules(data);
    } catch {
      // Non-blocking
    }
  }, []);

  // Create Recurring Schedule handler (User Story 3, T036)
  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setSchedFormError(null);
    setSuccess(null);
    setError(null);

    if (!isValidAmountDecimal(schedAmount)) {
      setSchedFormError("Amount must be greater than zero, with at most 2 decimal places.");
      return;
    }

    if (schedType === 'INTERNAL' && schedSourceAccountId === schedDestAccountId) {
      setSchedFormError("Source and destination accounts must be different.");
      return;
    }

    if (schedType === 'ACH') {
      const routing = schedRouting.trim();
      const account = schedAccount.trim();
      if (routing.length !== 9 || !/^\d+$/.test(routing)) {
        setSchedFormError("Routing number must be exactly 9 numeric digits.");
        return;
      }
      if (account.length < 4 || account.length > 17 || !/^\d+$/.test(account)) {
        setSchedFormError("Account number must be between 4 and 17 numeric digits.");
        return;
      }
    }

    try {
      setSchedSubmitting(true);
      const amtNum = parseFloat(schedAmount);
      const formattedAmountStr = amtNum.toFixed(2);

      const payload: RecurringScheduleCreate = {
        transfer_type: schedType,
        source_account_id: schedSourceAccountId || (accounts[0] ? accounts[0].id : ''),
        amount: formattedAmountStr,
        frequency: schedFrequency,
        start_date: schedStartDate.trim() ? schedStartDate.trim() : undefined,
        destination_account_id: schedType === 'INTERNAL' ? (schedDestAccountId || (accounts[1] ? accounts[1].id : '')) : undefined,
        recipient_name: schedType === 'ACH' ? schedRecipientName.trim() : undefined,
        bank_name: schedType === 'ACH' ? schedBankName.trim() : undefined,
        routing_number: schedType === 'ACH' ? schedRouting.trim() : undefined,
        account_number: schedType === 'ACH' ? schedAccount.trim() : undefined,
      };

      const result = await createSchedule(payload);

      if (result.status === 'PENDING_MFA') {
        // Sensitive recurring schedule requires MFA
        setPendingMfaSchedule(result);
        setPendingTransfer(null);
        setTimeLeft(300);
        setShowMfaModal(true);
      } else {
        setSuccess(`Recurring schedule to ${result.destination_display} created successfully!`);
        setShowAddSchedule(false);
        setSchedAmount('');
        setSchedStartDate('');
        await loadSchedulesData();
      }
    } catch (err: any) {
      setSchedFormError(err.message || "Failed to create recurring schedule.");
    } finally {
      setSchedSubmitting(false);
    }
  };

  const handlePauseSchedule = async (id: string) => {
    try {
      await pauseSchedule(id);
      setSuccess("Recurring schedule paused successfully.");
      await loadSchedulesData();
    } catch (err: any) {
      setError(err.message || "Failed to pause recurring schedule.");
    }
  };

  const handleResumeSchedule = async (id: string) => {
    try {
      await resumeSchedule(id);
      setSuccess("Recurring schedule resumed successfully.");
      await loadSchedulesData();
    } catch (err: any) {
      setError(err.message || "Failed to resume recurring schedule.");
    }
  };

  const handleCancelSchedule = async (id: string) => {
    try {
      await cancelSchedule(id);
      setSuccess("Recurring schedule cancelled successfully.");
      await loadSchedulesData();
    } catch (err: any) {
      setError(err.message || "Failed to cancel recurring schedule.");
    }
  };

  const handleResumeScheduleMfa = (sched: RecurringSchedule) => {
    setPendingMfaSchedule(sched);
    setPendingTransfer(null);
    setMfaCode('');
    setMfaError(null);
    setTimeLeft(300);
    setShowMfaModal(true);
  };

  // Load accounts and initial setup
  const loadAccountsData = async (shouldLoadHistoryForId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAccounts();
      setAccounts(data);
      await loadLimitsData();
      await loadBeneficiariesData();
      await loadSchedulesData();
      
      if (data.length > 0) {
        const checking = data.find(a => a.name === 'Checking');
        const defaultSrcId = checking ? checking.id : data[0].id;
        
        let activeId = selectedAccountId;
        if (!activeId) {
          activeId = defaultSrcId;
          setSelectedAccountId(activeId);
        }

        // Default form selections if not set
        if (!sourceAccountId) {
          setSourceAccountId(defaultSrcId);
        }
        if (!destinationAccountId) {
          const savings = data.find(a => a.name === 'Savings');
          setDestinationAccountId(savings ? savings.id : (data[1] ? data[1].id : ''));
        }
        if (!achSourceAccountId) {
          setAchSourceAccountId(defaultSrcId);
        }
        if (!schedSourceAccountId) {
          setSchedSourceAccountId(defaultSrcId);
        }
        if (!schedDestAccountId) {
          const savings = data.find(a => a.name === 'Savings');
          setSchedDestAccountId(savings ? savings.id : (data[1] ? data[1].id : ''));
        }

        // Fetch transaction history for active account
        const idToFetch = shouldLoadHistoryForId || activeId;
        await loadHistoryData(idToFetch);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load accounts.');
    } finally {
      setLoading(false);
    }
  };

  // Load initial bank data on mount
  useEffect(() => {
    loadAccountsData();
  }, []);

  // Re-fetch transaction history whenever the selected account changes on dashboard
  useEffect(() => {
    if (selectedAccountId) {
      loadHistoryData(selectedAccountId);
    }
  }, [selectedAccountId, loadHistoryData]);

  // MFA Expiration timer effect
  useEffect(() => {
    if (showMfaModal && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft <= 0) {
      setMfaError("The 5-minute MFA window has expired. Submitting will result in error.");
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [showMfaModal, timeLeft]);

  // Format currency helper (strictly Colombian Peso)
  const formatCurrency = (amount: string) => {
    const num = parseFloat(amount);
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
    }).format(num);
  };

  // Format date helper
  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('es-CO', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  // Format remaining timer helper
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // Transfer Submit Handler (User Stories 2 & 4)
  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccess(null);
    setError(null);

    // 1. Client-side validations
    if (sourceAccountId === destinationAccountId) {
      setFormError("Source and destination accounts must be different.");
      return;
    }

    if (!isValidAmountDecimal(transferAmount)) {
      setFormError("Amount must be greater than zero, with at most 2 decimal places.");
      return;
    }

    const amountNum = parseFloat(transferAmount);
    const sourceAccount = accounts.find(a => a.id === sourceAccountId);
    if (!sourceAccount) {
      setFormError("Source account not found.");
      return;
    }

    const sourceBalance = parseFloat(sourceAccount.balance);
    if (amountNum > sourceBalance) {
      setFormError("Insufficient funds.");
      return;
    }

    // 2. Call API
    try {
      setFormSubmitting(true);
      const formattedAmountStr = amountNum.toFixed(2);

      const transferResult = await initiateTransfer(
        sourceAccountId,
        destinationAccountId,
        formattedAmountStr
      );

      // Handle sensitive transfer pending MFA (202 Accepted response)
      if (transferResult.status === 'PENDING_MFA') {
        setPendingTransfer(transferResult);
        setPendingMfaSchedule(null);
        setMfaCode('');
        setMfaError(null);
        if (transferResult.expires_at) {
          const expiresAt = new Date(transferResult.expires_at).getTime();
          const now = new Date().getTime();
          const remainingSeconds = Math.max(0, Math.round((expiresAt - now) / 1000));
          setTimeLeft(remainingSeconds);
        } else {
          setTimeLeft(300); // Reset timer to 5 minutes
        }
        setShowMfaModal(true);
      } else if (transferResult.status === 'COMPLETED') {
        // Direct standard transfer success
        setSuccess(`Transfer of ${formatCurrency(formattedAmountStr)} executed successfully!`);
        setTransferAmount(''); // Clear form input
        await loadAccountsData(selectedAccountId || sourceAccountId);
      }
    } catch (err: any) {
      setFormError(err.message || "An error occurred initiating the transfer.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // MFA Code Submit Handler (User Story 4 & User Story 3)
  const handleMfaConfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMfaError(null);

    if (mfaCode.length !== 6 || !/^\d+$/.test(mfaCode)) {
      setMfaError("MFA code must be exactly 6 digits.");
      return;
    }

    try {
      setMfaSubmitting(true);

      if (pendingMfaSchedule) {
        // Confirm Recurring Schedule MFA
        await confirmScheduleMFA(pendingMfaSchedule.id, mfaCode);
        setSuccess(`Recurring schedule to ${pendingMfaSchedule.destination_display} activated successfully!`);
        setShowMfaModal(false);
        setPendingMfaSchedule(null);
        setMfaCode('');
        await loadSchedulesData();
      } else if (pendingTransfer) {
        // Confirm Transfer MFA
        const res = await confirmMFA(pendingTransfer.id, mfaCode);

        if (res.status === 'COMPLETED' || res.status === 'PENDING') {
          setSuccess(`Transfer of ${formatCurrency(pendingTransfer.amount)} verified successfully!`);
          setTransferAmount(''); // Clear transfer form input
          
          // Remove from pending list if confirming a resumed transfer
          setPendingTransfersList(prev => prev.filter(t => t.id !== pendingTransfer.id));
          
          // Close modal and reset
          setShowMfaModal(false);
          setPendingTransfer(null);
          
          // Reload all balances, limits, and history
          await loadAccountsData(selectedAccountId || '');
        }
      }
    } catch (err: any) {
      setMfaError(err.message || "MFA confirmation failed.");
    } finally {
      setMfaSubmitting(false);
    }
  };

  // Close MFA modal handler (moves transfer to resume list)
  const handleMfaModalClose = () => {
    if (pendingTransfer) {
      setPendingTransfersList(prev => {
        if (prev.some(t => t.id === pendingTransfer.id)) return prev;
        return [...prev, pendingTransfer];
      });
    }
    setShowMfaModal(false);
    setPendingTransfer(null);
    setPendingMfaSchedule(null);
    setMfaCode('');
    setMfaError(null);
  };

  // Resume a pending transfer from the list
  const handleResumeTransfer = (tx: Transfer) => {
    setPendingTransfer(tx);
    setMfaCode('');
    setMfaError(null);
    if (tx.expires_at) {
      const expiresAt = new Date(tx.expires_at).getTime();
      const now = new Date().getTime();
      const remainingSeconds = Math.max(0, Math.round((expiresAt - now) / 1000));
      setTimeLeft(remainingSeconds);
      if (remainingSeconds <= 0) {
        setMfaError("The 5-minute MFA window has expired. Submitting will result in error.");
      }
    } else {
      setTimeLeft(300); // Fallback
    }
    setShowMfaModal(true);
  };

  // Find currently selected account name for display
  const selectedAccountName = accounts.find(a => a.id === selectedAccountId)?.name || 'Account';

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <span>🏦</span> Shift Bank
        </div>
        <div style={{ color: 'var(--secondary-color)', fontSize: '0.9rem' }}>
          Authenticated Customer
        </div>
      </header>

      {/* Global Alerts */}
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Pending Transfers Resume Widget (User Story 4) */}
      {pendingTransfersList.length > 0 && (
        <div className="pending-transfers-widget">
          <h3 className="section-title" style={{ fontSize: '1.1rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            ⚠️ Pending Sensitive Transfers
          </h3>
          <div style={{ fontSize: '0.9rem', color: 'var(--secondary-color)', marginBottom: '0.75rem' }}>
            The following transfers require Multi-Factor Authentication (MFA) to finalize.
          </div>
          {pendingTransfersList.map((tx) => (
            <div key={tx.id} className="pending-transfer-item">
              <div>
                <strong>{tx.source_account} to {tx.destination_account}</strong>
                <div style={{ fontSize: '0.85rem', color: 'var(--secondary-color)' }}>
                  Amount: {formatCurrency(tx.amount)}
                </div>
              </div>
              <button
                className="btn-resume"
                onClick={() => handleResumeTransfer(tx)}
              >
                Resume
              </button>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading bank data...</div>
      ) : (
        <div className="dashboard-grid">
          {/* Main Content Area */}
          <div>
            {/* Account Overview Section (User Story 1) */}
            <section className="accounts-section">
              <h2 className="section-title">Account Overview</h2>
              <div className="accounts-container">
                {accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className={`account-card ${selectedAccountId === acc.id ? 'selected' : ''}`}
                    onClick={() => setSelectedAccountId(acc.id)}
                  >
                    <div className="account-type">{acc.name}</div>
                    <div className="account-balance">{formatCurrency(acc.balance)}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* Dynamic Limits Section (User Story 1, T014) */}
            {limits && (
              <section className="limits-section">
                <div className="limits-card">
                  <div className="limits-header">
                    <h2 className="section-title" style={{ marginBottom: 0 }}>Transfer Limits</h2>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ width: 'auto' }}
                      onClick={() => {
                        setShowLimitsEdit(!showLimitsEdit);
                        setLimitsError(null);
                        setLimitsSuccess(null);
                      }}
                    >
                      {showLimitsEdit ? 'Cancel Edit' : 'Edit Limits'}
                    </button>
                  </div>

                  {limitsSuccess && <div className="alert alert-success">{limitsSuccess}</div>}
                  {limitsError && <div className="alert alert-danger">{limitsError}</div>}

                  <div className="limits-stats-grid">
                    <div className="limit-stat-item">
                      <div className="limit-stat-label">Per-Transfer Limit</div>
                      <div className="limit-stat-value">{formatCurrency(limits.per_transfer_limit)}</div>
                    </div>
                    <div className="limit-stat-item">
                      <div className="limit-stat-label">Daily Limit</div>
                      <div className="limit-stat-value">{formatCurrency(limits.daily_limit)}</div>
                    </div>
                    <div className="limit-stat-item">
                      <div className="limit-stat-label">Today's Consumption (UTC)</div>
                      <div className="limit-stat-value consumed">{formatCurrency(limits.current_daily_consumption)}</div>
                    </div>
                    <div className="limit-stat-item">
                      <div className="limit-stat-label">Remaining Daily Availability</div>
                      <div className="limit-stat-value available">{formatCurrency(limits.remaining_daily_availability)}</div>
                    </div>
                  </div>

                  {showLimitsEdit && (
                    <form className="limits-form" onSubmit={handleLimitsSubmit}>
                      <div className="limits-form-grid">
                        <div className="form-group">
                          <label htmlFor="per-transfer-limit-input" className="form-label">
                            Per-Transfer Limit (COP)
                          </label>
                          <input
                            id="per-transfer-limit-input"
                            type="number"
                            step="0.01"
                            className="form-input"
                            value={perTransferInput}
                            onChange={(e) => {
                              setPerTransferInput(e.target.value);
                              setLimitsError(null);
                            }}
                            disabled={limitsSubmitting}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label htmlFor="daily-limit-input" className="form-label">
                            Daily Limit (COP)
                          </label>
                          <input
                            id="daily-limit-input"
                            type="number"
                            step="0.01"
                            className="form-input"
                            value={dailyLimitInput}
                            onChange={(e) => {
                              setDailyLimitInput(e.target.value);
                              setLimitsError(null);
                            }}
                            disabled={limitsSubmitting}
                            required
                          />
                        </div>
                      </div>
                      <button
                        type="submit"
                        className="btn btn-primary btn-sm"
                        style={{ width: 'auto' }}
                        disabled={limitsSubmitting}
                      >
                        {limitsSubmitting ? 'Saving...' : 'Save Limits'}
                      </button>
                    </form>
                  )}
                </div>
              </section>
            )}

            {/* Transaction History Section (User Story 3) */}
            <section className="history-section">
              <h2 className="section-title">Transaction History: {selectedAccountName}</h2>
              {history.length === 0 ? (
                <div style={{ color: 'var(--secondary-color)', fontStyle: 'italic' }}>
                  No completed transactions recorded for this account.
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Direction</th>
                        <th>Amount</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((tx) => (
                        <tr key={tx.id}>
                          <td>{formatDate(tx.date)}</td>
                          <td className={tx.direction === 'incoming' ? 'direction-incoming' : 'direction-outgoing'}>
                            {tx.direction === 'incoming' ? 'Incoming' : 'Outgoing'}
                          </td>
                          <td>{formatCurrency(tx.amount)}</td>
                          <td>{tx.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Saved Beneficiaries Section (User Story 2, T025) */}
            <section className="beneficiaries-section">
              <div className="beneficiaries-card">
                <div className="limits-header">
                  <h2 className="section-title" style={{ marginBottom: 0 }}>Saved ACH Beneficiaries</h2>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ width: 'auto' }}
                    onClick={() => {
                      setShowAddBeneficiary(!showAddBeneficiary);
                      setBenError(null);
                      setNewBenRoutingError(null);
                    }}
                  >
                    {showAddBeneficiary ? 'Cancel' : 'Add Beneficiary'}
                  </button>
                </div>

                {benError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{benError}</div>}

                {showAddBeneficiary && (
                  <form className="limits-form" onSubmit={handleCreateBeneficiary} style={{ marginBottom: '1.5rem' }}>
                    <div className="limits-form-grid">
                      <div className="form-group">
                        <label htmlFor="ben-name-input" className="form-label">Recipient Name</label>
                        <input
                          id="ben-name-input"
                          type="text"
                          className="form-input"
                          placeholder="e.g. Empresa de Energia"
                          value={newBenName}
                          onChange={(e) => setNewBenName(e.target.value)}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label htmlFor="ben-bank-input" className="form-label">Bank Name</label>
                        <input
                          id="ben-bank-input"
                          type="text"
                          className="form-input"
                          placeholder="e.g. Banco Davivienda"
                          value={newBenBank}
                          onChange={(e) => setNewBenBank(e.target.value)}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label htmlFor="ben-routing-input" className="form-label">Routing Number (9 digits)</label>
                        <input
                          id="ben-routing-input"
                          type="text"
                          maxLength={9}
                          className={`form-input ${newBenRoutingError ? 'input-error' : ''}`}
                          placeholder="123456789"
                          value={newBenRouting}
                          onChange={(e) => {
                            setNewBenRouting(e.target.value);
                            const val = e.target.value.trim();
                            if (val && (val.length !== 9 || !/^\d+$/.test(val))) {
                              setNewBenRoutingError("Routing number must be exactly 9 numeric digits.");
                            } else {
                              setNewBenRoutingError(null);
                            }
                          }}
                          required
                        />
                        {newBenRoutingError && <span className="inline-error">{newBenRoutingError}</span>}
                      </div>
                      <div className="form-group">
                        <label htmlFor="ben-account-input" className="form-label">Account Number (4–17 digits)</label>
                        <input
                          id="ben-account-input"
                          type="text"
                          maxLength={17}
                          className="form-input"
                          placeholder="9876543210"
                          value={newBenAccount}
                          onChange={(e) => setNewBenAccount(e.target.value)}
                          required
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      style={{ width: 'auto' }}
                      disabled={benSubmitting || !!newBenRoutingError}
                    >
                      {benSubmitting ? 'Saving...' : 'Save Beneficiary'}
                    </button>
                  </form>
                )}

                {beneficiaries.length === 0 ? (
                  <div style={{ color: 'var(--secondary-color)', fontStyle: 'italic', marginTop: '0.5rem' }}>
                    No saved ACH beneficiaries found.
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="beneficiaries-table">
                      <thead>
                        <tr>
                          <th>Recipient</th>
                          <th>Bank</th>
                          <th>Routing</th>
                          <th>Account</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {beneficiaries.map((b) => (
                          <tr key={b.id}>
                            <td><strong>{b.name}</strong></td>
                            <td>{b.bank_name}</td>
                            <td>{b.routing_number}</td>
                            <td>{b.account_number}</td>
                            <td>
                              <button
                                type="button"
                                className="btn-delete"
                                onClick={() => handleDeleteBeneficiary(b.id)}
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>

            {/* Scheduled Recurring Payments Section (User Story 3, T036) */}
            <section className="schedules-section">
              <div className="schedules-card">
                <div className="limits-header">
                  <h2 className="section-title" style={{ marginBottom: 0 }}>Scheduled Recurring Payments</h2>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ width: 'auto' }}
                    onClick={() => {
                      setShowAddSchedule(!showAddSchedule);
                      setSchedFormError(null);
                      setSchedRoutingError(null);
                    }}
                  >
                    {showAddSchedule ? 'Cancel' : 'Schedule Payment'}
                  </button>
                </div>

                {schedFormError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{schedFormError}</div>}

                {showAddSchedule && (
                  <form className="limits-form" onSubmit={handleCreateSchedule} style={{ marginBottom: '1.5rem' }}>
                    <div className="limits-form-grid">
                      <div className="form-group">
                        <label htmlFor="sched-type-select" className="form-label">Transfer Type</label>
                        <select
                          id="sched-type-select"
                          className="form-select"
                          value={schedType}
                          onChange={(e) => setSchedType(e.target.value as 'INTERNAL' | 'ACH')}
                        >
                          <option value="INTERNAL">Internal Transfer</option>
                          <option value="ACH">ACH Transfer</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label htmlFor="sched-source-select" className="form-label">Source Account</label>
                        <select
                          id="sched-source-select"
                          className="form-select"
                          value={schedSourceAccountId || (accounts[0] ? accounts[0].id : '')}
                          onChange={(e) => setSchedSourceAccountId(e.target.value)}
                        >
                          {accounts.map(a => (
                            <option key={a.id} value={a.id}>{a.name} ({formatCurrency(a.balance)})</option>
                          ))}
                        </select>
                      </div>

                      {schedType === 'INTERNAL' ? (
                        <div className="form-group">
                          <label htmlFor="sched-dest-select" className="form-label">Destination Account</label>
                          <select
                            id="sched-dest-select"
                            className="form-select"
                            value={schedDestAccountId || (accounts[1] ? accounts[1].id : '')}
                            onChange={(e) => setSchedDestAccountId(e.target.value)}
                          >
                            {accounts.map(a => (
                              <option key={a.id} value={a.id}>{a.name}</option>
                            ))}
                          </select>
                        </div>
                      ) : (
                        <>
                          <div className="form-group">
                            <label htmlFor="sched-beneficiary-select" className="form-label">Recipient</label>
                            <select
                              id="sched-beneficiary-select"
                              className="form-select"
                              value={schedBeneficiaryId}
                              onChange={(e) => {
                                const val = e.target.value;
                                setSchedBeneficiaryId(val);
                                if (val !== 'new') {
                                  const b = beneficiaries.find(x => x.id === val);
                                  if (b) {
                                    setSchedRecipientName(b.name);
                                    setSchedBankName(b.bank_name);
                                    setSchedRouting(b.routing_number);
                                    setSchedAccount(b.account_number);
                                  }
                                } else {
                                  setSchedRecipientName('');
                                  setSchedBankName('');
                                  setSchedRouting('');
                                  setSchedAccount('');
                                }
                              }}
                            >
                              <option value="new">-- New Ad Hoc Recipient --</option>
                              {beneficiaries.map(b => (
                                <option key={b.id} value={b.id}>{b.name} ({b.bank_name})</option>
                              ))}
                            </select>
                          </div>

                          <div className="form-group">
                            <label htmlFor="sched-recipient-input" className="form-label">Recipient Name</label>
                            <input
                              id="sched-recipient-input"
                              type="text"
                              className="form-input"
                              placeholder="Recipient name"
                              value={schedRecipientName}
                              onChange={(e) => setSchedRecipientName(e.target.value)}
                              disabled={schedBeneficiaryId !== 'new'}
                              required
                            />
                          </div>

                          <div className="form-group">
                            <label htmlFor="sched-bank-input" className="form-label">Bank Name</label>
                            <input
                              id="sched-bank-input"
                              type="text"
                              className="form-input"
                              placeholder="Bank name"
                              value={schedBankName}
                              onChange={(e) => setSchedBankName(e.target.value)}
                              disabled={schedBeneficiaryId !== 'new'}
                              required
                            />
                          </div>

                          <div className="form-group">
                            <label htmlFor="sched-routing-input" className="form-label">Routing Number (9 digits)</label>
                            <input
                              id="sched-routing-input"
                              type="text"
                              maxLength={9}
                              className={`form-input ${schedRoutingError ? 'input-error' : ''}`}
                              placeholder="123456789"
                              value={schedRouting}
                              onChange={(e) => {
                                setSchedRouting(e.target.value);
                                const val = e.target.value.trim();
                                if (val && (val.length !== 9 || !/^\d+$/.test(val))) {
                                  setSchedRoutingError("Routing number must be exactly 9 numeric digits.");
                                } else {
                                  setSchedRoutingError(null);
                                }
                              }}
                              disabled={schedBeneficiaryId !== 'new'}
                              required
                            />
                            {schedRoutingError && <span className="inline-error">{schedRoutingError}</span>}
                          </div>

                          <div className="form-group">
                            <label htmlFor="sched-account-input" className="form-label">Account Number (4–17 digits)</label>
                            <input
                              id="sched-account-input"
                              type="text"
                              maxLength={17}
                              className="form-input"
                              placeholder="Account number"
                              value={schedAccount}
                              onChange={(e) => setSchedAccount(e.target.value)}
                              disabled={schedBeneficiaryId !== 'new'}
                              required
                            />
                          </div>
                        </>
                      )}

                      <div className="form-group">
                        <label htmlFor="sched-amount-input" className="form-label">Amount (COP)</label>
                        <input
                          id="sched-amount-input"
                          type="number"
                          step="0.01"
                          className="form-input"
                          placeholder="e.g. 150000.00"
                          value={schedAmount}
                          onChange={(e) => {
                            setSchedAmount(e.target.value);
                            setSchedFormError(null);
                          }}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label htmlFor="sched-frequency-select" className="form-label">Frequency</label>
                        <select
                          id="sched-frequency-select"
                          className="form-select"
                          value={schedFrequency}
                          onChange={(e) => setSchedFrequency(e.target.value as RecurringFrequency)}
                        >
                          <option value="DAILY">Daily (every 24 hours)</option>
                          <option value="WEEKLY">Weekly (every 7 days)</option>
                          <option value="MONTHLY">Monthly (strictly every 30 days)</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label htmlFor="sched-start-date-input" className="form-label">Start Date (Optional YYYY-MM-DD)</label>
                        <input
                          id="sched-start-date-input"
                          type="date"
                          className="form-input"
                          value={schedStartDate}
                          onChange={(e) => setSchedStartDate(e.target.value)}
                        />
                        <span style={{ fontSize: '0.75rem', color: 'var(--secondary-color)' }}>
                          Leave blank to execute after 1 interval. Future dates start at 00:00:00 UTC.
                        </span>
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      style={{ width: 'auto' }}
                      disabled={schedSubmitting || !!schedRoutingError}
                    >
                      {schedSubmitting ? 'Scheduling...' : 'Create Schedule'}
                    </button>
                  </form>
                )}

                {schedules.length === 0 ? (
                  <div style={{ color: 'var(--secondary-color)', fontStyle: 'italic', marginTop: '0.5rem' }}>
                    No recurring payment schedules found.
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="schedules-table">
                      <thead>
                        <tr>
                          <th>Type</th>
                          <th>Recipient / Destination</th>
                          <th>Amount</th>
                          <th>Frequency</th>
                          <th>Status</th>
                          <th>Next Due Date (UTC)</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {schedules.map((s) => (
                          <tr key={s.id}>
                            <td><strong>{s.transfer_type}</strong></td>
                            <td>{s.destination_display}</td>
                            <td>{formatCurrency(s.amount)}</td>
                            <td>{s.frequency}</td>
                            <td>
                              <span className={`badge-status badge-${s.status.toLowerCase().replace('_', '-')}`}>
                                {s.status}
                              </span>
                            </td>
                            <td>{formatDate(s.next_due_date)}</td>
                            <td>
                              <div className="action-btn-group">
                                {s.status === 'ACTIVE' && (
                                  <>
                                    <button
                                      type="button"
                                      className="btn-action btn-pause"
                                      onClick={() => handlePauseSchedule(s.id)}
                                    >
                                      Pause
                                    </button>
                                    <button
                                      type="button"
                                      className="btn-action btn-cancel-action"
                                      onClick={() => handleCancelSchedule(s.id)}
                                    >
                                      Cancel
                                    </button>
                                  </>
                                )}
                                {s.status === 'PAUSED' && (
                                  <>
                                    <button
                                      type="button"
                                      className="btn-action btn-resume-action"
                                      onClick={() => handleResumeSchedule(s.id)}
                                    >
                                      Resume
                                    </button>
                                    <button
                                      type="button"
                                      className="btn-action btn-cancel-action"
                                      onClick={() => handleCancelSchedule(s.id)}
                                    >
                                      Cancel
                                    </button>
                                  </>
                                )}
                                {s.status === 'PENDING_MFA' && (
                                  <>
                                    <button
                                      type="button"
                                      className="btn-action btn-confirm-mfa"
                                      onClick={() => handleResumeScheduleMfa(s)}
                                    >
                                      Confirm MFA
                                    </button>
                                    <button
                                      type="button"
                                      className="btn-action btn-cancel-action"
                                      onClick={() => handleCancelSchedule(s.id)}
                                    >
                                      Cancel
                                    </button>
                                  </>
                                )}
                                {(s.status === 'CANCELLED' || s.status === 'EXPIRED') && (
                                  <span style={{ color: 'var(--secondary-color)', fontSize: '0.8rem' }}>Terminal</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* Right Sidebar Area (Transfer Funds Form with Tab Switcher) */}
          <div>
            <div className="form-card">
              <h2 className="section-title">Transfer Funds</h2>
              <div className="tab-switcher">
                <button
                  type="button"
                  className={`tab-btn ${transferTab === 'internal' ? 'active' : ''}`}
                  onClick={() => setTransferTab('internal')}
                >
                  Own Accounts
                </button>
                <button
                  type="button"
                  className={`tab-btn ${transferTab === 'ach' ? 'active' : ''}`}
                  onClick={() => setTransferTab('ach')}
                >
                  ACH / Third-Party
                </button>
              </div>

              {transferTab === 'internal' ? (
                <>
                  {formError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{formError}</div>}

                  <form onSubmit={handleTransferSubmit}>
                    <div className="form-group">
                      <label htmlFor="source-select" className="form-label">Source Account</label>
                      <select
                        id="source-select"
                        className="form-select"
                        value={sourceAccountId}
                        onChange={(e) => {
                          setSourceAccountId(e.target.value);
                          setFormError(null);
                        }}
                      >
                        {accounts.map(a => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="dest-select" className="form-label">Destination Account</label>
                      <select
                        id="dest-select"
                        className="form-select"
                        value={destinationAccountId}
                        onChange={(e) => {
                          setDestinationAccountId(e.target.value);
                          setFormError(null);
                        }}
                      >
                        {accounts.map(a => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="amount-input" className="form-label">Amount (COP)</label>
                      <input
                        id="amount-input"
                        type="number"
                        step="0.01"
                        className="form-input"
                        placeholder="Enter amount"
                        value={transferAmount}
                        onChange={(e) => {
                          setTransferAmount(e.target.value);
                          setFormError(null);
                        }}
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={formSubmitting}
                    >
                      {formSubmitting ? 'Transferring...' : 'Transfer'}
                    </button>
                  </form>
                </>
              ) : (
                <>
                  <h3 className="section-title" style={{ fontSize: '1.2rem' }}>Third-Party ACH Transfer</h3>
                  {achFormError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{achFormError}</div>}

                  <form onSubmit={handleAchSubmit}>
                    <div className="form-group">
                      <label htmlFor="ach-source-select" className="form-label">Source Account</label>
                      <select
                        id="ach-source-select"
                        className="form-select"
                        value={achSourceAccountId}
                        onChange={(e) => {
                          setAchSourceAccountId(e.target.value);
                          setAchFormError(null);
                        }}
                      >
                        {accounts.map(a => (
                          <option key={a.id} value={a.id}>{a.name} ({formatCurrency(a.balance)})</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="beneficiary-select" className="form-label">Recipient</label>
                      <select
                        id="beneficiary-select"
                        className="form-select"
                        value={selectedBeneficiaryId}
                        onChange={(e) => handleBeneficiarySelect(e.target.value)}
                      >
                        <option value="new">-- New Ad Hoc Recipient --</option>
                        {beneficiaries.map(b => (
                          <option key={b.id} value={b.id}>{b.name} ({b.bank_name})</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="ach-recipient-input" className="form-label">Recipient Name</label>
                      <input
                        id="ach-recipient-input"
                        type="text"
                        className="form-input"
                        placeholder="Recipient full name"
                        value={achRecipientName}
                        onChange={(e) => setAchRecipientName(e.target.value)}
                        disabled={selectedBeneficiaryId !== 'new'}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="ach-bank-input" className="form-label">Bank Name</label>
                      <input
                        id="ach-bank-input"
                        type="text"
                        className="form-input"
                        placeholder="Recipient bank name"
                        value={achBankName}
                        onChange={(e) => setAchBankName(e.target.value)}
                        disabled={selectedBeneficiaryId !== 'new'}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="ach-routing-input" className="form-label">Routing Number (9 digits)</label>
                      <input
                        id="ach-routing-input"
                        type="text"
                        maxLength={9}
                        className={`form-input ${achRoutingError ? 'input-error' : ''}`}
                        placeholder="123456789"
                        value={achRoutingNumber}
                        onChange={(e) => handleAchRoutingChange(e.target.value)}
                        disabled={selectedBeneficiaryId !== 'new'}
                        required
                      />
                      {achRoutingError && <span className="inline-error">{achRoutingError}</span>}
                    </div>

                    <div className="form-group">
                      <label htmlFor="ach-account-input" className="form-label">Account Number (4–17 digits)</label>
                      <input
                        id="ach-account-input"
                        type="text"
                        maxLength={17}
                        className={`form-input ${achAccountError ? 'input-error' : ''}`}
                        placeholder="Account number"
                        value={achAccountNumber}
                        onChange={(e) => handleAchAccountChange(e.target.value)}
                        disabled={selectedBeneficiaryId !== 'new'}
                        required
                      />
                      {achAccountError && <span className="inline-error">{achAccountError}</span>}
                    </div>

                    {selectedBeneficiaryId === 'new' && (
                      <div className="form-group">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={achSaveBeneficiary}
                            onChange={(e) => setAchSaveBeneficiary(e.target.checked)}
                          />
                          Save as beneficiary for future transfers
                        </label>
                      </div>
                    )}

                    <div className="form-group">
                      <label htmlFor="ach-amount-input" className="form-label">Amount (COP)</label>
                      <input
                        id="ach-amount-input"
                        type="number"
                        step="0.01"
                        className="form-input"
                        placeholder="Enter amount"
                        value={achAmount}
                        onChange={(e) => {
                          setAchAmount(e.target.value);
                          setAchFormError(null);
                        }}
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={achSubmitting || !!achRoutingError || !!achAccountError}
                    >
                      {achSubmitting ? 'Sending...' : 'Send ACH Transfer'}
                    </button>
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* step-up MFA Modal Overlay Component (User Story 4 & User Story 3) */}
      {showMfaModal && (pendingTransfer || pendingMfaSchedule) && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">MFA Verification</h3>
              <button
                className="modal-close"
                aria-label="Close"
                onClick={handleMfaModalClose}
              >
                &times;
              </button>
            </div>
            
            <form onSubmit={handleMfaConfirmSubmit}>
              <div className="modal-body">
                {mfaError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem', marginBottom: '1rem' }}>{mfaError}</div>}
                
                <div className="mfa-info">
                  {pendingMfaSchedule ? (
                    <>
                      A sensitive recurring schedule of <strong>{formatCurrency(pendingMfaSchedule.amount)}</strong> to <strong>{pendingMfaSchedule.destination_display}</strong> ({pendingMfaSchedule.frequency}) was requested.
                    </>
                  ) : pendingTransfer ? (
                    <>
                      A high-value transfer of <strong>{formatCurrency(pendingTransfer.amount)}</strong> from <strong>{pendingTransfer.source_account}</strong> to <strong>{pendingTransfer.destination_account}</strong> was requested.
                    </>
                  ) : null}
                </div>
                <div className="mfa-info">
                  Enter the 6-digit code to finalize. Time remaining: <span className="mfa-timer">{formatTimer(timeLeft)}</span>.
                </div>

                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label htmlFor="mfa-code-input" className="form-label">MFA Code</label>
                  <input
                    id="mfa-code-input"
                    type="text"
                    maxLength={6}
                    pattern="\d{6}"
                    className="form-input"
                    style={{ textAlign: 'center', fontSize: '1.2rem', letterSpacing: '4px' }}
                    placeholder="000000"
                    value={mfaCode}
                    onChange={(e) => {
                      setMfaCode(e.target.value);
                      setMfaError(null);
                    }}
                    disabled={mfaSubmitting}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleMfaModalClose}
                  disabled={mfaSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={mfaSubmitting}
                >
                  {mfaSubmitting ? 'Confirming...' : 'Confirm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
