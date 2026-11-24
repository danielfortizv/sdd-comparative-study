# Shift Bank E3 — OpenSpec Block 2 Evidence

Date: 2026-11-16 (America/Bogota)
Change: `stage3-banking-security-load-deployment` (OpenSpec 1.11.0, `spec-driven`)
Scope: Transactional audit, financial atomicity, integration, and verification only.

## Initial consistency review

The Block 1 design records a real choice relative to the earlier envelope-key-wrapping design: directly provisioned independent versioned 256-bit data keys are used instead of wrapped per-record DEKs. This is not a material conflict with the researcher-approved functional requirements, which require external key provision, versioning/rotation, and fail-closed behavior but do not mandate envelope wrapping. No encryption architecture or approved security requirement was changed in Block 2.

The referenced `../.tessl/RULES.md` was not present at the resolved path, so it could not be read. Native apply context was read through `openspec.cmd instructions apply --change stage3-banking-security-load-deployment --json`.

## Files created or modified in Block 2

- Created `backend/audit.py`: HMAC-SHA-256 canonical event chain, external 32-byte audit key, keyed checkpoint, append-only SQLite triggers, verification, protected initialization marker, safe rejection recorder, and no chain reset API.
- Modified `backend/database.py`: WAL mode and bounded SQLite connection busy timeout; audit initialization after encryption migration.
- Modified `backend/banking.py`: same-transaction events for successful mutations and explicit outcomes; rejection/MFA failure recording; bounded `BEGIN IMMEDIATE` retries; failure-safe commit handling.
- Modified `backend/main.py`: separately token-authorized HTTPS audit verification route and safe audit error response.
- Created `backend/SECURITY.md`: audit key/admin-token provisioning, chain guarantees, verification, and threat limitation.
- Created `backend/tests/test_audit.py`: 13 focused tests, including tampering, migration-safe initialization, atomicity, two-connection behavior, four-process concurrency, and restart verification.
- Modified `backend/tests/test_api.py`, `backend/tests/test_banking.py`, and `backend/tests/test_encryption.py` to provision isolated test-only audit configuration where required by application initialization.
- Modified `openspec/changes/stage3-banking-security-load-deployment/tasks.md`: marked tasks 2.1–2.6 complete after verification.

No frontend source, dependency manifest, or lockfile was intentionally changed. `npm ci` installed the exact locked frontend dependencies locally to enable the required build. It reported 3 dependency advisories (1 moderate, 2 high); no dependency audit fix was applied.

## Verification commands and results

Working directory for backend commands: `backend/`.

- `python -m unittest tests.test_audit -v` — PASS, 13 tests.
- `python -m unittest discover -s tests -v` — PASS, 48 tests (includes inherited banking and Block 1 encryption suites).
- `npm.cmd --prefix frontend test` — PASS, 8 tests.
- `npm.cmd --prefix frontend ci` — completed; installed 68 packages. npm reported 3 advisories as noted above.
- `npm.cmd --prefix frontend run build` — PASS after rerunning outside the sandbox because sandboxed esbuild could not access its parent directory. Vite 5.4.21 emitted production assets (`index.html`, CSS, JS); 34 modules transformed.
- `openspec.cmd validate --all --strict` — PASS, 6 passed, 0 failed.

## Acceptance evidence

- AC-01 inherited banking regression: full backend suite passed (48/48); frontend suite passed (8/8); Block 1 encryption scenarios reran as part of the backend suite. Existing Stage 2 ACH, MFA, beneficiary, limits, and recurring tests passed.
- AC-05 chain validity: focused chain verification plus concurrent/restart test passed. Four OS worker processes each completed six transfers; resulting chain had 25 entries including genesis, all 24 transfers committed, checking balance was COP 4,997,600.00, and transaction count was 26 including two seeded rows. A separate restarted Python process verified the persisted chain as valid.
- AC-06 tamper detection and append-only controls: SQL UPDATE/DELETE rejection, HMAC content alteration, deletion, insertion, reordered sequence, and missing checkpoint after bootstrap were tested; verification identified the first invalid position. The tests bypassed SQLite triggers only to simulate unauthorized database edits. Threat model excludes an operator controlling the database, application, and all cryptographic secrets.
- AC-07 atomicity: injected audit INSERT failures caused internal transfer debit/credit and limit usage to remain unchanged; ACH refund/state stayed pending and unrefunded; beneficiary creation left no beneficiary row. Invalid MFA produced a durable rejection event while preserving pending authorization state and balances. A bounded writer-contention test confirmed no transfer or transaction row was committed.
- AC-08 MFA failure outcomes: invalid MFA event persisted with rejection outcome and without the submitted code; inherited expiry and retry regressions passed in full backend suite.
- AC-09 concurrency: four independent OS Python processes accessed the same disposable synthetic SQLite database, ran reads and transfers concurrently, and produced no process failures, duplicate transfer effects, missing chain entries, or invalid chain. A two-connection WAL test held a read snapshot while a separate writer atomically updated balance and audit; the reader observed old committed values until ending its snapshot, then saw the fully committed values. A separate process verified after restart.

## Initial failures and corrections

- An early ACH rollback test did not reach settlement because the processing timestamp was less than the inherited 30-second settlement delay. The test now uses `now_utc() + 31 seconds`; it then confirmed rollback behavior.
- Early MFA test connections were not closed, causing SQLite teardown locking; tests now close each connection explicitly.
- A newly added insertion-tamper assertion expected checkpoint mismatch, but verifier correctly reported sequence/link mismatch first; assertion was corrected to the earliest invalid chain position.
- A first multiprocess read addition referenced nonexistent `banking.all_accounts`; corrected worker to read `accounts` through a separate SQLite connection before each transfer.
- Initial production build lacked installed TypeScript. After `npm ci`, sandboxed esbuild was denied parent-directory access; the authorized out-of-sandbox rerun succeeded.

## Design decisions, deviations, and limitations

- HMAC-SHA-256 uses a separately provisioned Base64 32-byte `SHIFT_BANK_AUDIT_KEY`; verification endpoint separately requires `SHIFT_BANK_AUDIT_ADMIN_TOKEN` over HTTPS.
- Events use canonical JSON, a sequence, prior hash, event hash, and keyed checkpoint. SQLite triggers enforce ordinary application-level append-only behavior. A persistent SQLite `application_id` marker makes a missing checkpoint after initialization fail closed rather than silently bootstrap a replacement chain.
- Successful financial writes and audit rows/checkpoint share the SQLite transaction. Failure outcomes are recorded after rejected operation rollback where possible; a failure to persist that rejection fails the request safely.
- SQLite connection busy timeout is 250 ms; writer acquisition retries use bounded backoff totaling about 375 ms in addition to SQLite waits. Exhaustion raises a safe database-busy audit error.
- No material deviation from the approved audit contract was identified. No guarantee is claimed against a privileged operator controlling database, application, and every secret.
- The sandboxed frontend build failure and the test iteration failures above are retained here as correction history; no raw stdout/stderr files were separately saved.

## OpenSpec progress and outstanding work

Before Block 2: 7/21 tasks complete. After verified tasks 2.1–2.6: 13/21 complete. Tasks 1.1–1.5, 2.1–2.6, and 5.1–5.2 are checked. Locust tasks 3.1–3.4, deployment tasks 4.1–4.3, and combined acceptance evidence task 5.3 remain pending.

## Telemetry and remaining risks

Codex session token/cost telemetry was not exposed to this execution environment; no values are reported. Remaining risks include key custody/backup and admin-token rotation being operator responsibilities, SQLite's single-writer scalability limit, and the 3 advisories reported by npm during locked dependency installation. Locust, container deployment, SonarQube, and final change closure were not in Block 2 scope.
