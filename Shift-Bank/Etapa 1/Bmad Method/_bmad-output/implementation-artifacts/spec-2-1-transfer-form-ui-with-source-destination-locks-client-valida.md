---
title: 'Story 2.1: Transfer Form UI with Source/Destination Locks & Client Validation'
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

**Problem:** Retail customer Alex Morgan needs an interactive transfer formulation panel that prevents invalid transfers (same-account selection, overdraft amounts, non-numeric or negative values) and communicates sensitive transfer step-up requirements before submission.

**Approach:** Implement `TransferForm.tsx` in React 18 with TypeScript using `DESIGN.md` tokens. The form dynamically filters the destination selector to exclude the selected source account, validates currency input to 2 decimal places, compares requested amounts against available balances to prevent overdraft, dynamically updates button labels to "Verify & Transfer ($X.XX)" for amounts > $1,000.00, and integrates into the dashboard layout.

## Boundaries & Constraints

**Always:**
- Dynamically exclude or disable the chosen Source Account from the Destination dropdown (`FR-3`, `UX-DR-4`).
- Validate amounts synchronously against the source account's `balance_cents` (`FR-5`).
- Enforce 2 decimal places maximum and reject negative or non-numeric inputs (`FR-4`).
- Update submit button label to "Verify & Transfer ($X,XXX.XX)" when amount > $1,000.00 (`FR-8`, `UX-DR-4`).
- Disable submit button when amount is empty, <= $0, or exceeds available balance.

**Never:**
- Never allow source and destination to be identical.
- Never implement backend transfer execution in this story (deferred to Story 2.2).
- Never modify unrelated Kiro files or experiment logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Select Source Account | Source changed to Savings | Destination options updated to exclude Savings; Destination auto-switches if it was Savings | Prevents same-account pairing |
| Insufficient Funds | Amount exceeds Source balance | Displays inline warning: "Insufficient funds ($X,XXX.XX available)"; submit button disabled | Prevents form submission |
| Negative / Zero Amount | Amount <= 0 or empty | Submit button disabled; inline hint if zero entered | Prevents invalid amounts |
| Exceeds $1,000.00 Threshold | Amount = $1,500.00 | Submit button label updates to "Verify & Transfer ($1,500.00)"; amber hint displayed | Real-time threshold feedback |
| Standard Transfer Amount | Amount = $250.00 | Submit button label displays "Transfer Funds" | Standard submission state |

</frozen-after-approval>

## Code Map

- `frontend/src/components/TransferForm.tsx` -- Transfer formulation panel with client validation
- `frontend/src/App.tsx` -- Update dashboard workspace layout to integrate TransferForm
- `frontend/src/test/TransferForm.test.tsx` -- Automated test suite verifying validation rules

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/TransferForm.tsx` -- Implement form with dynamic exclusion, input masking, and balance checks
- [x] `frontend/src/App.tsx` -- Assemble 2-column workspace layout with TransferForm
- [x] `frontend/src/test/TransferForm.test.tsx` -- Add automated test suite for all Story 2.1 acceptance criteria

**Acceptance Criteria:**
- Given the customer views the Transfer Action Panel, when selecting a Source Account, then the Destination Account dropdown dynamically disables or excludes the chosen Source Account, making self-transfer impossible in the UI.
- And the Amount field restricts input to positive numbers with at most 2 decimal places, rejecting negative numbers or non-numeric characters.
- And if the customer inputs an amount exceeding the Source Account balance, an inline warning displays: "Insufficient funds ($X,XXX.XX available)", and the submit button is disabled.
- And if the customer inputs an amount > $1,000.00, the submit button label dynamically updates to "Verify & Transfer ($X,XXX.XX)" with an amber sensitivity badge.

## Implementation Notes

- **Transfer Formulation Component**:
  - Implemented `TransferForm.tsx` in `frontend/src/components/TransferForm.tsx` with dynamic destination exclusion (`destinationOptions = accounts.filter(a => a.id !== sourceAccountId)`), preventing identical source and destination selection in the UI (`FR-3`, `UX-DR-4`).
  - Added decimal masking and exact integer conversion in `parseAmountToCents` preventing floating-point precision loss (`FR-4`, `AD-1`).
  - Implemented real-time balance validation: when requested amount exceeds source account's `balance_cents`, renders inline warning in `{colors.destructive}` (*"Insufficient funds in [Account] ($X,XXX.XX available)"*) and disables submit button (`FR-5`, `UX-DR-4`).
  - Implemented dynamic sensitive transfer label: for amounts $> \$1,000.00$, button displays *"Verify & Transfer ($X,XXX.XX)"* and renders an amber sensitivity notice (`FR-8`, `UX-DR-4`).
- **Dashboard Workspace Integration**:
  - Updated `frontend/src/App.tsx` to arrange the layout into the 2-column workspace specified in `DESIGN.md` and `EXPERIENCE.md` (Transfer Action Panel on the left, account activity placeholder on the right).
- **Automated Verification**:
  - Added 7 unit and integration tests in `frontend/src/test/TransferForm.test.tsx` covering all Story 2.1 acceptance criteria, integer conversions, and form submission callbacks.
  - All 15 frontend tests pass (`vitest`).
  - All 8 backend tests pass (`pytest`).
  - TypeScript compilation and Vite build verified (`tsc && vite build`) with 0 errors.
