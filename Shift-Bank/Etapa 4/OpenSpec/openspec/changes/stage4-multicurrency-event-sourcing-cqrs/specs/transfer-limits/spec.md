## Purpose

Defines operation and UTC daily limits consistently across supported currencies and fixes the Stage 4 MFA comparison boundary.

## ADDED Requirements

### Requirement: USD-equivalent operation and daily limits
The system MUST enforce a maximum operation amount of USD 5,000.00 equivalent and a maximum daily total of USD 10,000.00 equivalent. USD equivalents MUST use the approved exact rational D-03 rates without rounding for comparison. The same logical operation MUST contribute to daily use once: an accepted pending ACH counts at acceptance; settlement does not count again; a failed and refunded ACH is excluded from final usage. Current-day usage MUST use UTC day boundaries.

#### Scenario: Operation limit boundary
- **WHEN** an operation's exact USD equivalent is USD 5,000.00
- **THEN** it satisfies the per-operation limit, subject to other validations

#### Scenario: Operation exceeds limit
- **WHEN** an operation's exact USD equivalent is greater than USD 5,000.00
- **THEN** it is rejected without a financial effect

#### Scenario: Daily usage counts a logical operation once
- **WHEN** a successful internal transfer, FX conversion, recurring occurrence, or accepted ACH is recorded during a UTC day
- **THEN** the operation contributes its USD-equivalent amount once and settlement or exact request replay does not add usage

#### Scenario: Daily boundary and failed ACH
- **WHEN** a request occurs across UTC midnight or an ACH fails and is refunded
- **THEN** usage is assigned to its approved acceptance/commit UTC day, and a failed-refunded ACH does not remain in daily consumption

### Requirement: Preserve configurable limits within D-07 ceilings
The system MUST preserve the inherited ability to configure effective per-transfer and daily limits, with each configured amount represented as an explicit USD-equivalent value, greater than zero, and no higher than the D-07 ceilings. A limit update MUST affect subsequent validation without changing completed operations or retroactively changing already-recorded usage.

#### Scenario: Lower configurable limits take effect
- **WHEN** an authorized limit update sets positive per-transfer and daily values within the D-07 ceilings
- **THEN** the effective values are returned with USD currency and subsequent commands are checked against them

#### Scenario: Configured limit cannot exceed a D-07 ceiling
- **WHEN** a limit update attempts to set a per-transfer value above USD 5,000.00 or daily value above USD 10,000.00
- **THEN** the update is rejected and the prior effective limits remain unchanged

### Requirement: Migrate persisted user limits deterministically
The migration MUST convert each persisted per-user COP per-transfer and daily limit independently using the approved one-time rate of 4,000 COP per USD. It MUST calculate the exact quotient, round once to USD cents using ROUND_HALF_UP, then cap the result at USD 5,000.00 per transfer or USD 10,000.00 daily, as applicable. The effective result MUST be at least USD 0.01; a result below that minimum MUST fail closed and MUST NOT be rounded upward. The migration MUST record the source COP value, rate, exact quotient, rounded value, effective capped value, rounding residual, and cap adjustment for each setting. Missing, malformed, conflicting, or unreconcilable source settings MUST abort before financial mutation. The migration MUST be atomic and idempotent for the same identified source snapshot, MUST NOT convert an already migrated USD value again, and MUST NOT roll back over subsequent limit changes.

#### Scenario: Convert inherited default limits
- **WHEN** the source user has the inherited per-transfer limit of COP 5,000,000.00 and daily limit of COP 10,000,000.00
- **THEN** the migrated limits are USD 1,250.00 and USD 2,500.00 respectively, with exact conversion provenance recorded

#### Scenario: Convert configured limits independently per user
- **WHEN** a user has configured per-transfer COP 4,000,000.00 and daily COP 9,000,000.00 limits
- **THEN** the migrated limits are USD 1,000.00 and USD 2,250.00 respectively, without replacing them with global defaults

#### Scenario: Apply the minimum positive limit without rounding upward
- **WHEN** a source setting of COP 20.00 converts to USD 0.005 before rounding
- **THEN** the effective limit is USD 0.01
- **WHEN** a source setting of COP 10.00 converts to USD 0.0025 and rounds to USD 0.00
- **THEN** migration aborts before financial mutation and records a safe blocking reason

#### Scenario: Cap converted limits at D-07 ceilings
- **WHEN** a per-transfer source limit of COP 25,000,000.00 or daily source limit of COP 50,000,000.00 is converted
- **THEN** the effective limits are capped at USD 5,000.00 and USD 10,000.00, and the pre-cap values and cap adjustments are recorded

#### Scenario: Repeat the same limit migration idempotently
- **WHEN** the same identified migration batch is retried against an unchanged source snapshot
- **THEN** it has no additional setting, event, audit, or version effect, while a changed source setting fails closed

#### Scenario: Protect subsequent limit changes during rollback
- **WHEN** a post-cutover limit update exists and rollback is requested
- **THEN** rollback does not overwrite the subsequent update and fails closed if a safe restoration cannot be proven
