## Why

Stage 1 supports only transfers between the mock user's two accounts and has no configurable transfer limits, external recipients, or scheduled payments. This change adds those capabilities while preserving the existing COP account, transfer, history, and MFA behavior.

## What Changes

- Add simulated ACH transfers to saved or ad hoc external recipients, including beneficiary management, deterministic pending-to-settled or failed outcomes, and persistent, idempotent settlement/refund behavior.
- Add recurring internal and ACH payment schedules with active, paused, and terminal cancelled states, creation-time MFA authorization, execution history, and recovery after restart.
- Add mock-user-configurable, strictly positive per-transfer and UTC daily limits, initialized to COP 5,000,000 and COP 10,000,000 respectively. Limit reductions apply immediately without reversing accepted transactions.
- Anchor recurring execution timestamps and cadence in UTC, display the timezone in the interface, and skip missed occurrences without shifting future dates.
- Extend account balances, transaction history, transfer, and MFA requirements to define the combined Stage 1 and Stage 2 behavior.
- Extend the frontend for limits, beneficiaries, internal versus ACH transfers, recurring schedules, and transfer/execution statuses.
- Introduce automated verification for new behavior and Stage 1 regression coverage; no automated Stage 1 test suite has been identified.

## Capabilities

### New Capabilities
- `ach-transfers`: Simulated external ACH transfers and user-owned beneficiary management.
- `recurring-payments`: Recurring internal and ACH schedules, execution records, and schedule controls.
- `transfer-limits`: User-configurable per-transfer and UTC daily accumulated transfer limits.

### Modified Capabilities
- `bank-accounts`: Display persisted balances after internal and ACH debits/refunds.
- `transfers`: Preserve internal transfers while enforcing shared limits and defining available-funds behavior across accepted ACH debits.
- `mfa`: Preserve the existing threshold, code, and expiry while including sensitive ACH transfers and recurring schedule creation.
- `transaction-history`: Include external ACH and recurring execution records, recipient snapshots, statuses, settlement times, and failure reasons.

## Impact

- Backend FastAPI endpoints and business rules for limits, beneficiaries, ACH, recurring schedules, execution, and recovery.
- SQLite persistence for user limits, beneficiaries, ACH transfer lifecycle and recipient snapshots, recurring schedules, and per-occurrence results.
- React/TypeScript dashboard, transfer forms, beneficiary and limit management, recurring schedule controls, and transaction history.
- Automated backend and frontend verification to cover new behavior, money-movement invariants, persistence recovery, and Stage 1 regressions. No application dependency change is assumed by this proposal.
