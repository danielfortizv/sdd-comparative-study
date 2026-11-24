# E4 Kiro handoff — preparation only

## Objective and inherited workspace

Stage 4 Option A evolves Kiro's own completed Stage 3 Shift Bank toward multicurrency accounts, simulated FX, Event Sourcing and CQRS. Prepared copy: `Etapa 4/Kiro`; source: `Etapa 3/Kiro`. FastAPI backend/tests: `backend/app/`, `backend/tests/`; React/TypeScript and Vitest: `frontend/src/`; load scripts: `loadtest/`; deployment: root `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`. Kiro specs: `.kiro/specs/shift-bank`, `shift-bank-stage2`, `shift-bank-stage3`.

Inherited safeguards include decimal/cents money arithmetic, atomic transfers, mock MFA and transfer limits, ACH/recurring controls, encrypted sensitive snapshots, append-only HMAC audit records and idempotent migrations. The DB defaults to `backend/app/shift_bank.db`; the inherited tests isolate SQLite per test. `SHIFT_AUDIT_HMAC_KEY` supplies the audit secret; encryption keys are external environment configuration.

## Verified seed and D-01–D-14 guide decisions

Canonical experiment seed: `Etapa 4/SEED-4.md`; unchanged evidence copy: `Etapa 4/_experiment_logs/Kiro/preparacion/SEED-4.md`; SHA-256 `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`. Its text matches the complete Annex A block extracted from the official guide. Guide, seed and summary exact paths/hashes are recorded in `source-verification.md`.

The official guide decision table and supplied summary agree on these contracts (the summary is not the original approval transcript):

- **D-01:** One fixed currency per account: USD, EUR or GBP; never mix currencies in one balance.
- **D-02:** Preserve CHK-1001 USD 2,500.00 and SAV-2001 USD 10,000.00; add EUR-3001 and GBP-4001 at 0.00.
- **D-03:** Backend Decimal; frontend BigInt/minor units; two-decimal strings; exact rational FX rates; HALF_UP once at the end; no fees or financial floating point.
- **D-04:** Internal transfers only within one currency; cross-currency flows only through `/api/conversions`.
- **D-05:** Durable append-only SQLite domain events separate from legacy audit; migration without double counting.
- **D-06:** CQRS projections update synchronously and atomically with events; deterministic rebuild; fail closed on inconsistency.
- **D-07:** USD-equivalent limits 5,000.00 per operation and 10,000.00 daily; MFA only when unrounded USD equivalent is strictly greater than 1,000.00.
- **D-08:** ACH originates only in USD; recurring internal transfers stay same-currency; recurring ACH is USD-only.
- **D-09:** Composite events; account version increments once per affected account; ACH debit at pending, no second debit at settlement, one refund on failure.
- **D-10:** Dashboard totals remain separated by currency; estimated USD is presentation-only.
- **D-11:** AES-GCM encryption, HMAC-chained audit, atomic event/projection/audit/idempotency effects, auditable failures.
- **D-12:** Preserve FastAPI, React, SQLite and Compose/Nginx/TLS deployment capability; do not claim unobserved deployment verification.
- **D-13:** UUID `Idempotency-Key` required for internal transfer, FX and ACH; exact replay has no new effects; changed payload with reused key returns 409.
- **D-14:** Expected account versions required; stale request returns 409 `ACCOUNT_VERSION_CONFLICT`; idempotency replay is checked before version validation.

## Mandatory inherited-data conflict

Kiro Stage 3 seeds checking at **COP 5,000,000.00** and savings at **COP 15,000,000.00** (`backend/app/seed.py`, integer cents; no account currency column). Its requirements identify COP and MFA at/above COP 1,000,000.00. D-02 instead requires USD reference accounts with different IDs and values. This is an unresolved COP/USD and account-identity migration conflict. Do not convert, reinterpret, overwrite or migrate monetary data until the researcher explicitly approves a reconciliation.

## Baselines, limitations and D1

Observed inherited baseline: backend **372 passed, 1 warning**; Vitest **3 passed**; production build **passed**. Commands, outputs, timestamps, exit codes and versions are in the preparation evidence folder. Source/copy SHA comparison: 117/117 matches; no Stage 3 source hash changed. Stage 3 SonarQube POST retains one unresolved/new `typescript:S8786` finding and a failed new-code Quality Gate; preserve it as inherited evidence. No Stage 4 functional tests, migrations, scans or benchmarks were run.

PRE-KIRO D1 snapshot (researcher supplied, 2026-11-18 America/Bogota): **Kiro Student**, 898.98/1000 credits used, **101.02 remaining**, reset displayed 2026-12-01. This is a starting snapshot, not Stage 4 consumption. The screenshot was supplied by the researcher; no local image copy is claimed. Future sessions, exports, actual messages, tool calls, timestamps and credit deltas belong under `preparacion/D1/`.

## Kiro workflow and approval gates

Begin with read-only discovery. Do not create Stage 4 `requirements.md`, `design.md` or `tasks.md`, edit code/tests, migrate data, or run functional tests during discovery. Kiro must use its native Specs workflow after discovery and only after researcher approval; pause for approval at specification and separate implementation gates. Keep this handoff and measurement evidence outside native Specs.

## Exact initial Kiro prompt — read-only discovery

“Read the Stage 4 seed and D-01–D-14 decision summary, then inspect only this Kiro Stage 3 implementation. Perform read-only discovery: inventory actual accounts, seeded balances/currency, limits, MFA, ACH, recurring payments, encryption, audit, migrations, deployment and regression contracts with file references. Explicitly flag the COP Stage 3 balances and account identity versus D-02's USD accounts as a researcher decision; do not convert or change data. Do not create or edit Specs, code, tests or migrations, and do not run tests. Return findings and questions only, then stop for researcher review.”
