// Formulario de conversión de divisas (Etapa 4, D-03/D-10): muestra la tasa aplicada, origen y
// destino tras una conversión. Usa el cliente v2 (Idempotency-Key automático). Montos como string.

import { useState } from "react";
import type { AccountV2, ConversionResponse } from "./apiV2";
import { ApiV2Error, createConversion } from "./apiV2";
import { formatMoney } from "./currencyFormat";

interface Props {
  accounts: AccountV2[];
  onDone?: () => void;
}

export function ConversionForm({ accounts, onDone }: Readonly<Props>) {
  const [from, setFrom] = useState(accounts[0]?.public_id ?? "");
  const [to, setTo] = useState(accounts[1]?.public_id ?? "");
  const [amount, setAmount] = useState("");
  const [result, setResult] = useState<ConversionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      const res = await createConversion({ from, to, amount });
      setResult(res);
      onDone?.();
    } catch (err) {
      if (err instanceof ApiV2Error) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError("Error inesperado");
      }
    }
  }

  return (
    <section className="card" aria-label="Conversión de divisas">
      <h2>Convertir divisas</h2>
      <form onSubmit={submit}>
        <label>
          Origen
          <select value={from} onChange={(e) => setFrom(e.target.value)}>
            {accounts.map((a) => (
              <option key={a.public_id} value={a.public_id}>
                {a.public_id} ({a.currency})
              </option>
            ))}
          </select>
        </label>
        <label>
          Destino
          <select value={to} onChange={(e) => setTo(e.target.value)}>
            {accounts.map((a) => (
              <option key={a.public_id} value={a.public_id}>
                {a.public_id} ({a.currency})
              </option>
            ))}
          </select>
        </label>
        <label>
          Monto (origen)
          <input
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </label>
        <button type="submit">Convertir</button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && (
        <div className="conversion-result">
          <p>Tasa aplicada: {result.rate}</p>
          <p>
            Origen:{" "}
            {formatMoney(result.from.amount, result.from.currency)} ({result.from.public_id})
          </p>
          <p>
            Destino: {formatMoney(result.to.amount, result.to.currency)} ({result.to.public_id})
          </p>
        </div>
      )}
    </section>
  );
}
