# Shift Bank Stage 3 — OpenSpec initial state

Date: 2026-11-16 (America/Bogota)

## Inherited baseline

Stage 3 inherits the independent copy of `Etapa 2/OpenSpec`, whose Stage 2 change is `stage2-banking-enhancements`. Stage 2 reported 22/22 tasks complete, 22 passing backend tests, 5 passing frontend tests, a passing TypeScript/Vite production build, and passing strict OpenSpec validation. The final SonarQube analysis and its comparison are recorded in the original Stage 2 evidence. Manual acceptance remained partly unverified (A01–A21: 15 PASS, 5 PARTIAL, 0 FAIL, 1 NOT EXECUTED; A21 browser check not executed). These are historical records; this migration independently reran source verification and regression tests.

The Stage 2 OpenSpec change remains active and unsynchronized. It was neither archived nor synchronized. Four Stage 1 main specs coexist with seven Stage 2 delta specs; Stage 3 discovery must treat the active Stage 2 deltas as part of the effective inherited contract.

## Migration

- Source: `Etapa 2/OpenSpec`
- Destination: `Etapa 3/OpenSpec`
- Method: additive file copy into a destination confirmed absent before creation; source files were copied without edits.
- 62 files copied. Excluded: `.venv`, `node_modules`, `dist`, Python/Node caches, pytest/mypy/ruff caches, `.sonar`, Git metadata, SQLite/runtime database files and WAL/SHM files, environment secrets, and private key/certificate files.
- Stage 2 evidence remains at `Etapa 2/_experiment_logs/OpenSpec`; the evidence tree was not copied.
- Stage 3 copies retained the OpenSpec `.agents/skills` and project OpenSpec change/spec/config, backend, frontend, manifests, tests, and `.gemini` OpenSpec command/skill files.
- Hash comparison: 50/50 Stage 2 final manifest entries match byte-for-byte; 0 missing and 0 unexpected differences. Twelve copied `.gemini` OpenSpec command/skill adapter files are absent from that manifest and are listed as copied extras in the CSV.

## Verification

- Backend Python compilation: PASS.
- Backend unittest suite: 22/22 PASS. The tests create temporary SQLite databases; no historical database was opened or changed.
- Frontend Node tests: 5/5 PASS.
- Frontend production build: PASS (TypeScript and Vite 5.4.21; 33 modules). Initial sandbox build was denied while esbuild inspected an ancestor; retry with approved escalation succeeded.
- OpenSpec CLI 1.11.0: strict validation PASS, 5 items validated; active change listed complete and unarchived.
- Versions: Python 3.13.2, FastAPI 0.142.2, Uvicorn 0.54.0, Pydantic 2.12.5, Node.js 24.19.0, npm 11.17.0, OpenSpec 1.11.0, TypeScript 5.9.3, Vite 5.4.21. Stage 2 telemetry notes Codex CLI 0.168.0; model ID and complete session/token/cost telemetry were unavailable. No dependency versions were changed; frontend dependencies were installed from the existing lockfile for verification.
- Git root: `C:/Users/danie/Documents2/sdd-comparative-study`; HEAD `08311b42d1d5745540af459775b4bb24de181947`; branch `ShiftBank`. The shared worktree reports unrelated Spec Kit deletions and temporary artifacts, plus this run's untracked `Etapa 3/OpenSpec` copy. No Git metadata was copied into the Stage 3 project.

See `E3_OPENSPEC_BASELINE_SHA256.csv` for file-by-file migration comparison, `E3_OPENSPEC_REGRESION_PRE.txt` for command outcomes, and `E3_OPENSPEC_TRANSFERENCIA_E2.md` for inherited behavior and limitations.

## Seed integrity

The existing `Etapa 3/SEED-3.md` was preserved and verified byte-for-byte identical to the required canonical seed (1,535 bytes; SHA-256 `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`).
