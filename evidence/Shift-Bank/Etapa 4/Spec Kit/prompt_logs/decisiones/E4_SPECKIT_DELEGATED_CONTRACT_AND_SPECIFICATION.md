# E4 Spec Kit — Delegated Contract Authorization and Specification Record

**Date:** 2026-11-16  
**Workspace:** `Shift-Bank/Etapa 4/Spec Kit/`  
**Feature:** `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/`  
**Authority type:** Prospective researcher delegation in the E4-SK-03 conversation. This is not a recovered historical D-01–D-14 approval record.

## Researcher authorization source

The researcher instructed the supervising assistant:

> “tienes que poder tomar la decision siguiendo ese documento de lo que ya se hizo, y no podemos estar en muchas iteraciones con codex y tu. La idea es que saquemos la etapa 4 rapido”

The researcher then authorized specification and planning using the existing Stage 4 documentation and supplied the exact prospective COP/USD compatibility contract in the E4-SK-03 instruction. The scope authorizes specification/planning only. It does not grant Gate B or authorize implementation, test execution, migration, Docker, load testing, or deployment.

## Recorded prospective compatibility contract

1. Preserve `acc_checking_123` and `acc_savings_456`, COP 5,000,000.00 and COP 15,000,000.00 baseline values, transaction history, and monetary integrity; never reinterpret COP as USD.
2. Add `CHK-1001` USD 2,500.00; `SAV-2001` USD 10,000.00; `EUR-3001` EUR 0.00; and `GBP-4001` GBP 0.00 idempotently and without overwriting financial data.
3. Enforce one fixed currency per account; COP is a retained legacy exception.
4. Apply D-03 for USD/EUR/GBP: backend Decimal, frontend BigInt minor units, rational FX, two-decimal strings, one final ROUND_HALF_UP, no financial floats/fees; no invented COP rate.
5. Internal transfers remain same-currency; USD/EUR/GBP conversions use `/api/conversions`; COP is excluded absent an approved rate.
6. Preserve COP per-operation/daily limits COP 5,000,000 / 10,000,000 and MFA at or above COP 1,000,000. Apply USD-equivalent operation/daily limits USD 5,000 / 10,000 to USD/EUR/GBP; MFA only strictly above unrounded USD 1,000.
7. Preserve COP ACH and recurring as D-08 compatibility exceptions; USD ACH follows reference; EUR/GBP ACH is unsupported; internal recurring is same-currency.
8. Apply D-05, D-06, D-09–D-14: append-only events; atomic synchronous CQRS projections; deterministic replay; correct version increments and ACH refunds; separate currency dashboards; AES-GCM; HMAC audit; deployment compatibility; UUID idempotency and optimistic concurrency.
9. Display COP separately; exclude it from any estimated USD dashboard total without an approved conversion rate.
10. Preserve inherited functionality. Document and plan client/test adaptation for mandatory idempotency/version request-contract changes rather than weakening D-13/D-14.

These are prospective adaptations to the supplied reference, not a claim of exact identity with any other tool's implementation or specifications. Original standalone SEED-4 master provenance and original full D-01–D-14 approval records remain unavailable. The extracted SEED-4 copy is operative; its SHA-256 is `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`.

## Native workflow and outcome

Applied project-local Codex skills in native order: `$speckit-clarify` (no material unanswered business clarification under the supplied contract), `$speckit-specify`, `$speckit-plan`, `$speckit-tasks`, `$speckit-checklist`, and read-only `$speckit-analyze`. No specification generation command was used to bypass the skills, and `$speckit-implement` was not invoked.

Artifacts in the active feature directory: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/api.md`, `contracts/events.md`, `tasks.md`, `checklists/requirements.md`, and `checklists/contract-review.md`. The specification contains 27 FRs, REQ-01–REQ-06 traceability, D-01–D-14 traceability, 42 numbered acceptance scenarios plus three supplemental inherited acceptance criteria (AC-43–AC-45). Task plan has 68 unique future tasks. The 24-item contract-review checklist remains unchecked for researcher review. All tasks are planning only. No application code or tests were written or run.

Supplemental inherited requirements made explicit during cross-artifact review: ACH settlement eligibility delay and beneficiary identifier formats; recurring cadence/date semantics; and the inherited load-test profile. Their AC and task references are in the feature artifacts.

## Baseline and inventory evidence

- E4-SK-01 manifest: 105 entries. Current rehash observed 95 exact matches and 10 mismatches. The 10 are the nine native Codex integration-managed paths documented by E4-SK-02 plus `.specify/feature.json`, the active feature pointer. No other manifest entry differed. The 10 are tool configuration/state changes, not application changes.
- Added for this milestone: the ten documentation files listed above, all under the new `specs/004-*` feature directory. No existing baseline source, test, constitution, inherited E1–E3 artifact, seed, or integration file was edited in this milestone.
- Git branch observed: `ShiftBank`; HEAD: `ebf1017748928b30a9a5ad68a56b9b532f304e86`. Scoped `git status` showed the ten new feature artifacts as untracked. Repository-wide status also displayed pre-existing E3 dirty/untracked paths and a permission-denied warning for historical E3 temporary directories; those were not opened or modified.

## Commands and validation

- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks` — succeeded; active `FEATURE_DIR` resolves to the 004 feature; docs include research, data model, contracts, quickstart, tasks.
- `specify --version` — `specify 1.0.6`.
- `specify integration status` — OK; default Codex; Gemini and Codex installed; multi-install safe; modified managed files 0; missing managed files 0; invalid manifest paths 0; unchecked manifests 0.
- `codex.cmd --version` — `codex-cli 0.168.0`.
- Read-only baseline rehash — 105 entries, 95 MATCH, 10 expected integration/feature-pointer mismatches as identified above.
- Read-only artifact checks — 27 FR definitions, all six REQ IDs and D-01–D-14 present in traceability, 68 unique task definitions, 45 total acceptance criteria; no TODO/TKTK/FIXME markers (the checklist's literal clarification-marker check is explanatory text, not an unresolved marker).
- `.specify/extensions.yml` absent; no extension hooks were configured.
- No test, build, migration, Docker, Locust, SonarQube, or deployment command was run.

## D1–D5 telemetry

- **D1 Effort:** effective model N/D; session JSONL, token in/cache/out, cost, measured elapsed time, and tool-call telemetry N/D. Codex CLI and Spec Kit CLI versions are recorded above.
- **D2 Code quality:** application LOC/diff, SonarQube, coverage, complexity, duplication, and debt are N/A/not measured because no application code changed and no analyzer/tests ran.
- **D3 Specifications:** one functional spec (`spec.md`, 182 physical lines); accompanying plan/design/contracts/checklists are listed above and remain draft/planning artifacts.
- **D4 Functional:** no implementation acceptance tests executed; all functional outcomes remain NOT VERIFIED.
- **D5 Human interventions:** one researcher delegation/contract authorization in the E4-SK-03 conversation, recorded above; original approval records remain unavailable.

## Gate status

The delegated authorization supports the specification/planning milestone. Researcher review of the draft artifacts remains required. Gate B is NOT granted. No implementation or tests are authorized by this record.
