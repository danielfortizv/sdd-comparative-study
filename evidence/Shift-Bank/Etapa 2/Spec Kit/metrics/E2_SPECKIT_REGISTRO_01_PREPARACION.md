# Shift Bank Stage 2 — Spec Kit preparation record

**Status:** Preparation complete with human checkpoints pending; Stage 2 SDD work has not started.  
**Preparation date:** 2026-11-14  
**Source:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 1\Spec Kit`  
**Destination:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit`  
**Evidence:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\_experiment_logs\Spec Kit`

## 1. Scope and source selection

The Stage 1 Spec Kit source was unambiguous: `Shift-Bank/Etapa 1/Spec Kit` contains the Shift Bank application, its historical `specs/001-shift-bank-stage1` artifacts, `.specify/` project configuration, PowerShell workflow scripts/templates, and `.gemini/commands/` Gemini integration. No Stage 2 Spec Kit destination existed before preparation. The destination was created as a sibling at `Etapa 2/Spec Kit`.

The repository is `C:\Users\danie\Documents2\sdd-comparative-study`, branch `ShiftBank`, HEAD `130ca53c2854e042f89c8a957182c7925b176d6f`. The pre-copy repository and Stage 1 scoped statuses were clean. Stage 1 remains unchanged.

## 2. Copy and file integrity

The filtered copy used Python `os.walk(..., followlinks=False)` and `shutil.copy2`; Windows reparse points and symbolic links are not followed. SHA-256 is calculated from raw file bytes. Manifest paths are deterministic POSIX-style relative paths, including leading-dot directories.

- Eligible files copied: **59**
- Excluded generated/dependency/runtime files: **8,462**
- Skipped symbolic links/reparse points: **0**
- First comparison: **59 copied, 0 missing, 0 changed, 0 unexpected**
- Final pre-Gemini comparison against the first copy: **59 unchanged, 0 missing, 0 changed, 0 unexpected**

The source and copy manifests are in `preparacion/E1_SOURCE_MANIFEST_SHA256.csv` and `preparacion/E2_COPIED_MANIFEST_SHA256.csv`. The first comparison is `preparacion/E1_TO_E2_COPY_COMPARISON.csv`; the post-validation copy-to-ready comparison is `preparacion/E2_COPY_TO_READY_COMPARISON.csv`; the final manifest is `preparacion/E2_READY_FOR_GEMINI_SHA256.csv`.

Exclusions include 8,440 `frontend/node_modules` files; 9 files under `.pytest_cache`; 4 under `.ruff_cache`; 5 under `__pycache__`; 3 under `frontend/dist`; and the mutable SQLite database. `.env` secrets, build products, caches, local histories/dumps and temporary artifacts were excluded by policy. `.env.example` would be retained if present. See `preparacion/COPY_EXCLUSIONS_AND_SKIPPED_LINKS.md` for the precise policy and observed entries.

The original Stage 1 `.specify/`, `.gemini/commands/`, constitution, historical specification, API contract, data model, plan, tasks, tests, source, package manifests, and `package-lock.json` were copied without rewriting. No Stage 2 specification, plan, task list, seed, code, or tests were authored.

## 3. Stage 1 SQLite state and migration checkpoint

`backend/shift_bank.db` is a Git-tracked Stage 1 file and was deliberately not copied because it is mutable runtime state. A read-only SQLite inspection recorded its SHA-256 as `2FCD0C707E161807AC2AE54752D821ED0A95E1082F61BB5EDB6E10921FD5038A`; `git diff --quiet HEAD -- <database path>` returned 0.

The current Stage 1 database contains two accounts at COP 4,000,000 and COP 16,000,000 and five transfers. The code-defined fresh database initializer instead seeds COP 5,000,000 and COP 15,000,000 plus two historical transfers. The current runtime state is therefore not reproduced by the initializer. Stage 1 remains intact, but this mutable historical state is not present in the Stage 2 copy. A researcher must decide whether the Stage 2 baseline is intended to start from the reproducible code seed or whether a separately approved, safe migration fixture is needed; Codex did not copy or transform the database. Exact inspection facts are recorded in `preparacion/E1_DATABASE_READONLY_INSPECTION.txt`.

Backend tests created a separate `backend/shift_bank.db` inside Stage 2. It is generated test state, not part of the 59-file baseline manifests. No Stage 1 database was used by Stage 2 tests.

## 4. Spec Kit and Gemini integration

The copied `.specify/integration.json` reports Spec Kit 1.0.6 and Gemini as both the installed and default integration. There are ten copied Gemini slash-command TOML files: analyze, checklist, clarify, constitution, converge, implement, plan, specify, tasks, and taskstoissues. `.specify/integrations/gemini.manifest.json` declares the managed paths and hashes. The Stage 1 feature metadata still points to `specs/001-shift-bank-stage1`; the Stage 1 constitution (version 1.2.0) is preserved unchanged.

Installed `specify version` reported 1.0.6. The read-only `specify check` reported Gemini CLI available and exited 0. `specify integration status` exited 0 and reported Gemini as the default/installed integration, no modified or missing managed files, and no invalid manifest paths. The integration already works, so no init, reinstall, upgrade, or recovery was performed.

Gemini CLI `--version` reported 0.65.0. Stage 1's Spec Kit protocol records target Gemini CLI 0.60.0 and model `gemini-3.5-flash`. The current `GEMINI_MODEL` environment variable is `gemini-3.5-flash`, but effective routing cannot be confirmed without an authenticated session. The CLI version differs from protocol; no global or tool version was changed. Gemini was not launched for an agent turn, so authentication, billing, effective model, slash command display inside an interactive session, and session telemetry remain unverified. No project `.gemini/settings.json` exists.

## 5. Baseline validation

All commands ran only inside `Etapa 2/Spec Kit`; raw captures and readable UTF-8 normalized copies are in `pruebas/`.

| Validation | Result |
|---|---|
| `python -m pytest backend/tests -v` | Exit 0; **12 passed**, 1 Starlette/httpx deprecation warning |
| `npm ci` | Exit 0; 304 packages installed from lockfile; reported 12 vulnerabilities (9 moderate, 1 high, 2 critical); no remediation |
| `npm test` | Exit 0; **1 test file passed, 5 tests passed** |
| `npm run build` | Exit 0; TypeScript check and Vite production build succeeded |
| `specify check` | Exit 0; CLI reported ready and Gemini CLI available |
| `specify integration status` | Exit 0; Gemini integration OK, zero modified/missing managed files or invalid paths |

`npm ci` emitted an engine warning because the locked `@testing-library/jest-dom@7.0.1` requires Node `>=22`, while the observed Node version is `20.17.0`. The install, tests and build nevertheless succeeded. No dependency versions or lockfiles were changed. Backend packages were already available in the system Python 3.13.2 environment; because `backend/requirements.txt` is unpinned and has no lockfile, Codex did not create an unpinned environment or upgrade packages.

No database migration, SonarQube run, browser/manual scenario, Gemini prompt, or Stage 2 SDD command was executed.

## 6. Human decisions before Stage 2 specification work

1. **Common Stage 2 seed:** no approved Shift Bank `SEED-2.md` was found. Status: **PENDING HUMAN APPROVAL**. Do not treat the Stage 1 seed prompt or a retrospective Tessl document as the prospective common seed.
2. **Retrospective reference contract:** `SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md` was not found in the repository. It has not been read or used.
3. **Mutable database state:** decide whether Stage 2 should start from the code-defined fresh seed or require an approved, separate reproducible migration fixture reflecting Stage 1's current tracked DB state. The Stage 1 DB remains untouched and excluded.

Stage 2 functional scope is context only for later SDD: simulated ACH/interbank transfers, recurring payments, and dynamic transfer limits. No real bank connection, external payment gateway, authentication expansion, or later-stage functionality is authorized by this preparation.

## 7. Preparation incidents and changes

The first copy-script attempt stopped on a script error before copying files. It created only empty Stage 2/evidence directories; those exact empty directories were inspected and removed with non-recursive empty-directory removal. The corrected copy then completed and passed the 59-file comparison. No source data was deleted or altered.

The only persistent changes are the new Stage 2 Spec Kit working copy and its dedicated `_experiment_logs/Spec Kit/` evidence. Dependency installation and validation generated `frontend/node_modules`, `frontend/dist`, Python caches, and the isolated Stage 2 database; these are excluded from final baseline manifests. No files outside the Stage 2 application and its evidence directory were modified. No commit or staging operation was performed.

## 8. Required status

Stage 2 is prepared as an isolated, reproducibly hashed Spec Kit workspace with a verified Gemini integration and recorded baseline results. It is **not yet cleared to begin feature specification** until the researcher approves the common seed and decides how to handle the divergent tracked Stage 1 SQLite runtime state. The handoff file is `E2_SPECKIT_GEMINI_HANDOFF.md`.

> Stage 2 business requirements, specifications, implementation, and tests have **not** been developed by Codex. Gemini CLI + Spec Kit will perform the SDD workflow after human approval.
