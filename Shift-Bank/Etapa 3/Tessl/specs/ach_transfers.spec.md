---
name: Third-Party ACH and Interbank Transfers
description: Transfer money to external beneficiaries at other banks with simulated settlement lifecycle and format validation
targets:
  - ../backend/app/routers/transfers.py
  - ../backend/app/routers/beneficiaries.py
  - ../backend/app/services/transfer_service.py
  - ../backend/app/services/crypto_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/services/scheduler.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferModal.tsx
---

# Third-Party ACH and Interbank Transfers

Provides capabilities to send money to external bank accounts and beneficiaries via simulated ACH operations.

## Data Contract

```python
class BeneficiaryCreateRequest(BaseModel):
    name: str
    routing_number: str
    account_number: str
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
    amount: float
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
    from_account_id: int
    beneficiary_id: Optional[int]
    recipient_name: str
    routing_number: str
    account_number: str
    bank_name: str
    amount: float
    status: str  # "pending" | "settled" | "failed"
    description: Optional[str]
    created_at: datetime
    settled_at: Optional[datetime]
```

## Beneficiary Management

- `GET /api/beneficiaries` returns HTTP 200 with all saved beneficiaries belonging to the user.
  `[@test] ../backend/tests/test_ach_transfers.py`
- `POST /api/beneficiaries` creates a new saved beneficiary when valid.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Rejects with HTTP 422 if `routing_number` is not exactly 9 digits.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Rejects with HTTP 422 if `account_number` is not between 4 and 17 digits.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Rejects with HTTP 422 if `name` or `bank_name` is empty or whitespace.
  `[@test] ../backend/tests/test_ach_transfers.py`
- `DELETE /api/beneficiaries/{id}` deletes a saved beneficiary belonging to the user.
  `[@test] ../backend/tests/test_ach_transfers.py`

## ACH Transfer Initiation

- `POST /api/transfers/ach` creates an external ACH transfer in `pending` status.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Accepts either a valid `beneficiary_id` or ad-hoc details (`recipient_name`, `routing_number`, `account_number`, `bank_name`).
  `[@test] ../backend/tests/test_ach_transfers.py`
- When ad-hoc details are supplied with `save_beneficiary=True`, creates and saves the beneficiary to the user's saved beneficiaries.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Immediately debits the transfer amount from the source account balance upon creation.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Records a pending debit transaction on the source account with reference formatted as `ACH-{id:05d}-OUT`.
  `[@test] ../backend/tests/test_ach_transfers.py`
- ACH transfers with amount `<= $1,000.00` execute without requiring an MFA Security PIN.
  `[@test] ../backend/tests/test_ach_transfers.py`
- ACH transfers with amount `> $1,000.00` require a valid Security PIN; if omitted, returns HTTP 428 `MfaRequiredResponse`.
  `[@test] ../backend/tests/test_ach_transfers.py`
- ACH transfers with amount `> $1,000.00` and a valid Security PIN execute successfully into `pending` status.
  `[@test] ../backend/tests/test_ach_transfers.py`

## Validation and Error Handling

- Fails with HTTP 400 if `amount` exceeds the available balance of the source account.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 400 if `amount` exceeds the configured per-transaction limit or causes cumulative transfers to exceed the daily transfer limit.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 422 if `amount` is `<= 0` or has more than 2 decimal places.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 404 if `from_account_id` does not exist or does not belong to the user.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 404 if `beneficiary_id` is supplied but does not exist or does not belong to the user.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 422 if neither `beneficiary_id` nor complete ad-hoc details are provided.
  `[@test] ../backend/tests/test_ach_transfers.py`
- Fails with HTTP 422 if ad-hoc `routing_number` is not 9 digits or `account_number` is not 4-17 digits.
  `[@test] ../backend/tests/test_ach_transfers.py`

## Simulated Settlement Lifecycle

- Background scheduler periodically processes pending ACH transfers and transitions them to `settled` status.
  `[@test] ../backend/tests/test_ach_transfers.py`
- When an ACH transfer settles, its `status` is updated to `settled` and `settled_at` timestamp is recorded.
  `[@test] ../backend/tests/test_ach_transfers.py`
- If an ACH transfer transitions to `failed`, the debited amount is refunded to the source account balance and transaction status is updated accordingly.
  `[@test] ../backend/tests/test_ach_transfers.py`

## Data Protection, Encryption at Rest & Audit Ledger Integration

- Sensitive banking coordinates (account numbers and routing numbers in `beneficiaries` and `transfers`) are stored encrypted at rest using AES-256-GCM authenticated encryption (`enc:v1:<iv>:<tag>:<ciphertext>`).
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Beneficiary query and transfer query responses preserve `routing_number` and `account_number` schema fields for authenticated owner operations, maintaining contract compatibility with existing Stage 2 tests. Third-party account numbers are masked to the last 4 digits (e.g. `****5678`) in audit logs, error messages, and transaction history references.
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Emits immutable audit log entry `transfer_ach_initiated` with `status="SUCCESS"` (or `status="FAILURE"`) upon ACH initiation, with failure events preserved during transaction rollback.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Background scheduler emits `transfer_ach_settled` (or `transfer_ach_failed`) audit events upon reaching terminal settlement states.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Beneficiary creation and deletion operations emit `beneficiary_created` and `beneficiary_deleted` audit events with sanitized metadata.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`

## User Interface Display

- TransferModal allows toggling between Internal Account Transfer and External ACH Transfer.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- In ACH mode, allows selecting from saved beneficiaries dropdown or choosing "Enter New Beneficiary".
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Displays input fields for Recipient Name, 9-digit Routing Number, Account Number, and Bank Name when entering ad-hoc details.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Displays a "Save to Beneficiaries" checkbox for ad-hoc entries.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Displays real-time validation error below the routing number input as the user types if the value is not exactly 9 digits, and disables transfer submission until valid.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Intercepts ACH transfers `> $1,000.00` to prompt for MFA Security PIN.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Transaction history displays pending status badge for ACH transfers until settled.
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
