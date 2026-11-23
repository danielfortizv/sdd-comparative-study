"""Motor de conversión de divisas exacto (Etapa 4, Tarea 7; D-03, D-07).

Conversión entre monedas soportadas usando **tasas racionales fijas** (`fractions.Fraction`),
sin servicio externo de tasas en vivo y sin aritmética de punto flotante. El redondeo a unidades
menores se aplica con `ROUND_HALF_UP` **una sola vez al final** (D-03).

Modelo de unidades: todos los montos internos son **unidades menores enteras** (centavos) de su
moneda; todas las monedas soportadas tienen 2 decimales. Las tasas en `config.FX_RATES_PER_USD`
se expresan como "unidades de la moneda por 1 USD" (p. ej. EUR = 9/10 por USD).

Decisiones honradas:
- `convert(amount_minor, src, dst)` calcula el destino como `Fraction` exacta y cuantiza a
  unidades menores con `ROUND_HALF_UP` una sola vez (D-03). `src == dst` es identidad exacta.
- `usd_equivalent_minor_unrounded(amount_minor, ccy)` devuelve el equivalente USD **sin
  redondear** como `Fraction`, para el umbral de MFA estricto `> 1,000.00` (D-07).
- `usd_equivalent_minor(amount_minor, ccy)` devuelve el equivalente USD redondeado a centavos USD
  (`ROUND_HALF_UP` una vez), para la verificación de límites (D-07).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

from . import config


class UnsupportedCurrencyError(ValueError):
    """La moneda solicitada no pertenece al conjunto soportado (D-01)."""


def is_supported(currency: str) -> bool:
    """True si `currency` está en el conjunto cerrado de monedas soportadas (D-01)."""
    return currency in config.SUPPORTED_CURRENCIES


def _require_supported(currency: str) -> None:
    if not is_supported(currency):
        raise UnsupportedCurrencyError(f"Moneda no soportada: {currency!r}")


def _rate_per_usd(currency: str) -> Fraction:
    """Tasa racional exacta: unidades de `currency` por 1 USD (desde `config`)."""
    _require_supported(currency)
    return Fraction(config.FX_RATES_PER_USD[currency])


def rate(src: str, dst: str) -> Fraction:
    """Tasa racional exacta aplicada para convertir de `src` a `dst` (unidades dst por unidad src).

    rate(src, dst) = (dst_por_usd) / (src_por_usd). Para `src == dst` es exactamente 1.
    """
    _require_supported(src)
    _require_supported(dst)
    if src == dst:
        return Fraction(1)
    return _rate_per_usd(dst) / _rate_per_usd(src)


def _round_half_up_to_int(value: Fraction) -> int:
    """Cuantiza una `Fraction` a entero con `ROUND_HALF_UP` una sola vez (D-03).

    Se usa `Decimal` solo como vehículo de redondeo determinista; el valor de entrada es exacto
    (Fraction), por lo que no hay pérdida de punto flotante antes del redondeo final.
    """
    dec = Decimal(value.numerator) / Decimal(value.denominator)
    return int(dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def convert(amount_minor: int, src: str, dst: str) -> tuple[int, Fraction]:
    """Convierte `amount_minor` (unidades menores de `src`) a unidades menores de `dst`.

    Devuelve `(dest_minor, rate_aplicada)`. El redondeo `ROUND_HALF_UP` se aplica **una sola vez
    al final** sobre el producto exacto. `src == dst` devuelve el mismo monto (identidad).

    Raises:
        UnsupportedCurrencyError: si `src` o `dst` no están soportadas.
    """
    r = rate(src, dst)
    if src == dst:
        return amount_minor, r
    exact = Fraction(amount_minor) * r
    return _round_half_up_to_int(exact), r


def usd_equivalent_minor_unrounded(amount_minor: int, currency: str) -> Fraction:
    """Equivalente en centavos USD **sin redondear** (Fraction exacta) de `amount_minor` de `currency`.

    Para el umbral de MFA estricto `> 1,000.00` (D-07): la comparación usa este valor sin redondear.
    """
    _require_supported(currency)
    if currency == "USD":
        return Fraction(amount_minor)
    # amount_minor (en `currency`) / (currency_por_usd) = USD_minor exacto.
    return Fraction(amount_minor) / _rate_per_usd(currency)


def usd_equivalent_minor(amount_minor: int, currency: str) -> int:
    """Equivalente en centavos USD **redondeado** (`ROUND_HALF_UP` una vez) para límites (D-07)."""
    return _round_half_up_to_int(usd_equivalent_minor_unrounded(amount_minor, currency))


def requires_mfa_usd(amount_minor: int, currency: str) -> bool:
    """True si el equivalente USD SIN redondear es estrictamente > USD 1,000.00 (D-07)."""
    threshold_minor = Fraction(int(config.MFA_THRESHOLD_USD * 100))
    return usd_equivalent_minor_unrounded(amount_minor, currency) > threshold_minor
