import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Account, Transfer, HistoryEntry } from './types';
import { fetchAccounts, fetchHistory, initiateTransfer, confirmMFA } from './services';

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  
  // Loading and global alert states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Transfer Form States (User Story 2)
  const [sourceAccountId, setSourceAccountId] = useState<string>('');
  const [destinationAccountId, setDestinationAccountId] = useState<string>('');
  const [transferAmount, setTransferAmount] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);

  // MFA State Machine (User Story 4)
  const [showMfaModal, setShowMfaModal] = useState<boolean>(false);
  const [pendingTransfer, setPendingTransfer] = useState<Transfer | null>(null);
  const [pendingTransfersList, setPendingTransfersList] = useState<Transfer[]>([]);
  const [mfaCode, setMfaCode] = useState<string>('');
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [mfaSubmitting, setMfaSubmitting] = useState<boolean>(false);
  
  // Timer for MFA Expiration
  const [timeLeft, setTimeLeft] = useState<number>(300); // 5 minutes in seconds
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load history function
  const loadHistoryData = useCallback(async (accountId: string) => {
    try {
      const historyData = await fetchHistory(accountId);
      setHistory(historyData);
    } catch (err: any) {
      setError(err.message || 'Failed to load transaction history.');
    }
  }, []);

  // Load accounts and initial setup
  const loadAccountsData = async (shouldLoadHistoryForId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAccounts();
      setAccounts(data);
      
      if (data.length > 0) {
        const checking = data.find(a => a.name === 'Checking');
        const defaultSrcId = checking ? checking.id : data[0].id;
        
        let activeId = selectedAccountId;
        if (!activeId) {
          activeId = defaultSrcId;
          setSelectedAccountId(activeId);
        }

        // Default form selections if not set
        if (!sourceAccountId) {
          setSourceAccountId(defaultSrcId);
        }
        if (!destinationAccountId) {
          const savings = data.find(a => a.name === 'Savings');
          setDestinationAccountId(savings ? savings.id : (data[1] ? data[1].id : ''));
        }

        // Fetch transaction history for active account
        const idToFetch = shouldLoadHistoryForId || activeId;
        await loadHistoryData(idToFetch);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load accounts.');
    } finally {
      setLoading(false);
    }
  };

  // Load initial bank data on mount
  useEffect(() => {
    loadAccountsData();
  }, []);

  // Re-fetch transaction history whenever the selected account changes on dashboard
  useEffect(() => {
    if (selectedAccountId) {
      loadHistoryData(selectedAccountId);
    }
  }, [selectedAccountId, loadHistoryData]);

  // MFA Expiration timer effect
  useEffect(() => {
    if (showMfaModal && timeLeft > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft <= 0) {
      setMfaError("The 5-minute MFA window has expired. Submitting will result in error.");
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [showMfaModal, timeLeft]);

  // Format currency helper (strictly Colombian Peso)
  const formatCurrency = (amount: string) => {
    const num = parseFloat(amount);
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
    }).format(num);
  };

  // Format date helper
  const formatDate = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('es-CO', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  // Format remaining timer helper
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // Transfer Submit Handler (User Stories 2 & 4)
  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccess(null);
    setError(null);

    // 1. Client-side validations
    if (sourceAccountId === destinationAccountId) {
      setFormError("Source and destination accounts must be different.");
      return;
    }

    const amountNum = parseFloat(transferAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setFormError("Amount must be greater than zero.");
      return;
    }

    const sourceAccount = accounts.find(a => a.id === sourceAccountId);
    if (!sourceAccount) {
      setFormError("Source account not found.");
      return;
    }

    const sourceBalance = parseFloat(sourceAccount.balance);
    if (amountNum > sourceBalance) {
      setFormError("Insufficient funds.");
      return;
    }

    // 2. Call API
    try {
      setFormSubmitting(true);
      const formattedAmountStr = amountNum.toFixed(2);

      const transferResult = await initiateTransfer(
        sourceAccountId,
        destinationAccountId,
        formattedAmountStr
      );

      // Handle sensitive transfer pending MFA (202 Accepted response)
      if (transferResult.status === 'PENDING_MFA') {
        setPendingTransfer(transferResult);
        setMfaCode('');
        setMfaError(null);
        if (transferResult.expires_at) {
          const expiresAt = new Date(transferResult.expires_at).getTime();
          const now = new Date().getTime();
          const remainingSeconds = Math.max(0, Math.round((expiresAt - now) / 1000));
          setTimeLeft(remainingSeconds);
        } else {
          setTimeLeft(300); // Reset timer to 5 minutes
        }
        setShowMfaModal(true);
      } else if (transferResult.status === 'COMPLETED') {
        // Direct standard transfer success
        setSuccess(`Transfer of ${formatCurrency(formattedAmountStr)} executed successfully!`);
        setTransferAmount(''); // Clear form input
        await loadAccountsData(selectedAccountId || sourceAccountId);
      }
    } catch (err: any) {
      setFormError(err.message || "An error occurred initiating the transfer.");
    } finally {
      setFormSubmitting(false);
    }
  };

  // MFA Code Submit Handler (User Story 4)
  const handleMfaConfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingTransfer) return;
    setMfaError(null);

    if (mfaCode.length !== 6 || !/^\d+$/.test(mfaCode)) {
      setMfaError("MFA code must be exactly 6 digits.");
      return;
    }

    try {
      setMfaSubmitting(true);
      const res = await confirmMFA(pendingTransfer.id, mfaCode);

      if (res.status === 'COMPLETED') {
        setSuccess(`Transfer of ${formatCurrency(pendingTransfer.amount)} executed successfully!`);
        setTransferAmount(''); // Clear transfer form input
        
        // Remove from pending list if confirming a resumed transfer
        setPendingTransfersList(prev => prev.filter(t => t.id !== pendingTransfer.id));
        
        // Close modal and reset
        setShowMfaModal(false);
        setPendingTransfer(null);
        
        // Reload all balances and history
        await loadAccountsData(selectedAccountId || '');
      }
    } catch (err: any) {
      setMfaError(err.message || "MFA confirmation failed.");
    } finally {
      setMfaSubmitting(false);
    }
  };

  // Close MFA modal handler (moves transfer to resume list)
  const handleMfaModalClose = () => {
    if (pendingTransfer) {
      setPendingTransfersList(prev => {
        // Avoid duplicates in the list
        if (prev.some(t => t.id === pendingTransfer.id)) return prev;
        return [...prev, pendingTransfer];
      });
    }
    setShowMfaModal(false);
    setPendingTransfer(null);
  };

  // Resume a pending transfer from the list
  const handleResumeTransfer = (tx: Transfer) => {
    setPendingTransfer(tx);
    setMfaCode('');
    setMfaError(null);
    if (tx.expires_at) {
      const expiresAt = new Date(tx.expires_at).getTime();
      const now = new Date().getTime();
      const remainingSeconds = Math.max(0, Math.round((expiresAt - now) / 1000));
      setTimeLeft(remainingSeconds);
      if (remainingSeconds <= 0) {
        setMfaError("The 5-minute MFA window has expired. Submitting will result in error.");
      }
    } else {
      setTimeLeft(300); // Fallback
    }
    setShowMfaModal(true);
  };

  // Find currently selected account name for display
  const selectedAccountName = accounts.find(a => a.id === selectedAccountId)?.name || 'Account';

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <span>🏦</span> Shift Bank
        </div>
        <div style={{ color: 'var(--secondary-color)', fontSize: '0.9rem' }}>
          Authenticated Customer
        </div>
      </header>

      {/* Global Alerts */}
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Pending Transfers Resume Widget (User Story 4) */}
      {pendingTransfersList.length > 0 && (
        <div className="pending-transfers-widget">
          <h3 className="section-title" style={{ fontSize: '1.1rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            ⚠️ Pending Sensitive Transfers
          </h3>
          <div style={{ fontSize: '0.9rem', color: 'var(--secondary-color)', marginBottom: '0.75rem' }}>
            The following transfers require Multi-Factor Authentication (MFA) to finalize.
          </div>
          {pendingTransfersList.map((tx) => (
            <div key={tx.id} className="pending-transfer-item">
              <div>
                <strong>{tx.source_account} to {tx.destination_account}</strong>
                <div style={{ fontSize: '0.85rem', color: 'var(--secondary-color)' }}>
                  Amount: {formatCurrency(tx.amount)}
                </div>
              </div>
              <button
                className="btn-resume"
                onClick={() => handleResumeTransfer(tx)}
              >
                Resume
              </button>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading bank data...</div>
      ) : (
        <div className="dashboard-grid">
          {/* Main Content Area */}
          <div>
            {/* Account Overview Section (User Story 1) */}
            <section className="accounts-section">
              <h2 className="section-title">Account Overview</h2>
              <div className="accounts-container">
                {accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className={`account-card ${selectedAccountId === acc.id ? 'selected' : ''}`}
                    onClick={() => setSelectedAccountId(acc.id)}
                  >
                    <div className="account-type">{acc.name}</div>
                    <div className="account-balance">{formatCurrency(acc.balance)}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* Transaction History Section (User Story 3) */}
            <section className="history-section">
              <h2 className="section-title">Transaction History: {selectedAccountName}</h2>
              {history.length === 0 ? (
                <div style={{ color: 'var(--secondary-color)', fontStyle: 'italic' }}>
                  No completed transactions recorded for this account.
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Direction</th>
                        <th>Amount</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((tx) => (
                        <tr key={tx.id}>
                          <td>{formatDate(tx.date)}</td>
                          <td className={tx.direction === 'incoming' ? 'direction-incoming' : 'direction-outgoing'}>
                            {tx.direction === 'incoming' ? 'Incoming' : 'Outgoing'}
                          </td>
                          <td>{formatCurrency(tx.amount)}</td>
                          <td>{tx.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          {/* Right Sidebar Area (User Story 2: Transfer Funds Form) */}
          <div>
            <div className="form-card">
              <h2 className="section-title">Transfer Funds</h2>
              
              {formError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{formError}</div>}

              <form onSubmit={handleTransferSubmit}>
                <div className="form-group">
                  <label htmlFor="source-select" className="form-label">Source Account</label>
                  <select
                    id="source-select"
                    className="form-select"
                    value={sourceAccountId}
                    onChange={(e) => {
                      setSourceAccountId(e.target.value);
                      setFormError(null);
                    }}
                  >
                    {accounts.map(a => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="dest-select" className="form-label">Destination Account</label>
                  <select
                    id="dest-select"
                    className="form-select"
                    value={destinationAccountId}
                    onChange={(e) => {
                      setDestinationAccountId(e.target.value);
                      setFormError(null);
                    }}
                  >
                    {accounts.map(a => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="amount-input" className="form-label">Amount (COP)</label>
                  <input
                    id="amount-input"
                    type="number"
                    step="0.01"
                    className="form-input"
                    placeholder="Enter amount"
                    value={transferAmount}
                    onChange={(e) => {
                      setTransferAmount(e.target.value);
                      setFormError(null);
                    }}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? 'Transferring...' : 'Transfer'}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* step-up MFA Modal Overlay Component (User Story 4) */}
      {showMfaModal && pendingTransfer && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">MFA Verification</h3>
              <button
                className="modal-close"
                aria-label="Close"
                onClick={handleMfaModalClose}
              >
                &times;
              </button>
            </div>
            
            <form onSubmit={handleMfaConfirmSubmit}>
              <div className="modal-body">
                {mfaError && <div className="alert alert-danger" style={{ padding: '0.5rem', fontSize: '0.85rem', marginBottom: '1rem' }}>{mfaError}</div>}
                
                <div className="mfa-info">
                  A high-value transfer of <strong>{formatCurrency(pendingTransfer.amount)}</strong> from <strong>{pendingTransfer.source_account}</strong> to <strong>{pendingTransfer.destination_account}</strong> was requested.
                </div>
                <div className="mfa-info">
                  Enter the 6-digit code to finalize. Time remaining: <span className="mfa-timer">{formatTimer(timeLeft)}</span>.
                </div>

                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label htmlFor="mfa-code-input" className="form-label">MFA Code</label>
                  <input
                    id="mfa-code-input"
                    type="text"
                    maxLength={6}
                    pattern="\d{6}"
                    className="form-input"
                    style={{ textAlign: 'center', fontSize: '1.2rem', letterSpacing: '4px' }}
                    placeholder="000000"
                    value={mfaCode}
                    onChange={(e) => {
                      setMfaCode(e.target.value);
                      setMfaError(null);
                    }}
                    disabled={mfaSubmitting}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleMfaModalClose}
                  disabled={mfaSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={mfaSubmitting}
                >
                  {mfaSubmitting ? 'Confirming...' : 'Confirm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
