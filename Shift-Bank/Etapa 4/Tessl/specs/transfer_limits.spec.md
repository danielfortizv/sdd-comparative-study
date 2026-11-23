---
name: Dynamic Transfer Limits
description: Configurable per-transaction and daily cumulative transfer limits in USD reference currency across internal transfers, conversions, and ACH operations with exact Decimal precision
targets:
  - ../backend/app/routers/limits.py
  - ../backend/app/services/limit_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferLimits.tsx
---

# Dynamic Transfer Limits

Provides configurable per-transaction and daily cumulative transfer limits denominated in USD reference currency that gate financial operations across all supported currencies using exact Decimal arithmetic.

Governed by Researcher Decisions D-01, D-03, D-04, and D-07 and SEED-4 Items 2, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class TransferLimitsResponse(BaseModel):
    per_transaction_limit: Decimal # default: Decimal("5000.00") (denominated in USD) [MODIFIED D-03]
    daily_limit: Decimal           # default: Decimal("10000.00") (denominated in USD) [MODIFIED D-03]
    current_daily_total: Decimal   # sum of transfers, conversions, and pending/settled ACH today in USD equivalent [MODIFIED D-03]
    remaining_daily_limit: Decimal # max(Decimal("0.00"), daily_limit - current_daily_total) [MODIFIED D-03]
    reference_currency: str = "USD"# Common reference currency [NEW D-07]

class TransferLimitsUpdateRequest(BaseModel):
    per_transaction_limit: Decimal # [MODIFIED D-03]
    daily_limit: Decimal           # [MODIFIED D-03]
```

## Limits Configuration and Reference Currency

- Common Reference Currency: Limits are configured and denominated in `USD`. Non-USD transaction amounts are normalized to unrounded USD equivalents for limit comparison:
  `USD_equivalent = source_amount / USD_base_factor(source_currency)`. [NEW D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- `GET /api/limits` returns HTTP 200 with the user's current limits and cumulative USD-equivalent daily total. [MODIFIED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Default Limits: Initial user settings default to `per_transaction_limit = 5000.00` USD and `daily_limit = 10000.00` USD. [INHERITED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- `PUT /api/limits` updates configured limits and returns updated `TransferLimitsResponse`. [INHERITED]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Input Validation: Fails with HTTP 422 if either limit is `<= 0` or has more than 2 decimal places. Fails with HTTP 400 if `per_transaction_limit > daily_limit`. Calculations use exact `Decimal` arithmetic. [MODIFIED D-03]
  `[@test] ../backend/tests/test_transfer_limits.py`

## Shared Multicurrency Limit Enforcement

- Applicable Financial Operations: Limits apply to internal transfers (`POST /api/transfers`), currency conversions (`POST /api/conversions`), and ACH transfers (`POST /api/transfers/ach`). Conversions cannot bypass financial limits. [NEW D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Atomic Pre-Execution Check: Limit validation executes before funds are debited or events appended. [INHERITED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Per-Transaction Rejection: Rejects any operation with HTTP 400 Bad Request if `USD_equivalent > per_transaction_limit`. [MODIFIED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Daily Cumulative Rejection: Rejects any operation with HTTP 400 Bad Request if `USD_equivalent + current_daily_total > daily_limit`. [MODIFIED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Shared Daily Consumption: All successful internal transfers, successful conversions, and pending/settled ACH transfers contribute their source debit `USD_equivalent` once to the single shared daily total for the current UTC calendar day. [NEW D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
- Non-Consumption by Failed Operations: Rejected or failed operations (e.g. balance or MFA failures, failed ACH settlements) do NOT consume daily limits. [NEW D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`

## Validation Order and Interaction with MFA

- Limit Check Precedence: Available balance and dynamic transfer limits are evaluated strictly prior to MFA PIN authorization. A valid Security PIN never overrides an exceeded limit. [NEW D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
  `[@test] ../backend/tests/test_mfa.py`
- Operations with `USD_equivalent <= 1000.00` execute without MFA if within limits. Operations with `USD_equivalent > 1000.00` require the Security PIN, provided they are within limits. [MODIFIED D-07]
  `[@test] ../backend/tests/test_transfer_limits.py`
  `[@test] ../backend/tests/test_mfa.py`

## User Interface Display

- Settings View: Renders configured limits along with a visual gauge of today's spent amount and remaining allowance clearly labeled in USD. [MODIFIED D-07]
  `[@test] ../frontend/src/__tests__/TransferLimits.test.tsx`
- Modal Warnings: Transfer and conversion modals show real-time warning indicators when the entered amount's USD equivalent exceeds remaining daily or per-transaction allowances. [MODIFIED D-07]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
