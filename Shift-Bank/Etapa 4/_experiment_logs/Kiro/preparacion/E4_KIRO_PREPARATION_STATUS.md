# Stage 4 Kiro preparation status

Updated: 2026-11-18 (America/Bogota)

## Source and copy integrity

- Source `Etapa 3/Kiro`; destination `Etapa 4/Kiro`. Git branch `ShiftBank`, revision `08311b42d1d5745540af459775b4bb24de181947`.
- 117 transferable files: 117 source/destination SHA-256 matches, 0 source hashes changed, 0 missing copies, 0 mismatches. Stage 3 was not modified by this preparation.
- Stage 3 Kiro tasks show task 36 complete. App areas: `backend/app/`, `backend/tests/`, `frontend/src/`, `loadtest/`; inherited Kiro specs under `.kiro/specs/`.
- Kiro Stage 3 actual seed data: checking (`kind=checking`) COP 5,000,000.00; savings (`kind=savings`) COP 15,000,000.00. The Stage 3 schema stores integer cents without a currency column; seed comments and specs identify COP. D-02 instead names CHK-1001 USD 2,500.00 and SAV-2001 USD 10,000.00 plus EUR-3001/GBP-4001 at zero. This is a material currency, identifier, and balance conflict. Researcher approval is required; no conversion or banking data change was made.
- DB default: `backend/app/shift_bank.db`; inherited test fixture patches per-test temporary DB paths. Test secrets were generated ephemerally for the observed baseline.

## Supplied source verification

Exact paths and SHA-256 values are recorded in `source-verification.md`. The supplied seed hash matches the required digest `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`. The guide's complete Annex A seed text, extracted from DOCX XML, is character-equivalent after whitespace normalization; the seed copy in this evidence folder is byte-identical to `Etapa 4/SEED-4.md`.

D-01 through D-14 were checked against the guide's decision table and the supplied summary sheet. The summary explicitly is not the original approval transcript; this preparation verifies the guide table/summary, not the missing original conversation records. The full decision references are in the handoff.

## Baseline and environment

- Backend pytest: **372 passed, 1 warning, exit 0**.
- Frontend Vitest: **3 passed, exit 0**.
- Frontend production build: **passed, exit 0**; 41 modules transformed.
- Environment: Python 3.13.2; isolated pip 24.3.1; Node.js v24.19.0; npm 11.17.0; Vitest 2.1.9; Vite 5.4.21.
- Exact successful command records, stdout, timestamps and exit codes are in this directory. Disposable `.venv`, `node_modules`, build output, caches, and pytest temporary DBs were removed after the baseline. No Stage 4 functional tests, migrations, SonarQube scans, or benchmarks were run.
- Stage 3 SonarQube POST limitation is inherited: one unresolved/new `typescript:S8786` at `AccountsPanel.tsx:17` and a failed new-code Quality Gate (new coverage 39.7% below 80%, one new violation). It was not altered.

## PRE-KIRO D1 credit snapshot

Researcher-provided snapshot dated **2026-11-18 (America/Bogota)**: Kiro Student plan; **898.98 / 1000 credits used**, **101.02 remaining**; next reset displayed **2026-12-01**. This is the PRE-KIRO D1 starting snapshot, not Stage 4 credit consumption. The screenshot was supplied by the researcher; no local screenshot image was identified or copied. Session exports and interaction tracking templates are under `D1/`. No Kiro session has been invoked or logged for this preparation; preserve future session timestamps, exports, actual messages, calls and credits there.

## Readiness and limits

Ready for Kiro read-only discovery using the prompt in `E4_KIRO_HANDOFF.md`. Resolve the COP/USD D-02 conflict with the researcher before finalizing specifications or implementing migration behavior. Do not infer FX conversion or overwrite inherited monetary values. Preserve the Stage 3 scanner configuration only as historical reference; any future authorized Stage 4 scan needs a separate project key.
