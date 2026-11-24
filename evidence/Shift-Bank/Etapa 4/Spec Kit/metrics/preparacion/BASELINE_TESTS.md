# Stage 4 / Spec Kit — Baseline Test Record

**Execution status:** **NOT RUN — E4 isolation and dependency prerequisites were not established.**  
**Date:** 2026-11-16  
**Baseline copy integrity check:** `2026-11-16T05:09:58.9112245-05:00`
**Attribution:** GitHub Copilot preparation; no test result is attributed to the measured Stage 4 agent.

## E4 results

| Area | Command intended for later review | Result | Reason |
|---|---|---|---|
| Backend | `python -m pytest backend/tests -v --basetemp="<E4 Spec Kit>\.pytest-tmp"` | **NOT RUN** | The E4 copy has no virtual environment, and dependency installation is prohibited in preparation. The existing E3 tests/configuration were inspected but the entire suite was not executed to establish every side effect against E4-only resources. |
| Frontend Vitest | `npm.cmd run test -- --run` from `Etapa 4\Spec Kit\frontend` | **NOT RUN** | `node_modules` was deliberately excluded and `npm ci` was not run. |
| Frontend production build | `npm.cmd run build` from `Etapa 4\Spec Kit\frontend` | **NOT RUN** | Same dependency restriction; no build was started. |
| Docker deployment smoke | No command run | **NOT RUN** | Docker execution is prohibited during preparation; no active Compose resources were inspected or reused. |
| Locust | No command run | **NOT RUN** | Locust was not executed. |
| SonarQube | No command run | **NOT RUN** | No scan was executed. |

No tests or builds failed because none were run. No database or certificate was opened by this test-preparation step. The E4 workspace excludes the E3 SQLite databases, certificate directory, secret `deployment/docker.env`, `.venv`, `node_modules`, and E3 outputs.

## Historical E3 outcomes — references only

These are not E4 test results:

- E3 H9 final evaluation reports backend **97/97**, frontend **13/13**, build **PASS**, and isolated Docker smoke **9/9**.
- E3 HITO 0 recorded **47 inherited backend tests** and **12 frontend tests** at that earlier checkpoint.
- E3 Locust reports are historical E3 experiments; no E4 performance baseline exists.

The E3 acceptance review, final evaluation, HITO 0 readiness, and raw historical reports remain in their original E3 paths. The different E3 checkpoint counts are not combined or relabeled as an E4 run.

## Commands actually used for environment/provenance checks

Verification/version commands below returned exit code 0; test commands above were not invoked. The E3→E4 copy wrote only into the previously absent E4 destinations and completed with 105/105 hash matches.

- `git -C <repository> status --short --branch`
- `git -C <repository> rev-parse HEAD`
- `git -C <repository> log -1 --format=%H%n%cs%n%s`
- `git -C <repository> diff --numstat -- <E3 source/evidence paths>`
- `python --version`; E3 venv `python.exe --version`; `python.exe -m pip show fastapi pytest uvicorn`
- `node --version`; `npm.cmd --version`; `git --version`
- `gemini --version` (version query only; no agent session); `specify --version`; `code --version`; filtered `code --list-extensions --show-versions`
- `Get-FileHash -Algorithm SHA256` for packet and E4/Tessl seed files
- Deterministic copy and SHA-256 calculation for 105 E3→E4 files; separate full manifest recheck: **105 rows, 0 mismatches**

Git status emitted warnings for the three pre-existing E3 `.pytest-h8-*` directories (`Permission denied`). They were explicitly excluded; no ACL changes or retries were made.
