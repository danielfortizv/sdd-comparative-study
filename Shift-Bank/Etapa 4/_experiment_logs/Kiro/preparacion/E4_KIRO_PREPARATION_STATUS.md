# Stage 4 Kiro preparation status

Date: 2026-11-17 (local)

## Source inventory

- Source: `Etapa 3/Kiro`; destination: `Etapa 4/Kiro` (was absent before preparation).
- Git branch `ShiftBank`, revision `08311b42d1d5745540af459775b4bb24de181947`.
- The repository working tree was not clean; `git status --short` showed numerous unrelated Stage 2/3/4 artifacts and an existing untracked Stage 4 Kiro path during this preparation. Source files were not edited.
- Stage 3 Kiro tasks show task 36 checked. The final report says backend regression 372 passed, frontend Vitest 3 passed, and production build exit 0. It records Docker/HTTPS validation as passing.
- SonarQube PRE/POST: preserve the inherited limitation: one unresolved/new `typescript:S8786` at `AccountsPanel.tsx:17`; POST new-code Quality Gate ERROR (new coverage 39.7% below 80% and one new violation). No scan was run for Stage 4.
- DB path defaults to `backend/app/shift_bank.db`; tests patch `app.config.DB_PATH` and `app.db.DB_PATH` with temporary paths. Audit HMAC key comes from `SHIFT_AUDIT_HMAC_KEY`; encryption is externally configured. Inherited conftest contains a fixed test key, so baseline execution was withheld pending disposable external secret setup.

## Copy and exclusions

The Stage 3 Kiro tree was copied to `Etapa 4/Kiro` with backend, tests, frontend, `.kiro` specs, load-test scripts, Docker/Compose/Nginx, environment templates, scanner config, manifests and lockfiles. Excluded virtual environments, dependency trees, Git metadata, generated `loadtest/results`, caches, database/WAL/SHM files, credentials and key/certificate files. Generated backend coverage files copied by the first pass were removed. See `stage4_kiro_source_manifest.csv` for destination SHA-256 values. A complete source-to-destination comparison manifest has not yet been produced.

## Essential contract blocker

The official `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx` and standalone canonical `SEED-4(1).md` were not found in the supplied repository. The only seed is an extracted packet copy whose README explicitly says the standalone master was unavailable and records a provisional extracted hash `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`. It is not copied into the Kiro workspace or represented as canonical. The accompanying D-01–D-14 sheet labels itself a summary, not the full approved records. Therefore exact seed integrity, official guide review, exact approved-decision wording, and a verified handoff cannot be claimed.

## Baselines

Backend pytest, Vitest and production build were not run in this preparation. No test output is represented as a Stage 4 baseline. Tests should only run after isolated dependency setup and disposable database plus externally generated disposable encryption/audit secrets. No functional tests, migrations, scans or benchmarks were run.

## D1 protocol and initial balance

Start Stage 4 measurements at a new D1 baseline. Record a verified Kiro credit snapshot before the first measured interaction; current balance is `N/D`. For each session preserve export, start/end timestamps with timezone, actual user/agent message counts, tool calls by category, elapsed time, credit change and source evidence. Keep setup activity separate; never infer missing values. Preserve Stage 3 D1 evidence in its existing Stage 3 location.

## SonarQube isolation plan

The inherited `sonar-project.properties` names the Stage 3 component. Preserve it only as historical reference. Before any separately authorized Stage 4 scan, make a Stage 4-specific config with a new project key, Stage 4 base directory, fresh coverage imports, and explicit exclusions; never submit Stage 4 sources under the Stage 3 key. No scan was run.
