// Formateo monetario multidivisa de la Etapa 4 (D-03, D-10).
//
// Los montos SIEMPRE son `string` (decimal-string) o `bigint` en unidades menores, NUNCA `number`,
// para preservar la exactitud decimal (D-03). Cada moneda soportada (USD, EUR, GBP) tiene 2
// decimales. No se mezclan monedas en un total (D-10): los totales se agrupan por moneda y el
// total estimado en USD se etiqueta explícitamente como "solo visualización".

export type Currency = "USD" | "EUR" | "GBP";

export const SUPPORTED_CURRENCIES: readonly Currency[] = ["USD", "EUR", "GBP"] as const;

const SYMBOLS: Record<Currency, string> = { USD: "$", EUR: "€", GBP: "£" };

// Tasas racionales fijas de la guía Etapa 4, como [numerador, denominador] de "unidades por USD".
// EUR = 9/10, GBP = 8/10. Deben coincidir con el backend (`config.FX_RATES_PER_USD`).
const PER_USD: Record<Currency, [bigint, bigint]> = {
  USD: [1n, 1n],
  EUR: [9n, 10n],
  GBP: [8n, 10n],
};

/** Convierte una cadena decimal de 2 decimales a `bigint` de unidades menores (centavos). */
export function toMinor(amount: string): bigint {
  const [intPart, decRaw = ""] = amount.trim().split(".");
  const dec = (decRaw + "00").slice(0, 2);
  const sign = intPart.startsWith("-") ? -1n : 1n;
  const intAbs = intPart.replace("-", "") || "0";
  return sign * (BigInt(intAbs) * 100n + BigInt(dec || "0"));
}

/** Convierte `bigint` de unidades menores a cadena decimal de 2 decimales. */
export function fromMinor(minor: bigint): string {
  const neg = minor < 0n;
  const abs = neg ? -minor : minor;
  const intPart = abs / 100n;
  const dec = (abs % 100n).toString().padStart(2, "0");
  return `${neg ? "-" : ""}${intPart.toString()}.${dec}`;
}

/** Formatea un monto (decimal-string) con su símbolo de moneda y 2 decimales. */
export function formatMoney(amount: string, currency: Currency): string {
  const minor = toMinor(amount);
  const [intPart, dec] = fromMinor(minor).replace("-", "").split(".");
  const withThousands = intPart.replace(/\d(?=(?:\d{3})+$)/g, "$&,");
  const sign = minor < 0n ? "-" : "";
  return `${sign}${SYMBOLS[currency]}${withThousands}.${dec} ${currency}`;
}

/**
 * Equivalente USD ESTIMADO (solo visualización, D-10) de un monto en unidades menores.
 * Usa las tasas racionales fijas con aritmética `bigint` y redondeo HALF_UP una sola vez.
 * NO es autoritativo; solo para el total estimado del dashboard.
 */
export function usdEstimateMinor(minor: bigint, currency: Currency): bigint {
  if (currency === "USD") return minor;
  const [num, den] = PER_USD[currency]; // unidades de `currency` por USD
  // USD_minor = minor * den / num, HALF_UP una vez.
  const numerator = minor * den;
  const q = numerator / num;
  const r = numerator % num;
  // HALF_UP: si 2*resto >= divisor, redondear hacia arriba (en magnitud).
  const rounded = 2n * (r < 0n ? -r : r) >= num ? q + (q < 0n ? -1n : 1n) : q;
  return rounded;
}

/** Agrupa saldos por moneda (sin mezclar) y calcula un total estimado USD (solo visualización). */
export function groupByCurrency(
  accounts: { currency: Currency; balance: string }[],
): { perCurrency: Record<string, string>; usdEstimate: string } {
  const totals: Partial<Record<Currency, bigint>> = {};
  let usd = 0n;
  for (const a of accounts) {
    const minor = toMinor(a.balance);
    totals[a.currency] = (totals[a.currency] ?? 0n) + minor;
    usd += usdEstimateMinor(minor, a.currency);
  }
  const perCurrency: Record<string, string> = {};
  for (const ccy of SUPPORTED_CURRENCIES) {
    if (totals[ccy] !== undefined) perCurrency[ccy] = fromMinor(totals[ccy] as bigint);
  }
  return { perCurrency, usdEstimate: fromMinor(usd) };
}
