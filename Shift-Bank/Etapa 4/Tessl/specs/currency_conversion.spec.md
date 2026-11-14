---
name: Currency Conversion
description: Simulated foreign exchange conversion between distinct user accounts with deterministic rates, exact Decimal rounding, and atomic CQRS/Event Sourcing integration
targets:
  - ../backend/app/routers/conversions.py
  - ../backend/app/services/conversion_service.py
  - ../backend/app/services/event_store.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/ConversionModal.tsx
---

# Currency Conversion

Provides capabilities for the authenticated mock user (`Alex Morgan`, `user_id=1`) to execute simulated currency conversions between distinct owned accounts denominated in different supported currencies (`USD`, `EUR`, `GBP`).

Conversions are governed by Researcher Decisions D-01, D-03, D-04, D-07, D-09, D-10, D-11, D-13, and D-14 and SEED-4 Items 1, 2, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class ConversionRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    source_amount: Decimal = Field(..., gt=0, description="Source amount to convert; strictly positive, max 2 decimals") # [MODIFIED D-03]
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account for optimistic concurrency")
    expected_to_version: int = Field(..., ge=0, description="Expected version of destination account for optimistic concurrency")
    description: Optional[str] = None
    pin: Optional[str] = None  # Required if USD-equivalent amount > 1000.00

class ConversionResponse(BaseModel):
    id: int
    operation_id: str                      # Unique UUID of conversion operation
    from_account_id: int
    to_account_id: int
    source_currency: str                   # "USD" | "EUR" | "GBP"
    destination_currency: str              # "USD" | "EUR" | "GBP"
    source_amount: Decimal                 # Exact debited source amount (2 decimals) [MODIFIED D-03]
    destination_amount: Decimal            # Converted & rounded credited amount (2 decimals) [MODIFIED D-03]
    exchange_rate_display: Decimal         # Applied exchange rate formatted to up to 10 decimal places [MODIFIED D-03]
    rate_numerator: int                    # Exact rational numerator (e.g. 80)
    rate_denominator: int                  # Exact rational denominator (e.g. 90)
    rate_version: str                      # "v1.0-simulated"
    rounding_residual: Decimal             # Destination-cent rounding residual (|residual| <= 0.005) [MODIFIED D-03]
    from_account_version: int              # Incremented version of source account
    to_account_version: int                # Incremented version of destination account
    status: str                            # "completed"
    created_at: datetime
```

## Supported Currencies and Operational Boundaries

- Supported Currencies: Exactly `USD`, `EUR`, and `GBP` (ISO 4217). Each account holds a single fixed currency and balance. [NEW D-01]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Dedicated Banking Operation: Currency conversion is exposed exclusively through `POST /api/conversions` and a dedicated UI modal/workflow. Legacy endpoint `POST /api/transfers` is preserved strictly for same-currency internal transfers. [NEW D-04]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Cross-Currency Rejection on Legacy Transfers: Calling `POST /api/transfers` between accounts of different currencies must fail with HTTP 400 Bad Request (`CROSS_CURRENCY_NOT_PERMITTED`) without modifying balances or generating events. [NEW D-04]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Distinct Accounts Requirement: A conversion must involve two distinct existing accounts owned by the user (`from_account_id != to_account_id`) with different currencies (`from_account.currency != to_account.currency`). Same-account conversions or conversions between same-currency accounts fail with HTTP 400 Bad Request. [NEW D-01, D-04]
  `[@test] ../backend/tests/test_currency_conversion.py`

## Exchange Rate Mechanics, Precision & Rounding Rules

- Fixed Internal Simulated Reference Rates:
  - `1 USD = 1.00 USD` (Base factor: 1.00)
  - `1 USD = 0.90 EUR` (Base factor: 0.90)
  - `1 USD = 0.80 GBP` (Base factor: 0.80)
  No external live FX APIs are called; no rate-editing workflow is provided. [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Exact Cross & Inverse Rate Derivation: All directional pairs are derived from the single reference table as rational values:
  `effective_rate(S -> D) = USD_base_factor(D) / USD_base_factor(S)`.
  - `EUR -> GBP = 0.80 / 0.90` (rational 8/9)
  - `GBP -> EUR = 0.90 / 0.80` (rational 9/8)
  - `EUR -> USD = 1.00 / 0.90` (rational 10/9)
  - `GBP -> USD = 1.00 / 0.80` (rational 5/4)
  Calculations must never use pre-rounded or floating-point intermediate approximations. [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Zero Fees & Spreads: No conversion fees, commissions, or spreads. Source debit equals requested source amount; destination credit equals the converted and quantized destination amount. [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Monetary Precision & Non-Floating-Point Arithmetic: All monetary operations use exact `Decimal` or integer-minor-unit arithmetic (cents/minor units = 0.01). Amounts with more than 2 decimal places are rejected with HTTP 422. Binary floating-point math is strictly forbidden. [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Destination Rounding: The unrounded destination amount is computed from the exact rational rate, then quantized ONCE to 2 decimal places using `ROUND_HALF_UP` (ties away from zero).
  - Example 1: `100.00 USD -> 90.00 EUR`
  - Example 2: `90.00 EUR -> 80.00 GBP`
  - Example 3: `0.05 USD -> 0.05 EUR` (since `0.05 * 0.90 = 0.045`, rounding half-up gives `0.05 EUR`)
  `[@test] ../backend/tests/test_currency_conversion.py`
- Zero-Amount Rejection: If the rounded destination amount equals `0.00`, the conversion is rejected with HTTP 400 Bad Request (`CONVERSION_AMOUNT_TOO_SMALL`). [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Rounding Traceability: The rounding residual (`destination_amount - unrounded_destination_amount`, with `|residual| <= 0.005`) is recorded with the conversion. [NEW D-03]
  `[@test] ../backend/tests/test_currency_conversion.py`

## Financial Limits & MFA Security Integration

- Common Reference Currency: Limits and MFA thresholds are evaluated in USD equivalent:
  `USD_equivalent = source_amount / USD_base_factor(source_currency)`.
  The USD equivalent is compared without prior rounding against configured limits using exact Decimal arithmetic. [NEW D-07]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Dynamic Transfer Limits:
  - Fails with HTTP 400 if `USD_equivalent > per_transaction_limit` ($5,000.00 default).
  - Fails with HTTP 400 if `USD_equivalent + current_daily_total > daily_limit` ($10,000.00 default).
  - Successful conversions contribute their exact source debit `USD_equivalent` once to the shared daily total. [NEW D-07]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Mock MFA Threshold:
  - If `USD_equivalent <= 1000.00`, executes immediately without PIN.
  - If `USD_equivalent > 1000.00`, requires valid Security PIN (`1234`). Missing PIN returns HTTP 428 `MfaRequiredResponse`. Incorrect PIN decrements attempts; 3 failures locks account (HTTP 423). [NEW D-07]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Validation Order: Balance and dynamic limit checks are strictly validated before MFA authorization. A correct PIN never overrides insufficient funds or limit violations. [NEW D-07]
  `[@test] ../backend/tests/test_currency_conversion.py`

## Idempotency and Optimistic Concurrency Control

- Mandatory Idempotency Header: Every request to `POST /api/conversions` must include an `Idempotency-Key` HTTP header containing a valid UUID. [NEW D-13]
  - Missing header returns HTTP 400 with code `MISSING_IDEMPOTENCY_KEY`.
  - Malformed header returns HTTP 400 with code `INVALID_IDEMPOTENCY_KEY`.
  `[@test] ../backend/tests/test_currency_conversion.py`
- Idempotent Replay: Retrying with the same `Idempotency-Key` and identical request parameters returns the original committed `ConversionResponse` without re-executing debits, credits, events, or audit records. [NEW D-13]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Parameter Conflict: Reusing an `Idempotency-Key` with different request parameters returns HTTP 409 Conflict with code `IDEMPOTENCY_KEY_REUSE`. [NEW D-13]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Optimistic Concurrency Validation: Compares `expected_from_version` and `expected_to_version` against authoritative account versions. If either is stale, rejects with HTTP 409 Conflict with code `ACCOUNT_VERSION_CONFLICT`. [NEW D-14]
  `[@test] ../backend/tests/test_currency_conversion.py`

## Event Sourcing, CQRS & Audit Integration

- Atomic Operation Event: A successful conversion appends ONE immutable domain event of type `CurrencyConversionCompleted` recording both accounts, currencies, exact decimal amounts, rate version, rational factors, and incremented account versions. [NEW D-09]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Single Transaction Commit: The `CurrencyConversionCompleted` event, CQRS read projection updates (both account balances and transaction history rows), and the Stage 3 HMAC audit log entry commit in ONE SQLite database transaction. [NEW D-06, D-09]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Dual Account Version Advancement: Advances both `from_account` and `to_account` versions by +1 atomically. [NEW D-14]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Independent HMAC Audit Ledger: Emits an immutable audit log entry `currency_conversion` with `status="SUCCESS"` on success and `status="FAILURE"` on rejected attempts. Failed conversions do not produce domain events or alter balances. [NEW D-11]
  `[@test] ../backend/tests/test_currency_conversion.py`
- Deterministic Replay: Event replay and projection rebuilding reproduce the original converted amounts and rates exactly, without recalculation. [NEW D-03, D-06]
  `[@test] ../backend/tests/test_currency_conversion.py`

## User Interface Display & Workflow

- Conversion Modal allows selecting source account and destination account (filtered to accounts with different currencies). [NEW D-04]
  `[@test] ../frontend/src/__tests__/ConversionModal.test.tsx`
- Displays the applied simulated exchange rate and live calculated destination amount as the user types the source amount, using integer cents or decimal string math to eliminate JavaScript floating-point errors. [NEW D-03, D-10]
  `[@test] ../frontend/src/__tests__/ConversionModal.test.tsx`
- Automatically intercepts conversions with USD-equivalent `> $1,000.00` to prompt for the MFA Security PIN. [NEW D-07]
  `[@test] ../frontend/src/__tests__/ConversionModal.test.tsx`
- Generates a unique UUID `Idempotency-Key` for each submission and supplies the latest `expected_from_version` and `expected_to_version` from account state. [NEW D-13, D-14]
  `[@test] ../frontend/src/__tests__/ConversionModal.test.tsx`
- On HTTP 409 `ACCOUNT_VERSION_CONFLICT`, refreshes account balances and versions and notifies the user of updated financial state without silent resubmission. [NEW D-14]
  `[@test] ../frontend/src/__tests__/ConversionModal.test.tsx`
