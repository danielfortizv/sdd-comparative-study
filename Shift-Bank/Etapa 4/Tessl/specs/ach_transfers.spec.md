---
name: Third-Party ACH and Interbank Transfers
description: Transfer money to external beneficiaries at other banks with USD-only currency restriction, exact Decimal precision, optimistic concurrency, multi-phase domain events, simulated settlement/refund lifecycle, and AES-256-GCM encryption
targets:
  - ../backend/app/routers/transfers.py
  - ../backend/app/routers/beneficiaries.py
  - ../backend/app/services/transfer_service.py
  - ../backend/app/services/event_store.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/services/crypto_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/services/scheduler.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferModal.tsx
---

# Third-Party ACH and Interbank Transfers

Provides capabilities to send money to external bank accounts and beneficiaries via simulated ACH operations, restricted to USD source accounts and governed by exact Decimal precision.

Governed by Researcher Decisions D-01, D-03, D-05, D-06, D-07, D-08, D-09, D-11, D-13, and D-14 and SEED-4 Items 1, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class BeneficiaryCreateRequest(BaseModel):
    name: str
    routing_number: str                # 9 digits (encrypted at rest)
    account_number: str                # 4-17 digits (encrypted at rest)
    bank_name: str

class BeneficiaryResponse(BaseModel):
    id: int
    user_id: int
    name: str
    routing_number: str
    account_number: str
    bank_name: str
    created_at: datetime

class AchTransferRequest(BaseModel):
    from_account_id: int
    amount: Decimal = Field(..., gt=0, description="ACH transfer amount in USD; strictly positive, max 2 decimals") # [MODIFIED D-03]
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account for optimistic concurrency [NEW D-14]")
    description: Optional[str] = None
    pin: Optional[str] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    save_beneficiary: Optional[bool] = False

class AchTransferResponse(BaseModel):
    id: int
    operation_id: str                  # Unique UUID of ACH operation [NEW D-09]
    from_account_id: int
    from_account_version: int          # Advanced version of source account [NEW D-14]
    beneficiary_id: Optional[int]
    recipient_name: str
    routing_number: str                # Masked in logs and public responses
    account_number: str                # Masked in logs and public responses
    bank_name: str
    amount: Decimal                    # Exact Decimal amount [MODIFIED D-03]
    currency: str = "USD"              # Strictly USD [NEW D-08]
    status: str                        # "pending" | "settled" | "failed"
    description: Optional[str]
    created_at: datetime
    settled_at: Optional[datetime]
```

## Beneficiary Management & Encryption

- `GET /api/beneficiaries` returns HTTP 200 with saved beneficiaries belonging to the user. [INHERITED]
  `[@test] ../backend/tests/test_ach_transfers.py`
- `POST /api/beneficiaries` creates a saved beneficiary when valid. [INHERITED]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Routing & Account Validation: Rejects with HTTP 422 if `routing_number` is not exactly 9 digits or `account_number` is not between 4 and 17 digits. Rejects with HTTP 422 if `name` or `bank_name` is empty or whitespace. [INHERITED]
  `[@test] ../backend/tests/test_ach_transfers.py`
- AES-256-GCM Encryption: Beneficiary routing and account numbers are encrypted at rest and in domain event payloads using Stage 3 AES-256-GCM (`enc:v1:<iv>:<tag>:<ciphertext>`). Plaintext sensitive numbers are never stored unencrypted. [INHERITED D-11]
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- `DELETE /api/beneficiaries/{id}` deletes a saved beneficiary belonging to the user. [INHERITED]
  `[@test] ../backend/tests/test_ach_transfers.py`

## USD-Only Currency Restriction

- Strict USD Source Requirement: ACH transfers must originate exclusively from USD-denominated accounts (`from_acc.currency == "USD"`). [NEW D-08]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Non-USD Rejection: Any ACH transfer attempted from a EUR or GBP account is rejected with HTTP 400 Bad Request (`ACH_REQUIRES_USD_ACCOUNT`) without debiting funds or generating domain events. [NEW D-08]
  `[@test] ../backend/tests/test_ach_transfers.py`

## Idempotency and Optimistic Concurrency Control

- Mandatory Idempotency Header: Requests to `POST /api/transfers/ach` must include an `Idempotency-Key` HTTP header (UUID). [NEW D-13]
  - Missing header returns HTTP 400 (`MISSING_IDEMPOTENCY_KEY`).
  - Malformed header returns HTTP 400 (`INVALID_IDEMPOTENCY_KEY`).
  `[@test] ../backend/tests/test_ach_transfers.py`
- Idempotent Replay: Retrying with the same key and identical parameters returns the original `AchTransferResponse` without duplicating debits or events. [NEW D-13]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Parameter Conflict: Reusing a key with different parameters returns HTTP 409 Conflict (`IDEMPOTENCY_KEY_REUSE`). [NEW D-13]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Source Account Version Check: Compares `expected_from_version` against the current authoritative version of `from_account`. Stale versions reject with HTTP 409 Conflict (`ACCOUNT_VERSION_CONFLICT`). [NEW D-14]
  `[@test] ../backend/tests/test_ach_transfers.py`

## Multi-Phase Domain Events & Simulated Settlement Lifecycle

- Phase 1 (Initiation): `POST /api/transfers/ach` appends an `AchTransferInitiated` domain event, immediately debits the source account, increments `from_account` version by +1, records a pending debit transaction with reference `ACH-{id:05d}-OUT`, and updates CQRS read projections synchronously into `pending` status. [NEW D-06, D-09, D-14]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Phase 2 (Settlement): Asynchronous simulated settlement worker periodically checks `pending` transfers and appends an `AchTransferSettled` domain event updating status to `settled` with `settled_at = now` without an additional debit. Uses deterministic idempotency based on operation ID. [INHERITED, NEW D-09]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Phase 3 (Failure & Automated Refund): On simulated settlement failure, worker appends an `AchTransferFailed` event updating status to `failed`, applies an exact refund credit to the source account with reference `ACH-{id:05d}-REFUND`, and increments source account version by +1. [INHERITED, NEW D-09, D-14]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Simulation Trigger Endpoint: `POST /api/transfers/ach/process-settlements` immediately triggers processing of pending ACH transfers and returns execution summaries for simulation and testing. [INHERITED]
  `[@test] ../backend/tests/test_ach_transfers.py`
- Terminal State Immutability: Once settled or failed, an ACH transfer cannot transition to any other state. [INHERITED D-09]
  `[@test] ../backend/tests/test_ach_transfers.py`

## Limits, MFA & Audit Integration

- Validation Order & Limits: Fails with HTTP 400 if `amount` exceeds available balance. Rejects with HTTP 400 if amount exceeds USD limits ($5,000.00 per-transaction, $10,000.00 daily). Limits checked prior to MFA. [INHERITED D-07]
  `[@test] ../backend/tests/test_ach_transfers.py`
  `[@test] ../backend/tests/test_transfer_limits.py`
- Mock MFA PIN Challenge: ACH transfers with amount `> $1,000.00` require Security PIN (`1234`); omission returns HTTP 428 `MfaRequiredResponse`. [INHERITED D-07]
  `[@test] ../backend/tests/test_ach_transfers.py`
  `[@test] ../backend/tests/test_mfa.py`
- Audit Ledger Integration: Emits Stage 3 HMAC-SHA256 audit entries: `transfer_ach_initiated`, `transfer_ach_settled`, and `transfer_ach_failed`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`

## User Interface Display & Workflow

- TransferModal External ACH Tab: Enables sending funds to external accounts via saved beneficiary selection or ad-hoc input form. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Ad-Hoc Beneficiary Inputs: Provides fields for Recipient Name, 9-digit Routing Number, Account Number, Bank Name, and a "Save to Beneficiaries" checkbox. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Real-Time Validations: Displays format errors for non-9-digit routing numbers, account numbers outside 4-17 digits, and amounts exceeding balance. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- MFA Prompt Interception: Intercepts ACH submissions `> $1,000.00` to prompt for MFA PIN. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Masked Presentation: Renders third-party account numbers masked (e.g. `****1234`) across transfer confirmation and transaction history. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
