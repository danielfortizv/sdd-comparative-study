# Data Model: Shift Bank Stage 2 — Functional Complexity and State (Remediated)

This document defines the SQLite database schema, entity structures, validation constraints, and state transition lifecycles for Shift Bank Stage 2, preserving brownfield continuity with Stage 1 and implementing approved decisions D-01 through D-09 alongside formal remediations F-01 through F-10.

---

## 1. Database Schema & Migration Strategy (SQLite)

### 1.1. Inherited Stage 1 Schema Baseline (Actual Code in `backend/src/database.py`)
In the actual inherited Stage 1 application, the `accounts` and `transfers` tables were created as follows:

```sql
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    balance TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'COP'
);

CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT NOT NULL,  -- NOTE: NOT NULL in Stage 1 baseline!
    amount TEXT NOT NULL,
    status TEXT NOT NULL,                  -- 'COMPLETED', 'PENDING_MFA', 'FAILED', 'EXPIRED'
    created_at TEXT NOT NULL,
    expires_at TEXT,
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
);
```

---

### 1.2. Safe, Idempotent Table-Rebuild Migration for `transfers` (Remediating F-01)
In Stage 2, external third-party ACH transfers have no internal destination account; `destination_account_id` must be `NULL` (and the foreign key to `accounts(id)` must only apply when non-null). Because SQLite does not support `ALTER TABLE ALTER COLUMN DROP NOT NULL`, `backend/src/database.py` executes an idempotent table rebuild if `destination_account_id` has `notnull == 1` in `PRAGMA table_info(transfers)`:

```sql
-- 1. Disable foreign keys temporarily for the migration transaction
PRAGMA foreign_keys = OFF;

-- 2. Create the evolved transfers table with nullable destination_account_id
CREATE TABLE IF NOT EXISTS transfers_v2 (
    id TEXT PRIMARY KEY,
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT,             -- NULL for external ACH transfers
    amount TEXT NOT NULL,                    -- Decimal string COP (e.g., '1500000.00')
    status TEXT NOT NULL,                    -- 'COMPLETED', 'PENDING_MFA', 'PENDING', 'SETTLED', 'FAILED', 'EXPIRED'
    created_at TEXT NOT NULL,                -- ISO-8601 UTC timestamp
    expires_at TEXT,                         -- ISO-8601 UTC timestamp (nullable)
    transfer_type TEXT NOT NULL DEFAULT 'INTERNAL', -- 'INTERNAL' or 'ACH'
    recipient_name TEXT,                     -- Immutable snapshot for ACH (D-08)
    bank_name TEXT,                          -- Immutable snapshot for ACH (D-08)
    routing_number TEXT,                     -- Exactly 9 numeric digits snapshot (D-08)
    account_number TEXT,                     -- 4 to 17 numeric digits snapshot (D-08)
    settled_at TEXT,                         -- ISO-8601 UTC timestamp (nullable)
    failed_at TEXT,                          -- ISO-8601 UTC timestamp (nullable)
    refunded_at TEXT,                        -- ISO-8601 UTC timestamp (nullable)
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
);

-- 3. Copy existing records preserving IDs, amounts, and timestamps
INSERT INTO transfers_v2 (
    id, source_account_id, destination_account_id, amount, status, created_at, expires_at
)
SELECT id, source_account_id, destination_account_id, amount, status, created_at, expires_at
FROM transfers;

-- 4. Swap the tables
DROP TABLE transfers;
ALTER TABLE transfers_v2 RENAME TO transfers;

-- 5. Re-enable foreign keys
PRAGMA foreign_keys = ON;
```

---

### 1.3. New Table: `beneficiaries` (Stage 2, Decision D-08)
Stores saved external third-party ACH recipients. Banking details are immutable after creation.

```sql
CREATE TABLE IF NOT EXISTS beneficiaries (
    id TEXT PRIMARY KEY,                     -- e.g., 'ben_uuid'
    user_id TEXT NOT NULL DEFAULT 'user_mock_001', -- Scoped to customer boundary (ACH-02)
    name TEXT NOT NULL,                      -- Beneficiary full name
    bank_name TEXT NOT NULL,                 -- Destination bank name
    routing_number TEXT NOT NULL,            -- Exactly 9 numeric digits (ACH-03, A05)
    account_number TEXT NOT NULL,            -- 4 to 17 numeric digits (ACH-03, A06)
    created_at TEXT NOT NULL                 -- ISO-8601 UTC timestamp
);
```

---

### 1.4. New Table: `limits` (Stage 2, Decisions D-01, D-07)
Stores user-configurable dynamic limits in Colombian Pesos (COP).

```sql
CREATE TABLE IF NOT EXISTS limits (
    id TEXT PRIMARY KEY,                     -- e.g., 'lim_default'
    user_id TEXT NOT NULL UNIQUE DEFAULT 'user_mock_001',
    per_transfer_limit TEXT NOT NULL DEFAULT '5000000.00', -- Decimal string COP (LIM-01, D-01)
    daily_limit TEXT NOT NULL DEFAULT '10000000.00',        -- Decimal string COP (LIM-01, D-01)
    updated_at TEXT NOT NULL                 -- ISO-8601 UTC timestamp
);
```

---

### 1.5. New Table: `recurring_schedules` (Stage 2, Decisions D-03, D-05, D-08, D-09)
Stores automated recurring payment instructions for internal and ACH transfers. Captures flat, immutable recipient snapshots for ACH (D-08).

```sql
CREATE TABLE IF NOT EXISTS recurring_schedules (
    id TEXT PRIMARY KEY,                     -- e.g., 'rec_uuid'
    user_id TEXT NOT NULL DEFAULT 'user_mock_001',
    transfer_type TEXT NOT NULL,             -- 'INTERNAL' or 'ACH'
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT,             -- For INTERNAL schedules (nullable for ACH)
    recipient_name TEXT,                     -- Immutable snapshot for ACH (D-08)
    bank_name TEXT,                          -- Immutable snapshot for ACH (D-08)
    routing_number TEXT,                     -- Exactly 9 numeric digits snapshot (D-08)
    account_number TEXT,                     -- 4 to 17 numeric digits snapshot (D-08)
    amount TEXT NOT NULL,                    -- Decimal string COP
    frequency TEXT NOT NULL,                 -- 'DAILY', 'WEEKLY', 'MONTHLY' (REC-02, D-09)
    status TEXT NOT NULL,                    -- 'PENDING_MFA', 'ACTIVE', 'PAUSED', 'CANCELLED', 'EXPIRED' (D-05)
    next_due_date TEXT NOT NULL,             -- ISO-8601 UTC timestamp
    last_executed_at TEXT,                   -- ISO-8601 UTC timestamp (nullable)
    mfa_expires_at TEXT,                     -- ISO-8601 UTC timestamp (nullable, for PENDING_MFA)
    created_at TEXT NOT NULL,                -- ISO-8601 UTC timestamp
    FOREIGN KEY (source_account_id) REFERENCES accounts(id)
);
```

---

## 2. State Machine Transitions & Atomicity Rules

### 2.1. Direct Transfer State Machine (Internal & ACH)
- **Validation Precedence (Remediating F-09)**: In `POST /api/transfers` and `POST /api/transfers/ach`, dynamic limit checks (per-transfer limit and remaining daily availability) MUST be evaluated BEFORE checking the sensitive threshold (amount >= COP 1M). Exceeded limits return HTTP 400 immediately; a valid MFA PIN cannot bypass limits (LIM-07, A14).
- **Internal Transfers**:
  - Amount < COP 1M: Immediately debits source, credits destination, inserts record with status `COMPLETED` under `BEGIN IMMEDIATE`.
  - Amount >= COP 1M: Inserts record with status `PENDING_MFA` and `expires_at = now + 300s` under `BEGIN IMMEDIATE` without modifying balances.
- **ACH Transfers**:
  - Amount < COP 1M: Debits source account immediately, inserts record with status `PENDING` under `BEGIN IMMEDIATE`.
  - Amount >= COP 1M: Inserts record with status `PENDING_MFA` and `expires_at = now + 300s`. Debits source balance once confirmed.

---

### 2.2. ACH Settlement & Atomic Single Refund (Remediating F-03, F-05)
- **Autonomous Settlement (F-03)**:
  - Background worker checks for transfers where `transfer_type = 'ACH'`, `status = 'PENDING'`, and `created_at <= now_utc - 10 seconds` (10-second settlement eligibility delay).
  - Transitions `PENDING` -> `SETTLED`, sets `settled_at = now_utc`. No additional debits.
- **Deterministic Test-Only Failure & Single Refund (F-05)**:
  - Transition from `PENDING` to `FAILED` is strictly conditional under `BEGIN IMMEDIATE`:
    ```sql
    UPDATE transfers 
    SET status = 'FAILED', failed_at = :now, refunded_at = :now 
    WHERE id = :transfer_id AND status = 'PENDING';
    ```
  - The refund balance increment (`UPDATE accounts SET balance = balance + amount WHERE id = source_id`) is executed **ONLY IF** `cursor.rowcount == 1`.
  - If `cursor.rowcount == 0` (transfer was already `SETTLED` or `FAILED`), the refund is skipped and HTTP 409 Conflict is returned, guaranteeing zero double refunds.

---

### 2.3. Recurring Schedule Lifecycle & Expiration Sweep (Remediating F-08, D-05, D-09)
- **State Lifecycle**:
  - Amount < COP 1M: Created in `ACTIVE` status.
  - Amount >= COP 1M: Created in `PENDING_MFA` status with `mfa_expires_at = now + 300s`. Closing modal leaves it `PENDING_MFA`, resumable via UI (D-05).
  - Expiration Sweep (F-08): Both the background scheduler and schedule listing endpoint (`GET /api/recurring-schedules`) automatically transition schedules where `status = 'PENDING_MFA'` and `mfa_expires_at < now_utc` to `EXPIRED`.
- **Timing & Intervals (D-09)**:
  - Explicit start date: `YYYY-MM-DD` validated as strictly future; becomes due at `00:00:00 UTC` on that date.
  - Default start date: `created_at + interval` (Daily = 24h, Weekly = 7d, Monthly = strictly 30d).
  - Advance on execution: Advances `next_due_date = previous_due_date + interval`. On funding/limit failure, logs failure and advances without debiting (REC-10).

---

### 2.4. Unified Account Movement History Query Model (Remediating F-02)
To provide unified history visibility across internal and external ACH transfers (ACH-05, HER-01, A07):
- **Query Structure**: The query uses a `LEFT JOIN` on `accounts` because external ACH transfers have `destination_account_id = NULL`:
  ```sql
  SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.status, t.created_at,
         sa.name AS source_account_name, da.name AS destination_account_name,
         t.transfer_type, t.recipient_name, t.bank_name
  FROM transfers t
  JOIN accounts sa ON t.source_account_id = sa.id
  LEFT JOIN accounts da ON t.destination_account_id = da.id
  WHERE (t.source_account_id = ? OR t.destination_account_id = ?)
    AND t.status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')
  ORDER BY t.created_at DESC;
  ```
- **Formatting Rules**:
  - Internal transfers: `Transfer from {source_account_name} to {destination_account_name}`
  - ACH transfers: `ACH Transfer to {recipient_name} ({bank_name}) - {status}`
  - Direction: For ACH transfers, direction is always `outgoing` from the source account perspective.
  - Omitted: Transfers in `PENDING_MFA` or `EXPIRED` status are excluded from account movement history.

---

## 3. Financial Precision & Daily Limit Invariants (Remediating F-04, F-07)

1. **Precision Math**: All monetary values are stored as decimal strings and computed using Python `decimal.Decimal` (2 decimal places). Direct SQL arithmetic or `REAL` types are strictly prohibited.
2. **Half-Open UTC Consumption Interval (F-04)**:
   Daily consumption aggregates outgoing movements within the strict half-open window `[start_of_day, next_day_start)`:
   ```sql
   SELECT amount FROM transfers 
   WHERE source_account_id = ? 
     AND created_at >= ? AND created_at < ? 
     AND status IN ('COMPLETED', 'PENDING', 'SETTLED');
   ```
   where `start_of_day = YYYY-MM-DDT00:00:00Z` and `next_day_start = NEXT_DAY_YYYY-MM-DDT00:00:00Z`.
   This captures all timestamps on that UTC calendar day (including `.500000Z` fractional seconds) and strictly excludes `FAILED` and `EXPIRED` transfers.
3. **Non-Negative Availability (D-07)**:
   $$\text{Remaining Availability} = \max\left(\text{Decimal}("0.00"), \text{daily\_limit} - \text{consumption}\right)$$
   If daily limit is reduced below consumption, availability clamps immediately to COP 0.00 without modifying past records.
4. **Single-Process Constraint & Concurrency Locking (F-07)**:
   The backend runs as a single Uvicorn worker process (`--workers 1`). All balance updates and state machine claims execute under `BEGIN IMMEDIATE` transaction locks to guarantee cross-thread and cross-job safety.
