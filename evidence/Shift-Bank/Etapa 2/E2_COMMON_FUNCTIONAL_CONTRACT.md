# Shift Bank — Stage 2 Common Functional Contract

Version: 1.0 DRAFT · Prepared: 2026-11-14
Status: Proposed forward-looking alignment contract; approval pending.
Scope: Option A — ACH transfers to third parties, recurring payments, and dynamic limits.
Audience: All remaining SDD tools. This describes behavior, NOT a reference implementation.

This contract operationalizes the three Stage 2 features selected in the official project matrix. It has been derived from the researcher's existing Stage 2 alignment document. It must not be misrepresented as a seed supplied to earlier experiments.

## 1. Inherited Stage 1 is authoritative

Each tool extends its own Stage 1 implementation and preserves its existing balances, transaction history, currency, mocked MFA rules, and technical architecture. Registration and real login are outside scope. Differences between tools are experimental data and must be recorded; never silently overwrite a tool's Stage 1 to match another implementation.

## 2. ACH and beneficiaries

| ID | Verifiable behavior |
|---|---|
| ACH-01 | The mock user can select an existing saved beneficiary or provide an ad hoc recipient for a third-party ACH transfer. |
| ACH-02 | Saved beneficiaries belong to the mock user; creation, retrieval and management cannot expose another user's data. |
| ACH-03 | Both recipient types contain name, bank, routing_number (exactly 9 numeric digits), and account number (4–17 numeric digits). Validate format only; do not contact an external bank. |
| ACH-04 | The transfer amount is positive and has at most two decimal places; source account exists, funds are sufficient, and all effective limits are met. |
| ACH-05 | A newly accepted ACH transfer is recorded as `pending`, immediately debits the source account and appears as pending in history. |
| ACH-06 | Autonomous settlement advances an eligible transfer from `pending` to `settled` with settlement timestamp; settlement must not debit again. |
| ACH-07 | A failed ACH transfer becomes `failed` and refunds the exact previously debited amount once. An additional compensating ledger entry is not a mandatory public contract. |
| ACH-08 | Duplicate state transitions or ordinary reprocessing cannot produce double debit or double refund; persisted balance and transfer records remain consistent. |
| ACH-09 | The UI clearly differentiates internal and ACH transfers, supports saved/ad hoc beneficiaries, an option to save and transfer status visibility. |
| ACH-10 | Invalid routing input is flagged during entry, before submission, and prevents submission until valid. |

The ACH workflow is a simulation, not a real clearing network or external ABA validation. If a test-trigger endpoint is proposed, it must be explicitly classified as a test-only mechanism, not a required public endpoint.

## 3. Recurring payments

| ID | Verifiable behavior |
|---|---|
| REC-01 | Create a recurring internal or ACH payment with a valid source, destination and amount. |
| REC-02 | Daily, weekly and monthly periods mean increments of 1, 7 and 30 days, respectively, for the common acceptance contract; a 30-day interval is not a calendar month. |
| REC-03 | A new schedule starts as `active`. |
| REC-04 | A supplied valid future start date is the first due date. If omitted, the first execution is due after one full configured interval, never immediately on creation. |
| REC-05 | A scheduler/automatic process executes active due schedules without a fresh human action for each cycle. |
| REC-06 | Support pausing active schedules, resuming paused schedules and cancelling schedules. |
| REC-07 | Cancellation is terminal: a `cancelled` schedule cannot return to `paused` or `active`; invalid state transitions are rejected without mutation. |
| REC-08 | `paused` and `cancelled` schedules are never executed, even after their due date. |
| REC-09 | Preserve the inherited PIN/MFA scheme: sensitive recurring payments are authorized at schedule creation; automatic runs do not request an interactive PIN. Recheck balance and limits at every run. |
| REC-10 | If a due execution fails (e.g. insufficient funds or limits), record the failure and advance the next due date so the schedule is not stuck. |
| REC-11 | A saved ACH recipient's removal must not make an already-authorized scheduled payment unusable; schedules retain sufficient destination data. |
| REC-12 | The UI lists schedule status and next due date, supports creation and pause/resume/cancel and displays understandable feedback. |

Use a consistent, documented time convention; UTC internally and explicit offsets in API payloads are recommended, provided inherited API compatibility is preserved. No particular public administrative scheduler-trigger endpoint is required.

## 4. Dynamic limits

| ID | Verifiable behavior |
|---|---|
| LIM-01 | Provide a per-transfer maximum and a cumulative daily maximum for the mock user. |
| LIM-02 | Both limits can be viewed and edited in the UI, displaying current values and optionally today's consumption and remaining availability. |
| LIM-03 | Reject transfers exceeding the per-operation limit, regardless of funds or correct MFA. |
| LIM-04 | Reject transactions exceeding daily usage computed from both internal and ACH transfers. |
| LIM-05 | Exactly reaching either the per-transfer limit or available daily limit is allowed when all other checks pass. |
| LIM-06 | Use a documented UTC day boundary; count internal completed transfers and ACH `pending`/`settled`, but exclude ACH `failed` after refund. Avoid double-counting transitions. |
| LIM-07 | Check limits before completing MFA authorization. A correct PIN never overrides a limit. |
| LIM-08 | Re-evaluate current limits and available balance when each recurring payment executes. |
| LIM-09 | Reject invalid limit updates or amounts, including negative values or monetary precision beyond the documented contract. |

Initial/default limit values must be approved for the currency of each inherited E1. Do NOT silently import USD amounts into a COP-based application. Currency-normalization decisions must be recorded prospectively if tools differ.

## 5. Inherited banking invariants

| ID | Invariant |
|---|---|
| HER-01 | Accounts, balances, history and existing Stage 1 queries continue to work. |
| HER-02 | Internal transfers and their debit/credit transaction records remain correct. |
| HER-03 | Preserve that tool's own E1 PIN, MFA threshold, errors, challenge expiration and lockout behavior. |
| HER-04 | Sensitive direct ACH transfers require the inherited MFA checks, after transfer-limit checks. |
| HER-05 | Business and persistence failures must not leave inconsistent financial balances or transaction states. |
| HER-06 | Keep the already-authenticated mock-user scope: no registration, real authentication, real bank API or Stage 3 functionality. |

## 6. Shared acceptance scenarios (external evaluation)

| ID | Scenario |
|---|---|
| A01 | Stage 1 accounts, balances and history remain available. |
| A02 | Valid internal transfer preserves balance/movement invariants. |
| A03 | Create, retrieve and use a valid saved beneficiary for ACH. |
| A04 | Valid ad hoc ACH, optionally saving the beneficiary. |
| A05 | Reject 8-digit and nonnumeric routing; accept 9 numeric digits; verify immediate UI feedback. |
| A06 | Reject 3-digit/18-digit account numbers; accept 4–17 digits. |
| A07 | ACH pending immediately debits once; settlement updates state, not funds. |
| A08 | Failed ACH refunds once and records failed state even if a transition is retried. |
| A09 | Reject zero/negative amounts and monetary amounts with more than two decimals. |
| A10 | View and edit limits; an approved change affects subsequent transfers. |
| A11 | Reject above per-transfer maximum; permit an exactly-equal amount with sufficient funds. |
| A12 | With daily limit 1000 and adequate per-transfer limit, 400 + 300 + 300 succeeds; the next 10 fails. Use a fresh isolated fixture; amount units can follow the tool's E1 currency. |
| A13 | Preserve E1 MFA threshold boundaries, wrong PIN and lockout behavior. |
| A14 | Correct PIN cannot bypass per-transfer or daily limits. |
| A15 | Daily schedule without start date first runs after a day, not immediately. |
| A16 | Weekly and monthly schedules follow the agreed 7/30-day intervals. |
| A17 | Both internal and ACH schedules can execute when due, updating movements, balance and next run. |
| A18 | Paused schedules do not run; resumed schedules become eligible; cancelled is terminal. |
| A19 | Insufficient funds/limit failure is logged and schedule advances without debit. |
| A20 | All inherited E1 tests, new tests and frontend build execute; preserve real outputs. |
| A21 | Manual browser inspection checks navigation, forms, validation, status and schedule controls; report what was actually observed. |

The acceptance IDs are scenarios, not a prescribed count of automated tests. Record PASS / FAIL / NOT VERIFIED and evidence. Keep internal implementation choices, endpoints, files and test frameworks appropriate to each tool and its inherited application.

## 7. Explicit exclusions and experimental integrity

- No code/spec copying from other SDD tools.
- No live ACH clearing, bank registration/login, real identity verification or production banking features.
- No forced endpoint to manually process due recurring payments.
- No prescribed number of generated spec files, lines of code, test cases or tool invocations.
- The seed, specification revisions, discussions, approvals, tests, failures, telemetry, hashes and static-analysis reports must be saved with truthful provenance.
