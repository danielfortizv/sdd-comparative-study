// Gestión de beneficiarios guardados (Requisitos 1.1, 1.5, 1.6, 2.1–2.4; ACH-01, ACH-02, D05).
// Lista beneficiarios con la cuenta enmascarada y el routing visible (F14), permite crear uno
// nuevo con validación inmediata de formato (bloquea el envío) y eliminarlo lógicamente.

import { useState } from "react";

import {
  ApiRequestError,
  createBeneficiary,
  deleteBeneficiary,
} from "../api/client";
import type { Beneficiary } from "../types";
import { validateAccountNumber, validateRouting } from "./beneficiaryValidation";

interface Props {
  beneficiaries: Beneficiary[];
  onChanged: () => void;
}

export function BeneficiariesPanel({ beneficiaries, onChanged }: Readonly<Props>) {
  const [name, setName] = useState("");
  const [bank, setBank] = useState("");
  const [routing, setRouting] = useState("");
  const [account, setAccount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Validación de formato inmediata (Requisito 2.4; ACH-10). Se recalcula en cada render para
  // mostrar el error y bloquear el envío mientras algo sea inválido.
  const routingError = routing ? validateRouting(routing) : null;
  const accountError = account ? validateAccountNumber(account) : null;

  const canSubmit =
    name.trim() !== "" &&
    bank.trim() !== "" &&
    validateRouting(routing) === null &&
    validateAccountNumber(account) === null &&
    !submitting;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    // Doble comprobación: nunca enviar con formato inválido (A05, A06).
    if (!canSubmit) {
      setError("Corrige los datos del beneficiario antes de guardarlo.");
      return;
    }
    setSubmitting(true);
    try {
      await createBeneficiary({
        name: name.trim(),
        bank: bank.trim(),
        routing_number: routing.trim(),
        account_number: account.trim(),
      });
      setInfo("Beneficiario guardado.");
      setName("");
      setBank("");
      setRouting("");
      setAccount("");
      onChanged();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo guardar el beneficiario.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    setInfo(null);
    setDeletingId(id);
    try {
      await deleteBeneficiary(id);
      setInfo("Beneficiario eliminado.");
      onChanged();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo eliminar el beneficiario.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="card" aria-label="Beneficiarios">
      <h2>Beneficiarios</h2>

      {beneficiaries.length === 0 ? (
        <p className="message">No hay beneficiarios guardados.</p>
      ) : (
        <ul className="beneficiary-list">
          {beneficiaries.map((b) => (
            <li className="beneficiary-item" key={b.id}>
              <div className="beneficiary-main">
                <span className="beneficiary-name">{b.name}</span>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void handleDelete(b.id)}
                  disabled={deletingId === b.id}
                >
                  {deletingId === b.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
              <div className="beneficiary-meta">
                <span>{b.bank}</span>
                <span className="beneficiary-account">
                  Cuenta {b.account_masked} · Routing {b.routing_number}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreate} className="transfer-form beneficiary-form">
        <h3>Nuevo beneficiario</h3>
        <label>
          Nombre
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre del beneficiario"
          />
        </label>
        <label>
          Banco
          <input
            type="text"
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            placeholder="Banco"
          />
        </label>
        <label>
          Número de routing
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
          Número de cuenta
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
        <button type="submit" disabled={!canSubmit}>
          {submitting ? "Guardando..." : "Guardar beneficiario"}
        </button>
      </form>

      {error && <p className="message error">{error}</p>}
      {info && <p className="message success">{info}</p>}
    </section>
  );
}
