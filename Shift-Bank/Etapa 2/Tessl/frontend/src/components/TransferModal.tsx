import React, { useState, useEffect } from 'react';
import { Account, TransferRequest } from '../api/types';

interface TransferModalProps {
  isOpen: boolean;
  accounts: Account[];
  isSubmitting?: boolean;
  errorMessage?: string | null;
  onClose: () => void;
  onSubmit: (transferData: TransferRequest) => void;
}

export const TransferModal: React.FC<TransferModalProps> = ({
  isOpen,
  accounts,
  isSubmitting = false,
  errorMessage = null,
  onClose,
  onSubmit,
}) => {
  const [fromAccountId, setFromAccountId] = useState<number>(accounts[0]?.id || 0);
  const [toAccountId, setToAccountId] = useState<number>(accounts[1]?.id || 0);
  const [amountStr, setAmountStr] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

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

  const handleAmountChange = (val: string) => {
    setAmountStr(val);
    const parsed = parseFloat(val);
    if (!isNaN(parsed) && sourceAccount && parsed > sourceAccount.balance) {
      setValidationError(`Amount exceeds available balance ($${sourceAccount.balance.toFixed(2)})`);
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
              <p className="modal-subtitle">Transfer money between your Shift Bank accounts</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close transfer modal">
            ✕
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
                !!validationError
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
