# Shift Bank Stage 4 — Final experimental closure (E4-SK-08)

**Disposition: CLOSED WITH DOCUMENTED LIMITATIONS.** The researcher explicitly approved this final review and accepted closure under the documented limitations. This is not a statement of production readiness, independent technical verification, or successful completion of failed criteria. T068 is complete as the researcher-facing closure review; the task list is 68/68 checked.

Researcher authorization recorded verbatim: “By submitting this instruction, I, the researcher responsible for this experiment, approve the final review of Stage 4 under the documented limitations. I authorize closure as CLOSED WITH DOCUMENTED LIMITATIONS, including any confirmed performance failure, unresolved SonarQube findings, and unavailable telemetry. This acceptance does not mean that failed requirements passed or that the software is production-ready.”

## Final acceptance

| Scope | Final status | Evidence / qualification |
|---|---|---|
| AC-01–AC-44 | PASS | E4-SK-07 acceptance matrix and tests/smoke evidence; these are automated results, not independent human validation. |
| AC-45 approved profile | **FAIL** | One corrected run used balance/history/transfers 60/30/10. Read p95 and unexpected-error targets passed; transfer p95 failed (2,803.02 ms vs <500 ms). No optimization or rerun was performed. |
| REQ-01–REQ-05 | PASS | E4-SK-07 acceptance matrix. |
| REQ-06 | PASS WITH LIMITATION | Functional and isolated deployment evidence passed; performance acceptance fails at transfer p95. |
| D-01–D-14 | PASS WITH DOCUMENTED COP COMPATIBILITY EXCEPTIONS | Implemented contract and E4-SK-07 matrix; COP remains separate legacy currency, retains inherited accounts/values/behavior, and has no invented FX rate. This does not erase the AC-45 failure. |
| Deployment smoke | PASS | Isolated E4 Docker backend/Nginx smoke, HTTPS redirect/TLS routing, health, representative encrypted/versioned transfer, replay, audit, projection rebuild and restart persistence; disposable volume and test-only secrets. |
| SonarQube | Quality Gate OK; findings unresolved | Four bugs, zero vulnerabilities, 93 code smells, 959 minutes debt. No issue-level disposition was recorded. |
| Human validation | Researcher accepted closure | Acceptance is based on recorded agent evidence and does not claim independent review of each test or finding. |

## Corrected AC-45 benchmark

Exactly one corrected benchmark was run using the approved profile and disposable E4 SQLite data/test-only secrets. The existing Locust harness was minimally adjusted to use six balance reads, three history reads, and one same-currency versioned transfer per cycle. Transfers used fresh UUID idempotency keys and expected account versions. Business conflicts were counted separately as expected rejections.

- Command: `python .e4sk08_ac45_once.py` (one-shot orchestration; launches isolated Uvicorn and Locust, then removes its temporary database/keys and stops the process).
- 30 concurrent users observed continuously (60 samples), 5 users/s ramp (5.03 s), 60.0 s sustained.
- 12,979 steady-state requests; 216.32 requests/s. Mix: 7,788 balance reads (60.03%), 3,896 history reads (30.03%), 1,290 transfers (9.94%); five startup public-key fetches were separately accounted; zero request reconciliation discrepancy.
- Reads: p50 48.18 ms, p95 172.57 ms, p99 279.34 ms; <200 ms p95 target PASS.
- Transfers: p50 182.43 ms, p95 2,803.02 ms, p99 6,349.29 ms; <500 ms p95 target **FAIL**.
- Expected business rejections: 1,234; successful responses: 11,745, including 56 successful transfers. Unexpected errors: 0/12,979 (0%); <1% target PASS.
- Overall AC-45 result: **FAIL**. No further run or tuning was done.

Primary raw evidence: `E4-SK-08-AC45-locust-metrics.json`, `E4-SK-08-AC45-locust-output.txt`, and `E4-SK-08-AC45-backend.log` in this directory. The earlier E4-SK-07 run is a distinct, more transfer-intensive profile (observed 60.28% balance / 29.81% transfers / 9.91% history): transfer p95 5,277.63 ms, read p95 99.42 ms, 0% unexpected errors, 89.72 requests/s, 1,499 expected rejections and 104 successful transfers. It is not used to claim AC-45 compliance.

## D1–D5 experimental measures

### D1 — Effort and telemetry

Recorded Codex-reported durations: SK-01 4:29; SK-02 4:20; SK-03 specification completion 30:25 (blocked attempts excluded from this milestone duration); SK-04 46:48; SK-05 implementation 56:30 (a separate 0:23 blocked attempt exists); SK-06 57:53; SK-07 38:58. These sum to 3:59:23 and are reported session durations, not independently instrumented wall time. SK-08 has only a partial observed interval of 2:18 from session start to corrected benchmark completion; total milestone duration is N/D. Available tokens, cached tokens, input/output tokens, total tool calls, per-milestone cost, and exact effective model/session identifiers: N/D. Previously observed Codex CLI 0.168.0 and GitHub Spec Kit 1.0.6 are historical tool versions from SK-04, not re-probed here. Human approvals: delegated Gate A compatibility decision, explicit Gate B approval, and this explicit final limitation-aware closure acceptance. GitHub Copilot performed the separately documented preparation; these preparation measures are not attributed to Codex E4. No E3 or Tessl measurement is included.

### D2 — Code quality and change volume

- Prepared 105-file source baseline: 71 unchanged, 34 changed at the SK-07 comparison. Among comparable production source files, 14 were compared; six production files were additions and measured source delta was +1,744 / -166 lines. No baseline-source file was reported unverifiable. This is cumulative Stage 4 change, not solely SK-08.
- Physical LOC method in SK-07: 7,800 production LOC across 20 backend/frontend source files; 6,272 test LOC across 30 backend/frontend test files. Excludes dependencies/build output and is not Sonar ncloc.
- E4-only SonarQube: 6,557 ncloc; Quality Gate “Sonar way” OK; 4 bugs (unresolved, issue-level assessment N/D), 0 vulnerabilities, 93 code smells, 959 minutes technical debt, 0.0% reported duplication.
- Sonar displayed 0.0% coverage because no coverage report was imported. This is **not evidence of 0% actual test coverage**; actual line/branch coverage is N/D.
- Sonar and code evidence: `E4-SK-07-sonarqube-metrics.json`, `E4-SK-07-FINAL-VALIDATION.md`, scanner output, and failure/correction records.

### D3 — Specification package

Counting scope: approved native Spec Kit feature package under `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/`, excluding `implementation-evidence/`. It contains 11 Markdown documents (spec, plan, tasks, research, implementation notes, data model, quickstart, two checklists, API contract, event contract). The formal specification measure is `spec.md` only: 247 physical lines. It contains 27 functional requirements, 45 acceptance criteria and 6 top-level REQs; the approved cross-reference includes D-01–D-14 and the task list contains 68 tasks. Density: 10.93 FR / 100 spec lines; 18.22 AC / 100 spec lines; 26.55 Sonar ncloc per formal-spec line (6,557/247). Physical production LOC/formal spec ratio: 31.58 (7,800/247). Requirement-description word-count five-number summary across 27 FR descriptions: min 17, Q1 23, median 29, Q3 34, max 71 words. The companion-document LOC is not added to the formal spec denominator. E3/Tessl specs are excluded.

### D4 — Functional quality

- Backend: 138 passed, one deprecation warning. Frontend: 20 passed across four files. TypeScript check and production build passed. Exact commands and logs are in `E4-SK-07-FINAL-VALIDATION.md` and the SK-07 acceptance directory.
- Isolated Docker/Nginx smoke passed (HTTP→HTTPS redirect, HTTPS SPA, backend health/database/crypto/scheduler, six accounts and initial values, encrypted versioned transfer, idempotency replay/conflict, projection rebuild, HMAC verification/unauthorized rejection, backend restart persistence). Evidence: `E4-SK-07-deployment-smoke.json` and final validation report.
- AC-01–AC-44 PASS per mapped tests/verification; corrected AC-45 FAIL as above. REQ-01–05 PASS; REQ-06 PASS WITH LIMITATION. D-01–D-14 are covered in the documented implementation contract with accepted COP exceptions.
- Load profiles remain separate: corrected approved profile fails transfer p95 at 2,803.02 ms; earlier transfer-heavy profile fails at 5,277.63 ms. Both passed the read p95 and unexpected-error thresholds reported for their respective runs.

### D5 — Human intervention, corrections, limitations

Researcher interactions: Gate A delegated compatibility resolution based on Stage 4 documentation; explicit Gate B acceptance; explicit final closure acceptance. Accepted COP adaptations retain COP legacy balances/accounts, operations, limits/MFA, ACH/recurring behavior, separate dashboard display, and prohibit unapproved COP FX. Agent corrections and failed runs are detailed in SK-05/06/07 evidence; SK-07 recorded test/build/deployment/Sonar query corrections and an intermediate load run with one HTTP 500 that was not diagnosed. E4-SK-08 corrected the AC-45 workload mix once and did not alter application logic, thresholds, or the contract; no second benchmark followed. Four Sonar bugs remain unresolved; coverage telemetry and detailed agent cost/token/session telemetry remain unavailable. Closure accepts these limitations without converting failures to passes.

## Repository and reproducibility record

Current branch observed: `ShiftBank`. `.gitignore` ignores caches, dependencies, frontend build output, environment files, PEM certificates and logs, but does not ignore native E4 specs/evidence or the new integration/decision/acceptance records. Git reports the E4 feature package and E4 evidence directories untracked, so they must be explicitly included in any later archival/commit process; nothing was staged or committed. E4 implementation source and tests remain modified/untracked as expected for this workspace.

The working tree also reports unrelated Stage 2 untracked Kiro paths and Stage 3 temporary-directory deletions/untracked pytest directories (Git emitted missing-directory warnings). This invocation did not inspect their contents, restore, delete, or modify them. They are a repository-level provenance/reproducibility risk and remain outside this E4 closure action. No prior E4 baseline evidence or historical logs were overwritten. The one-shot runner was removed after execution; its disposable runtime state was cleaned automatically. Empty backend log is retained as raw output evidence.

## Primary evidence index

- E4-SK-01–SK-07 experiment records: `../_experiment_logs/Spec Kit/bitacora.md` and linked preparation, decisions and acceptance evidence.
- Final pre-closure matrix and tests/build/smoke/Sonar results: `E4-SK-07-acceptance-matrix.md`, `E4-SK-07-FINAL-VALIDATION.md`, `E4-SK-07-deployment-smoke.json`, `E4-SK-07-sonarqube-metrics.json`.
- Earlier distinct load profile and preserved failures: `E4-SK-07-locust-metrics.json`, `E4-SK-07-locust-output.txt`, `E4-SK-07-locust-metrics-run02-failure.json`, and `E4-SK-07-corrections-and-failures.md`.
- Corrected AC-45 run: `E4-SK-08-AC45-locust-metrics.json`, `E4-SK-08-AC45-locust-output.txt`, `E4-SK-08-AC45-backend.log`.
- Gate A delegated contract and Gate B approval: `../_experiment_logs/Spec Kit/decisiones/E4_SPECKIT_DELEGATED_CONTRACT_AND_SPECIFICATION.md` and `E4_SPECKIT_GATE_B_APPROVAL_2026-11-16.md`.
- T068 is checked in `../../../Spec Kit/specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/tasks.md` after this final researcher acceptance.

**Final classification: CLOSED WITH DOCUMENTED LIMITATIONS.** The software is not declared production-ready. The corrected AC-45 transfer p95 failure and unresolved Sonar findings remain visible for any future engineering work; no further work is authorized by this closure record.
