---
name: Recurring Payment Scheduling
description: Configure and manage scheduled recurring same-currency transfers with automated background execution, exact Decimal precision, optimistic concurrency, and deterministic event idempotency
targets:
  - ../backend/app/routers/recurring.py
  - ../backend/app/services/recurring_service.py
  - ../backend/app/services/event_store.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/services/crypto_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/services/scheduler.py
  - ../backend/app/models.py
  - ../frontend/src/components/RecurringPayments.tsx
---

# Recurring Payment Scheduling

Provides capabilities to schedule recurring same-currency internal and USD-denominated external ACH transfers with automated background execution, lifecycle controls, and event-sourced integration using exact Decimal precision.

Governed by Researcher Decisions D-01, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-11, D-12, and D-14 and SEED-4 Items 1, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class RecurringScheduleCreateRequest(BaseModel):
    transfer_type: str                 # "internal" | "ach"
    from_account_id: int
    to_account_id: Optional[int] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    amount: Decimal = Field(..., gt=0, description="Amount; strictly positive, max 2 decimals") # [MODIFIED D-03]
    frequency: str                     # "daily" | "weekly" | "monthly"
    start_date: Optional[datetime] = None
    description: Optional[str] = None
    pin: Optional[str] = None          # Required at creation if USD-equivalent amount > 1000.00

class RecurringScheduleResponse(BaseModel):
    id: int
    user_id: int
    transfer_type: str
    from_account_id: int
    to_account_id: Optional[int]
    beneficiary_id: Optional[int]
    recipient_name: Optional[str]
    routing_number: Optional[str]
    account_number: Optional[str]
    bank_name: Optional[str]
    amount: Decimal                    # Exact Decimal amount [MODIFIED D-03]
    currency: str                      # Fixed currency matching source account [NEW D-08]
    frequency: str
    status: str                        # "active" | "paused" | "cancelled"
    description: Optional[str]
    next_execution_date: datetime
    created_at: datetime
    last_executed_at: Optional[datetime]
```

## Schedule Creation & Currency Restrictions

- `POST /api/recurring` creates a new recurring payment schedule in `active` status. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Supports both `internal` (between user's own accounts) and `ach` (to external beneficiary) transfer types. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Same-Currency Restriction for Internal Transfers: Internal recurring transfers are permitted strictly between accounts sharing the SAME currency (`from_acc.currency == to_acc.currency`). Supports USD, EUR, and GBP same-currency pairs. [NEW D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Cross-Currency Rejection: Cross-currency recurring schedules are rejected with HTTP 400 Bad Request (`RECURRING_REQUIRES_SAME_CURRENCY`). [NEW D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- No Recurring Conversions: Automatic recurring currency conversions are strictly prohibited; conversions are user-initiated operations via `POST /api/conversions`. [NEW D-04, D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Recurring ACH Currency Restriction: Recurring ACH transfers remain USD-only and must use USD source accounts (`from_acc.currency == "USD"`). [NEW D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Inherited Schedule Preservation: Existing USD recurring schedules are preserved during migration with explicit USD currency identity and without changing amounts, recipients, or next execution dates. [INHERITED D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Next Execution Date Calculation:
  - When `start_date` is specified in the future, sets `next_execution_date` to `start_date`.
  - When `start_date` is omitted, sets `next_execution_date` to the first recurrence interval from creation (`now + 1 day` for daily, `now + 7 days` for weekly, `now + 30 days` for monthly). [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- MFA Authorization at Creation: If schedule amount's USD-equivalent `> $1,000.00`, requires a valid mock Security PIN (`1234`) at creation time; if omitted, returns HTTP 428 `MfaRequiredResponse`. [MODIFIED D-07, D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Input Validations: Fails with HTTP 422 if `frequency` not one of `"daily"`, `"weekly"`, `"monthly"`, or if `amount <= 0` or has > 2 decimals. Fails with HTTP 404 if source account does not exist. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`

## Lifecycle Management & Manual Simulation

- Schedule Query: `GET /api/recurring` returns HTTP 200 with all recurring schedules configured by the user. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Status Transitions:
  - `POST /api/recurring/{id}/pause` updates an `active` schedule to `paused` status. Fails with HTTP 400 if already paused or cancelled.
  - `POST /api/recurring/{id}/resume` updates a `paused` schedule back to `active` status.
  - `POST /api/recurring/{id}/cancel` updates a schedule to `cancelled` status.
  - Cancelled schedules are immutable and cannot be transitioned to `paused` or `active`. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Simulation Trigger Endpoint: `POST /api/recurring/process-due` triggers immediate processing of all due recurring payments and returns execution summaries for simulation and testing. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`

## Automated Execution & Event-Sourced Idempotency

- Background Execution Autonomy: Background execution runs periodically (`next_execution_date <= now`) autonomously without prompting for interactive MFA PIN, as authorization was verified at creation time. [INHERITED D-07, D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Internal Version Resolution: At execution time, the scheduler queries the authoritative current versions of affected accounts internally rather than relying on stale versions from creation time. [NEW D-14]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Dynamic Limit & Balance Check: Validates available balance and USD-equivalent daily transfer limits at execution time. If breached, records failed attempt, leaves schedule active, and advances next execution date. [MODIFIED D-07, D-08]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Successful Execution State Mutation: Executes the transfer, updates account balance, records transaction history, sets `last_executed_at = now`, and advances `next_execution_date` by recurrence interval (+1 day, +7 days, +30 days). [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Event Sourcing & Deterministic Idempotency: On execution, appends the appropriate domain event (`InternalTransferCompleted` or `AchTransferInitiated`) using a deterministic idempotency key derived from `schedule_id` and execution timestamp. Repeated scheduler executions or restarts cannot execute the same recurrence twice. [NEW D-08, D-09, D-12]
  `[@test] ../backend/tests/test_recurring_payments.py`
- Paused/Cancelled Exclusion: Schedules in `paused` or `cancelled` status are skipped by the scheduler. [INHERITED]
  `[@test] ../backend/tests/test_recurring_payments.py`

## Data Protection & Audit Integration

- Sensitive Coordinate Encryption: Recipient routing and account numbers stored in `recurring_schedules` and event payloads are encrypted using AES-256-GCM (`enc:v1:<iv>:<tag>:<ciphertext>`). Third-party account numbers are masked to last 4 digits (`****5678`) in audit logs and execution references. [INHERITED D-11]
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_recurring_payments.py`
- Audit Logging: Emits Stage 3 HMAC-SHA256 audit events for schedule lifecycle transitions (`recurring_schedule_created`, `recurring_schedule_paused`, `recurring_schedule_resumed`, `recurring_schedule_cancelled`) and executions (`recurring_payment_executed`). [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_recurring_payments.py`

## User Interface Display & Workflow

- Recurring Payments Panel: Renders list of all configured schedules with transfer type, formatted amount and currency symbol, frequency badge, status indicator, and next execution date. [INHERITED]
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- Action Controls: Provides intuitive controls to pause, resume, or cancel active schedules with instant optimistic UI update. [INHERITED]
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- Schedule Modal: Enables creating internal or ACH recurring schedules with currency-aware account selection and start-date picker. [INHERITED]
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
