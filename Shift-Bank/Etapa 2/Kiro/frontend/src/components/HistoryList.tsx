// Historial unificado (Requisitos 5.1, 5.2, 5.3, 2.2 de E1; 6.1, 6.2, 6.3, 7.4 de E2).
// Renderiza entradas internas y ACH diferenciadas por `type` (D03, D05, UI-1):
//   - internas: `direction {from,to}` con nombres amigables y estados MAYÚSCULAS (sin cambios E1);
//   - ACH: beneficiario enmascarado (nombre + cuenta •••• últimos 4) y estados minúsculas.
// Muestra fecha, monto (decimal-string) y descripción. No expone saldo resultante,
// identificadores internos ni números de cuenta completos (6.4).

import type { TransferHistoryItem } from "../types";

interface Props {
  transfers: TransferHistoryItem[];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("es-CO", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Etiquetas de estado para ambos conjuntos: internas (MAYÚSCULAS, E1) y ACH (minúsculas, D03).
// El renderizado conserva un fallback al estado crudo para valores desconocidos (UI-1).
const STATUS_LABEL: Record<string, string> = {
  // Internas (Etapa 1).
  COMPLETED: "Completada",
  PENDING_MFA: "Pendiente de MFA",
  FAILED: "Fallida",
  EXPIRED: "Expirada",
  // ACH (Etapa 2, minúsculas).
  pending: "Pendiente",
  settled: "Liquidada",
  failed: "Fallida",
  pending_auth: "Pendiente de autorización",
  expired: "Expirada",
};

// Descripción textual del beneficiario ACH: nombre + banco + cuenta enmascarada (6.3/6.4).
function beneficiaryLabel(t: TransferHistoryItem): string {
  const b = t.beneficiary;
  if (!b) return "";
  const parts = [b.name, b.bank].filter(Boolean);
  const header = parts.join(" · ");
  return b.account_masked ? `${header} (${b.account_masked})` : header;
}

// Texto principal de la fila: beneficiario enmascarado para ACH, "from → to" para internas
// con dirección, y cadena vacía en cualquier otro caso. Idéntico al ternario anidado previo.
function entryLabel(t: TransferHistoryItem): string {
  if (t.type === "ach") return beneficiaryLabel(t);
  if (t.direction) return `${t.direction.from} → ${t.direction.to}`;
  return "";
}

export function HistoryList({ transfers }: Readonly<Props>) {
  return (
    <section className="card">
      <h2>Historial de transferencias</h2>
      {transfers.length === 0 ? (
        <p className="message">No hay transferencias.</p>
      ) : (
        <ul className="history">
          {transfers.map((t, idx) => (
            <li className="history-item" key={`${t.date}-${idx}`}>
              <div className="history-main">
                <span className="history-direction">{entryLabel(t)}</span>
                <span className="history-amount">COP {t.amount}</span>
              </div>
              <div className="history-meta">
                <span className="history-date">{formatDate(t.date)}</span>
                <span className={`badge badge-${String(t.status).toLowerCase()}`}>
                  {STATUS_LABEL[t.status] ?? t.status}
                </span>
              </div>
              {t.description && <p className="history-description">{t.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
