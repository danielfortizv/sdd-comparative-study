---
name: Mock Multi-Factor Authentication
description: Multi-factor verification with Security PIN and lockout for sensitive transfer operations exceeding $1,000
targets:
  - ../backend/app/services/mfa_service.py
  - ../backend/app/routers/transfers.py
  - ../backend/app/models.py
  - ../frontend/src/components/MfaModal.tsx
---

# Mock Multi-Factor Authentication (MFA)

Provides security verification for sensitive transfer operations exceeding the `$1,000.00` monetary threshold.

## Data Contract

```python
class MfaVerifyRequest(BaseModel):
    pin: str

class MfaStatusResponse(BaseModel):
    threshold: float          # 1000.00
    locked: bool              # False initially
    remaining_attempts: int   # 3 initially
```

## Security PIN Validation

- The mock Security PIN is configured as `'1234'`.
  `[@test] ../backend/tests/test_mfa.py`
- Operations with transfer amount `<= 1000.00` (including boundary value `1000.00`) bypass MFA checks entirely.
  `[@test] ../backend/tests/test_mfa.py`
  `[@test] ../backend/tests/test_transfers.py`
- Operations with transfer amount `> 1000.00` (including boundary value `1000.01`) require providing the valid PIN.
  `[@test] ../backend/tests/test_mfa.py`
  `[@test] ../backend/tests/test_transfers.py`
- Submitting the correct PIN `'1234'` succeeds and resets failed attempts back to 3.
  `[@test] ../backend/tests/test_mfa.py`
- Submitting an incorrect PIN decrements `remaining_attempts` and returns HTTP 400 with remaining attempts count.
  `[@test] ../backend/tests/test_mfa.py`
- After 3 consecutive incorrect PIN attempts, the MFA status becomes locked (`locked = True`, `remaining_attempts = 0`).
  `[@test] ../backend/tests/test_mfa.py`
- While locked, any transfer requiring MFA is rejected with HTTP 423 Locked.
  `[@test] ../backend/tests/test_mfa.py`

## User Interface Display

- Automatically opens the MFA modal when a user attempts a transfer exceeding `$1,000.00`.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Clearly displays the transfer details awaiting authorization: Source Account, Destination Account, and Amount.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Includes a 4-digit PIN input and helper text indicating `Default Mock PIN: 1234`.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Displays error messages and remaining attempts on incorrect PIN submission.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Disables submission and displays an account lockout warning when 3 attempts are exhausted.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
- Allows the user to cancel the verification, returning safely to the transfer form without executing any transaction.
  `[@test] ../frontend/src/__tests__/MfaModal.test.tsx`
