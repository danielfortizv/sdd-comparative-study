# Post-correction regression record

| Check | Command | Result |
|---|---|---|
| Focused API | `python -m unittest discover -s tests -p test_api.py -v` (from `backend`) | 3 passed, including HTTP/API compatibility and OpenAPI response regression |
| Focused banking | `python -m unittest discover -s tests -p test_banking.py -v` (from `backend`) | 21 passed |
| Full backend with coverage | `python -m coverage run --data-file=../sonarqube/reports/.coverage-backend-postcorrection --source=main,banking,database,encryption,audit -m unittest discover -s tests -v` | 54 passed, 0 failed |
| Backend Cobertura | `python -m coverage xml --data-file=../sonarqube/reports/.coverage-backend-postcorrection -o ../sonarqube/reports/backend-coverage-postcorrection.xml` | XML generated; 890/996 lines, 89.36% |
| Frontend regression | `npm.cmd test` (from `frontend`) | 9 passed, 0 failed |
| Frontend LCOV run | `npm.cmd exec --yes --package=c8 -- c8 --reporter=lcovonly --reports-dir=../sonarqube/reports/frontend-coverage-postcorrection --include=src/api.mjs --include=src/validation.mjs --include=src/refreshPolling.mjs -- node --test tests/*.test.mjs` | 9 passed; LCOV 57/57 lines across the same 3 `.mjs` files (100% of measured paths); React TSX remains unmeasured |
| Production build | `npm.cmd run build` (from `frontend`) | TypeScript and Vite build passed; 34 modules transformed |
| Strict OpenSpec validation | `openspec.cmd validate --all --strict` | 6 passed, 0 failed |

Backend test output is `sonarqube/reports/backend-test-output-postcorrection.txt`; frontend output is `sonarqube/reports/frontend-test-output-postcorrection.txt`. Fresh reports are `backend-coverage-postcorrection.xml` and `frontend-coverage-postcorrection/lcov.info`; the configured Sonar paths were refreshed from these outputs. The original baseline coverage reports were copied to `*-baseline` filenames first.

The inherited backend regression exercised transfers, MFA, beneficiaries, ACH/refunds, limits, recurring execution, encryption/migration, audit integrity/atomicity, HTTPS API flows, multiprocess concurrency, and SQLite reader/writer behavior. No Locust run or Docker deployment was repeated. No final Sonar scan was performed.
