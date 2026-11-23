import { describe, it, expect } from 'vitest';
import {
  isValidMonetaryString,
  validateMonetaryString,
  parseToCents,
  centsToDecimalString,
  addCents,
  subCents,
  compareCents,
  addMonetary,
  subMonetary,
  compareMonetary,
  divideHalfUp,
  convertCurrency,
  compareUsdEquivalentToThreshold,
  isUsdEquivalentExceedingThreshold,
  isUsdEquivalentAtOrAboveThreshold,
  REFERENCE_RATES,
  USD_BASE_FACTORS,
  formatCurrency,
  sumCents,
  sumMonetary,
  calculateEstimatedUsdTotalCents,
  calculateEstimatedUsdTotal,
  gcd,
  formatRationalRate,
} from '../utils/monetary';

describe('Frontend D-03 Exact Monetary Arithmetic Utility', () => {
  describe('Parsing and Decimal String Validation (0.10, 0.29, 0.05, 2500.00)', () => {
    it('correctly parses and validates standard monetary values into exact BigInt cents', () => {
      // 0.10
      expect(isValidMonetaryString('0.10')).toBe(true);
      expect(parseToCents('0.10')).toBe(10n);
      expect(centsToDecimalString(10n)).toBe('0.10');

      // 0.29 (classic binary floating point imprecision representation)
      expect(isValidMonetaryString('0.29')).toBe(true);
      expect(parseToCents('0.29')).toBe(29n);
      expect(centsToDecimalString(29n)).toBe('0.29');

      // 0.05
      expect(isValidMonetaryString('0.05')).toBe(true);
      expect(parseToCents('0.05')).toBe(5n);
      expect(centsToDecimalString(5n)).toBe('0.05');

      // 2500.00 (seed checking balance)
      expect(isValidMonetaryString('2500.00')).toBe(true);
      expect(parseToCents('2500.00')).toBe(250000n);
      expect(centsToDecimalString(250000n)).toBe('2500.00');
    });

    it('correctly handles zero and single-decimal inputs without losing precision', () => {
      expect(parseToCents('0')).toBe(0n);
      expect(centsToDecimalString(0n)).toBe('0.00');

      expect(parseToCents('0.00')).toBe(0n);
      expect(centsToDecimalString(0n)).toBe('0.00');

      expect(parseToCents('0.5')).toBe(50n);
      expect(centsToDecimalString(50n)).toBe('0.50');

      expect(parseToCents('100')).toBe(10000n);
      expect(centsToDecimalString(10000n)).toBe('100.00');
    });

    it('correctly handles negative values', () => {
      expect(isValidMonetaryString('-0.10')).toBe(true);
      expect(parseToCents('-0.10')).toBe(-10n);
      expect(centsToDecimalString(-10n)).toBe('-0.10');

      expect(parseToCents('-2500.00')).toBe(-250000n);
      expect(centsToDecimalString(-250000n)).toBe('-2500.00');
    });
  });

  describe('Invalid Input and Excess Decimal Places', () => {
    it('strictly rejects amounts with excess decimal places (> 2 decimal digits)', () => {
      const invalidExcessDecimals = ['0.295', '0.051', '0.1001', '2500.001', '1.999'];
      for (const val of invalidExcessDecimals) {
        expect(isValidMonetaryString(val)).toBe(false);
        expect(() => validateMonetaryString(val)).toThrow();
        expect(() => parseToCents(val)).toThrow();
      }
    });

    it('strictly rejects non-numeric or malformed decimal strings', () => {
      const malformed = [
        '',
        '   ',
        'abc',
        '1.2.3',
        '1.',
        '.5',
        '$100',
        '100 USD',
        'NaN',
        'Infinity',
        '--10',
        '12,50',
      ];
      for (const val of malformed) {
        expect(isValidMonetaryString(val)).toBe(false);
        expect(() => validateMonetaryString(val)).toThrow();
        expect(() => parseToCents(val)).toThrow();
      }
    });
  });

  describe('Exact Arithmetic without Floating-Point Drift', () => {
    it('demonstrates exact addition where IEEE-754 floats fail (0.10 + 0.20 = 0.30)', () => {
      // In binary floating point: 0.1 + 0.2 === 0.30000000000000004
      expect(0.1 + 0.2).not.toBe(0.3);

      // In exact monetary utility:
      expect(addMonetary('0.10', '0.20')).toBe('0.30');
      expect(addCents(10n, 20n)).toBe(30n);
    });

    it('preserves exact balances across 10 consecutive subtractions of 0.29 without drift', () => {
      const initialBalance = '2500.00';
      const step = '0.29';
      let currentBalance = initialBalance;

      // In IEEE-754 float: 2500.0 - 0.29 * 10 = 2497.1000000000004
      let floatBalance = 2500.0;
      for (let i = 0; i < 10; i++) {
        floatBalance -= 0.29;
        currentBalance = subMonetary(currentBalance, step);
      }

      expect(floatBalance).not.toBe(2497.1);
      expect(floatBalance.toString()).toContain('2497.1000000000004');

      // Exact monetary utility has zero drift
      expect(currentBalance).toBe('2497.10');
      expect(parseToCents(currentBalance)).toBe(249710n);
    });

    it('correctly executes exact additions and subtractions', () => {
      expect(addMonetary('2499.56', '0.44')).toBe('2500.00');
      expect(subMonetary('2500.00', '0.10')).toBe('2499.90');
      expect(subCents(250000n, 10n)).toBe(249990n);
      expect(subMonetary('2499.90', '0.29')).toBe('2499.61');
      expect(subMonetary('2499.61', '0.05')).toBe('2499.56');
    });

    it('correctly performs exact comparisons', () => {
      expect(compareMonetary('100.00', '100.00')).toBe(0);
      expect(compareMonetary('100.00', '99.99')).toBe(1);
      expect(compareMonetary('99.99', '100.00')).toBe(-1);

      expect(compareCents(10000n, 10000n)).toBe(0);
      expect(compareCents(10001n, 10000n)).toBe(1);
      expect(compareCents(9999n, 10000n)).toBe(-1);
    });
  });

  describe('ROUND_HALF_UP Boundaries in Rational Operations', () => {
    it('verifies integer division ROUND_HALF_UP rounding logic', () => {
      // 3.4 rounds down to 3
      expect(divideHalfUp(34n, 10n)).toBe(3n);
      // 3.5 rounds up to 4
      expect(divideHalfUp(35n, 10n)).toBe(4n);
      // 3.6 rounds up to 4
      expect(divideHalfUp(36n, 10n)).toBe(4n);

      // Negative values
      expect(divideHalfUp(-34n, 10n)).toBe(-3n);
      expect(divideHalfUp(-35n, 10n)).toBe(-4n);
      expect(divideHalfUp(-36n, 10n)).toBe(-4n);
    });

    it('verifies ROUND_HALF_UP boundaries on specific currency conversions matching backend', () => {
      // 1. 0.04 EUR -> USD (rate 10/9)
      // 0.04 * 10 / 9 = 0.40 / 9 = 0.0444... rounds down to 0.04
      const res1 = convertCurrency('0.04', 'EUR', 'USD');
      expect(res1.destinationAmount).toBe('0.04');
      expect(res1.destinationCents).toBe(4n);
      expect(res1.rateNumerator).toBe(10n);
      expect(res1.rateDenominator).toBe(9n);

      // 2. 0.05 EUR -> USD (rate 10/9)
      // 0.05 * 10 / 9 = 0.50 / 9 = 0.0555... rounds up to 0.06
      const res2 = convertCurrency('0.05', 'EUR', 'USD');
      expect(res2.destinationAmount).toBe('0.06');
      expect(res2.destinationCents).toBe(6n);

      // 3. Exact half boundary: 0.04 GBP -> EUR (rate 9/8)
      // 0.04 * 9 / 8 = 0.36 / 8 = 0.045000 -> rounds UP to 0.05
      const res3 = convertCurrency('0.04', 'GBP', 'EUR');
      expect(res3.destinationAmount).toBe('0.05');
      expect(res3.destinationCents).toBe(5n);

      // 4. 0.02 GBP -> EUR (rate 9/8)
      // 0.02 * 9 / 8 = 0.18 / 8 = 0.0225 -> rounds down to 0.02
      const res4 = convertCurrency('0.02', 'GBP', 'EUR');
      expect(res4.destinationAmount).toBe('0.02');
      expect(res4.destinationCents).toBe(2n);
    });
  });

  describe('Approved Reference Rates and Rational Cross-Currency Conversions', () => {
    it('verifies the approved reference rates table', () => {
      expect(REFERENCE_RATES.USD.EUR).toEqual({ numerator: 9n, denominator: 10n });
      expect(REFERENCE_RATES.USD.GBP).toEqual({ numerator: 8n, denominator: 10n });
      expect(REFERENCE_RATES.EUR.USD).toEqual({ numerator: 10n, denominator: 9n });
      expect(REFERENCE_RATES.GBP.USD).toEqual({ numerator: 10n, denominator: 8n });
      expect(REFERENCE_RATES.EUR.GBP).toEqual({ numerator: 8n, denominator: 9n });
      expect(REFERENCE_RATES.GBP.EUR).toEqual({ numerator: 9n, denominator: 8n });
    });

    it('performs exact round-trip conversions USD <-> EUR', () => {
      // 100.00 USD -> EUR (rate 9/10) = 90.00 EUR
      const usdToEur = convertCurrency('100.00', 'USD', 'EUR');
      expect(usdToEur.destinationAmount).toBe('90.00');

      // 90.00 EUR -> USD (rate 10/9) = 100.00 USD
      const eurToUsd = convertCurrency(usdToEur.destinationAmount, 'EUR', 'USD');
      expect(eurToUsd.destinationAmount).toBe('100.00');
    });

    it('performs exact round-trip conversions EUR <-> GBP', () => {
      // 90.00 EUR -> GBP (rate 8/9) = 80.00 GBP
      const eurToGbp = convertCurrency('90.00', 'EUR', 'GBP');
      expect(eurToGbp.destinationAmount).toBe('80.00');

      // 80.00 GBP -> EUR (rate 9/8) = 90.00 EUR
      const gbpToEur = convertCurrency(eurToGbp.destinationAmount, 'GBP', 'EUR');
      expect(gbpToEur.destinationAmount).toBe('90.00');
    });

    it('performs exact round-trip conversions USD <-> GBP', () => {
      // 100.00 USD -> GBP (rate 8/10) = 80.00 GBP
      const usdToGbp = convertCurrency('100.00', 'USD', 'GBP');
      expect(usdToGbp.destinationAmount).toBe('80.00');

      // 80.00 GBP -> USD (rate 10/8) = 100.00 USD
      const gbpToUsd = convertCurrency(usdToGbp.destinationAmount, 'GBP', 'USD');
      expect(gbpToUsd.destinationAmount).toBe('100.00');
    });

    it('returns exact same amount for identity conversions (e.g. USD -> USD)', () => {
      const res = convertCurrency('2500.00', 'USD', 'USD');
      expect(res.destinationAmount).toBe('2500.00');
      expect(res.destinationCents).toBe(250000n);
      expect(res.rateNumerator).toBe(1n);
      expect(res.rateDenominator).toBe(1n);
    });

    it('rejects zero or negative conversion amounts', () => {
      expect(() => convertCurrency('0.00', 'USD', 'EUR')).toThrow();
      expect(() => convertCurrency('-10.00', 'USD', 'EUR')).toThrow();
    });
  });

  describe('Exact Financial Threshold Comparisons via Integer Cross-Multiplication', () => {
    it('verifies USD base factors', () => {
      expect(USD_BASE_FACTORS.USD).toEqual({ numerator: 1n, denominator: 1n });
      expect(USD_BASE_FACTORS.EUR).toEqual({ numerator: 10n, denominator: 9n });
      expect(USD_BASE_FACTORS.GBP).toEqual({ numerator: 10n, denominator: 8n });
    });

    it('exact comparison against $1,000.00 USD MFA threshold in USD', () => {
      const threshold = '1000.00';

      // 999.99 USD < 1000.00 USD
      expect(compareUsdEquivalentToThreshold('999.99', 'USD', threshold)).toBe(-1);
      expect(isUsdEquivalentExceedingThreshold('999.99', 'USD', threshold)).toBe(false);
      expect(isUsdEquivalentAtOrAboveThreshold('999.99', 'USD', threshold)).toBe(false);

      // 1000.00 USD == 1000.00 USD (exact boundary)
      expect(compareUsdEquivalentToThreshold('1000.00', 'USD', threshold)).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('1000.00', 'USD', threshold)).toBe(false);
      expect(isUsdEquivalentAtOrAboveThreshold('1000.00', 'USD', threshold)).toBe(true);

      // 1000.01 USD > 1000.00 USD
      expect(compareUsdEquivalentToThreshold('1000.01', 'USD', threshold)).toBe(1);
      expect(isUsdEquivalentExceedingThreshold('1000.01', 'USD', threshold)).toBe(true);
    });

    it('exact comparison against $1,000.00 USD MFA threshold in EUR (exact equivalent: 900.00 EUR)', () => {
      const threshold = '1000.00';

      // 900.00 EUR * 10 / 9 = 1000.00 USD exactly
      expect(compareUsdEquivalentToThreshold('900.00', 'EUR', threshold)).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('900.00', 'EUR', threshold)).toBe(false);
      expect(isUsdEquivalentAtOrAboveThreshold('900.00', 'EUR', threshold)).toBe(true);

      // 899.99 EUR < 1000.00 USD
      expect(compareUsdEquivalentToThreshold('899.99', 'EUR', threshold)).toBe(-1);
      expect(isUsdEquivalentExceedingThreshold('899.99', 'EUR', threshold)).toBe(false);

      // 900.01 EUR > 1000.00 USD
      expect(compareUsdEquivalentToThreshold('900.01', 'EUR', threshold)).toBe(1);
      expect(isUsdEquivalentExceedingThreshold('900.01', 'EUR', threshold)).toBe(true);
    });

    it('exact comparison against $1,000.00 USD MFA threshold in GBP (exact equivalent: 800.00 GBP)', () => {
      const threshold = '1000.00';

      // 800.00 GBP * 10 / 8 = 1000.00 USD exactly
      expect(compareUsdEquivalentToThreshold('800.00', 'GBP', threshold)).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('800.00', 'GBP', threshold)).toBe(false);
      expect(isUsdEquivalentAtOrAboveThreshold('800.00', 'GBP', threshold)).toBe(true);

      // 799.99 GBP < 1000.00 USD
      expect(compareUsdEquivalentToThreshold('799.99', 'GBP', threshold)).toBe(-1);
      expect(isUsdEquivalentExceedingThreshold('799.99', 'GBP', threshold)).toBe(false);

      // 800.01 GBP > 1000.00 USD
      expect(compareUsdEquivalentToThreshold('800.01', 'GBP', threshold)).toBe(1);
      expect(isUsdEquivalentExceedingThreshold('800.01', 'GBP', threshold)).toBe(true);
    });

    it('exact comparison against $5,000.00 per-transaction and $10,000.00 daily limits', () => {
      // Per-transaction limit: 5000.00 USD
      // In EUR: 4500.00 EUR == 5000.00 USD
      expect(compareUsdEquivalentToThreshold('4500.00', 'EUR', '5000.00')).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('4500.01', 'EUR', '5000.00')).toBe(true);

      // In GBP: 4000.00 GBP == 5000.00 USD
      expect(compareUsdEquivalentToThreshold('4000.00', 'GBP', '5000.00')).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('4000.01', 'GBP', '5000.00')).toBe(true);

      // Daily limit: 10000.00 USD
      // In EUR: 9000.00 EUR == 10000.00 USD
      expect(compareUsdEquivalentToThreshold('9000.00', 'EUR', '10000.00')).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('9000.01', 'EUR', '10000.00')).toBe(true);

      // In GBP: 8000.00 GBP == 10000.00 USD
      expect(compareUsdEquivalentToThreshold('8000.00', 'GBP', '10000.00')).toBe(0);
      expect(isUsdEquivalentExceedingThreshold('8000.01', 'GBP', '10000.00')).toBe(true);
    });
  });

  describe('Pure Decimal-String and BigInt Currency Formatting without Number or toFixed', () => {
    it('formats standard amounts with currency symbols and comma separators', () => {
      expect(formatCurrency('2500.00', 'USD')).toBe('$2,500.00');
      expect(formatCurrency('10000.00', 'USD')).toBe('$10,000.00');
      expect(formatCurrency('12500.00', 'USD')).toBe('$12,500.00');
      expect(formatCurrency('90.00', 'EUR')).toBe('€90.00');
      expect(formatCurrency('80.00', 'GBP')).toBe('£80.00');
    });

    it('formats small amounts and zero correctly', () => {
      expect(formatCurrency('0.00', 'USD')).toBe('$0.00');
      expect(formatCurrency('0', 'USD')).toBe('$0.00');
      expect(formatCurrency('0.05', 'USD')).toBe('$0.05');
      expect(formatCurrency('0.02', 'GBP')).toBe('£0.02');
      expect(formatCurrency('0.10', 'EUR')).toBe('€0.10');
      expect(formatCurrency('0.5', 'USD')).toBe('$0.50');
    });

    it('formats negative amounts correctly', () => {
      expect(formatCurrency('-10.50', 'USD')).toBe('-$10.50');
      expect(formatCurrency('-0.05', 'USD')).toBe('-$0.05');
      expect(formatCurrency('-2500.00', 'USD')).toBe('-$2,500.00');
    });

    it('accepts BigInt cents directly', () => {
      expect(formatCurrency(250000n, 'USD')).toBe('$2,500.00');
      expect(formatCurrency(5n, 'USD')).toBe('$0.05');
      expect(formatCurrency(0n, 'USD')).toBe('$0.00');
      expect(formatCurrency(-1050n, 'USD')).toBe('-$10.50');
    });

    it('handles fallback for non-symbol currencies', () => {
      expect(formatCurrency('100.00', 'CAD')).toBe('CAD 100.00');
    });

    it('rejects invalid inputs', () => {
      expect(() => formatCurrency('abc', 'USD')).toThrow();
      expect(() => formatCurrency('1.2.3', 'USD')).toThrow();
    });
  });

  describe('Exact Monocurrency Summation (sumCents, sumMonetary)', () => {
    it('accurately sums arrays of monetary values without floating point drift', () => {
      expect(sumMonetary(['2500.00', '10000.00'])).toBe('12500.00');
      expect(sumCents(['2500.00', '10000.00'])).toBe(1250000n);

      // Sum of 0.10 + 0.20
      expect(sumMonetary(['0.10', '0.20'])).toBe('0.30');

      // Ten 0.29 values = 2.90 exactly
      const tens = Array(10).fill('0.29');
      expect(sumMonetary(tens)).toBe('2.90');
    });

    it('handles empty and single-element arrays', () => {
      expect(sumMonetary([])).toBe('0.00');
      expect(sumCents([])).toBe(0n);
      expect(sumMonetary(['2500.00'])).toBe('2500.00');
    });
  });

  describe('Multicurrency Estimated Total (USD) with Single Final ROUND_HALF_UP (D-10, D-03)', () => {
    it('demonstrates that two GBP accounts of 0.02 GBP each equal 0.05 USD, not 0.06 USD', () => {
      // 1 GBP = 10/8 USD = 1.25 USD.
      // Account 1: 0.02 GBP = 2 cents * 10 / 8 = 2.5 cents unrounded.
      // Account 2: 0.02 GBP = 2 cents * 10 / 8 = 2.5 cents unrounded.
      // Independent rounding: 2.5 -> 3 cents ($0.03), 3 + 3 = 6 cents ($0.06 USD).
      // Unrounded accumulation: 2.5 + 2.5 = 5.0 cents -> rounds to 5 cents ($0.05 USD).
      const accounts = [
        { balance: '0.02', currency: 'GBP' },
        { balance: '0.02', currency: 'GBP' },
      ];

      expect(calculateEstimatedUsdTotalCents(accounts)).toBe(5n);
      expect(calculateEstimatedUsdTotal(accounts)).toBe('0.05');
    });

    it('demonstrates unrounded accumulation across three 0.01 GBP accounts', () => {
      // 0.01 GBP * 10 / 8 = 1.25 cents.
      // Three accounts: 1.25 * 3 = 3.75 cents -> divideHalfUp(30n, 8n) = 4 cents ($0.04).
      // Independent rounding would give: 1 + 1 + 1 = 3 cents ($0.03).
      const accounts = [
        { balance: '0.01', currency: 'GBP' },
        { balance: '0.01', currency: 'GBP' },
        { balance: '0.01', currency: 'GBP' },
      ];

      expect(calculateEstimatedUsdTotalCents(accounts)).toBe(4n);
      expect(calculateEstimatedUsdTotal(accounts)).toBe('0.04');
    });

    it('demonstrates unrounded accumulation across EUR accounts', () => {
      // 1 EUR = 10/9 USD = 1.111... USD.
      // Account 1: 0.04 EUR = 40/9 = 4.444... cents (rounds to 4 cents).
      // Account 2: 0.04 EUR = 40/9 = 4.444... cents (rounds to 4 cents).
      // Independent sum = 4 + 4 = 8 cents ($0.08).
      // Unrounded sum: 80/9 = 8.888... cents -> rounds to 9 cents ($0.09).
      const accounts = [
        { balance: '0.04', currency: 'EUR' },
        { balance: '0.04', currency: 'EUR' },
      ];

      expect(calculateEstimatedUsdTotalCents(accounts)).toBe(9n);
      expect(calculateEstimatedUsdTotal(accounts)).toBe('0.09');
    });

    it('accurately computes portfolio estimated USD total matching seed accounts', () => {
      const accounts = [
        { balance: '2500.00', currency: 'USD' },
        { balance: '10000.00', currency: 'USD' },
        { balance: '90.00', currency: 'EUR' },
        { balance: '80.00', currency: 'GBP' },
      ];

      // USD: 12500.00
      // EUR: 90.00 * 10 / 9 = 100.00 USD
      // GBP: 80.00 * 10 / 8 = 100.00 USD
      // Total: 12700.00 USD
      expect(calculateEstimatedUsdTotal(accounts)).toBe('12700.00');
      expect(calculateEstimatedUsdTotalCents(accounts)).toBe(1270000n);
    });

    it('handles empty portfolio gracefully', () => {
      expect(calculateEstimatedUsdTotal([])).toBe('0.00');
      expect(calculateEstimatedUsdTotalCents([])).toBe(0n);
    });

    it('verifies exact greatest common divisor computation for rational reduction', () => {
      expect(gcd(54n, 24n)).toBe(6n);
      expect(gcd(20n, 8n)).toBe(4n);
      expect(gcd(80n, 16n)).toBe(16n);
      expect(gcd(7n, 13n)).toBe(1n);
      expect(gcd(-20n, 8n)).toBe(4n);
    });

    it('throws on unsupported currency in portfolio', () => {
      expect(() =>
        calculateEstimatedUsdTotal([{ balance: '100.00', currency: 'JPY' }])
      ).toThrow('Unsupported currency for USD equivalent calculation: JPY');
    });

    it('formats rational rates into exact 4-decimal strings with ROUND_HALF_UP', () => {
      // 9/10 USD -> EUR
      expect(formatRationalRate(9n, 10n)).toBe('0.9000');
      // 10/9 EUR -> USD (1.111111...)
      expect(formatRationalRate(10n, 9n)).toBe('1.1111');
      // 8/10 USD -> GBP
      expect(formatRationalRate(8n, 10n)).toBe('0.8000');
      // 10/8 GBP -> USD
      expect(formatRationalRate(10n, 8n)).toBe('1.2500');
      // 8/9 EUR -> GBP (0.888888... rounds up to 0.8889)
      expect(formatRationalRate(8n, 9n)).toBe('0.8889');
      // 9/8 GBP -> EUR
      expect(formatRationalRate(9n, 8n)).toBe('1.1250');
      // Division by zero throws
      expect(() => formatRationalRate(1n, 0n)).toThrow();
    });
  });
});
