# Quickstart & Verification Guide: Shift Bank Stage 2

This guide outlines the concrete, runnable verification steps to validate Shift Bank Stage 2 features against acceptance scenarios **A01 through A21**, all inherited Stage 1 tests, and the common functional contract.

---

## 1. Prerequisites & Environment Setup

- **Python Runtime**: Python 3.13+ with active dependencies (`fastapi`, `uvicorn`, `pydantic`, `pytest`, `httpx`).
- **Node.js Runtime**: Node 20+ with npm dependencies installed under `frontend/`.
- **Single-Process Mandate (F-07)**: Backend application runs strictly as a single worker process (`uvicorn backend.src.main:app --workers 1`) to guarantee single-instance background scheduler execution and cross-request serialization via SQLite `BEGIN IMMEDIATE` transaction locking.
- **Database Safety & Isolation (D-02, F-10)**: Automated test suites execute against isolated, code-seeded SQLite test databases (via `TEST_DB_PATH` or temporary test fixtures). The primary development database (`backend/shift_bank.db`) and historical Stage 1 databases are never modified or imported.
- **Test Endpoints Gate**: Test-only simulation endpoints (`/api/test/*`) are disabled in normal environments (returning 404). For test runs, set `ENABLE_TEST_ENDPOINTS=true`.

---

## 2. Automated Test Suite Execution

### 2.1. Backend Tests (Inherited & Partitioned Stage 2 Test Suite) (F-06, F-10)
Execute all backend tests via `pytest`:
```powershell
pytest backend/tests/ -v
```
To run specific functional test modules partitioned to prevent file collision:
```powershell
pytest backend/tests/test_api.py -v                # Inherited Stage 1 baseline (12 tests)
pytest backend/tests/test_limits.py -v             # US1 Dynamic Limits (A10, A11, A12, A14)
pytest backend/tests/test_ach.py -v                # US2 ACH & Beneficiaries (A03–A09)
pytest backend/tests/test_recurring.py -v          # US3 Recurring Payments (A15–A19)
pytest backend/tests/test_stage2_regression.py -v   # US4 Regression & Multi-State History (A01, A02, A13, A20)
```
**Expected Outcome**: All inherited Stage 1 tests (12 tests) and new Stage 2 test suites pass with 0 failures against isolated test databases.

### 2.2. Frontend Component Tests & Build
Execute frontend tests via `vitest` and verify build compilation:
```powershell
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
**Expected Outcome**: All inherited frontend tests (5 tests) and new Stage 2 component tests pass; Vite production build succeeds with 0 TypeScript/compilation errors.

---

## 3. Scenario-by-Scenario Verification Mapping (A01 – A21)

### Section 1: Inherited Invariants & Core Accounts
- **A01 (Inherited Accounts & Balances)**:
  - Run `GET /api/accounts` -> Verifies Checking (COP 5,000,000.00) and Savings (COP 15,000,000.00) (HER-01, D-02).
- **A02 (Internal Own-Account Transfer & History)**:
  - Submit transfer from Checking to Savings under COP 1M -> Verifies immediate atomic balance update and unified history entry via `GET /api/accounts/{id}/history` (HER-02, F-02).
- **A13 (Inherited Sensitive MFA Threshold & Window)**:
  - Submit internal transfer of COP 1,500,000.00 -> Verifies `PENDING_MFA` response, 300s expiration timer, invalid PIN retry, and completion upon entering code `123456` (HER-03).
- **A20 (Automated Test Execution)**:
  - Run `pytest` and `npm test` -> Verifies full automated regression suite passes.

### Section 2: Beneficiary Management & ACH Transfers
- **A03 (Saved Beneficiary Creation & Listing)**:
  - Create beneficiary with name, bank, 9-digit routing, 4–17 digit account number -> Verifies persistence and retrieval via `GET /api/beneficiaries` (ACH-01, ACH-02).
- **A04 (Ad Hoc ACH Transfer & Optional Save)**:
  - Initiate ACH transfer providing ad hoc recipient details with `save_beneficiary: true` -> Verifies transfer accepted as `PENDING` and beneficiary saved (ACH-01, ACH-04).
- **A05 (Routing Number Validation)**:
  - Enter 8-digit or non-numeric routing in UI -> Verifies immediate input error and disabled submit button; submit 9 numeric digits -> Verifies acceptance (ACH-10, A05).
- **A06 (Account Number Length Validation)**:
  - Submit account numbers with 3 digits or 18 digits -> Verifies 400 Bad Request error; submit 4 to 17 digits -> Verifies acceptance (ACH-03).
- **A07 (ACH Immediate Debit, History Visibility & Autonomous Settlement)**:
  - Submit valid ACH transfer -> Verifies source balance debited immediately and status is `PENDING`. Verifies movement is immediately visible in `GET /api/accounts/{id}/history` via `LEFT JOIN` (F-02). After 10-second settlement eligibility delay (F-03), background settlement sweeps transfer to `SETTLED` with timestamp and no second debit (ACH-05, ACH-06, D-06).
- **A08 (Failed ACH Atomic Refund & Idempotency)**:
  - For a `PENDING` ACH transfer (invoked before 10s auto-settlement, F-03), trigger test failure (`POST /api/test/ach/{id}/fail`) -> Verifies status transitions conditionally to `FAILED`, exact amount refunded to source account once (`cursor.rowcount == 1`), and refunded amount excluded from daily limit consumption. Retrying failure trigger returns `409 Conflict` without duplicate refund (ACH-07, ACH-08, D-06, F-05).
- **A09 (Monetary Precision & Non-Positive Rejection)**:
  - Submit COP 0, negative amount, or amount with 3 decimal places -> Verifies immediate 400 rejection (ACH-04, LIM-09).

### Section 3: Dynamic Limits
- **A10 (View & Update Dynamic Limits)**:
  - Query `GET /api/limits` -> Verifies default COP 5M per-transfer and COP 10M daily. Update limits via `PUT /api/limits` -> Verifies new limits apply immediately to subsequent operations (LIM-01, LIM-02, D-01).
- **A11 (Per-Transfer Limit Enforcement & Exact Boundary)**:
  - Set per-transfer limit to COP 2,000,000.00. Attempt transfer of COP 2,000,001.00 -> Verifies immediate rejection before MFA (F-09). Attempt transfer of exactly COP 2,000,000.00 -> Verifies acceptance (LIM-03, LIM-05).
- **A12 (Daily Limit Accumulation Test & Half-Open Window)**:
  - Set daily limit to COP 1,000.00. Execute transfers of 400.00, 300.00, and 300.00 -> All three succeed (total 1,000.00). Attempt transfer of 10.00 -> Verifies rejection for exceeding daily limit. Aggregation verifies movements within half-open interval `[00:00:00Z, next_day 00:00:00Z)` including fractional seconds (LIM-04, F-04).
- **A14 (Limits Evaluated Before MFA)**:
  - Set daily limit to COP 1,000,000.00 and submit sensitive transfer of COP 1,500,000.00 -> Verifies limit validation fails immediately with 400 prior to presenting MFA prompt (LIM-07, F-09).

### Section 4: Recurring Payments
- **A15 (Default First Execution Interval)**:
  - Create daily recurring schedule without start date -> Verifies first due date is scheduled exactly +24 hours from creation, never executing immediately (REC-04, D-09).
- **A16 (Weekly & Monthly Frequency Intervals)**:
  - Create weekly schedule -> Verifies next due date is +7 days. Create monthly schedule -> Verifies next due date is strictly +30 days (not calendar month) (REC-02, D-09).
- **A17 (Due Schedule Automatic Execution)**:
  - Create active internal and ACH schedules due now. Run scheduler evaluation -> Verifies funds are debited, movements logged in history, and `next_due_date` advances by interval (REC-05, D-04, D-09).
- **A18 (Pause, Resume, Terminal Cancel & Expiration Sweep)**:
  - Pause active schedule -> Verifies status is `PAUSED` and scheduler skips it. Resume schedule -> Verifies status returns to `ACTIVE`. Cancel schedule -> Verifies status becomes `CANCELLED` and subsequent pause/resume attempts are rejected (REC-06, REC-07, REC-08). Any `PENDING_MFA` schedule exceeding 300s window automatically sweeps to `EXPIRED` upon listing or scheduler tick (F-08).
- **A19 (Insufficient Funds/Limit Advance on Execution)**:
  - Active due schedule exceeds account balance or dynamic limit -> Verifies execution logs failure, leaves balance undebited, and advances `next_due_date` by interval to prevent getting stuck (REC-10).

### Section 5: UI & Visual Inspection
- **A21 (Manual Browser Inspection)**:
  - Open `http://localhost:5173` in a browser.
  - Verify tabbed navigation between Own Transfers, ACH Transfers, Beneficiaries, Recurring Payments, and Limits.
  - Verify real-time routing input feedback (red/disabled on <9 digits, green on 9 digits).
  - Verify clear separation of Configured Daily Limit, Today's Consumption, and Remaining Availability (D-07).
  - Verify MFA modal triggers on sensitive transfers (>= COP 1M) and schedule creations (D-03, D-05), with visible timer and cancel/resume capability.
