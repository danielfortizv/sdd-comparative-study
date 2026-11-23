# Shift Bank Etapa 2 — OpenSpec Preparation Record

## Purpose and scope

This record documents the focused audit and correction of the existing Stage 2 OpenSpec preparation. It does not authorize or record Stage 2 feature implementation. Stage 1 application code and specifications were not modified; no Stage 2 business specification or change proposal was created.

## Paths and Git baseline

- Source: `Shift-Bank/Etapa 1/OpenSpec`
- Destination / first Codex working directory: `Shift-Bank/Etapa 2/OpenSpec`
- Evidence directory: `Shift-Bank/Etapa 2/_experiment_logs/OpenSpec`
- Repository commit: `da4209dc3ea9eda08f13de08abe29800bcdf6513`
- Branch: `ShiftBank`

The Stage 1 source path has no tracked or untracked working-tree changes. All 37 Git-tracked source paths were verified against the recorded commit using Git's configured clean filters (`git hash-object --path` matched each `HEAD` object). The overall repository has unrelated uncommitted changes under Stage 2 Kiro and its logs; these were not changed.

There was no pre-copy SHA-256 inventory. The original source/destination manifests were produced after copying, so they cannot prove the source was unchanged before the initial copy. Current source contents do match the Git commit above. The original manifests and reports remain preserved under their original names as historical evidence.

The original post-copy source inventory contains the same 36 relative paths, sizes, and SHA-256 hashes as the corrected current source inventory. This establishes consistency since that post-copy inventory, but does not establish a pre-copy source state.

## Copy and corrected inventory

The corrected inventories include hidden files and would include a safe `.env.example` if present. No `.env.example` exists in this source. Real `.env`/`.env.*` files (except `.env.example`), credential/private-key material, databases, and generated artifacts are excluded.

- Eligible source files: 36
- Eligible destination files: 36
- Missing: 0
- Unexpected: 0
- Size/hash mismatches: 0
- Stage 2 files sharing a file identity with same-path Stage 1 files: 0
- Reparse points/symlinks/junctions in the destination: none
- Real environment files, credential/private-key files, and mutable database files in the copied project tree: none found
- Common private-key and credential patterns in copied project text files: no matches; values were not logged

Corrected evidence:

- `E2_OPENSPEC_BASELINE_SHA256.csv` — current eligible source inventory
- `E2_OPENSPEC_COPIA_SHA256.csv` — inherited eligible destination inventory; generated setup files are excluded
- `E2_OPENSPEC_VERIFICACION_COPIA.csv` — per-path SHA-256 comparison

The source contained excluded generated/dependency files in `backend/.venv` (2,912), `frontend/node_modules` (2,444), `frontend/dist` (3), and `backend/__pycache__` (2). `backend/bank.db` was excluded as mutable SQLite state. These exclusions account for the source files not represented in the working-copy baseline inventory.

The original copy procedure's ignore rules did not exclude `.env` files even though its inventory did. The current destination was audited independently: no real environment file or credential was found, and no secret values were written to the evidence. The corrected inventory rule explicitly excludes real environment files while preserving `.env.example`.

Files generated after copying are kept separate from the inherited baseline:

- `openspec init --tools codex --no-animation` generated `.agents/skills/.openspec-target` and six `.agents/skills/openspec-*` skill files.
- Environment setup created `backend/.venv` and `frontend/node_modules`.
- Validation-generated `backend/__pycache__` and `frontend/dist` were removed after checks.

The inherited `.gemini` directory was preserved as part of the Stage 1 baseline. Its presence does not change the selected Stage 2 tool: the experiment handoff is explicitly for Codex.

## Environment and dependency versions

| Tool/runtime | Version |
| --- | --- |
| Git | 2.48.1.windows.1 |
| System Python | 3.13.2 |
| Destination virtualenv Python | 3.13.2 |
| Node.js | v20.17.0 |
| npm | 11.6.3 |
| OpenSpec CLI | 1.9.0 |
| Codex CLI | codex-cli 0.168.0 |

Backend requirements are unpinned in `backend/requirements.txt`; the isolated destination environment resolved to:

`annotated-doc==0.0.6`, `annotated-types==0.8.0`, `anyio==4.16.0`, `click==8.5.1`, `fastapi==0.163.1`, `h11==0.16.0`, `idna==3.20`, `opentelemetry-api==1.45.2`, `pydantic==2.14.3`, `pydantic-settings==2.16.3`, `pydantic_core==2.50.4`, `python-dotenv==1.2.4`, `starlette==1.10.0`, `typing-inspection==0.4.5`, `typing_extensions==4.16.0`, `uvicorn==0.54.0`.

Frontend dependencies were installed from the existing lockfile. Installed direct versions: `@types/react-dom@18.3.7`, `@types/react@18.3.31`, `@vitejs/plugin-react@4.7.0`, `react-dom@18.3.1`, `react@18.3.1`, `typescript@5.9.3`, `vite@5.4.21`.

Installation commands previously executed in the destination:

```powershell
python -m venv "backend\.venv"
& ".\backend\.venv\Scripts\python.exe" -m pip install -r ".\backend\requirements.txt"
npm ci --prefix ".\frontend" --no-fund --no-audit
openspec init --tools codex --no-animation "C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\OpenSpec"
```

The backend requirements were installed without editing the manifest. The frontend used `npm ci`; neither application dependency manifest nor lockfile was changed by this audit.

## OpenSpec / Codex handoff

OpenSpec 1.9.0 is initialized in the destination. `openspec list --specs` exited 0 and exposes the four inherited specifications: `bank-accounts`, `mfa`, `transaction-history`, and `transfers`. `openspec list` exited 0 and reported no active changes. The archived change `2026-09-29-stage1-requirements` and its design, proposal, tasks, and archived specs are present.

The generated Codex integration is available under `.agents/skills` (apply, archive, explore, propose, sync-specs, and update-change). `codex --version` and `codex --help` both launched successfully from the destination working directory. No Codex session was opened, so runtime account authentication and in-session skill discovery were not exercised.

The Stage 2 experiment uses Codex, not the Gemini CLI described in the original research protocol. This is a methodological deviation and must remain visible in the final cross-tool comparison. No OpenSpec proposal, Stage 2 spec, implementation, or archive operation was run.

## Baseline verification status

See `E2_OPENSPEC_BASELINE_PRUEBAS.md` for exact commands, working directories, exit codes, and the distinction between syntax/build/structural checks and automated tests.

## Remaining limitations

- No pre-copy source inventory exists; Git confirms current Stage 1 content at the recorded commit but cannot establish the source's state before the original copy.
- No backend or frontend automated test suite/configuration was found. Syntax validation and a frontend build are not functional test coverage.
- Codex CLI startup and local integration files were verified, but authentication and live in-session skill discovery were not tested because no session was opened.
