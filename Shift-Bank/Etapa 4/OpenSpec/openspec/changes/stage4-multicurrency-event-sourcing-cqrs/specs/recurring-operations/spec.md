## Purpose

Defines currency-safe recurring internal transfers and ACH while preserving the inherited schedule lifecycle and restart behavior.

## ADDED Requirements

### Requirement: Currency-compatible recurring schedules
Recurring internal transfers MUST use source and destination accounts with the same currency. Recurring ACH MUST originate only from a USD account. Unsupported currency combinations MUST be rejected before schedule activation.

#### Scenario: Same-currency recurring internal schedule
- **WHEN** an internal recurring schedule is created between accounts of the same supported currency
- **THEN** the schedule records that currency and each execution uses same-currency transfer rules

#### Scenario: Cross-currency recurring internal schedule is rejected
- **WHEN** a recurring internal schedule uses different source and destination currencies
- **THEN** schedule creation is rejected without an active schedule or financial effect

#### Scenario: Recurring ACH requires USD
- **WHEN** a recurring ACH schedule is requested from a non-USD account
- **THEN** schedule creation is rejected without an ACH obligation

### Requirement: Exactly-once occurrence processing and lifecycle continuity
Each scheduled occurrence MUST have a deterministic unique identity and MUST produce at most one financial effect across concurrent workers, retries, or restart. Existing daily/weekly/30-day monthly cadence, UTC anchor, pause/resume/cancel behavior, authorization rules, and missed-occurrence recovery semantics MUST remain observable unless explicitly changed by an approved Stage 4 requirement. Paused and terminal schedules MUST NOT execute.

#### Scenario: Concurrent workers process one occurrence
- **WHEN** multiple workers attempt the same due schedule occurrence
- **THEN** exactly one occurrence is committed and no duplicate debit, credit, ACH, event, or version increment occurs

#### Scenario: Restart recovers due work
- **WHEN** the scheduler restarts with a due active schedule
- **THEN** inherited recovery behavior advances the cadence without duplicate execution and records an auditable outcome

#### Scenario: Paused or cancelled schedule is not executed
- **WHEN** a schedule is paused or cancelled while its prior next-run time is due
- **THEN** no financial occurrence is created until a permitted explicit resume, and a cancelled schedule remains terminal
