# Shift Bank E3 OpenSpec — Block 1 implementation record

Date: 2026-11-16 (America/Bogota)
Change: `stage3-banking-security-load-deployment`
Block: sensitive-data encryption, migration, HTTPS protection, inherited compatibility
Scope: Stage 3 Block 1 only. No audit implementation, Locust, container deployment, SonarQube, or archive/synchronization work.

## Workflow and traceability

Used OpenSpec CLI 1.11.0 and the installed `openspec-apply-change` skill with the `spec-driven` schema. `openspec.cmd instructions apply --change stage3-banking-security-load-deployment --json` reported ready, 0/21 tasks initially complete. Read the proposal, design, all five specs, task checklist, four inherited main specs, all seven Stage 2 delta specs, and relevant existing FastAPI, SQLite, React, and test files.

Implemented against `banking-data-protection` and `banking-compatibility`. Marked tasks 1.1–1.5 and 5.1 complete. Audit tasks 2.1–2.6, load-test tasks 3.1–3.4, deployment tasks 4.1–4.3, and deployment/load evidence task 5.3 remains unchecked.

## Implementation summary

- AES-256-GCM with fresh 96-bit random nonces; AAD binds table, row identifier, field name, and ciphertext format version.
- Versioned 256-bit keys are externally provided by `SHIFT_BANK_ENCRYPTION_KEYS` or `SHIFT_BANK_ENCRYPTION_KEYS_FILE`; `SHIFT_BANK_ACTIVE_KEY_VERSION` selects the write key. Old versions must remain provisioned while rows depend on them; startup migration atomically re-encrypts old-version rows to the active key and verifies them before commit. No key generation or plaintext fallback occurs in the application.
- Encrypted columns cover beneficiary name/bank/routing/account details, captured ACH recipient details, and recurring ACH recipient instructions. Authorized API behavior decrypts in memory and preserves existing response shapes.
- Legacy rows migrate in one SQLite write transaction at startup. Existing ciphertext is authenticated and checked. New ciphertext is immediately decrypted and compared before update. The migration marker commits only after the full scan succeeds. Any error rolls back all row updates; startup fails on unsupported/corrupt data or unavailable keys. Reruns verify and skip already encrypted fields.
- Sensitive API routes and responses require HTTPS. A proxy may assert HTTPS only when its source IP is explicitly configured in `SHIFT_BANK_TRUSTED_PROXY_IPS`. The browser helper blocks sensitive paths over HTTP before calling `fetch`.
- Added `backend/SECURITY.md` describing external provisioning and rotation.
- Design refinement from the approved proposal's envelope-key example: the implementation uses directly provisioned versioned 256-bit data keys. The security contract is unchanged; this simpler keyring is documented in the design and security instructions.

## Files created or modified

Created:
- `backend/encryption.py`
- `backend/SECURITY.md`
- `backend/tests/test_encryption.py`
- `frontend/src/api.mjs`
- `frontend/src/api.d.mts`

Modified:
- `backend/banking.py`
- `backend/database.py`
- `backend/main.py`
- `backend/requirements.txt` (adds `cryptography>=42,<51`; installed environment had 50.0.2)
- `backend/tests/test_api.py`
- `backend/tests/test_banking.py`
- `frontend/src/App.tsx`
- `frontend/tests/validation.test.mjs`
- `openspec/changes/stage3-banking-security-load-deployment/design.md`
- `openspec/changes/stage3-banking-security-load-deployment/tasks.md`

No package manifest or lockfile changes. Temporary `frontend/node_modules`, `frontend/dist`, and `backend/__pycache__` produced for verification were removed. Tests used temporary databases and temporary test certificates; no persistent or inherited database was opened.

## Commands and final results

- `openspec.cmd --version` → `1.11.0`.
- `openspec.cmd instructions apply --change stage3-banking-security-load-deployment --json` → ready, 0/21 at start.
- `python -m unittest discover -s tests -v` (cwd `Etapa 3/OpenSpec/backend`) → **35 tests, OK**. Includes encryption, tamper/AAD binding, missing/invalid/obsolete keys, rotation, plaintext rejection, legacy migration of beneficiary/ACH/schedule data, idempotence, transaction rollback, real subprocess restart, HTTPS API smoke, HTTP rejection, and inherited banking regression.
- `npm.cmd test` (cwd `Etapa 3/OpenSpec/frontend`) → **8 tests, 8 passed, 0 failed**.
- `npm.cmd ci` (cwd `Etapa 3/OpenSpec/frontend`) → 68 locked packages installed; npm warned that esbuild's install script was not approved, but the production build passed.
- `npm.cmd run build` (cwd `Etapa 3/OpenSpec/frontend`) → TypeScript and Vite passed; 34 modules transformed.
- `openspec.cmd validate --all --strict` → **6 passed, 0 failed** (including Stage 3 change and still-active Stage 2 change).

Historical Stage 2 test results were not rerun as Stage 3 results and are not included in the totals above.

## Initial failures and corrections

These are excerpts from initial command outputs in this implementation session; they are retained as debugging evidence, not final results.

1. Initial encryption/API focused run: migration rollback test failed because the fixture inherited a completed migration marker and expected no marker. The test now removes the marker before simulating an uncompleted migration.
2. Initial ciphertext-tamper test changed the final Base64 character, which can modify only unused padding bits; decryption therefore correctly saw unchanged bytes. The test now flips a bit in the decoded ciphertext/tag bytes.
3. Initial frontend test invocation used `npm.cmd --prefix frontend test` while cwd was already `backend`, yielding ENOENT for `backend/frontend/package.json`. Subsequent frontend commands ran from the frontend directory.
4. Initial full backend run: 33 tests, 2 failures. One test had erroneously applied ACH decryption to internal transaction rows; another showed ACH history returning ciphertext. Decryption was moved to the ACH history loop, and storage tests now assert ciphertext while API/history compatibility asserts decrypted values.
5. Initial frontend run: 8 tests, 7 passed, 1 failed because the test expected `assert.rejects` to return the error object. The test now captures the thrown error explicitly; final frontend suite passes 8/8.

## Evidence, telemetry, and limitations

This file records Block 1 evidence only and does not incorporate E2 results. No Codex session/token/cost telemetry was exposed through the available tools; none is estimated or fabricated.

HTTPS enforcement and API transport behavior were verified by local HTTPS smoke tests using a disposable self-signed certificate and by HTTP rejection tests. A production TLS termination/proxy deployment has not been implemented or verified; it belongs to a later authorized block. External key custody, backup/recovery, filesystem permissions, key re-encryption/removal procedures, and a full production key-provider integration remain operational responsibilities or future work.


