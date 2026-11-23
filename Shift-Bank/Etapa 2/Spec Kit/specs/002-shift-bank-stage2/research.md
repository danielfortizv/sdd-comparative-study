# Research Log: Shift Bank Stage 2 — Functional Complexity and State (Remediated)

This document consolidates the key technical research findings, architecture choices, rationales, and evaluated alternatives for Shift Bank Stage 2 (Option A: Functional Complexity and State), adhering strictly to the approved specification (`specs/002-shift-bank-stage2/spec.md`), the inherited constitution (`.specify/memory/constitution.md` v1.2.0), researcher decisions D-01 through D-09, and the formal audit remediations F-01 through F-10.

---

### Decision 1: Background Autonomous Execution & Worker Engine (Remediating F-03, F-07)
- **Chosen**: In-process `asyncio` background worker task managed via FastAPI's native lifespan context (`@asynccontextmanager`) within a single-process deployment (`uvicorn --workers 1`), backed by SQLite `BEGIN IMMEDIATE` database transactions for cross-worker safety, an in-process `asyncio.Lock` for request/scheduler serialization, an explicit 10-second settlement eligibility delay for ACH transfers, and an explicit test-environment registration gate.
- **Rationale**:
  - The contract strictly mandates autonomous execution while the application is running (REC-05, D-04, ACH-06) and explicitly rejects manual-only execution.
  - **Settlement Timing & Test Determinism (F-03)**: If the background worker settles pending ACH transfers immediately on every tick, automated test suites asserting failure refunds (`POST /api/test/ach/{transfer_id}/fail`, scenario A08) will race against the worker and encounter unexpected `409 Conflict` errors. Imposing an explicit settlement eligibility delay (transfers must remain in `PENDING` status for >= 10 seconds before autonomous settlement) allows test suites to deterministically simulate failures immediately upon transfer creation without racing against the background timer.
  - **Process-Level Concurrency & Single-Worker Mandate (F-07)**: An `asyncio.Lock` provides synchronization only within a single Python event loop. It does NOT provide cross-process locking. If Uvicorn runs multiple worker processes (`--workers > 1`), each process would spawn its own background worker, risking split-brain scheduling and duplicate debits. The application runtime must mandate single-process execution (`--workers 1`), and all database state modifications must execute under SQLite's native transaction locking (`BEGIN IMMEDIATE`).
  - **Test Endpoint Security & Isolation Gate**: Test-only administrative endpoints (`/api/test/...`) are mounted only when an explicit environment gate is enabled (e.g. `ENABLE_TEST_ENDPOINTS=true` or during test sessions). For unit and integration tests, internal test-callable service functions (`services.simulate_ach_failure(...)`, `scheduler.run_due_recurring_schedules(...)`) are directly imported, keeping testing hermetic without exposing public administrative routes in production.
- **Alternatives Considered**:
  - *Celery with Redis/RabbitMQ*: Rejected as severe architectural gold-plating violating Constitution Principle III (Proportional Implementation).
  - *0-second immediate auto-settlement*: Rejected due to confirmed race conditions against failure assertion tests (F-03).

---

### Decision 2: Schema Evolution & Brownfield SQLite Table-Rebuild Migration (Remediating F-01)
- **Chosen**: Safe, idempotent SQLite table-rebuild migration in `backend/src/database.py` that inspects `transfers.destination_account_id` via `PRAGMA table_info(transfers)`. If the column is `NOT NULL` (as inherited from Stage 1), a table rebuild is executed:
  1. Temporarily disable foreign keys: `PRAGMA foreign_keys = OFF;`
  2. Create a temporary table `transfers_v2` with `destination_account_id TEXT NULL`, all existing Stage 1 columns, and new Stage 2 columns (`transfer_type`, `recipient_name`, `bank_name`, `routing_number`, `account_number`, `settled_at`, `failed_at`, `refunded_at`).
  3. Copy existing records: `INSERT INTO transfers_v2 (id, source_account_id, destination_account_id, amount, status, created_at, expires_at) SELECT id, source_account_id, destination_account_id, amount, status, created_at, expires_at FROM transfers;`
  4. Drop the old table: `DROP TABLE transfers;`
  5. Rename table: `ALTER TABLE transfers_v2 RENAME TO transfers;`
  6. Re-enable foreign keys: `PRAGMA foreign_keys = ON;`
  7. Create new Stage 2 tables (`beneficiaries`, `limits`, `recurring_schedules`) using `CREATE TABLE IF NOT EXISTS`.
- **Rationale**:
  - In the actual Stage 1 SQLite database (`backend/src/database.py`), `destination_account_id` was declared `TEXT NOT NULL` with `FOREIGN KEY (destination_account_id) REFERENCES accounts(id)`.
  - For external ACH transfers, destination accounts belong to external banks and have no entry in `accounts`. Attempting to insert an ACH transfer with `destination_account_id = NULL` crashes with a SQLite `IntegrityError: NOT NULL constraint failed`.
  - Standard SQLite does not support `ALTER TABLE ALTER COLUMN DROP NOT NULL`. A table rebuild is SQLite's official, recommended migration procedure.
  - The migration is idempotent: if `destination_account_id` is already nullable, the rebuild is bypassed.
  - Historical Stage 1 database is never accessed, imported, or modified (D-02).
- **Alternatives Considered**:
  - *Basic ALTER TABLE ADD COLUMN*: Rejected because it leaves `destination_account_id` with its existing `NOT NULL` and foreign key constraint, breaking ACH transfers (F-01).
  - *Alembic*: Rejected because it requires SQLAlchemy ORM, which is explicitly prohibited by the project baseline.

---

### Decision 3: Dynamic Limits Engine & Half-Open UTC Consumption Windowing (Remediating F-04, F-09)
- **Chosen**: Dynamic limits consumption calculation using a mathematically sound half-open UTC interval `[start_of_day, next_day_start)`:
  ```sql
  SELECT amount FROM transfers 
  WHERE source_account_id = ? 
    AND created_at >= ? AND created_at < ? 
    AND status IN ('COMPLETED', 'PENDING', 'SETTLED');
  ```
  where `start_of_day = YYYY-MM-DDT00:00:00Z` and `next_day_start = NEXT_DAY_YYYY-MM-DDT00:00:00Z`.
- **Rationale**:
  - **Timestamp Normalization & Fractional Seconds (F-04)**: The previous plan's inclusive upper bound `created_at <= 'YYYY-MM-DDT23:59:59Z'` failed to reliably include timestamps containing fractional seconds (e.g. `23:59:59.500000Z`) or offset representations (`+00:00`). Using a normalized half-open interval `[start_of_day, next_day_start)` or date prefix matching guarantees that 100% of movements occurring within that UTC day are captured accurately.
  - **Order of Validation (F-09)**: In `POST /api/transfers`, dynamic limits (both per-transfer limit and remaining daily availability) MUST be evaluated before the sensitive transfer check (amount >= COP 1,000,000.00). If a transfer exceeds either limit, it is rejected immediately with HTTP 400, preventing invalid requests from presenting an MFA prompt or bypassing limits with a valid PIN (LIM-07, A14).
  - **Non-Negative Availability & Immediate Clamping (D-07)**: Calculated as $\max(\text{Decimal("0.00")}, \text{daily\_limit} - \text{consumption})$. Reducing the daily limit below current consumption immediately clamps availability to COP 0.00 without modifying past records.
- **Alternatives Considered**:
  - *Inclusive 23:59:59Z upper bound*: Rejected due to boundary bugs with microsecond timestamps (F-04).

---

### Decision 4: Atomic Transactions, Conditional Status Transitions, & Refund Safety (Remediating F-05)
- **Chosen**: Strict conditional SQL updates under `BEGIN IMMEDIATE` transactions. A refund is credited to the source account ONLY if the transition from `PENDING` to `FAILED` succeeds atomically in SQL:
  ```sql
  UPDATE transfers 
  SET status = 'FAILED', failed_at = ?, refunded_at = ? 
  WHERE id = ? AND status = 'PENDING';
  ```
  The refund balance increment (`UPDATE accounts SET balance = balance + amount WHERE id = source_id`) is executed ONLY IF `cursor.rowcount == 1`.
- **Rationale**:
  - Guarantees exactly-once refunds (ACH-07, ACH-08, A08).
  - If concurrent or duplicate calls attempt to fail the same transfer, only the first call updates a row (`rowcount == 1`) and issues the refund. Subsequent calls update 0 rows (`rowcount == 0`), preventing duplicate refunds.
  - `SETTLED` and `FAILED` are mutually exclusive terminal states. Once settled, `status = 'PENDING'` will not match, preventing refunds on settled transfers.
- **Alternatives Considered**:
  - *Unconditional status update*: Rejected because it permits duplicate refunds under concurrent or repeated requests (F-05).

---

### Decision 5: Recurring Schedule Lifecycle, Timing, & MFA Expiration Sweep (Remediating F-08)
- **Chosen**: Comprehensive lifecycle management for recurring schedules with on-demand and background expiration sweeps:
  1. Statuses: `PENDING_MFA`, `ACTIVE`, `PAUSED`, `CANCELLED`, `EXPIRED`.
  2. Background worker and schedule listing endpoints (`GET /api/recurring-schedules`) automatically transition any schedule with `status = 'PENDING_MFA'` and `mfa_expires_at < now_utc` to `EXPIRED` (F-08).
  3. Start dates (`YYYY-MM-DD`) must represent a strictly future execution instant relative to `now_utc` and become due at `00:00:00 UTC` on that date (D-09).
  4. Advance logic: Successful execution advances `next_due_date = previous_due_date + interval`. Failed execution (insufficient funds/limits per REC-10) records the failure and advances `next_due_date` by interval without debiting.
  5. Immutability: Schedules store flat snapshot recipient columns, ensuring beneficiary deletion never impacts active schedules (REC-11, D-08).
- **Alternatives Considered**:
  - *Client-only timer expiration*: Rejected because server-side state must be authoritative and persistent.

---

### Decision 6: Account History Visibility & Multi-State Support (Remediating F-02)
- **Chosen**: Modernized account history query in `backend/src/api.py` utilizing `LEFT JOIN`:
  ```sql
  SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.status, t.created_at,
         sa.name, da.name, t.transfer_type, t.recipient_name, t.bank_name
  FROM transfers t
  JOIN accounts sa ON t.source_account_id = sa.id
  LEFT JOIN accounts da ON t.destination_account_id = da.id
  WHERE (t.source_account_id = ? OR t.destination_account_id = ?)
    AND t.status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')
  ORDER BY t.created_at DESC;
  ```
- **Rationale**:
  - The inherited Stage 1 query used an `INNER JOIN accounts da ON t.destination_account_id = da.id WHERE t.status = 'COMPLETED'`.
  - For external ACH transfers, `destination_account_id` is NULL, so an `INNER JOIN` completely omitted ACH movements from history, directly violating ACH-05 and A07.
  - A `LEFT JOIN` allows ACH transfers to be included.
  - Description formatting:
    - Internal transfers: `Transfer from {src_name} to {dest_name}` (100% backwards-compatible).
    - ACH transfers: `ACH Transfer to {recipient_name} ({bank_name}) - {status}`.
    - Direction: For ACH transfers, direction is `outgoing` from the source account perspective.
- **Alternatives Considered**:
  - *Separate endpoint for ACH history*: Rejected because customers expect a unified transaction history per account (HER-01).

---

### Decision 7: Test Database Isolation & Parallel Test Module Architecture (Remediating F-06, F-10)
- **Chosen**: Dedicated test database isolation via `TEST_DB_PATH` (or pytest fixtures using isolated temporary files), plus partitioning Stage 2 backend tests into distinct functional modules:
  - `backend/tests/test_limits.py` (US1 Dynamic Limits)
  - `backend/tests/test_ach.py` (US2 ACH & Beneficiaries)
  - `backend/tests/test_recurring.py` (US3 Recurring Payments)
  - `backend/tests/test_stage2_regression.py` (US4 Inherited & Regression Tests)
- **Rationale**:
  - **File Collision Prevention (F-06)**: Partitioning tests into dedicated files enables genuine task parallelism without multiple tasks attempting to modify `backend/tests/test_stage2.py` simultaneously.
  - **Database Isolation (F-10)**: Prevents test runs from corrupting `backend/shift_bank.db` or interfering with inherited Stage 1 test fixtures (`test_api.py`), strictly upholding decision D-02.
