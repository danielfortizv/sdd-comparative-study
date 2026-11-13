import React, { useState } from 'react';
import {
  RecurringSchedule,
  RecurringScheduleCreateRequest,
  Account,
  Beneficiary,
} from '../api/types';

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
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('monthly');
  const [description, setDescription] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen) return null;

  const destinationOptions = accounts.filter((a) => a.id !== fromAccountId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
      setFormError('Please enter a valid amount greater than zero.');
      return;
    }

    if (transferType === 'internal') {
      if (fromAccountId === toAccountId) {
        setFormError('Source and destination accounts must be different.');
        return;
      }
      await onCreateSchedule({
        transfer_type: 'internal',
        from_account_id: fromAccountId,
        to_account_id: toAccountId,
        amount,
        frequency,
        description: description.trim() || undefined,
      });
    } else {
      if (beneficiaryId) {
        await onCreateSchedule({
          transfer_type: 'ach',
          from_account_id: fromAccountId,
          beneficiary_id: Number(beneficiaryId),
          amount,
          frequency,
          description: description.trim() || undefined,
        });
      } else {
        if (!recipientName.trim() || !routingNumber.trim() || !accountNumber.trim() || !bankName.trim()) {
          setFormError('All external beneficiary fields are required.');
          return;
        }
        if (routingNumber.trim().length !== 9) {
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
          amount,
          frequency,
          description: description.trim() || undefined,
        });
      }
    }

    setShowCreateForm(false);
    setAmountStr('');
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
          <form onSubmit={handleSubmit} className="transfer-form" data-testid="create-schedule-form">
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
                onChange={(e) => setFromAccountId(Number(e.target.value))}
                className="form-select"
                data-testid="schedule-from-account"
              >
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.account_name} — ${acc.balance.toFixed(2)} ({acc.account_number})
                  </option>
                ))}
              </select>
            </div>

            {transferType === 'internal' ? (
              <div className="form-group">
                <label htmlFor="schedule-to-account" className="form-label">
                  Transfer To Account
                </label>
                <select
                  id="schedule-to-account"
                  value={toAccountId}
                  onChange={(e) => setToAccountId(Number(e.target.value))}
                  className="form-select"
                  data-testid="schedule-to-account"
                >
                  {destinationOptions.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.account_name} — ${acc.balance.toFixed(2)} ({acc.account_number})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label htmlFor="schedule-beneficiary-select" className="form-label">
                    Saved Beneficiary (Optional)
                  </label>
                  <select
                    id="schedule-beneficiary-select"
                    value={beneficiaryId}
                    onChange={(e) => setBeneficiaryId(e.target.value ? Number(e.target.value) : '')}
                    className="form-select"
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
                        required={!beneficiaryId}
                      />
                    </div>
                  </div>
                )}
              </>
            )}

            <div className="form-group">
              <label htmlFor="schedule-amount-input" className="form-label">
                Amount (USD)
              </label>
              <div className="input-with-prefix">
                <span className="input-prefix">$</span>
                <input
                  id="schedule-amount-input"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amountStr}
                  onChange={(e) => setAmountStr(e.target.value)}
                  placeholder="0.00"
                  className="form-input amount-input"
                  data-testid="schedule-amount-input"
                  required
                />
              </div>
              {parseFloat(amountStr) > 1000 && (
                <div className="mfa-notice">
                  ℹ️ Recurring payments over $1,000.00 require mock Security PIN authorization when creating schedule.
                </div>
              )}
            </div>

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
              />
            </div>

            {formError && (
              <div className="error-message" role="alert">
                ⚠️ {formError}
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting || !amountStr || parseFloat(amountStr) <= 0}
                data-testid="submit-schedule-btn"
              >
                {isSubmitting ? 'Creating...' : 'Create Recurring Schedule'}
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
                            ${sched.amount.toFixed(2)} / {sched.frequency}
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
