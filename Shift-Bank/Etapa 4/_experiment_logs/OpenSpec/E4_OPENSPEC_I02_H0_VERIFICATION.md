# H0 verification — iteration 02

## Scope and result
H0 is **PARTIAL** overall: copy integrity is independently confirmed and frontend regression/build now pass. Canonical seed/guide verification is blocked because the referenced source documents were not found within the project. No functional source or Stage 4 specification was changed.

## Independent frozen-copy audit
Read `inventory.md` and the original `source-manifest-sha256.json` without modifying them. Parsed the UTF-8 BOM JSON and independently checked each relative path against Stage 3/OpenSpec and this Stage 4/OpenSpec destination. All 80 entries exist at both ends; each source hash matches `source_sha256`, each destination hash matches `copied_sha256`, all source/destination hashes match, and all `identical` flags are true. Independently summed source lengths: 441,008 bytes. Result: 80/80, 0 discrepancies.

Source and destination are distinct ordinary directories. Recursive ReparsePoint queries found no symlink/junction entries in the copied source or destination. Runtime database, WAL/SHM, `.env`, and credential files were excluded according to the inventory; a read-only filename scan found no DB or `.env` file in backend/frontend. No runtime DB was opened. Independent copy is supported by distinct roots and a physical file/hash comparison; it does not rely on live links to Stage 3.

## Source facts and historical backend result
`backend/database.py` initializes `acc_checking` at `5000000.00`, `acc_savings` at `15000000.00`, and synthetic transactions `tx_seed_1` for 500000.00 and `tx_seed_2` for 100000.00. `backend/tests/test_banking.py` explicitly tests legacy state migration while preserving a 4321000.00 checking balance. These are code/test fixtures, not evidence of production data.

Original evidence remains unchanged. `backend-tests-output.txt` reports `Ran 54 tests in 8.054s` and `OK`. `frozen-baseline-discovery.md` separately reports 8.096 seconds. Preserve both source-attributed observations; they differ by 0.042 seconds.

## Frontend recovery and result
Original `package.json` and lockfile v3 are consistent; `npm ci` succeeded in the E4 frontend. It added 68 packages; no package manifest changes were observed. Install warned that esbuild's lifecycle script was not covered by npm's allowScripts approval. Both exact scripts then succeeded: `npm.cmd test`: 9/9 passed, exit 0; `npm.cmd run build` (`tsc && vite build`): exit 0, Vite 5.4.21 built 34 modules. See `H0-frontend-install-iteration02.txt`, `H0-frontend-tests-iteration02.txt`, `H0-frontend-build-iteration02.txt`.

## Native OpenSpec
Installed CLI help confirms `validate --all`, `--changes`, `--specs`, `--archived`, and `--strict`. `openspec validate --all --strict` exit 0: six current specs/change targets passed. This is actual validation of inherited non-archived targets. It does not validate archived change task completion or runtime behavior. Historical default strict command output “Nothing to validate” is not evidence of spec validity; explicit all mode resolved the target ambiguity.

Workspace contains four inherited main specs (bank-accounts, mfa, transaction-history, transfers), active stage2 and stage3 changes, and archived changes dated 2026-09-29. Config schema is `spec-driven`. No Stage 4 change was created.

## Seed/reference integrity
Local evidence contains only `SEED-4_AnexoA_replicacion.md`; its previously reported SHA-256 is `9714EF4854501FB1000EB5790A5D3F27C0E787A00F97EFF9F88D8C5D61871BF9`. This iteration did not recompute its hash. The canonical `SEED-4.md`, replication DOCX, metrics guide PDF, and project stages PDF were not located within the repository tree. The annex hash is therefore a local reported hash, not a verified canonical reference hash. Complete D-01..D-14 contract comparison against those normative sources remains unverified. The supplied decision text is treated as analysis input only.

## Runtime and working tree
Observed Windows 11 environment (PowerShell; host version not independently collected); Python 3.13.2; Node v24.19.0; npm 11.17.0; OpenSpec CLI version not collected due PowerShell shim execution-policy behavior; `codex --version` via cmd: codex-cli 0.170.0. Resolved frontend versions from build/install: React 18.3.1, React DOM 18.3.1, TypeScript 5.9.2, Vite 5.4.21, plugin-react 4.3.4 (lock resolution). Python package exact versions were not inventoried.

`CODEX-INTERACTION-REGISTER.md` is a blank template. It contains no current or previous session IDs, prompts, agent/model identity, commands, timestamps, human interventions, or telemetry. Do not infer model or token counts. Source-level evidence, original raw command logs and new iteration02 logs are retained separately. Task elapsed time and model processing time are unavailable.

A repository-wide `git status --short` showed pre-existing unrelated Stage 3 Spec Kit deletions/untracked temporary artifacts and Kiro/experiment files, plus an untracked `Etapa 4/_experiment_logs/OpenSpec/bitacora.md`. This check is broader than this workspace and cannot attribute those changes to the present work. Stage 4/OpenSpec code/spec path edits were not made by this task; dependency installation created ignored node_modules and build output under frontend only.

## Commands executed this iteration
- `npm.cmd ci` (E4/OpenSpec/frontend)
- `npm.cmd test` (E4/OpenSpec/frontend), 9 pass/0 fail
- `npm.cmd run build` (E4/OpenSpec/frontend), exit 0
- `openspec validate --all --strict`, exit 0; explicit CLI help inspected
- Python read-only manifest/hash/size verifier, 80 entries / 441008 source bytes / 0 mismatches
- Read-only filesystem, symlink, runtime-db filename, and git status inspection

Command outputs and exit codes are preserved in the named iteration02 files. No backend rerun was needed.

## Integrity exception discovered at closeout — do not treat as PASS
The manifest explicitly includes `deployment\\.env.local` (415 bytes) in both Stage 3 source and Stage 4 destination. A redacted local structural scan found non-empty, non-placeholder values in the key configuration entries (including encryption/audit credential fields). Secret values were not emitted or included here. This contradicts the inventory statement that `.env`/private credentials were excluded. Hash equality remains 80/80 and establishes copying fidelity, but not safe exclusion. No file was opened for display, changed, removed, or transmitted. Do not inspect or use those credentials. Researcher/operator should handle the unexpected sensitive-file inclusion under their data-handling procedure before any further work. This triggers the user’s stop condition for unexpected integrity/scope failure.

Correction to runtime/dependency observations: OS reports Microsoft Windows version 10.0.26300.9974 (caption unavailable due denied OS query); OpenSpec CLI is 1.11.0. Lock-resolved React 18.3.1, React DOM 18.3.1, TypeScript 5.9.3, Vite 5.4.21, @vitejs/plugin-react 4.7.0. Earlier approximate versions in this report are superseded by these exact lock values. Python 3.13.2, Node v24.19.0, npm 11.17.0, Codex CLI 0.170.0.
