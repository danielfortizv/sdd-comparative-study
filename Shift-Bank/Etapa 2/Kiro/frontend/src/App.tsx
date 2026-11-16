// Orquestación de la app (Requisitos 2.1, 5.1, 6.4, 7.3, 7.1, 16.2).
// Mantiene cuentas, historial y el pending de MFA; recarga datos tras cada operación.
// Navegación por secciones (tabs/paneles) sin router nuevo, preservando la
// experiencia interna existente (Req. 16.2; diseño §Frontend, UI-1; contrato A21).

import { useCallback, useEffect, useState } from "react";

import {
  getAccounts,
  getBeneficiaries,
  getHistory,
  getLimits,
  getRecurring,
} from "./api/client";
import { AccountsPanel } from "./components/AccountsPanel";
import { AchTransferForm } from "./components/AchTransferForm";
import { BeneficiariesPanel } from "./components/BeneficiariesPanel";
import { HistoryList } from "./components/HistoryList";
import { LimitsPanel } from "./components/LimitsPanel";
import { MfaDialog } from "./components/MfaDialog";
import { RecurringPanel } from "./components/RecurringPanel";
import { TransferForm } from "./components/TransferForm";
import type {
  Account,
  Beneficiary,
  LimitsResponse,
  RecurringSchedule,
  TransferHistoryItem,
} from "./types";

interface PendingMfa {
  reference: string;
  expiresAt: string;
  amount: string;
}

// Secciones de navegación. "Transferencias" e "Historial" preservan la
// experiencia interna de la Etapa 1; las demás se completan en tareas 37–39.
type Section =
  | "transfers"
  | "ach"
  | "beneficiaries"
  | "recurring"
  | "limits"
  | "history";

const SECTIONS: ReadonlyArray<{ id: Section; label: string }> = [
  { id: "transfers", label: "Transferencias" },
  { id: "ach", label: "ACH" },
  { id: "beneficiaries", label: "Beneficiarios" },
  { id: "recurring", label: "Recurrentes" },
  { id: "limits", label: "Límites" },
  { id: "history", label: "Historial" },
];

export default function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [history, setHistory] = useState<TransferHistoryItem[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [recurring, setRecurring] = useState<RecurringSchedule[]>([]);
  const [limits, setLimits] = useState<LimitsResponse | null>(null);
  const [pending, setPending] = useState<PendingMfa | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [section, setSection] = useState<Section>("transfers");

  const refresh = useCallback(async () => {
    try {
      const [acc, hist, bens, rec, lim] = await Promise.all([
        getAccounts(),
        getHistory(),
        getBeneficiaries(),
        getRecurring(),
        getLimits(),
      ]);
      setAccounts(acc.accounts);
      setHistory(hist.transfers);
      setBeneficiaries(bens.beneficiaries);
      setRecurring(rec.recurring);
      setLimits(lim);
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

      <nav className="tabs" role="tablist" aria-label="Secciones">
        {SECTIONS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={section === id}
            aria-controls={`panel-${id}`}
            className={section === id ? "tab tab-active" : "tab"}
            onClick={() => setSection(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {loadError && <p className="message error">{loadError}</p>}

      {/* Transferencias (interno): preserva AccountsPanel + TransferForm tal cual. */}
      {section === "transfers" && (
        <main
          className="layout"
          role="tabpanel"
          id="panel-transfers"
          aria-labelledby="tab-transfers"
        >
          <AccountsPanel accounts={accounts} />
          <TransferForm onCompleted={refresh} onPendingMfa={handlePendingMfa} />
        </main>
      )}

      {/* Historial: preserva HistoryList tal cual. */}
      {section === "history" && (
        <main
          className="layout"
          role="tabpanel"
          id="panel-history"
          aria-labelledby="tab-history"
        >
          <HistoryList transfers={history} />
        </main>
      )}

      {/* Secciones nuevas (tareas 37–39): marcadores de posición por ahora. */}
      {section === "ach" && (
        <main className="layout" role="tabpanel" id="panel-ach" aria-labelledby="tab-ach">
          <AccountsPanel accounts={accounts} />
          <AchTransferForm beneficiaries={beneficiaries} onCompleted={refresh} />
        </main>
      )}

      {section === "beneficiaries" && (
        <main
          className="layout"
          role="tabpanel"
          id="panel-beneficiaries"
          aria-labelledby="tab-beneficiaries"
        >
          <BeneficiariesPanel beneficiaries={beneficiaries} onChanged={refresh} />
        </main>
      )}

      {section === "recurring" && (
        <main
          className="layout"
          role="tabpanel"
          id="panel-recurring"
          aria-labelledby="tab-recurring"
        >
          <RecurringPanel
            schedules={recurring}
            beneficiaries={beneficiaries}
            onChanged={refresh}
          />
        </main>
      )}

      {section === "limits" && (
        <main
          className="layout"
          role="tabpanel"
          id="panel-limits"
          aria-labelledby="tab-limits"
        >
          <LimitsPanel limits={limits} onChanged={refresh} />
        </main>
      )}

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
