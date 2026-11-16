# Feature Specification: Shift Bank Stage 4 Multicurrency, FX, Events, and CQRS

**Feature Directory**: `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs`  
**Created**: 2026-11-16  
**Status**: Gate B approved for scoped implementation milestone on 2026-11-16
**Input**: SEED-4 Option A, the D-01–D-14 reference, and the prospective COP compatibility contract authorized by the researcher’s delegation.

## Purpose and Scope

Evolve the existing authenticated mock-user Shift Bank application from its Stage 3 banking model to currency-aware accounts, simulated conversions, durable monetary domain events, and query projections. Preserve the inherited COP accounts, monetary values, transaction history, internal transfers, MFA, COP ACH and recurring behavior, dynamic limits, encryption, audit integrity, load-test artifacts, and deployment capability. Add the four D-02 reference accounts without replacing or relabeling the COP accounts.

This is a specification for a disruptive migration of an existing application, not a new application. Gate B authorizes only the scoped milestone recorded in `implementation-notes.md`; later milestone work is not authorized here. Real banking/FX integrations, registration, login, and any conversion of COP are out of scope.

## Contract Provenance and Accepted Compatibility Decisions

The operative common seed is the complete supplied `SEED-4.md`, extracted from the replication-guide appendix. Its declared SHA-256 is `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`. The standalone approved seed master and original full D-01–D-14 approvals were not available in the inspected workspace. Their absence is recorded; no historical approval is claimed or inferred.

The researcher delegated resolution to the supervising assistant: “tienes que poder tomar la decision siguiendo ese documento de lo que ya se hizo, y no podemos estar en muchas iteraciones con codex y tu. La idea es que saquemos la etapa 4 rapido”. Under that delegation, the numbered COP compatibility contract in the 2026-11-16 researcher instruction is the prospective authority for this specification. The researcher subsequently granted Gate B on 2026-11-16 for the scoped milestone recorded in `implementation-notes.md`; this is researcher acceptance based on the E4-SK-04 agent review and not independent verification.

Accepted prospective deviations from the D-01–D-14 reference are limited to: retain both existing COP accounts and values alongside all four D-02 reference accounts (D-01/D-02); preserve COP limits and `>= COP 1,000,000` MFA while applying D-07 USD-equivalent rules to USD/EUR/GBP; preserve legacy COP ACH and recurring ACH as a D-08 exception; exclude COP from conversions and any estimated USD dashboard total until a COP rate is approved. These adaptations are not claims of identity with another tool’s implementation or specifications.

## User Scenarios & Testing

### User Story 1 — See currency-specific accounts and history (Priority: P1)

As the authenticated mock customer, I need each balance and history entry to identify its currency, so that the migration does not make existing money ambiguous or change its value.

**Why this priority**: Preserving customer monetary state is a prerequisite for every Stage 4 operation.

**Independent Test**: Start from an E3-compatible database fixture and inspect accounts, balances, and histories before and after the specified migration and account provisioning.

**Acceptance Scenarios**:

1. **[AC-01] Given** the two E3 COP accounts and their persisted histories, **When** the Stage 4 migration is applied, **Then** `acc_checking_123` remains COP 5,000,000.00 and `acc_savings_456` remains COP 15,000,000.00 at the baseline snapshot, with every historical entry and amount preserved exactly and no COP value treated as USD.
2. **[AC-02] Given** an account set without the four D-02 IDs, **When** reference provisioning runs, **Then** it creates `CHK-1001` USD 2,500.00, `SAV-2001` USD 10,000.00, `EUR-3001` EUR 0.00, and `GBP-4001` GBP 0.00; repeating provisioning changes no existing balance or history.
3. **[AC-03] Given** a requested reference ID already exists with conflicting identity, currency, or monetary value, **When** provisioning runs, **Then** it fails closed and preserves the existing row rather than overwriting it.
4. **[AC-04] Given** accounts in COP, USD, EUR, and GBP, **When** the dashboard and account histories are viewed, **Then** each amount is labeled and grouped by its own currency; a USD-estimated total excludes COP and is labeled as an estimate.

### User Story 2 — Make safe internal and recurring transfers (Priority: P1)

As the authenticated mock customer, I need same-currency transfers with currency-correct limits, MFA, retries, and conflict handling, so that existing workflows remain safe as more currencies are added.

**Why this priority**: Transfers exercise the inherited financial invariants and concurrency safeguards.

**Independent Test**: Exercise allowed and rejected transfers, MFA boundaries, idempotent replay, and stale account versions independently for COP and USD/EUR/GBP accounts.

**Acceptance Scenarios**:

1. **[AC-05] Given** source and destination accounts with the same currency, **When** an authorized internal transfer is accepted, **Then** the source debit equals the destination credit, one composite domain event records the operation, each affected account version increments once, and balances/history reflect the event.
2. **[AC-06] Given** source and destination currencies differ, **When** an internal transfer is submitted, **Then** it is rejected without monetary or projection changes; conversion must use the conversion workflow.
3. **[AC-07] Given** a COP transfer of COP 999,999.99, COP 1,000,000.00, or COP 1,000,000.01, **When** MFA classification is applied, **Then** only the amounts below COP 1,000,000.00 avoid MFA; the exact threshold and above require MFA.
4. **[AC-08] Given** a USD/EUR/GBP transfer whose exact rational USD equivalent is USD 1,000.00 or less, **When** MFA classification is applied, **Then** MFA is not required; when the unrounded equivalent is greater than USD 1,000.00, MFA is required.
5. **[AC-09] Given** the applicable per-operation or daily limit, **When** an operation would exceed it, **Then** it is rejected before MFA confirmation or debit; equality is allowed, preserving the inherited exact-limit boundary behavior.
6. **[AC-10] Given** an internal recurring instruction, **When** its source and destination are same-currency accounts, **Then** scheduled executions preserve that currency and existing lifecycle behavior; mixed-currency instructions are rejected.

### User Story 3 — Convert supported non-COP currencies (Priority: P2)

As the authenticated mock customer, I need transparent simulated conversions between USD, EUR, and GBP, so that I can understand the exact source, rate, destination, and resulting history.

**Why this priority**: FX is the new cross-currency movement and must be distinct from internal transfers.

**Independent Test**: Exercise each approved rate pair, exact decimal boundaries, insufficient funds, replay, and failure rollback without involving COP.

**Acceptance Scenarios**:

1. **[AC-11] Given** sufficient funds in a USD, EUR, or GBP source account and a destination account in a different supported currency, **When** `/api/conversions` accepts a request, **Then** it returns the exact rational rate, source and destination currencies/amounts, and linked transaction records.
2. **[AC-12] Given** the reference rates, **When** converting 100.00 USD to EUR, 90.00 EUR to GBP, or 0.05 USD to EUR, **Then** the destination amounts are respectively 90.00 EUR, 80.00 GBP, and 0.05 EUR after one final `ROUND_HALF_UP` rounding.
3. **[AC-13] Given** a COP account as either conversion side, **When** conversion is requested, **Then** the request is rejected because no approved COP rate exists and no balances, events, or projections change.
4. **[AC-14] Given** a failed conversion validation, projection update, audit append, or idempotency write, **When** the operation rolls back, **Then** no partial debit, credit, event, projection, or successful idempotency result remains.

### User Story 4 — Use ACH and recurring payments under currency rules (Priority: P2)

As the authenticated mock customer, I need existing COP external payments preserved and new USD ACH supported, so that adding currencies does not silently remove established payment behavior.

**Why this priority**: ACH and recurring schedules have separate lifecycle and double-debit/refund risks.

**Independent Test**: Exercise COP compatibility, USD ACH, unsupported EUR/GBP ACH, settlement, failure refund, and same-currency recurring schedules.

**Acceptance Scenarios**:

1. **[AC-15] Given** an eligible COP or USD account, **When** ACH is accepted, **Then** the source is debited exactly once at pending acceptance, the immutable recipient snapshot and currency are retained, and settlement does not debit again.
2. **[AC-16] Given** a pending ACH that fails, **When** the failure transition is processed more than once, **Then** the source is refunded exactly once and the terminal retry produces no second credit.
3. **[AC-17] Given** an EUR or GBP source account, **When** ACH or recurring ACH is submitted, **Then** it is rejected without monetary effects.
4. **[AC-18] Given** a recurring ACH schedule in COP or USD, **When** it is authorized and due, **Then** existing schedule, MFA, limit, and audit rules apply using that source currency’s approved limit policy.

### User Story 5 — Reconstruct balances and audit operations (Priority: P1)

As a researcher and customer, I need durable monetary events, deterministic query projections, and a distinct security audit chain, so that state can be reconstructed and discrepancies detected.

**Why this priority**: Event replay and separate auditability are the core architectural objective and protect the migrated ledger.

**Independent Test**: Migrate a fixture, replay its event stream into fresh projections, and compare balances, versions, histories, idempotency results, and audit-chain verification.

**Acceptance Scenarios**:

1. **[AC-19] Given** migrated E3 state, **When** the migration imports it, **Then** opening-balance snapshot events establish the exact cutover balances, legacy history remains visible, and legacy transfers are not replayed as new debits/credits on top of those balances.
2. **[AC-20] Given** committed monetary events, **When** projections are rebuilt in event order, **Then** the rebuilt currency-specific balances, account versions, and transaction histories equal the live projections exactly.
3. **[AC-21] Given** an event/projection/audit/idempotency persistence failure, **When** a financial command is processed, **Then** all monetary changes in the command transaction roll back and the failure is recorded through the approved auditable-failure path.
4. **[AC-22] Given** an audit chain and a monetary event stream, **When** either is queried, **Then** the system keeps the HMAC audit ledger separate from domain events and does not treat either as a substitute for the other.

### User Story 6 — Review and operate the Stage 4 application safely (Priority: P3)

As a researcher, I need the existing web application, security controls, and deployment capability represented in acceptance evidence, so that Stage 4 remains comparable and reviewable.

**Why this priority**: Cross-stage regression and deployment capability must be planned even though deployment is not authorized in this milestone.

**Independent Test**: Review the frontend/API contracts and later run the specified isolated acceptance suite and deployment smoke only after implementation authorization.

**Acceptance Scenarios**:

1. **[AC-23] Given** currency-aware account data, **When** the React interface displays balances, histories, transfer details, limits, and schedules, **Then** it uses exact minor-unit arithmetic and explicit currency labels without financial floating-point calculations.
2. **[AC-24] Given** the existing FastAPI/React/SQLite and Docker Compose/Nginx/TLS structure, **When** Stage 4 is implemented, **Then** those deployment capabilities remain specified and no deployment is reported as verified without observed execution.
3. **[AC-25] Given** inherited E1–E3 acceptance contracts, **When** the post-implementation regression suite is eventually run, **Then** results map individually to inherited and Stage 4 acceptance IDs; historical results are not presented as E4 results.

## Requirements

### Functional Requirements

- **FR-001 (REQ-01, D-01/D-02)**: Every account and monetary history entry MUST carry one explicit fixed currency. COP remains a legacy exception; a single account MUST NOT hold heterogeneous-currency balances.
- **FR-002 (REQ-01, D-02)**: The migration MUST preserve the E3 account IDs `acc_checking_123` and `acc_savings_456`, their COP denomination, their cutover monetary values, and every existing history record without relabeling or converting COP to USD.
- **FR-003 (REQ-01, D-02)**: Provisioning MUST add `CHK-1001` USD 2,500.00, `SAV-2001` USD 10,000.00, `EUR-3001` EUR 0.00, and `GBP-4001` GBP 0.00 only when absent; repeated provisioning MUST be idempotent and MUST fail closed on conflicting existing identities or financial values.
- **FR-004 (REQ-01, D-10)**: Account and history views MUST group and label amounts by currency. COP MUST be displayed separately; an estimated USD total MUST exclude COP unless a future approved COP rate is supplied.
- **FR-005 (REQ-01, D-02/D-05)**: Migration MUST establish an unambiguous cutover snapshot for each existing account and preserve historical transactions without applying them a second time to cutover balances.
- **FR-006 (REQ-03, D-05)**: The monetary domain MUST persist append-only domain events independently of the inherited Stage 3 HMAC audit records.
- **FR-007 (REQ-03/REQ-05, D-05/D-09)**: Internal transfers, conversions, ACH lifecycle changes, recurring executions, and migration imports MUST emit deterministic event records with stable IDs, account identity/currency, event time, and command correlation/idempotency reference as applicable.
- **FR-008 (REQ-04, D-06/D-09)**: Query projections for balances, account versions, and transaction histories MUST update synchronously and atomically with accepted domain events.
- **FR-009 (REQ-03/REQ-04, D-06)**: Projection rebuild MUST be deterministic and MUST fail closed with an actionable integrity error if event order, currency, version, or conservation invariants fail.
- **FR-010 (REQ-02, D-03)**: Financial arithmetic for USD/EUR/GBP MUST use exact decimal/rational arithmetic; frontend amounts MUST use integer minor units; monetary strings MUST have two fractional digits; no financial floating-point arithmetic or fees are permitted.
- **FR-011 (REQ-02, D-03)**: The six supplied USD/EUR/GBP pair rates MUST be represented exactly as rational numbers; conversion output MUST round once, at the end, using `ROUND_HALF_UP`.
- **FR-012 (REQ-02, D-04/D-13/D-14)**: `/api/conversions` MUST allow conversions only between different USD/EUR/GBP accounts, return the applied rate and both amounts/currencies, and apply idempotency and expected-version checks.
- **FR-013 (REQ-05, D-04/D-13/D-14)**: Internal transfers MUST be limited to same-currency accounts, preserve source/destination value exactly, enforce source currency limits/MFA, and apply idempotency/version checks.
- **FR-014 (REQ-05, D-07)**: COP operations MUST retain COP 5,000,000.00 per-operation and COP 10,000,000.00 daily limits. USD/EUR/GBP operations MUST use exact, unrounded USD-equivalent per-operation USD 5,000.00 and daily USD 10,000.00 limits; equality is permitted and amounts above a limit are rejected.
- **FR-015 (REQ-05, D-07)**: COP transfers MUST require MFA at or above COP 1,000,000.00. USD/EUR/GBP transfers MUST require MFA only when their unrounded exact USD equivalent is strictly greater than USD 1,000.00. Preserve the inherited mock code `123456`, 300-second challenge window, retry behavior, no-debit-before-confirmation, and limit-before-MFA precedence.
- **FR-016 (REQ-05, D-08)**: ACH MUST be supported from COP accounts as the explicit legacy exception and from USD accounts under the reference contract; EUR and GBP ACH MUST be rejected.
- **FR-017 (REQ-05, D-09)**: ACH MUST debit exactly once at accepted pending state; remain eligible for simulated failure for at least 10 seconds before autonomous settlement; settlement MUST not debit again; terminal failure MUST refund exactly once; every transition MUST be represented in events and projections atomically. Routing numbers MUST contain exactly 9 digits and bank account numbers 4–17 digits.
- **FR-018 (REQ-05, D-08/D-09)**: Internal recurring payments MUST use same-currency accounts. Recurring ACH MUST be supported for COP as a legacy exception and USD under the reference contract, and rejected for EUR/GBP. Preserve daily +24-hour, weekly +7-day, and monthly strictly +30-day cadence; explicit future dates execute at 00:00 UTC. Schedule creation MUST NOT debit; preserve authorization, 300-second MFA expiry, limits, and failed-run advancement. Concurrent workers processing one occurrence MUST produce at most one financial effect.
- **FR-019 (REQ-03/REQ-05, D-11/D-13)**: Internal transfers, conversions, and ACH MUST require a UUID `Idempotency-Key`. An exact accepted replay MUST return the stored outcome without additional monetary, event, projection, or audit effects; reuse with a different payload MUST return HTTP 409.
- **FR-020 (REQ-04/REQ-05, D-14)**: Monetary commands MUST include expected versions for all affected accounts. Stale versions MUST return HTTP 409 `ACCOUNT_VERSION_CONFLICT` without financial effects. Exact idempotent replay MUST be resolved before version validation.
- **FR-021 (REQ-03/REQ-05, D-11)**: Accepted commands MUST commit events, projections, audit records, and idempotency outcome atomically. Rejections/failures MUST not alter balances and MUST be auditable using the separate legacy audit mechanism.
- **FR-022 (REQ-05, D-11)**: Existing AES-GCM sensitive-data encryption, authenticated at-rest encryption, key-failure fail-closed behavior, and HMAC-chained append-only audit integrity MUST be preserved and applied consistently to new sensitive records.
- **FR-023 (REQ-05, D-12)**: The application MUST preserve FastAPI, React/TypeScript, SQLite, and Docker Compose/Nginx/TLS deployment capability; real financial integrations and live FX services remain out of scope.
- **FR-024 (REQ-01/REQ-03, D-05)**: Migration MUST be atomic and repeatable, maintain an import marker, prevent duplicate event application, validate all account currencies and opening balances, and provide a rollback path that leaves the pre-migration database usable on failure.
- **FR-025 (REQ-05, D-13/D-14)**: API request/response contracts and clients MUST expose required idempotency keys and expected account versions. Their addition to old request shapes is an intentional compatibility change and MUST return documented errors rather than weakening D-13/D-14.
- **FR-026 (REQ-06, D-01–D-14)**: Acceptance evidence MUST cover migration preservation, every currency/limit/MFA boundary, conversion rates/rounding, event replay/projection equality, retries, concurrency conflicts, ACH/recurring lifecycle, encryption/audit, and inherited E1–E3 regressions.
- **FR-027 (REQ-06, D-12)**: E3 load-test definitions and historical outputs MUST remain historical evidence; future E4 performance results MUST be measured independently and deployment MUST NOT be called verified absent an observed deployment run.

### Acceptance Traceability

| Common requirement | Verifiable criteria | Requirements | Acceptance scenarios |
|---|---|---|---|
| REQ-01 Currency-aware balances/history and monetary preservation | Original COP IDs, currencies, snapshot values and history are preserved; four reference accounts are idempotently added; conflict fails closed; currencies remain separated in views. | FR-001–FR-005 | AC-01–04, AC-19, AC-26, AC-38 |
| REQ-02 Simulated FX and exact arithmetic | Six rational pair rates, required sanity amounts, single final HALF_UP rounding, no COP FX, no partial effects. | FR-010–FR-012 | AC-11–14, AC-30–32, AC-38 |
| REQ-03 Durable events distinct from audit | Append-only event stream; migration snapshot; separate HMAC audit; deterministic replay and atomic failures. | FR-005–FR-007, FR-009, FR-019, FR-021, FR-024 | AC-19–22, AC-32–35, AC-39 |
| REQ-04 CQRS and projections | Synchronous atomic projections, versioning, deterministic rebuild, fail-closed mismatch behavior. | FR-008–FR-009, FR-020 | AC-20–21, AC-34–35, AC-40 |
| REQ-05 Inherited/security compatibility | Same-currency transfers; currency-specific limits/MFA; COP/USD ACH; recurring; encryption/audit; idempotency and concurrency. | FR-013–FR-025 | AC-05–10, AC-15–18, AC-27–29, AC-33, AC-36–44 |
| REQ-06 Verifiability | Planned isolated acceptance/regression evidence with no claims of unrun tests/deployment. | FR-024, FR-026–FR-027 | AC-01–25, AC-32–45 |

### D-01–D-14 Traceability and deviations

| Decision | Applied contract in this specification | FR trace | Observable acceptance | Status |
|---|---|---|---|---|
| D-01 | One fixed currency per account; retain COP as explicit legacy exception. | FR-001 | AC-01, AC-04, AC-06 | Prospective COP deviation, authorized by delegated contract. |
| D-02 | Add all four specified USD/EUR/GBP reference accounts while preserving E3 COP accounts and value. | FR-002–FR-005 | AC-01–AC-04, AC-19, AC-35, AC-38 | Prospective additive compatibility deviation; values never relabeled. |
| D-03 | Decimal backend, BigInt frontend, two-decimal strings, rational rates, one final HALF_UP, no fees/floats for USD/EUR/GBP; no COP FX. | FR-010–FR-012 | AC-11–AC-14, AC-23, AC-31–AC-34 | Applied; COP conversion excluded by compatibility contract. |
| D-04 | Same-currency internal transfers; supported cross-currency conversion only at `/api/conversions`. | FR-012–FR-013 | AC-05–AC-06, AC-11–AC-13 | Applied. |
| D-05 | Durable append-only SQLite monetary events separate from audit; snapshot migration avoids double counting. | FR-005–FR-009, FR-024 | AC-19–AC-22, AC-35–AC-37 | Applied. |
| D-06 | Atomic synchronous projections, deterministic rebuild, fail closed. | FR-008–FR-009 | AC-20–AC-21, AC-37 | Applied. |
| D-07 | D-07 applies to USD/EUR/GBP using unrounded USD equivalents; COP keeps inherited limits and `>=` MFA threshold. | FR-014–FR-015 | AC-07–AC-09, AC-27, AC-40 | Prospective COP deviation; no COP rate invented. |
| D-08 | USD ACH/recurring ACH follows reference; COP legacy ACH/recurring retained; EUR/GBP ACH unsupported; internal recurring same-currency. | FR-016–FR-018 | AC-10, AC-15–AC-18, AC-26, AC-44 | Prospective COP deviation. |
| D-09 | Composite events, one version increment per affected account/command, ACH debit at pending, no settlement debit, one refund. | FR-007–FR-009, FR-017, FR-020 | AC-05, AC-15–AC-16, AC-20–AC-21, AC-36, AC-41, AC-43–AC-44 | Applied. |
| D-10 | Dashboard separates currencies; estimated USD summary is presentation-only and excludes COP. | FR-004 | AC-04, AC-34 | Applied with explicit COP exclusion. |
| D-11 | AES-GCM, HMAC audit, atomic event/projection/audit/idempotency, auditable failures. | FR-021–FR-022 | AC-21–AC-22, AC-36, AC-39 | Applied. |
| D-12 | Preserve FastAPI/React/SQLite/Compose/Nginx/TLS capability; no deployment verification claim without running it. | FR-023, FR-027 | AC-24–AC-25, AC-42, AC-45 | Applied. |
| D-13 | UUID idempotency keys mandatory for internal transfers, FX, ACH; exact replay no new effects; changed payload returns HTTP 409. | FR-019, FR-025 | AC-28–AC-29 | Applied. |
| D-14 | Expected account versions mandatory; stale version returns HTTP 409 `ACCOUNT_VERSION_CONFLICT`; replay checked first. | FR-020, FR-025 | AC-09, AC-28, AC-30, AC-41 | Applied. |

### Acceptance Scenarios (continued)

5. **[AC-26] Given** same-currency internal recurring accounts, **When** a schedule is created, paused, resumed, canceled, or executed, **Then** the inherited lifecycle and currency are retained and each executed movement is recorded once.
6. **[AC-27] Given** a transfer that exceeds a per-operation or remaining daily limit, **When** submitted, **Then** the limit rejection occurs before MFA and no balance/event is applied.
7. **[AC-28] Given** an exact accepted command replay with the same UUID key and payload but an old expected version, **When** repeated, **Then** the original response is returned without new effects because replay is checked first.
8. **[AC-29] Given** a changed payload using an accepted command’s key, **When** submitted, **Then** HTTP 409 is returned and no second operation is applied.
9. **[AC-30] Given** a command with stale version on any affected account, **When** submitted with a new idempotency key, **Then** HTTP 409 `ACCOUNT_VERSION_CONFLICT` is returned with no monetary effects.
10. **[AC-31] Given** each of the six supported conversion pairs, **When** a valid conversion is completed, **Then** source and destination account currencies are unchanged and the amounts/rate match the rational contract: USD→EUR 9/10; USD→GBP 8/10; EUR→USD 10/9; GBP→USD 10/8; EUR→GBP 8/9; GBP→EUR 9/8.
11. **[AC-32] Given** a conversion result with a half-cent boundary, **When** the destination is calculated, **Then** the exact rational result is rounded once with HALF_UP and no intermediate rounded result is used.
12. **[AC-33] Given** a conversion involving insufficient funds, identical currencies, unsupported currency, malformed idempotency key, or missing/stale versions, **When** submitted, **Then** the documented rejection occurs with no partial account/event/projection changes.
13. **[AC-34] Given** COP in a conversion or USD-estimated dashboard request, **When** no approved COP rate exists, **Then** conversion is rejected and COP is excluded from the estimate while displayed separately.
14. **[AC-35] Given** an E3 state snapshot with existing balances and transaction history, **When** imported, **Then** one cutover opening event per account establishes the exact snapshot and legacy history remains queryable without double application.
15. **[AC-36] Given** an accepted composite transfer or conversion event, **When** persisted, **Then** all account projection updates, history entries, versions, audit record, and idempotency result commit together or none do.
16. **[AC-37] Given** the same event stream and migration snapshot, **When** projections are rebuilt repeatedly, **Then** balances, histories, and versions are identical and conservation invariants hold.
17. **[AC-38] Given** a destination reference account is absent, **When** provisioning runs twice, **Then** the account is created once with its specified identity/currency/seed; existing balances are never reset.
18. **[AC-39] Given** a tampered event or audit record, invalid AES-GCM ciphertext, or missing/invalid key, **When** the affected operation/read runs, **Then** the system fails closed, preserves committed balances, and reports an auditable error without plaintext fallback.
19. **[AC-40] Given** USD/EUR/GBP transfer amounts on either side of USD-equivalent 1,000 and 5,000 operation / 10,000 daily thresholds, **When** submitted, **Then** MFA and limit outcomes follow the exact strictness and unrounded rational comparisons defined above.
20. **[AC-41] Given** two concurrent commands use the same expected account version, **When** both attempt a state change, **Then** at most one commits and the other receives `ACCOUNT_VERSION_CONFLICT`; no duplicate debit/credit occurs.
21. **[AC-42] Given** the inherited E1–E3 acceptance suite and Stage 3 security/deployment artifacts, **When** implementation verification is later authorized, **Then** each inherited workflow/security contract has an explicit observed E4 regression result or is reported NOT VERIFIED; prior E3 outcomes are not reused as E4 measurements.

### Edge Cases

- Existing reference account IDs with wrong currency, name, or balance; missing/duplicate migration marker; malformed legacy monetary values; existing history inconsistent with projected balance.
- Empty event stream, duplicate event ID, out-of-order event, gap in account version, replayed migration snapshot, projection rebuild mismatch, SQLite transaction/commit failure.
- No FX rate for COP, unsupported currency pair, exact half-cent rounding, zero/negative/too-precise amounts, source equals destination, insufficient funds, or changed rate policy (not supported in this fixed-rate contract).
- Missing/invalid UUID idempotency key; same key/same request replay; same key/different payload; concurrent commands sharing one expected version; replay with stale version.
- ACH pending, settlement retry, failure retry, duplicate refund attempt, recurring schedule MFA expiration, insufficient funds/limit on due execution.
- AES-GCM authentication failure, unavailable encryption key, HMAC chain mismatch, audit persistence failure, event/projection/audit/idempotency partial-write attempt.
- COP display or USD estimate with no COP conversion rate; frontend amount beyond safe IEEE-754 range (must remain exact through minor units).

## Key Entities

- **Account**: Stable account ID, display name/type, immutable currency, exact current minor-unit balance, monotonically increasing version, active state, and cutover/provisioning provenance.
- **Domain Event**: Stable event ID, event type, account ID(s), currency, exact amount/rational metadata as applicable, account version(s), timestamp, command/idempotency reference, and immutable event payload.
- **Transaction/History Entry**: User-visible movement tied to one or more domain events; source/destination accounts and currencies, exact amounts, rate for FX, lifecycle status, and legacy-history provenance.
- **Projection**: Rebuildable currency-specific account balance, account version, transaction history, pending ACH/recurring state, and audit-facing read model derived from domain events plus immutable legacy history snapshot.
- **Idempotency Record**: UUID key, canonical request fingerprint, operation type, committed result, and associated event IDs; unique per command scope.
- **Audit Record**: Existing append-only HMAC-chained security/financial audit entry; logically and physically distinct from domain events.
- **Transfer Limit Policy**: COP legacy limits or USD-equivalent non-COP limits, UTC daily consumption, and the applied policy/rational comparison context.
- **Recurring Schedule / Beneficiary**: Existing schedule lifecycle and immutable recipient snapshot, extended with fixed source currency and event/version linkage.
- **Exchange Rate**: Supported directed currency pair and exact numerator/denominator; fixed rates supplied in the reference sheet, with no external service or COP rate.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of migrated baseline COP account balances, IDs, currencies, and historical records equal their pre-migration values; no COP amount is relabeled or converted.
- **SC-002**: Exactly four D-02 accounts exist with their specified IDs, currencies, and seed values after one or repeated provisioning runs; no existing account is reset.
- **SC-003**: All six supported conversion directions produce exact rational results and all three reference sanity cases match to the stated cent after exactly one HALF_UP rounding.
- **SC-004**: 100% of accepted same-currency transfer/conversion/ACH operations preserve currency-specific monetary conservation; rejected/failed operations cause zero partial monetary effects.
- **SC-005**: Rebuilding projections from the committed event stream reproduces every account balance, version, and history entry exactly across repeated rebuilds.
- **SC-006**: Exact accepted idempotent replays create zero additional monetary events, balance changes, projection changes, or successful audit effects; changed-payload key reuse and stale versions return the required HTTP 409 codes.
- **SC-007**: ACH settlement results in zero second debit; repeated failure handling results in at most one refund.
- **SC-008**: Currency-specific limit and MFA boundary scenarios match FR-014/FR-015, including COP `>=` and non-COP strict `>` unrounded USD-equivalent MFA behavior.
- **SC-009**: AES-GCM authentication/key failures and HMAC audit verification failures fail closed; no sensitive data falls back to plaintext storage.
- **SC-010**: Post-implementation E4 verification reports observed outcomes for all AC-01–AC-45 and inherited E1–E3 regressions; unexecuted tests, load runs, and deployment checks remain NOT VERIFIED.

## Assumptions and Out of Scope

- The authenticated mock user and established FastAPI/React/SQLite/Docker Compose/Nginx/TLS application remain the deployment context.
- The fixed FX table in the supplied D-01–D-14 reference is the only rate source for this stage. Rates are deterministic and versioned with each conversion/limit decision; no live FX API, fee, or COP rate is introduced.
- The E3 seed values are baseline snapshot values, not instructions to reset a nonempty database on every startup.
- Existing account/history APIs remain available; D-13/D-14 intentionally add mandatory request fields/headers and documented conflict responses.
- Exact database column layout, transaction batching, event serialization format, query indexes, backup medium, and deployment commands are planning decisions constrained by this contract, not additional business features.
- This milestone creates only specification/planning artifacts. It does not run tests, migrations, builds, load tests, Docker, deployment, or SonarQube and does not authorize application implementation.

### Additional inherited E1–E3 acceptance details

- **AC-43 — ACH delay and beneficiary format**: ACH remains failure-eligible for at least 10 seconds after acceptance before autonomous settlement; settlement does not debit again. Routing numbers contain exactly 9 digits and bank account numbers contain 4–17 digits. Accepted ACH retains an immutable recipient snapshot.
- **AC-44 — Recurring schedule timing and concurrency**: Daily schedules recur at +24 hours, weekly at +7 days, and monthly strictly at +30 days. Explicit future dates are due at 00:00 UTC. Schedule creation makes no debit; retain 300-second MFA expiration and advance schedules under the inherited failed-run behavior. Concurrent workers claiming the same schedule occurrence result in one committed financial effect; retries return the stored outcome without a second debit or credit.
- **AC-45 — Performance profile**: When separately authorized, use 30 Locust users, a 5-users/second ramp, 60 seconds sustained, and a 60% balance-read / 30% history-read / 10% encrypted-transfer mix. Targets remain read p95 <200 ms, transfer p95 <500 ms, unexpected errors <1%; E4 results must be independently observed.
