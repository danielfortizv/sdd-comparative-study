# Quickstart & Verification Runbook: Shift Bank Stage 3

This runbook provides concrete, step-by-step instructions to configure, run, test, benchmark, and deploy Shift Bank Stage 3 in strict alignment with approved specification `specs/003-shift-bank-stage3/spec.md`, Constitution v1.2.0, and the delivered Stage 3 implementation.

---

## 1. Prerequisites & Cryptographic Secret Provisioning

### 1.1. Required Runtimes
- **Python**: Python 3.13+ with active virtual environment (`.venv`).
- **Node.js**: Node 20+ with npm dependencies installed in `frontend/`.
- **Docker**: Docker Engine (v24+) and Docker Compose (v2+).

### 1.2. Cryptographic Secret Generation (Zero Hardcoded Secrets)
Stage 3 enforces strict cryptographic credential isolation. Secrets are provisioned externally; images, repositories, and build artifacts contain zero hardcoded or fallback credentials.

Generate cryptographically strong secrets via the automated provisioning utility:
```powershell
python scripts/generate_deployment_secrets.py
```
- **Create-Only Protection**: By default, this utility refuses to overwrite an existing `deployment/docker.env` file to prevent accidental loss of encryption keys for existing persistent databases.
- **Platform Access Control**:
  - **Windows (NTFS)**: Uses `icacls` to disable inheritance and grant exclusive read/write access to the current Windows user (`icacls <file> /inheritance:r /grant:r "%USERNAME%:(R,W)"`).
  - **Linux / macOS**: Enforces POSIX mode `0600` (`stat.S_IRUSR | stat.S_IWUSR`).
- **Permission Verification**:
  ```powershell
  python scripts/generate_deployment_secrets.py --verify-permissions
  ```

### 1.3. Safe Backup & Disaster Recovery Runbook
1. **Backup**:
   - Securely back up `deployment/docker.env` and `backend/certs/` to an encrypted, offline vault or hardware security module (HSM).
   - Never commit `.env` files, private keys (`*.pem`), or unencrypted archives to source control.
2. **Restoration**:
   - Prior to launching containers on a new host or after disaster recovery:
     a. Restore `docker.env` into `deployment/docker.env`.
     b. Restore `bank_private.pem`, `bank_public.pem`, `localhost_cert.pem`, and `localhost_key.pem` into `backend/certs/`.
     c. Verify file permissions: `python scripts/generate_deployment_secrets.py --verify-permissions`.
     d. Launch stack: `docker compose -f deployment/docker-compose.yml up -d`.
3. **Key Rotation Notice**:
   - Symmetric storage keys (`BANK_STORAGE_KEY`) cannot be rotated by simple secret regeneration; doing so invalidates existing SQLite at-rest records (`InvalidTag` error). Key rotation requires an approved online re-encryption migration utility.

---

## 2. Automated Test Suite Execution

### 2.1. Backend Test Suite (Pytest)
Execute all 97 backend automated tests:
```powershell
.venv\Scripts\pytest.exe -o cache_dir=.tmp/pytest_cache -v
```

#### Test Module Breakdown
| Test Module | Coverage Scope | Test Count |
|---|---|---|
| `backend/tests/test_api.py` | Inherited Stage 1 account overview, balances, and internal transfers | 12 |
| `backend/tests/test_limits.py` | Inherited Stage 2 dynamic limits, accumulation, and UTC windowing | 9 |
| `backend/tests/test_ach.py` | Inherited Stage 2 external beneficiaries, ACH lifecycle, and single refunds | 11 |
| `backend/tests/test_recurring.py` | Inherited Stage 2 recurring schedules, pause/resume/cancel, and sweeps | 9 |
| `backend/tests/test_stage2_regression.py` | Inherited Stage 2 multi-state history, left-join queries, and seed accounts | 6 |
| `backend/tests/test_crypto.py` | Stage 3 RSA-OAEP / AES-GCM envelope encryption and at-rest field encryption | 17 |
| `backend/tests/test_migration.py` | Stage 3 Idempotent legacy migration scanner, rollback, and corruption abort | 3 |
| `backend/tests/test_audit.py` | Stage 3 Append-only HMAC audit chaining, triggers, and admin verification | 10 |
| `backend/tests/test_load_seed.py` | Stage 3 Synthetic database seeder (COP 100M balances, COP 50M limits) | 2 |
| `backend/tests/test_concurrency_invariants.py` | Stage 3 Multi-threaded concurrent transfers and atomic limit enforcement | 2 |
| `backend/tests/test_fail_closed_secrets.py` | Stage 3 Granular fail-closed behavior on individual secret omissions | 4 |
| `backend/tests/test_health_scheduler.py` | Stage 3 `/api/health` endpoint and single-instance scheduler guard | 4 |
| `backend/tests/test_secret_generator.py` | Stage 3 Create-only guard and platform permission restrictions | 2 |
| `backend/tests/test_inherited_compatibility.py` | Stage 3 Direct CryptographicEnvelope requests bypassing test adapters | 6 |
| **Total Backend Test Suite** | **100% Passing Coverage Across All Functional Requirements** | **97** |

### 2.2. Frontend Test Suite & Static Production Build
```powershell
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
**Expected Outcome**: 13/13 Vitest unit and component tests pass; production bundle compiles with zero TypeScript errors into `frontend/dist/`.

---

## 3. Automated Locust Load Testing (E3-LOAD-01)

### 3.1. Workload Profile & Performance Criteria
- **Target URL**: Real backend HTTPS interface (`https://127.0.0.1:8443`) with local development TLS certificate verification.
- **Client Encryption**: True hybrid application-layer encryption (RSA-OAEP + AES-256-GCM) per transfer request.
- **Concurrency & Timing**: 30 virtual users ramped up at 5 users/sec, sustaining a full 60.0 seconds of steady-state execution after 30 users are confirmed active.
- **Continuous Concurrency Invariant**: Periodic 1 Hz sampling auditing that active concurrency never drops below 30 users.
- **Configured Weights**: 60% account balance reads, 30% account history reads, 10% encrypted internal transfers.
- **SLA Thresholds**:
  - Read operations p95 latency: < 200 ms.
  - Transfer operations p95 latency: < 500 ms.
  - Unexpected error rate: < 1.0% (5xx server errors, connection drops, unhandled exceptions).
- **Post-Run Invariants**: 100% funds conservation (COP 600,000,000.00 exact) and contiguous HMAC audit ledger integrity.

### 3.2. Automated Benchmark Execution
Run the automated benchmark runner:
```powershell
.venv\Scripts\python.exe scripts/run_load_test.py
```
This script autonomously:
1. Provisions local TLS certificates (`backend/certs/localhost_cert.pem`) and application RSA keypair if absent.
2. Seeds isolated synthetic database (`backend/test_load_bank.db`) with COP 100M balances and COP 50M limits.
3. Launches background backend process over HTTPS.
4. Executes Locust headless with 30 users, 5 users/s spawn rate, and 60s sustained steady-state.
5. Verifies post-run balances and traverses the complete audit ledger.
6. Reconciles 100% of steady-state requests (operational banking workload vs startup handshake requests).
7. Archives results to `locust/reports/`:
   - Preserves `initial_benchmark_report.json` and `.md` as the permanent baseline.
   - Archives subsequent runs to `benchmark_run_<timestamp>.json` and `.md` without overwriting historical evidence.

---

## 4. Multi-Container Local Docker Deployment (E3-DEP-01)

### 4.1. Launch Stack via Docker Compose
```powershell
# 1. Generate deployment secrets if not already present (create-only)
python scripts/generate_deployment_secrets.py

# 2. Build and launch container stack in detached mode
docker compose -f deployment/docker-compose.yml up -d --build
```

### 4.2. Verify Container Health
```powershell
docker compose -f deployment/docker-compose.yml ps
# Expected: shift_bank_backend (healthy) and shift_bank_nginx (healthy)
```

### 4.3. Automated Deployment Smoke Test
Execute the end-to-end smoke verification suite:
```powershell
.venv\Scripts\python.exe deployment/smoke_test.py
```
**Automated Verifications (9/9 Tests)**:
1. HTTP (port 8080) automatically redirects to HTTPS (port 8443) with HTTP 301.
2. Nginx delivers static React production bundle over TLS (port 8443).
3. Backend reports healthy status, database connectivity, active scheduler, and loaded keys (`/api/health`).
4. Account queries return decrypted balances through Nginx reverse proxy (`/api/accounts`).
5. Client-to-server encrypted transfer executes atomically (`/api/transfers`).
6. Sensitive transfer step-up MFA challenge (`202 PENDING_MFA`) and encrypted code confirmation (`200 COMPLETED`).
7. Authorized audit ledger cryptographic verification (`/api/audit/verify` with `X-Audit-Admin-Key`).
8. Unauthorized audit verification rejection (HTTP 401 on missing/invalid admin key).
9. Container restart and persistent SQLite storage survival (restarts container, verifies balances and audit intact).

### 4.4. Container Teardown
- **Preserve Persistent Financial Data**:
  ```powershell
  docker compose -f deployment/docker-compose.yml down
  ```
- **Purge Disposable Test Volumes** (Destroys persistent database):
  ```powershell
  docker compose -f deployment/docker-compose.yml down -v
  ```
