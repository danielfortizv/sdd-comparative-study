---
name: Internal Account Transfers
description: Transfer money between the authenticated user's own bank accounts with balance validation and atomicity
targets:
  - ../backend/app/routers/transfers.py
  - ../backend/app/services/transfer_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransferModal.tsx
---

# Internal Account Transfers

Provides capabilities to transfer money between the authenticated user's own accounts.

## Data Contract

```python
class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float
    description: Optional[str] = None
    pin: Optional[str] = None

class TransferResponse(BaseModel):
    id: int
    from_account_id: int
    to_account_id: int
    amount: float
    status: str  # "completed" | "mfa_required" | "failed"
    description: Optional[str]
    created_at: datetime

class MfaRequiredResponse(BaseModel):
    detail: str  # "MFA_REQUIRED"
    message: str  # "Security PIN required for transfers over $1,000"
```

## Transfer Execution

- `POST /api/transfers` executes an internal transfer between user accounts when valid.
  `[@test] ../backend/tests/test_transfers.py`
- Decrements the source account balance and increments the destination account balance atomically.
  `[@test] ../backend/tests/test_transfers.py`
- Records two linked transaction movements: a debit (`withdrawal`/`transfer_out`) on the source account and a credit (`deposit`/`transfer_in`) on the destination account.
  `[@test] ../backend/tests/test_transfers.py`
- Transfers with amount `<= $1,000.00` (including boundary value `$1,000.00`) execute immediately without requiring an MFA PIN.
  `[@test] ../backend/tests/test_transfers.py`
- Transfers with amount `> $1,000.00` (including boundary value `$1,000.01`) require a valid Security PIN; if omitted, returns HTTP 428 with `MfaRequiredResponse`: `{"detail": "MFA_REQUIRED", "message": "Security PIN required for transfers over $1,000"}`.
  `[@test] ../backend/tests/test_transfers.py`
- Transfers with amount `> $1,000.00` and a valid Security PIN execute successfully.
  `[@test] ../backend/tests/test_transfers.py`

## Validation and Error Handling

- Fails with HTTP 400 if `from_account_id` equals `to_account_id`.
  `[@test] ../backend/tests/test_transfers.py`
- Fails with HTTP 422 if `amount` is `<= 0`.
  `[@test] ../backend/tests/test_transfers.py`
- Fails with HTTP 422 if `amount` has more than 2 decimal places.
  `[@test] ../backend/tests/test_transfers.py`
- Fails with HTTP 400 if `amount` exceeds the available balance of the source account.
  `[@test] ../backend/tests/test_transfers.py`
- Fails with HTTP 404 if either source or destination account does not exist or does not belong to the user.
  `[@test] ../backend/tests/test_transfers.py`

## User Interface Display

- Transfer modal allows selecting source account, destination account (filtered to exclude source), and amount.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Displays real-time validation for amount exceeding available source balance.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Automatically intercepts transfers `> $1,000.00` to prompt the user with the MFA Security PIN modal.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
- Updates account balances and appends new transactions in the UI immediately upon successful transfer.
  `[@test] ../frontend/src/__tests__/TransferModal.test.tsx`
