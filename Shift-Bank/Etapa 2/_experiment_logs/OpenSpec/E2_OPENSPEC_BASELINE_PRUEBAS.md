# Shift Bank Etapa 2 — Inherited Baseline Checks

These are checks of the inherited Stage 1 implementation copied to the Stage 2 destination. A syntax check, production build, or OpenSpec listing is not a functional automated test.

## Test discovery

- Backend: no `tests` directory, test files, `pytest` configuration, `tox.ini`, or `pyproject.toml` was found. `requirements.txt` contains no test runner.
- Frontend: no test files or Vitest/Jest/Playwright/Cypress configuration was found. `frontend/package.json` declares only `dev`, `build`, and `preview`; there is no test script.
- Actual backend automated tests: **NOT EXECUTED — none are present.**
- Actual frontend automated tests: **NOT EXECUTED — none are present.**
- Test totals: not applicable; no automated test cases were available.

## Checks executed

| Check | Exact command | Working directory | Result |
| --- | --- | --- | --- |
| Python syntax validation (not backend tests) | `& ".\backend\.venv\Scripts\python.exe" -m py_compile main.py database.py` | `Shift-Bank\Etapa 2\OpenSpec\backend` | Passed; exit code 0; no output |
| Frontend TypeScript check and production build (not frontend tests) | `npm run build` (`tsc && vite build`) | `Shift-Bank\Etapa 2\OpenSpec\frontend` | Passed; exit code 0; TypeScript check passed, 31 modules transformed, Vite 5.4.21 build completed |
| OpenSpec inherited-spec listing (structural check, not application test) | `openspec list --specs` | `Shift-Bank\Etapa 2\OpenSpec` | Passed; exit code 0; listed four inherited specs |
| OpenSpec change listing (structural check, not application test) | `openspec list` | `Shift-Bank\Etapa 2\OpenSpec` | Passed; exit code 0; “No active changes found.” |
| Codex CLI launch check (not an implementation session) | `codex --help` and `codex --version` | `Shift-Bank\Etapa 2\OpenSpec` | Passed; exit code 0; CLI reported `codex-cli 0.168.0` |

The Vite build generated `frontend/dist`, and Python compilation generated `backend/__pycache__`; both validation outputs were removed afterward. No application server was started and no database was opened, migrated, or modified.

Historical raw logs from the initial preparation remain preserved in this directory: `backend_py_compile.log`, `frontend_build.log`, `openspec_list_specs.txt`, and `openspec_list.txt`. The checks above were rerun during the audit to capture explicit exit codes.
