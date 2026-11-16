import { describe, expect, test } from 'vitest';
import { decimalToMinorUnitsString, formatDecimalMoney, parseMinorUnits } from './money';

describe('exact monetary input helpers', () => {
  test('parses decimal strings into integer minor units without floating point', () => {
    expect(decimalToMinorUnitsString('2500')).toBe('250000');
    expect(parseMinorUnits('10000.05')).toBe(1000005n);
  });

  test('rejects excess precision, signs, exponent notation, and malformed values', () => {
    for (const value of ['1.001', '-1.00', '+1.00', '1e3', '.50', '01.00']) {
      expect(() => parseMinorUnits(value)).toThrow();
    }
  });

  test('formats large balances and exact cents without Number conversion', () => {
    expect(formatDecimalMoney('15000000.01', 'COP', 'en-US')).toBe('COP 15,000,000.01');
    expect(formatDecimalMoney('15000000.01', 'COP', 'es-CO')).toBe('COP 15.000.000,01');
  });
});
