# Frozen baseline and discovery

## Workspace
Independent copy created from Etapa 3/OpenSpec. Application/test source and OpenSpec directories are included. source-manifest-sha256.json records hashes for copied files and confirms byte identity.

## Environment observed
- Windows PowerShell; Python and Node.js available.
- Backend declarations: FastAPI, Uvicorn, Pydantic, pydantic-settings, cryptography >=42,<51; exact resolved Python versions are not frozen in requirements.txt.
- Frontend: React/React DOM ^18.3.1; TypeScript ^5.2.2; Vite ^5.3.1; @vitejs/plugin-react ^4.3.1; package-lock included.
- Backend regression: 54 tests passed (unittest; 8.096 s observed).
- Frontend regression: 9 cases, 8 passed, 1 failed because TypeScript was unavailable in the isolated workspace.
- Frontend build: blocked; tsc executable unavailable (dependencies not installed).
- OpenSpec strict validation attempted; CLI reported “Nothing to validate” for default invocation. --all validation remains to be run.
- No dependency install was performed.

## Architecture and inherited contracts
- Backend: Python FastAPI; SQLite via sqlite3; synchronous banking domain functions; Decimal/cents arithmetic.
- Frontend: React + TypeScript, Vite; API helper in frontend/src/api.mjs.
- Routes: GET /health/live, GET /health/ready, GET /api/accounts, GET /api/history, GET /api/admin/audit/verify; POST /api/transfers, POST /api/transfers/{tx_id}/confirm; GET/PUT /api/limits; GET/POST/PUT/DELETE /api/beneficiaries; GET/POST /api/ach-transfers and confirmation; GET/POST /api/recurring-schedules, confirmation, and pause/resume/cancel action.
- Transfer request: source_account_id, destination_account_id, amount (string); MFA confirmation: code (string).
- Account response exposes id, name, balance; no explicit currency field. History amounts are decimal strings with transfer/status/timestamp metadata.
- Sensitive routes enforce HTTPS. Encryption protects beneficiary/ACH/recurring recipient details. Audit events are appended in the same SQLite transactions as financial state changes; BEGIN IMMEDIATE and uniqueness constraints serialize/idempotently guard recurring effects. Background processor polls MFA expiry, ACH settlement, and schedules every second; restart recovery advances missed schedule occurrences.
- Schema is initialized and incrementally altered by backend/database.py; WAL enabled. Source has no database file. Fresh initialization seeds acc_checking at 5000000.00 and acc_savings at 15000000.00, plus historical 500000.00 and 100000.00 transfers. No runtime database was opened or modified.

## Inherited state versus D-02 and seed
- Code identifiers are acc_checking and acc_savings (not CHK-1001/SAV-2001); no EUR/GBP accounts are seeded.
- Balances are decimal strings without currency identity. Frontend validation/test language describes COP, but account schema and API do not store currency. Do not relabel or convert amounts.
- D-02 reference values cannot be applied as-is: identifiers differ, currency identity is implicit, and replacing values would destroy or reinterpret inherited value. No migration rate or account rename is approved.
- These are initialization assumptions, not a claim about persisted user state.
- Seed found: SEED-4_AnexoA_replicacion.md; SHA-256 9714EF4854501FB1000EB5790A5D3F27C0E787A00F97EFF9F88D8C5D61871BF9. Its complete text is preserved. Expected SEED-4.md and replication DOCX were not found; guide comparison and canonical-seed confirmation remain unresolved.
- D-01 through D-14 were not available in permitted Stage 3 OpenSpec or the expected guide; additional conflicts cannot be asserted. D-02 conflict is concrete above.

## Stage 4 impact and artifacts (read-only)
Likely artifacts cover currency-aware accounts/money, exact simulated conversion, durable domain events and replay, CQRS projections, inherited-state migration, and compatibility with transfers/ACH/recurring, limits/MFA, encryption/audit, idempotency/concurrency, API/UI, persistence/deployment, and executed acceptance evidence. Native workflow appears to use proposal, design, delta specs, tasks, then validation. No specification artifacts were created.

## Researcher checkpoint
Decide the intended currency and treatment of inherited acc_checking/acc_savings balances and history before applying D-02 or specifying migration. No balance relabeling, replacement, account-ID change, or migration rate was applied.
