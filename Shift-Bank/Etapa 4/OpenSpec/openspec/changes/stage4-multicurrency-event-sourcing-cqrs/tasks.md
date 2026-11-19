## 1. Freeze contracts and migration fixtures

- [ ] 1.1 Record the researcher-approved D-01–D-14 contracts and D-02 deviations as the implementation baseline without editing inherited Stage 3 specs.
- [ ] 1.2 Define deterministic fixtures for the reported COP balances, seeded transaction provenance, currency mappings, exact conversion vectors, and ROUND_HALF_UP tie cases.
- [x] 1.3 Define migration preflight fixtures for pending ACH, pending MFA, active/paused schedules, nonzero UTC-day usage, audit verification failure, identity conflicts, and changed source snapshots.

## 2. Currency-aware model, migration, and API

- [x] 2.1 Add explicit USD/EUR/GBP account currencies, stable internal IDs, canonical public references, and legacy request aliases.
- [x] 2.2 Implement the approved one-time 4,000 COP/USD snapshot import with exact residual reconciliation and no balancing transactions.
- [ ] 2.3 Preserve terminal legacy operations as non-posting COP provenance with original IDs, timestamps, amounts, and directions.
- [x] 2.4 Enforce all approved migration preconditions before any financial write and prove abort leaves source financial state unchanged.
- [x] 2.5 Add and verify the zero-balance EUR-3001 and GBP-4001 accounts only as part of an authorized migration execution.
- [ ] 2.6 Expose currency, canonical IDs, legacy aliases, monetary strings, and expected account versions in API responses.
- [x] 2.7 Convert each persisted per-user COP limit once using the approved rate, ROUND_HALF_UP, D-07 caps, minimum-positive fail-closed rule, and recorded rounding/cap provenance.

## 3. Exact FX and financial commands

- [ ] 3.1 Implement backend Decimal and frontend BigInt/integer-cent calculations with two-decimal strings and final-only ROUND_HALF_UP.
- [ ] 3.2 Implement the six fixed rational operational FX rates and conversion history without fees or floating-point arithmetic.
- [ ] 3.3 Enforce same-currency internal transfer rules and reject cross-currency movement outside `/api/conversions`.
- [ ] 3.4 Require UUID idempotency keys and canonical-payload replay/conflict handling for internal transfers, conversions, and ACH.
- [ ] 3.5 Require expected versions for affected accounts, return 409 `ACCOUNT_VERSION_CONFLICT`, and prove exact replay precedes version validation.
- [ ] 3.6 Enforce atomic balance effects and exactly one account-version increment per balance-affecting operation.

## 4. Event store, projections, and integrity

- [x] 4.1 Add the durable append-only SQLite domain event store with explicit ordering and aggregate sequences, separate from HMAC audit records.
- [ ] 4.2 Add synchronous CQRS projections and atomic command/event/projection/audit/idempotency persistence.
- [ ] 4.3 Implement deterministic projection rebuild, snapshot-boundary bootstrap, reconciliation, and fail-closed behavior on missing, duplicate, or inconsistent events.
- [ ] 4.4 Preserve AES-GCM key-version access and verify inherited HMAC audit-chain continuity without rewriting prior records.
- [ ] 4.5 Add injected persistence-failure scenarios proving rollback and auditable rejection/failure behavior without partial financial effects.

## 5. ACH, recurring schedules, limits, and MFA

- [ ] 5.1 Enforce USD-only ACH, debit exactly once at accepted pending, no settlement debit, and exactly one failure refund.
- [ ] 5.2 Preserve recurring cadence, authorization, pause/resume/cancel behavior, single scheduler ownership, deterministic occurrence identity, and restart recovery.
- [ ] 5.3 Enforce same-currency recurring internal transfers and USD recurring ACH.
- [ ] 5.4 Enforce USD-equivalent USD 5,000.00 per-operation and USD 10,000.00 UTC daily limits, counting logical effects once.
- [ ] 5.5 Apply MFA only when exact unrounded USD equivalent is strictly greater than USD 1,000.00; preserve mock code and expiry behavior.
- [ ] 5.6 Verify scheduler retries, concurrent execution, settlement/refund, and account-version behavior with deterministic acceptance tests.

## 6. React client and deployment continuity

- [ ] 6.1 Update React/TypeScript account, history, conversion, idempotency, expected-version, and typed 409 contracts.
- [ ] 6.2 Use BigInt minor units in financial client calculations and display currency-separated totals plus estimate-only USD equivalents.
- [ ] 6.3 Preserve Compose/Nginx/TLS and durable SQLite deployment capability with externally provisioned secrets and TLS material.
- [ ] 6.4 Document restart, backup/rebuild, secure configuration, and deployment acceptance; report deployment NOT VERIFIED until an authorized deployment is actually checked.

## 7. Acceptance evidence and specification traceability

- [ ] 7.1 Add acceptance tests for every scenario in the Stage 4 delta specs and link each result to its requirement and D-01–D-14 contract.
- [ ] 7.2 Run inherited backend/frontend regression only under separate implementation authorization and retain exact commands, outputs, exit codes, and test totals.
- [ ] 7.3 Verify migration conservation, no double-posting, no artificial funds, deterministic reruns, rollback boundaries, and terminal-history preservation.
- [ ] 7.4 Verify all six FX directions, exact rounding vectors, cross-currency rejection, D-07 limits/MFA, D-08 constraints, D-09 event/version behavior, and D-13/D-14 error ordering.
- [ ] 7.5 Record deployment and security verification as PASS, FAIL, or NOT VERIFIED only from observed evidence.
- [ ] 7.6 Verify per-user limit conversion vectors, minimum and ceiling boundaries, provenance, same-batch idempotency, changed-source rejection, and rollback protection for subsequent limit updates.
