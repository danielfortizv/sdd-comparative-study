/** Exact two-decimal input/output helpers. Monetary paths never pass through Number. */
const DECIMAL = /^(0|[1-9]\d*)(?:\.(\d{1,2}))?$/;

export function parseMinorUnits(input: string): bigint {
  const value = input.trim();
  const match = DECIMAL.exec(value);
  if (!match) throw new Error('Enter a non-negative amount with at most two decimal places.');
  const whole = BigInt(match[1]);
  const fraction = BigInt((match[2] ?? '').padEnd(2, '0'));
  return whole * 100n + fraction;
}

export function formatMinorUnits(minor: bigint, currency: string, locale = 'en-US'): string {
  const negative = minor < 0n;
  const absolute = negative ? -minor : minor;
  const whole = absolute / 100n;
  const cents = (absolute % 100n).toString().padStart(2, '0');
  const grouped = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(whole);
  const decimal = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
    .formatToParts(1.1).find(part => part.type === 'decimal')?.value ?? '.';
  return `${negative ? '-' : ''}${currency} ${grouped}${decimal}${cents}`;
}

export function decimalToMinorUnitsString(value: string): string {
  return parseMinorUnits(value).toString();
}

export function formatDecimalMoney(value: string, currency: string, locale = 'en-US'): string {
  return formatMinorUnits(parseMinorUnits(value), currency, locale);
}
