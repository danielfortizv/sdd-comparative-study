# Stage 4 preparation record — Tessl

## 1. Stage 3 architecture and inherited capabilities

Stage 3 is a brownfield evolution of Stage 2 that keeps the banking core but adds enterprise-grade security, auditability, deployment controls, and benchmark validation.

### Backend architecture
- FastAPI application in `backend/app/main.py`
- SQLAlchemy + SQLite in `backend/app/database.py`
- Router set: accounts, transfers, transactions, beneficiaries, limits, recurring, crypto, and audit
- startup lifecycle runs secret validation, table creation, seed initialization, encryption migration, scheduler startup
- primary business services include account_service, transfer_service, recurring_service, limit_service, crypto_service, audit_service, migration_service

### Frontend architecture
- React + TypeScript + Vite app in `frontend/`
- API layer wraps encrypted payload handling and key refresh logic
- Tests cover accounts, transfers, MFA, recurring payments, limits, and crypto

### Security and operational capabilities inherited from Stage 3
- RSA-OAEP / AES-GCM field-level encryption for sensitive values
- server-side encryption-at-rest and startup migration validation
- append-only HMAC audit ledger with fail-closed behavior
- Docker Compose + nginx reverse proxy + TLS configuration
- persistent SQLite volume and secret validation rules
- load-performance benchmark and deployment smoke checks

### Tessl SDD readiness
- vendored plugin: `tessl-labs/spec-driven-development` version `2.0.1`
- `tessl.json` declares vendored mode and the agent list
- `.tessl/RULES.md` references the required spec-before-code workflow
- `.agents`, `.codex`, `.github`, and `.vscode` skill junctions point to the vendored skills
- 16 junctions recreated in Stage 4, all pointing to `Stage 4\Tessl\.tessl\plugins\...`

## 2. Stage 4 copy status and paths

- Source Stage 3: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Tessl`
- Destination Stage 4: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\Tessl`
- Evidence directory: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl`

Stage 4 was created as an isolated working copy. The copy excludes runtime artifacts such as `node_modules`, `dist`, `.pytest_cache`, `.scannerwork`, `__pycache__`, coverage and SQLite journal files. The Stage 4 copy intentionally does not include Stage 3 mutable runtime state or generated caches.

### Correction of evidence directory
A previous preparation attempt wrote evidence to `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4_experiment_logs\Tessl`. That directory was retained as historical evidence, and the same files were copied to the correct location `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl` without overwriting any original record.

## 3. SHA-256 baseline verification results

Baseline comparison was run against Stage 3 for the included source files only. Included file count = 112; `MATCH = 112`, `MISMATCH = 0`, with intentionally excluded runtime artifacts noted separately.

Evidence:
- `E4_TESSL_BASELINE_SHA256.csv`
- `E4_TESSL_BASELINE_SPECS.csv`
- `E4_TESSL_BASELINE_METADATA.json`

## 4. Inherited test and build results

### Backend baseline
Command run:
- `python -m pytest backend/tests -v`

Result:
- exit code 0
- 86 passed, 3 warnings in 5.27s

### Frontend baseline
Commands run:
- `npm ci`
- `npm test`
- `npm run build`

Results:
- `npm ci` exit code 0
- `npm run build` exit code 0
- `npm test` exit code 1

The frontend test failure is isolated to the crypto client tests in `src/__tests__/crypto.test.ts`. The failure indicates that `SubtleCrypto.importKey` receives an invalid key buffer format during the RSA-OAEP client-side encryption path. This is a reproducible blocker affecting the Stage 4 migration baseline and must be resolved by explicit stakeholder-approved design or a change request before implementation proceeds.

Evidence files:
- `E4_TESSL_BASELINE_TESTS.txt`
- `E4_TESSL_FRONTEND_NPM_CI.txt`
- `E4_TESSL_FRONTEND_TESTS.txt`
- `E4_TESSL_FRONTEND_BUILD.txt`

## 5. Migration risks and compatibility concerns

1. Multi-currency and monetary semantics are not yet established; Stage 3 currently assumes a single USD-like banking model.
2. Event Sourcing/CQRS will need to coexist with the existing immutable audit ledger; verification semantics differ from event replay semantics.
3. The crypto tests show a real compatibility problem in the frontend Web Crypto path for imported server keys; this is an inherited defect that must be understood before changing any Stage 4 architectural model.
4. Persistent database and deployment configuration are tied to security and runtime assumptions that must remain compatible with migration requirements.
5. Stage 3 uses strict secret validation and fail-closed migration logic; any Stage 4 migration must preserve these invariants.

## 6. Proposed tool-neutral Stage 4 requirement seed

Draft seed (not yet approved for implementation):

- The Stage 4 architecture must evolve the existing Stage 3 banking application without replacing its banking core.
- Account identities must support explicit currency metadata while preserving existing balances and customer behaviors.
- Multi-currency balances, transfers, and transaction history must maintain monetary integrity and deterministic conversion semantics.
- Historical Stage 3 balances and transactions must be migrated in a traceable, auditable manner.
- Event Sourcing must be modeled as an authoritative financial event stream, with replay, ordering, and idempotency rules that are compatible with the existing audit ledger.
- CQRS must separate command validation from read-side projection logic without weakening current authorization or audit guarantees.
- The Stage 3 encryption and audit safeguards must remain effective across the migration and any future projections.
- The migration must preserve current MFA, recurring-payment, ACH, and dynamic-limit behavior.
- Any exchange-rate source, currency set, precision policy, and conversion fee rules require explicit stakeholder approval before implementation.

## 7. First essential unresolved stakeholder decision

The most critical unresolved decision is:

- Which currencies are supported at launch, what exchange-rate source and update cadence are approved, and what rounding/precision rules govern conversion and balances?

Without this decision, any Stage 4 model for multi-currency accounts, conversions, and event/replay semantics would be speculative and not ready for implementation.

## 8. Preparation incidents and corrections

1. The evidence directory was initially created under `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4_experiment_logs\Tessl` instead of the required `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl`.
2. A cleanup command removed the Stage 4 working tree before the copy could be revalidated; the tree was restored from the Stage 3 source and the restored copy was compared against the Stage 3 baseline before any implementation work.
3. The frontend crypto test suite remains blocked by two inherited failures in `src/__tests__/crypto.test.ts`; both fail with the same `SubtleCrypto.importKey` invalid key buffer error.
4. Runtime artifacts created during validation (`.coverage`, `.pytest_cache`, `.scannerwork`, and SQLite database files) remain outside the clean source baseline and must be treated as generated state, not as part of the source-controlled Stage 4 copy.

## 9. Decision status

This report is a preparation and baseline record only. No Stage 4 implementation, specification changes, or production changes were made. The current Stage 4 copy is not yet a pristine implementation-ready baseline because the working tree still contains generated runtime artifacts and the inherited frontend crypto tests remain blocked. The next action should be explicit stakeholder approval on the currency, conversion, and migration policy before any Stage 4 specification or implementation work begins.
