"""Utilidades monetarias decimal-safe (Requisito 3.5).

El dinero se almacena en SQLite como centavos enteros, se opera en Python con `Decimal`
y se transporta en la API como cadenas decimales (decimal-string). Este módulo concentra
todas las conversiones para evitar aritmética de punto flotante.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Dos decimales canónicos para todos los montos.
_CENTS = Decimal("0.01")


class InvalidAmountError(ValueError):
    """El monto recibido no es una cadena decimal válida (p. ej. no numérico o >2 decimales)."""


def cents_to_decimal(cents: int) -> Decimal:
    """Convierte centavos enteros a un `Decimal` con 2 decimales."""
    return (Decimal(cents) / Decimal(100)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def decimal_to_cents(value: Decimal) -> int:
    """Convierte un `Decimal` a centavos enteros, validando que no haya pérdida.

    Cuantiza a 2 decimales con `ROUND_HALF_UP` y multiplica por 100.
    """
    quantized = value.quantize(_CENTS, rounding=ROUND_HALF_UP)
    cents = quantized * Decimal(100)
    # El resultado debe ser entero exacto tras cuantizar a 2 decimales.
    if cents != cents.to_integral_value():
        raise InvalidAmountError("El monto no se puede representar en centavos exactos")
    return int(cents)


def parse_amount(raw: str) -> Decimal:
    """Convierte la cadena decimal del request a `Decimal`.

    Rechaza entradas no numéricas, notación no decimal (p. ej. científica) y montos
    con más de 2 decimales.
    """
    if not isinstance(raw, str):
        raise InvalidAmountError("El monto debe enviarse como cadena decimal")
    text = raw.strip()
    if text == "":
        raise InvalidAmountError("El monto no puede estar vacío")
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise InvalidAmountError("El monto no es un decimal válido") from exc
    # Rechazar NaN/Infinity y notación no finita.
    if not value.is_finite():
        raise InvalidAmountError("El monto no es un decimal finito")
    # Rechazar más de 2 decimales.
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise InvalidAmountError("El monto no puede tener más de 2 decimales")
    return value


def format_amount(value: Decimal) -> str:
    """Produce la cadena decimal canónica con 2 decimales (p. ej. `"1000000.00"`)."""
    return str(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def format_cents(cents: int) -> str:
    """Atajo: centavos enteros a cadena decimal canónica."""
    return format_amount(cents_to_decimal(cents))
