# Gemini CLI handoff — Shift Bank Stage 2 / Spec Kit

## Workspace and baseline

- **Stage 1 source (absolute):** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 1\Spec Kit`
- **Stage 1 source (repo-relative):** `Shift-Bank/Etapa 1/Spec Kit`
- **Stage 2 working copy (absolute):** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit`
- **Stage 2 working copy (repo-relative):** `Shift-Bank/Etapa 2/Spec Kit`
- **Start Gemini CLI from exactly:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit`
- **Evidence directory:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\_experiment_logs\Spec Kit`
- **Copy timestamp:** 2026-11-14T11:55:43.799604-05:00 (local time recorded at copy)
- **Git:** branch `ShiftBank`; HEAD `130ca53c2854e042f89c8a957182c7925b176d6f`. Repository and Stage 1 scoped status were clean before copying. Currently only Stage 2 application/evidence paths are untracked; Stage 1 scoped status is clean. No commit/staging.
- **Initial copy manifest:** `preparacion/E1_SOURCE_MANIFEST_SHA256.csv`
- **Initial Stage 2 manifest:** `preparacion/E2_COPIED_MANIFEST_SHA256.csv`
- **Initial comparison:** `preparacion/E1_TO_E2_COPY_COMPARISON.csv` — 59 copied, 0 missing, 0 changed, 0 unexpected.
- **Final Stage 2 pre-Gemini manifest:** `preparacion/E2_READY_FOR_GEMINI_SHA256.csv`
- **Copy-to-ready comparison:** `preparacion/E2_COPY_TO_READY_COMPARISON.csv` — 59 unchanged, 0 missing, 0 changed, 0 unexpected.
- **File counts:** 59 durable source files copied; 8,462 generated/dependency/runtime files excluded; no links/reparse points skipped.
- **Preparation-time infrastructure changes:** no application, Spec Kit integration, constitution, specification, dependency manifest, or lockfile files were changed. Only external evidence files were added. `node_modules`, `dist`, caches, and the Stage 2 test database are generated runtime artifacts and are excluded from the final manifest.

## Technology, runtime, and persistence

- Backend: Python 3.13.2, FastAPI 0.142.2, native SQLite (`sqlite3`), exact decimal-string amounts and Python `decimal.Decimal`.
- Backend entry points: `backend/src/main.py` (FastAPI app), `backend/src/api.py` (API router), `backend/src/database.py` (DB initializer).
- Backend tests: `python -m pytest backend/tests -v`; `backend/tests/test_api.py`.
- Persistence: `backend/src/database.py` resolves `backend/shift_bank.db` relative to the copied source. Its fresh-database initializer seeds two COP accounts and two historical transfers. Stage 2 tests used a Stage 2-local database only.
- Frontend: React 18, TypeScript, Vite 5.4.21, Vitest 2.1.9.
- Frontend entry points: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/services.ts`.
- Frontend scripts: `npm test`, `npm run build` (runs `tsc && vite build`), `npm run dev`.
- Node/npm: Node v20.17.0, npm 11.6.3; lockfileVersion 3.
- Backend dependency note: `backend/requirements.txt` is unpinned and has no lockfile. Existing system Python packages were used; no unpinned package install or upgrade was performed.
- `npm ci` used the existing Stage 1 `package-lock.json`; it emitted a Node engine warning because `@testing-library/jest-dom@7.0.1` requires Node >=22, while Node 20.17.0 was installed. Install, tests, and build passed. npm reported 12 vulnerabilities (9 moderate, 1 high, 2 critical); no remediation was run.

## Spec Kit and Gemini configuration

- Installed Spec Kit CLI: 1.0.6. The project `.specify/integration.json` also records 1.0.6.
- Installed Gemini CLI: 0.65.0.
- The Stage 1 Spec Kit protocol in `Shift-Bank/Etapa 1/_experiment_logs/Spec Kit/shared_environment.md` records Gemini CLI 0.60.0 and target model `gemini-3.5-flash`. The installed CLI version is a deviation; it was not changed. The `GEMINI_MODEL` environment variable currently says `gemini-3.5-flash`, but effective model routing has not been verified.
- No project `.gemini/settings.json` was present. Gemini authentication/billing and actual model routing were not tested.
- `.specify/integration.json` records Gemini as the default/installed integration; `.specify/init-options.json` records Gemini/PowerShell (`ps`) and `here: true`.
- `specify check` reported Gemini CLI available. `specify integration status` reported `Integration status: OK`, Gemini default/installed, zero modified or missing managed files, zero invalid manifest paths, exit 0.
- Ten Gemini commands are present under `.gemini/commands/`: `speckit.analyze`, `speckit.checklist`, `speckit.clarify`, `speckit.constitution`, `speckit.converge`, `speckit.implement`, `speckit.plan`, `speckit.specify`, `speckit.tasks`, and `speckit.taskstoissues`. Their presence and Spec Kit manifest status were verified. Interactive slash-command display was not tested because Gemini was not launched.
- The existing `.specify/memory/constitution.md` is Stage 1 version 1.2.0 and was copied unchanged. Existing `.specify/feature.json` still points to `specs/001-shift-bank-stage1`. The historical `specs/001-shift-bank-stage1/` feature spec and its checklist, API contract, data model, plan, research, quickstart and tasks remain present and unmodified.
- No Spec Kit init, reinit, integration install, or upgrade was performed.

## Stage 1 behavior (from Spec Kit Stage 1 only)

The Stage 1 specification and implementation define a pre-authenticated mock customer with exactly two own accounts, both COP-denominated: Checking and Savings. The code-defined fresh DB seed is COP 5,000,000 for Checking and COP 15,000,000 for Savings, plus two completed historical internal transfers (COP 500,000 Savings→Checking; COP 100,000 Checking→Savings). Internal transfers only are supported; non-positive amounts, same-account transfers, and overdrafts are rejected. Monetary values are represented as decimal strings and calculated with `Decimal`.

Sensitive transfers at or above COP 1,000,000 enter a pending state and require mock code `123456` within a five-minute window. Expiration is checked on confirmation (no background scheduler); incorrect codes may be retried; the balance is revalidated at confirmation. The documented routes include `GET /api/accounts`, `GET /api/accounts/{account_id}/history`, `POST /api/transfers`, and `POST /api/transfers/{transfer_id}/mfa`. Registration, login expansion, external bank connections, and third-party payment services are outside the inherited Stage 1 contract.

Important persisted-state difference: the tracked Stage 1 `backend/shift_bank.db` currently holds Checking COP 4,000,000, Savings COP 16,000,000, and five transfer rows (three beyond the code-seeded history). It was inspected read-only, SHA-256 `2FCD0C707E161807AC2AE54752D821ED0A95E1082F61BB5EDB6E10921FD5038A`, and confirmed unchanged. It was not copied. The source remains intact; Stage 2 tests ran on a separate DB. **Human decision required:** should the Stage 2 baseline derive from the reproducible code seed, or should the researcher provide an approved, safe migration fixture for the current historical state?

## Validation evidence

All paths below are relative to this evidence directory. `*_NORMALIZED.txt` files are readable UTF-8 copies of the captured PowerShell output; original capture files are retained alongside them.

- Backend: **12 passed**, 1 Starlette/httpx deprecation warning; exit 0 — [`pruebas/backend_pytest_NORMALIZED.txt`](./pruebas/backend_pytest_NORMALIZED.txt).
- Frontend: **5 passed** in 1 test file; exit 0 — [`pruebas/frontend_npm_test_NORMALIZED.txt`](./pruebas/frontend_npm_test_NORMALIZED.txt).
- Frontend typecheck/build: success (`tsc` + Vite build); exit 0 — [`pruebas/frontend_npm_build_NORMALIZED.txt`](./pruebas/frontend_npm_build_NORMALIZED.txt).
- Frontend dependency install: `npm ci` exit 0 — [`pruebas/frontend_npm_ci_NORMALIZED.txt`](./pruebas/frontend_npm_ci_NORMALIZED.txt).
- Spec Kit environment check: exit 0 — [`pruebas/specify_check_NORMALIZED.txt`](./pruebas/specify_check_NORMALIZED.txt).
- Spec Kit integration status: exit 0 — [`pruebas/specify_integration_status_NORMALIZED.txt`](./pruebas/specify_integration_status_NORMALIZED.txt).
- Spec Kit integration CLI help — [`pruebas/specify_integration_help_NORMALIZED.txt`](./pruebas/specify_integration_help_NORMALIZED.txt).
- Copy policy and excluded material — [`preparacion/COPY_EXCLUSIONS_AND_SKIPPED_LINKS.md`](./preparacion/COPY_EXCLUSIONS_AND_SKIPPED_LINKS.md).
- Read-only Stage 1 DB facts — [`preparacion/E1_DATABASE_READONLY_INSPECTION.txt`](./preparacion/E1_DATABASE_READONLY_INSPECTION.txt).

## Human checkpoints — do not begin Stage 2 specification yet

1. **PENDING HUMAN APPROVAL: COMMON STAGE 2 SEED.** No approved Shift Bank `SEED-2.md` was located. Do not invent one, infer one from Stage 1, or treat a retrospective reference as a prospective common seed. Supply the approved seed before feature specification.
2. `SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md` was not found anywhere in the repository. It was not read or used. Provide it if it is required as a retrospective alignment reference.
3. Resolve the Stage 1 mutable-database state question above before deciding Stage 2's data migration baseline.
4. Model/CLI protocol: E1 records CLI 0.60.0 and model `gemini-3.5-flash`; current CLI is 0.65.0 and `GEMINI_MODEL` matches, but effective routing is unverified. Confirm/accept the version deviation before collecting Stage 2 telemetry.

## Draft first Gemini message (discovery only; do not execute before human approval)

> You are beginning a discovery-only review for Shift Bank Stage 2 in this copied Spec Kit project. Do not edit any file, create or update specifications, plans, tasks, code, tests, or database state. First inspect the existing `.specify/` configuration, the preserved Stage 1 constitution and `specs/` artifacts, the application entry points, persistence initialization, and tests in this Stage 2 working copy. Review the researcher-approved common Stage 2 seed only after it is supplied. The later context is simulated third-party ACH/interbank transfers, recurring payment scheduling, and dynamic transfer limits; do not implement these capabilities or assume unresolved policy. Identify what the Stage 1 system already does, compatibility gaps, ambiguities, and questions for the researcher. Describe which Spec Kit-native specification/clarification/planning workflows would apply and propose artifacts, but do not invoke mutating workflows. Present findings and wait for explicit human approval before editing any Stage 2 specification or code.

## Researcher next-step sequence

1. Resolve the common seed approval and the Stage 1 database-state checkpoint; supply any approved safe migration fixture if required.
2. Review this handoff, the preparation record, and the 59-file final manifest.
3. Open `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit` in VS Code.
4. Before beginning telemetry, record the then-current Spec Kit/Gemini CLI versions and confirm protocol deviation/model routing. Launch Gemini CLI with its current directory exactly set to the Stage 2 Spec Kit path.
5. In Gemini CLI, check that the copied `/speckit.*` commands are available; do not run feature-writing commands yet.
6. Provide the approved common seed and request only the discovery message above. Capture the start of the Gemini session under `_experiment_logs/Spec Kit/sesiones/`.
7. Review Gemini's findings and approve the requirements/specification scope before any mutating Spec Kit workflow.

> Stage 2 business requirements, specifications, implementation, and tests have **not** been developed by Codex. Gemini CLI + Spec Kit will perform the SDD workflow after human approval.
