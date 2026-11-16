// Panel de pagos recurrentes (Requisitos 12.1, 12.2, 12.3; contrato REC-12, A21).
// Lista los schedules con su estado y próxima fecha de vencimiento (`next_run_at`), permite
// crear uno nuevo (interno o ACH) y ejecutar las acciones de pausar/reanudar/cancelar, cada una
// con retroalimentación de carga/éxito/error. Para montos sensibles (≥ umbral) la creación exige
// un código MFA, que se captura en línea porque el backend acepta `mfa_code` en POST /api/recurring.

import { useState } from "react";

import {
  ApiRequestError,
  cancelRecurring,
  createRecurring,
  pauseRecurring,
  resumeRecurring,
} from "../api/client";
import type {
  AccountKind,
  Beneficiary,
  CreateRecurringRequest,
  RecurringFrequency,
  RecurringSchedule,
  RecurringStatus,
  TransferType,
} from "../types";
import { validateAccountNumber, validateRouting } from "./beneficiaryValidation";

interface Props {
  schedules: RecurringSchedule[];
  beneficiaries: Beneficiary[];
  onChanged: () => void;
}

type BeneficiaryMode = "saved" | "adhoc";

const STATUS_LABEL: Record<RecurringStatus, string> = {
  active: "Activo",
  paused: "Pausado",
  cancelled: "Cancelado",
};

const FREQUENCY_LABEL: Record<RecurringFrequency, string> = {
  daily: "Diaria",
  weekly: "Semanal",
  monthly: "Mensual",
};

// Formatea la próxima fecha de vencimiento (ISO-8601 UTC) de forma legible, cayendo al valor
// crudo si el string no es una fecha válida.
function formatNextRun(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function RecurringPanel({ schedules, beneficiaries, onChanged }: Props) {
  // Campos comunes del formulario de creación.
  const [type, setType] = useState<TransferType>("internal");
  const [frequency, setFrequency] = useState<RecurringFrequency>("monthly");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [startAt, setStartAt] = useState(""); // opcional (REC-04)
  const [mfaCode, setMfaCode] = useState(""); // opcional, requerido si el monto es sensible (REC-09)

  // Interno: origen/destino.
  const [from, setFrom] = useState<AccountKind>("checking");
  const [to, setTo] = useState<AccountKind>("savings");

  // ACH: beneficiario guardado o ad hoc.
  const [beneficiaryMode, setBeneficiaryMode] = useState<BeneficiaryMode>(
    beneficiaries.length > 0 ? "saved" : "adhoc"
  );
  const [beneficiaryId, setBeneficiaryId] = useState("");
  const [adName, setAdName] = useState("");
  const [adBank, setAdBank] = useState("");
  const [adRouting, setAdRouting] = useState("");
  const [adAccount, setAdAccount] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Feedback por schedule: acción en curso y mensajes de resultado por id.
  const [actingId, setActingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<Record<string, string>>({});
  const [actionInfo, setActionInfo] = useState<Record<string, string>>({});

  // Validación inmediata del beneficiario ad hoc (bloquea el envío; ACH-10).
  const routingError =
    type === "ach" && beneficiaryMode === "adhoc" && adRouting
      ? validateRouting(adRouting)
      : null;
  const accountError =
    type === "ach" && beneficiaryMode === "adhoc" && adAccount
      ? validateAccountNumber(adAccount)
      : null;

  const adhocValid =
    adName.trim() !== "" &&
    adBank.trim() !== "" &&
    validateRouting(adRouting) === null &&
    validateAccountNumber(adAccount) === null;

  const destinationValid =
    type === "internal"
      ? from !== to
      : beneficiaryMode === "saved"
        ? beneficiaryId !== ""
        : adhocValid;

  const canSubmit = destinationValid && amount.trim() !== "" && !submitting;

  function handleFromChange(value: AccountKind) {
    setFrom(value);
    if (value === to) {
      setTo(value === "checking" ? "savings" : "checking");
    }
  }

  function resetForm() {
    setAmount("");
    setDescription("");
    setStartAt("");
    setMfaCode("");
    setBeneficiaryId("");
    setAdName("");
    setAdBank("");
    setAdRouting("");
    setAdAccount("");
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    if (!canSubmit) {
      setError("Completa y corrige los datos del schedule antes de crearlo.");
      return;
    }
    const payload: CreateRecurringRequest = {
      type,
      amount: amount.trim(),
      frequency,
      description: description.trim() || undefined,
      start_at: startAt.trim() || undefined,
      mfa_code: mfaCode.trim() || undefined,
    };
    if (type === "internal") {
      payload.from = from;
      payload.to = to;
    } else if (beneficiaryMode === "saved") {
      payload.beneficiary_id = beneficiaryId;
    } else {
      payload.adhoc = {
        name: adName.trim(),
        bank: adBank.trim(),
        routing_number: adRouting.trim(),
        account_number: adAccount.trim(),
      };
    }
    setSubmitting(true);
    try {
      const res = await createRecurring(payload);
      setInfo(
        `Schedule creado (${STATUS_LABEL[res.status]}). Próxima ejecución: ${formatNextRun(
          res.next_run_at
        )}.`
      );
      resetForm();
      onChanged();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.code === "MFA_REQUIRED") {
          setError("Este monto requiere un código MFA para autorizar el schedule.");
        } else if (err.code === "INVALID_MFA_CODE") {
          setError("Código MFA incorrecto. Verifícalo e inténtalo de nuevo.");
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo crear el pago recurrente.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // Ejecuta una acción de ciclo de vida sobre un schedule con feedback por id.
  async function runAction(
    id: string,
    action: (id: string) => Promise<{ status: RecurringStatus; next_run_at: string }>,
    successLabel: string
  ) {
    setActingId(id);
    setActionError((prev) => ({ ...prev, [id]: "" }));
    setActionInfo((prev) => ({ ...prev, [id]: "" }));
    try {
      const res = await action(id);
      setActionInfo((prev) => ({
        ...prev,
        [id]: `${successLabel} (${STATUS_LABEL[res.status]}). Próxima: ${formatNextRun(
          res.next_run_at
        )}.`,
      }));
      onChanged();
    } catch (err) {
      setActionError((prev) => ({
        ...prev,
        [id]:
          err instanceof ApiRequestError ? err.message : "No se pudo completar la acción.",
      }));
    } finally {
      setActingId(null);
    }
  }

  return (
    <section className="card" aria-label="Pagos recurrentes">
      <h2>Pagos recurrentes</h2>

      {schedules.length === 0 ? (
        <p className="message">No hay pagos recurrentes configurados.</p>
      ) : (
        <ul className="beneficiary-list">
          {schedules.map((s) => {
            const busy = actingId === s.id;
            return (
              <li className="beneficiary-item" key={s.id}>
                <div className="beneficiary-main">
                  <span className="beneficiary-name">
                    {s.type === "internal" ? "Interno" : "ACH"} · COP {s.amount}
                  </span>
                  <span className={`badge badge-${s.status}`}>
                    {STATUS_LABEL[s.status]}
                  </span>
                </div>
                <div className="beneficiary-meta">
                  <span>{FREQUENCY_LABEL[s.frequency]}</span>
                  <span>Próxima: {formatNextRun(s.next_run_at)}</span>
                </div>
                {s.description && (
                  <p className="history-description">{s.description}</p>
                )}
                <div className="modal-actions recurring-actions">
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || s.status !== "active"}
                    onClick={() => void runAction(s.id, pauseRecurring, "Schedule pausado")}
                  >
                    {busy ? "..." : "Pausar"}
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || s.status !== "paused"}
                    onClick={() => void runAction(s.id, resumeRecurring, "Schedule reanudado")}
                  >
                    {busy ? "..." : "Reanudar"}
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || s.status === "cancelled"}
                    onClick={() => void runAction(s.id, cancelRecurring, "Schedule cancelado")}
                  >
                    {busy ? "..." : "Cancelar"}
                  </button>
                </div>
                {actionError[s.id] && (
                  <p className="message error">{actionError[s.id]}</p>
                )}
                {actionInfo[s.id] && (
                  <p className="message success">{actionInfo[s.id]}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <form onSubmit={handleCreate} className="transfer-form">
        <h3>Nuevo pago recurrente</h3>

        <label>
          Tipo
          <select value={type} onChange={(e) => setType(e.target.value as TransferType)}>
            <option value="internal">Interno (entre tus cuentas)</option>
            <option value="ach">ACH (a terceros)</option>
          </select>
        </label>

        <label>
          Frecuencia
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
          >
            <option value="daily">Diaria</option>
            <option value="weekly">Semanal</option>
            <option value="monthly">Mensual</option>
          </select>
        </label>

        {type === "internal" ? (
          <>
            <label>
              Desde
              <select
                value={from}
                onChange={(e) => handleFromChange(e.target.value as AccountKind)}
              >
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
          </>
        ) : (
          <>
            <fieldset className="ach-mode">
              <legend>Beneficiario</legend>
              <label className="radio">
                <input
                  type="radio"
                  name="rec-ben-mode"
                  checked={beneficiaryMode === "saved"}
                  onChange={() => setBeneficiaryMode("saved")}
                  disabled={beneficiaries.length === 0}
                />
                Guardado
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="rec-ben-mode"
                  checked={beneficiaryMode === "adhoc"}
                  onChange={() => setBeneficiaryMode("adhoc")}
                />
                Ad hoc
              </label>
            </fieldset>

            {beneficiaryMode === "saved" ? (
              <label>
                Beneficiario guardado
                <select
                  value={beneficiaryId}
                  onChange={(e) => setBeneficiaryId(e.target.value)}
                >
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
                  Nombre
                  <input
                    type="text"
                    value={adName}
                    onChange={(e) => setAdName(e.target.value)}
                    placeholder="Nombre del beneficiario"
                  />
                </label>
                <label>
                  Banco
                  <input
                    type="text"
                    value={adBank}
                    onChange={(e) => setAdBank(e.target.value)}
                    placeholder="Banco"
                  />
                </label>
                <label>
                  Número de routing
                  <input
                    type="text"
                    inputMode="numeric"
                    value={adRouting}
                    onChange={(e) => setAdRouting(e.target.value)}
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
                    value={adAccount}
                    onChange={(e) => setAdAccount(e.target.value)}
                    placeholder="4 a 17 dígitos"
                    aria-invalid={accountError !== null}
                  />
                  {accountError && <span className="message error">{accountError}</span>}
                </label>
              </>
            )}
          </>
        )}

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
        <label>
          Fecha de inicio (opcional)
          <input
            type="datetime-local"
            value={startAt}
            onChange={(e) => setStartAt(e.target.value)}
          />
        </label>
        <label>
          Código MFA (si el monto es sensible)
          <input
            type="text"
            inputMode="numeric"
            placeholder="Requerido para montos altos"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
          />
        </label>

        <button type="submit" disabled={!canSubmit}>
          {submitting ? "Creando..." : "Crear pago recurrente"}
        </button>
      </form>

      {error && <p className="message error">{error}</p>}
      {info && <p className="message success">{info}</p>}
    </section>
  );
}
