import React, { useState, useEffect } from 'react';
import { Account, TransferRequest, Beneficiary, AchTransferRequest, TransferLimits } from '../api/types';

interface TransferModalProps {
  isOpen: boolean;
  accounts: Account[];
  isSubmitting?: boolean;
  errorMessage?: string | null;
  onClose: () => void;
  onSubmit: (transferData: TransferRequest) => void;
  beneficiaries?: Beneficiary[];
  limits?: TransferLimits | null;
  onSubmitAch?: (achData: AchTransferRequest) => void;
}

export const TransferModal: React.FC<TransferModalProps> = ({
  isOpen,
  accounts,
  isSubmitting = false,
  errorMessage = null,
  onClose,
  onSubmit,
  beneficiaries = [],
  limits = null,
  onSubmitAch,
}) => {
  const [transferType, setTransferType] = useState<'internal' | 'ach'>('internal');
  const [fromAccountId, setFromAccountId] = useState<number>(accounts[0]?.id || 0);
  const [toAccountId, setToAccountId] = useState<number>(accounts[1]?.id || 0);
  const [amountStr, setAmountStr] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  // ACH ad-hoc & beneficiary state
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState<number | ''>('');
  const [recipientName, setRecipientName] = useState<string>('');
  const [routingNumber, setRoutingNumber] = useState<string>('');
  const [routingError, setRoutingError] = useState<string | null>(null);
  const [accountNumber, setAccountNumber] = useState<string>('');
  const [bankName, setBankName] = useState<string>('');
  const [saveBeneficiary, setSaveBeneficiary] = useState<boolean>(false);

  useEffect(() => {
    if (accounts.length >= 2) {
      if (!fromAccountId || !accounts.some((a) => a.id === fromAccountId)) {
        setFromAccountId(accounts[0].id);
      }
      if (!toAccountId || !accounts.some((a) => a.id === toAccountId) || toAccountId === accounts[0]?.id) {
        const other = accounts.find((a) => a.id !== accounts[0]?.id);
        if (other) setToAccountId(other.id);
      }
    }
  }, [accounts, fromAccountId, toAccountId]);

  if (!isOpen) return null;

  const sourceAccount = accounts.find((a) => a.id === fromAccountId) || null;
  const destinationOptions = accounts.filter((a) => a.id !== fromAccountId);

  const handleRoutingNumberChange = (val: string) => {
    setRoutingNumber(val);
    const trimmed = val.trim();
    if (trimmed.length > 0 && trimmed.length !== 9) {
      setRoutingError('Routing number must be exactly 9 digits.');
    } else if (trimmed.length === 9 && !/^\d{9}$/.test(trimmed)) {
      setRoutingError('Routing number must contain only digits.');
    } else {
      setRoutingError(null);
    }
  };

  const handleAmountChange = (val: string) => {
    setAmountStr(val);
    const parsed = parseFloat(val);
    if (!isNaN(parsed)) {
      if (sourceAccount && parsed > sourceAccount.balance) {
        setValidationError(`Amount exceeds available balance ($${sourceAccount.balance.toFixed(2)})`);
        return;
      }
      if (limits && parsed > limits.per_transaction_limit) {
        setValidationError(`Amount exceeds per-transaction limit ($${limits.per_transaction_limit.toFixed(2)})`);
        return;
      }
      if (limits && parsed > limits.remaining_daily_limit) {
        setValidationError(`Amount exceeds remaining daily limit ($${limits.remaining_daily_limit.toFixed(2)})`);
        return;
      }
      setValidationError(null);
    } else {
      setValidationError(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(amountStr);

    if (isNaN(amount) || amount <= 0) {
      setValidationError('Please enter a valid transfer amount greater than zero.');
      return;
    }

    if (sourceAccount && amount > sourceAccount.balance) {
      setValidationError(`Amount exceeds available balance ($${sourceAccount.balance.toFixed(2)})`);
      return;
    }

    if (limits && amount > limits.per_transaction_limit) {
      setValidationError(`Amount exceeds per-transaction limit ($${limits.per_transaction_limit.toFixed(2)})`);
      return;
    }

    if (limits && amount > limits.remaining_daily_limit) {
      setValidationError(`Amount exceeds remaining daily limit ($${limits.remaining_daily_limit.toFixed(2)})`);
      return;
    }

    if (transferType === 'internal') {
      if (fromAccountId === toAccountId) {
        setValidationError('Source and destination accounts must be different.');
        return;
      }
      onSubmit({
        from_account_id: fromAccountId,
        to_account_id: toAccountId,
        amount,
        description: description.trim() || undefined,
      });
    } else {
      if (selectedBeneficiaryId) {
        if (onSubmitAch) {
          onSubmitAch({
            from_account_id: fromAccountId,
            beneficiary_id: Number(selectedBeneficiaryId),
            amount,
            description: description.trim() || undefined,
          });
        }
      } else {
        if (!recipientName.trim() || !routingNumber.trim() || !accountNumber.trim() || !bankName.trim()) {
          setValidationError('All external beneficiary fields are required.');
          return;
        }
        if (routingNumber.trim().length !== 9 || !/^\d{9}$/.test(routingNumber.trim())) {
          setRoutingError('Routing number must be exactly 9 digits.');
          setValidationError('Routing number must be exactly 9 digits.');
          return;
        }
        if (onSubmitAch) {
          onSubmitAch({
            from_account_id: fromAccountId,
            recipient_name: recipientName.trim(),
            routing_number: routingNumber.trim(),
            account_number: accountNumber.trim(),
            bank_name: bankName.trim(),
            save_beneficiary: saveBeneficiary,
            amount,
            description: description.trim() || undefined,
          });
        }
      }
    }
  };

  const amountNumber = parseFloat(amountStr) || 0;
  const isSensitive = amountNumber > 1000.0;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="transfer-title">
      <div className="modal-card" data-testid="transfer-modal">
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">⇄</span>
            <div>
              <h2 id="transfer-title" className="modal-title">Transfer Funds</h2>
              <p className="modal-subtitle">Transfer money between accounts or to external payees</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close transfer modal">
            ✕
          </button>
        </div>

        <div className="transfer-type-tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <button
            type="button"
            className={`btn btn-sm ${transferType === 'internal' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              setTransferType('internal');
              setValidationError(null);
            }}
            data-testid="tab-internal-transfer"
          >
            Internal Account
          </button>
          <button
            type="button"
            className={`btn btn-sm ${transferType === 'ach' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              setTransferType('ach');
              setValidationError(null);
            }}
            data-testid="tab-ach-transfer"
          >
            External ACH Transfer
          </button>
        </div>

        <form onSubmit={handleSubmit} className="transfer-form">
          <div className="form-group">
            <label htmlFor="from-account-select" className="form-label">
              Transfer From
            </label>
            <select
              id="from-account-select"
              value={fromAccountId}
              onChange={(e) => {
                const newFrom = Number(e.target.value);
                setFromAccountId(newFrom);
                if (toAccountId === newFrom) {
                  const fallback = accounts.find((a) => a.id !== newFrom);
                  if (fallback) setToAccountId(fallback.id);
                }
              }}
              className="form-select"
              data-testid="from-account-select"
              disabled={isSubmitting}
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
              <label htmlFor="to-account-select" className="form-label">
                Transfer To
              </label>
              <select
                id="to-account-select"
                value={toAccountId}
                onChange={(e) => setToAccountId(Number(e.target.value))}
                className="form-select"
                data-testid="to-account-select"
                disabled={isSubmitting}
              >
                {destinationOptions.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.account_name} — ${acc.balance.toFixed(2)} ({acc.account_number})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="ach-recipient-section" data-testid="ach-recipient-section">
              <div className="form-group">
                <label htmlFor="beneficiary-select" className="form-label">
                  External Beneficiary
                </label>
                <select
                  id="beneficiary-select"
                  value={selectedBeneficiaryId}
                  onChange={(e) => setSelectedBeneficiaryId(e.target.value ? Number(e.target.value) : '')}
                  className="form-select"
                  data-testid="beneficiary-select"
                  disabled={isSubmitting}
                >
                  <option value="">-- Enter New Beneficiary Details --</option>
                  {beneficiaries.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.bank_name} - ••••{b.account_number.slice(-4)})
                    </option>
                  ))}
                </select>
              </div>

              {!selectedBeneficiaryId && (
                <div className="ad-hoc-beneficiary-group" style={{ display: 'grid', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Recipient Name</label>
                    <input
                      type="text"
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                      placeholder="Jane Doe / Company Inc"
                      className="form-input"
                      data-testid="recipient-name-input"
                      disabled={isSubmitting}
                      required={!selectedBeneficiaryId}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">9-Digit Routing Number</label>
                    <input
                      type="text"
                      maxLength={9}
                      value={routingNumber}
                      onChange={(e) => handleRoutingNumberChange(e.target.value)}
                      placeholder="123456789"
                      className="form-input"
                      data-testid="routing-number-input"
                      disabled={isSubmitting}
                      required={!selectedBeneficiaryId}
                    />
                    {routingError && (
                      <div className="field-error-text" role="alert" data-testid="routing-number-error" style={{ color: '#e53e3e', fontSize: '0.8rem', marginTop: '4px' }}>
                        ⚠️ {routingError}
                      </div>
                    )}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Account Number</label>
                    <input
                      type="text"
                      value={accountNumber}
                      onChange={(e) => setAccountNumber(e.target.value)}
                      placeholder="Account Number (4-17 digits)"
                      className="form-input"
                      data-testid="account-number-input"
                      disabled={isSubmitting}
                      required={!selectedBeneficiaryId}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Bank Name</label>
                    <input
                      type="text"
                      value={bankName}
                      onChange={(e) => setBankName(e.target.value)}
                      placeholder="e.g. Chase Bank, Wells Fargo"
                      className="form-input"
                      data-testid="bank-name-input"
                      disabled={isSubmitting}
                      required={!selectedBeneficiaryId}
                    />
                  </div>
                  <div className="form-group-checkbox" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      id="save-ben-checkbox"
                      type="checkbox"
                      checked={saveBeneficiary}
                      onChange={(e) => setSaveBeneficiary(e.target.checked)}
                      data-testid="save-beneficiary-checkbox"
                      disabled={isSubmitting}
                    />
                    <label htmlFor="save-ben-checkbox" className="form-label" style={{ margin: 0, cursor: 'pointer' }}>
                      Save beneficiary for future use
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="transfer-amount-input" className="form-label">
              Amount (USD)
            </label>
            <div className="input-with-prefix">
              <span className="input-prefix">$</span>
              <input
                id="transfer-amount-input"
                type="number"
                step="0.01"
                min="0.01"
                value={amountStr}
                onChange={(e) => handleAmountChange(e.target.value)}
                placeholder="0.00"
                className="form-input amount-input"
                data-testid="transfer-amount-input"
                disabled={isSubmitting}
                required
              />
            </div>

            {isSensitive && (
              <div className="mfa-notice" data-testid="mfa-sensitive-notice">
                ℹ️ Transfers over $1,000.00 will require mock Security PIN authorization.
              </div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="transfer-desc-input" className="form-label">
              Note / Description (Optional)
            </label>
            <input
              id="transfer-desc-input"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Monthly Savings, Rent buffer"
              className="form-input"
              data-testid="transfer-desc-input"
              disabled={isSubmitting}
            />
          </div>

          {(validationError || errorMessage) && (
            <div className="error-message" role="alert" data-testid="transfer-error-message">
              ⚠️ {validationError || errorMessage}
            </div>
          )}

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
              data-testid="transfer-cancel-btn"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={
                isSubmitting ||
                !amountStr ||
                parseFloat(amountStr) <= 0 ||
                !!validationError ||
                !!routingError
              }
              data-testid="transfer-submit-btn"
            >
              {isSubmitting ? 'Processing...' : isSensitive ? 'Continue to Verification' : 'Confirm Transfer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
