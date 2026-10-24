import React, { useState, useEffect, useRef, useId } from 'react';
import { Account } from '../types/account';

interface TransferFormProps {
  accounts: Account[];
  defaultSourceAccountId?: string | null;
  resetKey?: number;
  onSubmitTransfer?: (data: {
    fromAccountId: string;
    toAccountId: string;
    amountCents: number;
    amountFormatted: string;
  }) => void;
  isSubmitting?: boolean;
}

export function parseAmountToCents(amount: string): number {
  if (!amount || isNaN(Number(amount))) return 0;
  const parts = amount.split('.');
  const dollars = parseInt(parts[0] || '0', 10);
  const cents = parts[1] ? parseInt(parts[1].padEnd(2, '0').slice(0, 2), 10) : 0;
  return dollars * 100 + cents;
}

export function formatCentsToUsd(cents: number): string {
  const dollars = Math.floor(cents / 100);
  const remainingCents = cents % 100;
  return `$${dollars.toLocaleString('en-US')}.${remainingCents.toString().padStart(2, '0')}`;
}

export const TransferForm: React.FC<TransferFormProps> = ({
  accounts,
  defaultSourceAccountId,
  resetKey,
  onSubmitTransfer,
  isSubmitting = false,
}) => {
  const formId = useId();
  const [sourceAccountId, setSourceAccountId] = useState<string>(
    defaultSourceAccountId || (accounts[0] ? accounts[0].id : '')
  );
  const [destinationAccountId, setDestinationAccountId] = useState<string>('');
  const [amountInput, setAmountInput] = useState<string>('');
  const prevDefaultSourceRef = useRef<string | null | undefined>(defaultSourceAccountId);

  // Synchronize when external defaultSourceAccountId changes
  useEffect(() => {
    if (defaultSourceAccountId && defaultSourceAccountId !== prevDefaultSourceRef.current) {
      prevDefaultSourceRef.current = defaultSourceAccountId;
      setSourceAccountId(defaultSourceAccountId);
    }
  }, [defaultSourceAccountId]);

  // Ensure sourceAccountId is initialized once accounts are loaded
  useEffect(() => {
    if (accounts.length > 0 && !sourceAccountId) {
      setSourceAccountId(defaultSourceAccountId || accounts[0].id);
    }
  }, [accounts, defaultSourceAccountId, sourceAccountId]);

  // Reset form amount input when resetKey changes
  useEffect(() => {
    if (resetKey !== undefined) {
      setAmountInput('');
    }
  }, [resetKey]);

  // Destination accounts excluding the currently selected source account
  const destinationOptions = accounts.filter((a) => a.id !== sourceAccountId);

  // Ensure destination account is valid and distinct from source account
  useEffect(() => {
    if (destinationOptions.length > 0) {
      if (!destinationAccountId || destinationAccountId === sourceAccountId) {
        setDestinationAccountId(destinationOptions[0].id);
      }
    } else {
      setDestinationAccountId('');
    }
  }, [sourceAccountId, destinationAccountId, destinationOptions]);

  const sourceAccount = accounts.find((a) => a.id === sourceAccountId);
  const amountCents = parseAmountToCents(amountInput);

  // Validation rules (FR-4, FR-5, FR-8)
  const isPositive = amountCents >= 1;
  const hasSufficientFunds = sourceAccount ? amountCents <= sourceAccount.balance_cents : false;
  const isSensitive = amountCents > 100000; // > $1,000.00 USD (100,000 cents)
  const isExceedingBalance = sourceAccount && amountCents > sourceAccount.balance_cents;
  const isValid = isPositive && hasSufficientFunds && sourceAccountId !== destinationAccountId && !isSubmitting;

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string or positive numbers with up to 2 decimals
    if (val === '' || /^\d+(\.\d{0,2})?$/.test(val)) {
      setAmountInput(val);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || !sourceAccount || isSubmitting) return;

    if (onSubmitTransfer) {
      onSubmitTransfer({
        fromAccountId: sourceAccountId,
        toAccountId: destinationAccountId,
        amountCents,
        amountFormatted: formatCentsToUsd(amountCents),
      });
    }
  };

  return (
    <section
      aria-labelledby={`${formId}-title`}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--rounded-lg)',
        padding: 'var(--spacing-lg)',
        boxShadow: 'var(--shadow-sm)',
      }}
      data-testid="transfer-form-panel"
    >
      <div style={{ marginBottom: 'var(--spacing-md)' }}>
        <h3
          id={`${formId}-title`}
          style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-primary)' }}
        >
          Transfer Funds
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--color-muted)', marginTop: '4px' }}>
          Move money instantly between your owned accounts.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Source Account Dropdown */}
        <div style={{ marginBottom: 'var(--spacing-md)' }}>
          <label
            htmlFor={`${formId}-source`}
            style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 500,
              marginBottom: '6px',
              color: 'var(--color-foreground)',
            }}
          >
            Source Account
          </label>
          <select
            id={`${formId}-source`}
            value={sourceAccountId}
            disabled={isSubmitting}
            onChange={(e) => setSourceAccountId(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--rounded-md)',
              fontSize: '14px',
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-foreground)',
              outline: 'none',
              cursor: isSubmitting ? 'not-allowed' : 'default',
            }}
            data-testid="transfer-source-select"
          >
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.nickname} ({acc.balance_formatted})
              </option>
            ))}
          </select>
        </div>

        {/* Destination Account Dropdown (Source excluded) */}
        <div style={{ marginBottom: 'var(--spacing-md)' }}>
          <label
            htmlFor={`${formId}-destination`}
            style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 500,
              marginBottom: '6px',
              color: 'var(--color-foreground)',
            }}
          >
            Destination Account
          </label>
          <select
            id={`${formId}-destination`}
            value={destinationAccountId}
            disabled={isSubmitting}
            onChange={(e) => setDestinationAccountId(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--rounded-md)',
              fontSize: '14px',
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-foreground)',
              outline: 'none',
              cursor: isSubmitting ? 'not-allowed' : 'default',
            }}
            data-testid="transfer-destination-select"
          >
            {destinationOptions.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.nickname} ({acc.balance_formatted})
              </option>
            ))}
          </select>
        </div>

        {/* Transfer Amount Input */}
        <div style={{ marginBottom: 'var(--spacing-md)' }}>
          <label
            htmlFor={`${formId}-amount`}
            style={{
              display: 'block',
              fontSize: '13px',
              fontWeight: 500,
              marginBottom: '6px',
              color: 'var(--color-foreground)',
            }}
          >
            Transfer Amount (USD)
          </label>
          <div style={{ position: 'relative' }}>
            <span
              style={{
                position: 'absolute',
                left: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-muted)',
                fontFamily: 'var(--font-family-mono)',
                fontWeight: 600,
              }}
              aria-hidden="true"
            >
              $
            </span>
            <input
              type="text"
              inputMode="decimal"
              id={`${formId}-amount`}
              value={amountInput}
              disabled={isSubmitting}
              onChange={handleAmountChange}
              placeholder="0.00"
              style={{
                width: '100%',
                padding: '10px 14px 10px 28px',
                border: isExceedingBalance
                  ? '1px solid var(--color-destructive)'
                  : '1px solid var(--color-border)',
                borderRadius: 'var(--rounded-md)',
                fontSize: '16px',
                fontFamily: 'var(--font-family-mono)',
                fontWeight: 600,
                outline: 'none',
                color: 'var(--color-foreground)',
                cursor: isSubmitting ? 'not-allowed' : 'text',
              }}
              aria-describedby={`${formId}-hint ${formId}-error`}
              data-testid="transfer-amount-input"
            />
          </div>

          {/* Insufficient Funds Error Alert (FR-5, UX-DR-4) */}
          {isExceedingBalance && sourceAccount && (
            <div
              id={`${formId}-error`}
              role="alert"
              style={{
                color: 'var(--color-destructive)',
                fontSize: '12px',
                marginTop: '6px',
                fontWeight: 500,
              }}
              data-testid="insufficient-funds-warning"
            >
              Insufficient funds in {sourceAccount.nickname} ({sourceAccount.balance_formatted} available).
            </div>
          )}

          {/* Dynamic Sensitivity Threshold Notice (FR-8, UX-DR-4) */}
          {isSensitive && (
            <div
              id={`${formId}-hint`}
              style={{
                color: 'var(--color-warning)',
                fontSize: '12px',
                marginTop: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 500,
              }}
              data-testid="mfa-sensitivity-hint"
            >
              <span aria-hidden="true">⚠️</span> Sensitive transfer: Mock MFA verification will be required.
            </div>
          )}

          {!isSensitive && !isExceedingBalance && (
            <div
              id={`${formId}-hint`}
              style={{ color: 'var(--color-muted)', fontSize: '12px', marginTop: '6px' }}
            >
              Transfers above $1,000.00 require mock MFA verification.
            </div>
          )}
        </div>

        {/* Submit Button (FR-7, FR-8, UX-DR-4) */}
        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          style={{
            width: '100%',
            padding: '12px 18px',
            backgroundColor: 'var(--color-primary)',
            color: 'var(--color-primary-foreground)',
            border: 'none',
            borderRadius: 'var(--rounded-md)',
            fontSize: '14px',
            fontWeight: 600,
            cursor: isValid && !isSubmitting ? 'pointer' : 'not-allowed',
            opacity: isValid && !isSubmitting ? 1 : 0.5,
            transition: 'all 0.15s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
          data-testid="transfer-submit-btn"
        >
          {isSubmitting ? (
            <>
              <span
                style={{
                  display: 'inline-block',
                  width: '14px',
                  height: '14px',
                  border: '2px solid rgba(255, 255, 255, 0.3)',
                  borderTopColor: '#FFFFFF',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
                data-testid="submit-spinner"
                aria-hidden="true"
              />
              <span>Processing Transfer...</span>
            </>
          ) : isSensitive ? (
            `Verify & Transfer (${formatCentsToUsd(amountCents)})`
          ) : (
            'Transfer Funds'
          )}
        </button>
      </form>
    </section>
  );
};
