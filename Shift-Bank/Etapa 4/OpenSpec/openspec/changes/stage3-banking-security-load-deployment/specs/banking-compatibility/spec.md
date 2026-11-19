## Purpose

Keep the completed Shift Bank E1/E2 banking behavior intact while Stage 3 security, audit, performance, and deployment capabilities are introduced.

## ADDED Requirements

### Requirement: Preserve inherited account and transaction behavior
Stage 3 MUST preserve the inherited mock authenticated user's two COP accounts, persisted balance updates, chronological transaction history, incoming/outgoing account filtering, decimal-safe amounts, self-transfer and insufficient-funds rejection, and current source-balance revalidation. Encryption and audit additions MUST NOT change existing banking API behavior for these operations.

#### Scenario: Account and history regression
- **WHEN** the inherited account and transaction-history flows are exercised before and after a valid internal transfer
- **THEN** persisted balances and chronological account-filtered history reflect the transfer with the existing response semantics

#### Scenario: Invalid transfer remains rejected
- **WHEN** a transfer is self-directed, non-positive, over precision, or exceeds available balance
- **THEN** it is rejected without unauthorized balance mutation and the existing API reports an understandable outcome

### Requirement: Preserve MFA, ACH, beneficiary, and limit semantics
Stage 3 MUST preserve inherited simulated MFA threshold of COP 1,000,000, code `123456`, five-minute expiration and retry semantics; beneficiary validation and encrypted external details; ACH pending, settlement, failure, refund, and history behavior; per-transfer and UTC daily limits including exact boundary behavior; and recurring payment authorization and execution semantics. Audit failure handling MUST NOT create a debit, duplicate refund, or skipped validation.

#### Scenario: Sensitive operation retains MFA behavior
- **WHEN** an inherited sensitive one-time transfer or recurring schedule is created and authorized
- **THEN** its existing MFA threshold, code, expiration, and activation/execution rules remain in force

#### Scenario: ACH and limit outcomes remain consistent
- **WHEN** inherited ACH lifecycle and transfer-limit boundary cases are exercised
- **THEN** acceptance, debit, settlement, failure refund, UTC usage, and recorded history remain consistent with Stage 2 contracts

### Requirement: Preserve recurring schedule lifecycle and restart safety
Stage 3 MUST preserve recurring schedule frequencies, UTC cadence, immutable financial terms, pause/resume/cancel behavior, current execution validations, idempotent occurrences, and restart recovery. Deployment MUST preserve the existing single-scheduler operational constraint.

#### Scenario: Recurring payment lifecycle regression
- **WHEN** a recurring payment is created, paused, resumed, cancelled, and processed across restart
- **THEN** its inherited cadence and state rules apply without duplicate or missed monetary effects

#### Scenario: Scheduler regression under deployed lifecycle
- **WHEN** the deployed service is restarted with due or partially processed schedules
- **THEN** one scheduler recovers due work using the inherited idempotent processing behavior
