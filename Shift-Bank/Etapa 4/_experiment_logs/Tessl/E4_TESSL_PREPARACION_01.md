# Stage 4 preparation report — Tessl

## Scope and intent

This report records the safe preparation of an independent Stage 4 working environment for Shift Bank using the actual completed Stage 3 source, without modifying Stage 3, introducing Stage 4 functionality, or creating new functional specifications.

- Source (read-only): `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Tessl`
- Source evidence (read-only): `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Tessl`
- Destination (Stage 4 working copy): `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\Tessl`
- Evidence directory: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl`

## 1. Stage 3 status as inspected from the actual source and evidence

Stage 3 was reviewed from the actual working tree and the available Stage 3 evidence, not from memory or a previous preparation log alone.

### Verified architecture and artifacts
- Backend: FastAPI + SQLAlchemy + SQLite.
- Frontend: React + TypeScript + Vite.
- Supporting infrastructure: Docker Compose, nginx, TLS cert generation, deployment files.
- Security: encryption at rest, client/server encrypted field flow, key rotation expectations, fail-closed startup validation.
- Audit: append-only chain integrity with HMAC-SHA256-style security ledger semantics.
- SDD workflow: vendored Tessl plugin, `.agents`, `.codex`, `.github`, `.vscode`, `.tessl`, and rules.
- Testing: backend pytest suite and frontend Vitest suite.

### Stage 3 Option A workstreams
The actual Stage 3 implementation/evidence was classified as follows:

- Multi-currency/account migration support: not selected / not implemented / not evidenced as a Stage 3 deliverable.
- Event Sourcing / CQRS: not selected / not implemented / not evidenced as a Stage 3 deliverable.
- Zero Trust / step-up auth: not selected / not evidenced as Stage 3 requirement.
- Batch processing / Spring Batch: not selected / not evidenced as Stage 3 requirement.

### Verified state and caveats
- The Stage 3 baseline is an operational banking application with inherited security and audit safeguards.
- The Stage 4 task is specifically migration-oriented preparation and requirements capture, not feature implementation.
- The Stage 3 app is not to be modified. Its runtime artifacts and databases remain outside the Stage 4 source baseline.

## 2. What was copied to Stage 4

The following categories were preserved in the Stage 4 working tree:
- Backend application code and services.
- Frontend application code and tests.
- Project docs and specs.
- `.tessl`, `.agents`, `.codex`, `.gemini`, `.github`, `.vscode` integration metadata.
- Dependency manifests and lockfiles.
- Docker and deployment configuration.
- Existing test infrastructure and fixture files.
- Stage 3 source configuration needed to run or inspect the app without introducing new functionality.

## 3. What was excluded from the Stage 4 source baseline

The following were intentionally excluded from the copied source tree because they are generated, runtime, or mutable state and not part of the clean baseline:
- `node_modules`
- `dist`
- `build`
- `.pytest_cache`
- `.scannerwork`
- `__pycache__`
- coverage artifacts
- SQLite runtime files (`.db`, `.db-wal`, `.db-shm`)
- transient temp/log files

Reasoning: these are not source-controlled application logic and are not required to preserve the working baseline. Their exclusion avoids copying mutable runtime state or generated caches into Stage 4.

## 4. Stage 4 working copy creation and integrity

### Creation result
A clean Stage 4 working tree was prepared at:
`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\Tessl`

### File integrity status
The Stage 4 source baseline was revalidated against the Stage 3 source tree using SHA-256.

Observed result:
- Included source files: 112
- Matching files: 112
- Mismatches: 0
- Generated runtime files intentionally excluded from the clean baseline: 11

The baseline SHA manifest is stored in:
- `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl\E4_TESSL_BASELINE_SHA256.csv`

### Integrity evidence
- `E4_TESSL_BASELINE_SHA256.csv`
- `E4_TESSL_BASELINE_METADATA.json`
- `E4_TESSL_FILE_INVENTORY.csv` is part of the preserved evidence set when applicable

## 5. Tessl integration and junction verification

The Stage 4 copy preserves the actual installed Tessl integration by restoring the required skill links under the Stage 4 project integration directories:
- `.agents`
- `.codex`
- `.github`
- `.vscode`

All generated skill junctions resolve only to Stage 4 vendored Tessl skill directories under the Stage 4 project tree. No link resolves into Stage 1 or Stage 2.

Evidence:
- `E4_TESSL_JUNCTIONS.txt`

## 6. Configuration and environment facts

Actual tool and stack versions observed in the staged environment are recorded in the baseline metadata and evidence set.

Important facts:
- Tessl CLI version: observed and recorded in metadata.
- Vendored plugin: `tessl-labs/spec-driven-development` v2.0.1.
- Python environment and backend toolchain: actual project environment as installed in the Stage 4 working copy.
- Node/npm frontend toolchain: actual project lockfile and installed versions.

## 7. Regression and validation performed in Stage 4

The normal backend and frontend regression checks were run in the isolated Stage 4 copy only after safe setup and copy verification.

### Backend result
Command executed:
- `python -m pytest backend/tests -v`

Observed outcome:
- Exit code: 0
- Result: 86 passed, 3 warnings

### Frontend result
Command executed:
- `npm test`

Observed outcome:
- Exit code: 1
- Result: 37 passed, 2 failed
- Failure is isolated to the crypto Web Crypto client tests in `frontend/src/__tests__/crypto.test.ts`
- The failure is consistent with a WebCrypto/jsdom interop issue and was not resolved by modifying production code or tests.

### Frontend build result
Command executed:
- `npm run build`

Observed outcome:
- Exit code: 0
- Production build succeeded

Evidence files:
- `E4_TESSL_BASELINE_TESTS.txt`
- `E4_TESSL_FRONTEND_TESTS.txt`
- `E4_TESSL_FRONTEND_BUILD.txt`
- `E4_TESSL_FRONTEND_NPM_CI.txt`

## 8. Blockers and method deviations

### Confirmed issues
- The Stage 4 evidence was initially created in the wrong directory before being copied to the correct path.
- A prior cleanup operation removed the Stage 4 working tree; it was restored and then revalidated.
- The frontend inherited crypto tests remain blocked by a WebCrypto compatibility issue in the test environment. This was not resolved by making implementation changes.

### Non-destructive outcome
These are preparation incidents and inherited blockers, not Stage 4 implementation changes.

## 9. Stage 4 preparation status

This task is prepared and verified as a baseline environment, but not as a Stage 4 implementation.

Stage 4 preparation is complete as an environment and baseline preparation task:
- Stage 3 source preserved
- Stage 4 working copy created and isolated
- Stage 3 evidence preserved
- File integrity verified
- Backend regression captured
- Frontend validation captured
- Evidence archived under the corrected location
- No Stage 4 functionality implemented
- No new Stage 4 functional specifications generated

## 10. Human-readable final status

Stage 4 preparation complete; awaiting selection and approval of the common Stage 4 seed; no Stage 4 functionality implemented.

## 11. Exact evidence paths

- Stage 4 working copy: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\Tessl`
- Stage 4 evidence directory: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl`
- Preparation report: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl\E4_TESSL_PREPARACION_01.md`
- Incident report: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl\E4_TESSL_INCIDENTES_PREPARACION.md`
