## 1. Data protection

- [x] 1.1 Inventory sensitive persisted fields and define versioned authenticated ciphertext representation; verify no designated banking identifier remains plaintext after migration.
- [x] 1.2 Implement externally provisioned key loading, availability checks, access controls, and key versioning; verify missing, invalid, and unavailable keys fail closed.
- [x] 1.3 Implement idempotent transactional encryption migration with integrity/coverage checks; verify restart resume, rollback on injected failure, and recoverability.
- [x] 1.4 Preserve existing API behavior for beneficiary, ACH, history, and recurring operations; verify inherited regression scenarios pass.
- [x] 1.5 Enforce HTTPS browser/API transport and verify sensitive requests cannot use an HTTP fallback.

## 2. Transactional audit

- [x] 2.1 Implement append-only audit event model and keyed verifiable chain with protected checkpoint; verify alteration, deletion, insertion, and reordering are detected.
- [x] 2.2 Integrate audit events into successful, rejected, and failed financial flows; verify every committed financial mutation has its required audit event.
- [x] 2.3 Make financial, limit, audit-entry, and chain-head changes atomic; verify audit persistence failure leaves no partial financial mutation.
- [x] 2.4 Implement separately authorized chain verification and report valid range or first invalid link; verify unauthorized checks are denied.
- [x] 2.5 Exercise actual multiple backend processes against shared SQLite with concurrent transfers and reads; verify no duplicate effects, missing events, chain forks, or inconsistent snapshots.
- [x] 2.6 Document and verify bounded SQLite contention behavior, WAL reader behavior, retries, and safe rollback on exhausted writer contention.

## 3. Load testing

- [x] 3.1 Add isolated synthetic database setup and a fail-closed target guard; verify Locust cannot select operational banking storage.
- [x] 3.2 Implement Locust workload with 30 users, 5 users/second ramp, 60 seconds post-ramp steady state, and configured 60/30/10 task weighting; verify transfers execute through the real application flow.
- [x] 3.3 Calculate observed distribution and required latency, throughput, count, and classified error metrics from request events; verify configured weights are never substituted for observed mix.
- [x] 3.4 Preserve original machine-readable output and complete per-run environment report; verify strict threshold equality is reported as failure.

## 4. Local deployment

- [x] 4.1 Add Docker Compose deployment for FastAPI, Nginx-served production assets, development HTTPS, external secrets, and isolated persistent SQLite; verify private keys and credentials are excluded.
- [x] 4.2 Configure healthchecks and exactly one scheduler owner; verify restart and service-count behavior cannot activate concurrent schedulers.
- [x] 4.3 Verify HTTPS banking operations, encryption at rest, MFA, audit-chain verification, and data persistence after container restart.

## 5. Compatibility and acceptance

- [x] 5.1 Exercise inherited account, balance, history, transfer, MFA, beneficiary, ACH, limit, and recurring-payment scenarios; verify Stage 1/2 behavior and API responses remain compatible.
- [x] 5.2 Run strict OpenSpec validation and resolve all specification validation errors before implementation begins.
- [x] 5.3 Capture deployment and load-test acceptance evidence with original machine-readable results and environment details; verify no evidence is overwritten.
