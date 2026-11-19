## Why

Shift Bank's inherited OpenSpec contract stores untyped COP balances and mutable financial rows, so it cannot meet the approved Stage 4 currency, conversion, durable event, projection-rebuild, and concurrency contracts. This change specifies a controlled brownfield transition using the researcher's approved one-time COP migration deviation while preserving legacy provenance and Stage 3 safeguards.

## What Changes

- **BREAKING:** Give each active account an explicit USD, EUR, or GBP currency; expose the approved public account references while accepting inherited account identifiers as compatibility aliases.
- **BREAKING:** Specify the approved one-time COP-to-USD migration equivalence, balance snapshot boundary, explicit D-02 balance deviations, exact reconciliation, terminal-history preservation, and fail-closed preconditions for legacy obligations.
- Add fixed-rational FX conversion, same-currency internal transfer constraints, USD-equivalent limits and MFA, currency-specific dashboard totals, and explicit currency-bearing history.
- Add durable append-only domain events, atomic CQRS projections and reconstruction, account versions, UUID idempotency, and exactly-once ACH/recurring transitions.
- Preserve FastAPI, React/TypeScript, SQLite, AES-GCM protection, the HMAC audit chain, and Compose/Nginx/TLS deployment capability.
- Define acceptance scenarios and implementation tasks; this change authorizes specification only, not application changes or financial migration execution.

## Capabilities

### New Capabilities
- `currency-conversion`: Fixed-rational FX, exact arithmetic, serialization, and conversion records.
- `domain-events`: Durable append-only monetary events and event versioning.
- `cqrs-projections`: Synchronous query projections, deterministic rebuild, and fail-closed reconciliation.
- `financial-commands`: Atomic commands, expected account versions, and UUID idempotency.
- `ach-operations`: Currency-aware ACH acceptance, settlement, and single refund.
- `recurring-operations`: Currency-aware schedules, occurrence deduplication, pause/resume, and recovery.
- `transfer-limits`: USD-equivalent operation/daily limits and MFA threshold behavior.
- `migration-and-reconciliation`: Approved COP snapshot import, history provenance, preconditions, replay boundary, and rollback evidence.
- `financial-integrity`: Atomic event/projection/audit/idempotency persistence and preservation of encryption/audit integrity.
- `client-and-api-compatibility`: Public/legacy account references, currency-aware responses, integer-cent UI, and per-currency totals.
- `deployment-continuity`: Durable SQLite event/projection storage and protected external TLS/configuration compatibility.

### Modified Capabilities
- `bank-accounts`: Replace implicit COP/two-account display contract with the approved explicit-currency account and migration contract.
- `transfers`: Add same-currency constraints and preserve inherited transfer validation under the Stage 4 model.
- `mfa`: Replace the inherited COP threshold with the D-07 unrounded USD-equivalent threshold while retaining mock-code and expiry behavior.
- `transaction-history`: Preserve immutable legacy COP provenance and expose currency-explicit Stage 4 transactions.

## Impact

The future implementation will affect `backend/database.py`, `backend/banking.py`, `backend/main.py`, backend schemas and tests; React/TypeScript API types, arithmetic, views and tests; and local Compose/Nginx/TLS configuration and acceptance documentation. The specification phase creates only this native OpenSpec change. It adds no dependency, does not alter inherited source/specifications, and does not execute a migration, test suite, or deployment.
