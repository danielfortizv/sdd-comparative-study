/**
 * Exact Monetary Arithmetic Utility (Frontend D-03)
 *
 * Implements strict decimal-string parsing, exact BigInt cents representation,
 * canonical decimal formatting, exact arithmetic, rational FX conversions
 * with single ROUND_HALF_UP quantization, and unrounded USD-equivalent threshold
 * comparisons via integer cross-multiplication.
 *
 * NEVER uses binary floating-point arithmetic (Number, parseFloat, toFixed).
 */

export type SupportedCurrency = 'USD' | 'EUR' | 'GBP';

export interface RationalRate {
  numerator: bigint;
  denominator: bigint;
}

export interface FxConversionResult {
  destinationCents: bigint;
  destinationAmount: string;
  rateNumerator: bigint;
  rateDenominator: bigint;
}

/**
 * Approved Stage 4 deterministic reference rates (D-03):
 * USD/EUR = 9/10
 * USD/GBP = 8/10
 * EUR/USD = 10/9
 * GBP/USD = 10/8
 * EUR/GBP = 8/9
 * GBP/EUR = 9/8
 */
export const REFERENCE_RATES: Record<SupportedCurrency, Record<SupportedCurrency, RationalRate>> = {
  USD: {
    USD: { numerator: 1n, denominator: 1n },
    EUR: { numerator: 9n, denominator: 10n },
    GBP: { numerator: 8n, denominator: 10n },
  },
  EUR: {
    USD: { numerator: 10n, denominator: 9n },
    EUR: { numerator: 1n, denominator: 1n },
    GBP: { numerator: 8n, denominator: 9n },
  },
  GBP: {
    USD: { numerator: 10n, denominator: 8n },
    EUR: { numerator: 9n, denominator: 8n },
    GBP: { numerator: 1n, denominator: 1n },
  },
};

/**
 * Base factors to convert to USD equivalent:
 * 1 USD = 1.00 USD (equiv rate 1/1)
 * 1 USD = 0.90 EUR (equiv rate 10/9)
 * 1 USD = 0.80 GBP (equiv rate 10/8)
 */
export const USD_BASE_FACTORS: Record<SupportedCurrency, RationalRate> = {
  USD: { numerator: 1n, denominator: 1n },
  EUR: { numerator: 10n, denominator: 9n },
  GBP: { numerator: 10n, denominator: 8n },
};

/**
 * Regex for strict monetary strings with at most two decimal places.
 * Matches:
 *  - Non-empty
 *  - Optional leading minus sign '-'
 *  - Integer digits
 *  - Optional decimal point followed by exactly 1 or 2 digits
 * Rejects:
 *  - Empty or whitespace strings
 *  - More than 2 decimal places (e.g. 0.295, 0.051)
 *  - Trailing or leading decimals without digits (e.g. "1.", ".5")
 *  - Multiple decimal points (e.g. "1.2.3")
 *  - Non-numeric characters (e.g. "12a", "abc", "$100")
 */
const MONETARY_REGEX = /^-?\d+(\.\d{1,2})?$/;

/**
 * Validates whether a string matches strict monetary decimal format.
 */
export function isValidMonetaryString(value: unknown): value is string {
  if (typeof value !== 'string') {
    return false;
  }
  const trimmed = value.trim();
  if (trimmed === '' || trimmed !== value) {
    return false;
  }
  return MONETARY_REGEX.test(value);
}

/**
 * Asserts that a value is a valid monetary decimal string, throwing an Error if not.
 */
export function validateMonetaryString(value: string): void {
  if (!isValidMonetaryString(value)) {
    throw new Error(
      `Invalid monetary decimal string: "${value}". Must be a valid numeric string with at most 2 decimal places.`
    );
  }
}

/**
 * Converts a valid decimal string to BigInt integer cents.
 * Handles exact parsing without any floating-point numbers.
 *
 * Examples:
 *  "2500.00" -> 250000n
 *  "0.10"    -> 10n
 *  "0.29"    -> 29n
 *  "0.05"    -> 5n
 *  "10"      -> 1000n
 *  "0.5"     -> 50n
 */
export function parseToCents(value: string): bigint {
  validateMonetaryString(value);

  const isNegative = value.startsWith('-');
  const raw = isNegative ? value.slice(1) : value;

  const dotIndex = raw.indexOf('.');
  let integerPartStr: string;
  let centsPartStr: string;

  if (dotIndex === -1) {
    integerPartStr = raw;
    centsPartStr = '00';
  } else {
    integerPartStr = raw.slice(0, dotIndex);
    const fraction = raw.slice(dotIndex + 1);
    if (fraction.length === 1) {
      centsPartStr = fraction + '0';
    } else if (fraction.length === 2) {
      centsPartStr = fraction;
    } else {
      throw new Error(`Excess decimal places in monetary amount: "${value}"`);
    }
  }

  const integerCents = BigInt(integerPartStr) * 100n;
  const fractionCents = BigInt(centsPartStr);
  const totalCents = integerCents + fractionCents;

  return isNegative ? -totalCents : totalCents;
}

/**
 * Converts BigInt cents to a canonical two-decimal string.
 *
 * Examples:
 *  250000n -> "2500.00"
 *  10n     -> "0.10"
 *  29n     -> "0.29"
 *  5n      -> "0.05"
 *  0n      -> "0.00"
 *  -10n    -> "-0.10"
 */
export function centsToDecimalString(cents: bigint): string {
  const isNegative = cents < 0n;
  const absCents = isNegative ? -cents : cents;

  const integerPart = absCents / 100n;
  const remainder = absCents % 100n;
  const fractionStr = remainder.toString().padStart(2, '0');

  const sign = isNegative ? '-' : '';
  return `${sign}${integerPart.toString()}.${fractionStr}`;
}

/**
 * Helper to ensure a monetary argument is in BigInt cents.
 */
export function toCents(amount: string | bigint): bigint {
  return typeof amount === 'bigint' ? amount : parseToCents(amount);
}

/**
 * Exact addition of two monetary values (cents).
 */
export function addCents(a: bigint, b: bigint): bigint {
  return a + b;
}

/**
 * Exact subtraction of two monetary values (cents).
 */
export function subCents(a: bigint, b: bigint): bigint {
  return a - b;
}

/**
 * Exact comparison of two monetary values (cents).
 * Returns -1 if a < b, 0 if a == b, 1 if a > b.
 */
export function compareCents(a: bigint, b: bigint): -1 | 0 | 1 {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

/**
 * Exact addition of two monetary decimal strings.
 * Returns a canonical two-decimal string.
 */
export function addMonetary(a: string, b: string): string {
  return centsToDecimalString(addCents(parseToCents(a), parseToCents(b)));
}

/**
 * Exact subtraction of two monetary decimal strings (a - b).
 * Returns a canonical two-decimal string.
 */
export function subMonetary(a: string, b: string): string {
  return centsToDecimalString(subCents(parseToCents(a), parseToCents(b)));
}

/**
 * Exact comparison of two monetary decimal strings.
 * Returns -1 if a < b, 0 if a == b, 1 if a > b.
 */
export function compareMonetary(a: string, b: string): -1 | 0 | 1 {
  return compareCents(parseToCents(a), parseToCents(b));
}

/**
 * Performs integer division with ROUND_HALF_UP rounding.
 * In ROUND_HALF_UP, if the fractional remainder is >= 0.5 (i.e. 2 * remainder >= denominator),
 * the magnitude is rounded up away from zero.
 */
export function divideHalfUp(p: bigint, q: bigint): bigint {
  if (q === 0n) {
    throw new Error('Division by zero in divideHalfUp');
  }

  const isNegative = (p < 0n) !== (q < 0n);
  const absP = p < 0n ? -p : p;
  const absQ = q < 0n ? -q : q;

  let quotient = absP / absQ;
  const remainder = absP % absQ;

  if (2n * remainder >= absQ) {
    quotient += 1n;
  }

  return isNegative ? -quotient : quotient;
}

/**
 * Executes exact rational FX conversion according to D-03:
 * 1. Derives integer rational rate (numerator, denominator).
 * 2. Multiplies source cents by rate numerator.
 * 3. Applies single ROUND_HALF_UP quantization to destination cents.
 * 4. Returns destination amount as canonical two-decimal string and rate details.
 */
export function convertCurrency(
  amount: string | bigint,
  sourceCurrency: SupportedCurrency,
  destinationCurrency: SupportedCurrency
): FxConversionResult {
  const sourceCents = toCents(amount);

  if (sourceCents <= 0n) {
    throw new Error('Conversion amount must be strictly positive');
  }

  if (sourceCurrency === destinationCurrency) {
    return {
      destinationCents: sourceCents,
      destinationAmount: centsToDecimalString(sourceCents),
      rateNumerator: 1n,
      rateDenominator: 1n,
    };
  }

  const rates = REFERENCE_RATES[sourceCurrency];
  if (!rates || !rates[destinationCurrency]) {
    throw new Error(`Unsupported currency conversion pair: ${sourceCurrency} -> ${destinationCurrency}`);
  }

  const { numerator, denominator } = rates[destinationCurrency];
  const product = sourceCents * numerator;
  const destinationCents = divideHalfUp(product, denominator);

  if (destinationCents <= 0n) {
    throw new Error('Conversion amount too small; resulting amount would be zero');
  }

  return {
    destinationCents,
    destinationAmount: centsToDecimalString(destinationCents),
    rateNumerator: numerator,
    rateDenominator: denominator,
  };
}

/**
 * Compares the exact unrounded USD equivalent of a monetary amount against a USD threshold
 * using integer cross-multiplication (D-07, D-03).
 *
 * USD equivalent formula:
 *   usd_equivalent = amount * base_factor_num / base_factor_den
 *
 * Comparing:
 *   (amountCents * num) / den vs thresholdCents
 * Cross-multiplying:
 *   amountCents * num vs thresholdCents * den
 *
 * Returns:
 *   -1 if unrounded USD equivalent < threshold
 *    0 if unrounded USD equivalent == threshold
 *    1 if unrounded USD equivalent > threshold
 */
export function compareUsdEquivalentToThreshold(
  amount: string | bigint,
  currency: SupportedCurrency,
  threshold: string | bigint
): -1 | 0 | 1 {
  const amountCents = toCents(amount);
  const thresholdCents = toCents(threshold);

  const factor = USD_BASE_FACTORS[currency];
  if (!factor) {
    throw new Error(`Unsupported currency for USD equivalent calculation: ${currency}`);
  }

  const lhs = amountCents * factor.numerator;
  const rhs = thresholdCents * factor.denominator;

  if (lhs < rhs) return -1;
  if (lhs > rhs) return 1;
  return 0;
}

/**
 * Checks whether the unrounded USD equivalent strictly exceeds a threshold.
 * (e.g. for MFA requirement where usd_equivalent > $1,000.00).
 */
export function isUsdEquivalentExceedingThreshold(
  amount: string | bigint,
  currency: SupportedCurrency,
  threshold: string | bigint
): boolean {
  return compareUsdEquivalentToThreshold(amount, currency, threshold) === 1;
}

/**
 * Checks whether the unrounded USD equivalent is greater than or equal to a threshold.
 */
export function isUsdEquivalentAtOrAboveThreshold(
  amount: string | bigint,
  currency: SupportedCurrency,
  threshold: string | bigint
): boolean {
  return compareUsdEquivalentToThreshold(amount, currency, threshold) >= 0;
}

/**
 * Sums an array of monetary values (decimal strings or BigInt cents) in BigInt cents.
 */
export function sumCents(amounts: Array<string | bigint>): bigint {
  return amounts.reduce<bigint>((sum, amt) => sum + toCents(amt), 0n);
}

/**
 * Sums an array of monetary values and returns a canonical two-decimal string.
 */
export function sumMonetary(amounts: Array<string | bigint>): string {
  return centsToDecimalString(sumCents(amounts));
}

/**
 * Formats a monetary value (decimal string or BigInt cents) into a localized currency string
 * using pure string and BigInt operations WITHOUT Number, parseFloat, or toFixed.
 *
 * Examples:
 *  "2500.00", "USD" -> "$2,500.00"
 *  "90.00", "EUR"   -> "€90.00"
 *  "80.00", "GBP"   -> "£80.00"
 *  "0.05", "USD"    -> "$0.05"
 *  "12500.00", "USD"-> "$12,500.00"
 *  "-10.50", "USD"  -> "-$10.50"
 */
export function formatCurrency(amount: string | bigint, currency: string = 'USD'): string {
  const decimalStr = typeof amount === 'bigint' ? centsToDecimalString(amount) : amount;
  validateMonetaryString(decimalStr);

  const isNegative = decimalStr.startsWith('-');
  const raw = isNegative ? decimalStr.slice(1) : decimalStr;

  const dotIndex = raw.indexOf('.');
  let intPart = dotIndex === -1 ? raw : raw.slice(0, dotIndex);
  let decPart = dotIndex === -1 ? '00' : raw.slice(dotIndex + 1);
  if (decPart.length === 1) {
    decPart += '0';
  }

  // Insert thousands separators (commas) into the integer part
  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

  const symbols: Record<string, string> = {
    USD: '$',
    EUR: '€',
    GBP: '£',
  };

  const symbol = symbols[currency];
  if (symbol) {
    return `${isNegative ? '-' : ''}${symbol}${formattedInt}.${decPart}`;
  }
  return `${isNegative ? '-' : ''}${currency} ${formattedInt}.${decPart}`;
}

/**
 * Greatest common divisor for bigints.
 */
export function gcd(a: bigint, b: bigint): bigint {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y !== 0n) {
    const t = y;
    y = x % y;
    x = t;
  }
  return x;
}

/**
 * Formats a rational rate (numerator / denominator) to an exact 4-decimal string
 * using integer arithmetic and ROUND_HALF_UP rounding.
 *
 * Examples:
 *  9n / 10n -> "0.9000"
 *  10n / 9n -> "1.1111"
 *  8n / 10n -> "0.8000"
 *  10n / 8n -> "1.2500"
 *  8n / 9n  -> "0.8889"
 *  9n / 8n  -> "1.1250"
 */
export function formatRationalRate(numerator: bigint, denominator: bigint): string {
  if (denominator === 0n) {
    throw new Error('Division by zero in formatRationalRate');
  }
  const integerPart = numerator / denominator;
  const remainder = numerator % denominator;
  let fractionPart = divideHalfUp(remainder * 10000n, denominator);
  let intPart = integerPart;
  if (fractionPart >= 10000n) {
    intPart += 1n;
    fractionPart -= 10000n;
  }
  return `${intPart.toString()}.${fractionPart.toString().padStart(4, '0')}`;
}

/**
 * Calculates the display-only estimated total in USD across multiple multicurrency accounts (D-10, D-03).
 *
 * Requirements:
 * 1. Converts each account balance to its exact rational USD equivalent without intermediate rounding.
 * 2. Accumulates the unrounded rational equivalents across all accounts.
 * 3. Applies ROUND_HALF_UP only ONCE to the final accumulated USD total.
 * 4. Never independently rounds each account's USD equivalent before summation.
 *
 * For example:
 * Two GBP accounts of 0.02 GBP each have unrounded USD equivalents of 2.5 cents each.
 * Accumulated unrounded USD equivalent = 5.0 cents.
 * Single final ROUND_HALF_UP = 5 cents ($0.05 USD), NOT 6 cents ($0.06 USD).
 */
export function calculateEstimatedUsdTotalCents(
  accounts: Array<{ balance: string | bigint; currency: string }>
): bigint {
  if (accounts.length === 0) {
    return 0n;
  }

  let totalNum = 0n;
  let totalDen = 1n;

  for (const acc of accounts) {
    const factor = USD_BASE_FACTORS[acc.currency as SupportedCurrency];
    if (!factor) {
      throw new Error(`Unsupported currency for USD equivalent calculation: ${acc.currency}`);
    }
    const cents = typeof acc.balance === 'bigint' ? acc.balance : parseToCents(acc.balance);
    const termNum = cents * factor.numerator;
    const termDen = factor.denominator;

    totalNum = totalNum * termDen + termNum * totalDen;
    totalDen = totalDen * termDen;

    const d = gcd(totalNum, totalDen);
    if (d > 1n) {
      totalNum /= d;
      totalDen /= d;
    }
  }

  if (totalDen === 1n && totalNum === 0n) {
    return 0n;
  }

  return divideHalfUp(totalNum, totalDen);
}

/**
 * Calculates the display-only estimated total in USD across accounts as a canonical decimal string.
 */
export function calculateEstimatedUsdTotal(
  accounts: Array<{ balance: string | bigint; currency: string }>
): string {
  return centsToDecimalString(calculateEstimatedUsdTotalCents(accounts));
}

