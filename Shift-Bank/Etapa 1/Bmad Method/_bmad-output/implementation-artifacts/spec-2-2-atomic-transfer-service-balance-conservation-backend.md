---
title: 'Story 2.2: Atomic Transfer Service & Balance Conservation Backend'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/prd.md'
  - '_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Shift Bank needs a robust, transactional transfer execution service that enforces relational ACID guarantees, prevents overdrafts, verifies total balance conservation, protects against duplicate in-flight submissions via idempotency keys, and records dual-entry ledger rows.

**Approach:** Implement `backend/app/schemas/transfer.py`, `backend/app/services/transfer_service.py`, and `backend/app/api/transfers.py` exposing `POST /api/transfers`. For standard transfers ($\le \$1,000.00$), the service executes within an explicit SQLite `BEGIN IMMEDIATE TRANSACTION` boundary, checks sufficient funds, atomically debits source and credits destination, records two linked immutable movements (`DEBIT`/`CREDIT`), validates balance conservation ($\sum B_{after} == \sum B_{before}$), and commits. Idempotency is enforced using a 60-second TTL cache.

## Boundaries & Constraints

**Always:**
- Execute transfer mutations inside a single isolated transaction (`BEGIN IMMEDIATE`) (`AD-2`).
- Verify balance conservation invariant: sum of customer balances across all accounts after equals sum before (`AD-2`).
- Create exactly two immutable movements (`DEBIT` on source, `CREDIT` on destination) with the identical `transfer_id` (`FR-13`, `AD-7`).
- Reject same-account transfers (`from_account_id == to_account_id`) with HTTP 400 (`SAME_ACCOUNT_TRANSFER_NOT_ALLOWED`) (`FR-3`, `AD-10`).
- Reject non-positive amounts (`amount_cents <= 0`) with HTTP 422 (`INVALID_TRANSFER_AMOUNT`) (`FR-4`, `AD-10`).
- Reject insufficient funds (`amount_cents > source.balance_cents`) with HTTP 422 (`INSUFFICIENT_FUNDS`) (`FR-5`, `AD-10`).
- Cache idempotency response for 60 seconds; identical in-flight or completed requests return cached response (`FR-7`, `AD-5`).

**Never:**
- Never allow partial execution where one account is updated and the other is not.
- Never use binary floating-point math (`AD-1`).
- Never allow overdrafts (account balance < 0).
- Never modify unrelated Kiro files or experiment logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Valid Standard Transfer | $250.00 from Checking to Savings, valid Idempotency-Key | HTTP 200, status COMPLETED, balances atomically updated, 2 movements logged | Full rollback on SQL error |
| Same-Account Transfer | from: CHK-1001, to: CHK-1001 | HTTP 400 Bad Request | `SAME_ACCOUNT_TRANSFER_NOT_ALLOWED` |
| Negative or Zero Amount | amount_cents <= 0 | HTTP 422 Unprocessable Entity | `INVALID_TRANSFER_AMOUNT` |
| Insufficient Funds | amount_cents > source balance | HTTP 422 Unprocessable Entity | `INSUFFICIENT_FUNDS` |
| Duplicate Idempotency Key | Repeated request within 60s with same key | Returns cached HTTP 200 response | No balance mutation |
| Transaction Failure | Simulated database error mid-transfer | Balances and movements completely rolled back | `TRANSACTION_ABORTED` |

</frozen-after-approval>

## Code Map

- `backend/app/schemas/transfer.py` -- Pydantic request and response schemas for transfers
- `backend/app/services/transfer_service.py` -- Atomic transfer execution, balance conservation, idempotency cache
- `backend/app/api/transfers.py` -- FastAPI router exposing `POST /api/transfers`
- `backend/app/main.py` -- Register transfers router
- `backend/tests/test_transfers.py` -- Automated test suite verifying atomic transfers, rollback, and edge cases

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/schemas/transfer.py` -- Define TransferRequest, TransferResponse, and TransferItem schemas
- [x] `backend/app/services/transfer_service.py` -- Implement execute_transfer with BEGIN IMMEDIATE and balance conservation
- [x] `backend/app/api/transfers.py` -- Implement POST /api/transfers endpoint with Idempotency-Key handling
- [x] `backend/app/main.py` -- Mount transfers router under /api
- [x] `backend/tests/test_transfers.py` -- Add automated tests verifying AC-1 through AC-8

**Acceptance Criteria:**
- Given a valid transfer request POST /api/transfers with amount <= $1,000.00, execution occurs within a single SQLite BEGIN IMMEDIATE boundary, source balance decrements, destination balance increments, two linked movements are created, and balance conservation invariant is verified.
- If from_account_id == to_account_id, API returns HTTP 400 SAME_ACCOUNT_TRANSFER_NOT_ALLOWED.
- If amount_cents <= 0, API returns HTTP 422 INVALID_TRANSFER_AMOUNT.
- If amount_cents > source balance, API returns HTTP 422 INSUFFICIENT_FUNDS.
- Submitting duplicate request with identical Idempotency-Key within 60 seconds returns cached response without re-executing balances.

## Implementation Notes

- **Transfer Schemas & Formatting**:
  - Implemented `TransferRequest`, `TransferItem`, and `TransferResponse` in `backend/app/schemas/transfer.py`.
- **Atomic Transfer Execution & Invariant Enforcement**:
  - Implemented `execute_standard_transfer` in `backend/app/services/transfer_service.py`.
  - Transaction boundary managed via SQLite `BEGIN IMMEDIATE TRANSACTION` (`AD-2`).
  - Enforced atomic debit on source (`balance_cents = balance_cents - :amt`) and credit on destination (`balance_cents = balance_cents + :amt`) (`FR-6`).
  - Recorded paired immutable movements (`DEBIT` on source, `CREDIT` on destination) with post-transaction running balance and identical `transfer_id` (`FR-13`, `AD-7`).
  - Enforced Balance Conservation Invariant ($\sum B_{after} == \sum B_{before}$) before commit (`AD-2`).
  - Added 60s TTL idempotency caching via `idempotency_cache` table (`FR-7`, `AD-5`).
- **Validation & Error Handling**:
  - Prohibits same-account transfers with HTTP 400 `SAME_ACCOUNT_TRANSFER_NOT_ALLOWED` (`FR-3`, `AD-10`).
  - Prohibits non-positive amounts with HTTP 422 `INVALID_TRANSFER_AMOUNT` (`FR-4`, `AD-10`).
  - Prohibits overdrafts with HTTP 422 `INSUFFICIENT_FUNDS` (`FR-5`, `AD-10`).
  - Guarantees complete atomic rollback on transaction errors (`AD-2`).
- **Router & Endpoint**:
  - Exposes `POST /api/transfers` in `backend/app/api/transfers.py`, registered in `backend/app/main.py`.
- **Automated Verification**:
  - Implemented 6 test cases in `backend/tests/test_transfers.py` covering standard execution, balance conservation, same-account rejection, non-positive amounts, insufficient funds, idempotency duplicate submission, and atomic rollback on simulated failure.
  - All 14 backend tests pass (`pytest`).
  - All 15 frontend tests pass (`vitest`).
  - Production build verified with 0 errors (`tsc && vite build`).
