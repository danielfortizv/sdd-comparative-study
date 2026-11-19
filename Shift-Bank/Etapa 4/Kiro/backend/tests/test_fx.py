"""Verificación del motor FX exacto de la Etapa 4 (Tarea 7; D-03, D-07).

Cubre: tasas racionales fijas, identidad `src==dst`, `ROUND_HALF_UP` aplicado una sola vez,
determinismo para igual entrada, equivalente USD (sin redondear y redondeado) y el umbral de MFA
estricto en equivalente USD.

_Requisitos: R3, R4, R11_ · _Diseño: §2_ · _AC: AC4-04, AC4-05, AC4-06, AC4-17_
"""

from fractions import Fraction

import pytest

from app import fx


def test_identidad_misma_moneda():
    # src == dst: identidad exacta, tasa 1, sin redondeo que altere el monto.
    for ccy in ("USD", "EUR", "GBP"):
        dest, r = fx.convert(123_45, ccy, ccy)
        assert dest == 123_45
        assert r == Fraction(1)


def test_conversion_usd_a_eur_half_up_una_vez():
    # 1 USD = 0.90 EUR -> 100.00 USD => 90.00 EUR exacto.
    dest, r = fx.convert(100_00, "USD", "EUR")
    assert dest == 90_00
    assert r == Fraction(9, 10)


def test_conversion_usd_a_gbp():
    # USD/GBP = 8/10 -> 250.00 USD => 200.00 GBP exacto.
    dest, r = fx.convert(250_00, "USD", "GBP")
    assert dest == 200_00
    assert r == Fraction(8, 10)


def test_matriz_oficial_de_tasas_de_la_guia():
    # Tasas exactas de la guía Etapa 4 (racionales).
    assert fx.rate("USD", "EUR") == Fraction(9, 10)
    assert fx.rate("USD", "GBP") == Fraction(8, 10)
    assert fx.rate("EUR", "USD") == Fraction(10, 9)
    assert fx.rate("GBP", "USD") == Fraction(10, 8)
    assert fx.rate("EUR", "GBP") == Fraction(8, 9)
    assert fx.rate("GBP", "EUR") == Fraction(9, 8)


def test_round_half_up_se_aplica_una_sola_vez():
    # EUR -> USD con un monto que fuerza medio centavo: 0.90 EUR por USD.
    # 1 EUR (100 minor) / (9/10) = 111.111... USD_minor -> 111 (HALF_UP una vez).
    dest, _ = fx.convert(1_00, "EUR", "USD")
    assert dest == 111
    # 5 EUR -> USD: 500 / (9/10) = 555.55... -> 556.
    dest5, _ = fx.convert(5_00, "EUR", "USD")
    assert dest5 == 556


def test_determinismo_misma_entrada():
    a = fx.convert(333_33, "EUR", "GBP")
    b = fx.convert(333_33, "EUR", "GBP")
    assert a == b


def test_ida_y_vuelta_conserva_bajo_reglas_de_redondeo():
    # Ida y vuelta puede diferir por redondeo documentado, pero nunca crea/destruye valor fuera
    # de +-1 unidad menor por el HALF_UP final.
    original = 1000_00
    eur, _ = fx.convert(original, "USD", "EUR")
    back, _ = fx.convert(eur, "EUR", "USD")
    assert abs(back - original) <= 1


def test_usd_equivalent_unrounded_es_fraction_exacta():
    # 100.00 EUR sin redondear = 100.00 / (9/10) = 1000/9 * 100 ... comprobamos exactitud.
    val = fx.usd_equivalent_minor_unrounded(90_00, "EUR")
    assert val == Fraction(90_00) / Fraction(9, 10)
    assert val == Fraction(100_00)  # 90.00 EUR == 100.00 USD exacto


def test_usd_equivalent_redondeado_para_limites():
    assert fx.usd_equivalent_minor(90_00, "EUR") == 100_00
    assert fx.usd_equivalent_minor(80_00, "GBP") == 100_00
    assert fx.usd_equivalent_minor(5000_00, "USD") == 5000_00


def test_requires_mfa_usd_umbral_estricto():
    # Exactamente 1000.00 USD NO requiere MFA (estricto >).
    assert fx.requires_mfa_usd(1000_00, "USD") is False
    # 1000.01 USD sí.
    assert fx.requires_mfa_usd(1000_01, "USD") is True
    # 900.00 EUR == 1000.00 USD exacto -> NO requiere (estricto, sin redondear).
    assert fx.requires_mfa_usd(900_00, "EUR") is False
    # 900.01 EUR -> > 1000.00 USD sin redondear -> sí.
    assert fx.requires_mfa_usd(900_01, "EUR") is True


def test_moneda_no_soportada_rechazada():
    with pytest.raises(fx.UnsupportedCurrencyError):
        fx.convert(100, "USD", "JPY")
    with pytest.raises(fx.UnsupportedCurrencyError):
        fx.usd_equivalent_minor(100, "JPY")
