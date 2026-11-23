# Tasks: Shift Bank Stage 2 — Functional Complexity and State

**Input**: Design documents from `/specs/002-shift-bank-stage2/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`)
**Prerequisites**: Approved `spec.md`, `plan.md`, `data-model.md`, `contracts/api.md`, `research.md`, `quickstart.md`
**Tests**: Automated tests are required covering scenarios A01 through A21 and inherited E1 tests.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes explicit file paths and testable completion criteria.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify and prepare project baseline for Stage 2 development without altering Stage 1 artifacts.

- [X] T001 Verify clean brownfield environment and baseline test passing status (12 backend tests, 5 frontend tests, frontend build) across `backend/tests/test_api.py` and `frontend/src/App.test.tsx`
- [X] T002 [P] Create Stage 2 test scaffold and isolated SQLite test database fixtures in `backend/tests/conftest.py` maintaining reproducible fresh seed balances (COP 5,000,000.00 Checking, COP 15,000,000.00 Savings) per decisions D-02 and F-10
- [X] T003 [P] Extend TypeScript contract and model declarations in `frontend/src/types.ts` for Dynamic Limits, Beneficiaries, ACH Transfers, and Recurring Schedules per `specs/002-shift-bank-stage2/contracts/api.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema evolution, migration idempotency, and concurrency controls that MUST be complete before user story endpoints are implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement safe, idempotent SQLite schema evolution in `backend/src/database.py` executing a table-rebuild migration (`transfers_v2`) when `destination_account_id` has `notnull == 1` in `PRAGMA table_info(transfers)` to make `destination_account_id` nullable for ACH transfers, copying existing rows, dropping old `transfers`, and renaming `transfers_v2` to `transfers` under `PRAGMA foreign_keys = OFF / ON`, and `CREATE TABLE IF NOT EXISTS` for `beneficiaries`, `limits`, and `recurring_schedules` per `specs/002-shift-bank-stage2/data-model.md` (F-01)
- [X] T005 Implement initial database seed for default dynamic limits (`per_transfer_limit = '5000000.00'`, `daily_limit = '10000000.00'`, `user_id = 'user_mock_001'`) in `backend/src/database.py` per decision D-01, verifying that historical Stage 1 databases are never touched
- [X] T006 [P] Create Pydantic data transfer schemas in `backend/src/models.py` with strict decimal string validations and constraints: `LimitResponse`, `LimitUpdate`, `BeneficiaryCreate`, `BeneficiaryResponse`, `AchTransferCreate`, `RecurringScheduleCreate`, `RecurringScheduleResponse`
- [X] T007 [P] Create shared background execution lock `asyncio.Lock()`, SQLite `BEGIN IMMEDIATE` transaction helpers, and single-process execution mandate (`--workers 1`) in `backend/src/scheduler.py` to prevent race conditions and double financial executions between HTTP requests and background workers (F-07)
- [X] T008 Configure FastAPI lifespan context manager and test endpoint environment gate (`ENABLE_TEST_ENDPOINTS`) in `backend/src/main.py` to initialize and cleanly tear down the autonomous background worker task without blocking HTTP request routing, ensuring test simulation endpoints return 404 in normal application environments (F-03)

**Checkpoint**: Foundation ready — database schema evolved idempotently and background concurrency controls active. User story implementation can now begin.

---

## Phase 3: User Story 1 - User-Configurable Dynamic Limits (Priority: P1) 🎯 MVP

**Goal**: Provide customer controls to view and edit per-transfer and daily cumulative limits (default COP 5M / 10M), enforce limits across all outgoing movements, compute daily consumption within UTC boundaries, and allow immediate limit reductions below current consumption without altering past transactions.

**Independent Test**: Access limits UI, verify default COP 5M / COP 10M, update limits, submit transfers that exceed limits (verifying rejection before MFA), verify transfers matching exact limits succeed, and verify daily limit reduction immediately clamps remaining availability to COP 0.00 (scenarios A10, A11, A12, A14).

### Tests for User Story 1

- [X] T009 [P] [US1] Write automated integration tests in `backend/tests/test_limits.py` for dynamic limits: default retrieval, valid limit update, non-positive limit rejection, decimal precision validation, per-transfer limit boundary rejection, exact-equal boundary allowance, and MFA bypass prevention (A10, A11, A14, F-06)
- [X] T010 [US1] Add automated integration tests in `backend/tests/test_limits.py` for UTC daily cumulative limit aggregation (400 + 300 + 300 succeeds, next 10 fails), immediate daily limit reduction below current consumption with non-negative availability (`max(0, limit - consumed)`), and midnight UTC half-open boundary reset (A12, D-07, F-04)

### Implementation for User Story 1

- [X] T011 [US1] Implement dynamic limits domain service in `backend/src/services.py` computing UTC day consumption within half-open interval `[start_of_day, next_day_start)` (`created_at >= ? AND created_at < ?`), remaining availability `max(Decimal('0.00'), daily_limit - consumption)`, and limit enforcement logic that runs strictly prior to MFA verification (LIM-01..09, D-01, D-07, F-04, F-09)
- [X] T012 [US1] Implement REST endpoints `GET /api/limits` and `PUT /api/limits` in `backend/src/api.py` with input validation rejecting non-positive numbers or amounts with > 2 decimal places per `contracts/api.md`
- [X] T013 [P] [US1] Implement API client methods `getLimits()` and `updateLimits()` in `frontend/src/services.ts`
- [X] T014 [US1] Create Dynamic Limits management component and view in `frontend/src/App.tsx` displaying Configured Limit, Today's Accumulated Consumption, and Remaining Availability, with an edit form and feedback messaging
- [X] T015 [P] [US1] Add Vanilla CSS layout and component styling for the Dynamic Limits card, stats badges, and edit form in `frontend/src/App.css`
- [X] T016 [US1] Write frontend component tests in `frontend/src/App.test.tsx` verifying dynamic limits rendering, consumption display, validation errors on invalid input, and successful limit updates

**Checkpoint**: User Story 1 (MVP) is fully functional and independently testable. Dynamic limits protect all subsequent operations.

---

## Phase 4: User Story 2 - Simulated Third-Party ACH Transfers & Beneficiary Management (Priority: P1)

**Goal**: Support third-party ACH transfers using saved or ad hoc beneficiaries, validate 9-digit routing numbers in real time, debit source balance immediately upon acceptance, settle transfers autonomously in background, simulate deterministic failure via test endpoint, and support beneficiary Create, List, Delete with immutable details.

**Independent Test**: Create and list saved beneficiaries, submit ad hoc ACH transfer with invalid routing (verifying real-time error), submit valid ACH transfer under COP 1M (verifying immediate debit and `PENDING` status), observe background transition to `SETTLED` without second debit, trigger test failure on pending ACH to verify single refund and daily limit exclusion, and delete saved beneficiary verifying past history remains intact (scenarios A03, A04, A05, A06, A07, A08, A09).

### Tests for User Story 2

- [X] T017 [P] [US2] Write automated integration tests in `backend/tests/test_ach.py` for beneficiary management: Create with 9-digit routing and 4–17 digit account number, List, and Delete, verifying immutability and customer boundary scoping (A03, D-08, F-06)
- [X] T018 [US2] Add automated integration tests in `backend/tests/test_ach.py` for ACH transfers: ad hoc transfer with optional save, 9-digit routing validation, 4–17 digit account validation, immediate source debit on `PENDING`, autonomous background settlement to `SETTLED` without double debit, and sensitive ACH MFA step-up (A04, A05, A06, A07)
- [X] T019 [US2] Add automated integration tests in `backend/tests/test_ach.py` for deterministic test-only ACH failure simulation: invoking `POST /api/test/ach/{transfer_id}/fail` on `PENDING` transfer, atomic single refund under `BEGIN IMMEDIATE`, daily limit consumption exclusion, and terminal idempotency / 409 conflict handling (A08, D-06, F-05)

### Implementation for User Story 2

- [X] T020 [US2] Implement Beneficiary domain services in `backend/src/services.py` supporting Create, List, and Delete with strict validation (routing: exactly 9 numeric digits; account: 4–17 numeric digits; immutable banking details) per decision D-08
- [X] T021 [US2] Implement ACH transfer processing domain service in `backend/src/services.py`: dynamic limits validation evaluated strictly prior to sensitive MFA threshold check (F-09), immediate source debit within atomic transaction, recording transfer in `PENDING` status with immutable recipient snapshot, and sensitive MFA intercept (amount >= COP 1M) (ACH-01..05, D-06, F-09)
- [X] T022 [US2] Implement autonomous ACH background settlement logic in `backend/src/scheduler.py` with an explicit 10-second settlement eligibility delay (`created_at <= now_utc - 10s`) transitioning eligible `PENDING` transfers to `SETTLED` with `settled_at` timestamp without secondary debit (ACH-06, D-06, F-03)
- [X] T023 [US2] Implement REST endpoints in `backend/src/api.py`: `GET /api/beneficiaries`, `POST /api/beneficiaries`, `DELETE /api/beneficiaries/{id}`, `POST /api/transfers/ach`, and non-public test endpoint `POST /api/test/ach/{id}/fail` (guarded by `ENABLE_TEST_ENDPOINTS`, using conditional update `WHERE status = 'PENDING'` under `BEGIN IMMEDIATE` for single atomic refund, returning 409 Conflict if not pending) per `contracts/api.md` (F-03, F-05)
- [X] T024 [P] [US2] Implement API client methods `getBeneficiaries()`, `createBeneficiary()`, `deleteBeneficiary()`, `submitAchTransfer()`, and `confirmAchMfa()` in `frontend/src/services.ts`
- [X] T025 [US2] Implement ACH Transfer form and Beneficiary Management section in `frontend/src/App.tsx` with saved beneficiary selector, ad hoc fields, real-time 9-digit routing input validation, "Save beneficiary" toggle, beneficiary deletion controls, and status badges
- [X] T026 [P] [US2] Add Vanilla CSS styling for ACH transfer forms, inline validation error states, beneficiary management cards/table, and ACH status indicators in `frontend/src/App.css`
- [X] T027 [US2] Write frontend component tests in `frontend/src/App.test.tsx` verifying real-time 9-digit routing feedback, beneficiary listing/deletion, ACH submission, and MFA modal handling for sensitive ACH transfers

**Checkpoint**: User Stories 1 and 2 are fully functional and independently testable. Both internal and external ACH transfers operate with limits and beneficiary persistence.

---

## Phase 5: User Story 3 - Scheduled Recurring Payments Lifecycle & Automatic Execution (Priority: P2)

**Goal**: Support recurring payment schedules for internal and ACH transfers with daily (+24h), weekly (+7d), and monthly (+30d) intervals, deterministic UTC start date scheduling, sensitive schedule MFA authorization (`PENDING_MFA` with 300s window and UI resumption), autonomous due processing while running, pause/resume/cancel controls, and failed-run advancement without getting stuck.

**Independent Test**: Create daily schedule without start date (verifying first run is +24h), create schedule with explicit future date `YYYY-MM-DD` (verifying 00:00:00 UTC due date), create sensitive schedule >= COP 1M (verifying `PENDING_MFA`, 300s window, resumption, and activation upon PIN `123456`), trigger background execution sweep (verifying funds debited, history logged, and due date advanced), pause/resume/cancel schedule (verifying cancelled is terminal), and verify schedule due with insufficient funds logs failure and advances due date without debiting (scenarios A15, A16, A17, A18, A19).

### Tests for User Story 3

- [X] T028 [P] [US3] Write automated integration tests in `backend/tests/test_recurring.py` for recurring schedule creation: daily (+24h), weekly (+7d), monthly (strictly +30d), rejection of current/past start dates, valid future `YYYY-MM-DD` at `00:00:00 UTC`, and immutable recipient snapshot retention (A15, A16, D-08, D-09, F-06)
- [X] T029 [US3] Add automated integration tests in `backend/tests/test_recurring.py` for sensitive recurring schedule MFA lifecycle: initialization in `PENDING_MFA` for periodic amount >= COP 1M, no debit on creation, activation on PIN `123456`, challenge expiration to `EXPIRED` after 300s, and unexecutable state while pending (D-03, D-05, F-08)
- [X] T030 [US3] Add automated integration tests in `backend/tests/test_recurring.py` for autonomous recurring execution and lifecycle controls: automated execution of active due schedules, advancing next due date by interval, pause/resume behavior, terminal cancel behavior, and failed execution handling advancing due date upon insufficient funds or dynamic limits (A17, A18, A19, D-04)

### Implementation for User Story 3

- [X] T031 [US3] Implement recurring schedule domain service in `backend/src/services.py`: schedule creation with interval calculation (Daily = 24h, Weekly = 7d, Monthly = strictly 30d), future start date validation (`YYYY-MM-DD` at `00:00:00 UTC`), `PENDING_MFA` lifecycle management with 300s challenge expiration and sweep, and immutable snapshot capture (REC-01..04, D-05, D-08, D-09, F-08)
- [X] T032 [US3] Implement schedule state transition handlers in `backend/src/services.py` for `confirm_mfa`, `pause`, `resume`, and `cancel` (enforcing terminality of `CANCELLED` status per REC-07)
- [X] T033 [US3] Implement autonomous due recurring schedule execution and expiration sweep engine in `backend/src/scheduler.py`: query active overdue schedules under `BEGIN IMMEDIATE` lock, re-validate live balance and dynamic limits, execute transfer atomically, log history movement, advance `next_due_date` by interval (on balance/limit failure, record failure and advance `next_due_date` without debiting), and sweep expired `PENDING_MFA` schedules (REC-05, REC-08, REC-09, REC-10, D-04, F-07, F-08)
- [X] T034 [US3] Implement REST endpoints in `backend/src/api.py`: `GET /api/recurring-schedules` (including on-demand expiration sweep for `PENDING_MFA` past `mfa_expires_at`), `POST /api/recurring-schedules`, `POST /api/recurring-schedules/{id}/confirm-mfa`, `POST /api/recurring-schedules/{id}/pause`, `POST /api/recurring-schedules/{id}/resume`, `POST /api/recurring-schedules/{id}/cancel`, and test endpoint `POST /api/test/recurring/run-due` (guarded by `ENABLE_TEST_ENDPOINTS`) per `contracts/api.md` (F-03, F-08)
- [X] T035 [P] [US3] Implement API client methods for recurring schedules in `frontend/src/services.ts`: `getSchedules()`, `createSchedule()`, `confirmScheduleMfa()`, `pauseSchedule()`, `resumeSchedule()`, `cancelSchedule()`
- [X] T036 [US3] Implement Recurring Payments section in `frontend/src/App.tsx`: schedule creation form (frequency selector, UTC date picker, source/destination), schedule list table displaying statuses (`PENDING_MFA`, `ACTIVE`, `PAUSED`, `CANCELLED`, `EXPIRED`), next due dates, and action buttons for pause, resume, cancel, and MFA resumption
- [X] T037 [US3] Connect sensitive schedule creation to the shared MFA modal in `frontend/src/App.tsx`, supporting closing modal without cancelling, displaying pending schedule in UI, and confirming with code `123456` within 300s window (D-03, D-05)
- [X] T038 [P] [US3] Add Vanilla CSS styling for the Recurring Payments table, frequency dropdowns, status pills, and schedule action buttons in `frontend/src/App.css`
- [X] T039 [US3] Verify that deleting a saved beneficiary does not invalidate or alter active recurring schedules referencing that beneficiary in `backend/tests/test_recurring.py` (REC-11, D-08)
- [X] T040 [US3] Write frontend component tests in `frontend/src/App.test.tsx` for recurring schedule creation, pause/resume/cancel UI interactions, and sensitive schedule MFA modal confirmation

**Checkpoint**: User Story 3 complete. Automated scheduled payments operate autonomously with complete lifecycle controls, MFA verification, and failure advance logic.

---

## Phase 6: User Story 4 - Preservation of Inherited Stage 1 Banking Invariants (Priority: P2)

**Goal**: Preserve 100% backwards compatibility and functional integrity for all inherited Stage 1 capabilities: Checking and Savings accounts, COP currency formatting, own-account transfers, transaction history, sensitive transfer MFA (threshold >= COP 1M, mock PIN `123456`, 300s window, unlimited retries), and fresh seed balances.

**Independent Test**: Run the complete inherited test suite (`test_api.py` and `App.test.tsx`), verifying that all 12 backend tests and 5 frontend tests pass with zero regressions against isolated test databases (scenarios A01, A02, A13, A20).

### Tests for User Story 4

- [X] T041 [P] [US4] Run inherited backend test suite `pytest backend/tests/test_api.py -v` to verify all 12 inherited tests pass against evolved schema without regression (HER-01..05, A01, A02, A13, A20)
- [X] T042 [P] [US4] Write regression tests in `backend/tests/test_stage2_regression.py` verifying that account history queries (`GET /api/accounts/{id}/history`) use `LEFT JOIN accounts da ON t.destination_account_id = da.id` and include `status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')`, returning combined internal and ACH movements in newest-first order with proper description formatting and without exposing internal database IDs (HER-01, F-02, F-06)

### Implementation for User Story 4

- [X] T043 [US4] Ensure `backend/src/api.py` and `backend/src/services.py` implement the multi-state `LEFT JOIN` query for `/api/accounts/{id}/history` and preserve existing Stage 1 payload contracts and response schemas for `/api/accounts`, `/api/transfers`, `/api/transfers/{id}/confirm-mfa` without breaking changes (F-02)
- [X] T044 [US4] Verify database isolation in `backend/src/database.py` and `backend/tests/conftest.py` ensuring test runs create isolated database instances and never access, mutate, or import the preserved historical Stage 1 SQLite database or `backend/shift_bank.db` (D-02, F-10)
- [X] T045 [US4] Ensure frontend dashboard in `frontend/src/App.tsx` maintains friendly Checking and Savings account cards, COP currency formatting (`es-CO`), and Stage 1 history table column headers (Date, Description, Amount)
- [X] T046 [US4] Run inherited frontend test suite `npm --prefix frontend test -- --run` to verify all 5 inherited frontend tests pass without regression

**Checkpoint**: All 4 user stories implemented and integrated. Stage 1 invariants and Stage 2 enhancements coexist seamlessly.

---

## Phase 7: Polish & Cross-Cutting Verification

**Purpose**: Execute end-to-end verification, build validation, error handling audits, and requirement traceability checks across all scenarios A01 through A21.

- [X] T047 [P] Audit all API error responses in `backend/src/api.py` ensuring consistent `{ "detail": "..." }` JSON structures with appropriate HTTP status codes (400 Bad Request, 404 Not Found, 409 Conflict, 410 Gone)
- [X] T048 [P] Audit decimal arithmetic across `backend/src/services.py` and `backend/src/scheduler.py` ensuring zero floating-point operations and strict 2-decimal-place COP precision
- [X] T049 Execute complete backend test suite `pytest backend/tests/ -v` covering all inherited and partitioned Stage 2 tests against isolated test databases, verifying 100% pass rate (A20, F-10)
- [X] T050 Execute complete frontend test suite `npm --prefix frontend test -- --run` and production build `npm --prefix frontend run build` verifying zero TypeScript or bundling errors (A20)
- [X] T051 Run full validation checklist from `specs/002-shift-bank-stage2/quickstart.md` auditing scenarios A01 through A21 and documenting observable evidence
- [X] T052 Verify traceability completeness across `specs/002-shift-bank-stage2/spec.md`, `specs/002-shift-bank-stage2/plan.md`, and this task list, confirming every requirement ID (ACH-01..10, REC-01..12, LIM-01..09, HER-01..06, D-01..09) is fulfilled

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all User Stories**.
- **User Story 1 (Phase 3 - Dynamic Limits)**: Depends on Phase 2 completion — blocks ACH and recurring operations from executing without limits.
- **User Story 2 (Phase 4 - ACH & Beneficiaries)**: Depends on Phase 2 & Phase 3 (dynamic limits must be active to enforce limits on ACH).
- **User Story 3 (Phase 5 - Recurring Schedules)**: Depends on Phase 2, Phase 3, and Phase 4 (schedules execute internal or ACH transfers under limits).
- **User Story 4 (Phase 6 - Inherited Invariants)**: Validates backwards compatibility across all evolved components.
- **Polish (Phase 7)**: Depends on completion of all user story phases.

### Parallel Opportunities

- **Phase 1**: T002 (test scaffold / conftest) and T003 (TypeScript types) can execute in parallel.
- **Phase 2**: T006 (Pydantic models) and T007 (concurrency lock) can execute in parallel.
- **Within US1**: T009 (test scaffold in `test_limits.py`), T013 (frontend service), and T015 (CSS) can run in parallel (T010 extends `test_limits.py` sequentially after T009 to prevent file collision per F-06).
- **Within US2**: T017 (test scaffold in `test_ach.py`), T024 (frontend service), and T026 (CSS) can run in parallel (T018 and T019 extend `test_ach.py` sequentially after T017 to prevent file collision per F-06).
- **Within US3**: T028 (test scaffold in `test_recurring.py`), T035 (frontend service), and T038 (CSS) can run in parallel (T029, T030, and T039 extend `test_recurring.py` sequentially after T028 to prevent file collision per F-06).
- **Within US4 & Polish**: T041 (verification command), T042 (regression tests in `test_stage2_regression.py`), T047 (audit `api.py`), and T048 (audit `services.py`/`scheduler.py`) can run in parallel.

---

## Implementation Strategy & MVP Scope

### MVP Delivery (Phase 1 + Phase 2 + Phase 3)
1. Complete Setup and Foundational database migrations.
2. Implement User Story 1 (Dynamic Limits) end-to-end (backend domain service, REST API, React limits editor).
3. **Validate MVP**: Verify limits configuration, persistence, and boundary enforcement independently.

### Incremental Full Scope Delivery
1. Add User Story 2: Implement Beneficiary Create/List/Delete and simulated ACH transfers with autonomous settlement and single refund.
2. Add User Story 3: Implement automated recurring payment schedules, `asyncio` background execution, MFA authorization, and UTC timing.
3. Validate User Story 4: Run full inherited Stage 1 regression suite (12 backend, 5 frontend tests).
4. Complete Polish: Run production build and verify all scenarios A01 through A21 per `quickstart.md`.
