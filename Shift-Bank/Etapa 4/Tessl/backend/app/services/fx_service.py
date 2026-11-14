from decimal import Decimal, ROUND_HALF_UP
from math import gcd
from typing import Tuple, Dict

# Approved deterministic fixed reference rates for Stage 4 (D-03)
# 1 USD = 1.00 USD, 1 USD = 0.90 EUR, 1 USD = 0.80 GBP
BASE_FACTORS: Dict[str, Decimal] = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("0.90"),
    "GBP": Decimal("0.80"),
}

SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP"}


def get_usd_equivalent(amount: Decimal, currency: str) -> Decimal:
    """
    Calculate unrounded USD equivalent for financial limit and MFA threshold comparisons (D-07).
    USD_equivalent = source_amount / USD_base_factor(source_currency).
    Never round before threshold comparisons.
    """
    if currency not in BASE_FACTORS:
        raise ValueError(f"Unsupported currency: {currency}")
    factor = BASE_FACTORS[currency]
    return amount / factor


def get_rational_rate(source_currency: str, destination_currency: str) -> Tuple[int, int]:
    """
    Derive exact rational rate factors (numerator, denominator) from the single reference table (D-03).
    effective_rate(S -> D) = USD_base_factor(D) / USD_base_factor(S).
    """
    if source_currency not in BASE_FACTORS or destination_currency not in BASE_FACTORS:
        raise ValueError(f"Unsupported currency pair: {source_currency} -> {destination_currency}")

    # Multiply by 100 to get exact integers
    int_d = int(BASE_FACTORS[destination_currency] * 100)
    int_s = int(BASE_FACTORS[source_currency] * 100)

    common = gcd(int_d, int_s)
    return int_d // common, int_s // common


def calculate_conversion(
    source_amount: Decimal, source_currency: str, destination_currency: str
) -> Tuple[Decimal, Decimal, int, int, Decimal]:
    """
    Execute simulated currency conversion calculation according to D-03:
    1. Calculate unrounded destination amount from exact rational rate.
    2. Quantize ONCE to 2 decimal places using ROUND_HALF_UP.
    3. Return (destination_amount, exchange_rate_display, rate_num, rate_den, rounding_residual).
    """
    if source_amount <= Decimal("0.00"):
        raise ValueError("Conversion amount must be strictly positive")

    num, den = get_rational_rate(source_currency, destination_currency)

    # Unrounded exact destination value
    unrounded_dest = (source_amount * Decimal(num)) / Decimal(den)

    # Quantize once to 2 decimals with ROUND_HALF_UP
    destination_amount = unrounded_dest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if destination_amount <= Decimal("0.00"):
        raise ValueError("Conversion amount too small; resulting amount would be zero")

    rounding_residual = (destination_amount - unrounded_dest).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
    exchange_rate_display = (Decimal(num) / Decimal(den)).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)

    return destination_amount, exchange_rate_display, num, den, rounding_residual
