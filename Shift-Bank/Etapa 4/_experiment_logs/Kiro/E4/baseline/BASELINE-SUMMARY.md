# Stage 4 Kiro — Inherited baseline (Task 1) — observed evidence

Captured: 2026-11-18 (America/Bogota), Stage 4 workspace `Etapa 4/Kiro`.

## Observed results (real, not asserted)

- **Backend Pytest:** `372 passed, 3 warnings, exit 0` (22.79s). Evidence:
  `backend-pytest-baseline.txt`. The 3 warnings are a `.pytest_cache` write-permission
  notice (WinError 5) plus deprecations, not test failures.
- **Frontend Vitest:** `3 passed (1 file), exit 0`. Evidence: `frontend-vitest-baseline.txt`.
- **Frontend production build:** `41 modules transformed, built in 877ms, exit 0`. Evidence:
  `frontend-build-baseline.txt`.

## Environment (observed)

- Python 3.13.2; pip 26.2.1; venv isolated at `backend/.venv`.
- Node v20.17.0; npm 11.6.3.
- Dependencies installed at pinned versions (fastapi 0.115.5, pytest 8.3.4, httpx 0.28.1,
  cryptography 50.0.2, locust 2.47.0, pytest-cov 7.1.0, coverage 7.17.3, pydantic 2.10.3,
  uvicorn 0.32.1). Evidence: `pip-install.log`, `frontend-npm-install.log`,
  `environment-versions-*.txt`.

## Differences vs. preparation baseline (recorded, not hidden)

- Prep recorded Node **v24.19.0 / npm 11.17.0**; this machine has Node **v20.17.0 / npm 11.6.3**.
  Backend/Vitest/build results match prep (372 / 3 / 41 modules) despite the Node difference.
- Prep recorded backend "372 passed, 1 warning"; here "372 passed, 3 warnings" — same pass
  count; extra warnings are environment/cache notices, not failures.

## Isolation

Backend tests isolate a temp SQLite DB per test (`conftest.py`); test-only keys set via
`setdefault`. No Stage 3 data or DB was read or modified. Disposable `.venv`, `node_modules`,
and build output remain local and are not part of the committed evidence.
