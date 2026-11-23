---
name: Recurring Payment Scheduling
description: Configure and manage scheduled recurring transfers with automated background execution and lifecycle states
targets:
  - ../backend/app/routers/recurring.py
  - ../backend/app/services/recurring_service.py
  - ../backend/app/services/scheduler.py
  - ../backend/app/models.py
  - ../frontend/src/components/RecurringPayments.tsx
---

# Recurring Payment Scheduling

Provides capabilities to schedule recurring internal and external ACH transfers with automated background execution and lifecycle controls.

## Data Contract

```python
class RecurringScheduleCreateRequest(BaseModel):
    transfer_type: str  # "internal" | "ach"
    from_account_id: int
    to_account_id: Optional[int] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    amount: float
    frequency: str  # "daily" | "weekly" | "monthly"
    start_date: Optional[datetime] = None
    description: Optional[str] = None
    pin: Optional[str] = None

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
    amount: float
    frequency: str
    status: str  # "active" | "paused" | "cancelled"
    description: Optional[str]
    next_execution_date: datetime
    created_at: datetime
    last_executed_at: Optional[datetime]
```

## Schedule Creation

- `POST /api/recurring` creates a new recurring payment schedule in `active` status.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Supports both `internal` (between user's own accounts) and `ach` (to external beneficiary) transfer types.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Accepts frequency values: `"daily"`, `"weekly"`, and `"monthly"`.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Sets `next_execution_date` to `start_date` or the next scheduled recurrence timestamp:
  - When `start_date` is specified in the future, sets `next_execution_date` to `start_date`.
  - When `start_date` is omitted, sets `next_execution_date` to the first recurrence interval from creation (`now + 1 day` for daily, `now + 7 days` for weekly, `now + 30 days` for monthly).
  `[@test] ../backend/tests/test_recurring_payments.py`
- If schedule `amount > $1,000.00`, requires a valid mock Security PIN (`1234`) at creation time; if omitted, returns HTTP 428 `MfaRequiredResponse`.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Fails with HTTP 422 if `frequency` is not one of `"daily"`, `"weekly"`, or `"monthly"`.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Fails with HTTP 422 if `amount` is `<= 0` or has more than 2 decimal places.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Fails with HTTP 404 if source account does not exist or does not belong to the user.
  `[@test] ../backend/tests/test_recurring_payments.py`

## Schedule Management

- `GET /api/recurring` returns HTTP 200 with all recurring payment schedules configured by the user.
  `[@test] ../backend/tests/test_recurring_payments.py`
- `POST /api/recurring/{id}/pause` updates an `active` schedule to `paused` status.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Fails with HTTP 400 if attempting to pause a schedule that is in `cancelled` or `paused` status.
  `[@test] ../backend/tests/test_recurring_payments.py`
- `POST /api/recurring/{id}/resume` updates a `paused` schedule back to `active` status.
  `[@test] ../backend/tests/test_recurring_payments.py`
- `POST /api/recurring/{id}/cancel` updates a schedule to `cancelled` status; cancelled schedules cannot be resumed.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Cancelled schedules are immutable and cannot be transitioned to `paused` or `active`.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Returns HTTP 404 if schedule `{id}` does not exist or does not belong to the user.
  `[@test] ../backend/tests/test_recurring_payments.py`

## Simulation and Manual Processing

- `POST /api/recurring/process-due` triggers immediate processing of all due recurring payments and returns execution summaries (for testing and simulation).
  `[@test] ../backend/tests/test_recurring_payments.py`

## Automated Scheduled Execution

- Background scheduler periodically checks `active` schedules where `next_execution_date <= now`.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Background execution runs autonomously without prompting for interactive MFA PIN, as authorization was verified at creation time.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Validates source account available balance and daily cumulative transfer limit at execution time.
  `[@test] ../backend/tests/test_recurring_payments.py`
- On successful execution, executes the transfer, updates account balance, records transaction history, sets `last_executed_at = now`, and advances `next_execution_date` by recurrence interval (+1 day for daily, +7 days for weekly, +1 month for monthly).
  `[@test] ../backend/tests/test_recurring_payments.py`
- If execution fails (e.g., insufficient funds or daily limit exceeded), records the failed attempt, leaves the schedule `active`, and advances `next_execution_date` to the next cycle.
  `[@test] ../backend/tests/test_recurring_payments.py`
- Schedules with status `paused` or `cancelled` are ignored by the scheduler.
  `[@test] ../backend/tests/test_recurring_payments.py`

## User Interface Display

- Dedicated Recurring Payments view or tab renders all configured schedules with status badges (`active`, `paused`, `cancelled`), frequency, amount, and next execution date.
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- Provides intuitive controls to Pause, Resume, or Cancel existing recurring schedules.
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- "Schedule Payment" modal allows configuring transfer type (internal or external ACH), accounts/beneficiaries, amount, recurrence frequency, and optional start date.
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- Intercepts recurring schedule setup with MFA modal when amount exceeds `$1,000.00`.
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
- Displays clear error notifications if schedule creation fails validation.
  `[@test] ../frontend/src/__tests__/RecurringPayments.test.tsx`
