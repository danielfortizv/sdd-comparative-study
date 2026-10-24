---
title: 'Story 1.2: Account Portfolio API & Context Validation'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/prd.md'
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Retail customer Alex Morgan needs to retrieve their bank accounts and current balances through a secure REST API with exact monetary formatting and session boundary enforcement.

**Approach:** Implement Pydantic account schemas serializing balances as both integer cents and formatted USD strings, a FastAPI dependency extracting and validating `X-Customer-Id: cust_mock_001`, an account service querying SQLite, and the `GET /api/accounts` endpoint returning HTTP 200 on success and HTTP 403 on missing or invalid customer context.

## Boundaries & Constraints

**Always:**
- Require `X-Customer-Id` header on `GET /api/accounts` (`AD-4`).
- Validate that the customer exists; reject missing or mismatched customer IDs with HTTP 403 Forbidden and the standard JSON error envelope (`AD-4`, `AD-10`).
- Serialize monetary values as integer `balance_cents` and formatted string `balance_formatted` (e.g. `"$2,500.00"`) (`AD-1`).
- Return all three pre-seeded accounts: Primary Checking, High-Yield Savings, Emergency Reserve (`AD-8`).

**Never:**
- Never use floating point `float` for monetary balances (`AD-1`).
- Never expose technical database row IDs or unmasked foreign keys outside the contract.
- Never modify unrelated Kiro files or experiment logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Valid Customer Request | Header `X-Customer-Id: cust_mock_001` | HTTP 200 with list of 3 accounts with cents and formatted USD | N/A |
| Missing Customer Header | Header omitted | HTTP 403 Forbidden | `{ "error": { "code": "MISSING_CUSTOMER_CONTEXT", "message": "X-Customer-Id header is required." } }` |
| Invalid Customer ID | Header `X-Customer-Id: unknown_999` | HTTP 403 Forbidden | `{ "error": { "code": "UNAUTHORIZED_CUSTOMER", "message": "Customer identity not recognized or unauthorized." } }` |
| Monetary Formatting | Balance 250000 cents | `"balance_cents": 250000, "balance_formatted": "$2,500.00"` | Formatted via exact integer arithmetic |

</frozen-after-approval>

## Code Map

- `backend/app/schemas/account.py` -- Account response Pydantic models
- `backend/app/api/dependencies.py` -- Customer context dependency
- `backend/app/services/account_service.py` -- Account query and balance formatting service
- `backend/app/api/accounts.py` -- FastAPI router for accounts
- `backend/app/main.py` -- Router registration
- `backend/tests/test_accounts.py` -- Automated API test suite

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/schemas/account.py` -- Define AccountResponse and AccountListResponse schemas
- [x] `backend/app/api/dependencies.py` -- Implement get_current_customer dependency validating `X-Customer-Id`
- [x] `backend/app/services/account_service.py` -- Implement get_accounts_for_customer query
- [x] `backend/app/api/accounts.py` -- Implement GET /api/accounts endpoint
- [x] `backend/app/main.py` -- Include accounts router under /api
- [x] `backend/tests/test_accounts.py` -- Add automated test suite verifying 200, 403, and balance precision

**Acceptance Criteria:**
- Given an authenticated request with `X-Customer-Id: cust_mock_001`, when sending `GET /api/accounts`, then HTTP 200 is returned with all 3 accounts formatted correctly.
- Given a request without `X-Customer-Id` or with an invalid ID, when sending `GET /api/accounts`, then HTTP 403 Forbidden is returned with the standard error envelope.

## Implementation Notes

- **Account Schemas & Integer Formatting**:
  - Implemented `AccountResponse` in `backend/app/schemas/account.py` with integer `balance_cents` and exact formatted string `balance_formatted` using non-floating-point `divmod(cents, 100)` helper (`AD-1`).
  - Added support for both `type` and `account_type` fields in the response model to ensure 100% compatibility across frontend and acceptance test assertions.
- **Context Dependency & Error Envelopes**:
  - Implemented `get_current_customer` in `backend/app/api/dependencies.py` extracting `X-Customer-Id` header and verifying existence in the `customer` table (`AD-4`).
  - Configured standardized error handling (`AD-10`) in `backend/app/main.py` formatting HTTP 403 exceptions as `{"error": {"code": ..., "message": ...}}`.
- **Router & Endpoint**:
  - Implemented `GET /api/accounts` in `backend/app/api/accounts.py` and registered with prefix `/api` in `backend/app/main.py`.
- **Verification**:
  - Automated tests in `backend/tests/test_accounts.py` verifying successful retrieval of 3 accounts, 403 rejection on missing header, 403 rejection on invalid ID, and cents formatting edge cases. All 8 backend tests pass.
  - Frontend production build (`tsc && vite build`) confirmed 0 errors.
