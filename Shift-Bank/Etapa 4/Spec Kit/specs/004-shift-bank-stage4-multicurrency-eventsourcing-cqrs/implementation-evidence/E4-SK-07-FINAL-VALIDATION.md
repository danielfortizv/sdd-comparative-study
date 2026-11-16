# E4-SK-07 — Final validation and experimental closure

**Date:** 2026-11-16  
**Verdict:** **COMPLETE WITH LIMITATIONS**  
**Task state:** 67/68 checked; T068 remains pending researcher review.

## Executive result

The final E4 backend/frontend suites and isolated Docker smoke passed. The E4-only Sonar scan completed with Quality Gate OK. The requested Locust run achieved its concurrency, ramp, duration, read latency, and unexpected-error thresholds, but transfer p95 failed materially. The requested run also reverses the history/transfer workload order in approved spec AC-45. Those limitations require researcher disposition before experimental closure. T068 was prepared for human review and intentionally left unchecked.

No tests or outcomes were represented as independent human validation. Gate B authorization remains the earlier researcher authorization recorded in E4-SK-05; no new implementation authorization is claimed.

## Final task and contract counts

- T061–T067: checked against saved E4-SK-07 evidence.
- T068: pending the researcher-facing final review and sign-off.
- 27 functional requirements, REQ-01–REQ-06, D-01–D-14, and all 45 acceptance criteria are mapped in [`E4-SK-07-acceptance-matrix.md`](E4-SK-07-acceptance-matrix.md).
- AC-01–AC-44: PASS in the mapped automated/regression/deployment evidence.
- AC-45: FAIL for transfer p95, and not exactly comparable to the approved profile because of the workload-order discrepancy described below.
- Accepted COP compatibility deviations remain unchanged: preserve both COP legacy accounts/balances/history; add D-02 accounts; do not create a COP FX rate; retain COP limits/MFA/ACH/recurring behavior.

## Contract checks and corrections

- API contract, backend, frontend, and tests use `IDEMPOTENCY_KEY_CONFLICT` for HTTP 409 key reuse with a changed payload. Frontend has no active `IDEMPOTENCY_KEY_REUSE` branch.
- Corrected the frontend 100 USD→EUR fixture from 92/100 and 92.00 to the approved 9/10 and 90.00 EUR. Backend and API conversion tests already used the approved rate.
- Raw HTTP contract tests verify UUID `Idempotency-Key`, encrypted request envelopes, expected versions, replay-before-version checking, `ACCOUNT_VERSION_CONFLICT`, and no duplicate effects. The isolated HTTPS smoke independently verified replay returns the original operation and changed payload returns HTTP 409 `IDEMPOTENCY_KEY_CONFLICT`.
- AC-45 in `spec.md` currently says 60% balance / 30% history / 10% encrypted transfers. The E4-SK-07 run instruction requested 60% balance / 30% internal transfers / 10% history. The final measured Locust run follows the explicit run instruction, not the approved spec ordering. No specification was silently changed.
- The first smoke run caught a harness assertion that demanded the projection checkpoint equal the latest event before a replay. The observed checkpoint was 8 with latest event sequence 9. The test now accepts a checkpoint no later than the latest sequence before replay and requires equality after explicit rebuild. The isolated smoke then passed; details are in [`E4-SK-07-deployment-smoke-failure-01.md`](E4-SK-07-deployment-smoke-failure-01.md) and [`E4-SK-07-deployment-smoke.json`](E4-SK-07-deployment-smoke.json).

## Functional and regression verification

| Command | Result |
|---|---|
| `python -m pytest backend/tests -q --basetemp=backend/.e4sk07-pytest-final` | **138 passed**, 1 Starlette/httpx deprecation warning, 30.45 s. Includes Stage 4 and inherited regression modules. |
| `npm.cmd --prefix frontend test -- --reporter=dot` | **4 files / 20 tests passed**, 3.87 s. |
| `frontend\node_modules\.bin\tsc.cmd --noEmit -p frontend\tsconfig.json` | Exit 0. |
| `npm.cmd --prefix frontend run build` | Exit 0; `tsc` passed, Vite 5.4.21 built 34 modules. |

The backend suite includes temporary-database migration repeat/conflict rollback and COP/history preservation; exact FX pair and HALF_UP tests; transfers, stale/concurrent versions and UUID replay; event encryption/append-only/replay; atomic rollback; AES-GCM/HMAC; ACH timing/settlement/refund races; recurring concurrency; and raw HTTP mandatory-header tests. Frontend checks include exact BigInt money helpers, encrypted request transport, currency grouping, and conversion display. A first sandbox build attempt was denied by esbuild while reading an ancestor directory; the same production build passed when rerun with the required elevated permission. The standalone TypeScript check passed.

## Isolated deployment verification

Built and ran backend and Nginx/frontend with a unique `e4sk07` Compose project, fresh generated test-only crypto/TLS credentials, and a project-scoped disposable SQLite volume. The inherited Compose file has fixed container names/ports/volume names and references a missing `deployment/docker.env`; an ephemeral Compose file and Nginx port copy were used to avoid collisions. The original deployment files were not altered for this test. Smoke results:

- HTTP redirect 301; HTTPS SPA 200; API health 200 with database, keys, and scheduler healthy.
- All six COP/D-02 accounts and specified fresh-volume balances verified.
- Encrypted USD transfer using UUID idempotency and both expected account versions passed.
- Exact request replay caused no additional financial effect; changed payload returned HTTP 409 `IDEMPOTENCY_KEY_CONFLICT`.
- Projection rebuild replayed nine events; HMAC audit verified three records; missing audit authorization returned 401.
- Backend restart preserved balances and audit validity.

Raw result: [`E4-SK-07-deployment-smoke.json`](E4-SK-07-deployment-smoke.json). Test containers, network, images, volume, generated keys/certificates, and temporary secret files were removed. No historical database, E3 service, shared volume, or historical secret was used.

## Locust profile and outcome

Command executed by the isolated harness:

`python -m locust -f backend/tests/locustfile.py --headless -u 30 -r 5 --host http://127.0.0.1:18087 --loglevel WARNING`

The harness started FastAPI against a temporary SQLite file and generated RSA keys and test-only environment values in a temporary directory. It used 30 users, 5 users/s ramp, and 60 s sustained. Final measured workload was 60.28% account reads / 29.81% internal transfers / 9.91% history reads; 5 startup key handshakes were separately reconciled. There were 5,383 measured steady-state requests at 89.72 requests/s and 30 users remained active throughout.

- Read p50/p95: 33.08 / **99.42 ms** (target <200 ms: PASS).
- Transfer p50/p95: 147.76 / **5,277.63 ms** (target <500 ms: **FAIL**).
- Expected business rejections: 1,499, accounted separately; successful transfers: 104.
- Unexpected errors: 0 of 5,383 (0%; target <1%: PASS).
- Environment: host-based Locust and Uvicorn with local temporary SQLite on Windows/Docker Desktop host; exact CPU model and workload hardware profile were not captured (N/D). No funds were combined across currencies.

Raw results: [`E4-SK-07-locust-metrics.json`](E4-SK-07-locust-metrics.json) and [`E4-SK-07-locust-output.txt`](E4-SK-07-locust-output.txt). Earlier harness runs and one transient HTTP 500 are preserved in the `run02-failure` files and [`E4-SK-07-corrections-and-failures.md`](E4-SK-07-corrections-and-failures.md). The final run had no unexpected errors; the earlier 500’s cause was not independently established.

## E4-only SonarQube

SonarQube 26.9.0.129388 ran as a separate disposable container/project. The scanner received only a read-only staged copy of `backend/src` and `frontend/src`; its temporary analysis token was revoked and service/volumes removed after processing.

- Scanner / Compute Engine: success.
- Quality Gate (`Sonar way`): **OK**.
- Sonar ncloc: 6,557; bugs: **4**; vulnerabilities: 0; code smells: 93; technical debt: 959 minutes.
- Coverage: 0.0% because no coverage report was imported. Duplication: 0.0% reported.
- Issue-level review of the four bugs was not captured; count is reported without claiming they were all triaged.

Raw evidence: [`E4-SK-07-sonarqube-metrics.json`](E4-SK-07-sonarqube-metrics.json) and [`E4-SK-07-sonar-scanner-output.txt`](E4-SK-07-sonar-scanner-output.txt). Failed scanner/query attempts and corrections are preserved in the auth-query failure JSON and correction log.

## D1–D5 experimental metrics

### D1 — Effort and agent telemetry

- E4-SK-07 took approximately 30 minutes from first recorded test output to final analysis capture; exact task start/stop instrumentation was unavailable. Prior E4-SK-05/E4-SK-06 milestone durations: N/D.
- Effective Codex model/version, input/output/cache tokens, cost, session identifier, aggregate tool-call telemetry: N/D. Observed CLI versions from prior E4 evidence: Codex CLI 0.168.0; Spec Kit 1.0.6. Local tools observed for this run included Python 3.13.2, Node 24.19.0, Locust 2.47.0, Docker 29.9.3, Compose 5.7.0, Vite 5.4.21, TypeScript 5.9.3.

### D2 — Code quality and change volume

- Prepared baseline SHA-256 manifest contains 105 files: 71 still match the prepared E4 baseline; 34 differ. The changed set includes the cumulative approved E4 source/test changes and Spec Kit integration artifacts, not only this run.
- Production-source comparison against the verified manifest source copy: 14 comparable files, 6 new production source files, 1,744 line additions / 166 line deletions (all 14 source baselines verified). This is cumulative E4 change since the prepared baseline; E4-SK-07 changed no application production logic.
- Physical line-count method: backend Python and frontend TS/TSX/CSS production source excluding frontend tests/build output = 7,800 LOC across 20 files; tests = 6,272 LOC across 30 backend/frontend test files. Sonar reports 6,557 ncloc, a different comment/blank-excluding measure.
- Sonar findings are reported above; the four issue details were not retrieved for this closure.

### D3 — Specification package

- Native Spec Kit package: 11 Markdown documents (specification, research, plan, implementation notes, data model, API/event contracts, quickstart, tasks, and two checklists), 1,084 physical LOC excluding implementation evidence.
- 6 REQs, 27 FRs, 45 ACs, 14 decisions; FR density 2.49 per 100 specification LOC; AC density 4.15 per 100 LOC. Production physical-code/spec physical-LOC ratio: 7.20:1.

### D4 — Functional quality

- Backend 138/138; frontend 20/20; TypeScript/build pass; isolated deployment smoke pass.
- Acceptance matrix AC-01–AC-44 PASS; AC-45 FAIL for transfer p95 and not exact workload-order equivalence. REQ-01–REQ-05 PASS; REQ-06 PASS WITH LIMITATION.
- D-01–D-14 remain covered by the approved functional contract and tests; accepted COP compatibility exceptions remain unchanged. No production deployment or historical E3 result is claimed.

### D5 — Human intervention and rework

- Gate A delegation and Gate B approval are the researcher decisions already recorded in E4-SK-03/E4-SK-05. E4-SK-07 had no additional approval interaction and no repeated clarification request.
- E4-SK-07 corrected the 92 EUR fixture, made Locust request proportions observable, and corrected smoke assertions around a rebuild checkpoint. Sandbox/tooling and Sonar query failures were retried and recorded. One intermediate load run reported one HTTP 500; final run had none, but that transient failure was not diagnosed.
- Accepted contract adaptations were not changed. One conflict remains between E4-SK-07's requested Locust mix and the approved AC-45 wording.

## Changed files in this milestone

- `frontend/src/App.test.tsx` — corrected USD→EUR fixture/rate display from 92/100 to 9/10 and EUR 90.00.
- `backend/tests/locustfile.py` — Stage 4 same-currency/version/idempotency workload and fixed 60/30/10 operation cycles; expected stale-version conflicts are counted separately from unexpected failures.
- `deployment/smoke_test.py` — added isolated Stage 4 HTTPS/API/replay/rebuild/audit/restart checks while retaining inherited smoke mode.
- `docs/stage4-operations.md` — added Stage 4 backup/recovery and money-safety runbook.
- `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/tasks.md` — checked T061–T067 based on evidence and left T068 pending.
- Added E4-SK-07 matrix, deployment/load/Sonar raw evidence, review package, and correction log under `implementation-evidence/`.

No Stage 3 or other SDD implementation was intentionally changed. The shared worktree contains unrelated prior Stage 3 temporary-path and other-stage changes; they were not cleaned or modified.

## Researcher decision to close

Review the AC-45 workload-order discrepancy and transfer p95 failure, inspect the four Sonar bug findings if required, then complete T068. The researcher's response to those items and final T068 sign-off are required for **COMPLETE** status. Until then this package is **COMPLETE WITH LIMITATIONS** and the implementation must not be described as independently human-validated.
