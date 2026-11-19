## Purpose

Defines currency-explicit API and client behavior while preserving legacy account-reference compatibility and preventing imprecise financial interaction.

## ADDED Requirements

### Requirement: Canonical public IDs and legacy request compatibility
Account queries MUST expose canonical public references CHK-1001, SAV-2001, EUR-3001, and GBP-4001. Existing internal references `acc_checking` and `acc_savings` MUST remain accepted as request aliases for their mapped accounts. Responses and financial history MUST identify currency and must not silently replace original transaction IDs or provenance.

#### Scenario: Client submits an inherited account reference
- **WHEN** an inherited client sends `acc_checking` or `acc_savings` to a supported account operation
- **THEN** the API resolves it to the same account as CHK-1001 or SAV-2001 and returns the canonical public reference with currency

#### Scenario: Client queries a public account reference
- **WHEN** a client requests CHK-1001, SAV-2001, EUR-3001, or GBP-4001
- **THEN** the API returns its canonical identity, supported currency, balance, and expected account version

### Requirement: Precise client arithmetic and currency-separated dashboard
The React/TypeScript client MUST use integer minor units (`BigInt`) for financial calculations and MUST display currency-separated account totals. Any estimated USD total MUST be labelled as an estimate and MUST NOT be used as a ledger balance. The client MUST expose conversion inputs/rate/results, required idempotency and expected-version data, and typed HTTP 409 version/idempotency errors.

#### Scenario: Dashboard groups balances by currency
- **WHEN** the user views accounts with USD, EUR, and GBP balances
- **THEN** totals are separated by currency and any USD equivalent is explicitly marked estimated

#### Scenario: Client retries an ambiguous request
- **WHEN** a network timeout leaves a submitted transfer or conversion outcome unknown
- **THEN** the client retries with the same UUID key and identical payload rather than creating a new financial operation

#### Scenario: Client displays concurrency and idempotency conflicts
- **WHEN** the API returns `ACCOUNT_VERSION_CONFLICT` or an idempotency-key payload conflict
- **THEN** the client distinguishes the error and does not silently retry with a new key or stale account version
