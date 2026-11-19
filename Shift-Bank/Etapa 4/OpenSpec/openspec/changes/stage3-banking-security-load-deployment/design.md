## Context

The application is a FastAPI and React system backed directly by SQLite. The inherited active Stage 2 change supplies seven deltas alongside four main specifications. The current application lifecycle includes a background processor, so deployment process count affects scheduling. See proposal.md and the five delta specifications for scope and behavior.

## Goals / Non-Goals

**Goals:** Use authenticated encryption with backend decryption; make financial state and audit records consistent; define measurable isolated workload; and deploy locally with durable SQLite and a single scheduler.

**Non-Goals:** Zero-knowledge encryption, real user authentication, real bank connections, cloud deployment, Kubernetes, and guarantees against an operator controlling the application, database, and all cryptographic secrets.

## Decisions

- **Authenticated encryption and external versioned keys.** Use AES-256-GCM with a random nonce per encryption, and bind table, record identity, and field as authenticated metadata. Store a key version with ciphertext. Provision independent 256-bit data keys outside source and SQLite through a protected environment or mounted secret file. This simpler keyring fits the local simulated deployment while keeping keys separate from stored records; retain old versions during rotation until all associated records are verified under the replacement. TLS protects browser/backend transport. Plaintext compatibility is temporary only within an explicit transactional migration boundary and never a fallback.
- **Migration safety.** Migrate records in bounded transactions, recording completion/version state. Verify decryptability, identity, counts, and relationships before marking complete. On any failed transaction, rollback that unit and prevent the application from serving unprotected values. Restart resumes from durable progress and skips already verified records. Rollback restores a consistent pre-migration snapshot or transactional state; migration must not destroy the recoverable source before verification.
- **Audit chain within SQLite threat boundary.** Store append-only event rows with canonical serialization, prior-event digest, and an HMAC over the sequence and event. Keep the audit key external. Persist a separately protected chain checkpoint or anchor so database-only truncation is detectable. Require administrative authorization for verification. An operator with database, application, and all secrets can defeat the guarantee; no absolute immutability is claimed.
- **Atomic writes and process concurrency.** Financial mutation, limit accounting, audit row, and chain head update share one SQLite transaction. Serialize writers using SQLite's write transaction semantics (for example, `BEGIN IMMEDIATE`), with WAL for reader coexistence, an explicit busy timeout and bounded retry policy. On exhausted contention, roll back and report failure. Use constraints/idempotency keys for ACH, recurring executions, and retries. Readers use consistent committed snapshots.
- **Load measurement.** Use Locust's request events and actual counts to compute workload mix, latency percentiles, throughput, and classified failures. Generate synthetic identities/accounts in a separate database and fail closed if the target is not explicitly isolated. Preserve raw result files per run and calculate strict thresholds from observed samples.
- **Local deployment.** Compose runs Nginx for the production frontend and TLS termination, FastAPI connected to a dedicated persistent SQLite volume, and externally supplied secrets/certificates mounted read-only. Use one backend instance as the scheduler owner; do not scale scheduler-bearing workers. Healthchecks gate readiness on configuration, database availability, and key availability. Development certificates are generated/provisioned outside the repository and are not committed.

## Risks / Trade-offs

- [Key loss can make protected records unavailable] → Back up keys separately with controlled recovery and verify restoration before migration acceptance.
- [SQLite serializes writers and can limit throughput] → Use bounded retries, short transactions, WAL reader behavior, and measure contention under the specified workload.
- [Audit chain verification depends on protected key and anchor custody] → Keep secrets external, protect administrative verification, and state the privileged-operator limitation.
- [Schema or API changes can disrupt inherited clients] → Preserve response contracts and include the inherited regression scenarios before acceptance.
- [Development TLS is not production certificate management] → Document the local trust setup and keep private certificate material outside version control.

## Migration Plan

1. Back up the isolated SQLite database and externally provisioned keys; verify both are recoverable.
2. Run an idempotent migration that encrypts in-scope records and verifies record coverage before committing completion.
3. Initialize audit chain metadata and verify its checkpoint before enabling audited mutations.
4. Deploy the Compose stack with one scheduler-bearing backend, external secrets, development TLS material, and the persistent volume.
5. Run inherited regression and deployment acceptance checks, then capture isolated Locust runs.
6. If migration fails, stop serving affected banking operations, roll back the active migration transaction or restore the pre-migration database/key snapshot, and verify record integrity before retrying. Do not downgrade to plaintext fallback.

## Open Questions

None that change approved requirements or this implementation approach. Concrete key-provider mechanics and bounded SQLite retry durations can be selected during implementation and must be documented and tested against these contracts.
