---
name: Mock Multi-Factor Authentication
description: Multi-factor verification with Security PIN and lockout for sensitive transfer and conversion operations exceeding $1,000 USD equivalent with exact Decimal precision
targets:
  - ../backend/app/services/mfa_service.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/routers/transfers.py
  - ../backend/app/routers/conversions.py
  - ../backend/app/models.py
  - ../frontend/src/components/MfaModal.tsx
---

# Mock Multi-Factor Authentication (MFA)

Provides security verification for sensitive financial operations (internal transfers, currency conversions, ACH transfers, and recurring schedule setup) exceeding the `$1,000.00` USD-equivalent monetary threshold using exact Decimal comparisons.

Governed by Researcher Decisions D-01, D-03, D-04, and D-07 and SEED-4 Items 2, 5, and 6.

## Data Contract

```python
from decimal import Decimal

class MfaVerifyRequest(BaseModel):
    pin: str

class MfaStatusResponse(BaseModel):
    threshold: Decimal = Field(default=Decimal("1000.00")) # Denominated in USD reference currency [MODIFIED D-03]
    locked: bool              # False initially
    remaining_attempts: int   # 3 initially
```

## Security PIN Validation & USD-Equivalent Threshold

- Mock Security PIN: Configured as `'1234'`. [INHERITED]
  `[@test] ../backend/tests/test_mfa.py`
- Multicurrency Threshold Normalization: Evaluates threshold against the unrounded USD equivalent of the source amount using exact `Decimal` arithmetic:
  `USD_equivalent = source_amount / USD_base_factor(source_currency)`. [NEW D-07]
  `[@test] ../backend/tests/test_mfa.py`
- Threshold Bypass: Operations with `USD_equivalent <= Decimal("1000.00")` (including boundary value `1000.00`) bypass MFA checks entirely. [MODIFIED D-07]
  `[@test] ../backend/tests/test_mfa.py`
  `[@test] ../backend/tests/test_transfers.py`
- Threshold Trigger: Operations with `USD_equivalent > Decimal("1000.00")` (including boundary value `1000.01`) require providing the valid PIN. [MODIFIED D-07]
  `[@test] ../backend/tests/test_mfa.py`
  `[@test] ../backend/tests/test_transfers.py`
- Applicable Financial Commands: The threshold check gates same-currency transfers (`POST /api/transfers`), currency conversions (`POST /api/conversions`), external ACH transfers (`POST /api/transfers/ach`), and recurring schedule creation (`POST /api/recurring`). [NEW D-07]
  `[@test] ../backend/tests/test_mfa.py`
- Successful Verification: Submitting the correct PIN `'1234'` succeeds and resets failed attempts back to 3. [INHERITED]
  `[@test] ../backend/tests/test_mfa.py`
- Incorrect PIN: Decrements `remaining_attempts` and returns HTTP 400 with remaining attempts count. [INHERITED]
  `[@test] ../backend/tests/test_mfa.py`
- Account Lockout: After 3 consecutive incorrect PIN attempts, MFA status becomes locked (`locked = True`, `remaining_attempts = 0`). [INHERITED]
  `[@test] ../backend/tests/test_mfa.py`
- Lockout Enforcement: While locked, any transfer or conversion requiring MFA is rejected with HTTP 423 Locked. [INHERITED D-07]
  `[@test] ../backend/tests/test_mfa.py`

## Validation Order and Precedence

- Invariant Validation Precedence: Available balance, account status, and dynamic transfer limits are strictly validated before MFA verification. Supplying a valid PIN cannot override insufficient funds or limit violations. [NEW D-07]
  `[@test] ../backend/tests/test_mfa.py`
  `[@test] ../backend/tests/test_transfer_limits.py`

## Audit Ledger & Security Integration

- Successful PIN verification emits an immutable audit event `mfa_verified` with `status="SUCCESS"`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Failed PIN verification attempts emit an immutable audit event `mfa_attempt_failed` with `status="FAILURE"` recording remaining attempts count. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Reaching the 3-attempt limit triggers and emits an audit event `mfa_locked` with `status="FAILURE"`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Operations rejected due to locked MFA status emit an audit event `mfa_lockout_rejected` with `status="FAILURE"`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Audit log entry details, server logs, and error responses must NEVER contain the raw Security PIN or plaintext credentials. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`

## User Interface Display & Interception

- Automatically intercepts internal transfers and currency conversions with USD-equivalent `> $1,000.00` to prompt for MFA PIN. [MODIFIED D-07]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Clearly displays operation details awaiting authorization: Source Account & Currency, Destination Account & Currency, and Amount (with estimated USD equivalent when source is non-USD). [MODIFIED D-07]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Includes 4-digit PIN input with helper text indicating `Default Mock PIN: 1234`. [INHERITED]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Displays error messages and remaining attempts on incorrect PIN submission. [INHERITED]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Disables submission and displays account lockout warning when attempts are exhausted. [INHERITED]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Allows cancellation, returning safely to transfer or conversion form without executing any transaction. [INHERITED]
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
