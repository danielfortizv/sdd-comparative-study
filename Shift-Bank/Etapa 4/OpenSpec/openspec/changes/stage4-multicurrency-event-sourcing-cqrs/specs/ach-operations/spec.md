## Purpose

Defines currency-aware simulated ACH operations and their pending, settlement, and failure transitions under exactly-once financial effects.

## ADDED Requirements

### Requirement: USD-only ACH and single-debit lifecycle
ACH MUST originate only from a USD account. An accepted ACH operation MUST debit its source exactly once when it enters pending; settlement MUST NOT debit again. A failed pending ACH MUST refund exactly once. An ACH operation awaiting MFA MUST have no debit until authorized and accepted.

#### Scenario: Non-USD ACH is rejected
- **WHEN** ACH is requested from an EUR or GBP account
- **THEN** the request is rejected with no debit, pending transfer, event-posting effect, or version increment

#### Scenario: Pending ACH settles
- **WHEN** an accepted USD ACH changes from pending to settled
- **THEN** settlement records its outcome without another debit and preserves the original accepted operation

#### Scenario: Pending ACH fails
- **WHEN** an accepted pending ACH fails
- **THEN** exactly one refund event credits the source once and subsequent processing or replay cannot refund again

#### Scenario: ACH awaits MFA
- **WHEN** a USD ACH operation exceeds the D-07 MFA threshold and awaits confirmation
- **THEN** it remains unaccepted and undebited until valid confirmation rechecks balance, limits, expected version, and idempotency state
