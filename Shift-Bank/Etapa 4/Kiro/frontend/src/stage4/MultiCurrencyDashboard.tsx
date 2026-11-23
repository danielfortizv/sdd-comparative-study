// Dashboard multidivisa de la Etapa 4 (D-10): totales SEPARADOS por moneda y un total estimado en
// USD etiquetado explícitamente como "solo visualización". Los montos se muestran con su moneda y
// 2 decimales; nunca se mezclan monedas en un total.

import type { AccountV2 } from "./apiV2";
import { formatMoney, groupByCurrency } from "./currencyFormat";

interface Props {
  accounts: AccountV2[];
}

export function MultiCurrencyDashboard({ accounts }: Readonly<Props>) {
  const { perCurrency, usdEstimate } = groupByCurrency(
    accounts.map((a) => ({ currency: a.currency, balance: a.balance })),
  );

  return (
    <section className="card" aria-label="Cuentas multidivisa">
      <h2>Mis cuentas (multidivisa)</h2>
      <div className="accounts">
        {accounts.map((a) => (
          <div className="account" key={a.public_id}>
            <span className="account-name">
              {a.name} <code>{a.public_id}</code>
            </span>
            <span className="account-balance">{formatMoney(a.balance, a.currency)}</span>
          </div>
        ))}
      </div>

      <h3>Totales por moneda</h3>
      <ul className="totals-by-currency">
        {Object.entries(perCurrency).map(([ccy, total]) => (
          <li key={ccy}>
            {ccy}: {formatMoney(total, ccy as AccountV2["currency"])}
          </li>
        ))}
      </ul>

      <p className="usd-estimate">
        Total estimado: {formatMoney(usdEstimate, "USD")}{" "}
        <em>(estimado en USD, solo visualización)</em>
      </p>
    </section>
  );
}
