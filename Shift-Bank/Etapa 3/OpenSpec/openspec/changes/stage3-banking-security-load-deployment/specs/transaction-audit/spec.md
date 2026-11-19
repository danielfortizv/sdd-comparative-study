## Purpose

Maintain an append-only record of financial attempts and outcomes whose ordering and integrity can be independently verified against unauthorized changes within the stated threat model.

## ADDED Requirements

### Requirement: Append-only audit of financial operations
The system MUST append an audit event for successful, rejected, and failed financial operations, including internal transfers, ACH operations, recurring executions, and relevant authorization or validation outcomes. Events MUST include an unambiguous operation identity, event time, outcome, and sufficient non-secret context to explain the result. Corrections MUST be represented by later events; existing audit events MUST NOT be updated or deleted through application operations.

#### Scenario: Successful transfer has corresponding audit events
- **WHEN** an internal transfer completes
- **THEN** immutable audit events record the attempt and successful financial outcome with a unique operation identity

#### Scenario: Rejected and failed operations remain auditable
- **WHEN** a transfer is rejected by validation or fails during processing
- **THEN** the audit records its outcome and safe reason without recording secrets or implying a financial mutation that did not occur

### Requirement: Cryptographic verification and protected administration
Audit entries MUST be cryptographically linked in a verifiable ordered chain. Verification MUST detect alteration, deletion, insertion, or reordering within the retained chain. Administrative verification and any chain reset or key-management action MUST require separately protected authorization, and verification MUST report the first invalid link or an explicit valid result. The immutability guarantee applies against ordinary application-level modification and database-only tampering when the attacker lacks the audit integrity secret; an operator controlling the database, application, and all cryptographic secrets is outside the absolute guarantee.

#### Scenario: Verification detects altered audit history
- **WHEN** an audit entry or chain link is changed, deleted, inserted, or reordered without the integrity secret
- **THEN** verification reports an integrity failure identifying the affected chain position

#### Scenario: Authorized verification succeeds
- **WHEN** an authorized administrator requests verification of an intact audit chain
- **THEN** the system reports that the checked chain is valid and identifies its covered range

#### Scenario: Unauthorized verification is refused
- **WHEN** a caller without administrative verification authorization requests chain verification or reset
- **THEN** the request is denied and the audit state is unchanged

### Requirement: Atomic financial mutation and required audit event
Every successful financial mutation that requires an audit event MUST commit atomically with that event. If the required audit event cannot be persisted, the financial mutation MUST NOT commit. Rejection and failure events MUST be recorded when possible; an audit persistence failure MUST fail safely, must not authorize or report an unrecorded successful operation, and must not leave an unauthorized partial financial mutation.

#### Scenario: Audit persistence failure prevents financial commit
- **WHEN** a required success event cannot be persisted during a transfer
- **THEN** the transfer's debit and credit are rolled back and the operation is not reported as successful

#### Scenario: Failure is recorded without partial mutation
- **WHEN** a financial attempt fails before commit and audit persistence is available
- **THEN** its failure event is committed while balances and transfer-limit usage remain unchanged

### Requirement: Multiprocess audit and SQLite consistency
Audit appends and financial updates MUST remain serialized and consistent across concurrent application processes using SQLite. Concurrent writers MUST not fork or reuse chain positions, lose committed events, or produce duplicate monetary effects. SQLite reader/writer contention MUST have bounded, explicit behavior; exhausted lock retries or persistence errors MUST fail safely without partial financial mutation.

#### Scenario: Concurrent processes append and transfer
- **WHEN** multiple backend processes concurrently execute transfers and append audit events against the same SQLite database
- **THEN** all committed mutations have exactly one matching chain event, the chain verifies, and balances and limits reflect only committed operations

#### Scenario: SQLite writer contention exceeds available retry window
- **WHEN** a writer cannot acquire SQLite write access within the defined bounded retry policy
- **THEN** that operation fails without partial financial effects or a success response

#### Scenario: Readers observe consistent committed state
- **WHEN** a reader queries balances, history, or audit data while another process commits a transaction
- **THEN** it observes a consistent committed snapshot and never observes half of an atomic financial-and-audit change
