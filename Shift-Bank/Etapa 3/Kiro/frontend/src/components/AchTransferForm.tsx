// Formulario de transferencia ACH a terceros (Requisitos 2.4, 7.1, 7.2, 7.3; ACH-09, ACH-10).
// Permite elegir un beneficiario guardado o capturar uno ad hoc (con opción de guardarlo),
// valida el formato de routing/cuenta de forma inmediata bloqueando el envío (A05, A06), y para
// montos sensibles (≥ umbral) reutiliza MfaDialog confirmando con `confirmAchMfa`.

import { useState } from "react";

import { ApiRequestError, confirmAchMfa, createAch } from "../api/client";
import type { AccountKind, Beneficiary, CreateAchRequest } from "../types";
import { MfaDialog } from "./MfaDialog";
import { validateAccountNumber, validateRouting } from "./beneficiaryValidation";

interface Props {
  beneficiaries: Beneficiary[];
  onCompleted: () => void;
}

type Mode = "saved" | "adhoc";

interface PendingAch {
  reference: string;
  expiresAt: string;
  amount: string;
}

export function AchTransferForm({ beneficiaries, onCompleted }: Props) {
  const [mode, setMode] = useState<Mode>(beneficiaries.length > 0 ? "saved" : "adhoc");
  const [beneficiaryId, setBeneficiaryId] = useState("");
  const [from, setFrom] = useState<AccountKind>("checking");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  // Datos ad hoc.
  const [name, setName] = useState("");
  const [bank, setBank] = useState("");
  const [routing, setRouting] = useState("");
  const [account, setAccount] = useState("");
  const [saveAdhoc, setSaveAdhoc] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingAch | null>(null);

  // Validación inmediata del beneficiario ad hoc (Requisito 7.3; ACH-10, A05, A06).
  const routingError = mode === "adhoc" && routing ? validateRouting(routing) : null;
  const accountError = mode === "adhoc" && account ? validateAccountNumber(account) : null;

  const adhocValid =
    name.trim() !== "" &&
    bank.trim() !== "" &&
    validateRouting(routing) === null &&
    validateAccountNumber(account) === null;

  const destinationValid = mode === "saved" ? beneficiaryId !== "" : adhocValid;
  const canSubmit = destinationValid && amount.trim() !== "" && !submitting;

  function statusMessage(status: string): string {
    switch (status) {
      case "pending":
        return "Transferencia ACH autorizada (pending): el monto fue debitado.";
      case "settled":
        return "Transferencia ACH liquidada (settled).";
      case "pending_auth":
        return "La transferencia ACH requiere verificación MFA.";
      default:
        return `Estado de la transferencia ACH: ${status}.`;
    }
  }

  function resetForm() {
    setAmount("");
    setDescription("");
    if (mode === "adhoc") {
      setName("");
      setBank("");
      setRouting("");
      setAccount("");
      setSaveAdhoc(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    if (!canSubmit) {
      setError("Completa y corrige los datos antes de enviar.");
      return;
    }
    const payload: CreateAchRequest = {
      amount: amount.trim(),
      description: description.trim() || undefined,
      from,
    };
    if (mode === "saved") {
      payload.beneficiary_id = beneficiaryId;
    } else {
      payload.adhoc = {
        name: name.trim(),
        bank: bank.trim(),
        routing_number: routing.trim(),
        account_number: account.trim(),
      };
      payload.save_adhoc = saveAdhoc;
    }
    setSubmitting(true);
    try {
      const res = await createAch(payload);
      if (res.status === "pending_auth" && res.reference && res.expires_at) {
        // Monto sensible: abrir MFA (misma UI que internas), confirmando vía ACH.
        setPending({ reference: res.reference, expiresAt: res.expires_at, amount: amount.trim() });
      } else {
        setInfo(statusMessage(res.status));
        resetForm();
        onCompleted();
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo crear la transferencia ACH.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleMfaCompleted() {
    setPending(null);
    setInfo("Transferencia ACH autorizada (pending): el monto fue debitado.");
    resetForm();
    onCompleted();
  }

  return (
    <section className="card" aria-label="Transferencia ACH">
      <h2>Transferencia ACH (a terceros)</h2>
      <p className="message">
        Envía dinero a un beneficiario externo. A diferencia de una transferencia interna entre tus
        cuentas, una ACH requiere seleccionar un beneficiario guardado o capturar uno ad hoc.
      </p>

      <form onSubmit={handleSubmit} className="transfer-form">
        <fieldset className="ach-mode">
          <legend>Beneficiario</legend>
          <label className="radio">
            <input
              type="radio"
              name="ach-mode"
              checked={mode === "saved"}
              onChange={() => setMode("saved")}
              disabled={beneficiaries.length === 0}
            />
            {/* no space */}Guardado
          </label>
          <label className="radio">
            <input
              type="radio"
              name="ach-mode"
              checked={mode === "adhoc"}
              onChange={() => setMode("adhoc")}
            />
            {/* no space */}Ad hoc
          </label>
        </fieldset>

        {mode === "saved" ? (
          <label>
            Beneficiario guardado{/* no space */}
            <select value={beneficiaryId} onChange={(e) => setBeneficiaryId(e.target.value)}>
              <option value="">Selecciona un beneficiario…</option>
              {beneficiaries.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} · {b.bank} · {b.account_masked}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <label>
              Nombre{/* no space */}
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre del beneficiario"
              />
            </label>
            <label>
              Banco{/* no space */}
              <input
                type="text"
                value={bank}
                onChange={(e) => setBank(e.target.value)}
                placeholder="Banco"
              />
            </label>
            <label>
              Número de routing{/* no space */}
              <input
                type="text"
                inputMode="numeric"
                value={routing}
                onChange={(e) => setRouting(e.target.value)}
                placeholder="9 dígitos"
                aria-invalid={routingError !== null}
              />
              {routingError && <span className="message error">{routingError}</span>}
            </label>
            <label>
              Número de cuenta{/* no space */}
              <input
                type="text"
                inputMode="numeric"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                placeholder="4 a 17 dígitos"
                aria-invalid={accountError !== null}
              />
              {accountError && <span className="message error">{accountError}</span>}
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={saveAdhoc}
                onChange={(e) => setSaveAdhoc(e.target.checked)}
              />
              {/* no space */}Guardar este beneficiario para futuras transferencias
            </label>
          </>
        )}

        <label>
          Desde{/* no space */}
          <select value={from} onChange={(e) => setFrom(e.target.value as AccountKind)}>
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
          </select>
        </label>
        <label>
          Monto (COP){/* no space */}
          <input
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </label>
        <label>
          Descripción{/* no space */}
          <input
            type="text"
            placeholder="Opcional"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <button type="submit" disabled={!canSubmit}>
          {submitting ? "Enviando..." : "Enviar ACH"}
        </button>
      </form>

      {error && <p className="message error">{error}</p>}
      {info && <p className="message success">{info}</p>}

      {pending && (
        <MfaDialog
          reference={pending.reference}
          expiresAt={pending.expiresAt}
          amount={pending.amount}
          confirm={confirmAchMfa}
          onCompleted={handleMfaCompleted}
          onDismiss={() => setPending(null)}
        />
      )}
    </section>
  );
}
