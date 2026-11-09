// Historial (Requisitos 5.1, 5.2, 5.3, 2.2).
// Lista fecha, dirección (con nombres amigables), monto (decimal-string) y descripción.
// No muestra saldo resultante ni identificadores internos.

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

const STATUS_LABEL: Record<string, string> = {
  COMPLETED: "Completada",
  PENDING_MFA: "Pendiente de MFA",
  FAILED: "Fallida",
  EXPIRED: "Expirada",
};

export function HistoryList({ transfers }: Props) {
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
                <span className="history-direction">
                  {t.direction.from} → {t.direction.to}
                </span>
                <span className="history-amount">COP {t.amount}</span>
              </div>
              <div className="history-meta">
                <span className="history-date">{formatDate(t.date)}</span>
                <span className={`badge badge-${t.status.toLowerCase()}`}>
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
