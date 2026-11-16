# Tasks: Shift Bank Stage 4 Multicurrency, FX, Events, and CQRS

**Input**: Design documents from `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Authorization**: Researcher approved Gate B on 2026-11-16 for the reviewed specification and task list. The current implementation milestone is limited to the financial foundation, COP-preserving migration, account/transfer/FX paths, and focused verification; later task groups remain future work. Do not modify Stage 3 or another SDD tool.

**Tests**: Included because the feature contract explicitly requires planned verification for REQ-01â€“REQ-06 and AC-01â€“AC-45. Gate B was approved on 2026-11-16; implementation and task completion are limited to the milestone recorded in `implementation-notes.md`.

## Format

- Every task uses `- [ ] Tnnn [P?] [USn?] Description with exact file path`.
- `[P]` means the task edits a different file and can proceed independently after its listed prerequisites.
- User-story tasks carry `[US1]` through `[US6]`; setup/foundation/polish tasks do not.

## Phase 1: Setup

**Purpose**: Establish safe implementation and evidence boundaries without touching the E3 workspace or historical artifacts.

- [x] T001 Record the approved Stage 4 contract, Gate B precondition, and E4-only write boundary in `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/implementation-notes.md` (FR-026â€“FR-027; AC-25, AC-42).
- [x] T002 [P] Create isolated E3-compatible fixture builder with synthetic test keys and disposable database selection in `backend/tests/fixtures/stage4_baseline.py` (FR-002â€“FR-005, FR-024, FR-026; AC-01â€“AC-03, AC-19, AC-35, AC-38).
- [x] T003 [P] Add Stage 4 test fixtures for the four D-02 reference accounts and currencies in `backend/tests/fixtures/stage4_accounts.py` (FR-001â€“FR-003, FR-026; AC-01â€“AC-03, AC-38).
- [x] T004 [P] Document safe test database and key environment variables without values in `backend/tests/fixtures/README.md` (FR-022â€“FR-023, FR-026; AC-24, AC-39, AC-42).

## Phase 2: Foundational Event, Migration, and Integrity Work

**Purpose**: Build the atomic append-only event and projection foundation required by every monetary story.

- [x] T005 [P] Add migration tests for snapshot balance preservation, legacy history import without balance effects, repeat-run idempotency, conflicting IDs, and rollback in `backend/tests/test_stage4_migration.py` (FR-002â€“FR-005, FR-024; AC-01â€“AC-03, AC-19, AC-35, AC-38).
- [x] T006 [P] Add event-store tests for append-only uniqueness, sequence order, currency immutability, atomic failure, and deterministic replay in `backend/tests/test_stage4_events.py` (FR-006â€“FR-009, FR-021; AC-19â€“AC-22, AC-35â€“AC-37).
- [x] T007 [P] Add idempotency/version tests for exact replay-before-version, changed payload HTTP 409, and stale account HTTP 409 in `backend/tests/test_stage4_concurrency.py` (FR-019â€“FR-020; AC-28â€“AC-30, AC-41).
- [x] T008 Create SQLite event, idempotency, migration-marker, and projection schema with uniqueness/version constraints in `backend/src/database.py` (FR-006â€“FR-009, FR-019â€“FR-024).
- [x] T009 Implement immutable domain-event append/read and deterministic sequence validation in `backend/src/event_store.py` (FR-006â€“FR-009; AC-20â€“AC-22, AC-37).
- [x] T010 Implement atomic projection update/rebuild and currency/conservation/version invariant checks in `backend/src/projections.py` (FR-008â€“FR-009, FR-021; AC-20â€“AC-21, AC-36â€“AC-37).
- [x] T011 Implement UUID-key request fingerprint, stored response, exact replay, and changed-payload conflict handling in `backend/src/idempotency.py` (FR-019â€“FR-020; AC-28â€“AC-30).
- [x] T012 Extend the account entity with immutable currency, integer minor-unit projection, version, and cutover provenance in `backend/src/models.py` (FR-001â€“FR-003, FR-020).
- [x] T013 Implement cutover snapshot/history-only import, insert-if-absent D-02 provisioning, unique migration markers, validation, and rollback in `backend/src/database.py` (FR-002â€“FR-005, FR-024; AC-01â€“AC-03, AC-19, AC-35, AC-38).
- [x] T014 Integrate event, projection, HMAC audit, and idempotency persistence in one command transaction with fail-closed rollback in `backend/src/services.py` (FR-006â€“FR-009, FR-019, FR-021â€“FR-024; AC-14, AC-21, AC-36).

## Phase 3: User Story 1 â€” Currency-Aware Accounts and Preserving Migration (Priority: P1)

**Goal**: Preserve E3 COP balances/history, add four D-02 accounts idempotently, and expose currency-labelled accounts/history.

**Independent Test**: Apply migration to an isolated E3-compatible fixture, repeat provisioning, and compare exact IDs, currencies, amounts, and history before/after (AC-01â€“AC-04, AC-19, AC-35, AC-38).

### Tests for User Story 1

- [x] T015 [P] [US1] Add API tests for currency-labelled account/history responses and USD estimate COP exclusion in `backend/tests/test_stage4_api_contracts.py` (FR-001â€“FR-005; AC-01â€“AC-04, AC-34).
- [x] T016 [P] [US1] Add React tests for per-currency account/history grouping and COP exclusion from estimated USD totals in `frontend/src/App.test.tsx` (FR-004; AC-04, AC-34).

### Implementation for User Story 1

- [x] T017 [US1] Extend account/history response schemas with currency, version, and migration provenance-safe fields in `backend/src/models.py` (FR-001â€“FR-005).
- [x] T018 [US1] Update account and history query handlers to return explicit currency and preserve legacy history rows in `backend/src/api.py` (FR-001â€“FR-005; AC-01, AC-04, AC-19).
- [x] T019 [US1] Implement account provisioning conflict detection and no-overwrite behavior for D-02 IDs in `backend/src/database.py` (FR-003; AC-02â€“AC-03, AC-38).
- [x] T020 [US1] Update account/history frontend types and exact amount display helpers in `frontend/src/types.ts` and `frontend/src/services.ts` (FR-001, FR-004).
- [x] T021 [US1] Render explicit per-currency groups and exclude COP from any estimated USD summary in `frontend/src/App.tsx` (FR-004; AC-04, AC-34).
- [x] T022 [US1] Add migration and account/history acceptance cases to `backend/tests/test_stage2_regression.py` without modifying Stage 3 or older stages (FR-002â€“FR-005, FR-024; AC-01â€“AC-04, AC-19, AC-38).
- [x] T023 [US1] Add account/history currency scenarios to `frontend/src/App.test.tsx` and retain existing Stage 1â€“3 UI assertions (FR-004, FR-026; AC-04, AC-42).

## Phase 4: User Story 2 â€” Same-Currency Transfers, Limits, MFA, Idempotency, and Versions (Priority: P1)

**Goal**: Preserve safe transfers while applying per-currency policies and mandatory retry/concurrency contracts.

**Independent Test**: Cover COP and USD/EUR/GBP operation/daily limits, MFA boundaries, same-currency restriction, replay, and stale versions (AC-05â€“AC-10, AC-26â€“AC-30, AC-40â€“AC-41).

### Tests for User Story 2

- [x] T024 [P] [US2] Add exact Decimal/rational limit and MFA boundary tests for COP, USD, EUR, and GBP in `backend/tests/test_stage4_currency.py` (FR-014â€“FR-015; AC-07â€“AC-09, AC-27, AC-40).
- [x] T025 [P] [US2] Add internal-transfer API tests for mixed-currency rejection, mandatory key/version fields, HTTP 409 replay/version behavior, and no partial effects in `backend/tests/test_stage4_api_contracts.py` (FR-013, FR-019â€“FR-020, FR-025; AC-05â€“AC-06, AC-28â€“AC-30).
- [x] T026 [P] [US2] Add frontend request tests for UUID idempotency keys, expected versions, integer minor-unit payloads, and COP/non-COP MFA prompts in `frontend/src/App.test.tsx` (FR-010, FR-013â€“FR-015, FR-019â€“FR-020; AC-07â€“AC-09, AC-23).

### Implementation for User Story 2

- [x] T027 [US2] Implement exact minor-unit and Decimal/rational money helpers with no float conversions in `backend/src/money.py` and `frontend/src/money.ts` (FR-010, FR-014â€“FR-015).
- [x] T028 [US2] Implement immutable currency validation, same-currency transfer checks, and per-currency exact limit/MFA comparisons in `backend/src/services.py` (FR-013â€“FR-015; AC-05â€“AC-09, AC-27, AC-40).
- [x] T029 [US2] Extend transfer request/response schemas with currency, UUID idempotency key handling, and expected account versions in `backend/src/models.py` (FR-013â€“FR-015, FR-019â€“FR-020, FR-025).
- [x] T030 [US2] Update transfer initiation/MFA confirmation endpoints for version checking, replay-first behavior, limit-before-MFA, and stable 409 errors in `backend/src/api.py` (FR-013â€“FR-015, FR-019â€“FR-020, FR-025; AC-05â€“AC-09, AC-28â€“AC-30, AC-41).
- [x] T031 [US2] Add internal-transfer event creation and one-increment-per-affected-account projection logic in `backend/src/event_handlers.py` (FR-007â€“FR-009, FR-013, FR-020â€“FR-021; AC-05, AC-20, AC-36).
- [x] T032 [US2] Update the encrypted frontend transfer flow to submit the idempotency key and expected account versions without floats in `frontend/src/App.tsx` and `frontend/src/services.ts` (FR-010, FR-013, FR-019â€“FR-020, FR-025; AC-23, AC-28â€“AC-30).
- [x] T033 [US2] Add contract regression scenarios for existing COP transfers, MFA lifecycle, limits, and exact equality behavior in `backend/tests/test_inherited_compatibility.py` (FR-013â€“FR-015, FR-026; AC-05â€“AC-10, AC-27, AC-40, AC-42).

## Phase 5: User Story 3 â€” Simulated USD/EUR/GBP Conversions (Priority: P2)

**Goal**: Perform transparent fixed-rate conversions with exact arithmetic and atomic paired effects.

**Independent Test**: Exercise six rate pairs, sanity values, HALF_UP boundary, idempotency, versions, and COP/unsupported/insufficient-funds rejection (AC-11â€“AC-14, AC-31â€“AC-34).

### Tests for User Story 3

- [x] T034 [P] [US3] Add all six rational-pair, sanity-value, HALF_UP, no-fee, and COP rejection tests in `backend/tests/test_stage4_currency.py` (FR-010, FR-011, FR-012; AC-11â€“AC-14, AC-31â€“AC-34).
- [x] T035 [P] [US3] Add conversion request/response, replay, changed-key, stale-version, and atomic-failure API tests in `backend/tests/test_stage4_api_contracts.py` (FR-012, FR-019â€“FR-021; AC-11â€“AC-14, AC-28â€“AC-33, AC-36).

### Implementation for User Story 3

- [x] T036 [US3] Add the fixed directed rational USD/EUR/GBP rate table and exact conversion calculation in `backend/src/money.py` (FR-010â€“FR-012; AC-12, AC-31â€“AC-32).
- [x] T037 [US3] Implement conversion validation, one-final-rounding, dual-account version checks, and composite event handling in `backend/src/services.py` (FR-010â€“FR-012, FR-020â€“FR-021; AC-11â€“AC-14, AC-31â€“AC-36).
- [x] T038 [US3] Add `POST /api/conversions` request/response handling, encryption, UUID idempotency, and stable validation errors in `backend/src/api.py` (FR-012, FR-019â€“FR-020, FR-025; AC-11â€“AC-14, AC-28â€“AC-33).
- [x] T039 [US3] Add conversion source/destination history presentation with rate and currencies in `frontend/src/types.ts`, `frontend/src/services.ts`, and `frontend/src/App.tsx` (FR-004, FR-010â€“FR-012; AC-11â€“AC-13, AC-23, AC-34).
- [x] T040 [US3] Add frontend integer-minor-unit conversion form/result tests in `frontend/src/App.test.tsx` (FR-010â€“FR-012; AC-11â€“AC-13, AC-23, AC-31â€“AC-32).

## Phase 6: User Story 4 â€” ACH and Recurring Compatibility (Priority: P2)

**Goal**: Preserve COP ACH/recurring behavior, support USD ACH, reject EUR/GBP ACH, and prevent duplicate debit/refund.

**Independent Test**: Exercise COP/USD acceptance, EUR/GBP rejection, pending debit, settlement retry, exactly-once refund, recurring same-currency, and lifecycle/MFA/limit behavior (AC-10, AC-15â€“AC-18, AC-26â€“AC-27).

### Tests for User Story 4

- [x] T041 [P] [US4] Add currency-policy ACH and recurring tests for COP/USD support and EUR/GBP rejection, plus 9-digit routing and 4â€“17-digit bank account validation, in `backend/tests/test_stage4_ach_recurring.py` (FR-016â€“FR-018; AC-15â€“AC-18, AC-43).
- [x] T042 [P] [US4] Add 10-second ACH settlement eligibility, concurrent settle/fail race, settlement retry, failure/refund exactly-once, event version, and idempotency tests in `backend/tests/test_stage4_ach_recurring.py` (FR-017, FR-019â€“FR-021; AC-15â€“AC-16, AC-28, AC-36, AC-43).
- [x] T043 [P] [US4] Add recurring same-currency, daily +24-hour/weekly +7-day/monthly strictly +30-day timing, explicit-date midnight UTC, no-debit-at-creation, concurrent-worker duplicate prevention, 300-second MFA expiry, deterministic occurrence key, schedule lifecycle, and failed-run advancement tests in `backend/tests/test_stage4_ach_recurring.py` (FR-018â€“FR-020; AC-10, AC-18, AC-26â€“AC-27, AC-44).

### Implementation for User Story 4

- [x] T044 [US4] Extend ACH request/state models with immutable currency, expected version, event references, and idempotency identity in `backend/src/models.py` (FR-016â€“FR-019).
- [x] T045 [US4] Enforce COP-legacy/USD ACH allowance and EUR/GBP rejection while preserving recipient snapshots and MFA in `backend/src/services.py` and `backend/src/api.py` (FR-015â€“FR-017; AC-15â€“AC-18).
- [x] T046 [US4] Implement accepted/pending/settled/failed/refunded ACH event handlers with conditional single debit/refund and atomic projections in `backend/src/event_handlers.py` and `backend/src/scheduler.py` (FR-007â€“FR-009, FR-017, FR-021; AC-15â€“AC-16, AC-36).
- [x] T047 [US4] Extend recurring currency validation, same-currency checks, atomic unique occurrence claims, stable per-occurrence UUID keys, version use, and inherited lifecycle in `backend/src/services.py` and `backend/src/scheduler.py` (FR-018â€“FR-020; AC-10, AC-18, AC-26â€“AC-27, AC-44).

## Phase 7: User Story 5 â€” Deterministic Event Replay, Audit, Encryption, and Concurrency (Priority: P1)

**Goal**: Make event replay reliable and preserve separate audit/security guarantees under concurrent requests and failures.

**Independent Test**: Rebuild clean projections repeatedly, inject event/projection/audit/key failures, and race commands using one expected account version (AC-19â€“AC-22, AC-28â€“AC-30, AC-35â€“AC-41).

### Tests for User Story 5

- [x] T048 [P] [US5] Add projection rebuild equality, duplicate/out-of-order event, version-gap, and conservation tests in `backend/tests/test_stage4_events.py` (FR-006â€“FR-009; AC-20â€“AC-22, AC-37).
- [x] T049 [P] [US5] Add atomic rollback and separate audit-ledger verification/failure tests in `backend/tests/test_stage4_events.py` and `backend/tests/test_audit.py` (FR-021â€“FR-022; AC-21â€“AC-22, AC-36, AC-39).
- [x] T050 [P] [US5] Add AES-GCM invalid-key/ciphertext and sensitive log/audit redaction tests in `backend/tests/test_stage4_security.py` (FR-022; AC-39).
- [x] T051 [P] [US5] Add concurrent idempotency/version race tests with one accepted command and one 409 in `backend/tests/test_stage4_concurrency.py` (FR-019â€“FR-021; AC-28â€“AC-30, AC-41).

### Implementation for User Story 5

- [x] T052 [US5] Implement versioned event payload validators and operation-specific event handlers in `backend/src/event_handlers.py` (FR-006â€“FR-009; AC-19â€“AC-22, AC-35â€“AC-37).
- [x] T053 [US5] Enforce serialized SQLite write transactions and conditional expected-version updates in `backend/src/database.py` and `backend/src/services.py` (FR-008â€“FR-009, FR-020â€“FR-021; AC-20â€“AC-21, AC-41).
- [x] T054 [US5] Integrate safe event/command references with existing AES-GCM and HMAC audit helpers without merging event and audit stores in `backend/src/crypto.py` and `backend/src/services.py` (FR-021â€“FR-022; AC-22, AC-39).
- [x] T055 [US5] Add authorized read/rebuild diagnostics and safe integrity error mapping in `backend/src/api.py` (FR-009, FR-021â€“FR-022; AC-20â€“AC-22, AC-39).

## Phase 8: User Story 6 â€” Frontend, Inherited Regression, and Deployment Capability (Priority: P3)

**Goal**: Keep the existing application experience, Stage 3 security boundary, load profile, and deployment capability represented in post-implementation evidence.

**Independent Test**: Run later-authorized regression and isolated deployment checks; verify currency displays, encrypted requests, retained API behavior, and no false claim of E4 results (AC-04, AC-23â€“AC-25, AC-39, AC-42).

### Tests for User Story 6

- [x] T056 [P] [US6] Add dashboard grouping, currency formatting, and COP-estimate exclusion tests in `frontend/src/App.test.tsx` (FR-004, FR-026; AC-04, AC-23, AC-34).
- [x] T057 [P] [US6] Add inherited encrypted request and MFA envelope regression tests in `frontend/src/crypto.test.ts` and `backend/tests/test_stage2_regression.py` (FR-022â€“FR-027; AC-23, AC-39, AC-42).
- [x] T058 [P] [US6] Add API regression assertions for accounts/history/limits/audit/health and guarded test endpoints in `backend/tests/test_stage2_regression.py` (FR-023, FR-026â€“FR-027; AC-24â€“AC-25, AC-42).

### Implementation for User Story 6

- [x] T059 [US6] Update React currency/account/history/limits/transfer/ACH/recurring display and integer amount entry in `frontend/src/App.tsx`, `frontend/src/App.css`, and `frontend/src/types.ts` (FR-004, FR-010, FR-016â€“FR-018, FR-023; AC-04, AC-15â€“AC-18, AC-23).
- [x] T060 [US6] Update encrypted client request helpers to carry UUID idempotency metadata and expected versions without exposing sensitive fields in `frontend/src/crypto.ts` and `frontend/src/services.ts` (FR-019â€“FR-022, FR-025; AC-23, AC-28â€“AC-30, AC-39).
- [x] T061 [US6] Preserve existing container, health, persistent volume, Nginx HTTPS, and secret-mount behavior while adding Stage 4 schema/event storage requirements in `deployment/Dockerfile.backend`, `deployment/docker-compose.yml`, and `deployment/nginx.conf` (FR-022â€“FR-023, FR-027; AC-24â€“AC-25, AC-42).
- [x] T062 [US6] Extend the existing isolated Locust workload to report Stage 4 currency/account request mix while preserving 30 users, 5 users/second ramp, 60-second sustained phase, 60/30/10 balance/history/encrypted-transfer mix, and E3 thresholds in `backend/tests/locustfile.py` (FR-027; AC-25, AC-42, AC-45).
- [x] T063 [US6] Update deployment smoke coverage for currency-labelled accounts, encrypted transfers, MFA, audit verification, and post-restart persistence using disposable volumes in `deployment/smoke_test.py` (FR-022â€“FR-027; AC-24â€“AC-25, AC-39, AC-42).

## Phase 9: Polish and Cross-Cutting Acceptance

**Purpose**: Close traceability and collect separate E4 observations after Gate B only.

- [x] T064 [P] Update Stage 4-specific operational and recovery documentation without editing historical E1â€“E3 specifications in `docs/stage4-operations.md` (FR-024, FR-026â€“FR-027; AC-19, AC-24â€“AC-25, AC-35, AC-42).
- [x] T065 Create the E4 acceptance result matrix mapping AC-01â€“AC-45 and REQ-01â€“REQ-06 to observed outputs in `../_experiment_logs/Spec Kit/acceptance/` (FR-026â€“FR-027; AC-25, AC-42, AC-45).
- [x] T066 Run the authorized isolated backend/frontend acceptance and inherited regression suites after Gate B; record exact commands and observed counts in `../_experiment_logs/Spec Kit/acceptance/` (FR-026; AC-01â€“AC-23, AC-26â€“AC-44).
- [x] T067 Run the authorized E4 Locust profile and isolated deployment smoke only after Gate B; record observed results and limitations in `../_experiment_logs/Spec Kit/acceptance/` (FR-023, FR-027; AC-24â€“AC-25, AC-42, AC-45).
- [x] T068 Complete researcher-facing Gate B implementation review against the approved spec and this task list in `../_experiment_logs/Spec Kit/acceptance/` (FR-026â€“FR-027; AC-01â€“AC-45).

## Dependencies and Execution Order

### Phase Dependencies

- Setup (Phase 1) must establish isolated test resources and authorization notes; it does not modify application behavior.
- Foundational (Phase 2) blocks all stories and must first establish events, idempotency, projections, migration rollback, and atomic audit integration.
- US1 depends on migration/projection foundation and is the first demonstrable MVP slice.
- US2 depends on US1 account currency/version responses and foundational event/idempotency code.
- US3 depends on US1 account currencies and US2 exact arithmetic/version/idempotency helpers.
- US4 depends on US1/US2 currency policy and foundational event handling; it can proceed in parallel with US3 after shared foundations if file ownership is separated.
- US5 hardens shared event/projection/audit/concurrency behavior and should integrate before release acceptance.
- US6 depends on stable API contracts and can proceed in parallel by frontend/deployment ownership after US1/US2 contracts settle.
- Final acceptance tasks depend on all desired stories and a separately approved Gate B implementation.

### User Story Dependencies

- **US1 (P1)**: after Foundation; MVP for safe account/history migration and provisioning.
- **US2 (P1)**: after US1 for currency/version-aware accounts; preserves transfer safety.
- **US3 (P2)**: after US1 and shared arithmetic/idempotency foundation; may parallelize with US4 after shared contract review.
- **US4 (P2)**: after US1/US2 shared currency/limit helpers; ACH state machine work is separate from FX modules.
- **US5 (P1)**: foundational event model starts in Phase 2; story-level replay/security acceptance integrates after US2â€“US4 handlers.
- **US6 (P3)**: UI/deployment updates depend on settled API contracts; independent file ownership permits parallel frontend and deployment tasks.

### Parallel Opportunities

- T002â€“T004, T005â€“T007 can be parallelized by separate test-fixture files.
- T015â€“T016, T024â€“T026, T034â€“T035, T041â€“T043, T048â€“T051, and T056â€“T058 use distinct test files and can run in parallel after their fixtures/contracts are established.
- After foundational schemas settle, US3 rate/UI work and US4 ACH state machine work may proceed in parallel if they do not edit the same service/scheduler files simultaneously.
- US6 frontend tests and deployment regression work may proceed in parallel by file ownership after API contracts are frozen.
- Do not parallelize tasks that edit the same `backend/src/services.py`, `backend/src/database.py`, `backend/src/api.py`, or `frontend/src/App.tsx` without explicit sequencing.

## Planned Test Coverage

| Requirement / decisions | Planned test locations | Acceptance IDs |
|---|---|---|
| REQ-01, D-01/D-02 | `backend/tests/test_stage4_migration.py`, `backend/tests/test_stage4_api_contracts.py`, `frontend/src/App.test.tsx` | AC-01â€“AC-04, AC-19, AC-35, AC-38 |
| REQ-02, D-03/D-04 | `backend/tests/test_stage4_currency.py`, `backend/tests/test_stage4_api_contracts.py`, `frontend/src/App.test.tsx` | AC-11â€“AC-14, AC-31â€“AC-34 |
| REQ-03/REQ-04, D-05/D-06/D-09 | `backend/tests/test_stage4_events.py`, `backend/tests/test_stage4_migration.py` | AC-19â€“AC-22, AC-35â€“AC-37 |
| REQ-05, D-07/D-08 | `backend/tests/test_stage4_currency.py`, `backend/tests/test_stage4_ach_recurring.py`, inherited regression tests | AC-05â€“AC-10, AC-15â€“AC-18, AC-26â€“AC-27, AC-40 |
| D-11/D-13/D-14 | `backend/tests/test_stage4_security.py`, `backend/tests/test_stage4_concurrency.py`, `backend/tests/test_stage4_events.py` | AC-21â€“AC-22, AC-28â€“AC-30, AC-36, AC-39, AC-41 |
| D-10/D-12, REQ-06 | `frontend/src/App.test.tsx`, `backend/tests/test_stage2_regression.py`, `deployment/smoke_test.py`, `backend/tests/locustfile.py` | AC-04, AC-23â€“AC-25, AC-34, AC-42 |

### D-01â€“D-14 to planned verification tasks

| Decision | Planned test/verification tasks | Acceptance IDs |
|---|---|---|
| D-01 | T005, T015, T024 | AC-01, AC-04, AC-06 |
| D-02 | T005, T015, T022 | AC-01â€“AC-04, AC-19, AC-35, AC-38 |
| D-03 | T024, T026, T034, T040 | AC-11â€“AC-14, AC-23, AC-31â€“AC-34 |
| D-04 | T025, T034â€“T035 | AC-05â€“AC-06, AC-11â€“AC-13 |
| D-05 | T005â€“T006, T048 | AC-19â€“AC-22, AC-35â€“AC-37 |
| D-06 | T006, T048 | AC-20â€“AC-21, AC-37 |
| D-07 | T024, T033 | AC-07â€“AC-09, AC-27, AC-40 |
| D-08 | T041â€“T043 | AC-10, AC-15â€“AC-18, AC-26, AC-44 |
| D-09 | T006, T042â€“T043, T048 | AC-05, AC-15â€“AC-16, AC-20â€“AC-21, AC-36, AC-41, AC-43â€“AC-44 |
| D-10 | T016, T056 | AC-04, AC-34 |
| D-11 | T006, T049â€“T050 | AC-21â€“AC-22, AC-36, AC-39 |
| D-12 | T057â€“T058, T062â€“T063 | AC-24â€“AC-25, AC-42, AC-45 |
| D-13 | T007, T025, T035, T042, T051 | AC-28â€“AC-29, AC-41 |
| D-14 | T007, T025, T051 | AC-09, AC-28, AC-30, AC-41 |

## Implementation Strategy

### MVP First

After Gate B only: complete Setup and Foundation, then US1 migration/accounts/history. Validate exact COP value preservation and four-account provisioning before enabling any new monetary command. Continue with US2 and US5 before exposing new conversion/ACH paths.

### Incremental Delivery

1. Foundation and migration snapshots.
2. US1 currency-aware accounts/history.
3. US2 transfers, limits/MFA, idempotency, and versions.
4. US3 FX; US4 ACH/recurring after their shared foundations.
5. US5 replay/audit/concurrency hardening and US6 frontend/deployment/regression evidence.
6. Gate B was granted for the scoped first implementation milestone only. Later milestones and pre-completion researcher review remain separate.

## Notes

- Tasks checked in this file have corresponding implementation and verification evidence. Unchecked tasks remain planned and are not represented as complete.
- All database fixtures must be disposable and isolated. Never mutate the excluded Stage 3 database or real Docker volumes.
- Historical Stage 3 Locust, SonarQube, tests, and deployment reports are context only and cannot satisfy E4 acceptance.
- Tasks T065â€“T068 are complete under E4-SK-07/E4-SK-08 evidence; final researcher acceptance closes the experiment with documented limitations and does not reclassify failures as passes.


## E4-SK-07 Final Validation Status

- T061?T067 are checked based on the E4-SK-07 build, isolated smoke, revised Locust execution, operational runbook, acceptance matrix, and full suite evidence in `implementation-evidence/E4-SK-07-*`. AC-45's transfer p95 target failed; its workload ordering also differs from the approved AC-45 wording and is disclosed in the matrix.
- T068 completed in E4-SK-08 after the researcher explicitly accepted closure with documented limitations. This review is based on recorded automated evidence and is not represented as independent human technical validation.
