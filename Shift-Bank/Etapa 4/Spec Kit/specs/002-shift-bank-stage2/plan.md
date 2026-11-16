# Implementation Plan: Shift Bank Stage 2 — Functional Complexity and State

**Branch**: `002-shift-bank-stage2` | **Date**: 2026-11-14 | **Spec**: [specs/002-shift-bank-stage2/spec.md](spec.md)

**Input**: Approved Stage 2 feature specification from `/specs/002-shift-bank-stage2/spec.md`

## Summary

Extend the brownfield Shift Bank Stage 1 application with Stage 2 (Option A: Functional Complexity and State) capabilities: user-configurable dynamic limits (default COP 5M per-transfer / COP 10M daily), simulated third-party ACH transfers with autonomous background settlement and test-only deterministic failure simulation, automated scheduled recurring payments (daily, weekly, monthly) with inherited MFA verification for sensitive creations, and persistent immutable beneficiary records.

The technical approach builds directly upon the existing Python 3.13 FastAPI backend with direct `sqlite3` persistence (no ORMs) and the Vanilla CSS React + TypeScript frontend built with Vite. Background processing is executed autonomously via FastAPI's native lifespan `asyncio` worker tasks running in a single-process deployment (`uvicorn --workers 1`), protected by an in-process `asyncio.Lock` and SQLite `BEGIN IMMEDIATE` transaction locks (F-07), with an explicit 10-second settlement eligibility delay for ACH transfers (F-03) and test-only simulation endpoints protected by an environment gate. Brownfield schema evolution is handled through a safe, idempotent SQLite table-rebuild migration in `backend/src/database.py` that makes `destination_account_id` nullable without breaking foreign keys (F-01) and protects Stage 1 seed reproducibility (Checking COP 5,000,000.00, Savings COP 15,000,000.00) without accessing or migrating the historical Stage 1 database (D-02).

---

## Technical Context

**Language/Version**: Python 3.13 (Backend), TypeScript 5.5+ / React 18+ (Frontend)

**Primary Dependencies**: `fastapi`, `uvicorn`, `pydantic` (Backend); `react`, `react-dom`, `vite` (Frontend). No new external packages required.

**Storage**: SQLite using Python's built-in `sqlite3` module directly (no ORMs). Single-process mandate (`uvicorn --workers 1`) with write operations executed under `BEGIN IMMEDIATE` transaction locks (F-07).

**Testing**: `pytest` and `httpx` (Backend); `vitest` and `@testing-library/react` (Frontend). Tests run against isolated, code-seeded SQLite test databases (`TEST_DB_PATH` / temporary fixtures) to prevent test pollution of `shift_bank.db` (F-10).

**Target Platform**: Modern Web Browsers and Python 3.13+ runtime environment (Windows / cross-platform, single worker process).

**Project Type**: Web service / Web application (Brownfield extension).

**Performance Goals**: Sub-second API responses; background processing sweeps every 5–10 seconds; instant input feedback (< 50ms) on routing number validation.

**Constraints**: Exact Colombian Peso (`COP`) currency representation using Python `decimal.Decimal` (string representation in REST APIs); Vanilla CSS only (no Tailwind or external CSS frameworks); pre-authenticated mock customer session (no real login or external clearing house); test simulation endpoints strictly disabled in normal environments.

**Scale/Scope**: Single authenticated mock user with Checking and Savings accounts, up to dozens of saved beneficiaries, dynamic limits, active recurring schedules, and ACH transfer movements.

---

## Constitution Check

*GATE: Passed before Phase 0 research. Re-evaluated and passed after Phase 1 design.*

- **Specification Authority (Principle I)**: PASS. All planned capabilities map directly to approved requirements (FR-001 through FR-038) and researcher decisions D-01 through D-09. Live clearing networks, real login, card payments, and loans are strictly out of scope.
- **Specification-First Changes (Principle II)**: PASS. The specification (`spec.md`) and requirements quality checklist (`checklists/requirements.md`) were fully clarified, verified, and ratified before formulating this implementation plan.
- **Proportional Implementation (Principle III)**: PASS. No heavyweight task queues (Celery/Redis) or ORMs (SQLAlchemy) are introduced. Native `asyncio` lifespan workers and pure `sqlite3` queries keep the implementation stage-proportional and maintainable.
- **Requirement-Driven Validation (Principle IV)**: PASS. All 21 shared acceptance scenarios (A01 through A21) and inherited E1 tests are explicitly mapped to automated unit/integration tests and observable criteria.
- **Strict Scope Compliance (Principle V)**: PASS. Internal database IDs remain hidden from user-facing views; accounts display friendly labels; currency is strictly COP.
- **Workflow & Tool Neutrality**: PASS. The plan employs project-native test runners (`pytest`, `npm test`) and avoids proprietary external tool locks.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-shift-bank-stage2/
├── spec.md              # Approved Stage 2 feature specification
├── plan.md              # This file (Technical Implementation Plan)
├── research.md          # Technical research log and architectural decisions
├── data-model.md        # Extended SQLite schema, entity models, and state machines
├── quickstart.md        # Runnable verification and testing guide (A01–A21)
├── checklists/
│   └── requirements.md  # Requirements quality validation checklist (16/16 pass)
└── contracts/
    └── api.md           # REST API endpoint contract definitions
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api.py                   # FastAPI REST endpoints (inherited + Stage 2 endpoints)
│   ├── database.py              # SQLite connection, idempotent rebuild migration, fresh seed
│   ├── main.py                  # FastAPI app bootstrapper with background lifespan worker
│   ├── models.py                # Pydantic schemas with decimal string conversions
│   ├── scheduler.py             # Background worker: recurring schedules, ACH settlement, MFA sweep
│   └── services.py              # Core domain logic: limits engine, MFA lifecycle, ACH transitions
├── requirements.txt             # Python backend dependencies
└── tests/
    ├── conftest.py              # Isolated test database fixtures & TEST_DB_PATH setup (F-10)
    ├── test_api.py              # Inherited Stage 1 test suite (12 tests preserved)
    ├── test_limits.py           # US1 Dynamic Limits tests (A10, A11, A12, A14) (F-06)
    ├── test_ach.py              # US2 ACH & Beneficiaries tests (A03–A09) (F-06)
    ├── test_recurring.py        # US3 Recurring Payments tests (A15–A19) (F-06)
    └── test_stage2_regression.py # US4 Inherited & multi-state history tests (A01, A02, A13, A20) (F-06)

frontend/
├── src/
│   ├── App.css                  # Vanilla CSS layout and tab/modal styling
│   ├── App.tsx                  # Main React layout with section tabs & state orchestration
│   ├── main.tsx                 # React DOM bootstrapper
│   ├── services.ts              # API client functions for backend endpoints
│   ├── types.ts                 # TypeScript interfaces for Stage 2 models & contracts
│   └── components/              # (Optional internal modularization if needed)
│       ├── AchTransferForm.tsx
│       ├── BeneficiaryList.tsx
│       ├── LimitsEditor.tsx
│       └── RecurringScheduleList.tsx
├── package.json                 # Frontend dependencies and test scripts
├── tsconfig.json                # TypeScript configuration
└── vite.config.ts               # Vite build configuration
```

**Structure Decision**: Option 2 (Web application with separate `backend/` and `frontend/` directories), extending the existing Stage 1 application layout without reorganizing directory trees.

---

## Technical Architecture & Design Decisions

### 1. Autonomous Background Engine & Scheduler (`scheduler.py`) (Remediating F-03, F-07)
- Integrated into FastAPI via `@asynccontextmanager` in `main.py` under a mandated single-process deployment (`uvicorn --workers 1`).
- Runs a background loop every 5 seconds (configurable) that:
  1. Acquires an `asyncio.Lock` to guarantee in-process concurrency protection against active HTTP requests.
  2. Executes database updates inside SQLite `BEGIN IMMEDIATE` transactions to prevent write contention and race conditions.
  3. Queries `recurring_schedules` for records with `status = 'ACTIVE'` and `next_due_date <= now_utc`.
  4. Evaluates each due schedule: checks account balance and dynamic daily/per-transfer limits. If valid, debits account, creates completed transfer record, and advances `next_due_date` by interval. If funding or limits fail, logs failure and advances `next_due_date` by interval without debiting (REC-10).
  5. Sweeps `recurring_schedules` in `PENDING_MFA` status where `mfa_expires_at < now_utc`, transitioning them to `EXPIRED` (F-08).
  6. Queries `transfers` for ACH records where `transfer_type = 'ACH'`, `status = 'PENDING'`, and `created_at <= now_utc - 10 seconds` (10-second settlement eligibility delay, F-03), updates status to `SETTLED`, and records `settled_at` without secondary debits (ACH-06, D-06).
- Concurrency & Restart Recovery:
  - If backend is restarted, on startup it immediately recovers any overdue active schedules and processes them.
  - Test-only trigger endpoints (`POST /api/test/recurring/run-due` and `POST /api/test/ach/settle-pending`) allow synchronous invocation during testing without waiting for the timer.
  - **Environment Gating**: Test endpoints (`/api/test/...`) are mounted only when `ENABLE_TEST_ENDPOINTS=true` (or during test sessions) and return HTTP 404 in normal application environments.

### 2. Brownfield Schema Evolution & Migration Safety (`database.py`) (Remediating F-01)
- In the Stage 1 baseline, `transfers.destination_account_id` was declared `TEXT NOT NULL REFERENCES accounts(id)`. Standard SQLite cannot drop `NOT NULL` constraints via `ALTER TABLE`.
- Python migration function in `backend/src/database.py` runs during `init_db()` and inspects `PRAGMA table_info(transfers)`:
  - If `destination_account_id` has `notnull == 1`, executes an idempotent table rebuild:
    1. `PRAGMA foreign_keys = OFF;`
    2. Creates `transfers_v2` with `destination_account_id TEXT NULL`, all Stage 1 columns, and new Stage 2 columns (`transfer_type`, `recipient_name`, `bank_name`, `routing_number`, `account_number`, `settled_at`, `failed_at`, `refunded_at`).
    3. Copies existing records: `INSERT INTO transfers_v2 (id, source_account_id, destination_account_id, amount, status, created_at, expires_at) SELECT id, source_account_id, destination_account_id, amount, status, created_at, expires_at FROM transfers;`
    4. Drops old table: `DROP TABLE transfers;`
    5. Renames table: `ALTER TABLE transfers_v2 RENAME TO transfers;`
    6. `PRAGMA foreign_keys = ON;`
  - Creates new tables `beneficiaries`, `limits`, and `recurring_schedules` via `CREATE TABLE IF NOT EXISTS`.
  - Seeds default limits (`per_transfer_limit = '5000000.00'`, `daily_limit = '10000000.00'`, `user_id = 'user_mock_001'`) if not already present.
  - Invariant: Historical Stage 1 database is never touched; fresh seed balances (COP 5M checking / 15M savings) and the two seeded transfers are preserved intact (D-02).

### 3. Dynamic Limits Engine & UTC Consumption Windowing (`services.py`) (Remediating F-04, F-09)
- **Daily Consumption Calculation (F-04)**: Computed dynamically using a mathematically sound half-open UTC interval `[start_of_day, next_day_start)`:
  ```sql
  SELECT amount FROM transfers 
  WHERE source_account_id = ? 
    AND created_at >= ? AND created_at < ? 
    AND status IN ('COMPLETED', 'PENDING', 'SETTLED');
  ```
  where `start_of_day = YYYY-MM-DDT00:00:00Z` and `next_day_start = NEXT_DAY_YYYY-MM-DDT00:00:00Z`. This reliably captures timestamps with fractional seconds (e.g. `.500000Z`) or offset notation and excludes `FAILED` and `EXPIRED` transfers (LIM-06, D-06).
- **Validation Precedence (F-09)**: In `POST /api/transfers` and `POST /api/transfers/ach`, dynamic limits (both per-transfer limit and remaining daily availability) MUST be evaluated BEFORE checking the sensitive transfer threshold (amount >= COP 1,000,000.00). If a transfer exceeds either limit, it is rejected immediately with HTTP 400 Bad Request, preventing MFA prompts on invalid requests and ensuring a valid MFA PIN cannot bypass limits (LIM-07, A14).
- **Remaining Availability Calculation (D-07)**:
  $$\text{remaining} = \max(\text{Decimal("0.00")}, \text{daily\_limit} - \text{consumption})$$
- Immediate reduction: When daily limit is updated below current consumption, remaining availability evaluates to COP 0.00, blocking subsequent outgoing transfers until midnight UTC (D-07).

### 4. ACH Lifecycle, Atomic Settlement, Failure Simulation & History Visibility (Remediating F-02, F-03, F-05)
- **Creation & Debiting**:
  - Direct ACH transfers debit source account balance immediately upon acceptance and enter `PENDING` status (ACH-05, A07).
  - Sensitive ACH transfers (>= COP 1M) enter `PENDING_MFA`; source account is debited once code `123456` is confirmed.
- **Autonomous Settlement (F-03)**:
  - Background worker checks for transfers where `transfer_type = 'ACH'`, `status = 'PENDING'`, and `created_at <= now_utc - 10 seconds` (10-second settlement eligibility delay).
  - Transitions `PENDING` -> `SETTLED`, records `settled_at`. No secondary debit occurs.
- **Deterministic Test-Only Failure & Atomic Single Refund (F-05)**:
  - Transition from `PENDING` to `FAILED` is strictly conditional under SQLite `BEGIN IMMEDIATE`:
    ```sql
    UPDATE transfers 
    SET status = 'FAILED', failed_at = ?, refunded_at = ? 
    WHERE id = ? AND status = 'PENDING';
    ```
  - Refund balance increment (`UPDATE accounts SET balance = balance + amount WHERE id = source_id`) executes **ONLY IF** `cursor.rowcount == 1`.
  - If `cursor.rowcount == 0` (transfer was already `SETTLED` or `FAILED`), the refund is skipped and HTTP 409 Conflict is returned, guaranteeing zero double refunds and idempotent handling.
- **Account Movement History Visibility (F-02)**:
  - The endpoint `GET /api/accounts/{id}/history` uses a `LEFT JOIN accounts da ON t.destination_account_id = da.id` and queries `status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')`.
  - Format: Internal transfers display `Transfer from {src} to {dest}` (or `Transfer to {dest}`); ACH transfers display `ACH Transfer to {recipient_name} ({bank_name}) - {status}` with direction `outgoing`.

### 5. Recurring Schedule Lifecycle & Sensitive Authorization (Remediating F-08, D-03, D-05, D-08, D-09)
- Standard schedule (< COP 1M): Persisted directly in `ACTIVE` status.
- Sensitive schedule (>= COP 1M):
  - Persisted in `PENDING_MFA` status with `mfa_expires_at = now + 300s`.
  - Closing the modal retains `PENDING_MFA` and allows UI resumption (D-05).
  - Entering `123456` transitions status to `ACTIVE`.
- **Expiration Sweep (F-08)**: Both the background scheduler and schedule listing endpoint (`GET /api/recurring-schedules`) automatically transition any schedule where `status = 'PENDING_MFA'` and `mfa_expires_at < now_utc` to `EXPIRED`.
- Scheduling Timing (D-09):
  - If `start_date` (`YYYY-MM-DD`) is provided, validated to be strictly future relative to `now_utc`; first due date is `YYYY-MM-DDT00:00:00Z`.
  - If omitted, first due date is `now_utc + interval` (Daily = 24h, Weekly = 7d, Monthly = strictly 30d).
- Immutability Snapshot (D-08):
  - Recipient banking details are stored directly in `recurring_schedules`. Deleting the saved beneficiary has no impact on existing schedules.

### 6. Frontend Component Integration & Real-Time Validation
- Section Tabs in `App.tsx`:
  1. **Accounts & History**: Preserves Stage 1 account overview cards and movement table.
  2. **Internal Transfers**: Preserves own-account transfer form with limits validation.
  3. **ACH Transfers**: Dedicated form with saved beneficiary dropdown or ad hoc recipient inputs, real-time 9-digit routing validation (instant inline error on < 9 digits), and "Save beneficiary" checkbox.
  4. **Beneficiaries**: Table of saved recipients with "Add Beneficiary" modal/form and "Delete" actions (D-08).
  5. **Recurring Payments**: Table of active/paused/cancelled schedules, status badges, next due dates (with UTC note), and pause/resume/cancel controls.
  6. **Dynamic Limits**: Card displaying Per-Transfer Limit, Daily Limit, Today's Consumption, and Non-negative Remaining Availability, with an Edit form.
- MFA Modal:
  - Reused for sensitive transfers (internal & ACH) and sensitive recurring schedule creations (D-03, D-05).
  - Displays countdown timer (300 seconds), handles invalid PIN retries, and supports closing and resuming.

---

## Requirement-Driven Test Strategy (A01 – A21) (Remediating F-06, F-10)

| Scenario | Scope & Focus | Verification Method |
|---|---|---|
| **A01** | Inherited accounts, COP starting balances (5M / 15M), history | `test_api.py::test_get_accounts` |
| **A02** | Own-account internal transfer balance & history invariants | `test_api.py::test_transfer_success_under_one_million` |
| **A03** | Create, list, and retrieve saved ACH beneficiary | `test_ach.py::test_create_and_list_beneficiary` |
| **A04** | Valid ad hoc ACH transfer with optional save beneficiary | `test_ach.py::test_adhoc_ach_transfer_with_save` |
| **A05** | Reject 8-digit and non-numeric routing; accept 9 digits | `test_ach.py::test_routing_number_validation` + `App.test.tsx` |
| **A06** | Reject 3-digit and 18-digit account numbers; accept 4–17 | `test_ach.py::test_account_number_validation` |
| **A07** | ACH pending immediately debits; settlement updates state only | `test_ach.py::test_ach_pending_debit_and_settlement` |
| **A08** | Failed ACH refunds once; idempotent reprocessing | `test_ach.py::test_ach_failure_single_refund_and_idempotency` |
| **A09** | Reject 0, negative amounts, and > 2 decimal places | `test_ach.py::test_invalid_amounts_rejection` |
| **A10** | View & edit limits; takes effect immediately | `test_limits.py::test_update_dynamic_limits` |
| **A11** | Reject above per-transfer limit; permit exact equal amount | `test_limits.py::test_per_transfer_limit_boundaries` |
| **A12** | Daily limit accumulation test (400 + 300 + 300 ok; 10 fails) | `test_limits.py::test_daily_limit_accumulation_scenario` |
| **A13** | Preserve E1 MFA threshold (>= 1M), wrong PIN retry, expiry | `test_api.py::test_sensitive_transfer_*` |
| **A14** | Valid MFA PIN cannot bypass per-transfer or daily limits | `test_limits.py::test_mfa_cannot_bypass_limits` |
| **A15** | Daily schedule without start date runs after +24h, not immediately | `test_recurring.py::test_recurring_default_first_due_date` |
| **A16** | Weekly (+7d) and monthly (strictly +30d) schedule intervals | `test_recurring.py::test_recurring_frequency_intervals` |
| **A17** | Internal and ACH schedules execute when due, advancing interval | `test_recurring.py::test_recurring_due_execution` |
| **A18** | Paused schedules skip; resume enables; cancelled is terminal | `test_recurring.py::test_recurring_pause_resume_cancel` |
| **A19** | Insufficient funds/limits logs failure & advances without debit | `test_recurring.py::test_recurring_insufficient_funds_advances` |
| **A20** | All inherited E1 tests (12 backend, 5 frontend) + build pass | `pytest backend/tests/` && `npm test` && `npm run build` |
| **A21** | Manual browser visual verification of UI criteria | Manual inspection checklist in `quickstart.md` |

---

## Architectural Trade-offs & Risk Analysis

1. **In-Process Background Worker vs External Queue**:
   - *Trade-off*: An in-process `asyncio` loop shares process memory and CPU with the FastAPI application rather than running in a separate worker cluster.
   - *Rationale*: Appropriate and optimal for single-node / stage-proportional banking prototype. Eliminates infrastructure complexity while fully satisfying the autonomous execution mandate (D-04). Protected by `uvicorn --workers 1` and SQLite `BEGIN IMMEDIATE` transactions (F-07).
2. **Dynamic Limit Calculation on Demand vs Counter Table**:
   - *Trade-off*: Calculating daily consumption via an aggregated SQL query on transfer records requires indexing `created_at` and `status`, rather than reading a single cached accumulator column.
   - *Rationale*: Eliminates synchronization bugs, concurrency race conditions, and drift during refunds (D-06, D-07) across half-open UTC day windows (F-04).
3. **Immutable Recipient Snapshots vs Relational Normalization**:
   - *Trade-off*: Storing recipient name, bank, routing, and account numbers on both `transfers` and `recurring_schedules` denormalizes data relative to `beneficiaries`.
   - *Rationale*: Enforces financial auditing standards where past transactions and existing scheduled commitments must never change or break when a customer deletes a saved contact (REC-11, D-08).
4. **Deterministic Test Endpoints & Environment Gating (F-03, F-05)**:
   - *Trade-off*: Providing test-only endpoints (`/api/test/...`) introduces testing hooks into the router.
   - *Rationale*: Test endpoints are mounted conditionally under an environment gate (`ENABLE_TEST_ENDPOINTS=true`). In normal application environments, these endpoints are strictly disabled and return HTTP 404, preventing unauthorized administrative triggers while enabling 100% deterministic, hermetic automated test execution without brittle clock manipulation (D-04, D-06).

---

## Complexity Tracking

| Category | Solution Chosen | Simpler Alternative Rejected Because |
|---|---|---|
| Background Worker | In-process `asyncio` task in lifespan (`--workers 1`) | Manual button execution rejected by researcher (D-04); external queue (Celery) rejected as excessive gold-plating. |
| DB Migrations | Safe SQLite table rebuild (`transfers_v2`) | Basic `ALTER TABLE` leaves `destination_account_id` NOT NULL, crashing ACH transfers (F-01); Alembic requires ORM (prohibited). |
| Recipient Snapshot | Flat columns on transfers/schedules | Relational foreign key with cascade breaks on beneficiary deletion (violates REC-11, D-08). |
