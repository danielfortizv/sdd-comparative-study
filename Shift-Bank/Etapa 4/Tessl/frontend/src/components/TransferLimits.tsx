import React, { useState, useEffect, useMemo } from 'react';
import { TransferLimits as TransferLimitsType } from '../api/types';
import {
  isValidMonetaryString,
  parseToCents,
  centsToDecimalString,
  divideHalfUp,
  formatCurrency,
} from '../utils/monetary';

interface TransferLimitsProps {
  isOpen: boolean;
  limits: TransferLimitsType | null;
  onClose: () => void;
  onUpdateLimits: (perTx: string, daily: string) => Promise<void>;
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
      setPerTxStr(limits.per_transaction_limit);
      setDailyStr(limits.daily_limit);
    }
  }, [limits]);

  const spentPercent = useMemo(() => {
    if (!limits) return 0;
    try {
      const dailyLimitCents = parseToCents(limits.daily_limit);
      const currentSpentCents = parseToCents(limits.current_daily_total);
      if (dailyLimitCents <= 0n) return 0;

      const percentBig = divideHalfUp(currentSpentCents * 100n, dailyLimitCents);
      if (percentBig < 0n) return 0;
      if (percentBig > 100n) return 100;
      return Number(percentBig);
    } catch {
      return 0;
    }
  }, [limits]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedPerTx = perTxStr.trim();
    if (!isValidMonetaryString(trimmedPerTx)) {
      setValidationError('Per-transaction limit must be a valid positive amount with at most 2 decimal places.');
      return;
    }

    const perTxCents = parseToCents(trimmedPerTx);
    if (perTxCents <= 0n) {
      setValidationError('Per-transaction limit must be strictly positive.');
      return;
    }

    const trimmedDaily = dailyStr.trim();
    if (!isValidMonetaryString(trimmedDaily)) {
      setValidationError('Daily transfer limit must be a valid positive amount with at most 2 decimal places.');
      return;
    }

    const dailyCents = parseToCents(trimmedDaily);
    if (dailyCents <= 0n) {
      setValidationError('Daily transfer limit must be strictly positive.');
      return;
    }

    if (perTxCents > dailyCents) {
      setValidationError('Per-transaction limit cannot exceed daily limit.');
      return;
    }

    const canonicalPerTx = centsToDecimalString(perTxCents);
    const canonicalDaily = centsToDecimalString(dailyCents);

    await onUpdateLimits(canonicalPerTx, canonicalDaily);
  };

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
                  {formatCurrency(limits.daily_limit, limits.reference_currency || 'USD')}
                </span>
              </div>
              <div>
                <span className="stat-label">Used Today</span>
                <span className="stat-value" data-testid="daily-spent-display">
                  {formatCurrency(limits.current_daily_total, limits.reference_currency || 'USD')}
                </span>
              </div>
              <div>
                <span className="stat-label">Remaining</span>
                <span className="stat-value text-green" data-testid="daily-remaining-display">
                  {formatCurrency(limits.remaining_daily_limit, limits.reference_currency || 'USD')}
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

        <form onSubmit={handleSubmit} className="transfer-form" noValidate>
          <div className="form-group">
            <label htmlFor="per-tx-limit-input" className="form-label">
              Per-Transaction Limit (USD)
            </label>
            <div className="input-with-prefix">
              <span className="input-prefix">$</span>
              <input
                id="per-tx-limit-input"
                type="text"
                inputMode="decimal"
                value={perTxStr}
                onChange={(e) => setPerTxStr(e.target.value)}
                placeholder="0.00"
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
                type="text"
                inputMode="decimal"
                value={dailyStr}
                onChange={(e) => setDailyStr(e.target.value)}
                placeholder="0.00"
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
              disabled={isSubmitting || !perTxStr.trim() || !dailyStr.trim()}
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
