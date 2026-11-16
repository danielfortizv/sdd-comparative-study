# Shift Bank E2 — OpenSpec Implementation and Initial Measurement

## Status

- Approved change: `stage2-banking-enhancements` (`spec-driven`).
- Implementation tasks: 22/22 complete (confirmed by `openspec instructions apply`).
- REC-D03 is in the recurring-payments delta: late MFA confirmation rejects activation, leaves no executable schedule, produces no debit, and explains that the first run time passed. No new specification edit was needed in this verification turn.
- This record covers implementation verification and the attempted INITIAL SonarQube measurement only. The independent human audit and correction round has not started.
- No sync, archive, commit, or application code modification was made during this verification turn.

## Implemented functionality and files

Implementation is detailed in `E2_OPENSPEC_IMPLEMENTATION_LOG.md`; source and test files there remain the implementation record. The implemented areas are:

- Additive SQLite persistence for limits, beneficiaries, ACH transfers, schedule occurrences, and Stage 1 completion timestamps.
- Exact COP amounts, shared backend-enforced per-transfer and UTC daily limits, MFA revalidation, and once-only internal-transfer accounting.
- Saved/ad hoc beneficiaries, simulated ACH pending/settled/failed lifecycle, 30-second settlement, deterministic internal failure selection, exact-once refunds, history snapshots, and recovery.
- Recurring internal/ACH schedules with creation MFA, REC-D03, 1/7/30-day UTC cadence, state controls, missed-occurrence skipping, execution-time validation, and idempotent processing.
- React flows for limits, internal/ACH transfers, beneficiaries, MFA, schedules, and history.

The implementation source/test files are `backend/banking.py`, `backend/database.py`, `backend/main.py`, `backend/tests/test_banking.py`, `backend/tests/test_api.py`, `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/validation.mjs`, `frontend/src/validation.d.mts`, `frontend/tests/validation.test.mjs`, and `frontend/package.json`. OpenSpec task checkboxes are complete in `openspec/changes/stage2-banking-enhancements/tasks.md`. `frontend/dist/` is generated build output.

No new application dependency was added. No Stage 1 or other SDD tool implementation was read or modified.

## Verification run for this initial measurement phase

Commands were run in the stated working directories:

- `backend`: `.venv\Scripts\python.exe -m py_compile main.py database.py banking.py tests\test_banking.py tests\test_api.py` — passed.
- `backend`: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — 21 passed, 0 failed, 0 skipped. Coverage includes the Stage 1-shaped migration fixture, accounts/internal transfers/MFA, limit boundaries and reductions, ACH validations/MFA/concurrency/settlement/refund/midnight accounting, recurring cadence/state/recovery/idempotency, and HTTP route smoke coverage.
- `frontend`: `npm.cmd test` — 4 passed, 0 failed, 0 skipped.
- `frontend`: `npm.cmd run build` — TypeScript and Vite production build passed; Vite transformed 32 modules.
- `openspec`: `openspec.cmd validate stage2-banking-enhancements --strict` — passed.
- `openspec`: `openspec.cmd instructions apply --change stage2-banking-enhancements --json` — 22 complete, 0 remaining.

The change contains 22 delta requirements and 91 acceptance scenarios after REC-D03. No browser-driven UI test was run. No historical runtime `backend/bank.db` existed; migration verification used an isolated Stage 1-shaped SQLite fixture and temporary test databases.

The A01–A21 labels are not enumerated in the accessible OpenSpec artifacts or OpenSpec-specific preparation files. The test run covers the approved OpenSpec behavior above, but this record does not claim a one-to-one A01–A21 mapping. No other tool's implementation was consulted.

## Initial SonarQube measurement

### Environment and attempted scope

- SonarQube service was reachable and reported `UP`, version `26.9.0.129388`.
- Scanner image: preinstalled `sdd-sonar-scanner:frozen`; SonarScanner CLI `8.1.0.6389`.
- Anonymous project lookup returned HTTP 401. No `SONAR_TOKEN` environment variable or scanner token was configured.
- Attempted OpenSpec project key: `shift-bank-stage2-openspec`.
- Attempted project name: `Shift Bank E2 OpenSpec`.
- Source scope: `backend,frontend/src`.
- Test scope: `backend/tests,frontend/tests`.
- Exclusions: `backend/.venv/**,backend/__pycache__/**,backend/bank.db,frontend/node_modules/**,frontend/dist/**,openspec/**,**/*.pyc`.
- No canonical project-key or analysis-scope configuration was present in the accessible OpenSpec project/evidence files. The key and source/test scope above are the explicit values used for the attempt; they are not represented as a pre-existing standardized configuration.

### Outcome and raw evidence

The first invocation was rejected by the scanner CLI because PowerShell split unquoted `-Dsonar.*` arguments. Its raw output is preserved at `E2_OPENSPEC_SONAR_INITIAL_RAW.log` (exit code 1; no request reached SonarQube).

The corrected invocation reached the server and failed before project analysis with HTTP 401: `Failed to query server version ... Please check the property sonar.token or the environment variable SONAR_TOKEN.` Its raw output is preserved at `E2_OPENSPEC_SONAR_INITIAL_RAW_02.log` (scanner exit code 1). No analysis was submitted, so no analysis ID, quality gate, or code metrics exist. The SonarQube service itself is available; the genuine blocker is missing authentication/analysis permission. Do not treat the failed scanner attempt as the initial measurement result.

## Environment deviations and remaining issues

- Current: OpenSpec 1.11.0; Codex CLI 0.168.0; Python 3.13.2; Node.js v24.19.0; npm 11.17.0; FastAPI 0.163.1; Pydantic 2.14.3; Vite 5.4.21.
- Preparation recorded OpenSpec 1.9.0, Node.js v20.17.0, and npm 11.6.3. Python 3.13.2 and Codex CLI 0.168.0 match the preparation record. These differences are recorded, not silently normalized.
- SonarQube scan remains blocked until an authorized token/project permission is provided. This log does not contain credentials.
- Automated browser interaction coverage and a real historical Stage 1 database were unavailable; the isolated migration fixture is the evidence used instead.
- No reliable Codex token, tool-call, or cost telemetry was available; no such metrics are claimed.
- No known implementation failure remains from this verification run. The change is still unarchived and unsynchronized.