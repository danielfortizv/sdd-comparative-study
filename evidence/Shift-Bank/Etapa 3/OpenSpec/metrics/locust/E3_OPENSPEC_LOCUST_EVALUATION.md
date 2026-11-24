# E3 OpenSpec — Locust benchmark evaluation

## Run identity and outcome

- Run ID: `RUN_01_20261116T201253Z`
- Command: `python backend\loadtest\run_benchmark.py --run-id RUN_01 --steady-seconds 60`
- Target: one real FastAPI/Uvicorn process on loopback HTTPS, using a run-specific self-signed certificate that Locust explicitly trusted.
- Database: fresh isolated synthetic SQLite database selected via `SHIFT_BANK_DB` before application import/start; WAL mode. It was in a unique temporary path and was disposed after the run. No historical database/sidecar was opened or altered.
- Configured profile: 30 concurrent users; 5 users/s spawn rate; 60 seconds after the runner verified 30 users in `running` state; 6:3:1 task weights; actual COP 1.00 internal transfers.
- Ramp to verified full concurrency: 5.029 seconds. End-to-end measurement: 65.032 seconds. Verified steady state: 60.003 seconds, with active users minimum and maximum both 30.

## Observed performance

SLOs are evaluated against steady-state request samples, using strict comparisons.

| Steady-state endpoint | Requests | Observed mix | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| Balance read | 4,471 | 60.443% | 8.291 ms | 47.391 ms | 251.434 ms |
| Transaction history read | 2,195 | 29.674% | 26.805 ms | 177.468 ms | 348.980 ms |
| Internal transfer | 731 | 9.882% | 40.479 ms | 437.330 ms | 1,091.890 ms |
| Combined reads | 6,666 | 90.118% | 16.460 ms | 121.835 ms | 416.632 ms |
| All requests | 7,397 | 100% | 16.460 ms | 121.835 ms | 416.632 ms |

Steady-state throughput was 123.277 requests/second. The full run including ramp-up recorded 7,755 requests (4,679 balance, 2,310 history, 766 transfers), or 119.250 requests/second over 65.032 seconds. Ramp-only traffic contained 358 requests (208 balance, 115 history, 35 transfers) over 5.029 seconds, or 71.193 requests/second.

| Acceptance condition | Measured value | Result |
|---|---:|---|
| Balance read p95 < 200 ms | 47.391 ms | PASS |
| History read p95 < 200 ms | 177.468 ms | PASS |
| Combined read p95 < 200 ms | 121.835 ms | PASS |
| Transfer p95 < 500 ms | 437.330 ms | PASS |
| Unexpected steady-state errors < 1% | 0 / 7,397 = 0.000% | PASS |

Expected business rejections: 0. Locust failures: 0. Threshold comparisons are strict; the automated helper tests confirm exact equality is a failure. Values above are rounded only for presentation; comparisons use measured values.

## Financial and audit integrity

The workload produced 766 distinct completed API transfer responses and 766 matching completed transfer rows. No expected rejection occurred. Starting balances totaled COP 20,000,000.00; final balances were checking COP 4,999,234.00 and savings COP 15,000,766.00, preserving the total and matching every COP 1.00 transfer. The audit chain verified valid with 767 entries: one genesis entry and one completion event per transfer. Database transaction count was 768, including the two seed rows.

## Raw artifacts

- `E3_OPENSPEC_LOCUST_RUN_01.json` — complete machine-readable run report, Locust serialized stats, environment, SLO results, and integrity checks.
- `RUN_01_20261116T201253Z_requests.csv` — all original Locust request-event samples with timestamps, endpoint, latency, HTTP status, rejection classification, and error classification.
- `RUN_01_20261116T201253Z_stats.csv` and `RUN_01_20261116T201253Z_failures.csv` — Locust request statistics and failure exports; the failure export contains its header and no failures.
- `RUN_01_20261116T201253Z_users.csv` — timestamped active-user/ramp/steady timeline.
- `RUN_01_20261116T201253Z_runner.txt` — timestamped runner ID, target, and HTTPS readiness evidence.
- `RUN_01_20261116T201253Z_server.log` — backend output (empty; Uvicorn emitted no warnings/errors).
- Synthetic database SHA-256 before disposal: `fe513fc0641d1ae0e932dcdd11ca0a235118c198e0d4926b8c1a531a7bcfad48`.

No private key, encryption key, audit key, verification token, or MFA code is present in the artifacts. TLS-linked Python OpenSSL was 3.0.15; CPU/memory utilization was not measured.

## Verification after implementation

- `python -m unittest discover -s tests -v` from `backend/` — PASS, 53 tests.
- `npm.cmd --prefix frontend test` — PASS, 8 tests.
- `npm.cmd --prefix frontend run build` — PASS, TypeScript and Vite production build (34 modules transformed). Sandbox execution was denied access to esbuild's parent directory; the same command passed when rerun outside the sandbox.
- `openspec.cmd validate --all --strict` — PASS, 6 passed, 0 failed.
- Load-test helper checks — PASS, 5 tests, including fail-closed DB paths, observed distribution, strict thresholds, and ramp/steady boundary.

## Corrections and limitations

The first full backend test discovery after adding Locust paused because importing Locust during test collection monkey-patched `socket` and `threading`, which interfered with the inherited API smoke test. The workload-weight test was changed to parse `@task` decorators with Python AST rather than importing Locust; the full 53-test backend suite then passed. No workload parameter, security control, business rule, application financial behavior, or performance threshold was changed. There were no benchmark performance failures, so no optimization cycle or RUN_02 was required.

Performance evidence is for this local Windows environment, a single backend process, local TLS, and synthetic SQLite data only. It is not a production capacity claim. Container deployment tasks 4.1–4.3, integrated acceptance task 5.3, SonarQube, and change closure remain pending.
