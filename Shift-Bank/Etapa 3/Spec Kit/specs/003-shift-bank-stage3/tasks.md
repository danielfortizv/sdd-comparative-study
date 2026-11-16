# Tasks: Shift Bank Stage 3 — Security Hardening, Audit Integrity, Load Testing, and Containerized Deployment

**Input**: Design documents from `/specs/003-shift-bank-stage3/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`)  
**Prerequisites**: Approved `spec.md`, `plan.md`, `data-model.md`, `contracts/api.md`, `research.md`, `quickstart.md`  
**Requirements Coverage**: All 35 Functional Requirements (`FR-001` through `FR-035`) and all 38 Acceptance Scenarios (`Scenarios 1.1..1.10`, `2.1..2.9`, `3.1..3.6`, `4.1..4.7`, `5.1..5.6`)  
**Organization**: Tasks are grouped by phase and user story to enable independent implementation, testing, and verification.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with exact file paths`

- **[P]**: Can run in parallel (different files, no blocking dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Every task includes explicit file paths and verifiable completion criteria.

---

## Phase 1: Setup & Shared Infrastructure

**Purpose**: Prepare project dependencies, cryptographic test harnesses, and type declarations without altering historical Stage 1/2 artifacts.

- [x] T001 Verify clean brownfield environment and baseline test passing status (47 backend pytest tests passing, 12 frontend Vitest tests passing, frontend production build succeeding) across `backend/tests/` and `frontend/src/`
- [x] T002 [P] Configure cryptographic test fixtures and external key generation in `backend/tests/conftest.py`, providing temporary RSA-2048 keypairs, 256-bit AES storage keys, HMAC signing keys, and administrative verification tokens without hardcoding secrets, supporting `TEST_DB_PATH` isolation
- [x] T003 [P] Extend backend package dependencies in `backend/requirements.txt` with `cryptography` and `locust`
- [x] T004 [P] Extend TypeScript contract and model declarations in `frontend/src/types.ts` for `CryptographicEnvelope`, `PublicKeyResponse`, `AuditRecord`, `AuditVerificationResponse`, and `HealthResponse` per `specs/003-shift-bank-stage3/contracts/api.md`

---

## Phase 2: Foundational (Blocking Core Prerequisites)

**Purpose**: Core cryptographic wrappers, database-level audit triggers, contiguous sequence allocation, and legacy migration scanner that MUST be complete before user story endpoints are implemented.

**⚠️ CRITICAL**: No user story implementation work can begin until this phase is complete.

- [x] T005 Implement backend cryptographic core module in `backend/src/crypto.py`: RSA keypair loading from external configuration (`BANK_PRIVATE_KEY_PATH`), RSA-OAEP unwrapping of ephemeral AES keys, AES-256-GCM authenticated payload decryption, AES-256-GCM field encryption/decryption at rest (`enc:v1:<iv>:<ciphertext_tag>`) using `BANK_STORAGE_KEY`, and HMAC-SHA256 digest calculations (FR-001..FR-010)
- [x] T006 [P] Implement frontend Web Crypto wrapper in `frontend/src/crypto.ts`: fetch public key from `/api/crypto/public-key`, generate ephemeral 256-bit AES-GCM key, encrypt payload with fresh 12-byte random IV, wrap AES key using RSA-OAEP, and format `CryptographicEnvelope` without exposing server secrets (FR-001..FR-004)
- [x] T007 Implement database-level audit schema, triggers, and contiguous sequence allocation in `backend/src/database.py`: create `audit_logs` table, create `trg_prevent_audit_update` and `trg_prevent_audit_delete` triggers, and implement `get_next_audit_sequence()` under `BEGIN IMMEDIATE;` write locking to guarantee gap-free contiguous sequencing ($1, 2, 3, \dots, N$) (FR-013..FR-020)
- [x] T008 Implement safe, idempotent legacy plaintext migration scanner in `backend/src/database.py`: multi-field validation of all sensitive columns across `accounts`, `limits`, `beneficiaries`, `transfers`, and `recurring_schedules`, converting plaintext to `enc:v1:...`, validating existing envelopes, aborting on corrupted ciphertext, rolling back atomically on error, and isolating historical databases (FR-012, FR-013)
- [x] T009 [P] Update Pydantic data models in `backend/src/models.py`: add `CryptographicEnvelope`, `AuditRecordResponse`, `AuditVerificationResponse`, and `HealthResponse` schemas per `specs/003-shift-bank-stage3/data-model.md`

**Checkpoint**: Foundational core ready — cryptographic primitives, database triggers, sequence calculation, and migration scanner functional. User story implementation can now begin.

---

## Phase 3: User Story 1 - Client-to-Server Application-Layer Encryption & Secure Persistence (Priority: P1) 🎯 MVP

**Goal**: Encrypt sensitive client-originated banking data before network dispatch, decrypt in backend memory for business logic, encrypt sensitive fields at rest in SQLite while maintaining exact Python Decimal arithmetic, and execute safe legacy migration.

**Independent Test**: Submit internal and ACH transfers, beneficiary creations, and MFA confirmations from the browser; verify sensitive fields are transmitted exclusively as authenticated ciphertext envelopes; verify backend decrypts in memory to enforce limits and debits; verify raw SQLite file stores fields as `enc:v1:...`; verify legacy plaintext records are safely converted to encrypted storage without balance alteration (Scenarios 1.1..1.10).

### Tests for User Story 1

- [x] T010 [P] [US1] Write automated cryptographic unit and integration tests in `backend/tests/test_crypto.py`: RSA keypair loading, ephemeral AES-GCM wrapping/unwrapping, payload decryption, rejection of corrupted ciphertext/tag/missing envelope with HTTP 400/422, fail-secure behavior without plaintext fallback, at-rest field encryption/decryption, and exact `Decimal` precision preservation (Scenarios 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7)
- [x] T011 [P] [US1] Write automated migration tests in `backend/tests/test_migration.py`: full legacy Stage 2 plaintext migration across all five entities (accounts, limits, beneficiaries, transfers, recurring_schedules), atomic rollback on error, corrupted ciphertext detection/abort, and restart idempotency (Scenarios 1.8, 1.9, 1.10)
- [x] T012 [P] [US1] Write frontend unit tests in `frontend/src/crypto.test.ts`: verify Web Crypto hybrid envelope generation, public key caching, and payload encryption without leaking secrets

### Implementation for User Story 1

- [x] T013 [US1] Implement `GET /api/crypto/public-key` endpoint in `backend/src/api.py` exposing backend RSA public key in PEM format per `contracts/api.md` (FR-004)
- [x] T014 [US1] Update API client methods in `frontend/src/services.ts` to transparently wrap outgoing sensitive payloads (`submitTransfer`, `confirmMfa`, `submitAchTransfer`, `createBeneficiary`, `createRecurringSchedule`, `updateLimits`) in `CryptographicEnvelope` using `crypto.ts` (FR-001, FR-002)
- [x] T015 [US1] Update backend endpoint handlers in `backend/src/api.py` to accept `CryptographicEnvelope`, decrypt payload in memory via `crypto.py`, validate against Pydantic models, and proceed with banking validations, returning HTTP 400 on decryption failure (FR-003, FR-005, FR-006)
- [x] T016 [US1] Update at-rest persistence and retrieval in `backend/src/services.py`: encrypt balances, transfer amounts/beneficiary data, dynamic limits, and recurring schedule amounts into `enc:v1:...` in SQLite; decrypt amounts into exact Python `Decimal` instances in memory, preserving exact arithmetic for balance and limit checks (FR-009, FR-010, FR-011)
- [x] T017 [US1] Integrate `migrate_legacy_plaintext_records()` into `init_db()` in `backend/src/database.py`, executing migration on application boot with atomic rollback and isolation of historical databases (FR-012, FR-013)

**Checkpoint**: User Story 1 (MVP) is fully functional and testable independently. Sensitive data is protected in transit and at rest.

---

## Phase 4: User Story 2 - Tamper-Evident Transaction Audit Ledger & Integrity Verification (Priority: P1)

**Goal**: Maintain an append-only, tamper-evident audit ledger capturing all financial state transitions and operational rejections; fail-closed atomic commits; database-level abort triggers; administrative verification with external checkpoint validation.

**Independent Test**: Execute internal transfers, ACH transfers, limit updates, and recurring executions; verify corresponding contiguous audit records are created atomically; verify simulated audit write failure triggers complete financial rollback (fail-closed); verify rejections log in separate atomic transactions; verify database triggers block `UPDATE` and `DELETE`; verify `GET /api/audit/verify` authorizes requests with valid admin key and rejects unauthorized requests (401/403); verify detection of tampered records and tail truncation against an external checkpoint (Scenarios 2.1..2.9).

### Tests for User Story 2

- [x] T018 [P] [US2] Write automated audit tests in `backend/tests/test_audit.py`: atomic commit of transfer + audit record, fail-closed rollback of financial state upon simulated audit failure, separate atomic logging of rejected operations, privacy preservation (no plaintext PINs or raw secrets in audit payload), and SQLite trigger rejection of `UPDATE` / `DELETE` (Scenarios 2.1, 2.2, 2.3, 2.4, 2.5)
- [x] T019 [P] [US2] Write automated verification tests in `backend/tests/test_audit.py`: authorized verification with valid admin key returning full integrity report, unauthorized rejection (401/403) without admin key, detection of modified/inserted/deleted records with exact sequence pinpointed, and tail truncation detection when verified against external trusted checkpoint (Scenarios 2.6, 2.7, 2.8, 2.9)

### Implementation for User Story 2

- [x] T020 [US2] Implement audit logging service in `backend/src/services.py`: `append_audit_record()` calculating contiguous sequence, predecessor HMAC, entry HMAC-SHA256, and canonical non-sensitive payload digest within the active atomic transaction under `BEGIN IMMEDIATE;` (FR-014..FR-017)
- [x] T021 [US2] Integrate atomic audit logging across all banking operations in `backend/src/services.py`: internal transfer create/complete, MFA challenge/verify/fail, ACH transfer create/settle/fail/refund, dynamic limit updates, and recurring schedule create/execute/fail (FR-014..FR-017)
- [x] T022 [US2] Implement separate atomic rejection audit logging in `backend/src/services.py` for dynamic limit rejections, balance insufficiency, and MFA failures, with safe fallback rejection if audit storage fails (FR-018, FR-019)
- [x] T023 [US2] Implement administrative verification endpoints `GET /api/audit/verify` and `GET /api/audit/records` in `backend/src/api.py`, enforcing `X-Audit-Admin-Key` authorization, traversing the chain, and comparing against optional `expected_head_hash` / `expected_count` external checkpoints (FR-021, FR-022, FR-023)

**Checkpoint**: User Stories 1 and 2 are fully functional and independently verified. Financial mutations are tamper-evident and atomic.

---

## Phase 5: User Story 3 - Reproducible High-Concurrency Load Testing (Priority: P2)

**Goal**: Provide an automated Locust load testing suite executing over the real encrypted HTTP interface; sustain 30 concurrent users for 60 actual seconds post ramp-up based on observed ramp completion; measure steady-state metrics separately; isolate test data; classify errors; archive initial baseline without overwrite.

**Independent Test**: Execute Locust load test against live backend using synthetic database; observe 30 concurrent users for 60 full seconds after ramp-up completes; record observed request distribution against configured 60/30/10 weights; verify steady-state read p95 < 200 ms, transfer p95 < 500 ms, unexpected error rate < 1.0%; verify initial valid benchmark report is archived without silent overwriting (Scenarios 3.1..3.6).

### Tests & Implementation for User Story 3

- [x] T024 [P] [US3] Create synthetic test database generator in `backend/tests/conftest.py` / `scripts/seed_load_db.py`: seed dedicated `test_load_bank.db` with synthetic accounts (COP 100,000,000.00 balances, COP 50,000,000.00 limits) to isolate load tests and prevent business limit exhaustion or MFA triggers (FR-028, Scenario 3.1)
- [x] T025 [P] [US3] Implement Locust benchmark script in `backend/tests/locustfile.py`:
  - `on_start`: fetches backend RSA public key from `/api/crypto/public-key`
  - Configured task weights: `@task(6)` balance reads (`/api/accounts`), `@task(3)` history reads (`/api/accounts/{id}/history`), `@task(1)` internal transfers (`/api/transfers`) with client-side encryption simulation
  - Implements event listeners capturing observed ramp-up completion (when active users reaches 30) and isolating the subsequent 60 full seconds of steady-state execution for separate metrics evaluation
  - Classifies responses into Success (200/201), Expected Banking Rejection (400), and Unexpected Failure (5xx, timeouts) (FR-024..FR-027, FR-029, Scenarios 3.2, 3.3, 3.5)
- [x] T026 [US3] Implement load test execution runner and report archiver script in `scripts/run_load_test.py`: executes Locust headless (6s ramp + 60s steady-state), validates steady-state read p95 < 200 ms, transfer p95 < 500 ms, and unexpected error rate < 1.0%, and archives the initial valid baseline report to `locust/reports/` with timestamp, preventing silent overwriting (FR-029, Scenarios 3.4, 3.6)

**Checkpoint**: User Story 3 fully functional and verified against performance and reliability acceptance criteria.

---

## Phase 6: User Story 4 - Containerized HTTPS Deployment with Reverse Proxy (Priority: P2)

**Goal**: Reproducible local multi-container Docker Compose deployment; Nginx reverse proxy with local development TLS certificates and HTTP redirection; static React build; persistent SQLite volume; single scheduler instance; automated smoke verification.

**Independent Test**: Launch stack via `docker compose up -d`; verify containers reach healthy status; send HTTP request to port 8080 and verify 301/308 redirect to HTTPS port 8443; access application over HTTPS; execute automated smoke test verifying accounts, encrypted transfers, MFA, and audit verification; restart containers and verify persistent data survives intact (Scenarios 4.1..4.7).

### Implementation for User Story 4

- [x] T027 [P] [US4] Create production Nginx configuration in `deployment/nginx.conf`: HTTP port 80 redirecting to HTTPS port 443 (mapped to host 8080/8443), TLS certificate configuration, static React asset routing with SPA fallback, and `/api/` reverse proxy with proxy headers (FR-028, FR-029, Scenarios 4.2, 4.3, 4.4)
- [x] T028 [P] [US4] Create backend Dockerfile in `deployment/Dockerfile.backend` (Python 3.13-slim, non-root user `bankuser`, volume mount `/app/data`) and frontend build configuration in `deployment/Dockerfile.frontend` (multi-stage or static Nginx serving compiled React assets) (FR-027, Scenarios 4.1, 4.3)
- [x] T029 [US4] Create Docker Compose manifest in `deployment/docker-compose.yml`: multi-container service definition (`nginx`, `backend`), persistent named volume `shift_bank_data`, internal bridge network, external environment variable injection (`.env`), and container healthchecks for both services (FR-027, FR-030, FR-032, Scenarios 4.1, 4.5, 4.6)
- [x] T030 [US4] Implement `GET /api/health` endpoint in `backend/src/api.py` reporting backend health, database connectivity, scheduler status, and key availability (FR-035, Scenario 4.7)
- [x] T031 [US4] Implement single-instance background scheduler guard in `backend/src/scheduler.py` ensuring exactly one scheduler loop runs inside the backend lifespan, recovering overdue active schedules on restart (FR-034, Scenario 4.6)
- [x] T032 [P] [US4] Implement automated deployment smoke test script in `deployment/smoke_test.py`: validates HTTP $\to$ HTTPS redirection, API health over HTTPS, account queries, encrypted transfer, MFA confirmation, audit chain verification, unauthorized verification rejection, and container restart persistence against a fresh disposable volume (FR-035, Scenario 4.7)

**Checkpoint**: User Story 4 fully functional and verified. Deployment is secure, containerized, and persistent.

---

## Phase 7: User Story 5 - Preservation of Inherited Stage 1 & Stage 2 Banking Invariants (Priority: P2)

**Goal**: Ensure zero regressions across all established Stage 1 and Stage 2 banking capabilities.

**Independent Test**: Execute all 47 inherited backend tests and 12 frontend tests; verify Checking (COP 5M) and Savings (COP 15M) seed balances; verify dynamic limits enforcement before MFA; verify sensitive transfer MFA threshold ($\ge \text{COP } 1M$); verify ACH settlement/refund lifecycle; verify single active recurring scheduler (Scenarios 5.1..5.6).

### Tests & Verification for User Story 5

- [x] T033 [US5] Run complete inherited backend test suite (`pytest backend/tests/test_api.py backend/tests/test_limits.py backend/tests/test_ach.py backend/tests/test_recurring.py backend/tests/test_stage2_regression.py -v`) verifying all 47 inherited tests pass without modification (Scenarios 5.1..5.6)
- [x] T034 [US5] Run complete frontend test suite (`npm --prefix frontend test -- --run`) and production build (`npm --prefix frontend run build`) verifying all 12 tests pass and build succeeds (Scenarios 5.1..5.6)
- [x] T035 [US5] Execute cross-story regression integration test verifying that dynamic limits, simulated MFA step-up ($\ge \text{COP } 1M$), ACH settlement/refund, and recurring payments work seamlessly with encrypted storage and audit logging (Scenarios 5.1..5.6)

**Checkpoint**: User Story 5 verified. All brownfield banking invariants preserved with zero regressions.

---

## Phase 8: Polish & Operational Runbook Verification

**Purpose**: Cross-cutting verification, documentation alignment, and acceptance review.

- [x] T036 [P] Verify and update operational documentation in `specs/003-shift-bank-stage3/quickstart.md` ensuring all script paths, environment variables, and execution commands align with delivered implementation
- [x] T037 Perform code cleanliness, typing, and formatting review across all new and modified files in `backend/` and `frontend/`
- [x] T038 Conduct final end-to-end acceptance review against all 35 functional requirements and 10 success criteria

---

## Dependencies & Execution Order

### Phase Dependencies
```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational (Blocking Core Prerequisites)
    │
    ├──────────────────────────┬──────────────────────────┐
    ▼                          ▼                          ▼
Phase 3: User Story 1 (P1)   Phase 4: User Story 2 (P1)   Phase 7: US5 Regressions (P2)
    │                          │                          │
    └──────────────────────────┴──────────────────────────┘
                               │
                               ▼
                 Phase 5: User Story 3 (P2)
                               │
                               ▼
                 Phase 6: User Story 4 (P2)
                               │
                               ▼
                 Phase 8: Polish & Final Review
```

### Critical Path & Acceptance Gates
1. **Gate 1 (Foundational Complete)**: `crypto.py`, `database.py` (triggers & migration), and `models.py` must pass unit checks before any endpoint modifications.
2. **Gate 2 (MVP Security Complete)**: Phase 3 (US1 - Encryption & Persistence) and Phase 4 (US2 - Audit Trail) must pass all automated tests (`test_crypto.py`, `test_migration.py`, `test_audit.py`) before load testing or deployment packaging.
3. **Gate 3 (Operational Readiness Complete)**: Phase 5 (US3 - Locust Benchmark) must verify steady-state p95 latencies and error rates before Phase 6 (US4 - Deployment) smoke tests.
4. **Gate 4 (Regression Gate)**: Inherited 47 backend tests and 12 frontend tests must pass with 100% success at every phase boundary.

---

## Parallel Execution Opportunities

- **Phase 1**: T002 (Test fixtures), T003 (Dependencies), and T004 (Frontend types) can run in parallel.
- **Phase 2**: T006 (Frontend crypto) and T009 (Models) can run in parallel with T005, T007, and T008.
- **Phase 3**: Tests T010, T011, and T012 can be authored in parallel before implementation.
- **Phase 4**: Tests T018 and T019 can be authored in parallel.
- **Phase 6**: T027 (Nginx conf), T028 (Dockerfiles), and T032 (Smoke test script) can be authored in parallel.
