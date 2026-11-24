# Proposed native OpenSpec Stage 4 artifact plan (not authored)

Installed CLI reports `spec-driven`; native sequence is `openspec new change <name>` followed by proposal, design, delta specs and tasks, then `openspec validate <name> --strict` / `openspec validate --all --strict`. CLI supports `list --specs`, `list`, `show`, `status`, `instructions`, `templates`; `--archived` is a separate validation target. Do not run write commands until checkpoint authorization.

## Candidate change scope
One change for “multi-currency banking with event sourcing and CQRS,” explicitly retaining inherited security, ACH, recurring schedules, dynamic limits/MFA, API and deployment functions. Non-goals: real bank integrations, external FX feeds, user auth redesign, unrelated load tests/deployment redesign.

## Design topics
- Researcher-approved D-02 legacy handling and exactly-once balance/history import.
- Account currencies, account IDs/aliases, response compatibility and currency-separated totals.
- Decimal/integer cents, rational FX, final HALF_UP, conversion endpoint and test vectors.
- Domain event schema, atomic command handling, event versions and deterministic replay.
- CQRS read projections, rebuild, reconciliation and fail-closed response.
- Idempotency key scope/storage/replay response and ordering before expected-version checks.
- Compound-event account version increments and 409 error schemas.
- ACH debit/settlement/refund lifecycle and recurring worker recovery under event model.
- USD equivalent limits/MFA boundary; USD-only ACH; same-currency internal/recurring movement.
- Atomicity with AES-GCM, HMAC audit chain, failures and persistence migrations.
- React/TypeScript behavior and Compose/Nginx/TLS persistence/operations.

## Likely specifications
Modify `bank-accounts`, `transfers`, `mfa`, `transaction-history`; add focused specs for currencies/conversions, domain events/CQRS projections, idempotency/account versions, and migration/reconciliation. Modify inherited ACH/recurring, transfer-limits, audit, encryption, API compatibility, frontend and local deployment specs only where needed. Avoid broad duplicate requirements; delta specs should use native ADDED/MODIFIED/REMOVED requirements and GIVEN/WHEN/THEN scenarios.

## Task decomposition
1. Freeze approved policy, schemas and compatibility matrix.
2. Define and validate migration/reconciliation fixtures (no implementation until H2 approval).
3. Define event vocabulary and account-version invariants.
4. Specify arithmetic/FX and limits/MFA boundaries.
5. Specify transaction idempotency and stale-version/error order.
6. Specify ACH/recurring event transitions.
7. Specify projections/rebuild/fail-closed behavior.
8. Specify encryption/audit atomicity and API/UI/deployment changes.
9. Define automated acceptance/regression vectors and migration rollback/restart evidence.

## Validation and gates
At a future authorized authoring stage: validate named change strict, all active specs/changes strict, and archived task completion separately with `--archived`; inspect diff for traceability and no unrelated Stage 3 edits. Freeze proposal/design/specs/tasks with SHA-256 evidence and researcher sign-off. Only after explicit specification approval may implementation approval be requested. H2 is not authorized by this plan.
