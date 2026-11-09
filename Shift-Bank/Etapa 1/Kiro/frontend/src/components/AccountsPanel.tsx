// Panel de cuentas: muestra solo los nombres amigables y el saldo (Requisitos 2.1, 2.2).
// No muestra ningún identificador interno.

import type { Account } from "../types";

interface Props {
  accounts: Account[];
}

function formatCop(amount: string): string {
  // Formateo visual con separadores de miles. El valor original (decimal-string)
  // viene del backend; aquí solo se formatea para presentación.
  const [intPart, decPart] = amount.split(".");
  const withThousands = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const dec = decPart ?? "00";
  return `COP ${withThousands},${dec}`;
}

export function AccountsPanel({ accounts }: Props) {
  return (
    <section className="card">
      <h2>Mis cuentas</h2>
      <div className="accounts">
        {accounts.map((a) => (
          <div className="account" key={a.name}>
            <span className="account-name">{a.name}</span>
            <span className="account-balance">{formatCop(a.balance)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
