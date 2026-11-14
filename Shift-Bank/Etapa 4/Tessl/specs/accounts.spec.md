---
name: Bank Accounts and Balances
description: Retrieve and display multicurrency bank accounts, current balances, and versioned projections for the authenticated mock user with exact monetary decimal precision
targets:
  - ../backend/app/routers/accounts.py
  - ../backend/app/services/account_service.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/AccountSummary.tsx
---

# Bank Accounts and Balances

Provides multicurrency account management, versioned state tracking, and CQRS balance queries for the authenticated mock user (`Alex Morgan`, `user_id=1`).

Governed by Researcher Decisions D-01, D-02, D-03, D-05, D-06, D-10, and D-14 and SEED-4 Items 1, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    account_type: str                  # "checking" | "savings"
    account_name: str
    balance: Decimal = Field(..., description="Exact monetary balance with 2 decimal places") # [MODIFIED D-03]
    currency: str                      # "USD" | "EUR" | "GBP"
    version: int                       # Authoritative non-negative account sequence version [NEW D-14]
    created_at: datetime
```

## Multicurrency Account Provisioning & Retrieval

- `GET /api/accounts` returns HTTP 200 with all accounts belonging to the mock user, sourced from CQRS read projections. [MODIFIED D-01, D-06]
  `[@test] ../backend/tests/test_accounts.py`
- Provisioned Accounts: Exactly four pre-provisioned accounts are available [MODIFIED D-01, D-02, D-05]:
  1. `Primary Checking` with account number `CHK-1001`, initial balance `$2,500.00`, currency `USD`, `version >= 1`.
  2. `Standard Savings` with account number `SAV-2001`, initial balance `$10,000.00`, currency `USD`, `version >= 1`.
  3. `Euro Account` with account number `EUR-3001`, initial balance `0.00`, currency `EUR`, `version >= 1`.
  4. `British Pound Account` with account number `GBP-4001`, initial balance `0.00`, currency `GBP`, `version >= 1`.
  `[@test] ../backend/tests/test_accounts.py`
- Single Currency Invariant: Each account holds exactly ONE fixed currency and ONE balance. Multi-currency balances within a single account are prohibited. [NEW D-01]
  `[@test] ../backend/tests/test_accounts.py`
- Exact Monetary Representation: Balances must be represented and manipulated internally using exact `Decimal` or integer minor units (cents), never binary floating-point numbers. Serialized across APIs with exact 2-decimal precision (e.g. `"2500.00"` or exact decimal representation). [NEW D-03]
  `[@test] ../backend/tests/test_accounts.py`
- State Preservation: Existing USD account numbers, names, and exact persisted balances ($2,500.00 and $10,000.00) are preserved without silent revaluation or conversion. [INHERITED D-01, D-02, D-05]
  `[@test] ../backend/tests/test_accounts.py`
- Version Synchronization: `AccountResponse.version` reflects the authoritative event-sourced version, incremented atomically upon each completed monetary command. [NEW D-14]
  `[@test] ../backend/tests/test_accounts.py`
- `GET /api/accounts/{account_id}` returns HTTP 200 with the versioned account details for an existing account owned by the user. [MODIFIED D-14]
  `[@test] ../backend/tests/test_accounts.py`
- `GET /api/accounts/{account_id}` returns HTTP 404 when the account does not exist or belongs to another user. [INHERITED]
  `[@test] ../backend/tests/test_accounts.py`

## User Interface Display & Balance Presentation

- Account Cards: Renders an account card for each account showing its name, formatted account number, currency badge (`USD`, `EUR`, `GBP`), formatted balance with appropriate currency symbol (`$`, `€`, `£`), and current version. Frontend formatting uses exact decimal or integer-cents arithmetic to prevent JavaScript `Number` floating-point precision loss. [MODIFIED D-01, D-03, D-10, D-14]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Currency-Segregated Totals: The dashboard header card renders separate totals for each supported currency (`USD`, `EUR`, `GBP`), calculated strictly by summing accounts sharing the same currency. Never directly adds numerical amounts of different currencies. [NEW D-10]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Indicative USD Aggregate: The header displays an "Estimated Total (USD)" calculated by converting each non-USD currency total to USD using exact D-03 reference rates, summing unrounded USD equivalents, and applying `ROUND_HALF_UP` to 2 decimals once at the end. [NEW D-10]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Valuation Transparency: Clearly labels the aggregate as an estimated USD equivalent calculated via simulated fixed rates, making clear it is a display valuation rather than a single USD account balance. [NEW D-10]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Active Account Selection: Highlights the currently selected account for filtering transactions in the transaction history view. [INHERITED]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
- Loading and Error States: Displays loading indicators during queries and an error banner if API requests fail. [INHERITED]
  `[@test] ../frontend/src/__tests__/AccountSummary.test.tsx`
