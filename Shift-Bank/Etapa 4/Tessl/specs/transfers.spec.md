---
name: Internal Account Transfers
description: Transfer money between the authenticated user's same-currency bank accounts with Decimal precision, balance validation, optimistic concurrency, idempotency, and atomic event-sourced CQRS integration
targets:
  - ../backend/app/routers/transfers.py
  - ../backend/app/services/transfer_service.py
  - ../backend/app/services/event_store.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferModal.tsx
---

# Internal Account Transfers

Provides capabilities to transfer money between the authenticated user's own accounts holding the SAME currency.

Governed by Researcher Decisions D-01, D-03, D-04, D-05, D-06, D-07, D-09, D-11, D-13, and D-14 and SEED-4 Items 1, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0, description="Transfer amount; strictly positive, max 2 decimal places") # [MODIFIED D-03]
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account for optimistic concurrency [NEW D-14]")
    expected_to_version: int = Field(..., ge=0, description="Expected version of destination account for optimistic concurrency [NEW D-14]")
    description: Optional[str] = None
    pin: Optional[str] = None  # Required if USD-equivalent amount > 1000.00

class TransferResponse(BaseModel):
    id: int
    operation_id: str                      # Unique UUID of internal transfer operation [NEW D-09]
    from_account_id: int
    to_account_id: int
    currency: str                          # Fixed currency of both accounts [NEW D-01]
    amount: Decimal                        # Exact transferred amount (2 decimals) [MODIFIED D-03]
    from_account_version: int              # Incremented version of source account [NEW D-14]
    to_account_version: int                # Incremented version of destination account [NEW D-14]
    status: str                            # "completed" | "mfa_required" | "failed"
    description: Optional[str]
    created_at: datetime
```

## Transfer Execution & Currency Scope

- `POST /api/transfers` executes an internal transfer between user accounts when valid. [INHERITED]
  `[@test] ../backend/tests/test_transfers.py`
- Same-Currency Restriction: Both source and destination accounts must share the exact same currency (`from_acc.currency == to_acc.currency`). [NEW D-01, D-04]
  `[@test] ../backend/tests/test_transfers.py`
- Rejection of Cross-Currency Transfers: Any request where `from_acc.currency != to_acc.currency` is rejected with HTTP 400 Bad Request (`CROSS_CURRENCY_NOT_PERMITTED`). Cross-currency transfers must use `POST /api/conversions`. [NEW D-04]
  `[@test] ../backend/tests/test_transfers.py`
- Atomic Operation Event: Appends ONE compound `InternalTransferCompleted` event to `domain_events` recording both account IDs, currency, exact Decimal amount, and resulting versions. [NEW D-09]
  `[@test] ../backend/tests/test_transfers.py`
- Single Transaction Commit: The `InternalTransferCompleted` event, CQRS read projection updates (source debit, destination credit, transaction history records), and HMAC audit log entry commit in ONE SQLite database transaction. [NEW D-06, D-09]
  `[@test] ../backend/tests/test_transfers.py`
- Version Advancement: Successfully committed transfers advance both `from_account` and `to_account` versions by +1. [NEW D-14]
  `[@test] ../backend/tests/test_transfers.py`

## Idempotency and Optimistic Concurrency Control

- Mandatory Idempotency Header: Every request to `POST /api/transfers` must include an `Idempotency-Key` HTTP header containing a valid UUID. [NEW D-13]
  - Missing header returns HTTP 400 (`MISSING_IDEMPOTENCY_KEY`).
  - Malformed header returns HTTP 400 (`INVALID_IDEMPOTENCY_KEY`).
  `[@test] ../backend/tests/test_transfers.py`
- Idempotent Replay: Retrying with the same `Idempotency-Key` and identical request parameters returns the original committed `TransferResponse` without creating new events, adjusting balances, or logging duplicate audit records. [NEW D-13]
  `[@test] ../backend/tests/test_transfers.py`
- Parameter Conflict: Reusing an `Idempotency-Key` with different request parameters returns HTTP 409 Conflict (`IDEMPOTENCY_KEY_REUSE`). [NEW D-13]
  `[@test] ../backend/tests/test_transfers.py`
- Optimistic Concurrency Validation: Compares `expected_from_version` and `expected_to_version` against authoritative account versions. If either is stale, rejects with HTTP 409 Conflict (`ACCOUNT_VERSION_CONFLICT`). [NEW D-14]
  `[@test] ../backend/tests/test_transfers.py`

## Validation, Financial Limits & MFA Integration

- Same-Account Rejection: Fails with HTTP 400 if `from_account_id == to_account_id`. [INHERITED]
  `[@test] ../backend/tests/test_transfers.py`
- Precision Validation: Fails with HTTP 422 if `amount <= 0` or has more than 2 decimal places. Operations use exact `Decimal` arithmetic. [MODIFIED D-03]
  `[@test] ../backend/tests/test_transfers.py`
- Balance Check: Fails with HTTP 400 if `amount` exceeds available balance of source account. [INHERITED]
  `[@test] ../backend/tests/test_transfers.py`
- Common Reference Currency Limits: Limits and MFA threshold are evaluated in unrounded USD equivalent (`source_amount / USD_base_factor(source_currency)`). [NEW D-07]
  - Fails with HTTP 400 if `USD_equivalent > per_transaction_limit` ($5,000.00 default).
  - Fails with HTTP 400 if `USD_equivalent + current_daily_total > daily_limit` ($10,000.00 default).
  `[@test] ../backend/tests/test_transfers.py`
  `[@test] ../backend/tests/test_transfer_limits.py`
- MFA PIN Challenge:
  - If `USD_equivalent <= 1000.00`, executes immediately without PIN. [MODIFIED D-07]
  - If `USD_equivalent > 1000.00`, requires valid Security PIN (`1234`). Omission returns HTTP 428 `MfaRequiredResponse`. [MODIFIED D-07]
  `[@test] ../backend/tests/test_transfers.py`
- Validation Order: Account, balance, and limits are strictly validated before completing MFA authorization. A correct PIN never overrides limit or balance violations. [NEW D-07]
  `[@test] ../backend/tests/test_transfers.py`
- Non-Existent Account: Fails with HTTP 404 if either account does not exist or does not belong to the user. [INHERITED]
  `[@test] ../backend/tests/test_transfers.py`

## Audit Ledger & Security Integration

- Successful internal transfers emit an immutable audit log entry `transfer_internal` with `status="SUCCESS"` recording transfer ID, masked account numbers, and amount. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfers.py`
- Failed internal transfers emit an immutable audit log entry `transfer_internal` with `status="FAILURE"` and sanitized error code, preserved even when the business transaction rolls back. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfers.py`
- Audit log entries and error responses must never expose Security PINs or plaintext credentials. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfers.py`

## User Interface Display & Workflow

- Transfer modal allows selecting source account and destination account (filtered to exclude source AND accounts of different currencies). [MODIFIED D-04]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Displays real-time validation for amount exceeding available source balance using exact decimal math. [MODIFIED D-03]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Automatically intercepts transfers with USD-equivalent `> $1,000.00` to prompt for MFA Security PIN. [MODIFIED D-07]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Generates a unique UUID `Idempotency-Key` for each submission and supplies current `expected_from_version` and `expected_to_version`. [NEW D-13, D-14]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- On HTTP 409 `ACCOUNT_VERSION_CONFLICT`, refreshes account balances/versions and prompts the user without silent resubmission. [NEW D-14]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
