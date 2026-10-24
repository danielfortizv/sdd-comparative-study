---
title: 'Story 2.3: End-to-End Transfer Execution & View Synchronization'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/EXPERIENCE.md'
  - '_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Retail customer Alex Morgan needs to execute an internal transfer from the UI, see immediate visual feedback preventing accidental double-clicks, receive an authoritative success confirmation toast, and have the account balances update synchronously across the dashboard with a visual change indicator.

**Approach:** Implement `initiateTransfer` in `frontend/src/api/client.ts` with client-side UUIDv4 idempotency key generation, enhance `TransferForm.tsx` to handle in-flight submission locking (`Processing Transfer...` + spinner), build an accessible `Toast.tsx` notification component with `aria-live="polite"`, implement the 400ms accent highlight flash (`{colors.accent}`) on updated account cards, and wire full view synchronization in `App.tsx` upon receiving HTTP 200 without optimistic guessing.

## Boundaries & Constraints

**Always:**
- Disable submit button and render animated spinner + *"Processing Transfer..."* immediately upon click (`FR-7`, `UX-DR-4`).
- Generate and transmit client-side `Idempotency-Key` (UUIDv4) with every transfer request (`AD-5`).
- Display emerald confirmation toast upon HTTP 200: *"Transfer of $250.00 to [Destination] completed. Reference: TRF-XXXX"* (`FR-6`, `EXPERIENCE.md`).
- Update account portfolio cards synchronously from verified server response (`AD-9`, `NFR-4`).
- Apply 400ms accent highlight flash (`{colors.accent}`) on affected account cards (`EXPERIENCE.md`).
- Reset transfer amount input upon successful completion.

**Never:**
- Never use optimistic balance guessing or update balances before API response returns (`AD-9`).
- Never allow multiple in-flight transfer submissions.
- Never modify unrelated Kiro files or experiment logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Transfer Submission | Click "Transfer Funds" | Button disables, spinner activates, text becomes "Processing Transfer..." | Locks UI to prevent double click |
| HTTP 200 Confirmation | API returns COMPLETED | Amount field resets, emerald toast renders with transfer reference, source/dest balances update | Displays toast alert |
| Balance Change Indicator | Balances updated | Source and Destination cards display subtle 400ms accent flash (`#00D4B2`) | Automatically cleans up flash after 400ms |
| API Error / Rejection | Backend returns 422 or 400 | Button unlocks, error message displayed to user, balances remain unchanged | Non-blocking error handling |

</frozen-after-approval>

## Code Map

- `frontend/src/api/client.ts` -- Add initiateTransfer function with Idempotency-Key header
- `frontend/src/components/Toast.tsx` -- Accessible toast notification component
- `frontend/src/components/AccountCard.tsx` -- Add highlightFlash prop and transition styles
- `frontend/src/components/TransferForm.tsx` -- Add isSubmitting spinner and clear form trigger
- `frontend/src/App.tsx` -- Wire transfer execution, toast display, balance sync, and highlight timing
- `frontend/src/test/TransferExecution.test.tsx` -- Automated test suite verifying AC-1 through AC-4

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/api/client.ts` -- Implement initiateTransfer with UUIDv4 Idempotency-Key
- [x] `frontend/src/components/Toast.tsx` -- Create accessible emerald confirmation toast
- [x] `frontend/src/components/AccountCard.tsx` -- Add 400ms accent highlight flash
- [x] `frontend/src/components/TransferForm.tsx` -- Add in-flight button lock and spinner
- [x] `frontend/src/App.tsx` -- Wire end-to-end execution, form reset, and balance synchronization
- [x] `frontend/src/test/TransferExecution.test.tsx` -- Add automated test suite for Story 2.3

**Acceptance Criteria:**
- Given the customer clicks "Transfer Funds" for a transfer <= $1,000.00, when the request is dispatched, then the submit button immediately enters a disabled state displaying an animated spinner and "Processing Transfer..." to prevent double-clicks.
- And upon receiving HTTP 200 OK (status: "COMPLETED"), the form resets its amount field and an emerald confirmation toast appears: "Transfer of $250.00 to [Destination] completed. Reference: TRF-XXXX".
- And the account portfolio cards update their displayed balances synchronously without optimistic guessing.
- And the updated balance cards display a subtle 400ms accent highlight flash ({colors.accent}) to confirm the update.

## Implementation Notes

- **API Client & Idempotency Key**:
  - Implemented `initiateTransfer` in `frontend/src/api/client.ts` dispatching `POST /api/transfers` with `generateIdempotencyKey()` (UUIDv4) and `X-Customer-Id: cust_mock_001` (`AD-4`, `AD-5`).
- **Submit Button Lock & Spinner**:
  - Updated `TransferForm.tsx` to accept `isSubmitting` and `resetKey` props.
  - When in-flight, disables button and renders animated CSS circular spinner with label *"Processing Transfer..."* (`FR-7`, `UX-DR-4`).
- **Toast Notification**:
  - Created `frontend/src/components/Toast.tsx` rendering emerald confirmation alert with `role="status"`, `aria-live="polite"`, checkmark badge, and close affordance (`EXPERIENCE.md`).
- **View Synchronization & Highlight Flash**:
  - Wired `handleTransferSubmit` in `App.tsx` to await HTTP 200 confirmation, format toast with transfer reference ID, reset form amount, synchronously refetch balances via `refreshAccounts()` (`AD-9`), and trigger a 400ms accent highlight flash (`data-highlighted="true"`) on affected source and destination cards (`EXPERIENCE.md`).
- **Automated Verification**:
  - Added test suite in `frontend/src/test/TransferExecution.test.tsx` asserting button disabled lock with spinner, toast appearance with transfer ID, form amount reset, synchronous balance refresh, and 400ms highlight flash.
  - All 17 frontend tests pass (`vitest`).
  - All 14 backend tests pass (`pytest`).
  - Frontend production build verified (`tsc && vite build`) with 0 errors.
