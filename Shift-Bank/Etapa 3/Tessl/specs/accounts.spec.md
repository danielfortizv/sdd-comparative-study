---
name: Bank Accounts and Balances
description: Retrieve and display bank accounts and current balances for the authenticated mock user
targets:
  - ../backend/app/routers/accounts.py
  - ../backend/app/services/account_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/AccountSummary.tsx
---

# Bank Accounts and Balances

Provides account management and balance queries for the authenticated mock user (`Alex Morgan`, `user_id=1`).

## Data Contract

```python
class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    account_type: str  # "checking" | "savings"
    account_name: str
    balance: float
    currency: str      # "USD"
    created_at: datetime
```

## Account Retrieval

- `GET /api/accounts` returns HTTP 200 with all accounts belonging to the mock user.
  `[@test] ../backend/tests/test_accounts.py`
- Seed data initializes two accounts:
  1. `Primary Checking` with account number `CHK-1001` and initial balance `$2,500.00`.
  2. `Standard Savings` with account number `SAV-2001` and initial balance `$10,000.00`.
  `[@test] ../backend/tests/test_accounts.py`
- Each account includes formatted currency (`USD`), identifier, account type, name, and current balance.
  `[@test] ../backend/tests/test_accounts.py`
- `GET /api/accounts/{account_id}` returns HTTP 200 for an existing account owned by the user.
  `[@test] ../backend/tests/test_accounts.py`
- `GET /api/accounts/{account_id}` returns HTTP 404 when the account does not exist.
  `[@test] ../backend/tests/test_accounts.py`

## User Interface Display

- Renders an account card for each account with its name, masked or formatted account number, account type badge, and formatted balance.
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Displays the total aggregate net balance across all user accounts in the header summary card.
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Highlights the currently active/selected account for viewing transactions.
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Displays loading state while fetching and an error banner if the API request fails.
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
