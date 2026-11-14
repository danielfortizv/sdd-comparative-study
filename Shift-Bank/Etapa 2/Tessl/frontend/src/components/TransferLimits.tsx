import React, { useState, useEffect } from 'react';
import { TransferLimits as TransferLimitsType } from '../api/types';

interface TransferLimitsProps {
  isOpen: boolean;
  limits: TransferLimitsType | null;
  onClose: () => void;
  onUpdateLimits: (perTx: number, daily: number) => Promise<void>;
  isSubmitting?: boolean;
  errorMessage?: string | null;
}

export const TransferLimits: React.FC<TransferLimitsProps> = ({
  isOpen,
  limits,
  onClose,
  onUpdateLimits,
  isSubmitting = false,
  errorMessage = null,
}) => {
  const [perTxStr, setPerTxStr] = useState<string>('');
  const [dailyStr, setDailyStr] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (limits) {
      setPerTxStr(limits.per_transaction_limit.toString());
      setDailyStr(limits.daily_limit.toString());
    }
  }, [limits]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const perTx = parseFloat(perTxStr);
    const daily = parseFloat(dailyStr);

    if (isNaN(perTx) || perTx <= 0) {
      setValidationError('Per-transaction limit must be strictly positive.');
      return;
    }

    if (isNaN(daily) || daily <= 0) {
      setValidationError('Daily transfer limit must be strictly positive.');
      return;
    }

    if (perTx > daily) {
      setValidationError('Per-transaction limit cannot exceed daily limit.');
      return;
    }

    await onUpdateLimits(perTx, daily);
  };

  const spentPercent = limits && limits.daily_limit > 0
    ? Math.min(100, Math.round((limits.current_daily_total / limits.daily_limit) * 100))
    : 0;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="limits-title">
      <div className="modal-card" data-testid="limits-modal">
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">⚙️</span>
            <div>
              <h2 id="limits-title" className="modal-title">Dynamic Transfer Limits</h2>
              <p className="modal-subtitle">Configure per-transaction and daily limits</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close transfer limits">
            ✕
          </button>
        </div>

        {limits && (
          <div className="limits-summary-card" data-testid="limits-summary-gauge">
            <div className="limits-stat-row">
              <div>
                <span className="stat-label">Daily Limit</span>
                <span className="stat-value" data-testid="daily-limit-display">
                  ${limits.daily_limit.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="stat-label">Used Today</span>
                <span className="stat-value" data-testid="daily-spent-display">
                  ${limits.current_daily_total.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="stat-label">Remaining</span>
                <span className="stat-value text-green" data-testid="daily-remaining-display">
                  ${limits.remaining_daily_limit.toFixed(2)}
                </span>
              </div>
            </div>
            <div className="progress-bar-container" title={`${spentPercent}% of daily limit used`}>
              <div
                className={`progress-bar-fill ${spentPercent > 80 ? 'progress-warn' : ''}`}
                style={{ width: `${spentPercent}%` }}
              />
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="transfer-form">
          <div className="form-group">
            <label htmlFor="per-tx-limit-input" className="form-label">
              Per-Transaction Limit (USD)
            </label>
            <div className="input-with-prefix">
              <span className="input-prefix">$</span>
              <input
                id="per-tx-limit-input"
                type="number"
                step="0.01"
                min="0.01"
                value={perTxStr}
                onChange={(e) => setPerTxStr(e.target.value)}
                className="form-input"
                data-testid="per-tx-limit-input"
                disabled={isSubmitting}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="daily-limit-input" className="form-label">
              Daily Cumulative Limit (USD)
            </label>
            <div className="input-with-prefix">
              <span className="input-prefix">$</span>
              <input
                id="daily-limit-input"
                type="number"
                step="0.01"
                min="0.01"
                value={dailyStr}
                onChange={(e) => setDailyStr(e.target.value)}
                className="form-input"
                data-testid="daily-limit-input"
                disabled={isSubmitting}
                required
              />
            </div>
          </div>

          {(validationError || errorMessage) && (
            <div className="error-message" role="alert" data-testid="limits-error-message">
              ⚠️ {validationError || errorMessage}
            </div>
          )}

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || !perTxStr || !dailyStr}
              data-testid="save-limits-btn"
            >
              {isSubmitting ? 'Saving...' : 'Save Limits'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
