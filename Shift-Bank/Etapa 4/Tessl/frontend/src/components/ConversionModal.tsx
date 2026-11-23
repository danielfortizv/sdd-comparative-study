import React, { useState, useMemo } from 'react';
import { Account, ConversionResponse } from '../api/types';
import { api, ApiError, generateIdempotencyKey } from '../api/client';
import {
  isValidMonetaryString,
  parseToCents,
  centsToDecimalString,
  convertCurrency,
  isUsdEquivalentExceedingThreshold,
  formatRationalRate,
  formatCurrency,
  divideHalfUp,
  USD_BASE_FACTORS,
  SupportedCurrency,
} from '../utils/monetary';

interface ConversionModalProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: Account[];
  onConversionSuccess: (res: ConversionResponse) => void;
  onRefreshAccounts: () => void;
}

export const ConversionModal: React.FC<ConversionModalProps> = ({
  isOpen,
  onClose,
  accounts,
  onConversionSuccess,
  onRefreshAccounts,
}) => {
  const [fromAccountId, setFromAccountId] = useState<number>(accounts[0]?.id || 1);
  const [toAccountId, setToAccountId] = useState<number>(accounts[1]?.id || 2);
  const [amountStr, setAmountStr] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [pin, setPin] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeOperation, setActiveOperation] = useState<{
    payloadKey: string;
    idempotencyKey: string;
  } | null>(null);

  const fromAccount = useMemo(
    () => accounts.find((a) => a.id === fromAccountId) || accounts[0],
    [accounts, fromAccountId]
  );

  // Destination accounts must have a DIFFERENT currency (D-01, D-04)
  const availableDestinationAccounts = useMemo(() => {
    if (!fromAccount) return [];
    return accounts.filter((a) => a.id !== fromAccount.id && a.currency !== fromAccount.currency);
  }, [accounts, fromAccount]);

  const toAccount = useMemo(() => {
    return availableDestinationAccounts.find((a) => a.id === toAccountId) || availableDestinationAccounts[0];
  }, [availableDestinationAccounts, toAccountId]);

  // Live conversion preview using exact D-03 rational reference rates and single ROUND_HALF_UP
  const previewData = useMemo(() => {
    if (!fromAccount || !toAccount || fromAccount.currency === toAccount.currency) {
      return null;
    }
    const trimmed = amountStr.trim();
    if (!isValidMonetaryString(trimmed)) {
      return null;
    }
    const sourceCents = parseToCents(trimmed);
    if (sourceCents <= 0n) {
      return null;
    }

    try {
      const result = convertCurrency(
        sourceCents,
        fromAccount.currency as SupportedCurrency,
        toAccount.currency as SupportedCurrency
      );

      const usdFactor = USD_BASE_FACTORS[fromAccount.currency as SupportedCurrency];
      const usdCents = divideHalfUp(sourceCents * usdFactor.numerator, usdFactor.denominator);
      const rateDisplay = formatRationalRate(result.rateNumerator, result.rateDenominator);

      return {
        previewDestAmount: result.destinationAmount,
        rateDisplay,
        usdEquivalent: centsToDecimalString(usdCents),
        sourceCents,
      };
    } catch {
      return null;
    }
  }, [fromAccount, toAccount, amountStr]);

  // MFA check using unrounded integer cross-multiplication (D-07, D-03)
  const requiresMfa = useMemo(() => {
    if (!fromAccount) return false;
    const trimmed = amountStr.trim();
    if (!isValidMonetaryString(trimmed)) return false;
    const sourceCents = parseToCents(trimmed);
    if (sourceCents <= 0n) return false;

    return isUsdEquivalentExceedingThreshold(
      sourceCents,
      fromAccount.currency as SupportedCurrency,
      '1000.00'
    );
  }, [fromAccount, amountStr]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setError(null);

    if (!fromAccount || !toAccount || fromAccount.currency === toAccount.currency) {
      setError('Please select valid source and destination accounts with different currencies.');
      return;
    }

    const trimmedAmount = amountStr.trim();
    if (!isValidMonetaryString(trimmedAmount)) {
      setError('Invalid monetary amount. Please provide a positive amount with at most 2 decimal places.');
      return;
    }

    const sourceCents = parseToCents(trimmedAmount);
    if (sourceCents <= 0n) {
      setError('Conversion amount must be strictly positive.');
      return;
    }

    const sourceBalanceCents = parseToCents(fromAccount.balance);
    if (sourceCents > sourceBalanceCents) {
      setError(
        `Insufficient funds in ${fromAccount.account_name}. Available: ${formatCurrency(
          fromAccount.balance,
          fromAccount.currency
        )}`
      );
      return;
    }

    // Check if conversion produces a zero destination amount
    let convResult;
    try {
      convResult = convertCurrency(
        sourceCents,
        fromAccount.currency as SupportedCurrency,
        toAccount.currency as SupportedCurrency
      );
    } catch (err: any) {
      setError(err.message || 'Conversion amount too small; resulting amount would be zero.');
      return;
    }

    if (convResult.destinationCents <= 0n) {
      setError('Conversion amount too small; resulting amount would be zero.');
      return;
    }

    if (requiresMfa && (!pin || !pin.trim())) {
      setError('Security PIN is required for conversions exceeding $1,000 USD equivalent.');
      return;
    }

    const canonicalSourceAmount = centsToDecimalString(sourceCents);
    const payloadKey = JSON.stringify({
      from_account_id: fromAccount.id,
      to_account_id: toAccount.id,
      source_amount: canonicalSourceAmount,
      expected_from_version: fromAccount.version,
      expected_to_version: toAccount.version,
      description: description || undefined,
      pin: requiresMfa ? pin.trim() : undefined,
    });

    let idempotencyKey: string;
    if (activeOperation && activeOperation.payloadKey === payloadKey) {
      idempotencyKey = activeOperation.idempotencyKey;
    } else {
      idempotencyKey = generateIdempotencyKey();
      setActiveOperation({ payloadKey, idempotencyKey });
    }

    setIsSubmitting(true);
    try {
      const response = await api.executeConversion(
        {
          from_account_id: fromAccount.id,
          to_account_id: toAccount.id,
          source_amount: canonicalSourceAmount,
          expected_from_version: fromAccount.version,
          expected_to_version: toAccount.version,
          description: description || undefined,
          pin: requiresMfa ? pin.trim() : undefined,
        },
        idempotencyKey
      );

      setActiveOperation(null);
      onConversionSuccess(response);
      onClose();
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        if (err.code === 'ACCOUNT_VERSION_CONFLICT') {
          setActiveOperation(null);
          setError('Account version conflict detected: Account balances have changed. Refreshing accounts...');
          onRefreshAccounts();
        } else if (err.code === 'IDEMPOTENCY_KEY_REUSE' || err.code === 'IDEMPOTENCY_KEY_CONFLICT') {
          setError(
            err.message || 'Idempotency conflict: Key was previously submitted with different parameters.'
          );
        } else {
          setActiveOperation(null);
          setError(err.message || 'Conflict occurred during currency conversion.');
        }
      } else {
        setError(err.message || 'Currency conversion failed.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" data-testid="conversion-modal">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Simulated Currency Conversion</h2>
          <button
            className="close-btn"
            onClick={() => {
              setActiveOperation(null);
              onClose();
            }}
            aria-label="Close modal"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="error-banner" role="alert" data-testid="conversion-error">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="from-account-select">Source Account (Debit):</label>
            <select
              id="from-account-select"
              value={fromAccountId}
              onChange={(e) => setFromAccountId(parseInt(e.target.value, 10))}
              disabled={isSubmitting}
            >
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.account_name} ({formatCurrency(acc.balance, acc.currency)}) - v{acc.version}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="to-account-select">Destination Account (Credit):</label>
            <select
              id="to-account-select"
              value={toAccount?.id || ''}
              onChange={(e) => setToAccountId(parseInt(e.target.value, 10))}
              disabled={isSubmitting || availableDestinationAccounts.length === 0}
            >
              {availableDestinationAccounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.account_name} ({formatCurrency(acc.balance, acc.currency)}) - v{acc.version}
                </option>
              ))}
            </select>
            {availableDestinationAccounts.length === 0 && (
              <p className="help-text text-danger">No accounts in a different currency available.</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="source-amount-input">
              Source Amount ({fromAccount?.currency}):
            </label>
            <input
              id="source-amount-input"
              type="text"
              inputMode="decimal"
              placeholder="0.00"
              value={amountStr}
              onChange={(e) => setAmountStr(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>

          {/* Live Preview Box */}
          {previewData && fromAccount && toAccount && (
            <div className="conversion-preview-box" style={{ background: '#f8fafc', padding: '1rem', borderRadius: '6px', margin: '1rem 0' }}>
              <div>
                <strong>Applied FX Rate:</strong> 1 {fromAccount.currency} = {previewData.rateDisplay} {toAccount.currency}
              </div>
              <div style={{ marginTop: '0.25rem' }}>
                <strong>Credited Destination Amount:</strong>{' '}
                <span data-testid="preview-destination-amount" style={{ color: '#059669', fontWeight: 'bold' }}>
                  {toAccount.currency} {previewData.previewDestAmount}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>
                Estimated USD Equivalent: ${previewData.usdEquivalent} USD
              </div>
            </div>
          )}

          {requiresMfa && (
            <div className="form-group mfa-box" style={{ background: '#fffbeb', border: '1px solid #fef3c7', padding: '1rem', borderRadius: '6px' }}>
              <label htmlFor="conversion-pin-input">
                🔒 Security PIN Required (USD equivalent &gt; $1,000):
              </label>
              <input
                id="conversion-pin-input"
                type="password"
                maxLength={10}
                placeholder="Enter 4-digit PIN (default: 1234)"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                disabled={isSubmitting}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="conversion-desc-input">Description (Optional):</label>
            <input
              id="conversion-desc-input"
              type="text"
              placeholder="e.g. Travel fund conversion"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="modal-actions" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || !amountStr.trim() || !toAccount}
              data-testid="submit-conversion-btn"
            >
              {isSubmitting ? 'Converting...' : 'Execute Conversion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
