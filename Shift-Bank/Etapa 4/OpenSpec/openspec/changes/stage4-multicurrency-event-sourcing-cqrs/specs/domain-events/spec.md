## Purpose

Defines the durable append-only domain history that records monetary state transitions independently from the inherited security audit chain.

## ADDED Requirements

### Requirement: Durable append-only financial event history
Every committed financial transition MUST be recorded in a durable, ordered, append-only SQLite domain event store. Events MUST identify the account aggregate(s), operation, event type, event sequence, and exact currency-bearing amounts. The domain event store MUST remain distinct from the inherited HMAC audit log; an audit record MUST NOT be treated as a balance-posting domain event.

#### Scenario: Committed operation has durable events
- **WHEN** a financial command commits
- **THEN** its complete domain event set is durable, ordered, and sufficient to identify the resulting monetary transition

#### Scenario: Domain events cannot be overwritten
- **WHEN** an application request attempts to update or delete a committed domain event
- **THEN** the operation is rejected and the original event sequence remains unchanged

#### Scenario: Restart preserves events
- **WHEN** the application restarts after a committed operation
- **THEN** the same durable event history is available for query and deterministic replay

### Requirement: Compound event and account version semantics
A balance-affecting financial operation MUST record its complete compound transition atomically and increment each affected account version exactly once for that committed operation. Unaffected accounts and rejected operations MUST NOT have their versions incremented. A lifecycle event that does not change an account balance, such as successful ACH settlement after its accepted debit, MUST NOT increment an account version.

#### Scenario: Internal transfer increments each affected account once
- **WHEN** one internal transfer commits between two accounts
- **THEN** one compound financial transition is recorded and each of the two account versions increases by exactly one

#### Scenario: Rejected command does not increment versions
- **WHEN** a financial command fails validation before commit
- **THEN** no balance-posting event is committed and all account versions remain unchanged

#### Scenario: ACH settlement does not debit or increment account version
- **WHEN** an already accepted ACH settles successfully
- **THEN** settlement records the ACH outcome without another debit or account-version increment

#### Scenario: ACH refund increments the source version once
- **WHEN** an accepted ACH fails and its single refund is committed
- **THEN** the source account is credited once and its version advances exactly once for that refund operation
