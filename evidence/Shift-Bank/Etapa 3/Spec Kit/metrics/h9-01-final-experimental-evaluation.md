# H9 — Final Experimental Evaluation (Codex evidence consolidation)

Date: 2026-11-16  
Workflow: GitHub Spec Kit  
Attribution: Codex consolidated existing evidence and H8 verification. Historical implementation and Locust measurements remain attributed to Gemini CLI unless the source record explicitly says otherwise.

## Executive status

Technical implementation and functional verification are complete for the recorded scope: 38/38 tasks; backend 97/97; frontend 13/13; production build PASS; isolated Docker smoke 9/9 PASS. Validated SonarQube exports cover an isolated source snapshot. The project key matches the requested project, Quality Gate status is `OK`, and the metric export contains populated measures. Execution metadata recorded for that run: SonarScanner 5.1.0, SonarQube 26.9.0, 23 indexed files. Analysis ID/time, source revision, scope/exclusions, and coverage-report import status remain N/D; no Git revision is asserted.

## D1 — Effort and consumption

| Agent | Time | Tokens | Messages/tool calls | Cost |
|---|---|---|---|---|
| Gemini CLI | N/D in the inspected durable evidence | N/D | N/D | N/D |
| Codex | Session-level active/wall time not captured in durable telemetry | N/D | N/D | N/D |

Sources: Stage 3 bitácora and preparation handoff. No inferred token, cost, or elapsed-time estimates are substituted. Gemini billing interruption is documented as the agent transition context, not a measured effort value.

## D2 — Code quality

| Measure | Result |
|---|---|
| Sonar project key / qualifier | `Shift-Bank---Stage-3---Spec-Kit` / `TRK` |
| Scanner / SonarQube versions | SonarScanner 5.1.0 / SonarQube 26.9.0 |
| Scan source and indexed files | Isolated source snapshot / 23 files |
| Git revision | N/D; not recorded |
| Quality Gate | **OK** (`projectStatus.status`); conditions array empty; `ignoredConditions=false` |
| CAYC status | `compliant` |
| Bugs / reliability rating | 3 / 3.0 (**C**) |
| Vulnerabilities / security rating | 1 / 2.0 (**B**) |
| Security hotspots | 0 |
| Code smells / maintainability rating | 70 / 1.0 (**A**) |
| Technical debt (`sqale_index`) | 508 minutes (8 h 28 min) |
| NCLOC | 6,204 |
| Duplicated lines density | 0.0% |
| Coverage | 0.0 reported; coverage import/scope metadata absent. Per metric guide, this does not mean 0% of tests passed. |
| Classic issue count / density | 74 issues (3 bugs + 1 vulnerability + 70 smells); 11.93 issues/KLOC (`74 / 6.204`) |
| New-code measures, cognitive complexity, analysis ID/time, source revision, configured exclusions and coverage import metadata | N/D |

Evidence: `reports/sonarqube_metrics_speckit3_validated.json` and `reports/sonarqube_quality_gate_speckit3_validated.json`; run metadata records SonarScanner 5.1.0, SonarQube 26.9.0, isolated snapshot, and 23 indexed files. The JSON exports provide measures/status but no analysis ID/time, Git revision, source-scope/exclusion details, coverage-import metadata, or gate conditions. Earlier empty exports remain historical and are superseded here by the validated exports. No scan was executed by Codex. Historical Tessl Sonar reports are excluded; Stage 2 metrics are not substituted for Stage 3.

## D3 — Specification artifacts and completeness

The approved Stage 3 package contains the seven planned core artifacts: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`, and `tasks.md`; `checklists/acceptance_review.md` provides acceptance traceability. The approved specification states 35 functional requirements and 38 acceptance scenarios. The task checklist reports 38/38 tasks complete.

Normalized density, C/E ratio, requirement count under an atomicity rule, Req/CLOD, and quartile distribution: N/D. The inspected metric standardization guide prohibits arbitrary bullet-as-requirement counting; no independently frozen line-count/atomic requirement extraction was present for this report. No seed, prompt, README, or evidence report is counted as a generated specification.

## D4 — Functional compliance and tests

| Verification | Result | Evidence |
|---|---:|---|
| Stage 3 implementation tasks | 38/38 complete | `specs/003-shift-bank-stage3/tasks.md` |
| Backend automated tests | 97 passed, 0 failed | H8-07 fresh project-local pytest basetemp run |
| Frontend Vitest | 13 passed in 2 files | H8-07 `npm.cmd --prefix frontend test -- --run` |
| Production build | PASS; TypeScript + Vite, 33 modules | H8-07 `npm.cmd --prefix frontend run build` |
| Isolated Docker smoke | 9/9 PASS | H8-10 isolated project `sb-h810-967924cae6`, smoke output and resolved Compose config in its temporary evidence directory |
| Docker financial invariants | exact per-account restoration; total COP 20,000,000.00 | Initial Checking COP 5,000,000.00 and Savings COP 15,000,000.00 restored after reciprocal pairs; no limit changes/reset |
| Docker at-rest encryption | 2/2 account balances, 2/2 limits, 6/6 transfer amounts encrypted | Read-only SQLite check in isolated backend (`enc:v1:` prefixes) |
| Docker audit | 8 records valid; unauthorized request HTTP 401; valid after restart | H8-10 smoke verification |
| Locust | Three historical attempts, not rerun by Codex | `locust/reports/` and acceptance review: attempt 1 failed funds conservation (+COP 800 variance); attempt 2 conserved funds but TLS unverified and no 1 Hz sampling; attempt 3 met listed benchmark criteria with 30 users, 60 seconds, read p95 138.84 ms, transfer p95 357.77 ms, 7,076 operational requests plus 5 startup handshakes, 757 valid audit records, exact COP 600,000,000 conservation |

The two known security limitations in acceptance documentation remain relevant: no envelope replay deduplication and no deterministic in-memory key zeroization; local TLS is self-signed and authentication is a single mock user. Audit tail-truncation detection requires an external checkpoint.

## D5 — Incidents, corrections, and rework

- Gemini CLI became unavailable after Google Cloud billing was disabled; Codex continued H8 verification. Attribution and measured benchmark history were kept separate.
- H8-05/H8-06 exposed unsafe fixed pytest cleanup and Windows temp-root ACL restrictions. Codex moved databases/certificates under pytest-managed temporary paths and ran with a fresh project-local `--basetemp`.
- H8-07 identified `%USERNAME%`/executing identity mismatch in Windows ACL setup; a focused helper correction led to 97/97 backend tests passing.
- H8-08/H8-09 Docker access/isolation blockers were resolved for H8-10 by a unique isolated Compose project and configurable smoke runner. Intermediate config validation errors were corrected before containers started.
- H8-10 preserved original deployment resources; isolated test containers were stopped while the isolated volume/evidence were retained.
- H9-02/H9-03 credential/process-scope and empty-export blockers were resolved by the user's external isolated-snapshot analysis and validated exports. Codex did not execute Sonar or change code to influence ratings.

## Evidence boundaries and next action

N/D items are unavailable measurements, not zero. D1 agent-specific token/cost/time telemetry and several D3 normalized statistics remain N/D because source telemetry and frozen extraction data are unavailable. D2 is based on the validated export and recorded run metadata; coverage reports 0.0%, but coverage-import scope is unverified. D4 and D5 summarize recorded results/incidents, preserving Gemini/Codex attribution. Quality Gate is `OK` in the export, although its conditions array is empty. Missing analysis ID/time, Git revision, scan scope/exclusions, and coverage context limit reproducibility and comparison. No further tests or scans were run for this consolidation.

## Closing decision

The available evidence supports closing the Stage 3 documentation package for human review. Functional verification and the isolated Docker checks are recorded as passed; SonarQube reports Quality Gate `OK` and the measurements listed above. D1 and the unavailable D3 statistics remain N/D. Gemini CLI implementation/benchmark attribution and Codex verification/documentation attribution remain separate. This report does not assert a Git revision or claim complete Sonar reproducibility because the analysis identifier, scope/exclusions, and coverage-import details are unavailable.
