---
name: Account Transaction History
description: Query and display multicurrency movements, conversion details, and CQRS transaction projections associated with user accounts using exact Decimal precision
targets:
  - ../backend/app/routers/transactions.py
  - ../backend/app/services/account_service.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/models.py
  - ../frontend/src/components/TransactionHistory.tsx
---

# Account Transaction History

Provides movement tracking, historical conversion audits, and CQRS projection queries for user accounts.

Governed by Researcher Decisions D-01, D-03, D-05, D-06, and D-10 and SEED-4 Items 1, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str]
    transfer_id: Optional[int]
    conversion_id: Optional[int] = None       # ID of related currency conversion [NEW D-03, D-10]
    transaction_type: str                     # "credit" | "debit"
    amount: Decimal                           # Nominal amount in account's currency [MODIFIED D-03]
    currency: str                             # Account fixed currency ("USD" | "EUR" | "GBP") [NEW D-01]
    balance_after: Decimal                    # Resulting balance in account's currency [MODIFIED D-03]
    description: str
    reference: Optional[str]
    source_amount: Optional[Decimal] = None     # For conversions: original source debit [MODIFIED D-03]
    source_currency: Optional[str] = None     # For conversions: original source currency [NEW D-03]
    destination_amount: Optional[Decimal] = None # For conversions: rounded destination credit [MODIFIED D-03]
    destination_currency: Optional[str] = None # For conversions: destination currency [NEW D-03]
    exchange_rate_display: Optional[Decimal] = None # For conversions: display exchange rate [MODIFIED D-03]
    status: Optional[str] = "completed"
    created_at: datetime
```

## Transaction Retrieval & Projection Sourcing

- `GET /api/transactions` returns HTTP 200 with all transaction movements belonging to the user's accounts, ordered newest first, read from CQRS transaction projections. [MODIFIED D-06]
  `[@test] ../backend/tests/test_transactions.py`
- `GET /api/transactions?account_id={id}` returns HTTP 200 containing only transactions associated with the specified account. [INHERITED]
  `[@test] ../backend/tests/test_transactions.py`
- Inherited Historical Preservation: Inherited Stage 3 USD transactions (payroll deposit, utility payment, savings funding) remain accessible without modification or revaluation, reconstructed via `LegacyTransactionImported` events. [INHERITED D-01, D-05, D-10]
  `[@test] ../backend/tests/test_transactions.py`
- Explicit Currency Display: Every transaction record explicitly conveys its currency identity (`currency`), matching the owning account. [NEW D-01]
  `[@test] ../backend/tests/test_transactions.py`
- Conversion Traceability: Movements resulting from currency conversions include source amount/currency, destination amount/currency, and applied rate. [NEW D-03, D-10]
  `[@test] ../backend/tests/test_transactions.py`
- Non-Existent Account Query: Fails with HTTP 404 if `account_id` parameter does not match any account owned by the user. [INHERITED]
  `[@test] ../backend/tests/test_transactions.py`

## User Interface Display & Filtering

- Account Filter Tabs: Provides tabs/filters to switch between "All Accounts", "Primary Checking (USD)", "Standard Savings (USD)", "Euro Account (EUR)", and "British Pound Account (GBP)". [MODIFIED D-01, D-10]
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Color and Prefix Rendering: Renders credits in green with a `+` prefix and debits in red with a `-` prefix, with appropriate currency symbols (`$`, `€`, `£`) and exact two-decimal formatting. [MODIFIED D-03, D-10]
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Conversion Details Badging: Displays conversion badges showing applied exchange rate, paired currency, and counter-amount for conversion transactions. [NEW D-03, D-10]
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
- Empty State: Displays a clear empty state message when an account has no transactions matching the selected filter. [INHERITED]
  `[@test] ../frontend/src/__tests__/TransactionHistory.test.tsx`
