# E4 Kiro handoff — preparation only

## Objective and scope

Stage 4 Option A is to evolve Kiro's own completed Stage 3 Shift Bank implementation toward multicurrency accounts, simulated FX, Event Sourcing and CQRS. Kiro must perform discovery, author its native Specs, make architecture decisions through the approved workflow, and implement only after the required researcher gates. This handoff is experimental context, not `requirements.md` or `design.md`.

## Inherited workspace

Prepared copy: `Etapa 4/Kiro`; source: `Etapa 3/Kiro`. Backend is `backend/app/` (FastAPI, SQLite, encryption, audit, ACH, recurring, transfer limits); tests are `backend/tests/`. React/TypeScript frontend and Vitest tests are in `frontend/src/`. Load scripts are in `loadtest/`. Deployment assets are root `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `frontend/nginx.conf`. Kiro's inherited specs are in `.kiro/specs/shift-bank`, `shift-bank-stage2`, and `shift-bank-stage3`.

Inherited invariants include decimal money handling, atomic transfers, mocked MFA and configured limits; encrypted beneficiary and ACH snapshots; append-only HMAC audit records; migration idempotence; recurring/ACH safeguards; no sensitive plaintext in API responses. DB default is `backend/app/shift_bank.db`, overridden by config/environment/test monkeypatches. Audit HMAC key variable is `SHIFT_AUDIT_HMAC_KEY`; encryption keys are external configuration.

## Seed and decision references

Expected common seed location is a researcher-owned shared location outside native Kiro Specs. **Canonical seed is currently unavailable**: the only local `SEED-4.md` is an extracted appendix packet, and its own README states the standalone master was not supplied. Its extracted SHA-256 is `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`; this is not verified as the canonical original. The official replication guide was also not found. Do not proceed to specification authoring until the researcher supplies/verifies both.

The local D-01–D-14 sheet is explicitly a **summary**, not the full approval record. It describes: D-01 fixed USD/EUR/GBP per account; D-02 reference USD checking/savings plus zero EUR/GBP accounts; D-03 Decimal/BigInt minor units, exact rational rates and one final HALF_UP rounding; D-04 same-currency internal transfers, FX via conversion; D-05 durable append-only domain events separate from audit; D-06 synchronous atomic CQRS projections and deterministic fail-closed replay; D-07 USD-equivalent limits and strict greater-than MFA threshold; D-08 USD-only ACH and same-currency recurring internal transfers; D-09 composite event/version/ACH debit/refund rules; D-10 currency-separated dashboard totals; D-11 AES-GCM/HMAC/atomicity; D-12 preserve FastAPI/React/SQLite/Docker-Nginx-TLS; D-13 UUID idempotency semantics; D-14 mandatory account versions and stale-version conflict semantics. These are provisional summaries only, not approved exact contracts.

The packet also identifies an unresolved baseline conflict: historical decisions presume USD values/IDs while inherited Stage 3 may use different values and thresholds. Kiro should inventory actual Stage 3 behavior and report the conflict for researcher resolution; it must not convert balances or infer a reconciliation.

## Kiro workflow and gates

Begin with read-only discovery. Do not create or approve Stage 4 native Specs, change code, migrate data, or run functional tests until the researcher verifies the canonical seed and decision records and approves the discovery/requirements plan. Use Kiro's native Specs workflow, keep requirements/design/tasks in Kiro's native locations once authorized, and pause for explicit review at each specification and implementation approval gate. Keep the reference packet outside native Specs.

## Baseline and inherited limitations

Stage 3's final report records backend 372 passed, Vitest 3 passed, frontend build exit 0, and Docker/HTTPS validations passing. These are historical Stage 3 results, not Stage 4 baseline runs. Preparation did not run pytest, Vitest or build because a safe disposable external secrets setup was not established. Evidence/status: `Etapa 4/_experiment_logs/Kiro/preparacion/E4_KIRO_PREPARATION_STATUS.md`; copy hash list: `stage4_kiro_source_manifest.csv` in the same directory.

Inherited SonarQube POST limitation: one unresolved/new `typescript:S8786` finding and new-code Quality Gate ERROR. Preserve this observation without correction. The inherited scanner config references the Stage 3 project; never use it to submit Stage 4 analysis.

## First Kiro prompt (discovery only)

“Perform read-only Stage 4 discovery for Shift Bank Option A from this inherited Kiro Stage 3 workspace. Do not create or edit requirements.md, design.md, tasks.md, application code, tests, or migrations. First inventory the actual accounts, currencies/balances, limits, MFA, ACH, recurring, encryption, audit, migration, deployment, and test contracts with file references. Identify conflicts between inherited behavior and the provided Stage 4 decision summaries. The canonical common SEED-4.md and official replication guide are not yet verified; do not treat the local extracted packet or decision summaries as authoritative. Report the missing inputs and stop before proposing or approving specifications.”
