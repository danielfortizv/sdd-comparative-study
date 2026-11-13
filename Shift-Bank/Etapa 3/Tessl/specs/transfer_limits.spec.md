---
name: Dynamic Transfer Limits
description: Configurable per-transaction and daily cumulative transfer limits affecting transfer authorization
targets:
  - ../backend/app/routers/limits.py
  - ../backend/app/services/limit_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferLimits.tsx
---

# Dynamic Transfer Limits

Provides configurable per-transaction and daily cumulative transfer limits that gate transfer authorization and validation.

## Data Contract

```python
class TransferLimitsResponse(BaseModel):
    per_transaction_limit: float   # default: 5000.00
    daily_limit: float             # default: 10000.00
    current_daily_total: float     # sum of transfers executed today
    remaining_daily_limit: float   # max(0.0, daily_limit - current_daily_total)

class TransferLimitsUpdateRequest(BaseModel):
    per_transaction_limit: float
    daily_limit: float
```

## Limits Configuration and Query

- `GET /api/limits` returns HTTP 200 with the user's current transfer limits and daily cumulative consumption.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Initial user settings default to `per_transaction_limit = 5000.00` and `daily_limit = 10000.00`.
  `[@test] ../backend/tests/test_transfer_limits.py`
- `PUT /api/limits` updates the user's configured limits and returns the updated `TransferLimitsResponse`.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Fails with HTTP 422 if either limit is `<= 0` or has more than 2 decimal places.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Fails with HTTP 400 if `per_transaction_limit` is greater than `daily_limit`.
  `[@test] ../backend/tests/test_transfer_limits.py`

## Limits Enforcement

- Limit checks are evaluated atomically before any transfer (internal transfer, external ACH transfer, or recurring execution).
  `[@test] ../backend/tests/test_transfer_limits.py`
- Rejects transfer with HTTP 400 if `amount > per_transaction_limit` with descriptive error message.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Rejects transfer with HTTP 400 if `amount + current_daily_total > daily_limit` with descriptive error message.
  `[@test] ../backend/tests/test_transfer_limits.py`
- `current_daily_total` calculates the sum of all internal transfers and external ACH transfers executed or initiated in `pending` status on the current calendar day (UTC).
  `[@test] ../backend/tests/test_transfer_limits.py`

## Interaction with Mock MFA

- Transfer limits act as a hard cap, independent of MFA status.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Transfers with amount `<= $1,000.00` execute without requiring an MFA Security PIN, provided they are within limits.
  `[@test] ../backend/tests/test_transfer_limits.py`
- Transfers with amount `> $1,000.00` and `<= per_transaction_limit` require the valid mock Security PIN (`1234`).
  `[@test] ../backend/tests/test_transfer_limits.py`
- Transfers exceeding either `per_transaction_limit` or `daily_limit` are blocked immediately with HTTP 400, regardless of whether a PIN is supplied.
  `[@test] ../backend/tests/test_transfer_limits.py`

## User Interface Display

- Settings view/panel renders the current configured Per-Transaction Limit and Daily Limit along with a visual gauge of today's spent amount and remaining allowance.
  `[@test] ../frontend/src/__tests__/TransferLimits.test.tsx`
- Allows editing and saving new limit values with real-time validation.
  `[@test] ../frontend/src/__tests__/TransferLimits.test.tsx`
- TransferModal displays real-time warning indicators when the entered amount exceeds the remaining daily limit or per-transaction limit.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
