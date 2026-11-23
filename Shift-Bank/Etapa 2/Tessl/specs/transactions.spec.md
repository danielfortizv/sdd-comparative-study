---
name: Account Transaction History
description: Query and display movements and transaction history associated with user accounts
targets:
  - ../backend/app/routers/transactions.py
  - ../backend/app/services/account_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransactionHistory.tsx
---

# Account Transaction History

Provides movement tracking and historical transaction queries for user accounts.

## Data Contract

```python
class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str]
    transfer_id: Optional[int]
    transaction_type: str  # "credit" | "debit"
    amount: float
    balance_after: float
    description: str
    reference: Optional[str]
    created_at: datetime
```

## Transaction Retrieval

- `GET /api/transactions` returns HTTP 200 with all transaction movements belonging to the user's accounts, ordered newest first.
  `[@test] ../backend/tests/test_transactions.py`
- `GET /api/transactions?account_id={id}` returns HTTP 200 containing only transactions associated with the specified account.
  `[@test] ../backend/tests/test_transactions.py`
- Seed data includes initial transactions for both accounts (e.g., payroll deposit in Checking, interest/initial funding in Savings).
  `[@test] ../backend/tests/test_transactions.py`
- Each transaction record includes `transaction_type`, `amount`, `balance_after`, descriptive label, and formatted timestamp.
  `[@test] ../backend/tests/test_transactions.py`
- Fails with HTTP 404 if `account_id` parameter does not match any account owned by the user.
  `[@test] ../backend/tests/test_transactions.py`

## User Interface Display

- Provides tabs/filters to switch between "All Accounts", "Primary Checking", and "Standard Savings".
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Renders credits (money in) in green with a `+` prefix and debits (money out) in red with a `-` prefix.
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Displays transaction details: date/time, description, account name/badge, transaction amount, and resulting balance.
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Displays an empty state message when an account has no transactions matching the filter.
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
