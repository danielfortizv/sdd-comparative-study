## Why

Stage 3 must add protection for sensitive banking data, verifiable transaction auditing, reproducible performance evidence, and a repeatable local deployment while preserving the inherited SQLite banking behavior. The approved decisions make the security boundary, threat limitations, workload, and deployment target testable before implementation begins.

## What Changes

- Protect designated sensitive banking identifiers in browser-to-backend transit and at rest, while allowing authorized backend operations to decrypt them.
- Add append-only, cryptographically verifiable transactional audit records with defined atomicity, failure, concurrency, and threat boundaries.
- Define an isolated Locust workload with measured distribution and strict latency/error thresholds.
- Define local Docker Compose deployment, HTTPS development certificates, external secrets, persistent SQLite, healthchecks, and one scheduler.
- Require regression evidence for the inherited banking contract.

## Capabilities

### New Capabilities
- `banking-data-protection`: authenticated transport, encryption at rest, key handling, migration, and compatibility.
- `transaction-audit`: append-only audit integrity, verification, transactional consistency, and multiprocess behavior.
- `load-testing`: reproducible isolated Locust workload and measured acceptance results.
- `local-deployment`: local container operations, TLS, secrets, persistence, and operational verification.
- `banking-compatibility`: regression of inherited E1/E2 banking behavior.

### Modified Capabilities

None. The Stage 2 change remains active and unsynchronized; its contracts are referenced as inherited requirements without editing them.

## Impact

Planning impact covers FastAPI/React behavior, SQLite persistence, cryptographic key provisioning, audit operations, Locust evidence, and Docker Compose/Nginx deployment artifacts. No application code, dependencies, deployment configuration, or databases are changed in this specification phase.
