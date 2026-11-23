import React, { useState, useMemo } from 'react';
import {
  RecurringSchedule,
  RecurringScheduleCreateRequest,
  Account,
  Beneficiary,
  TransferLimits,
} from '../api/types';
import {
  isValidMonetaryString,
  parseToCents,
  centsToDecimalString,
  isUsdEquivalentExceedingThreshold,
  formatCurrency,
  SupportedCurrency,
} from '../utils/monetary';

interface RecurringPaymentsProps {
  isOpen: boolean;
  schedules: RecurringSchedule[];
  accounts: Account[];
  beneficiaries: Beneficiary[];
  onClose: () => void;
  onCreateSchedule: (data: RecurringScheduleCreateRequest) => Promise<void>;
  onPauseSchedule: (id: number) => Promise<void>;
  onResumeSchedule: (id: number) => Promise<void>;
  onCancelSchedule: (id: number) => Promise<void>;
  isSubmitting?: boolean;
  errorMessage?: string | null;
  limits?: TransferLimits | null;
}

export const RecurringPayments: React.FC<RecurringPaymentsProps> = ({
  isOpen,
  schedules,
  accounts,
  beneficiaries,
  onClose,
  onCreateSchedule,
  onPauseSchedule,
  onResumeSchedule,
  onCancelSchedule,
  isSubmitting = false,
  errorMessage = null,
  limits = null,
}) => {
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [transferType, setTransferType] = useState<'internal' | 'ach'>('internal');
  const [fromAccountId, setFromAccountId] = useState<number>(accounts[0]?.id || 0);
  const [toAccountId, setToAccountId] = useState<number>(accounts[1]?.id || 0);
  const [beneficiaryId, setBeneficiaryId] = useState<number | ''>('');
  const [recipientName, setRecipientName] = useState<string>('');
  const [routingNumber, setRoutingNumber] = useState<string>('');
  const [accountNumber, setAccountNumber] = useState<string>('');
  const [bankName, setBankName] = useState<string>('');
  const [amountStr, setAmountStr] = useState<string>('');
  const [pin, setPin] = useState<string>('');
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('monthly');
  const [description, setDescription] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);

  const fromAccount = useMemo(
    () => accounts.find((a) => a.id === fromAccountId) || accounts[0] || null,
    [accounts, fromAccountId]
  );

  // Filter destination accounts strictly to same currency for internal recurring transfers (D-08)
  const destinationOptions = useMemo(
    () => accounts.filter((a) => a.id !== fromAccountId && (fromAccount ? a.currency === fromAccount.currency : true)),
    [accounts, fromAccountId, fromAccount]
  );

  const toAccount = useMemo(
    () => accounts.find((a) => a.id === toAccountId) || destinationOptions[0] || null,
    [accounts, toAccountId, destinationOptions]
  );

  // MFA check on schedule setup: sensitive financial operations > $1,000 USD equivalent (D-07, D-08)
  const isSensitive = useMemo(() => {
    if (!fromAccount) return false;
    const trimmed = amountStr.trim();
    if (!isValidMonetaryString(trimmed)) return false;
    const cents = parseToCents(trimmed);
    if (cents <= 0n) return false;
    return isUsdEquivalentExceedingThreshold(
      cents,
      fromAccount.currency as SupportedCurrency,
      '1000.00'
    );
  }, [fromAccount, amountStr]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const trimmedAmount = amountStr.trim();
    if (!isValidMonetaryString(trimmedAmount)) {
      setFormError('Please enter a valid amount with at most 2 decimal places.');
      return;
    }

    const cents = parseToCents(trimmedAmount);
    if (cents <= 0n) {
      setFormError('Please enter a valid amount greater than zero.');
      return;
    }

    if (limits && fromAccount) {
      if (
        isUsdEquivalentExceedingThreshold(
          cents,
          fromAccount.currency as SupportedCurrency,
          limits.per_transaction_limit
        )
      ) {
        setFormError(
          `Amount exceeds per-transaction limit (${formatCurrency(
            limits.per_transaction_limit,
            limits.reference_currency || 'USD'
          )}).`
        );
        return;
      }
    }

    if (isSensitive && (!pin || !pin.trim())) {
      setFormError('Security PIN is required for recurring payments exceeding $1,000 USD equivalent.');
      return;
    }

    const canonicalAmount = centsToDecimalString(cents);

    if (transferType === 'internal') {
      if (!fromAccount || !toAccount) {
        setFormError('Source and destination accounts must be selected.');
        return;
      }
      if (fromAccountId === toAccountId) {
        setFormError('Source and destination accounts must be different.');
        return;
      }
      if (fromAccount.currency !== toAccount.currency) {
        setFormError('Recurring internal transfers are only permitted between accounts of the same currency.');
        return;
      }

      await onCreateSchedule({
        transfer_type: 'internal',
        from_account_id: fromAccountId,
        to_account_id: toAccountId,
        amount: canonicalAmount,
        frequency,
        description: description.trim() || undefined,
        pin: isSensitive ? pin.trim() : undefined,
      });
    } else {
      // ACH Transfer
      if (!fromAccount) {
        setFormError('Source account must be selected.');
        return;
      }
      if (fromAccount.currency !== 'USD') {
        setFormError('Recurring ACH transfers are only permitted from USD accounts.');
        return;
      }

      if (beneficiaryId) {
        await onCreateSchedule({
          transfer_type: 'ach',
          from_account_id: fromAccountId,
          beneficiary_id: Number(beneficiaryId),
          amount: canonicalAmount,
          frequency,
          description: description.trim() || undefined,
          pin: isSensitive ? pin.trim() : undefined,
        });
      } else {
        if (!recipientName.trim() || !routingNumber.trim() || !accountNumber.trim() || !bankName.trim()) {
          setFormError('All external beneficiary fields are required.');
          return;
        }
        if (routingNumber.trim().length !== 9 || !/^\d{9}$/.test(routingNumber.trim())) {
          setFormError('Routing number must be exactly 9 digits.');
          return;
        }
        await onCreateSchedule({
          transfer_type: 'ach',
          from_account_id: fromAccountId,
          recipient_name: recipientName.trim(),
          routing_number: routingNumber.trim(),
          account_number: accountNumber.trim(),
          bank_name: bankName.trim(),
          amount: canonicalAmount,
          frequency,
          description: description.trim() || undefined,
          pin: isSensitive ? pin.trim() : undefined,
        });
      }
    }

    setShowCreateForm(false);
    setAmountStr('');
    setPin('');
    setDescription('');
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="recurring-title">
      <div className="modal-card recurring-modal-card" data-testid="recurring-modal">
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">🔄</span>
            <div>
              <h2 id="recurring-title" className="modal-title">Recurring Payments</h2>
              <p className="modal-subtitle">Manage automated recurring transfers & schedules</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close recurring payments">
            ✕
          </button>
        </div>

        <div className="recurring-top-bar">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
            data-testid="open-create-schedule-btn"
          >
            {showCreateForm ? 'View All Schedules' : '+ Schedule New Payment'}
          </button>
        </div>

        {errorMessage && (
          <div className="error-message" role="alert">
            ⚠️ {errorMessage}
          </div>
        )}

        {showCreateForm ? (
          <form onSubmit={handleSubmit} className="transfer-form" data-testid="create-schedule-form" noValidate>
            <div className="form-group">
              <label className="form-label">Transfer Type</label>
              <div className="tab-group">
                <button
                  type="button"
                  className={`tab-btn ${transferType === 'internal' ? 'active' : ''}`}
                  onClick={() => setTransferType('internal')}
                  data-testid="tab-internal-schedule"
                >
                  Internal Transfer
                </button>
                <button
                  type="button"
                  className={`tab-btn ${transferType === 'ach' ? 'active' : ''}`}
                  onClick={() => setTransferType('ach')}
                  data-testid="tab-ach-schedule"
                >
                  External ACH Transfer
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="schedule-from-account" className="form-label">
                Transfer From Account
              </label>
              <select
                id="schedule-from-account"
                value={fromAccountId}
                onChange={(e) => setFromAccountId(parseInt(e.target.value, 10))}
                className="form-select"
                data-testid="schedule-from-account"
                disabled={isSubmitting}
              >
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.account_name} — {formatCurrency(acc.balance, acc.currency)} ({acc.account_number}) - v{acc.version}
                  </option>
                ))}
              </select>
            </div>

            {transferType === 'internal' ? (
              <div className="form-group">
                <label htmlFor="schedule-to-account" className="form-label">
                  Transfer To Account (Same Currency: {fromAccount?.currency})
                </label>
                <select
                  id="schedule-to-account"
                  value={toAccountId}
                  onChange={(e) => setToAccountId(parseInt(e.target.value, 10))}
                  className="form-select"
                  data-testid="schedule-to-account"
                  disabled={isSubmitting || destinationOptions.length === 0}
                >
                  {destinationOptions.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.account_name} — {formatCurrency(acc.balance, acc.currency)} ({acc.account_number}) - v{acc.version}
                    </option>
                  ))}
                </select>
                {destinationOptions.length === 0 && (
                  <p className="help-text" style={{ color: '#e53e3e', fontSize: '0.85rem' }}>
                    No other accounts in currency {fromAccount?.currency} available for internal transfers.
                  </p>
                )}
              </div>
            ) : (
              <>
                {fromAccount && fromAccount.currency !== 'USD' && (
                  <div className="error-message" style={{ marginBottom: '12px' }} data-testid="ach-currency-warning">
                    ⚠️ Recurring ACH transfers are only permitted from USD accounts. Selected source account is {fromAccount.currency}.
                  </div>
                )}
                <div className="form-group">
                  <label htmlFor="schedule-beneficiary-select" className="form-label">
                    Saved Beneficiary (Optional)
                  </label>
                  <select
                    id="schedule-beneficiary-select"
                    value={beneficiaryId}
                    onChange={(e) => setBeneficiaryId(e.target.value ? parseInt(e.target.value, 10) : '')}
                    className="form-select"
                    disabled={isSubmitting}
                  >
                    <option value="">-- Enter ad-hoc beneficiary details below --</option>
                    {beneficiaries.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} ({b.bank_name} - ••••{b.account_number.slice(-4)})
                      </option>
                    ))}
                  </select>
                </div>

                {!beneficiaryId && (
                  <div className="ad-hoc-fields">
                    <div className="form-group">
                      <label className="form-label">Recipient Name</label>
                      <input
                        type="text"
                        value={recipientName}
                        onChange={(e) => setRecipientName(e.target.value)}
                        className="form-input"
                        placeholder="Full Name / Company"
                        disabled={isSubmitting}
                        required={!beneficiaryId}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">9-Digit Routing Number</label>
                      <input
                        type="text"
                        maxLength={9}
                        value={routingNumber}
                        onChange={(e) => setRoutingNumber(e.target.value)}
                        className="form-input"
                        placeholder="123456789"
                        disabled={isSubmitting}
                        required={!beneficiaryId}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Account Number</label>
                      <input
                        type="text"
                        value={accountNumber}
                        onChange={(e) => setAccountNumber(e.target.value)}
                        className="form-input"
                        placeholder="Account Number"
                        disabled={isSubmitting}
                        required={!beneficiaryId}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Bank Name</label>
                      <input
                        type="text"
                        value={bankName}
                        onChange={(e) => setBankName(e.target.value)}
                        className="form-input"
                        placeholder="Bank Name"
                        disabled={isSubmitting}
                        required={!beneficiaryId}
                      />
                    </div>
                  </div>
                )}
              </>
            )}

            <div className="form-group">
              <label htmlFor="schedule-amount-input" className="form-label">
                Amount ({fromAccount?.currency || 'USD'})
              </label>
              <div className="input-with-prefix">
                <span className="input-prefix">
                  {fromAccount?.currency === 'EUR' ? '€' : fromAccount?.currency === 'GBP' ? '£' : '$'}
                </span>
                <input
                  id="schedule-amount-input"
                  type="text"
                  inputMode="decimal"
                  value={amountStr}
                  onChange={(e) => setAmountStr(e.target.value)}
                  placeholder="0.00"
                  className="form-input amount-input"
                  data-testid="schedule-amount-input"
                  disabled={isSubmitting}
                  required
                />
              </div>

              {isSensitive && (
                <div className="mfa-notice" data-testid="mfa-sensitive-notice">
                  ℹ️ Recurring payments over $1,000.00 USD equivalent require mock Security PIN authorization when creating schedule.
                </div>
              )}
            </div>

            {isSensitive && (
              <div className="form-group mfa-box" style={{ background: '#fffbeb', border: '1px solid #fef3c7', padding: '1rem', borderRadius: '6px' }}>
                <label htmlFor="schedule-pin-input" className="form-label">
                  🔒 Security PIN Required (USD equivalent &gt; $1,000):
                </label>
                <input
                  id="schedule-pin-input"
                  type="password"
                  maxLength={10}
                  placeholder="Enter 4-digit PIN (default: 1234)"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  data-testid="schedule-pin-input"
                  className="form-input"
                  disabled={isSubmitting}
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="schedule-frequency-select" className="form-label">
                Recurrence Frequency
              </label>
              <select
                id="schedule-frequency-select"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as any)}
                className="form-select"
                data-testid="schedule-frequency-select"
                disabled={isSubmitting}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="schedule-desc-input" className="form-label">
                Description / Memo (Optional)
              </label>
              <input
                id="schedule-desc-input"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Utility bill, Rent, Savings"
                className="form-input"
                disabled={isSubmitting}
              />
            </div>

            {formError && (
              <div className="error-message" role="alert" data-testid="schedule-error-message">
                ⚠️ {formError}
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCreateForm(false)}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={
                  isSubmitting ||
                  !amountStr.trim() ||
                  (transferType === 'internal' && destinationOptions.length === 0) ||
                  (transferType === 'ach' && fromAccount?.currency !== 'USD')
                }
                data-testid="submit-schedule-btn"
              >
                {isSubmitting ? 'Creating...' : isSensitive ? 'Authorize & Create Schedule' : 'Create Recurring Schedule'}
              </button>
            </div>
          </form>
        ) : (
          <div className="schedules-list" data-testid="schedules-list">
            {schedules.length === 0 ? (
              <div className="empty-state">
                <p>No recurring payments configured.</p>
                <p className="empty-state-sub">Click "+ Schedule New Payment" to set up recurring transfers.</p>
              </div>
            ) : (
              <div className="schedule-cards">
                {schedules.map((sched) => {
                  const fromAcc = accounts.find((a) => a.id === sched.from_account_id);
                  const toAcc = accounts.find((a) => a.id === sched.to_account_id);
                  const targetLabel = sched.transfer_type === 'internal'
                    ? toAcc?.account_name || `Account #${sched.to_account_id}`
                    : sched.recipient_name || `ACH Payee`;

                  return (
                    <div
                      key={sched.id}
                      className="schedule-card"
                      data-testid={`schedule-item-${sched.id}`}
                    >
                      <div className="schedule-header">
                        <div className="schedule-main">
                          <span className={`status-badge status-${sched.status}`}>
                            {sched.status.toUpperCase()}
                          </span>
                          <span className="schedule-title">
                            {formatCurrency(sched.amount, sched.currency || fromAcc?.currency || 'USD')} / {sched.frequency}
                          </span>
                        </div>
                        <div className="schedule-actions">
                          {sched.status === 'active' && (
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() => onPauseSchedule(sched.id)}
                              disabled={isSubmitting}
                              data-testid={`pause-schedule-btn-${sched.id}`}
                              title="Pause Schedule"
                            >
                              Pause
                            </button>
                          )}
                          {sched.status === 'paused' && (
                            <button
                              className="btn btn-sm btn-primary"
                              onClick={() => onResumeSchedule(sched.id)}
                              disabled={isSubmitting}
                              data-testid={`resume-schedule-btn-${sched.id}`}
                              title="Resume Schedule"
                            >
                              Resume
                            </button>
                          )}
                          {sched.status !== 'cancelled' && (
                            <button
                              className="btn btn-sm btn-danger"
                              onClick={() => onCancelSchedule(sched.id)}
                              disabled={isSubmitting}
                              data-testid={`cancel-schedule-btn-${sched.id}`}
                              title="Cancel Schedule"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="schedule-details">
                        <div className="schedule-detail-item">
                          <span className="detail-label">From:</span>
                          <span className="detail-val">{fromAcc?.account_name || `Acc #${sched.from_account_id}`}</span>
                        </div>
                        <div className="schedule-detail-item">
                          <span className="detail-label">To:</span>
                          <span className="detail-val">{targetLabel}</span>
                        </div>
                        <div className="schedule-detail-item">
                          <span className="detail-label">Next Execution:</span>
                          <span className="detail-val">
                            {new Date(sched.next_execution_date).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
