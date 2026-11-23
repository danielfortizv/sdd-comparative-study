---
name: Event Sourcing and CQRS Architecture
description: Durable append-only SQLite domain event store, dynamic legacy state migration, event-backed historical replay, synchronous read projections, dual-version tracking, and integrity-verified rebuild capabilities
targets:
  - ../backend/app/models.py
  - ../backend/app/services/event_store.py
  - ../backend/app/services/projection_service.py
  - ../backend/app/services/migration_service.py
---

# Event Sourcing and CQRS Architecture

Defines the event-sourced monetary account and transaction domain and the Command Query Responsibility Segregation (CQRS) architecture for Shift Bank Stage 4.

Governed by Researcher Decisions D-01, D-02, D-03, D-05, D-06, D-09, D-12, and D-14 and SEED-4 Items 1, 3, 4, 5, and 6.

## Data Contract

```python
from decimal import Decimal
from typing import Optional, List, Dict, Any

class DomainEventRecord(BaseModel):
    id: int                            # Monotonically increasing sequence ID
    event_id: str                      # Unique UUID v4 identifier
    event_type: str                    # "AccountStateImported" | "LegacyTransactionImported" | "AccountOpened" | "InternalTransferCompleted" | "CurrencyConversionCompleted" | "AchTransferInitiated" | "AchTransferSettled" | "AchTransferFailed"
    aggregate_id: str                  # Aggregate root identifier (e.g. "banking:{user_id}")
    aggregate_version: int             # Monotonic version within aggregate
    account_ids: List[int]             # Affected account IDs for multi-account indexing
    payload: Dict[str, Any]            # Structured JSON domain event payload with exact Decimal string amounts (sensitive fields encrypted with AES-256-GCM)
    correlation_id: Optional[str]      # Operation correlation identifier
    idempotency_key: Optional[str]     # Client or scheduler idempotency UUID
    created_at: datetime               # UTC ISO-8601 timestamp

class ProjectionCheckpoint(BaseModel):
    projection_name: str               # e.g., "account_balances", "transaction_history"
    last_applied_event_id: int         # Last sequence ID applied
    updated_at: datetime
```

## Append-Only SQLite Domain Event Store

- Dedicated Event Table: An append-only SQLite table named `domain_events` stores all monetary domain events. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Immutability Protection: `UPDATE` and `DELETE` operations on `domain_events` are strictly prohibited via database triggers and application guards. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Separation from Audit Ledger: The `domain_events` store is completely distinct from the Stage 3 HMAC-SHA256 `audit_logs` ledger. Domain events represent authoritative monetary state transitions; audit logs provide compliance and security tracing. [NEW D-05, D-11]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Global Ordering & Uniqueness: Events have a strictly monotonically increasing primary key `id` guaranteeing deterministic replay order. `event_id` is enforced as unique. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`

## Event Types, Boundaries & Dual-Version Tracking

- Atomic Multi-Account Operations: Operations affecting two accounts (internal transfers and currency conversions) are recorded as ONE compound domain event representing the entire business operation [NEW D-09]:
  - `InternalTransferCompleted`: records `from_account_id`, `to_account_id`, `currency`, exact Decimal `amount`, `from_account_version` (incremented by +1), `to_account_version` (incremented by +1).
  - `CurrencyConversionCompleted`: records `from_account_id`, `to_account_id`, `source_currency`, `destination_currency`, exact Decimal `source_amount`, exact Decimal `destination_amount`, `exchange_rate_display`, `rate_numerator`, `rate_denominator`, `rate_version`, `rounding_residual`, `from_account_version` (incremented by +1), `to_account_version` (incremented by +1).
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Single Account & Lifecycle Events:
  - `AccountStateImported`: records dynamically imported baseline balance (exact Decimal), currency, account number, account type, account name, and initial version (`1`) for each inherited account found in database. [NEW D-05]
  - `LegacyTransactionImported`: records an immutable, non-balance-changing snapshot of each inherited Stage 3 transaction row (id, account_id, transfer_id, transaction_type, amount, balance_after, description, reference, created_at). [NEW D-05]
  - `AccountOpened`: records newly provisioned account details with initial zero Decimal balance and initial version (`1`). [NEW D-02, D-05]
  - `AchTransferInitiated`: records immediate debit and pending external settlement state, advancing source account version. [NEW D-09, D-14]
  - `AchTransferSettled`: records successful external settlement state transition without extra debit or version advance. [NEW D-09]
  - `AchTransferFailed`: records external settlement failure and exact refund credit, advancing source account version. [NEW D-09, D-14]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Dual-Version Reconstruction Rules: When folding events during replay or rebuilding:
  - If event has account `A` as `from_account`, `A`'s balance is debited and its version is updated to `from_account_version`.
  - If event has account `A` as `to_account`, `A`'s balance is credited and its version is updated to `to_account_version`.
  - For single-account events (`AccountStateImported`, `AccountOpened`, `AchTransferInitiated`, `AchTransferFailed`), `A`'s version is updated to the recorded `account_version`.
  - Replaying compound events independently advances both affected account versions without ambiguity. [NEW D-09, D-14]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`

## Dynamic Legacy State Migration & Event-Backed Historical Replay

- Dynamic Baseline Discovery: Migration dynamically queries the existing `accounts` and `transactions` tables at runtime. It must NEVER hardcode baseline balances. It reads the exact persisted balance, currency, account number, name, and type for all existing accounts. [MODIFIED D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Account State Import: For each existing account, emits an `AccountStateImported` event with its actual persisted Decimal balance and version 1. Never resets previously modified balances. [MODIFIED D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Historical Transaction Event Capture: For each existing transaction record in `transactions`, emits a `LegacyTransactionImported` event to `domain_events`. These events are explicitly marked as non-balance-changing so that full projection rebuilds reconstruct all historical transaction history rows without altering account balances. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- New Currency Account Provisioning: Emits `AccountOpened` events with `0.00` balance for `Euro Account` (`EUR-3001`, EUR) and `British Pound Account` (`GBP-4001`, GBP) if not already present in the database. [NEW D-02, D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Reconstructed Balance Verification: The migration routine independently folds the imported events and asserts exact Decimal equality against the database balances before committing. On mismatch, rolls back atomically without corrupting data. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Migration Idempotency: Repeated application startups detect existing migration events and skip execution without duplicating accounts, generating duplicate events, or altering balances. [NEW D-05]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`

## CQRS Command and Query Separation

- Command Model: State-changing operations (`execute_transfer`, `execute_conversion`, `execute_ach_transfer`, `execute_recurring`) run through command handlers that validate invariants, enforce optimistic concurrency, append domain events, and advance account versions. [NEW D-06]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Query Model: Account and transaction queries (`GET /api/accounts`, `GET /api/accounts/{id}`, `GET /api/transactions`) read exclusively from CQRS read projections (`account_projections`, `transaction_projections`). [NEW D-06]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Strong Synchronous Consistency: Every command updates the relevant read projections within the SAME SQLite database transaction as the domain event. Users observe their updated balance and transaction history immediately upon command completion (read-your-own-writes). [NEW D-06]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`

## Optimistic Concurrency Control

- Account Versions: Every account maintains an authoritative monotonic integer version. [NEW D-14]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Expected Version Validation: Two-account commands validate `expected_from_version` and `expected_to_version`. If either does not match the authoritative version, the command is aborted with HTTP 409 Conflict (`ACCOUNT_VERSION_CONFLICT`). [NEW D-14]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Atomic Advancement: Committing an operation event increments the version of every affected account by +1 atomically within the SQLite write transaction. [NEW D-14]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`

## Projection Rebuilding, Replay & Deep Integrity Verification

- Protected Administrative Rebuild: An on-demand local administrative CLI and service routine (`rebuild_projections`) replays all events from `domain_events` in strictly sequential order to reconstruct read projections from scratch. [NEW D-06, D-12]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Side-Effect Free Replay: Replaying events during a rebuild must NOT re-execute transfers, invoke external networks, emit audit ledger entries, trigger MFA prompts, or re-encrypt payloads. [NEW D-06]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Atomic Rebuild Publication: Rebuilding executes into temporary projection tables or within an isolated transaction. The rebuilt state is validated and atomically published only if all balances match expected event fold values. [NEW D-06]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
- Startup Deep Integrity Verification: On startup, backend performs:
  1. Checkpoint sync check: verifies `checkpoint.last_applied_event_id == MAX(domain_events.id)`.
  2. Projection integrity verification: verifies that all accounts exist, balances are valid non-negative Decimals, and projection versions match `MAX(account_version)` recorded in `domain_events`.
  3. If checkpoint is stale OR integrity check detects corrupted balances/versions, backend initiates safe atomic rebuild before accepting incoming traffic. If rebuild fails, backend fails closed with a fatal startup error. [NEW D-06, D-12]
  `[@test] ../backend/tests/test_event_sourcing_cqrs.py`
