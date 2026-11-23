## MODIFIED Requirements

### Requirement: Chronological ledger of movements
The system MUST make completed, pending, and terminal financial operations queryable in chronological order with stable operation and transaction identifiers, source and destination references where applicable, explicit amount currency, status, and timestamp. Historical inherited COP transactions MUST retain their original identifiers, amounts, direction, timestamps, and COP provenance. When the migration boundary is a verified balance snapshot, imported legacy transactions MUST remain queryable as non-posting provenance and MUST NOT be replayed as additional balance effects on top of that snapshot.

#### Scenario: User views transaction history
- **WHEN** the user requests history after migration
- **THEN** the system returns the inherited COP transaction records with their original IDs and timestamps plus Stage 4 operations with explicit supported currencies in chronological order

#### Scenario: Account history includes both directions
- **WHEN** the user requests movements for CHK-1001
- **THEN** the system returns records where its canonical or legacy identity is the source or destination, preserving the original identity mapping

#### Scenario: Imported provenance does not post twice
- **WHEN** the event stream is replayed after a snapshot-based migration
- **THEN** legacy history remains visible but does not change the migrated opening balances a second time
