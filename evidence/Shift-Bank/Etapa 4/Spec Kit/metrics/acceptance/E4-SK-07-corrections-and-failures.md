# E4-SK-07 failures, corrections, and rework record

All attempts used disposable E4 data or an isolated SonarQube project. No E3 services, data, keys, or volumes were used.

| Attempt | Observed failure or issue | Correction / later outcome |
|---|---|---|
| Contract check | Frontend conversion fixture represented USD→EUR as 92/100 and 92.00 EUR; approved table and backend use 9/10 and 90.00 EUR. | Updated `frontend/src/App.test.tsx`; full 20-test frontend suite passed. |
| Locust run 1 | Legacy weighted tasks yielded 69.14% balance / 22.66% transfer / 8.19% history. Read p95 335.97 ms, transfer p95 1,519.86 ms, 0 unexpected errors. | Reworked harness into fixed 6/3/1 operation cycles to match the task-requested mix. |
| Locust run 2 | Startup refreshes on expected version conflicts inflated balance-read counts to 67.36%; one HTTP 500 was reported (0.017% unexpected rate). Read p95 77.32 ms; transfer p95 5,791.38 ms. | Removed hidden refresh reads after expected `ACCOUNT_VERSION_CONFLICT` so the requested mix remains observable. Root cause of the single HTTP 500 was not independently diagnosed. Detailed observed output is preserved in `E4-SK-07-locust-output-run02-failure.txt` and `E4-SK-07-locust-metrics-run02-failure.json`. |
| Locust final | 60.28% balance / 29.81% transfer / 9.91% history; 0 unexpected errors, 1,499 expected business rejections. Transfer p95 still 5,277.63 ms; threshold failed. | Accepted as a measured performance failure, not concealed or weakened. See final Locust metrics. |
| Deployment smoke 1 | A valid transfer left the projection checkpoint at sequence 8 with latest event sequence 9; the smoke harness incorrectly expected equality before replay. | Preserved in `E4-SK-07-deployment-smoke-failure-01.md`. Changed the harness to require checkpoint ≤ latest before replay and equality after the explicit projection rebuild. The subsequent isolated smoke passed. |
| Frontend build | Sandbox esbuild denied access to an ancestor directory while loading `vite.config.ts`. | Re-ran the same production build with the required elevated tool permission; TypeScript and Vite build passed. |
| Sonar attempt 1 | Read-only scanner mount traversed an inaccessible workspace `.pytest_cache` directory. | Preserved the scanner output; staged only the E4 production source into a temporary read-only scan root. |
| Sonar metrics attempt 1 | Scanner succeeded but metrics API authentication returned HTTP 401. | Corrected token Basic authentication; the isolated server/token were discarded and recreated. `E4-SK-07-sonarqube-authquery-failure.json` preserves the failed query. |
| Sonar metrics attempt 2 | Analysis upload succeeded, but measures were queried before server-side processing completed. | Added compute-engine task polling and assigned the isolated `Sonar way` gate; final analysis reported CE SUCCESS and retrieved metrics. |

No application acceptance outcomes were altered to obtain a pass. The remaining load-test threshold failure and AC-45 workload-order discrepancy require researcher disposition.
