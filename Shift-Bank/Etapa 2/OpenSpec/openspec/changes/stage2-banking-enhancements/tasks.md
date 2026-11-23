## 1. Persistence and domain foundations

- [x] 1.1 Add repeatable SQLite schema initialization for persisted mock-user limits, beneficiaries, ACH transfer snapshots/states, recurring schedules, occurrence records, and financial completion/acceptance timestamps; verify initialization preserves existing Stage 1 account and transaction rows and does not reset configured limits.
- [x] 1.2 Add exact COP amount parsing/validation and UTC date/time helpers shared across transfer types; verify positive two-decimal boundary values and rejection of malformed, non-positive, and over-precision values.
- [x] 1.3 Add stable transfer and schedule-occurrence identities with database uniqueness/state constraints; verify repeated claims cannot create a second debit or execution.

## 2. Shared transfer limits and internal-transfer compatibility

- [x] 2.1 Implement persisted user-level defaults of COP 5,000,000 per transfer and COP 10,000,000 per UTC day plus read/update operations; verify strictly positive two-decimal validation, malformed/zero/negative rejection, valid update preservation, and immediate limit reductions below current usage without reversing history.
- [x] 2.2 Enforce per-transfer and shared UTC daily limits in backend internal transfer paths and MFA confirmation, counting each internal transfer once; verify exact-limit acceptance, over-limit rejection, current-limit revalidation after updates, UTC day rollover, no MFA bypass, no negative balance, and the Stage 1 insufficient-funds scenario with the per-transfer limit raised to COP 6,000,000 and sufficient daily allowance.
- [x] 2.3 Add frontend limit display and update interaction with validation feedback; verify saved values refresh, invalid inputs are explained and blocked, and a reduction below current usage is reflected immediately.

## 3. Beneficiaries and ACH lifecycle

- [x] 3.1 Implement mock-user beneficiary create/list/update/delete operations and format validation; verify routing-number and account-number boundaries and field-specific errors, and that edits/deletions leave captured recipient snapshots intact.
- [x] 3.2 Implement ad hoc and saved-beneficiary ACH submission with backend validation, limit checks, and existing MFA flow before acceptance; verify `PENDING_MFA`/`EXPIRED` transitions, no debit before successful MFA, invalid recipient/balance/precision/limit rejection, and concurrent requests cannot overdraw.
- [x] 3.3 Implement atomic ACH acceptance debit and pending state with captured recipient details; verify the source balance decreases once and the transaction is queryable as pending.
- [x] 3.4 Implement automatic normal settlement at 30 seconds with settlement timestamp and persisted restart recovery; verify settlement occurs without a second debit before/after restart and repeated processor runs are idempotent.
- [x] 3.5 Implement a controlled internal deterministic ACH failure mechanism and atomic failed-state/refund transition; verify failure is reproducible, machine-readable reason and comprehensible explanation are retained, accepted history and recipient details remain available, the exact debit is refunded once, and failed ACH is excluded from its original acceptance date's daily usage, including when failure occurs after UTC midnight.
- [x] 3.6 Add ACH and beneficiary frontend flows for transfer-type selection, saved/ad hoc recipient, optional save, beneficiary list/create/update/delete, live routing-number validation, backend validation errors, and lifecycle display; verify invalid routing blocks submission and internal versus ACH outcomes are distinguishable.

## 4. Recurring payment schedules and execution

- [x] 4.1 Implement persisted schedule creation with exact 1/7/30-day cadence, future date at 00:00 UTC or first-after-full-interval calculation, strict future-time validation, persistent first-occurrence cadence anchor, immutable financial terms, and creation-time MFA before activation where required; verify exact intervals, timestamps, no drift, `PENDING_MFA`/`EXPIRED` transitions, current per-transfer-limit revalidation before activation, rejection when MFA completes at/after the first execution timestamp, no resulting executable schedule/debit, schedule inactivity until valid MFA, and unchanged Stage 1 MFA contract.
- [x] 4.2 Implement active/paused/cancelled transitions, terminal cancellation, and preserved cadence on resume; verify paused/cancelled schedules do not execute, missed paused occurrences are skipped, and cancelled schedules cannot resume.
- [x] 4.3 Implement durable due-occurrence processing with stable logical identities, execution-time balance and limit revalidation, internal and ACH routing, and recorded failure with next occurrence advancement; verify failed balance/limit attempts do not debit or block later occurrences.
- [x] 4.4 Implement restart recovery that skips offline-missed occurrences but resumes accepted or partially processed occurrences; verify neither case is duplicated or incorrectly marked skipped.
- [x] 4.5 Add frontend schedule creation and MFA confirmation, UTC next execution time, validation errors, execution results and failure reasons, pause/resume/cancel controls, and immutable-term behavior; verify users see UTC clearly, can inspect states, and failures remain distinct from schedule status.

## 5. Accounts and transaction history integration

- [x] 5.1 Extend account and history queries/presentation for ACH debits/refunds, recipient snapshots, ACH settlement/failure state, and recurring execution outcomes while preserving existing internal history filters; verify pending debit and exactly one failed-ACH refund appear correctly.
- [x] 5.2 Verify daily usage integration across completed internal, pending/settled/failed ACH, and recurring executions; verify internal counts once on completion date, ACH counts once on acceptance date even when settlement crosses midnight, a failure on day D+1 removes the ACH amount from day D and never attributes it to D+1, repeated failure processing has no effect, failed and skipped occurrences do not count, MFA completion across midnight uses completion date, and exact UTC-day boundary behavior.

## 6. Automated verification and regression

- [x] 6.1 Introduce backend automated tests for limit settings and boundary enforcement, beneficiary validation, ACH MFA/settlement/failure/refund/idempotency, recurring scheduling/recovery/state transitions, and existing internal transfer/account/MFA behavior; verify the test suite passes without relying on pre-existing Stage 1 automated tests.
- [x] 6.2 Introduce automated frontend tests for transfer type distinction, beneficiary/routing validation, limit settings, recurring schedule controls, validation errors, and transaction statuses; verify the frontend test suite passes.
- [x] 6.3 Run the complete Stage 2 acceptance and Stage 1 regression verification against a clean seeded database and an existing Stage 1 database; record commands, observed outcomes, and any failures without claiming unrun tests.

## Requirement traceability index

This index maps every delta requirement to implementation and verification tasks. Tasks 1.1-1.3 provide persistence, monetary validation, and idempotency support; task 6.3 provides cross-capability regression evidence.

| Capability | Requirement | Tasks |
|---|---|---|
| `ach-transfers` | Manage user-owned beneficiaries | 3.1, 3.6 |
| `ach-transfers` | Submit simulated ACH transfer | 1.2, 3.2, 3.6 |
| `ach-transfers` | Authorize and accept sensitive ACH transfers | 3.2, 6.1 |
| `ach-transfers` | Settle or fail accepted ACH transfers idempotently | 1.1, 1.3, 3.3, 3.4, 3.5, 6.1 |
| `ach-transfers` | Display ACH status and recipient history | 3.6, 5.1, 6.2 |
| `transfer-limits` | Configure user transfer limits | 2.1, 2.3, 6.1, 6.2 |
| `transfer-limits` | Enforce per-transfer limit | 2.2, 3.2, 4.3, 6.1 |
| `transfer-limits` | Enforce accumulated UTC daily limit | 2.2, 4.3, 5.2, 6.1 |
| `recurring-payments` | Create recurring payment schedule | 4.1, 4.5, 6.1 |
| `recurring-payments` | Authorize sensitive recurring schedule at creation | 4.1, 6.1 |
| `recurring-payments` | Manage schedule states and immutable terms | 4.2, 4.5, 6.1, 6.2 |
| `recurring-payments` | Execute due occurrences with current validations | 4.3, 5.2, 6.1 |
| `recurring-payments` | Recover schedules and occurrences safely | 1.1, 1.3, 4.4, 6.1 |
| `recurring-payments` | Display recurring schedules and executions | 4.5, 5.1, 6.2 |
| `bank-accounts` | Display accounts and balances | 5.1, 6.3 |
| `transfers` | Transfer between own accounts | 2.2, 5.2, 6.1, 6.3 |
| `transfers` | Validate transfers and reject invalid requests | 1.2, 2.2, 6.1, 6.3 |
| `transfers` | Source balance revalidation on confirmation | 2.2, 3.2, 4.3, 6.1 |
| `mfa` | Preserve MFA contract across transfer types | 3.2, 4.1, 6.1, 6.3 |
| `mfa` | Authorize sensitive recurring schedules at creation | 4.1, 6.1 |
| `transaction-history` | Chronological ledger of movements | 3.6, 4.5, 5.1, 6.2, 6.3 |
| `transaction-history` | Show both incoming and outgoing movements for each account | 5.1, 6.1, 6.3 |
