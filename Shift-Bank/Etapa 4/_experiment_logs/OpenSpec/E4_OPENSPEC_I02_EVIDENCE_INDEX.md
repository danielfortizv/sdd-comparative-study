# Iteration 02 evidence index

New artifacts in this iteration:
- `E4_OPENSPEC_I02_H0_VERIFICATION.md` — independent manifest audit, runtime, H0 outcomes, references and telemetry limits.
- `E4_OPENSPEC_I02_H1_IMPACT_MATRIX.md` — requested architectural and contract traceability.
- `E4_OPENSPEC_I02_DECISIONS_D01_D14.md` — per-decision status and source evidence.
- `E4_OPENSPEC_I02_D02_MIGRATION_OPTIONS.md` — technically distinct migration choices and invariant/approval needs.
- `E4_OPENSPEC_I02_SPECIFICATION_PLAN.md` — native workflow plan only.
- `H0-frontend-install-iteration02.txt`, `H0-frontend-tests-iteration02.txt`, `H0-frontend-build-iteration02.txt`, `H0-openspec-validation-iteration02.txt` — raw command outputs and exit codes.

Historical evidence read and preserved unchanged: `inventory.md`, `frozen-baseline-discovery.md`, `source-manifest-sha256.json`, original backend/frontend command/output files, original OpenSpec validation files, `CODEX-INTERACTION-REGISTER.md`, local `SEED-4_AnexoA_replicacion.md`.

Commands this iteration: `npm.cmd ci`; `npm.cmd test`; `npm.cmd run build`; installed CLI help (`openspec --help`, `openspec validate --help`); `openspec validate --all --strict`; read-only Python manifest/hash/size verifier; PowerShell filesystem/runtime/reference and `git status --short` inspections. Backend tests were not rerun. No test code, application source, Stage 4 OpenSpec artifacts, seed files or other tool workspace were changed. Dependency/build outputs are local E4 frontend artifacts only.

Raw prompt/session transcript and model/token telemetry are unavailable. The interaction register was blank; no synthetic values were added. The metrics/replication reference documents are missing from the locally searchable project, so common-decision canonical verification remains incomplete.

Closeout exception: the source manifest includes `deployment\\.env.local` containing non-empty non-placeholder values for protected key fields. No secret value is reproduced. This contradicts the stated exclusion policy, so H0 overall is PARTIAL and the unexpected sensitive inclusion is an integrity/scope failure. Stop further work at checkpoint A. No modification/removal occurred.
