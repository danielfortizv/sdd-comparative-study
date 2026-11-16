// Formulario de transferencia (Requisitos 3.1, 3.2, 6.1, 6.2).
// Selección de origen/destino, monto y descripción. Evita en la UI que destino = origen,
// pero la validación autoritativa es del backend.

import { useState } from "react";

import { ApiRequestError, createTransfer } from "../api/client";
import type { AccountKind, CreateTransferResponse } from "../types";

interface Props {
  onCompleted: () => void;
  onPendingMfa: (reference: string, expiresAt: string, amount: string) => void;
}

export function TransferForm({ onCompleted, onPendingMfa }: Props) {
  const [from, setFrom] = useState<AccountKind>("checking");
  const [to, setTo] = useState<AccountKind>("savings");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleFromChange(value: AccountKind) {
    setFrom(value);
    // Evitar en la UI que origen = destino.
    if (value === to) {
      setTo(value === "checking" ? "savings" : "checking");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      const res: CreateTransferResponse = await createTransfer({
        from,
        to,
        amount: amount.trim(),
        description: description.trim(),
      });
      if (res.status === "PENDING_MFA" && res.reference && res.expires_at) {
        onPendingMfa(res.reference, res.expires_at, amount.trim());
      } else if (res.status === "COMPLETED") {
        setInfo("Transferencia completada.");
        setAmount("");
        setDescription("");
        onCompleted();
      }
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError("No se pudo completar la solicitud.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Nueva transferencia</h2>
      <form onSubmit={handleSubmit} className="transfer-form">
        <label>
          Desde
          <select value={from} onChange={(e) => handleFromChange(e.target.value as AccountKind)}>
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
          </select>
        </label>
        <label>
          Hacia
          <select value={to} onChange={(e) => setTo(e.target.value as AccountKind)}>
            <option value="checking" disabled={from === "checking"}>
              Checking
            </option>
            <option value="savings" disabled={from === "savings"}>
              Savings
            </option>
          </select>
        </label>
        <label>
          Monto (COP)
          <input
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </label>
        <label>
          Descripción
          <input
            type="text"
            placeholder="Opcional"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Enviando..." : "Transferir"}
        </button>
      </form>
      {error && <p className="message error">{error}</p>}
      {info && <p className="message success">{info}</p>}
    </section>
  );
}
