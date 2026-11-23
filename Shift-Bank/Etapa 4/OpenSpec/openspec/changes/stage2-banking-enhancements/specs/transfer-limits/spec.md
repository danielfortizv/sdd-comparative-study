## Purpose

Defines user-controlled limits that constrain all internal, ACH, and recurring transfers consistently and transparently.

## ADDED Requirements

### Requirement: Configure user transfer limits
The system MUST provide the authenticated mock user with a configurable maximum amount per individual transfer and maximum accumulated transfer amount per UTC calendar day. Both limits MUST be strictly positive monetary values with no more than two decimal places. Initial values MUST be COP 5,000,000 per transfer and COP 10,000,000 per UTC day. Limits are shared across the user's accounts and transfer types, and users MUST be able to view and update both values through the application interface.

#### Scenario: View initial transfer limits
- **WHEN** the user opens transfer limit settings before changing either limit
- **THEN** the application displays a COP 5,000,000 per-transfer limit and a COP 10,000,000 UTC daily limit

#### Scenario: Update valid limits
- **WHEN** the user submits positive limit values with no more than two decimal places
- **THEN** the system persists both limits for the mock user and displays the updated values

#### Scenario: Reject invalid limit update
- **WHEN** the user submits a zero or negative, malformed, or more-than-two-decimal limit
- **THEN** the system rejects the update, preserves the previously saved limits, and displays an understandable validation error in the interface

#### Scenario: Reduce daily limit below current usage
- **WHEN** the user lowers the daily limit below the amount already used during the current UTC day
- **THEN** the system saves the new limit immediately without reversing or modifying accepted transactions, retains accurate usage, and rejects further transfers until sufficient daily capacity is available

### Requirement: Enforce per-transfer limit
The system MUST enforce the configured maximum amount on every internal transfer, ACH transfer, and recurring payment execution in the backend. An amount equal to the configured limit is allowed when all other checks pass. MFA authorization MUST NOT override this limit.

#### Scenario: Transfer equals per-transfer limit
- **WHEN** the user requests a transfer exactly equal to the configured per-transfer limit and all other checks pass
- **THEN** the system allows the transfer to continue through the applicable execution or MFA flow

#### Scenario: Transfer exceeds per-transfer limit
- **WHEN** an internal, ACH, or recurring transfer exceeds the configured per-transfer limit
- **THEN** the backend rejects that transfer without an unauthorized debit, even if a valid MFA code is supplied

### Requirement: Enforce accumulated UTC daily limit
The system MUST enforce the shared accumulated transfer limit across the mock user's internal transfers, ACH transfers, and recurring payment executions using UTC calendar days. Attribute internal transfer usage to the UTC date when the transfer completes and ACH usage to the UTC date when it is accepted; later ACH settlement MUST NOT move the usage to another date. The amount that brings usage exactly to the daily limit MUST be allowed. Each internal transfer MUST count once. Each ACH transfer MUST count once while pending or settled and failed ACH transfers MUST be excluded. Skipped recurring occurrences MUST NOT consume usage.

#### Scenario: Transfer reaches daily limit exactly
- **WHEN** a transfer makes that UTC day's accumulated usage equal to the configured daily limit
- **THEN** the system allows the transfer if its other validations pass

#### Scenario: Transfer exceeds remaining daily allowance
- **WHEN** a transfer would make accumulated usage exceed the configured daily limit
- **THEN** the backend rejects the transfer without a debit

#### Scenario: Daily limit resets at UTC day boundary
- **WHEN** a new transfer is evaluated after the UTC calendar day changes
- **THEN** only qualifying usage from the new UTC day is included in the daily total

#### Scenario: MFA completion determines internal transfer usage date
- **WHEN** an internal transfer initiated before UTC midnight completes after UTC midnight
- **THEN** its amount counts once toward the UTC day on which it completes

#### Scenario: ACH settlement does not change usage date
- **WHEN** an ACH transfer is accepted before UTC midnight and settles after UTC midnight
- **THEN** its amount remains counted once on the UTC day it was accepted and is not counted again on the settlement day

#### Scenario: Internal transfer counts once
- **WHEN** an internal transfer completes between the user's two accounts
- **THEN** its amount contributes once, not once per debit and credit, to that UTC day's usage

#### Scenario: Failed ACH is excluded
- **WHEN** an accepted ACH transfer transitions to failed and its debit is refunded
- **THEN** its amount is excluded from accumulated daily usage

#### Scenario: ACH failure after UTC midnight reverses usage on acceptance date
- **WHEN** an ACH transfer is accepted and debited shortly before UTC midnight on day D, remains pending across midnight, then fails deterministically when settlement processing runs on day D+1 and failure processing is repeated
- **THEN** its amount counts once on day D while pending, the original debit is refunded exactly once, the failed amount is removed from day D usage, no amount is attributed to day D+1 because of the failure, and repeated processing changes neither account balances nor daily usage again

#### Scenario: Pending ACH counts once through settlement
- **WHEN** an accepted ACH transfer changes from `pending` to `settled`
- **THEN** its amount counts once toward its acceptance UTC day before and after settlement

#### Scenario: Recurring execution uses current limits
- **WHEN** an active recurring schedule becomes due
- **THEN** the system checks the currently configured per-transfer and UTC daily limits before accepting that occurrence

#### Scenario: Recurring execution affects daily usage once
- **WHEN** a recurring internal transfer completes or a recurring ACH transfer is accepted
- **THEN** its amount counts once toward daily usage, while a failed execution without an accepted transfer consumes no usage

#### Scenario: Pending MFA revalidates current limits
- **WHEN** a transfer awaiting MFA is confirmed after a limit update or other transfer changes current daily capacity
- **THEN** the backend evaluates the current limits and usage and rejects completion without a debit if either limit would be exceeded
