# API Contract: Shift Bank Stage 2 — Functional Complexity and State

This document defines the REST API endpoints, request/response JSON schemas, HTTP status codes, and error payloads for Shift Bank Stage 2. All amounts are decimal strings denominated in Colombian Pesos (`COP`).

---

## 1. Inherited Endpoints (Preserved for Backwards Compatibility)

### `GET /api/accounts`
Returns all customer accounts with formatted balances.

- **Response `200 OK`**:
  ```json
  [
    {
      "id": "acc_checking_123",
      "name": "Checking",
      "balance": "5000000.00",
      "currency": "COP"
    },
    {
      "id": "acc_savings_456",
      "name": "Savings",
      "balance": "15000000.00",
      "currency": "COP"
    }
  ]
  ```

---

### `GET /api/accounts/{account_id}/history`
Returns chronological movement history (newest first) for the specified account, supporting both internal and external ACH transfers across multiple lifecycle states (Remediating F-02).

- **Query Invariants (F-02)**:
  - Uses `LEFT JOIN accounts da ON t.destination_account_id = da.id` because external ACH transfers have `destination_account_id = NULL`.
  - Filters `status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')`. (Transfers in `PENDING_MFA` or `EXPIRED` status are excluded).
  - Descriptions:
    - Internal transfers: `Transfer to {destination_account}` (outgoing) or `Transfer from {source_account}` (incoming).
    - ACH transfers: `ACH Transfer to {recipient_name} ({bank_name}) - {status}` with direction `outgoing`.
- **Response `200 OK`**:
  ```json
  [
    {
      "id": "tr_ach_001",
      "direction": "outgoing",
      "amount": "250000.00",
      "description": "ACH Transfer to Empresa de Energia (Banco Davivienda) - SETTLED",
      "date": "2026-11-14T12:40:00Z"
    },
    {
      "id": "tr_123",
      "direction": "outgoing",
      "amount": "100000.00",
      "description": "Transfer to Savings",
      "date": "2026-11-14T10:00:00Z"
    }
  ]
  ```

---

### `POST /api/transfers`
Initiates an internal transfer between the customer's own accounts.

- **Validation Precedence (Remediating F-09)**: Dynamic limits (per-transfer limit and remaining daily availability) MUST be evaluated BEFORE checking the sensitive threshold (amount >= COP 1,000,000.00). If a transfer exceeds either limit, the API immediately returns `400 Bad Request`. An MFA challenge (`202 Accepted`) is ONLY returned if the transfer is within all limits. A valid MFA PIN cannot bypass limits (LIM-07, A14).
- **Request Payload**:
  ```json
  {
    "source_account_id": "acc_checking_123",
    "destination_account_id": "acc_savings_456",
    "amount": "500000.00"
  }
  ```
- **Response `201 Created`** (Amount < COP 1,000,000.00):
  ```json
  {
    "id": "tr_abc123",
    "source_account": "Checking",
    "destination_account": "Savings",
    "amount": "500000.00",
    "status": "COMPLETED",
    "created_at": "2026-11-14T12:00:00Z"
  }
  ```
- **Response `202 Accepted`** (Amount >= COP 1,000,000.00, requires MFA):
  ```json
  {
    "id": "tr_sec456",
    "source_account": "Checking",
    "destination_account": "Savings",
    "amount": "1500000.00",
    "status": "PENDING_MFA",
    "created_at": "2026-11-14T12:00:00Z",
    "expires_at": "2026-11-14T12:05:00Z"
  }
  ```

---

### `POST /api/transfers/{transfer_id}/confirm-mfa`
Confirms a sensitive transfer pending MFA authorization.

- **Request Payload**: `{"code": "123456"}`
- **Response `200 OK`**:
  ```json
  {
    "id": "tr_sec456",
    "status": "COMPLETED",
    "message": "Transfer confirmed and completed successfully."
  }
  ```

---

## 2. Dynamic Limits Endpoints

### `GET /api/limits`
Retrieves the customer's active transfer limits and current UTC day's consumption.

- **Response `200 OK`**:
  ```json
  {
    "per_transfer_limit": "5000000.00",
    "daily_limit": "10000000.00",
    "current_daily_consumption": "1000000.00",
    "remaining_daily_availability": "9000000.00",
    "updated_at": "2026-11-14T00:00:00Z"
  }
  ```

---

### `PUT /api/limits`
Updates the customer's per-transfer and daily maximum limits.

- **Request Payload**:
  ```json
  {
    "per_transfer_limit": "2000000.00",
    "daily_limit": "4000000.00"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "per_transfer_limit": "2000000.00",
    "daily_limit": "4000000.00",
    "current_daily_consumption": "1000000.00",
    "remaining_daily_availability": "3000000.00",
    "updated_at": "2026-11-14T12:30:00Z"
  }
  ```
- **Error `400 Bad Request`**: Non-positive numbers or > 2 decimal places.

---

## 3. Beneficiaries Endpoints

### `GET /api/beneficiaries`
Lists all saved external ACH beneficiaries belonging to the user.

- **Response `200 OK`**:
  ```json
  [
    {
      "id": "ben_123",
      "name": "Maria Rodriguez",
      "bank_name": "Bancolombia",
      "routing_number": "123456789",
      "account_number": "9876543210",
      "created_at": "2026-11-14T10:00:00Z"
    }
  ]
  ```

---

### `POST /api/beneficiaries`
Creates a new saved external ACH beneficiary.

- **Request Payload**:
  ```json
  {
    "name": "Carlos Gomez",
    "bank_name": "Banco de Bogota",
    "routing_number": "987654321",
    "account_number": "1122334455"
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "id": "ben_456",
    "name": "Carlos Gomez",
    "bank_name": "Banco de Bogota",
    "routing_number": "987654321",
    "account_number": "1122334455",
    "created_at": "2026-11-14T12:35:00Z"
  }
  ```
- **Error `400 Bad Request`**: Routing number not exactly 9 digits, or account number not 4–17 digits.

---

### `DELETE /api/beneficiaries/{beneficiary_id}`
Deletes a saved beneficiary from future selection (D-08).

- **Response `200 OK`**:
  ```json
  {
    "id": "ben_456",
    "message": "Beneficiary deleted successfully."
  }
  ```

---

## 4. ACH Transfer Endpoints

### `POST /api/transfers/ach`
Initiates a simulated third-party ACH transfer with immediate debit.

- **Validation Precedence (Remediating F-09)**: Dynamic limits (per-transfer limit and remaining daily availability) MUST be evaluated BEFORE checking the sensitive threshold (amount >= COP 1,000,000.00). If either limit is exceeded, the endpoint returns `400 Bad Request` immediately, even if amount >= COP 1M. An MFA challenge (`202 Accepted`) is presented only when the amount is within all limits. A valid MFA PIN cannot bypass limits (LIM-07, A14).
- **Request Payload (Ad Hoc or Saved Beneficiary)**:
  ```json
  {
    "source_account_id": "acc_checking_123",
    "amount": "250000.00",
    "recipient_name": "Empresa de Energia",
    "bank_name": "Banco Davivienda",
    "routing_number": "123456789",
    "account_number": "456789123",
    "save_beneficiary": false
  }
  ```
- **Response `201 Created`** (Amount < COP 1,000,000.00):
  ```json
  {
    "id": "tr_ach_001",
    "transfer_type": "ACH",
    "source_account": "Checking",
    "recipient_name": "Empresa de Energia",
    "bank_name": "Banco Davivienda",
    "routing_number": "123456789",
    "account_number": "456789123",
    "amount": "250000.00",
    "status": "PENDING",
    "created_at": "2026-11-14T12:40:00Z"
  }
  ```
- **Response `202 Accepted`** (Amount >= COP 1,000,000.00):
  ```json
  {
    "id": "tr_ach_002",
    "transfer_type": "ACH",
    "source_account": "Checking",
    "recipient_name": "Empresa de Energia",
    "amount": "1500000.00",
    "status": "PENDING_MFA",
    "created_at": "2026-11-14T12:40:00Z",
    "expires_at": "2026-11-14T12:45:00Z"
  }
  ```
- **Error `400 Bad Request`**: Insufficient funds, exceeds per-transfer limit, exceeds daily limit, or invalid routing/account formats.

---

## 5. Recurring Payment Schedule Endpoints

### `GET /api/recurring-schedules`
Lists all recurring schedules for the customer.

- **MFA Expiration Sweep (Remediating F-08)**: Upon invocation, this endpoint automatically sweeps and transitions any schedule with `status = 'PENDING_MFA'` and `mfa_expires_at < now_utc` to `EXPIRED`.
- **Response `200 OK`**:
  ```json
  [
    {
      "id": "rec_001",
      "transfer_type": "ACH",
      "source_account_id": "acc_checking_123",
      "source_account": "Checking",
      "destination_display": "Empresa de Energia (Davivienda ***123)",
      "amount": "150000.00",
      "frequency": "MONTHLY",
      "status": "ACTIVE",
      "next_due_date": "2026-12-14T12:40:00Z",
      "last_executed_at": null,
      "mfa_expires_at": null,
      "created_at": "2026-11-14T12:40:00Z"
    }
  ]
  ```

---

### `POST /api/recurring-schedules`
Creates a recurring payment schedule for internal or ACH transfers (REC-01..12).

- **Request Payload**:
  ```json
  {
    "transfer_type": "ACH",
    "source_account_id": "acc_checking_123",
    "amount": "150000.00",
    "frequency": "WEEKLY",
    "start_date": "2026-11-20",
    "recipient_name": "Arrendatario",
    "bank_name": "Bancolombia",
    "routing_number": "123456789",
    "account_number": "99887766"
  }
  ```
- **Response `201 Created`** (Amount < COP 1,000,000.00):
  ```json
  {
    "id": "rec_002",
    "status": "ACTIVE",
    "next_due_date": "2026-11-20T00:00:00Z",
    "message": "Recurring schedule created successfully."
  }
  ```
- **Response `202 Accepted`** (Amount >= COP 1,000,000.00, D-05):
  ```json
  {
    "id": "rec_003",
    "status": "PENDING_MFA",
    "next_due_date": "2026-11-20T00:00:00Z",
    "expires_at": "2026-11-14T12:45:00Z",
    "message": "MFA verification required to activate recurring schedule."
  }
  ```

---

### `POST /api/recurring-schedules/{schedule_id}/confirm-mfa`
Confirms a sensitive recurring schedule in `PENDING_MFA` status (D-05).

- **Request Payload**: `{"code": "123456"}`
- **Response `200 OK`**:
  ```json
  {
    "id": "rec_003",
    "status": "ACTIVE",
    "message": "Recurring schedule activated successfully."
  }
  ```

---

### `POST /api/recurring-schedules/{schedule_id}/pause`
Pauses an active schedule (REC-06).

- **Response `200 OK`**: `{"id": "rec_001", "status": "PAUSED"}`

---

### `POST /api/recurring-schedules/{schedule_id}/resume`
Resumes a paused schedule (REC-06).

- **Response `200 OK`**: `{"id": "rec_001", "status": "ACTIVE"}`

---

### `POST /api/recurring-schedules/{schedule_id}/cancel`
Permanently cancels a schedule (terminal state, REC-07).

- **Response `200 OK`**: `{"id": "rec_001", "status": "CANCELLED"}`

---

## 6. Non-Public Test-Only Simulation Endpoints (Remediating F-03, F-05)

These endpoints exist solely for automated tests (`pytest`) to deterministically test state transitions without depending on timing delays or artificial recipient names (D-04, D-06).

**⚠️ ENVIRONMENT GATE (Security Mandate)**:
In normal application environments (e.g., production, staging, or normal user runs), all endpoints under `/api/test/*` are strictly disabled and return `404 Not Found`. They are mounted conditionally only when an explicit environment gate is enabled (`ENABLE_TEST_ENDPOINTS=true` or during test sessions).

---

### `POST /api/test/ach/{transfer_id}/fail`
Triggers simulated processing failure on an eligible `PENDING` ACH transfer, issuing the single refund and excluding it from daily limit consumption (ACH-07, D-06, Remediating F-03, F-05).

- **Settlement Timing & Determinism (F-03)**:
  Autonomous settlement requires transfers to remain in `PENDING` status for >= 10 seconds. This allows automated tests to invoke this failure endpoint deterministically immediately after transfer creation without racing against the background worker.
- **Atomic Single Refund & Idempotency (F-05)**:
  The state transition is executed conditionally within a SQLite `BEGIN IMMEDIATE` transaction:
  ```sql
  UPDATE transfers 
  SET status = 'FAILED', failed_at = :now, refunded_at = :now 
  WHERE id = :transfer_id AND status = 'PENDING';
  ```
  The refund credit (`UPDATE accounts SET balance = balance + amount WHERE id = source_id`) is executed **ONLY IF** `cursor.rowcount == 1`. If `cursor.rowcount == 0` (transfer was already `SETTLED` or `FAILED`), the refund is skipped and `409 Conflict` is returned, guaranteeing zero double refunds.
- **Response `200 OK`**:
  ```json
  {
    "id": "tr_ach_001",
    "status": "FAILED",
    "refunded_amount": "250000.00",
    "message": "Simulated ACH failure processed and refund credited."
  }
  ```
- **Error `409 Conflict`**: If transfer is already `SETTLED` or `FAILED`.
- **Error `404 Not Found`**: If transfer does not exist, or if test endpoints are disabled.

---

### `POST /api/test/ach/settle-pending`
Forces an immediate autonomous settlement sweep of all eligible `PENDING` ACH transfers (ACH-06, D-06).

- **Response `200 OK`**:
  ```json
  {
    "settled_count": 2,
    "message": "Settlement sweep completed successfully."
  }
  ```
- **Error `404 Not Found`**: If test endpoints are disabled.

---

### `POST /api/test/recurring/run-due`
Forces an immediate execution evaluation sweep of all active overdue recurring payment schedules under concurrency lock (REC-05, D-04).

- **Response `200 OK`**:
  ```json
  {
    "processed_count": 1,
    "failed_count": 0,
    "message": "Recurring execution sweep completed."
  }
  ```
- **Error `404 Not Found`**: If test endpoints are disabled.
