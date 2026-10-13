// Diálogo de MFA (Requisitos 6.4, 7.2, 7.3, 8.2, 8.3, 8.4).
// Pide el código, muestra un contador hacia expires_at, permite reintentos ante código
// incorrecto, y maneja COMPLETED / EXPIRED / FAILED. Los saldos solo cambian tras COMPLETED.

import { useEffect, useMemo, useState } from "react";

import { ApiRequestError, confirmMfa } from "../api/client";

interface Props {
  reference: string;
  expiresAt: string;
  amount: string;
  onCompleted: () => void;
  onDismiss: () => void;
}

function secondsLeft(expiresAt: string): number {
  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.floor(diff / 1000));
}

export function MfaDialog({ reference, expiresAt, amount, onCompleted, onDismiss }: Props) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [remaining, setRemaining] = useState(() => secondsLeft(expiresAt));

  useEffect(() => {
    const id = setInterval(() => setRemaining(secondsLeft(expiresAt)), 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  const countdown = useMemo(() => {
    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }, [remaining]);

  const expired = remaining <= 0;

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await confirmMfa(reference, code.trim());
      if (res.status === "COMPLETED") {
        onCompleted();
      }
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.code === "INVALID_MFA_CODE") {
          // Sigue PENDING_MFA: permitir reintento.
          setError("Código incorrecto. Intenta de nuevo.");
        } else if (err.code === "EXPIRED") {
          setError("La solicitud expiró. Debes iniciar una nueva transferencia.");
        } else if (err.code === "INSUFFICIENT_FUNDS") {
          setError("La transferencia falló por fondos insuficientes.");
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo confirmar la transferencia.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Verificación MFA">
      <div className="modal card">
        <h2>Verificación requerida</h2>
        <p>
          Esta transferencia de <strong>COP {amount}</strong> requiere verificación de
          seguridad. Ingresa el código MFA.
        </p>
        <p className={expired ? "message error" : "countdown"}>
          {expired ? "Solicitud expirada" : `Expira en ${countdown}`}
        </p>
        <form onSubmit={handleConfirm} className="mfa-form">
          <label>
            Código MFA
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={expired || submitting}
              autoFocus
            />
          </label>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={onDismiss}>
              Cerrar
            </button>
            <button type="submit" disabled={expired || submitting}>
              {submitting ? "Verificando..." : "Confirmar"}
            </button>
          </div>
        </form>
        {error && <p className="message error">{error}</p>}
      </div>
    </div>
  );
}
