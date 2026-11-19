## Purpose

Defines the approved one-time COP migration boundary, exact reconciliation, preserved provenance, and safe rejection of unsupported legacy states.

## ADDED Requirements

### Requirement: Approved legacy currency and account mapping
The migration MUST interpret the two inherited account balances as COP only under the approved researcher policy and convert once at the exact simulated rate 4,000 COP = 1 USD. The inherited internal IDs `acc_checking` and `acc_savings` MUST remain stable; canonical public references MUST be `CHK-1001` and `SAV-2001`. For the reported initial state, the resulting opening balances MUST be USD 1,250.00 and USD 3,750.00. New `EUR-3001` and `GBP-4001` accounts MUST start at zero. The resulting balances explicitly deviate from common D-02 reference balances USD 2,500.00 and USD 10,000.00. No artificial balancing transactions are permitted. The one-time migration rate MUST remain separate from operational D-03 rates.

#### Scenario: Reported initial state converts to approved values
- **WHEN** the source snapshot contains the reported 5,000,000.00 COP checking and 15,000,000.00 COP savings initialization state
- **THEN** the migrated accounts expose CHK-1001 USD 1,250.00 and SAV-2001 USD 3,750.00, with no balancing deposit or withdrawal, and zero-balance EUR-3001 and GBP-4001 accounts

#### Scenario: Unknown source currency or conflicting identity
- **WHEN** source currency cannot be established as COP under the approved policy, or an ID/reference conflict prevents deterministic mapping
- **THEN** migration aborts before financial mutation and reports nonsensitive conflicting identifiers

### Requirement: Exact reconciliation and migration idempotency
Migration MUST use exact decimal/rational arithmetic and round the final USD amount once to cents using ROUND_HALF_UP. It MUST record source snapshot identity, original amount and currency, exact rate, converted amount, and exact rational sub-cent residual, calculated as `(source COP amount / 4000) - posted USD amount`. Reconciliation MUST prove that the exact converted source value equals posted USD plus the recorded residual. Residuals MUST be reported and MUST NOT silently alter a spendable balance or create an artificial financial transaction. The migration MUST be repeat-safe for the same identified source snapshot and MUST fail closed if source state changes or reconciliation cannot prove the approved invariants.

#### Scenario: Rerun against the same source snapshot
- **WHEN** the same migration batch is requested again against the same identified source snapshot
- **THEN** it creates no additional balance, history, event, account-version, or audit effect

#### Scenario: Reconciliation has unexplained residual or mismatch
- **WHEN** exact source-to-target reconciliation cannot explain a difference under the approved conversion and rounding rule
- **THEN** the migration aborts without changing financial state and reports the mismatch without inserting a balancing entry

### Requirement: Snapshot boundary preserves history without double-posting
The migration MUST verify the inherited HMAC audit chain before cutover and preserve its records, identifiers, ordering, and verifiability. It MUST establish migrated balances from one verified cutover snapshot. Original terminal transactions MUST remain queryable with original IDs, direction, timestamps, amount, and COP provenance, but MUST NOT be replayed as additional balance effects on top of that snapshot. Domain events MUST remain distinct from audit records.

#### Scenario: Seeded history is retained as non-posting provenance
- **WHEN** the reported completed `tx_seed_1` and `tx_seed_2` rows are imported at a verified balance snapshot
- **THEN** their original IDs, directions, timestamps, amounts, and COP provenance remain queryable and the snapshot balances are not adjusted a second time

#### Scenario: Audit chain verification fails
- **WHEN** the inherited HMAC audit chain cannot be verified or its required key is unavailable
- **THEN** cutover aborts before financial state changes and the existing audit records remain untouched

### Requirement: Legacy-state preconditions fail closed
Before any migration financial-state mutation, the system MUST verify that no ACH transfer remains pending, no internal/ACH/schedule MFA authorization remains pending, no active or paused recurring schedule requiring migration exists, and current UTC-day transfer-limit consumption is zero. If any condition fails, migration MUST abort without modifying financial state; it MUST NOT settle, refund, cancel, expire, authorize, convert, or execute an obligation automatically. It MUST report blocking records using nonsensitive identifiers. Completed, settled, failed/refunded, cancelled, and expired records MUST remain as historical provenance.

#### Scenario: Pending ACH or MFA blocks migration
- **WHEN** any pending ACH or pending MFA record exists at preflight
- **THEN** migration aborts with unchanged financial state and reports only nonsensitive record IDs and blocking status

#### Scenario: Active or paused schedule blocks migration
- **WHEN** an active or paused recurring schedule requires migration
- **THEN** migration aborts without executing, cancelling, converting, or changing the schedule or any balance

#### Scenario: Nonzero current-day limit usage blocks migration
- **WHEN** reconstructed UTC current-day transfer-limit usage is nonzero or cannot be proven to be zero
- **THEN** migration aborts before financial mutation and reports the safe precondition failure

#### Scenario: Terminal history remains preserved
- **WHEN** completed, settled, failed/refunded, cancelled, or expired legacy records are included in migration
- **THEN** their original identity, state, direction, timestamps, and monetary provenance remain queryable without new financial effects

### Requirement: Migration recovery is atomic and reversible
Migration MUST commit its snapshot event, opening projection, provenance records, account mapping, converted per-user limit settings, audit outcome, and migration identity atomically. A failure before commit MUST leave the source financial state unchanged. A rollback after cutover MUST use the recorded boundary and MUST NOT discard or duplicate post-cutover events or overwrite subsequent limit changes; if safe rollback cannot be proven, recovery MUST fail closed and preserve both source and event evidence for review.

#### Scenario: Failure before migration commit
- **WHEN** any required migration write or verification fails before commit
- **THEN** the transaction rolls back with unchanged source balances, history, account identities, and audit chain

#### Scenario: Recovery after committed cutover
- **WHEN** a cutover recovery is requested after Stage 4 events have been appended
- **THEN** the system identifies all post-cutover events and refuses any rollback that would lose or double-apply them

#### Scenario: Rollback preserves a subsequent limit update
- **WHEN** a per-user limit has been changed after cutover and rollback is requested
- **THEN** rollback preserves that subsequent setting and fails closed if it cannot restore the pre-migration state without overwriting the later change
