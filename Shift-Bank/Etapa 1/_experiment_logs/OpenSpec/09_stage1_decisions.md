# Shift Bank - Stage 1 Frozen Decisions

## Functional
- Currency: COP only.
- Mock user: Already authenticated.
- Accounts: Exactly two accounts:
  - Checking account
  - Savings account
- Both accounts have initial balances.
- A small transaction history is pre-seeded.
- Transfers are only allowed between the user's own accounts.
- Same-account transfers are rejected.
- Transfer amount must be greater than zero.
- Transfers exceeding available balance are rejected.

## MFA
- Sensitive transfer threshold: >= COP 1,000,000.
- Mock MFA code: `123456`.
- No TOTP, SMS, email, or external MFA provider.
- Pending MFA transfers expire after 5 minutes.
- Invalid MFA does not execute the transfer.
- Balance must be revalidated when MFA is confirmed.
- No attempt-lockout mechanism is required for Stage 1.

## Transactions
- History displays incoming and outgoing movements.
- Resulting balance after each transaction is not required.
- Monetary values must use decimal-safe arithmetic.
- API monetary values should be represented as decimal strings.

## Technical
- Backend: Python + FastAPI.
- Database: SQLite.
- Frontend: React + TypeScript + Vite.
- Styling: Vanilla CSS.