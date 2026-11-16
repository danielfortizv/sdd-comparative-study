# Feature Specification: Shift Bank Stage 3 — Security Hardening, Audit Integrity, Load Testing, and Containerized Deployment

**Feature Branch**: `003-shift-bank-stage3`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "Shift Bank Stage 3 (Option A): Evolve the existing Stage 2 banking application according to the immutable SEED-3.md and the four approved decisions E3-ENC-01, E3-AUD-01, E3-LOAD-01, and E3-DEP-01."

## Clarifications

### Session 2026-11-15

- **E3-ENC-01 (Encryption Scope and Trust Boundary)**: Application-layer encryption operates for sensitive client-originated banking payloads sent from the client browser to the trusted backend application. The backend is authorized to decrypt banking data in memory to enforce business validations, dynamic limits, balance checks, and recurring schedule processing (this is not a zero-knowledge architecture). Sensitive client-originated fields (beneficiary names, bank account numbers, routing numbers, transfer amounts, and MFA PINs) must be encrypted before transmission. HTTPS is mandatory for deployment, ensuring transport security for all traffic including sensitive server responses, but TLS alone does not replace application-layer encryption for client-originated payloads; no additional application-layer response-payload re-encryption is imposed beyond HTTPS transport security. Sensitive identifiers and beneficiary information persisted at rest must use authenticated encryption while preserving exact arithmetic and consistency across limits and recurring schedules. Cryptographic keys must be managed through external configuration, never hardcoded, committed to Git, or exposed in client bundles, and must persist across authorized restarts. Key or decryption failures must fail securely without plaintext fallback.
- **E3-AUD-01 (Immutable Transaction Audit Logs)**: A tamper-evident, append-only audit trail must record all financial transactions and operational state transitions. Tamper-evidence is enforced through cryptographically verifiable chaining and database protections. Successful financial operations and their audit records must commit atomically; if an audit write fails, the financial operation must fail closed and roll back completely. Rejections and security failures must be recorded in separate atomic audit transactions where possible, or reject safely if audit storage is unavailable. Plaintext MFA PINs, secrets, and raw sensitive identifiers must never appear in audit entries. Administrative verification capabilities must be protected against unauthorized access without introducing a full multi-tenant authentication system.
- **E3-LOAD-01 (Reproducible Load Testing)**: Automated load testing uses Locust to generate real HTTP requests against the backend without requiring browser automation. The benchmark must exercise the real encrypted HTTP interface with 30 concurrent virtual users (ramp-up 5 users/second, sustained 60 seconds post ramp-up) with a configured workload distribution of 60% account balance reads, 30% transaction history reads, and 10% internal transfers. Performance criteria require p95 read latency < 200 ms, p95 transfer latency < 500 ms, and unexpected error rate < 1.0%. The benchmark must record the actual measured request distribution alongside configured weights and explicitly classify expected banking rejections (e.g., dynamic limit rejections, if triggered) separately from unexpected failures (HTTP 5xx server errors, network connection drops, or unhandled exceptions). Synthetic accounts and funds in an isolated disposable database prevent depletion of funds or unintended limit triggers. The initial valid benchmark result must be preserved without overwriting.
- **E3-DEP-01 (Deployment Requirements)**: Deployment uses a reproducible local multi-container Docker Compose architecture consisting of a containerized backend and compiled static production frontend assets served behind an Nginx reverse proxy. Nginx terminates local development HTTPS and redirects all HTTP traffic to HTTPS. Secrets and encryption keys are supplied externally; database files reside on a dedicated persistent volume. Recurring payment scheduling is preserved with exactly one active scheduler instance. Automated health checks and smoke verification validate HTTPS redirection, API health, account operations, encrypted transactions, MFA step-up, audit verification, and post-restart persistence using fresh disposable test volumes.
- **Audit Integrity Guarantees & Tail Truncation Boundary**: Cryptographic chaining (linking each entry to its predecessor via keyed cryptographic digests and strictly contiguous sequence numbers) combined with database-level update/delete protections mathematically detects any modification of historical records, insertion of unauthorized records, reordering of records, or deletion of interior records within the defined threat model. However, within a standalone database file without an external trusted anchor, cryptographic chaining cannot independently detect tail truncation (silent deletion of the most recent $N$ records), because any valid prefix of a valid hash chain is mathematically self-consistent. To detect tail truncation, the system's verification interface must support comparison against an externally supplied trusted checkpoint (e.g., trusted high-water mark, sequence counter, or external checkpoint digest). Absolute immutability against an administrator possessing total control over both storage media and cryptographic keys is explicitly outside the threat model. Claims of regulatory compliance or absolute non-repudiation are unsupported and excluded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Client-to-Server Application-Layer Encryption & Secure Persistence (Priority: P1)

As an authenticated banking customer, I want my sensitive client-originated banking details—including transfer amounts, recipient details, account identifiers, routing numbers, and MFA authorization PINs—to be encrypted directly within my browser before transmission over the network and stored securely at rest, with sensitive server responses protected by HTTPS, so that eavesdroppers, compromised intermediate proxies, or unauthorized access to raw database files cannot read or manipulate my private financial data.

**Why this priority**: Security hardening is the foundational prerequisite of Stage 3. It establishes the confidential transport envelope between client and server and protects persisted banking data without altering core financial business logic.

**Independent Test**: Can be fully tested by submitting internal transfers, ACH transfers, beneficiary creations, and MFA confirmations from the web client; inspecting network traffic to confirm that sensitive client-originated fields are transmitted exclusively as authenticated ciphertext envelopes while responses are served over HTTPS; confirming the trusted backend successfully decrypts valid envelopes in memory to evaluate limits and execute debits; inspecting the database file directly to verify that persisted sensitive identifiers and financial amounts are stored as authenticated ciphertext; and executing the legacy data migration to verify existing plaintext Stage 2 records are safely converted to encrypted storage.

**Acceptance Scenarios**:

1. **Given** a customer initiates an internal transfer, ACH transfer, or beneficiary creation from the browser, **When** the payload is dispatched over the network, **Then** all sensitive client-originated fields (beneficiary name, account number, routing number, transfer amount, and MFA PIN) are encrypted into an authenticated cryptographic envelope before transmission, and no sensitive field appears in plaintext in the network payload.
2. **Given** an encrypted banking request received by the backend, **When** the backend verifies the envelope using its externally configured private cryptographic credentials, **Then** the payload is decrypted into memory to validate balances, enforce dynamic limits, and process the transfer according to existing banking rules.
3. **Given** a client request containing a corrupted ciphertext, missing cryptographic envelope, mismatched authentication tag, or invalid key identifier, **When** the backend attempts processing, **Then** the request is rejected immediately with an HTTP client error (400 Bad Request or 422 Unprocessable Entity), no financial state is altered, and no fallback to plaintext processing occurs.
4. **Given** a customer confirms a sensitive transfer with a 6-digit MFA PIN, **When** transmitted, **Then** the PIN is transmitted exclusively within the encrypted payload envelope, decrypted only in memory for validation against the expected code (`123456`), and is never recorded in server application logs, audit logs, or error responses.
5. **Given** sensitive banking records (beneficiary accounts, routing details, transfer amounts, and balances) persisted in the database, **When** inspecting raw database storage, **Then** sensitive fields are stored as authenticated ciphertext envelopes and are unreadable without the server-side persistent storage key.
6. **Given** backend financial services reading stored accounts and transfers from database storage, **When** records are retrieved, **Then** the storage layer decrypts amounts into exact financial decimal representations in memory, ensuring that dynamic limit accumulation, balance checks, and recurring schedule evaluations maintain exact monetary precision without rounding drift.
7. **Given** the application restarts, **When** valid external configuration and persistent storage keys are supplied, **Then** all previously encrypted accounts, transfers, beneficiaries, and schedules remain fully readable and operational across restarts.
8. **Given** an existing Stage 2 database containing plaintext account balances, transfer records, saved beneficiaries, and recurring schedules, **When** the Stage 3 migration process executes during application initialization, **Then** all legacy plaintext sensitive identifiers, beneficiary details, and financial amounts are converted to authenticated ciphertext at rest, while all balance values, transfer histories, and schedule due dates remain mathematically identical to their pre-migration values.
9. **Given** a legacy migration process that encounters an unexpected error or storage failure midway through execution, **When** the failure occurs, **Then** the entire migration transaction rolls back safely to the pre-migration state, leaving no partially encrypted records or corrupted database tables.
10. **Given** an already migrated Stage 3 database containing encrypted records, **When** the migration process runs again during subsequent application restarts, **Then** it operates idempotently, detecting that data is already encrypted and completing without altering or re-encrypting existing records.

---

### User Story 2 - Tamper-Evident Transaction Audit Ledger & Integrity Verification (Priority: P1)

As an auditor, I want banking transactions and state changes to be recorded in an append-only, tamper-evident audit ledger with cryptographically verifiable chaining, so that unauthorized modifications, deletions, or insertions can be detected within the defined threat model.

**Why this priority**: A tamper-evident audit trail provides mathematical verification of historical ledger consistency within the approved threat model, detecting unauthorized alterations, omissions, and insertions.

**Independent Test**: Can be fully tested by executing a sequence of banking operations (internal transfer, sensitive transfer requiring MFA, ACH transfer lifecycle transitions, dynamic limit update, and recurring payment execution); verifying that corresponding contiguous audit records are created atomically; attempting direct SQL modifications or deletions against the audit table to verify database-level rejection; executing authorized and unauthorized requests to the verification interface; introducing simulated record tampering to verify detection; and evaluating tail truncation against an external checkpoint.

**Acceptance Scenarios**:

1. **Given** any financial transaction (internal transfer creation, ACH transfer creation, ACH settlement, ACH failure/refund, recurring payment execution, or dynamic limit update), **When** the transaction executes, **Then** a corresponding audit entry is written atomically in the same database transaction, containing a strictly monotonic sequence number, UTC timestamp, event type, actor identifier, payload snapshot digest, and cryptographic link to the previous audit record.
2. **Given** a financial transaction where the audit record cannot be written or the cryptographic link fails to compute, **When** the error occurs, **Then** the entire operation fails closed, the database transaction rolls back, account balances remain unchanged, and an error is returned to the caller.
3. **Given** an unauthorized or rejected financial operation (e.g., transfer exceeding dynamic limits, transfer with insufficient balance, invalid MFA code, or expired challenge), **When** the rejection occurs, **Then** the rejection event is captured in a separate atomic audit transaction without applying any financial state modifications.
4. **Given** an audit entry recording a sensitive transaction, **When** the audit record is stored and inspected, **Then** it contains non-sensitive metadata, event categories, and masked or cryptographically protected references, ensuring plaintext MFA PINs, cryptographic keys, and raw account numbers are never exposed in the audit trail.
5. **Given** standard database operations, **When** an application component or SQL query attempts an `UPDATE` or `DELETE` on the audit table, **Then** database-level protections (such as abort triggers) immediately block the operation and prevent alteration or removal of historical records.
6. **Given** an authorized administrative request containing valid verification credentials (e.g., an administrative token or header), **When** requesting the verification interface (`GET /api/audit/verify`), **Then** the system authorizes the request, traverses the audit log from genesis to head, recalculating and validating every cryptographic link, sequence number continuity, and payload digest, returning a comprehensive verification report.
7. **Given** a request to the verification interface (`GET /api/audit/verify`) that lacks valid administrative verification credentials or provides an invalid administrative secret, **When** received by the backend, **Then** the system rejects the request immediately with an HTTP 401 Unauthorized or 403 Forbidden status, without traversing the audit ledger or disclosing internal verification details.
8. **Given** an audit ledger that has been tampered with (e.g., an altered payload, modified timestamp, inserted record, or missing interior sequence), **When** an authorized verification executes, **Then** the system pinpoints the exact sequence number where the cryptographic chain was broken and reports an integrity violation.
9. **Given** an audit ledger where the latest $N$ entries were truncated from the tail, **When** verified against an externally supplied trusted checkpoint (e.g., expected high-water sequence number or expected head digest), **Then** the system detects the truncation and reports a discrepancy between the stored head and the trusted external checkpoint.

---

### User Story 3 - Reproducible High-Concurrency Load Testing (Priority: P2)

As a banking systems engineer, I want an automated, reproducible load testing suite that simulates realistic peak customer traffic over the encrypted HTTP interface, so that I can empirically verify system throughput, response latencies, and error rates under concurrent load against clear acceptance thresholds.

**Why this priority**: Validating application performance and stability under realistic concurrent load ensures that cryptographic operations and atomic audit logging do not degrade user experience or cause database lock contention.

**Independent Test**: Can be fully tested by executing the automated Locust benchmark script against the running backend with a dedicated synthetic database; observing 30 concurrent users over a 60-second measurement window; recording observed response times, error rates, and measured request distributions; and confirming that the first valid benchmark report is generated and archived without overwriting historical baselines.

**Acceptance Scenarios**:

1. **Given** the load testing suite initialized with a dedicated, disposable SQLite test database, **When** the benchmark runs, **Then** synthetic accounts are pre-seeded with sufficient COP balances and dynamic limit allocations to support the full transaction volume without triggering unintended balance depletion, daily limit exhaustion, or MFA challenges.
2. **Given** the Locust load test executing against the live backend, **When** generating traffic, **Then** it ramps up at 5 virtual users per second to 30 concurrent users and sustains that load for 60 seconds post ramp-up, transmitting real HTTP requests over the actual encrypted application interface.
3. **Given** the active load test workload configured with target weights of 60% balance reads, 30% history reads, and 10% internal transfers, **When** Locust executes over the measurement window, **Then** the test measures and records the actual observed request distribution across all endpoints alongside the configured target weights.
4. **Given** the sustained load test execution, **When** calculating latency metrics across the measurement period, **Then** the 95th-percentile (p95) response latency for read operations (balances and history) is strictly less than 200 milliseconds, and the p95 response latency for transfer operations is strictly less than 500 milliseconds.
5. **Given** the completed benchmark execution, **When** evaluating reliability metrics, **Then** the unexpected failure rate (HTTP 5xx server errors, unhandled exceptions, connection drops) across all requests is strictly less than 1.0%, and any expected banking rejections are explicitly categorized and reported separately.
6. **Given** the benchmark output artifacts, **When** the initial valid benchmark completes, **Then** the execution log, workload parameters, observed request distribution, and latency statistics (p50, p95, p99, total requests, RPS) are archived to a durable report file, and subsequent test runs are prevented from silently overwriting the initial baseline record.

---

### User Story 4 - Containerized HTTPS Deployment with Reverse Proxy (Priority: P2)

As a DevOps engineer, I want to deploy the complete Shift Bank application locally using Docker Compose with an Nginx reverse proxy terminating HTTPS, serving compiled static React frontend assets, and routing API calls to the containerized backend, so that the entire system can be reliably started, verified, and operated in an isolated, production-like environment.

**Why this priority**: Containerization and local HTTPS deployment fulfill the Stage 3 operational requirement, ensuring transport security and environment consistency across development and evaluation environments.

**Independent Test**: Can be fully tested by executing `docker compose up -d`; verifying container health status; sending an unencrypted HTTP request to verify automatic redirection to HTTPS; accessing the web application in a browser over HTTPS; executing end-to-end banking operations (balances, transfers, MFA, and audit verification); restarting containers; and verifying that persisted data survives intact across restarts.

**Acceptance Scenarios**:

1. **Given** the deployment configuration, **When** launching via Docker Compose, **Then** separate containers for the Nginx reverse proxy and the FastAPI backend start successfully, reach healthy status, and operate on an isolated internal container network.
2. **Given** a client sending an HTTP request to the exposed HTTP port (default 8080), **When** received by Nginx, **Then** the server immediately returns an HTTP 301/308 redirect to the secure HTTPS port (default 8443).
3. **Given** a client establishing a connection over HTTPS, **When** negotiating TLS, **Then** Nginx terminates HTTPS using local development certificates and successfully serves compiled, production-built React frontend assets (not a Vite development server).
4. **Given** API requests matching `/api/*` received by Nginx, **When** forwarded, **Then** Nginx proxies requests to the internal FastAPI backend container, preserving client headers and returning backend responses seamlessly over the TLS connection.
5. **Given** cryptographic keys, database paths, and runtime configuration, **When** containers are started, **Then** all secrets are injected exclusively through external environment variables or mounted configuration files, and no secret is embedded in Dockerfiles, Git repositories, or frontend static bundles.
6. **Given** bank accounts, completed transfers, and audit records created within the deployed application, **When** the Docker Compose containers are stopped and restarted, **Then** the database stored on the dedicated persistent Docker volume persists intact, and all encrypted data remains fully accessible and verifiable.
7. **Given** the deployed application, **When** the automated smoke test script is executed, **Then** it automatically validates HTTPS redirection, backend health endpoints, account queries, encrypted transfer execution, MFA confirmation, audit chain verification, and data persistence across a container restart.

---

### User Story 5 - Preservation of Inherited Stage 1 & Stage 2 Banking Invariants (Priority: P2)

As an existing bank customer, I want all established banking capabilities from Stage 1 and Stage 2—including account balances, own-account transfers, dynamic transfer limits, simulated MFA verification, external ACH transfers, and scheduled recurring payments—to remain fully functional and backwards-compatible with the new security and deployment enhancements.

**Why this priority**: Brownfield evolution requires strict preservation of prior functional contracts. Enhancements in Stage 3 must not regress or alter established banking rules.

**Independent Test**: Can be fully tested by running the complete inherited test suite (47 backend tests and 12 frontend tests) alongside Stage 3 enhancements; verifying that default accounts (Checking COP 5,000,000.00, Savings COP 15,000,000.00) initialize properly; confirming that dynamic limits (COP 5,000,000.00 per-transfer, COP 10,000,000.00 daily) are strictly enforced; confirming that MFA is triggered for amounts $\ge \text{COP } 1,000,000.00$; and verifying that recurring payment schedules execute automatically when due.

**Acceptance Scenarios**:

1. **Given** the application running with Stage 3 security enhancements, **When** checking account balances, **Then** Checking (COP 5,000,000.00) and Savings (COP 15,000,000.00) balances match their fresh seed values and display correctly formatted in Colombian Pesos.
2. **Given** an internal or ACH transfer with amount exceeding the remaining per-transfer or daily limit, **When** submitted, **Then** the system rejects the transaction with an HTTP 400 Bad Request before initiating any MFA step-up verification, and enters an audit rejection entry.
3. **Given** a sensitive internal or ACH transfer ($\ge \text{COP } 1,000,000.00$) within limits, **When** submitted, **Then** the system returns a pending MFA status with a 300-second validity window, prompts for the 6-digit code `123456`, debits funds only upon successful verification, and atomically writes the corresponding audit records.
4. **Given** external ACH transfers, **When** initiated, **Then** recipient details (name, bank, 9-digit routing, 4–17 digit account number) are validated according to Stage 2 rules, funds are debited immediately, autonomous settlement advances pending transfers to `SETTLED`, and simulated failures trigger an exact single refund (recorded via `refunded_at` timestamp) and atomic audit recording.
5. **Given** active scheduled recurring payments, **When** payments become due while the backend scheduler is running, **Then** exactly one active scheduler instance evaluates live balances and limits, executes due payments automatically without interactive MFA prompts, updates next due dates, and records atomic audit entries.
6. **Given** existing automated test suites, **When** executed in test isolation, **Then** all 47 inherited backend tests and 12 inherited frontend tests pass with zero regressions.

---

## Edge Cases

- **Corrupted or Tampered Ciphertext**: If an incoming client request contains malformed ciphertext, corrupted initialization vectors, or invalid authentication tags, the backend MUST abort processing immediately, reject the request with HTTP 400/422, write an audit rejection record, and never attempt plaintext evaluation.
- **Unavailable or Corrupted Cryptographic Keys**: If external key configuration is missing, unreadable, or invalid at startup, the backend MUST fail secure by refusing to start or refusing all crypto-dependent endpoints with HTTP 500, rather than operating with hardcoded fallback keys or plaintext processing.
- **Audit Storage Failure During Financial Mutation**: If the database encounters a write error, disk full condition, or constraint violation while appending the chained audit record during a transfer, the entire database transaction MUST immediately roll back to ensure zero partial financial state changes (fail-closed).
- **Audit Storage Failure During Rejection Logging**: If an operation is rejected (e.g., limit exceeded) and the separate audit transaction recording the rejection also fails, the backend MUST prioritize security and reject the client operation safely rather than allowing the unrecorded event to proceed.
- **Audit Chain Tail Truncation**: If an adversary with raw database access truncates the trailing records of the audit table, the internal hash chain remains self-consistent up to the truncated record. The verification endpoint MUST accept an optional external trusted checkpoint (expected sequence number or expected head hash); when provided, any discrepancy between the database head and the trusted checkpoint MUST be reported as a tail truncation violation.
- **Precision of Encrypted Amounts at Rest**: When financial amounts are stored as authenticated ciphertext in SQLite, the storage adapter MUST decrypt amounts into exact Python `Decimal` instances in memory, preserving exact two-decimal precision and preventing IEEE 754 floating-point rounding errors across balance aggregations and dynamic limit calculations.
- **Legacy Migration Interruption**: If the application crashes, loses power, or encounters a disk error while migrating legacy plaintext records to encrypted storage, the migration process MUST abort and roll back atomically, leaving the database in its original consistent state so that migration can safely restart upon next launch.
- **Database Lock Contention Under High Load**: Under concurrent write load (transfers and atomic audit log writes), SQLite must manage connection timeouts and transaction locking gracefully, completing operations within the p95 latency thresholds without unhandled `database is locked` operational crashes.
- **Synthetic Test Data Depletion During Load Testing**: To ensure load test reproducibility, the synthetic database seed MUST allocate sufficient initial balances across multiple synthetic accounts so that sustained 30-user traffic does not exhaust balances, breach daily limits, or trigger MFA challenges mid-test.
- **Scheduler Recovery After Container Restart**: If the backend container is stopped while recurring payments are due, the scheduler MUST detect overdue active schedules upon startup, process them sequentially according to existing business rules, and advance their due dates without executing duplicate payments.
- **Container Port Conflicts**: The deployment configuration MUST parameterize external host ports via environment variables (e.g., `HOST_HTTP_PORT=8080`, `HOST_HTTPS_PORT=8443`) so users can resolve local port binding conflicts without modifying container manifests.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Domain 1: Application-Layer Encryption & Key Management (E3-ENC-01)

- **FR-001**: System MUST implement application-layer encryption for all sensitive client-originated banking payloads transmitted from the client web browser to the backend service.
- **FR-002**: System MUST classify client-submitted beneficiary names, bank account numbers, routing numbers, transfer amounts, and MFA PINs as sensitive banking data requiring application-layer encryption prior to network dispatch.
- **FR-003**: System MUST permit the trusted backend to decrypt client-originated encrypted payloads in memory to enforce business validations, dynamic limits, balance checks, and recurring schedule execution.
- **FR-004**: System MUST establish client-to-server application-layer encryption without exposing long-lived symmetric server secrets to the client browser or committing private keys to the repository.
- **FR-005**: System MUST validate client-provided cryptographic envelopes and immediately reject requests with missing, invalid, or corrupted ciphertexts using HTTP client error status codes (400 or 422).
- **FR-006**: System MUST fail secure upon any cryptographic error, strictly prohibiting any fallback to plaintext transmission or unencrypted payload processing.
- **FR-007**: System MUST support external configuration of all cryptographic keys and secrets via environment variables or external configuration files.
- **FR-008**: System MUST prevent exposure of plaintext MFA PINs, cryptographic keys, and raw client credentials in application logs, error payloads, and audit trails.

#### Domain 2: Secure Persistence & Financial Invariants (E3-ENC-01)

- **FR-009**: System MUST apply authenticated encryption at rest to all persisted sensitive banking identifiers and beneficiary information stored in SQLite.
- **FR-010**: System MUST protect persisted financial amounts at rest while guaranteeing exact two-decimal monetary arithmetic and consistency across account balances, dynamic limits, and recurring payment schedules.
- **FR-011**: System MUST ensure that encrypted data remains fully accessible and decryptable across authorized backend service and container restarts when valid keys are provided.
- **FR-012**: System MUST maintain database isolation between production/runtime data, automated test databases, and historical Stage 1 and Stage 2 databases, and MUST NOT modify historical Stage 1 or Stage 2 reference databases.
- **FR-013**: System MUST provide an idempotent migration process that safely converts pre-existing Stage 2 plaintext banking records (account balances, transfers, beneficiaries, recurring schedules) to encrypted Stage 3 storage, preserving exact balances and historical consistency, rolling back completely on any failure.

#### Domain 3: Tamper-Evident Transaction Audit Logs (E3-AUD-01)

- **FR-014**: System MUST maintain an append-only, tamper-evident audit ledger recording all financial operations and security-critical state transitions.
- **FR-015**: System MUST record the following event types in the audit ledger: internal transfer creation and completion; ACH transfer creation, settlement, failure, and refund processing; dynamic limit updates; recurring schedule creation, status transitions, and automated executions; and MFA verification failures.
- **FR-016**: System MUST link each audit record cryptographically to its immediate predecessor using a keyed cryptographic digest and strictly contiguous sequence numbers.
- **FR-017**: System MUST commit financial state changes and their corresponding audit log entries atomically within the same database transaction.
- **FR-018**: System MUST fail closed and completely roll back any financial state mutation if the associated audit record cannot be generated, linked, or written to storage.
- **FR-019**: System MUST record rejected operations and authorization failures in a separate atomic audit transaction without applying any financial state modifications, rejecting safely if audit storage is unavailable.
- **FR-020**: System MUST enforce database-level protections preventing modification (`UPDATE`) or deletion (`DELETE`) of historical audit records during standard application operations.
- **FR-021**: System MUST provide an administrative verification interface that recalculates the cryptographic chain from genesis to head, reporting whether the ledger is intact or identifying the exact location of any tampering, modification, or sequence discontinuity.
- **FR-022**: System MUST protect the administrative audit verification capability against unauthorized access (e.g., via administrative credentials) without introducing a full multi-tenant authentication system.
- **FR-023**: System MUST support verifying the audit ledger against an external trusted checkpoint to detect tail truncation, documenting that internal chaining alone cannot detect deletion of trailing records without an external reference.

#### Domain 4: Reproducible Load Testing (E3-LOAD-01)

- **FR-024**: System MUST provide an automated Locust load testing benchmark targeting the running backend over its real, encrypted HTTP interface.
- **FR-025**: System MUST execute the load test with 30 concurrent virtual users, a ramp-up rate of 5 users per second, and a sustained 60-second measurement window post ramp-up.
- **FR-026**: System MUST execute load tests with configured target workload weights of 60% account balance reads, 30% transaction history reads, and 10% internal transfers.
- **FR-027**: System MUST measure and record the actual HTTP request distribution across endpoints, distinguishing observed request counts and percentages from the configured target weights.
- **FR-028**: System MUST execute load tests against an isolated disposable database pre-seeded with synthetic accounts and funds, preventing depletion of balances, unexpected daily limit exhaustion, or unintended MFA challenges.
- **FR-029**: System MUST explicitly classify load test results into successful requests, expected banking rejections (e.g., business validation errors), and unexpected failures (HTTP 5xx server errors, connection drops, unhandled exceptions), verifying that the unexpected failure rate remains strictly below 1.0%, and preserving the initial valid benchmark report without silent overwriting.

#### Domain 5: Containerized Deployment & Operational Verification (E3-DEP-01)

- **FR-030**: System MUST provide a reproducible multi-container Docker Compose deployment comprising a containerized backend and compiled static frontend assets.
- **FR-031**: System MUST configure Nginx as a reverse proxy that terminates HTTPS with local development certificates, serves static frontend assets, and proxies API traffic to the backend over an internal container network, protecting all server responses and sensitive banking communications in transit.
- **FR-032**: System MUST automatically redirect all unencrypted HTTP traffic to HTTPS on configurable host ports.
- **FR-033**: System MUST persist the SQLite database on a dedicated Docker volume and ensure data availability across container restarts.
- **FR-034**: System MUST preserve recurring payment processing with exactly one active scheduler instance inside the deployment.
- **FR-035**: System MUST provide container health checks and an automated smoke test suite verifying HTTPS redirection, API health, account operations, encrypted transactions, MFA step-up, audit verification, and persistence across container restarts.

---

### Key Entities

- **Account**: Represents a customer banking account (Checking or Savings) denominated in Colombian Pesos (COP). Attributes include unique account identifier, customer identifier, friendly name, encrypted balance, currency, and creation timestamp.
- **Transfer**: Represents a financial movement between accounts. Attributes include unique transfer identifier, transfer type (`INTERNAL` or `ACH`), source account, destination account or recipient snapshot, encrypted amount, status (`COMPLETED`, `PENDING`, `PENDING_MFA`, `SETTLED`, `FAILED`, `EXPIRED`), creation timestamp, expiration timestamp, and associated lifecycle timestamps (`settled_at`, `failed_at`, `refunded_at`).
- **Beneficiary**: Represents a saved external ACH recipient. Attributes include unique identifier, customer identifier, encrypted recipient name, encrypted bank name, encrypted 9-digit routing number, encrypted account number, and creation timestamp.
- **Transfer Limit**: Represents dynamic customer transfer constraints. Attributes include customer identifier, encrypted per-transfer limit, encrypted cumulative daily limit, and last update timestamp.
- **Recurring Schedule**: Represents an automated payment schedule. Attributes include unique identifier, customer identifier, transfer type (`INTERNAL` or `ACH`), source account, target details, encrypted amount, frequency (`DAILY`, `WEEKLY`, `MONTHLY`), status (`ACTIVE`, `PAUSED`, `CANCELLED`, `PENDING_MFA`, `EXPIRED`), next due date, and last executed timestamp.
- **Audit Record**: Represents an immutable ledger entry. Attributes include sequential record identifier, strictly contiguous sequence number, UTC timestamp, event type, actor identifier, resource identifier, payload digest, predecessor cryptographic digest, current cryptographic digest, and entry signature/HMAC.
- **Cryptographic Envelope**: Represents an encrypted message payload transmitted from client to server or stored at rest. Attributes include key identifier/version, initialization vector, ciphertext, and authentication tag.
- **Benchmark Run**: Represents an executed load test experiment. Attributes include run timestamp, user count, ramp rate, duration, configured weights, actual request counts and percentages by endpoint, p50/p95/p99 latencies, expected rejections count, unexpected errors count, and pass/fail verdict.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Confidentiality in Transit)**: 100% of sensitive client-originated banking payloads (transfers, beneficiaries, MFA confirmations) are transmitted as authenticated ciphertext, with zero sensitive client fields exposed in plaintext over network inspection, and all sensitive server responses protected by HTTPS transport security.
- **SC-002 (Integrity at Rest)**: 100% of sensitive persisted identifiers and financial amounts in SQLite are encrypted with authenticated encryption at rest, while maintaining exact arithmetic precision with zero rounding errors across all balance and limit calculations.
- **SC-003 (Audit Atomicity)**: 100% of successful financial operations have an accompanying chained audit log entry committed in the same database transaction; simulated audit write failures produce a 100% rollback rate of financial mutations (zero partial state changes).
- **SC-004 (Audit Tamper Detection)**: The audit verification mechanism detects 100% of simulated modifications to historical audit records, inserted records, deleted interior records, rejects unauthorized verification requests, and detects tail truncation when an external checkpoint is supplied.
- **SC-005 (Load Test Concurrency & Stability)**: The system sustains 30 concurrent virtual users over a 60-second measurement period with an unexpected error rate strictly below 1.0%, with expected banking rejections properly categorized.
- **SC-006 (Load Test Latency Targets)**: Under sustained 30-user load on the real encrypted HTTP interface, 95th-percentile (p95) response latency is less than 200 ms for read operations (balances and history) and less than 500 ms for transfer operations.
- **SC-007 (Deployment Security & Redirection)**: 100% of unencrypted HTTP requests to the reverse proxy are redirected to HTTPS, and all served web pages and API responses travel over TLS.
- **SC-008 (Deployment Persistence)**: 100% of accounts, completed transactions, and audit records created in the containerized deployment remain available and verifiable following container termination and restart.
- **SC-009 (Regression Prevention)**: 100% of inherited Stage 1 and Stage 2 test suites (47 backend tests, 12 frontend tests, and frontend production build) pass without regressions.
- **SC-010 (Benchmark Preservation)**: 100% of initial valid benchmark execution metrics (configured weights, actual distribution, latency percentiles, categorized error rates) are persisted to a durable report file without being overwritten by subsequent test runs.

---

## Assumptions

- **Mock Session Continuity**: The application continues to operate under the authenticated mock user model (`user_mock_001`); multi-tenant identity providers and user registration remain outside the scope of Stage 3.
- **Simulated External Networks**: Interbank ACH transfers continue to operate in a simulated environment; no real external clearing houses or central bank settlement APIs are integrated.
- **Local Deployment Scope**: The containerized deployment is designed for local evaluation and demonstration; production public cloud orchestration (Kubernetes, AWS/GCP infrastructure) and enterprise CI/CD pipelines are outside current requirements.
- **Cryptographic Key Provisioning**: Operators or test runners supply required cryptographic keys via environment variables or local configuration files before starting the application or test suites; automated public key infrastructure (PKI) certificate authority issuance is not required.
- **Single Scheduler Invariant**: Recurring payment processing runs with exactly one active scheduler instance inside the backend container; distributed leader election mechanisms are not required for this single-node local deployment.
