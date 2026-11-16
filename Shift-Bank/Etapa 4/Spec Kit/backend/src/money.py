"""Exact monetary helpers for the Stage 4 currency domain."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction

CENT = Decimal("0.01")
RATE_PAIRS = {
    ("USD", "EUR"): (9, 10),
    ("USD", "GBP"): (8, 10),
    ("EUR", "USD"): (10, 9),
    ("GBP", "USD"): (10, 8),
    ("EUR", "GBP"): (8, 9),
    ("GBP", "EUR"): (9, 8),
}
RATES = {pair: Fraction(*ratio) for pair, ratio in RATE_PAIRS.items()}


def parse_amount(value: str) -> Decimal:
    if not isinstance(value, str) or not value or any(c in value.lower() for c in ("e", "nan", "inf")):
        raise ValueError("Amount must be a plain decimal string")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError("Amount must be a plain decimal string") from None
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Amount must be positive with at most two decimal places")
    return amount.quantize(CENT)


def to_minor(amount: Decimal | str) -> int:
    value = Decimal(amount)
    if not value.is_finite() or value.as_tuple().exponent < -2:
        raise ValueError("Amount has excess precision")
    return int(value * 100)


def from_minor(minor: int) -> Decimal:
    if isinstance(minor, bool) or not isinstance(minor, int):
        raise TypeError("Minor units must be an integer")
    return (Decimal(minor) / 100).quantize(CENT)


def format_minor(minor: int) -> str:
    return f"{from_minor(minor):.2f}"


def convert_minor(source_minor: int, source: str, destination: str) -> tuple[int, int, int]:
    if source == "COP" or destination == "COP" or (source, destination) not in RATES:
        raise ValueError("Unsupported currency pair")
    rate = RATES[(source, destination)]
    exact_destination_minor = Fraction(source_minor) * rate
    # One HALF_UP rounding at the destination minor-unit boundary.
    quotient, remainder = divmod(exact_destination_minor.numerator, exact_destination_minor.denominator)
    rounded = quotient + (1 if remainder * 2 >= exact_destination_minor.denominator else 0)
    numerator, denominator = RATE_PAIRS[(source, destination)]
    return rounded, numerator, denominator


def usd_equivalent_minor(amount_minor: int, currency: str) -> Fraction:
    if currency == "USD":
        return Fraction(amount_minor)
    if currency in ("EUR", "GBP"):
        return Fraction(amount_minor) * RATES[(currency, "USD")]
    raise ValueError("COP has no approved USD equivalent")


def requires_mfa(amount_minor: int, currency: str) -> bool:
    if currency == "COP":
        return amount_minor >= 100_000_000
    return usd_equivalent_minor(amount_minor, currency) > 100_000


def within_non_cop_limits(amount_minor: int, currency: str) -> bool:
    equivalent = usd_equivalent_minor(amount_minor, currency)
    return equivalent <= 500_000 and equivalent <= 1_000_000
