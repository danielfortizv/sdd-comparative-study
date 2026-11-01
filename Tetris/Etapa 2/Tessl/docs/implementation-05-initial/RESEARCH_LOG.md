# Tessl — Stage 2 research log

## Resumed by user — 2026-10-25 America/Bogota, authentication pending

The user supplied a new Google account and explicitly authorized resuming Tessl with Google Cloud project `project-d419b4aa-7c3b-4fde-932` (SDD Comparison LAST MILE), retaining requested model `gemini-3.5-flash`. This is a project/account transition, not a change of requested model. The researcher launcher now targets that project and an isolated `gcloud-tetris-last-mile` credential profile outside the workspace. No password, OAuth code, refresh/access token or credential file is copied into experiment evidence or the Google Doc. The old launcher is retained by hash in transition-20261025/.

Gcloud's Google sign-in reached OAuth consent. Automatic review rejected the Allow action because the SDK asks for broad Google Cloud/App Engine/Cloud SQL/Compute permissions. Explicit user approval was requested; no bypass, model generation or application/spec edit was performed while approval is pending. Native `tessl whoami` exits 1 with authentication required; remote skills/search success is not claimed. Pinned Tessl executable hash matches 0.112.0 and Gemini CLI reports 0.60.0. Local plugin context remains available. The before-last-mile-20261025 checkpoint preserves the pre-resumption source/spec state.

Historical metrics remain: two closed launch attempts; known CLI405.215s, input574303 including cache409971, candidate output8458, thought12390, API19 requests/2 errors/17 successes. Session02 incomplete counters remain unknown. The first post-transition invocation must retry the pending preimplementation specification correction, preserving the full common seed and native source authorship boundary.

The existing Windows quota monitor was reactivated Ready/PT1H under the new user instruction. Its obsolete Codex executable path was corrected after an app update. All37 decision controls passed and a live dry run returned continue with84% five-hour/95% weekly remaining; no suspension was performed. The duplicate Codex heartbeat remains paused. These setup checks are outside Tessl generation metrics. Evidence: shared/quota-monitor/reactivation-20261025.json and events.jsonl.

## Paused by user — 2026-10-21 14:43 America/Bogota

Historical pause; superseded by the user-authorized resumption above. Current generation is waiting for OAuth scope approval, not for a new task authorization.

The user explicitly paused Tessl and BMAD until new Google credentials are supplied, and authorized continuing Kiro with its independent credits. No further Gemini/Tessl generation will be launched during this pause. Invocation `02-specify-correction` ended at 14:40:27 with exit 403 after 5.813 seconds; the actual Google response is `PERMISSION_DENIED / BILLING_DISABLED`. The user describes the account's credits as exhausted; the observed API error is retained precisely rather than relabeled as a token-count measurement.

Two closed launch attempts are preserved, with one observed model invocation: 405.215 seconds of instrumented CLI time. Known usage from session 01 is 574,303 input tokens, including 409,971 cached tokens, 8,458 candidate/output tokens and 12,390 thought tokens. Known API counters are 19 requests, 2 errors and 17 successes; session 02 lacks complete counters and remains explicitly unknown. There are 17 deduplicated token-bearing JSONL responses. No application source or inherited specification changed. New Stage 2 specifications exist, but their requested review correction and implementation remain pending. This is not a completed Tessl implementation.

The transcript archive and metrics.json were refreshed at the transition. The account login tab had been handed to the user before this pause; login does not authorize resuming generation without the user's new credentials/instruction.

## Status at 2026-10-21 09:37 America/Bogota

Stage 2 specification generation is running as `01-specify`. Implementation has not started. This log separates observed evidence, model self-reports and checks that remain pending. No Git branch, commit, push or repository upload is authorized or performed by this workflow.

## Experimental controls

- The complete shared English seed is unchanged: file SHA256 `63919779DD4104076FBABCB130CE296A160FA840E0B4755A2AA5D90757ADA8EF`; extracted normalized block SHA256 `60D6728689CD5CDAD7B1A386F95DAD4E34850EB5DE0AAB92E837D630DFD2B55A`.
- `01-effective-input-verification.json` verifies the first actual user message equals the intended full 6,506-character prompt, including every seed paragraph. A launch command alone is not treated as proof of effective input.
- Gemini CLI 0.60.0 requests `gemini-3.5-flash` through Vertex AI. Observed auxiliary models, API attempts/errors, cached/input/output/thought tokens and unknown fields will be recorded separately from the requested model.
- Tessl's actual pinned executable is 0.112.0, SHA256 `FD96BD5F832F4832DED7F238B74AA705C2404ACA4B488BE3B282472F26911AFA`. The npm bootstrap is 0.108.0 and is not the executed runtime. Automatic binary replacement is disabled by the pinned MCP environment.
- The inherited workflow uses Gemini with Tessl MCP and vendored plugin context. This installation has no native specification/build generator. New project specifications belong in `specs/stage2`; inherited specifications remain the historical baseline. Actual MCP calls and results will be audited, including failures.
- Only Gemini may modify application source, generated tests or feature specifications, after specification revision. Researcher helpers, environment replication and evidence capture are outside generated-source measurements.

## Unchanged starting baseline

`prepare-tessl-stage2.py` copied 48 files from Tessl's own Stage 1; dependencies, caches, old docs, Git, credentials and reparse points were excluded. Three skills junctions were recreated to point into the new Stage 2 vendored plugins. Source baseline: 19 files, 1,299 physical lines, 37,962 Unicode characters. Inherited specifications: 2 files, 136 lines, 10,093 characters. See the manifest and baseline metrics for exact paths and hashes.

Fresh backend verification: 9 tests passed with one inherited warning, 91% coverage (139/152 lines), XML in `baseline-coverage.xml`. The first attempt with shared Python failed during collection because `pydantic_settings` was absent; its original logs are retained as an environment failure. A Stage 2 owned virtual environment now matches all 51 installed packages from Tessl's own Stage 1 environment, using Python 3.12.14. The original environment remained unchanged. All 19 source files and both inherited specification hashes were verified before implementation.

Fresh frontend verification: npm ci succeeded, 2 tests passed and the production build passed. The baseline audit exited 1 with 7 reported vulnerabilities: 3 moderate, 2 high and 2 critical. These findings are not reported as a clean baseline. Exact commands, timestamps, outputs and exit statuses are retained in `baseline-*` files.

## Contract calibration and pending checks

Tessl's original `POST /api/games` status is HTTP 200, with two inherited regression assertions. The frozen seed preserves existing API compatibility and does not require HTTP 201. New researcher checker versions will take an explicit expected creation status; existing OpenSpec/Spec Kit checker files and historical results will be preserved. No application or legacy assertion should be changed merely to satisfy a checker calibrated to another tool.

Preserve Tessl's `active_piece` field, spawn origin (0,3), canonical unrotated shapes and row-zero locking terminal rule. A terminal lock that makes no spawn attempt must not invent a preview draw. Three- and four-row scoring cases require explicitly labeled isolated domain fixtures because ordinary unrotated pieces have height at most two.

Pending: completed Stage 2 specifications and review; implementation; independent functional/browser/concurrency checks; final XML/LCOV coverage, build, dependency audit; exact-task controlled SonarQube quality gate; complete session metrics and screenshots; final evidence corpus and Google Docs publication.

## Energy monitoring

Before starting Tessl, the user-authorized Windows task `Codex-Quota-Hourly-Suspend-Kevin` was registered hourly under the current user, with limited privileges and no wake-from-sleep. It reads Codex quota through the local app-server account RPC without a model turn. A known exhausted window triggers normal Windows suspension; failed, unknown or malformed readings do not. No shutdown, forced application closure or credential export is used.

The first actual scheduled-task invocation completed successfully at 09:27 America/Bogota: 29% remained in the five-hour window and 28% weekly, so no suspension occurred. Actual suspension has not been tested because the exhaustion condition has not occurred. The equivalent native Codex heartbeat is paused to prevent duplicate checks. Raw monitoring evidence is under `shared/quota-monitor`.

## Sonar baseline and publication — 2026-10-25

Own source/spec hashes were reverified:42/42 match across Stage1/Stage2; no generated application or feature-specification edits. Sonar26.9.0.129388 baseline project tetris-stage2-tessl/version1.0: CE6d7b7337-a783-49ed-912a-89302d344136 SUCCESS, analysis3480bd39-8d0a-4490-94c1-be6164d420b9. Coverage60.4%, duplication0%, bugs0, inherited smells14, inherited vulnerability1 (python:S2245 random.choice), hotspots0, debt72min, complexity86/cognitive69, ncloc788/lines970; ratings reliabilityA/securityC/maintainabilityA. Baseline gateOK has zero evaluated new-code conditions; it is not Stage2 acceptance. No frontend baselineLCOV. A first researcher scanner launch failed on argument grouping (Unexpected argument1.0), before analysis; retained original logs, corrected grouping and successful retry. No application change or finding suppression. Built-in gate unchanged; controlled gate requires newcoverage80%, newduplication3%, newviolations0.

Tessl baseline uses unseeded global random.choice; production sequence is not claimed fixed. Future deterministic researcher fixtures use seed20260929 or explicit canonical piece sequences without changing generated source. The shared English prompt seed stays unchanged.

The existing quota task completed a normal run at11:10:30 Bogota with LastTaskResult0; the11:13 automatic event also records continue/actionnone. Google Doc publication/readback verified: resumption section plus baseline metrics and one researcher-derived screenshot (18total inline images). Export55pages; new pages54-55 rendered and inspected, no clipping/overlap. Publication IDs/hashes are retained in transition-20261025/. OAuth consent remains pending explicit approval after automatic review rejection. No new-project Gemini call has been launched.

## 2026-10-25 — implementation in progress (researcher observation)

OAuth completed after explicit approval; isolated Google profile/project verified. Actual new-project sessions 03 and 04 requested/reported gemini-3.5-flash. Historical auth-pending entries above remain chronology, not current status. Closed known totals through 04: CLI 702.847 seconds; input including cache 1,338,659; cached input 817,045; output 30,376; thoughts 35,455; API attempts/errors/success 40/2/38. Failed 02 counters remain unknown. No final 05 usage is inferred while its invocation is open.

05 started 2026-10-25T20:33:44.593931Z. First native spec edit 20:34:47.712Z precedes first application edit 20:37:40.269Z. Later internal quality corrections require a separate ordering audit; no blanket claim of compliance is made. Original pieces.py hash reverified unchanged during implementation.

Sonar analysis 525346aa-6227-4aae-ab52-46450cc09cc0 was SUCCESS with gate ERROR: new coverage82.2%, new duplication0%, new violations5. Original current artifacts are rolling paths; observed failed attempts were copied under sonar-attempts. The researcher scanner adapter now archives its prior current artifacts before a new scan (infrastructure only; no source/feature edit). Earlier unarchived scan history must be recovered from retained native tool output where possible and marked partial if unavailable.

Prepared external domain harness17 records and interface concurrency harness6 tests; not executed while model edits are active. Harness preparation initially failed because the installed Vitest package exports ./config.default rather than ./config.import.default; corrected researcher helper only, no generated source changed. Preserve this as an instrumentation failure, not an application test failure.

The same Google Doc now contains the implementation progress checkpoint and explicitly provisional Sonar findings. Codex quota suspension task remains enabled; no real suspension was triggered for testing. No Git mutations or uploads performed.
