# SEED-3 — Shift Bank — Stage 3 (Option A)

## Existing application

Continue the existing Shift Bank web application from the completed Stage 2 implementation. This is an evolution of an existing system, not a new application.

The current technology stack is a Python/FastAPI backend and a React/TypeScript frontend. The application uses an already authenticated mock banking user. Preserve the existing capabilities: account balances, transaction history, transfers between the user's own accounts, simulated MFA for sensitive transfers, third-party ACH/interbank transfers, recurring payment scheduling, and dynamic transfer limits.

## Stage 3 requirements

Extend the existing application with the following capabilities:

1. End-to-end encryption of sensitive banking data.
2. Immutable audit logs for banking transactions.
3. Load testing of the application.
4. Deployment of the application.

## Scope and compatibility

Maintain the existing banking behavior and compatibility with the completed stages. Continue using the existing Python/FastAPI and React/TypeScript stack. This remains a simulated banking application; real banking-provider integrations, user registration, and login are outside the requested scope.

Clarify material ambiguities before implementation, especially the meaning and boundaries of end-to-end encryption, the immutability guarantees of audit logs, the load-test objectives, and the deployment target. Make the agreed requirements verifiable without silently adding unrelated functionality.
