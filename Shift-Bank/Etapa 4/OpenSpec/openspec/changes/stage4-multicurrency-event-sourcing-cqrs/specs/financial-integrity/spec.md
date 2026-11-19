## Purpose

Preserves inherited encryption and HMAC audit protections while making the new financial event, projection, and retry state atomic.

## ADDED Requirements

### Requirement: Atomic financial and audit persistence
For each financial command, its domain events, affected account projections, account versions, audit outcome, and idempotency result MUST commit atomically. If an event, projection, audit, or idempotency write fails, no partial successful financial effect may commit or be reported. Rejected and failed attempts MUST be auditable when the audit store is available, without implying a balance mutation that did not occur.

#### Scenario: Required persistence fails during a command
- **WHEN** any required financial event, projection, audit, or idempotency write fails
- **THEN** all financial writes in that operation roll back and no success response is returned

#### Scenario: Auditable rejection has no financial effect
- **WHEN** a request fails validation or concurrency checks and audit persistence is available
- **THEN** a safe rejection outcome is recorded while balances, account versions, and daily usage remain unchanged

### Requirement: Preserve AES-GCM protection and HMAC audit chain
Sensitive inherited records MUST remain protected with AES-GCM and key versioning; the inherited HMAC-chained audit log MUST remain verifiable and separate from the domain event store. Keys MUST remain externally provisioned, and missing or invalid keys MUST cause affected operations to fail closed without plaintext fallback. No Stage 4 event may rewrite or substitute an inherited audit record.

#### Scenario: Existing audit chain remains verifiable after migration
- **WHEN** a migration or Stage 4 operation commits
- **THEN** inherited audit records remain unchanged and the HMAC chain verifies with the authorized key

#### Scenario: Required encryption key is unavailable
- **WHEN** an authorized operation needs protected data but the required key is missing or invalid
- **THEN** it fails safely without disclosing plaintext or partially mutating financial state
