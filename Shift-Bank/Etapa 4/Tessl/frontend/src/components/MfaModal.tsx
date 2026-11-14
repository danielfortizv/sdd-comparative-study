import React, { useState } from 'react';
import { Account } from '../api/types';
import { formatCurrency } from '../utils/monetary';

interface MfaModalProps {
  isOpen: boolean;
  fromAccount: Account | null;
  toAccount: Account | null;
  amount: string;
  remainingAttempts: number;
  isLocked: boolean;
  errorMessage?: string | null;
  isSubmitting?: boolean;
  onConfirm: (pin: string) => void;
  onCancel: () => void;
}

export const MfaModal: React.FC<MfaModalProps> = ({
  isOpen,
  fromAccount,
  toAccount,
  amount,
  remainingAttempts,
  isLocked,
  errorMessage,
  isSubmitting = false,
  onConfirm,
  onCancel,
}) => {
  const [pin, setPin] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pin.trim().length >= 4 && !isLocked) {
      onConfirm(pin.trim());
    }
  };

  const formattedAmount = formatCurrency(amount, fromAccount?.currency || 'USD');

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="mfa-title">
      <div className="modal-card mfa-modal-card" data-testid="mfa-modal">
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="security-icon">🔒</span>
            <div>
              <h2 id="mfa-title" className="modal-title">Security PIN Verification</h2>
              <p className="modal-subtitle">Sensitive transfer authorization required (amount &gt; $1,000)</p>
            </div>
          </div>
          <button className="btn-close" onClick={onCancel} aria-label="Cancel verification">
            ✕
          </button>
        </div>

        <div className="transfer-summary-box">
          <div className="summary-row">
            <span className="summary-label">Transfer Amount:</span>
            <span className="summary-value highlight-amount" data-testid="mfa-amount">
              {formattedAmount}
            </span>
          </div>
          <div className="summary-row">
            <span className="summary-label">From:</span>
            <span className="summary-value" data-testid="mfa-from-account">
              {fromAccount ? `${fromAccount.account_name} (${fromAccount.account_number})` : '-'}
            </span>
          </div>
          <div className="summary-row">
            <span className="summary-label">To:</span>
            <span className="summary-value" data-testid="mfa-to-account">
              {toAccount ? `${toAccount.account_name} (${toAccount.account_number})` : '-'}
            </span>
          </div>
        </div>

        {isLocked ? (
          <div className="lockout-banner" role="alert" data-testid="mfa-lockout-alert">
            <span className="lockout-icon">🚫</span>
            <div>
              <strong>Account Locked</strong>
              <p>MFA verification is locked after 3 failed attempts. Please contact Shift Bank support.</p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mfa-form">
            <div className="form-group">
              <label htmlFor="mfa-pin-input" className="form-label">
                Enter 4-Digit Security PIN
              </label>
              <input
                id="mfa-pin-input"
                type="password"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
                placeholder="••••"
                className="pin-input"
                data-testid="mfa-pin-input"
                autoFocus
                disabled={isSubmitting || isLocked}
                required
              />
              <div className="pin-helper-text">
                <span className="hint-badge">Demo PIN: <strong>1234</strong></span>
                <span className="attempts-text" data-testid="remaining-attempts">
                  {remainingAttempts} attempt(s) remaining
                </span>
              </div>
            </div>

            {errorMessage && (
              <div className="error-message" role="alert" data-testid="mfa-error-message">
                ⚠️ {errorMessage}
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onCancel}
                disabled={isSubmitting}
                data-testid="mfa-cancel-btn"
              >
                Cancel Transfer
              </button>
              <button
                type="submit"
                className="btn btn-primary btn-authorize"
                disabled={pin.length < 4 || isSubmitting || isLocked}
                data-testid="mfa-submit-btn"
              >
                {isSubmitting ? 'Verifying...' : 'Authorize Transfer'}
              </button>
            </div>
          </form>
        )}

        {isLocked && (
          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCancel}
              data-testid="mfa-close-locked-btn"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
