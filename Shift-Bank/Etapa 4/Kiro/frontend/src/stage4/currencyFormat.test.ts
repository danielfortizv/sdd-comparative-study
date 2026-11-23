// Pruebas del formateo multidivisa de la Etapa 4 (D-03, D-10). Montos como string/bigint, nunca
// number; totales separados por moneda; USD estimado solo para visualización.

import { describe, expect, it } from "vitest";
import {
  formatMoney,
  fromMinor,
  groupByCurrency,
  toMinor,
  usdEstimateMinor,
} from "./currencyFormat";

describe("conversión de unidades menores (bigint)", () => {
  it("toMinor/fromMinor son inversos exactos", () => {
    expect(toMinor("2500.00")).toBe(250000n);
    expect(fromMinor(250000n)).toBe("2500.00");
    expect(toMinor("0.00")).toBe(0n);
    expect(fromMinor(90_00n)).toBe("90.00");
  });
});

describe("formato con símbolo y moneda", () => {
  it("formatea con separadores de miles y 2 decimales", () => {
    expect(formatMoney("2500.00", "USD")).toBe("$2,500.00 USD");
    expect(formatMoney("90.00", "EUR")).toBe("€90.00 EUR");
    expect(formatMoney("0.00", "GBP")).toBe("£0.00 GBP");
  });
});

describe("estimación USD (solo visualización) con bigint y HALF_UP", () => {
  it("90.00 EUR estima 100.00 USD exacto", () => {
    expect(usdEstimateMinor(90_00n, "EUR")).toBe(100_00n);
  });
  it("80.00 GBP estima 100.00 USD exacto", () => {
    expect(usdEstimateMinor(80_00n, "GBP")).toBe(100_00n);
  });
  it("USD se estima a sí mismo", () => {
    expect(usdEstimateMinor(2500_00n, "USD")).toBe(2500_00n);
  });
});

describe("agrupación por moneda (sin mezclar) y total estimado", () => {
  it("agrupa saldos por moneda y estima el total USD", () => {
    const { perCurrency, usdEstimate } = groupByCurrency([
      { currency: "USD", balance: "2500.00" },
      { currency: "USD", balance: "10000.00" },
      { currency: "EUR", balance: "90.00" },
      { currency: "GBP", balance: "80.00" },
    ]);
    expect(perCurrency).toEqual({ USD: "12500.00", EUR: "90.00", GBP: "80.00" });
    // 12500 USD + 100 (EUR) + 100 (GBP) = 12700.00 USD estimado.
    expect(usdEstimate).toBe("12700.00");
  });
});
