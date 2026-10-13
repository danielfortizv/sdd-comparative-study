# Kiro Seed Prompt

The initial Kiro prompt used to initiate the Shift Bank Stage 1 spec-driven workflow.

Build a Stage 1 banking application called Shift Bank.

The application represents an authenticated mock customer and must support only transfers between the customer's own Checking and Savings accounts.

Functional requirements:

- The application has exactly two accounts:
  - Checking: COP 5,000,000
  - Savings: COP 15,000,000
- The user interface must display only the friendly account names Checking and Savings. Do not expose account numbers, UUIDs, database IDs, or other internal identifiers.
- The customer can transfer money only between their own Checking and Savings accounts.
- Reject transfers to the same account.
- Reject zero or negative amounts.
- Reject transfers when the source account has insufficient funds.
- No deposits, withdrawals, salary deposits, purchases, card payments, or other transaction types are required.
- The application must contain exactly two pre-seeded completed historical transfers:
  - COP 500,000 from Savings to Checking
  - COP 100,000 from Checking to Savings
- Historical seed transactions must be represented as historical records and must not be applied again to the predefined starting balances.
- Transaction history must show date, direction, amount, and description. It must not require displaying resulting balances.
- Transfers below COP 1,000,000 execute normally without MFA.
- Transfers of COP 1,000,000 or more require mock multi-factor authentication.
- The MFA code is always 123456.
- A sensitive transfer enters PENDING_MFA before execution.
- The account balances must not change while the transfer is pending MFA.
- An incorrect MFA code leaves the transfer pending and allows retrying.
- The MFA request expires after five minutes.
- An expired request becomes EXPIRED and cannot be completed.
- If the source account becomes insufficient while the transfer is pending MFA, confirmation must fail and the transfer becomes FAILED.
- A successful MFA confirmation changes the transfer to COMPLETED and updates both account balances atomically.
- No MFA lockout mechanism is required.

Technical baseline:

- Backend: Python with FastAPI.
- Persistence: SQLite using Python's built-in sqlite3 module, without an ORM.
- Monetary calculations must use decimal-safe handling with Decimal and decimal-string API values.
- Frontend: React with TypeScript.
- Use Vanilla CSS rather than a CSS framework.
- No external authentication or MFA service is required.
- Keep the implementation limited to this Stage 1 scope.

Begin by analyzing the requirements and using Kiro's native specification-driven workflow. Do not implement application code yet. Create the appropriate requirements artifact first and stop for review before proceeding to design or implementation.