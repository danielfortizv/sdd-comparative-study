# Spec Kit — Stage 1 Seed Prompt

## Initial `/speckit.specify` prompt

> Develop Stage 1 of a web application called Shift Bank. Shift Bank is a basic banking application for an already authenticated mock user. For this stage, the application must allow the user to view their bank accounts and current balances, transfer money only between their own accounts, review the transaction history or movements associated with each account, and perform a mock multi-factor authentication (MFA) verification for sensitive transfer operations. User registration, login, password recovery, external bank transfers, payments, credit cards, loans, and other banking products are outside the scope of this stage. The backend must be implemented in Python and the frontend must use React with TypeScript. Explore these requirements before implementation: identify ambiguities, relevant edge cases, domain constraints, and decisions that should be clarified. Do not implement or modify code.

## Initial clarification inputs

The workflow asked three clarification questions.

### Q1 — Sensitive transfer threshold

A transfer is sensitive when the amount is **greater than or equal to COP 1,000,000**.

### Q2 — Mock MFA

Use a fixed six-digit mock MFA code of **`123456`** validated by the backend.

- Do not use TOTP.
- Do not use SMS.
- Do not use email.
- Do not use any external MFA service.
- An invalid code must not execute the transfer.

### Q3 — Initial accounts and overdraft policy

Seed exactly two accounts for the already authenticated mock user:

- Checking: initial balance **COP 5,000,000**
- Savings: initial balance **COP 15,000,000**

Overdraft is not allowed. Transfers exceeding the available source balance must be rejected.

Include a small pre-seeded transaction history.

## Human-approved baseline refinement

The generated specification was subsequently corrected to remove invented scope, make MFA lifecycle behavior explicit, require persistent server-side state, and remove arbitrary performance timing requirements.
