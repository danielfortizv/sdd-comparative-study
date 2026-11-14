import React, { useState, useEffect, useMemo } from 'react';
import { Account, TransferRequest, Beneficiary, AchTransferRequest, TransferLimits } from '../api/types';
import {
  isValidMonetaryString,
  parseToCents,
  centsToDecimalString,
  isUsdEquivalentExceedingThreshold,
  formatCurrency,
  SupportedCurrency,
} from '../utils/monetary';

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

  const sourceAccount = useMemo(
    () => accounts.find((a) => a.id === fromAccountId) || null,
    [accounts, fromAccountId]
  );

  // Filter destination accounts strictly to SAME currency (D-01, D-04)
  const destinationOptions = useMemo(
    () => accounts.filter((a) => a.id !== fromAccountId && (sourceAccount ? a.currency === sourceAccount.currency : true)),
    [accounts, fromAccountId, sourceAccount]
  );

  useEffect(() => {
    if (accounts.length >= 2) {
      if (!fromAccountId || !accounts.some((a) => a.id === fromAccountId)) {
        setFromAccountId(accounts[0].id);
      }
      if (!toAccountId || !destinationOptions.some((a) => a.id === toAccountId)) {
        if (destinationOptions.length > 0) {
          setToAccountId(destinationOptions[0].id);
        }
      }
    }
  }, [accounts, fromAccountId, toAccountId, destinationOptions]);

  const toAccount = useMemo(
    () => accounts.find((a) => a.id === toAccountId) || null,
    [accounts, toAccountId]
  );

  const isSensitive = useMemo(() => {
    if (!sourceAccount) return false;
    const trimmed = amountStr.trim();
    if (!isValidMonetaryString(trimmed)) return false;
    const cents = parseToCents(trimmed);
    if (cents <= 0n) return false;
    return isUsdEquivalentExceedingThreshold(
      cents,
      sourceAccount.currency as SupportedCurrency,
      '1000.00'
    );
  }, [sourceAccount, amountStr]);

  if (!isOpen) return null;

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

  const validateAmount = (val: string): boolean => {
    const trimmed = val.trim();
    if (!trimmed) {
      setValidationError(null);
      return false;
    }

    if (!isValidMonetaryString(trimmed)) {
      setValidationError('Please enter a valid transfer amount with at most 2 decimal places.');
      return false;
    }

    const cents = parseToCents(trimmed);
    if (cents <= 0n) {
      setValidationError('Please enter a valid transfer amount greater than zero.');
      return false;
    }

    if (sourceAccount) {
      const balanceCents = parseToCents(sourceAccount.balance);
      if (cents > balanceCents) {
        setValidationError(
          `Amount exceeds available balance (${formatCurrency(sourceAccount.balance, sourceAccount.currency)})`
        );
        return false;
      }
    }

    if (limits && sourceAccount) {
      if (
        isUsdEquivalentExceedingThreshold(
          cents,
          sourceAccount.currency as SupportedCurrency,
          limits.per_transaction_limit
        )
      ) {
        setValidationError(
          `Amount exceeds per-transaction limit (${formatCurrency(
            limits.per_transaction_limit,
            limits.reference_currency || 'USD'
          )})`
        );
        return false;
      }

      if (
        isUsdEquivalentExceedingThreshold(
          cents,
          sourceAccount.currency as SupportedCurrency,
          limits.remaining_daily_limit
        )
      ) {
        setValidationError(
          `Amount exceeds remaining daily limit (${formatCurrency(
            limits.remaining_daily_limit,
            limits.reference_currency || 'USD'
          )})`
        );
        return false;
      }
    }

    setValidationError(null);
    return true;
  };

  const handleAmountChange = (val: string) => {
    setAmountStr(val);
    validateAmount(val);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (!validateAmount(amountStr)) {
      return;
    }

    const trimmed = amountStr.trim();
    const cents = parseToCents(trimmed);
    const canonicalAmount = centsToDecimalString(cents);

    if (transferType === 'internal') {
      if (fromAccountId === toAccountId) {
        setValidationError('Source and destination accounts must be different.');
        return;
      }
      if (!sourceAccount || !toAccount) {
        setValidationError('Source and destination accounts must be selected.');
        return;
      }
      if (sourceAccount.currency !== toAccount.currency) {
        setValidationError('Internal transfers must be same-currency. Please use Currency Conversion.');
        return;
      }

      onSubmit({
        from_account_id: fromAccountId,
        to_account_id: toAccountId,
        amount: canonicalAmount,
        expected_from_version: sourceAccount.version,
        expected_to_version: toAccount.version,
        description: description.trim() || undefined,
      });
    } else {
      // ACH Transfer
      if (!sourceAccount) {
        setValidationError('Source account must be selected.');
        return;
      }
      if (sourceAccount.currency !== 'USD') {
        setValidationError('ACH transfers are only permitted from USD accounts.');
        return;
      }

      if (selectedBeneficiaryId) {
        if (onSubmitAch) {
          onSubmitAch({
            from_account_id: fromAccountId,
            beneficiary_id: Number(selectedBeneficiaryId),
            amount: canonicalAmount,
            expected_from_version: sourceAccount.version,
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
            amount: canonicalAmount,
            expected_from_version: sourceAccount.version,
            description: description.trim() || undefined,
          });
        }
      }
    }
  };

  const isAmountValid =
    amountStr.trim() !== '' &&
    isValidMonetaryString(amountStr.trim()) &&
    parseToCents(amountStr.trim()) > 0n;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="transfer-title">
      <div className="modal-card" data-testid="transfer-modal">
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">⇄</span>
            <div>
              <h2 id="transfer-title" className="modal-title">Transfer Funds</h2>
              <p className="modal-subtitle">Transfer money between same-currency accounts or via ACH</p>
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
            Internal Account (Same-Currency)
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
            External ACH (USD Only)
          </button>
        </div>

        <form onSubmit={handleSubmit} className="transfer-form" noValidate>
          <div className="form-group">
            <label htmlFor="from-account-select" className="form-label">
              Transfer From
            </label>
            <select
              id="from-account-select"
              value={fromAccountId}
              onChange={(e) => {
                const newFrom = parseInt(e.target.value, 10);
                setFromAccountId(newFrom);
              }}
              className="form-select"
              data-testid="from-account-select"
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
              <label htmlFor="to-account-select" className="form-label">
                Transfer To (Same Currency: {sourceAccount?.currency})
              </label>
              <select
                id="to-account-select"
                value={toAccountId}
                onChange={(e) => setToAccountId(parseInt(e.target.value, 10))}
                className="form-select"
                data-testid="to-account-select"
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
                  No other accounts with currency {sourceAccount?.currency}. For cross-currency transfers, use Currency Conversion.
                </p>
              )}
            </div>
          ) : (
            <div className="ach-recipient-section" data-testid="ach-recipient-section">
              {sourceAccount && sourceAccount.currency !== 'USD' && (
                <div className="error-message" style={{ marginBottom: '12px' }} data-testid="ach-currency-warning">
                  ⚠️ ACH transfers are only supported from USD accounts. Selected source account is {sourceAccount.currency}.
                </div>
              )}
              <div className="form-group">
                <label htmlFor="beneficiary-select" className="form-label">
                  External Beneficiary
                </label>
                <select
                  id="beneficiary-select"
                  value={selectedBeneficiaryId}
                  onChange={(e) => setSelectedBeneficiaryId(e.target.value ? parseInt(e.target.value, 10) : '')}
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
              Amount ({sourceAccount?.currency || 'USD'})
            </label>
            <div className="input-with-prefix">
              <span className="input-prefix">
                {sourceAccount?.currency === 'EUR' ? '€' : sourceAccount?.currency === 'GBP' ? '£' : '$'}
              </span>
              <input
                id="transfer-amount-input"
                type="text"
                inputMode="decimal"
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
                ℹ️ Transfers over $1,000.00 USD equivalent require mock Security PIN authorization.
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
                !isAmountValid ||
                !!validationError ||
                !!routingError ||
                (transferType === 'internal' && destinationOptions.length === 0) ||
                (transferType === 'ach' && sourceAccount?.currency !== 'USD')
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
