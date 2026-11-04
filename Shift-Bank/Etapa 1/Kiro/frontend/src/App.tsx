// Orquestación de la app (Requisitos 2.1, 5.1, 6.4, 7.3).
// Mantiene cuentas, historial y el pending de MFA; recarga datos tras cada operación.

import { useCallback, useEffect, useState } from "react";

import { getAccounts, getHistory } from "./api/client";
import { AccountsPanel } from "./components/AccountsPanel";
import { HistoryList } from "./components/HistoryList";
import { MfaDialog } from "./components/MfaDialog";
import { TransferForm } from "./components/TransferForm";
import type { Account, TransferHistoryItem } from "./types";

interface PendingMfa {
  reference: string;
  expiresAt: string;
  amount: string;
}

export default function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [history, setHistory] = useState<TransferHistoryItem[]>([]);
  const [pending, setPending] = useState<PendingMfa | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [acc, hist] = await Promise.all([getAccounts(), getHistory()]);
      setAccounts(acc.accounts);
      setHistory(hist.transfers);
      setLoadError(null);
    } catch {
      setLoadError("No se pudo cargar la información. ¿Está el backend en ejecución?");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function handlePendingMfa(reference: string, expiresAt: string, amount: string) {
    setPending({ reference, expiresAt, amount });
  }

  async function handleMfaCompleted() {
    setPending(null);
    await refresh();
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Shift Bank</h1>
      </header>

      {loadError && <p className="message error">{loadError}</p>}

      <main className="layout">
        <AccountsPanel accounts={accounts} />
        <TransferForm onCompleted={refresh} onPendingMfa={handlePendingMfa} />
        <HistoryList transfers={history} />
      </main>

      {pending && (
        <MfaDialog
          reference={pending.reference}
          expiresAt={pending.expiresAt}
          amount={pending.amount}
          onCompleted={handleMfaCompleted}
          onDismiss={() => setPending(null)}
        />
      )}
    </div>
  );
}
