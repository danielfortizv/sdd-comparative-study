// Panel de límites de transferencia dinámicos (Requisitos 13.2, 13.3; contrato LIM-02, A21).
// Muestra los límites vigentes (por transferencia y diario) junto con el consumo del día UTC y la
// disponibilidad restante, y permite editarlos (PUT) con validación de formato inmediata y
// retroalimentación de carga/éxito/error. El backend es la autoridad final de validación (LIM-09).

import { useState } from "react";

import { ApiRequestError, updateLimits } from "../api/client";
import type { LimitsResponse, UpdateLimitsRequest } from "../types";

interface Props {
  limits: LimitsResponse | null;
  onChanged: () => void;
}

// Replica mínima de validación para feedback inmediato: monto decimal no negativo con como mucho
// dos decimales (modelo monetario COP, D01). La autoridad es el backend (LIM-09).
function validateAmount(raw: string): string | null {
  const value = raw.trim();
  if (value === "") return "Ingresa un valor.";
  if (!/^\d+(\.\d{1,2})?$/.test(value)) {
    return "Usa un monto válido (hasta 2 decimales, sin signo).";
  }
  return null;
}

export function LimitsPanel({ limits, onChanged }: Readonly<Props>) {
  const [perTransfer, setPerTransfer] = useState("");
  const [daily, setDaily] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Solo valida los campos que el usuario rellenó (actualización parcial).
  const perTransferError = perTransfer ? validateAmount(perTransfer) : null;
  const dailyError = daily ? validateAmount(daily) : null;

  const hasInput = perTransfer.trim() !== "" || daily.trim() !== "";
  const canSubmit =
    hasInput && perTransferError === null && dailyError === null && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    if (!canSubmit) {
      setError("Ingresa al menos un límite válido antes de guardar.");
      return;
    }
    const payload: UpdateLimitsRequest = {};
    if (perTransfer.trim() !== "") payload.per_transfer = perTransfer.trim();
    if (daily.trim() !== "") payload.daily = daily.trim();
    setSubmitting(true);
    try {
      const res = await updateLimits(payload);
      setInfo(
        `Límites actualizados. Por transferencia: COP ${res.per_transfer} · Diario: COP ${res.daily}.`
      );
      setPerTransfer("");
      setDaily("");
      onChanged();
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "No se pudieron actualizar los límites."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card" aria-label="Límites de transferencia">
      <h2>Límites de transferencia</h2>

      {limits === null ? (
        <p className="message">Cargando límites…</p>
      ) : (
        <ul className="accounts">
          <li className="account">
            <span className="account-name">Por transferencia</span>
            <span className="account-balance">COP {limits.per_transfer}</span>
          </li>
          <li className="account">
            <span className="account-name">Diario</span>
            <span className="account-balance">COP {limits.daily}</span>
          </li>
          <li className="account">
            <span className="account-name">Consumido hoy (UTC)</span>
            <span className="account-balance">COP {limits.daily_consumed}</span>
          </li>
          <li className="account">
            <span className="account-name">Disponible hoy (UTC)</span>
            <span className="account-balance">COP {limits.daily_remaining}</span>
          </li>
        </ul>
      )}

      <form onSubmit={handleSubmit} className="transfer-form">
        <h3>Editar límites</h3>
        <p className="message">
          Deja un campo en blanco para no modificarlo. Los montos van en COP (hasta 2 decimales).
        </p>
        <label>
          Nuevo límite por transferencia (COP)
          <input
            type="text"
            inputMode="decimal"
            placeholder={limits ? limits.per_transfer : "0.00"}
            value={perTransfer}
            onChange={(e) => setPerTransfer(e.target.value)}
            aria-invalid={perTransferError !== null}
          />
          {perTransferError && <span className="message error">{perTransferError}</span>}
        </label>
        <label>
          Nuevo límite diario (COP)
          <input
            type="text"
            inputMode="decimal"
            placeholder={limits ? limits.daily : "0.00"}
            value={daily}
            onChange={(e) => setDaily(e.target.value)}
            aria-invalid={dailyError !== null}
          />
          {dailyError && <span className="message error">{dailyError}</span>}
        </label>
        <button type="submit" disabled={!canSubmit}>
          {submitting ? "Guardando..." : "Guardar límites"}
        </button>
      </form>

      {error && <p className="message error">{error}</p>}
      {info && <p className="message success">{info}</p>}
    </section>
  );
}
