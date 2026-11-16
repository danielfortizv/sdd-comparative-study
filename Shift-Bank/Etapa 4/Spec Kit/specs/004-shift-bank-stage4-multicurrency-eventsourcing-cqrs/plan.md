# Implementation Plan: Shift Bank Stage 4 Multicurrency, FX, Events, and CQRS

**Feature Directory**: `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification at `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/spec.md`.

## Summary

Preserve the E3 COP account state and legacy operations while adding four D-02 reference accounts, exact USD/EUR/GBP conversions, an append-only SQLite monetary event stream, and synchronously maintained/rebuildable CQRS projections. A single SQLite transaction boundary will coordinate accepted events, account/history projections, audit records, and idempotency outcomes. Migration uses a cutover snapshot so inherited balances and prior history are not applied twice. Existing FastAPI, React/TypeScript, SQLite, encryption/audit, and Compose/Nginx/TLS deployment remain the baseline. Gate B was approved on 2026-11-16 for the scoped financial foundation/account/transfer/FX milestone recorded in `implementation-notes.md`.

## Technical Context

**Language/Version**: Python 3.13 (from E3 `deployment/Dockerfile.backend`); TypeScript/React 18.3 (E3 `frontend/package.json`).  
**Primary Dependencies**: Existing FastAPI/uvicorn/cryptography backend; React, TypeScript, Vite frontend; exact locked versions remain in existing lockfiles.  
**Storage**: Existing SQLite database and migration code; new append-only monetary event, idempotency, and projection structures.  
**Testing**: Existing pytest/Vitest suites; focused Stage 4 backend migration/event/currency/concurrency/API/atomicity tests and inherited account, API, crypto, audit, and concurrency regressions have now been run. See `implementation-evidence/` for failure/correction history; exact latest counts are in the E4 implementation record. Frontend, ACH/recurring, deployment, load, and full acceptance suites remain unverified.  
**Target Platform**: Existing local/containerized FastAPI backend and static React frontend served through Nginx TLS.  
**Project Type**: Existing web application with Python API and React/TypeScript client.  
**Performance Goals**: Preserve E3 benchmark contract (30 Locust users, 5 users/second ramp-up, 60-second sustained phase; 60% balance reads, 30% history reads, 10% encrypted transfers; read p95 <200ms, transfer p95 <500ms, unexpected error rate <1%). E4 results must be measured independently after Gate B.  
**Constraints**: No financial float arithmetic; fixed rational rates only; no COP conversion; preserve all E3 money and audit history; SQLite transaction atomicity; no real bank/FX service; Gate B implementation remains bounded by `implementation-notes.md`.  
**Scale/Scope**: One pre-authenticated mock customer, six initial accounts (two inherited COP plus four D-02 accounts), existing transaction histories and recurring/ACH flows, and the Stage 4 monetary domain.

## Constitution Check

| Principle / gate | Plan alignment |
|---|---|
| I. Specification Authority | The supplied seed and prospective delegated COP contract are recorded in `spec.md`; no behavior outside them is planned. |
| II. Specification-First Changes | The reviewed specification preceded Gate B. Gate B now authorizes only the bounded implementation milestone in `implementation-notes.md`. |
| III. Proportional Implementation | Reuse the existing FastAPI/React/SQLite system; no broker, cloud service, live FX, or extra authentication platform. |
| IV. Requirement-Driven Validation | Each requirement and decision maps to AC IDs and planned tests; no result is claimed until observed. |
| V. Strict Scope Compliance | No login/registration, real banking/FX, COP rate, historical database, Docker volume, deployment, or load benchmark was touched in the current milestone. |
| Human gates | Gate B was explicitly approved on 2026-11-16 for the scoped implementation milestone recorded in `implementation-notes.md`; later milestones remain outside that authorization. |

**Gate result**: Gate B approved for the scoped financial foundation/account/transfer/FX milestone; later milestones and final human acceptance remain separate.

## Architecture and Data Flow

1. **Command path**: FastAPI validates encrypted request payloads, UUID idempotency key, currency pair, expected account versions, exact amount, limits, and MFA. It begins an immediate SQLite write transaction, checks a prior idempotency record before version checks, then appends domain event(s), updates account/history projections, appends the HMAC audit record, and stores the successful idempotency response. Commit all or roll back all.
2. **Query path**: Existing account/history reads query currency-aware projections. The projection is a CQRS read model; domain events are the authoritative post-cutover monetary state transitions. Legacy E3 history is imported/preserved as immutable history and is not replayed as new monetary effects.
3. **Migration path**: Inspect the existing E3 database schema and exact values; create a schema-version/import marker; in one transaction, record one cutover opening-balance event per inherited account, preserve existing transaction rows as legacy history, add missing D-02 accounts only, and establish version-zero projections. Validate exact balances, currencies, history counts/content, foreign keys, audit integrity, and account count before commit. On any mismatch, roll back and leave the source database usable. Never reset or relabel existing accounts.
4. **Event path**: Use typed events for account cutover/provisioning, internal transfer, conversion, ACH initiated/settled/failed/refunded, recurring schedule lifecycle, and recurring execution. Composite monetary commands carry one command ID and atomically update all affected account projections. Status-only events such as ACH settlement do not apply another debit.
5. **Rebuild path**: Rebuild a disposable projection from the cutover snapshot plus committed post-cutover events in deterministic order. Enforce event uniqueness, account-version sequence, currency identity, nonnegative balances where inherited rules require, and per-command conservation. A mismatch stops serving the rebuilt projection and fails closed; do not silently repair or skip events.
6. **Currency/limit path**: COP operations retain COP limits and inherited MFA. USD uses identity USD equivalence; EUR and GBP limits/MFA compare exact rational USD equivalents using the approved fixed EUR→USD 10/9 and GBP→USD 10/8 rates. Compare unrounded values and daily aggregates; equality is permitted, excess is rejected. No rate lookup or rounding applies to COP.
7. **Security path**: Preserve encrypted client request envelopes and authenticated AES-GCM storage for sensitive fields; keys remain externally configured. Preserve the separate append-only HMAC audit chain, existing audit verification, fail-closed key/audit behavior, HTTPS, and secret handling. Domain events are not the audit chain.
8. **Inherited workflow details**: Keep ACH failure eligibility through at least 10 seconds after acceptance; validate 9-digit routing and 4–17-digit bank account numbers; preserve daily +24-hour, weekly +7-day, monthly strictly +30-day recurrence and explicit future dates at 00:00 UTC, no debit at schedule creation, 300-second MFA expiry, and inherited failed-run schedule advancement.

## Data Model and Contracts

Detailed logical entities and constraints: [data-model.md](data-model.md).  
HTTP contracts: [contracts/api.md](contracts/api.md).  
Event schemas and lifecycle: [contracts/events.md](contracts/events.md).  
Migration/recovery and planned validation: [research.md](research.md), [quickstart.md](quickstart.md).

### Monetary and concurrency invariants

- Account currency is immutable. Existing E3 accounts remain COP; reference accounts carry USD/EUR/GBP exactly as specified.
- Store/exchange amounts as integer minor units at the frontend/API boundary and exact decimal text in the existing backend monetary domain. Never convert through binary floats.
- FX uses the directed rational rates in the approved reference. Round destination minor units once using HALF_UP. Persist the rate numerator/denominator and resulting amounts.
- Each successful monetary command increments each changed account version exactly once. A pending MFA request that has not moved money does not increment account balance versions. A stale version rejects the whole command.
- Each domain event is immutable and uniquely identified. A transfer/conversion event group is atomic and carries consistent command/event IDs and account versions.
- Exact idempotent replay is checked before account version validation and has no additional side effects. Reusing a key with a different canonical payload is HTTP 409.
- Event, changed projections, audit entry, and accepted idempotency result commit atomically. Failure before commit leaves no partial financial state.

## Implementation Phases

1. **Baseline and schema foundation**: snapshot/restore strategy, schema version, immutable event and idempotency storage, account version fields, disposable test fixtures, no seed overwrite.
2. **Migration and replay core**: cutover snapshots, preserved legacy history, migration idempotency/rollback, deterministic projection rebuild and invariant checks.
3. **Currency-aware accounts and transfers**: API/frontend contracts, exact arithmetic, currency-specific limits/MFA, idempotency and expected versions.
4. **FX conversions**: fixed rational rates, rounding, conversion events, linked history, replay/concurrency coverage.
5. **ACH and recurring compatibility**: COP exception, USD support, EUR/GBP rejection, no duplicate settlement/refund, same-currency recurring.
6. **Security, dashboard, and deployment regression**: AES-GCM/HMAC integrity, separate currency summaries, E1–E3 regression, independent E4 load/deployment evidence after authorization.

## Test and Verification Strategy (not executed)

Plan isolated pytest/Vitest tests for every AC-01–AC-42 group; use disposable SQLite databases and deterministic test keys, never the excluded production-like database or deployment secrets. Add API contract assertions for exact 409 errors and fields, migration no-value-change/repeat/rollback cases, rational arithmetic boundary cases, event replay equivalence, concurrent stale-version requests, ACH exactly-once transitions, frontend integer-minor-unit behavior, HMAC/AES-GCM failures, and E1–E3 workflow regression. Run the retained E3 Locust profile and deployment smoke only after Gate B and in isolated resources. Report all unexecuted evidence as NOT VERIFIED.

## Project Structure

### Documentation (this feature)

```text
specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   └── events.md
├── tasks.md
└── checklists/
    ├── requirements.md
    └── contract-review.md
```

### Application areas to be changed only after Gate B

```text
backend/src/{database.py,models.py,api.py,services.py,crypto.py,scheduler.py}
backend/tests/{migration,event-store,projections,currency,concurrency,api,ach,recurring,crypto}.py
frontend/src/{types.ts,services.ts,crypto.ts,App.tsx,App.css}
frontend/src/{App.test.tsx,crypto.test.ts}
deployment/{Dockerfile.backend,docker-compose.yml,nginx.conf}
scripts/{seed_load_db.py,run_load_test.py}
```

This is a task-planning map, not authorization to modify those files. Preserve existing files where possible; add narrowly scoped modules only if required by the approved data model.

## Complexity Tracking

| Added element | Why needed | Simpler alternative rejected because |
|---|---|---|
| Separate append-only monetary event store and read projections | Explicit REQ-03/REQ-04 and D-05/D-06 require replayable financial transitions distinct from the audit trail. | Treating audit records as domain events violates the contract and cannot reliably rebuild account balances. |
| Idempotency store and account versions | D-13/D-14 require replay safety and optimistic concurrency. | Relying only on current balances or UI disabling cannot prevent duplicate requests or stale concurrent writes. |
| Cutover snapshot plus preserved legacy history | Required to retain E3 balances/history without double applying historical transfers. | Replaying legacy transfer rows on top of current balances risks changing inherited monetary value. |
