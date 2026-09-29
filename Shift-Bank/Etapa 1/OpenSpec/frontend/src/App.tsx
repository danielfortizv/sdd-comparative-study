import React, { useState, useEffect } from 'react';

interface Account {
  id: string;
  name: string;
  balance: string;
}

interface Transaction {
  id: string;
  source_account_id: string;
  source_account_name: string;
  destination_account_id: string;
  destination_account_name: string;
  amount: string;
  timestamp: string;
  status: 'COMPLETED' | 'PENDING_MFA' | 'EXPIRED' | 'FAILED';
}

interface ActiveTransfer {
  sourceName: string;
  destName: string;
  amount: string;
}

export default function App() {
  // Accounts and transaction history state
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [history, setHistory] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form states
  const [sourceAccountId, setSourceAccountId] = useState<string>('');
  const [destinationAccountId, setDestinationAccountId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [transferError, setTransferError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // MFA Modal states
  const [isMfaOpen, setIsMfaOpen] = useState<boolean>(false);
  const [mfaTransferId, setMfaTransferId] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState<string>('');
  const [mfaTimer, setMfaTimer] = useState<number>(300); // 5 minutes in seconds
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [activeTransfer, setActiveTransfer] = useState<ActiveTransfer | null>(null);

  // Ledger filter state
  const [filter, setFilter] = useState<'All' | 'Checking' | 'Savings'>('All');

  // Hardcoded User Info
  const user = {
    name: "Jane Doe",
    id: "usr_101"
  };

  // Helper to format currency in COP
  const formatCOP = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    if (isNaN(num)) return '$0,00 COP';
    try {
      const formatted = new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(num);
      return `${formatted} COP`;
    } catch (e) {
      return `$${num.toFixed(2)} COP`;
    }
  };

  // Helper to format ISO Date to clean Colombian string
  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString('es-CO', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (e) {
      return isoString;
    }
  };

  // Fetch accounts and history data
  const refreshData = async () => {
    try {
      const [accRes, histRes] = await Promise.all([
        fetch('/api/accounts'),
        fetch('/api/history')
      ]);

      if (!accRes.ok) throw new Error('Error al obtener el estado de las cuentas');
      if (!histRes.ok) throw new Error('Error al obtener el historial de transacciones');

      const accData = await accRes.json();
      const histData = await histRes.json();

      setAccounts(accData);
      setHistory(histData);

      // Set initial form states if they are empty
      if (accData.length > 0) {
        if (!sourceAccountId) {
          setSourceAccountId(accData[0].id);
        }
        if (!destinationAccountId) {
          const secondAcc = accData.find((a: Account) => a.id !== accData[0].id);
          if (secondAcc) {
            setDestinationAccountId(secondAcc.id);
          } else {
            setDestinationAccountId(accData[0].id);
          }
        }
      }
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  // MFA Countdown timer effect
  useEffect(() => {
    if (!isMfaOpen || mfaTimer <= 0) return;

    const interval = setInterval(() => {
      setMfaTimer((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isMfaOpen, mfaTimer]);

  // Client-side Form Validation
  const isSameAccount = sourceAccountId !== '' && sourceAccountId === destinationAccountId;
  const parsedAmount = parseFloat(amount);
  const isAmountPositive = !isNaN(parsedAmount) && parsedAmount > 0;

  const selectedSourceAccount = accounts.find(a => a.id === sourceAccountId);
  const availableBalance = selectedSourceAccount ? parseFloat(selectedSourceAccount.balance) : 0;
  const hasSufficientFunds = !isNaN(parsedAmount) && parsedAmount <= availableBalance;

  const isFormValid =
    sourceAccountId !== '' &&
    destinationAccountId !== '' &&
    !isSameAccount &&
    isAmountPositive &&
    hasSufficientFunds;

  // Handle Initiating a Transfer
  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTransferError(null);
    setSuccessMsg(null);

    if (!isFormValid) return;

    const srcAcc = accounts.find(a => a.id === sourceAccountId);
    const destAcc = accounts.find(a => a.id === destinationAccountId);

    try {
      const res = await fetch('/api/transfers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          source_account_id: sourceAccountId,
          destination_account_id: destinationAccountId,
          amount: amount
        })
      });

      if (res.status === 202) {
        const data = await res.json();
        // Setup MFA Modal details
        setActiveTransfer({
          sourceName: srcAcc?.name || 'Cuenta Corriente',
          destName: destAcc?.name || 'Cuenta de Ahorros',
          amount: amount
        });
        setMfaTransferId(data.transfer_id);
        setMfaCode('');
        setMfaTimer(300); // 5 minutes
        setMfaError(null);
        setIsMfaOpen(true);
      } else if (res.status === 200) {
        setSuccessMsg(`¡Transferencia de ${formatCOP(amount)} realizada con éxito!`);
        setAmount('');
        await refreshData();
      } else {
        const data = await res.json();
        setTransferError(data.detail || 'Error al procesar la transferencia');
      }
    } catch (err: any) {
      setTransferError('No se pudo conectar con el servidor para iniciar la transferencia');
    }
  };

  // Handle Confirming the MFA Verification Code
  const handleConfirmMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    setMfaError(null);

    if (mfaCode.length !== 6) {
      setMfaError('El código de verificación debe ser de 6 dígitos');
      return;
    }

    if (!mfaTransferId) return;

    try {
      const res = await fetch(`/api/transfers/${mfaTransferId}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: mfaCode
        })
      });

      if (res.status === 200) {
        setSuccessMsg(`¡MFA Verificado! Transferencia de ${formatCOP(activeTransfer?.amount || '0')} completada.`);
        setIsMfaOpen(false);
        setMfaTransferId(null);
        setAmount('');
        await refreshData();
      } else {
        const data = await res.json();
        const errMsg = data.detail || 'Código de seguridad incorrecto';

        // Check if the error returned indicates failure or expiration
        const lowerErr = errMsg.toLowerCase();
        if (
          lowerErr.includes('expired') ||
          lowerErr.includes('expirado') ||
          lowerErr.includes('failed') ||
          lowerErr.includes('insufficient') ||
          lowerErr.includes('fondos') ||
          lowerErr.includes('depleted')
        ) {
          setTransferError(`La transferencia falló: ${errMsg}`);
          setIsMfaOpen(false);
          setMfaTransferId(null);
          await refreshData();
        } else {
          // Normal validation error (incorrect code, allow retry)
          setMfaError(errMsg);
          setMfaCode('');
        }
      }
    } catch (err: any) {
      setMfaError('Error de red al intentar confirmar la transacción');
    }
  };

  // Handle Cancelling or Closing MFA modal
  const handleCancelMfa = () => {
    setIsMfaOpen(false);
    setMfaTransferId(null);
    refreshData();
  };

  // Filtered History
  const filteredHistory = history.filter(tx => {
    if (filter === 'All') return true;
    if (filter === 'Checking') {
      return tx.source_account_id === 'acc_checking' || tx.destination_account_id === 'acc_checking';
    }
    if (filter === 'Savings') {
      return tx.source_account_id === 'acc_savings' || tx.destination_account_id === 'acc_savings';
    }
    return true;
  });

  return (
    <div className="app-container">
      {/* Header Section */}
      <header className="header-card">
        <div className="header-brand">
          <h1>Shift Bank</h1>
          <p>Banca digital segura y veloz</p>
        </div>
        <div className="user-profile">
          <div className="user-name">{user.name}</div>
          <div className="user-id">ID: {user.id}</div>
        </div>
      </header>

      {/* Global Connection/Fetch Error Alert */}
      {errorMsg && (
        <div className="alert alert-error">
          <span>⚠️ {errorMsg}</span>
          <button style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} onClick={refreshData}>Reintentar</button>
        </div>
      )}

      {/* Action Success Alert */}
      {successMsg && (
        <div className="alert alert-success">
          <span>✅ {successMsg}</span>
          <button style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold', color: 'inherit' }} onClick={() => setSuccessMsg(null)}>✕</button>
        </div>
      )}

      {/* Transfer Fail/Validation Error Alert */}
      {transferError && (
        <div className="alert alert-error">
          <span>❌ {transferError}</span>
          <button style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold', color: 'inherit' }} onClick={() => setTransferError(null)}>✕</button>
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <h2>Cargando su panel de control...</h2>
          <p>Por favor espere un momento.</p>
        </div>
      ) : (
        <>
          <div className="dashboard-grid">
            {/* Accounts Summary Panel */}
            <section className="accounts-section">
              <div className="accounts-grid">
                {accounts.map(acc => (
                  <div
                    key={acc.id}
                    className={`account-card ${acc.id === 'acc_checking' ? 'account-checking' : 'account-savings'}`}
                  >
                    <div>
                      <div className="account-type">
                        {acc.id === 'acc_checking' ? 'Cuenta Corriente' : 'Cuenta de Ahorros'}
                      </div>
                      <div className="account-name">{acc.name}</div>
                    </div>
                    <div>
                      <div className="account-balance">{formatCOP(acc.balance)}</div>
                      <div className="account-id-label">Nº {acc.id}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Transactions History Ledger */}
              <div className="card">
                <div className="history-header">
                  <h2 className="history-title">Historial de Transacciones</h2>
                  <div className="filter-tabs">
                    <button
                      className={`filter-tab ${filter === 'All' ? 'active' : ''}`}
                      onClick={() => setFilter('All')}
                    >
                      Todos
                    </button>
                    <button
                      className={`filter-tab ${filter === 'Checking' ? 'active' : ''}`}
                      onClick={() => setFilter('Checking')}
                    >
                      Corriente
                    </button>
                    <button
                      className={`filter-tab ${filter === 'Savings' ? 'active' : ''}`}
                      onClick={() => setFilter('Savings')}
                    >
                      Ahorros
                    </button>
                  </div>
                </div>

                {filteredHistory.length === 0 ? (
                  <div className="empty-state" style={{ padding: '24px 0' }}>
                    <p>No se encontraron movimientos para el filtro seleccionado.</p>
                  </div>
                ) : (
                  <div className="ledger-list">
                    {filteredHistory.map(tx => {
                      // Determine if outbound or inbound based on filter context
                      let displayType: 'in' | 'out' | 'transfer' = 'out';
                      if (filter === 'Checking') {
                        displayType = tx.source_account_id === 'acc_checking' ? 'out' : 'in';
                      } else if (filter === 'Savings') {
                        displayType = tx.source_account_id === 'acc_savings' ? 'out' : 'in';
                      } else {
                        // For 'All', we default outbound from the source perspective
                        displayType = 'transfer';
                      }

                      return (
                        <div key={tx.id} className="ledger-item">
                          <div className="ledger-left">
                            <div className={`tx-icon-container ${displayType === 'in' ? 'tx-icon-in' : 'tx-icon-out'}`}>
                              {displayType === 'in' ? '↓' : displayType === 'out' ? '↑' : '⇄'}
                            </div>
                            <div className="tx-details">
                              <div className="tx-accounts">
                                {tx.source_account_name} ➔ {tx.destination_account_name}
                              </div>
                              <div className="tx-meta">
                                <span className="tx-id">Ref: {tx.id}</span> • {formatDate(tx.timestamp)}
                              </div>
                            </div>
                          </div>
                          <div className="ledger-right">
                            <span className={`tx-amount ${displayType === 'in' ? 'amount-positive' : displayType === 'out' ? 'amount-negative' : ''}`}>
                              {displayType === 'in' ? '+' : displayType === 'out' ? '-' : ''} {formatCOP(tx.amount)}
                            </span>
                            <span className={`badge badge-${tx.status.toLowerCase().replace('_', '-')}`}>
                              {tx.status === 'PENDING_MFA' ? 'Pendiente MFA' : tx.status}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </section>

            {/* Transfer Money Form Section */}
            <aside>
              <div className="card">
                <h2 className="card-title">Transferir Dinero</h2>
                <form onSubmit={handleTransferSubmit}>
                  {/* Source Account Selector */}
                  <div className="form-group">
                    <label htmlFor="source-account">Cuenta de Origen</label>
                    <select
                      id="source-account"
                      className="form-control"
                      value={sourceAccountId}
                      onChange={(e) => setSourceAccountId(e.target.value)}
                    >
                      {accounts.map(acc => (
                        <option key={acc.id} value={acc.id}>
                          {acc.name} ({formatCOP(acc.balance)})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Destination Account Selector */}
                  <div className="form-group">
                    <label htmlFor="dest-account">Cuenta de Destino</label>
                    <select
                      id="dest-account"
                      className="form-control"
                      value={destinationAccountId}
                      onChange={(e) => setDestinationAccountId(e.target.value)}
                    >
                      {accounts.map(acc => (
                        <option key={acc.id} value={acc.id} disabled={acc.id === sourceAccountId}>
                          {acc.name} {acc.id === sourceAccountId ? ' (Misma de Origen)' : ''}
                        </option>
                      ))}
                    </select>
                    {isSameAccount && (
                      <span className="warning-text">
                        ⚠️ Las cuentas de origen y destino deben ser diferentes.
                      </span>
                    )}
                  </div>

                  {/* Amount Field */}
                  <div className="form-group">
                    <label htmlFor="transfer-amount">Monto a Transferir (COP)</label>
                    <input
                      id="transfer-amount"
                      type="number"
                      step="any"
                      min="0.01"
                      className="form-control"
                      placeholder="Ej: 1500000"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                    />
                    {amount !== '' && !isAmountPositive && (
                      <span className="warning-text">
                        ⚠️ El monto debe ser mayor a 0.
                      </span>
                    )}
                    {amount !== '' && isAmountPositive && !hasSufficientFunds && (
                      <span className="warning-text">
                        ⚠️ Fondos insuficientes en la cuenta seleccionada (Disponible: {formatCOP(availableBalance)}).
                      </span>
                    )}
                  </div>

                  {/* Transfer Action Button */}
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!isFormValid}
                    style={{ marginTop: '10px' }}
                  >
                    Transferir
                  </button>
                </form>
              </div>
            </aside>
          </div>

          {/* MFA Verification Overlay Modal */}
          <div className={`modal-overlay ${isMfaOpen ? 'open' : ''}`}>
            <div className="modal-window">
              <h2 className="modal-title">Confirmación de Seguridad (MFA)</h2>
              <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '20px' }}>
                Se requiere autorización adicional para transferencias iguales o superiores a {formatCOP(1000000)}.
              </p>

              {activeTransfer && (
                <div className="modal-summary">
                  <div className="modal-summary-item">
                    <span className="modal-summary-label">Monto:</span>
                    <span className="modal-summary-value" style={{ color: '#1e3a8a', fontWeight: 'bold' }}>
                      {formatCOP(activeTransfer.amount)}
                    </span>
                  </div>
                  <div className="modal-summary-item">
                    <span className="modal-summary-label">Origen:</span>
                    <span className="modal-summary-value">{activeTransfer.sourceName}</span>
                  </div>
                  <div className="modal-summary-item">
                    <span className="modal-summary-label">Destino:</span>
                    <span className="modal-summary-value">{activeTransfer.destName}</span>
                  </div>
                </div>
              )}

              {/* MFA Countdown Timer UI */}
              <div className="timer-container">
                <div className={`timer-circle ${mfaTimer <= 60 ? 'warning' : ''}`}>
                  {mfaTimer > 0 ? (
                    `${Math.floor(mfaTimer / 60)}:${String(mfaTimer % 60).padStart(2, '0')}`
                  ) : (
                    '00:00'
                  )}
                </div>
                <div className="timer-label">
                  {mfaTimer > 0 ? 'Tiempo restante para confirmar' : 'Sesión de verificación expirada'}
                </div>
              </div>

              {mfaTimer <= 0 ? (
                <div>
                  <div className="alert alert-error" style={{ textAlign: 'left', marginBottom: '24px' }}>
                    ⚠️ El tiempo límite de 5 minutos para ingresar el código MFA ha caducado. La transacción se marcará como EXPIRED.
                  </div>
                  <button className="btn btn-secondary" onClick={handleCancelMfa}>
                    Cerrar y Actualizar
                  </button>
                </div>
              ) : (
                <form onSubmit={handleConfirmMfa}>
                  <div className="form-group" style={{ textAlign: 'left' }}>
                    <label htmlFor="mfa-code" style={{ textAlign: 'center', display: 'block', fontSize: '15px' }}>
                      Ingrese el código de verificación de 6 dígitos
                    </label>
                    <input
                      id="mfa-code"
                      type="text"
                      maxLength={6}
                      pattern="\d{6}"
                      className="form-control"
                      placeholder="Ej: 123456"
                      style={{
                        textAlign: 'center',
                        fontSize: '24px',
                        letterSpacing: '8px',
                        fontWeight: 'bold',
                        padding: '10px'
                      }}
                      value={mfaCode}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, ''); // digit-only
                        setMfaCode(val);
                      }}
                      autoFocus
                    />
                    {mfaError && (
                      <span className="warning-text" style={{ justifyContent: 'center', marginTop: '10px', fontSize: '14px' }}>
                        ⚠️ {mfaError}
                      </span>
                    )}
                  </div>

                  <div className="modal-actions">
                    <button type="button" className="btn btn-secondary" onClick={handleCancelMfa}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={mfaCode.length !== 6}>
                      Confirmar
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
