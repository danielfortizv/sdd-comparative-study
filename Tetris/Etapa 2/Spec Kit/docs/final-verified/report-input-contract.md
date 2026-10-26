# Final report helper: evidence contract

Researcher helper: `../shared/build-spec-kit-report.py`. It reads local evidence and never runs app tests, servers, scanners, models, repository actions or Drive mutations. It does not generate a final corpus.

- `--check` validates and prints all blockers without writing `FINAL_REPORT.md`.
- Default mode writes the Spanish final report only when validation succeeds.
- Do not use default mode while QA is open. A previous passing snapshot is not final acceptance of later source changes.

## Inputs

| Artifact | Required shape or scope |
| --- | --- |
| `metrics.json` | Current collector output: source/spec hashes, net deltas, densities, per-run usage, correction attempts/intents/retries/process outcomes. Closed labels must match actual run metadata; no open started label. Historical failed attempts remain visible and are not relabeled completed fixes. Resumed 12 usage requires interval/response-ID scope verification before CLI totals can be added; unmatched CLI totals use the explicitly limited main-JSONL fallback. |
| `input-audit.json` | Every closed invocation; complete effective first input for initial implementation and code-producing corrections. Earlier delivery deviations remain visible. Exact intended-submission matches are recorded separately from the first user-like record, which may contain synthetic/replayed CLI context. |
| `13-input-replay-verification.json` | Specific no-application-work resume13 exception: hashed raw evidence proves the exact intended prompt with complete seed preceded its first token response. CLI response empty, only update_topic,0/0 changed-line statistics. Its first-record seed flag stays false. This exception cannot approve a code-producing correction with missing first-input seed. |
| `question-audit.json` | Every closed invocation, no pending labels, observed blocking count with interrupted/failed-session limits preserved. The through-08 baseline is frozen. New main text requires explicit manual adjudication with response/session IDs, timestamps, hashes and evidence snippets; resumed history is interval-bounded and deduplicated. |
| `environment.json` | Recorded versions/model/seed. |
| `verification-commands.json` | Existing four independent commands with exit code 0, nonempty logs, start timestamps after the last app/test/config change. |
| `backend-coverage.log`, `frontend-test-coverage.log`, `frontend-build.log`, `npm-audit.json` | Canonical original command outputs. The helper verifies test-pass text and zero audit vulnerabilities; coverage is reported from raw logs, not model prose. |
| `acceptance-api.json` | Unchanged common checker: its seven passing records covering eight distinct catalog IDs. |
| `acceptance-matrix.json` | List or `rows`/`cases`/`scenarios`: exactly 20 unique IDs; each row has `id`, `status: pass`, `mechanism`, `evidence` as existing path(s). Three/four rows need an explicit isolated-domain label or flag. Evidence may use `path::test_name` or `path#anchor`. |
| `acceptance-contract.json` | Supplemental S2-16 overall `status: pass`, nine passing `controls`; these do not add catalog IDs. |
| `acceptance-provenance.json` | Actual schema supported: `backend_app_files: [{path, sha256}]`, `checker_files: [{path, sha256}]`, `backend_origin`, `base_url`. Every current backend/app Python file and both shared checker hashes must match. Older map/hash aliases are optional. |
| `browser-evidence.json` | `observations` list of passed records; `captures: [{path, caption, kind, raw_sources?}]`; at least one `actual_ui` image. Other kinds: `actual_cli`, `actual_sonar`, `derived_panel`. Derived panels require existing raw sources and are never called native UI screenshots. |
| `sonar-verification.json`, `sonar-exact-task.json`, `sonar-exact-quality-gate.json`, `sonar-task.json` | Existing exact-analysis helper output. Latest queue empty, exact task SUCCESS, matching analysis/task IDs, project key, unchanged 80/3/0 gate conditions, gate OK and current report-task hash. Scan must postdate production changes. |
| `sonar-summary.json`, `sonar-open-issues.json` | Matching current quality summary, zero open issues/bugs/vulnerabilities/hotspots/smells. Production-only scope remains separate from source counts including tests/config. |
| XML and LCOV | Current `docs/coverage.xml` and `frontend/coverage/lcov.info`, both matching the verifier's input hashes. |
| `bertopic-corpus/final/manifest.json` | A separately prepared final Markdown-only corpus, current source/copy/unified hashes. Pre-QA corpus does not satisfy this requirement. No BERTopic modelling is implied. |
| `generation-08/metrics.json` | Frozen original baseline hashes for Stage 1 preservation checks and the earlier self-report/quality comparison. |

JSON statuses use `pass`; Sonar's native gate statuses use `OK`/`SUCCESS`. Relative evidence paths are resolved against docs, the tool directory and Stage 2. Missing, failed, stale or incomplete checks block final writing and are listed as errors. All source/spec hashes must still match the metrics snapshot.

The report includes per-session tokens and known/unknown time, API attempts/errors/successes versus JSONL responses, auxiliary roles, artifact density/net/QA deltas, categorized external correction attempts versus distinct QA intents, retries and process outcomes, seed/version provenance, tests/coverage/audit, Sonar gate/ratings/debt, the 20-case mechanism map, screenshots/raw sources and attribution/scalability limits. Terminal429 and network fetch failures are retained separately from unknown attempt/error aggregates. A resumed single-model CLI interval can include an empty JSONL record with no model label only when all token sums and successful-call counts match exactly and no record names another model; the raw missing label stays visible. The report preserves generation-08 self-report limitations and does not repeat any generator claim of being universally robust or ready for deployment.

If Sonar's web UI still requires login and there is no `actual_sonar` capture, the report states that limitation and attributes metrics to the authenticated local API. No UI login or password is needed by this helper.
