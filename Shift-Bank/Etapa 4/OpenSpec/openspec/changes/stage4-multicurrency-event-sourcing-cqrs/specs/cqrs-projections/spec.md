## Purpose

Defines synchronous query views derived from financial events and their deterministic reconstruction and integrity behavior.

## ADDED Requirements

### Requirement: Synchronous atomic CQRS projections
State-changing commands and balance/history queries MUST use logically separate write and read models. A successful command MUST make its complete event set and affected query projections visible atomically before success is returned. Readers MUST observe either the prior committed state or the complete new state, never a partial compound operation.

#### Scenario: Query after successful command
- **WHEN** a command returns success
- **THEN** a subsequent account and history query reflects all of that command's committed effects

#### Scenario: Projection write failure
- **WHEN** any required projection update fails during a financial command
- **THEN** the event, account effects, audit outcome, and idempotency result do not partially commit

### Requirement: Deterministic projection rebuild and fail-closed inconsistency handling
The system MUST rebuild projections deterministically from the durable domain event sequence and MUST compare rebuilt state with persisted projections. If event order, sequence, integrity, or reconciliation is inconsistent, the system MUST fail closed for affected financial reads and writes rather than serve or mutate an ambiguous balance.

#### Scenario: Rebuild reproduces the committed projection
- **WHEN** projections are rebuilt from an intact event history
- **THEN** rebuilt balances, currencies, account versions, and history equal the committed query state

#### Scenario: Corrupt or incomplete event history
- **WHEN** replay detects a gap, duplicate sequence, invalid event, or balance mismatch
- **THEN** affected financial reads and writes fail safely and report a nonsensitive integrity error without changing financial state
