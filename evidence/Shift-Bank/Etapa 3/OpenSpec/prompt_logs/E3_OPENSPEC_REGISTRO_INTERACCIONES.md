# Stage 3 OpenSpec interaction register

## Initial discovery — 2026-11-16

Stage 3 preparation and read-only discovery started from the copied Stage 2 OpenSpec project. The active Stage 2 change and all delta specs remain available as the effective inherited contract. The common E3 handoff context supplied proposed crypto/audit security properties and load/deployment acceptance constraints; the named investigator protocol document was not found by filename. No Stage 3 change, application code, or implementation artifacts were created.

### Decisions requiring investigator approval

1. **Encryption trust boundary and migration.** Which data must be encrypted (balances, transaction amounts/parties, beneficiary and ACH account/routing details, recurring instructions, logs, backups)? Who are the communicating endpoints in a single authenticated mock-user app? Is encryption intended only in transit and at rest, or must the server be unable to read selected values? Which threat actors are in scope? Who creates/holds/rotates/revokes keys, how are browser key loss and recovery handled, and how should existing SQLite rows migrate without losing history or exposing plaintext during transition? Are searchable/filterable history and server-side limits allowed to use plaintext or metadata?

2. **Audit integrity and immutability.** Which events are audited (attempts, MFA, accepted/rejected transfers, balance mutations, ACH settlement/refund, schedule changes)? Must records be append-only only at the application layer, tamper-evident by hash chaining/signatures, or resistant to a privileged database operator? What actors may verify/export records, what fields may be redacted or encrypted, and how should corrections, retention, backups, and restore verification work? Define measurable tamper-detection and failure behavior.

3. **Load-test objective and limits.** The shared Stage 3 handoff gives a proposed profile: 30 concurrent users, ramp at 5 users/s, 60 seconds steady state, 60% balance reads, 30% history reads, and 10% real internal transfers; proposed acceptance is read p95 <200 ms, transfer p95 <500 ms, and <1% unexpected errors. Confirm these values and define whether duration excludes ramp-up, dataset size/seed state, isolation, scheduler/background jobs, measurement source, resource/SQLite contention and correctness checks, test run repetitions, and cleanup/reproducibility. These are reference constraints awaiting approval, not results or permission to run Locust now.

4. **Deployment target and operations.** The shared Stage 3 handoff proposes local containers with HTTPS, externally supplied secrets, isolated persistence, and one scheduler. Confirm this target and the HTTPS termination/certificate owner, encryption key injection/rotation, persistent volume and backup/restore behavior, SQLite suitability, health/restart policy, scheduler singleton mechanism, migrations, logs/monitoring, rollback, and acceptable availability/cost constraints. These are proposed reference constraints pending investigator approval.

5. **Operational reference provenance.** The Stage 3 handoff context attributes the load/deployment constraints above to an investigator protocol, but the named protocol document itself was not found in the workspace filename search. The Stage 2 A01–A21 mapping is not the canonical external contract. Provide the protocol or confirm that the handoff's quoted constraints are authoritative for OpenSpec.

### Readiness

Not ready for Stage 3 specification authoring until the material decisions above (at minimum encryption trust boundary/key lifecycle, audit guarantee, load acceptance criteria, and deployment target/operations) are approved. Do not implement the four Stage 3 capabilities before approval.
