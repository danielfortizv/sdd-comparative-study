# Shift Bank Stage 4 — GitHub Spec Kit Preparation

**Status:** PREP ONLY — baseline copied; human review required before measured discovery or specification authoring.  
**Attribution:** Prepared by GitHub Copilot as repository/setup assistant. This is not a measured Stage 4 agent session.  
**Date:** 2026-11-16

## Executive readiness

The Stage 4 Spec Kit workspace and a separate evidence structure have been created without modifying E3. The E3 worktree snapshot copied 105 files (1,279,387 bytes); all 105 copied-file SHA-256 values match the source, destination, and source recheck recorded in `BASELINE_FILES_SHA256.tsv`.

This is **not approval to begin measured discovery**. Gate A remains blocked pending human decisions on the COP/USD baseline, confirmation of the E3 snapshot, and access to authoritative source/approval records. Gate B remains pending. No E4 functional specification, test, or implementation was authored; no tests, Docker, Locust, SonarQube, or measured-agent workflow were run.

## Instructions and source material

Read in full:

- `Etapa 4/_preparacion_investigador/SHIFT_BANK_E4_SPECKIT_PREPARACION/00_README.md`
- `.../01_COPILOT_PROMPT_PREPARATION.md`
- `.../02_D01_D14_REFERENCE.md`
- `.../03_BASELINE_METRICS_CHECKLIST.md`
- `.../SEED-4.md`

The prompt also names authoritative research PDFs/DOCX, an E3 protocol DOCX, an E2 common-contract Markdown file, the standalone approved `SEED-4(1).md`, and full D-01–D-14 approval records. A filename search under `C:\Users\danie\Documents2` did not find those sources. They are **MISSING**, not inferred from the packet. The supplied D-01–D-14 file is explicitly a summary/reference, not an approval record.

The packet seed's SHA-256 is `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`, matching the hash declared by the packet. The non-authoritative `Etapa 4/_experiment_logs/Tessl/SEED-4.md` has the same hash. The standalone approved master was not found, so exact comparison against the authoritative original remains **NOT VERIFIED**. Neither seed file was changed.

## Source provenance and Git state at copy

- Source: `Shift-Bank/Etapa 3/Spec Kit/`
- Destination: `Shift-Bank/Etapa 4/Spec Kit/`
- Repository branch: `ShiftBank`, tracking `origin/ShiftBank`
- Repository HEAD: `82f3795a0ec4e834967f5f97a6f2e380c8bc57d1`, dated 2026-11-16; subject `SpecKit etapa 2`
- Source was **not a clean commit snapshot**. The baseline is the exact current E3 working-tree content at copy time, not an assertion that HEAD contains all E3 changes.
- Pre-existing tracked diffs: `backend/tests/conftest.py` (23 insertions/47 deletions), `deployment/smoke_test.py` (17/2), `scripts/generate_deployment_secrets.py` (13/6), and E3 experimental `E3_SPECKIT_BITACORA_EXPERIMENTAL.md` (1,194/1).
- Pre-existing untracked E3 artifacts included four `.sb-h810-*` directories, `reports/`, and `scripts/run_isolated_docker_smoke.py`. The E3 metrics register and E4 preparation packet were also untracked before this copy. No files in E1, E2, or E3 were changed by this preparation.
- Git status emitted three `Permission denied` warnings while enumerating existing E3 `.pytest-h8-*` directories. They were not opened, altered, or permission-adjusted.

### Copy inventory and exclusions

| E4 baseline area | Files |
|---|---:|
| `.gemini` | 10 |
| `.specify` | 21 |
| `specs` (Stages 1–3) | 25 |
| `backend` | 24 |
| `frontend` | 15 |
| `deployment` | 6 |
| `scripts` | 3 |
| `.gitignore` | 1 |
| **Total** | **105** |

Copied files are listed in `BASELINE_FILES_SHA256.tsv`. The manifest records relative path, source/destination paths, source and destination SHA-256, a source recheck hash, and match status. Verification: **105/105 MATCH; 0 mismatches**.

Excluded, preserved in E3, and not opened for sensitive contents:

- 22 directories: `.venv`, `node_modules`, `dist`, `.scannerwork`, caches, temporary directories, four `.sb-h810-*` H8–H10 scratch directories, E3 `reports/` (including H9 outputs), `locust/reports/`, `backend/certs/`, and three inaccessible `.pytest-h8-*` directories.
- Four files: `backend/shift_bank.db`, `backend/test_load_bank.db`, `deployment/docker.env`, and the H8–H10 helper `scripts/run_isolated_docker_smoke.py`.
- Generated logs, certificates/private-key extensions, database/WAL/SHM extensions, `.env` files except safe `.env.example`, and `.npmrc` credentials were filtered by the copy procedure.
- Safe `deployment/.env.example` was copied. The E4 workspace has no E3 database, deployment secret file, certificate directory, `.venv`, `node_modules`, `dist`, or experiment reports.

The original E3 code, evidence, databases, and scratch artifacts remain in place. E3 Locust and H9 reports were not copied into the E4 implementation tree; their original paths are retained for historical reference.

## Native Spec Kit and inherited functionality

- The copied project contains native `.specify/` assets, `.gemini/commands/`, a Gemini integration manifest at version **1.0.6**, and a workflow registry describing `specify → plan → tasks → implement` with review gates. The local `specify --version` also reported **1.0.6**.
- Existing native specification directories: `specs/001-shift-bank-stage1/`, `002-shift-bank-stage2/`, and `003-shift-bank-stage3/`. No `004-*` E4 specification directory was created.
- E3 Stage 3 implementation documents encryption of sensitive browser requests using AES-GCM/RSA-OAEP, authenticated at-rest field encryption and legacy plaintext migration, HMAC-chained append-only audit records, Locust load testing, and FastAPI/React deployment through Docker Compose and Nginx HTTPS. Inherited flows include accounts/history, internal transfers, simulated MFA, ACH settlement/failure/refund, dynamic limits, and recurring schedules.
- E3 source seeds accounts `acc_checking_123` / Checking / **COP 5,000,000.00** and `acc_savings_456` / Savings / **COP 15,000,000.00**. Seed history includes COP 500,000.00 and COP 100,000.00 internal transfers. Default limits are **COP 5,000,000.00 per operation** and **COP 10,000,000.00 daily**. Backend code requires MFA for amounts **greater than or equal to COP 1,000,000.00**.
- The actual E3 API includes accounts/history, transfers/MFA, ACH, beneficiaries, limits, recurring schedules, crypto public key, audit verification/records, health, and test-only endpoints. The inspected E3 storage/schema has encrypted monetary data and an audit ledger; Stage 4's separate durable domain-event store and CQRS projections are new work, not assumed to exist in E3.
- The current E3 `spec.md` says `Status: Draft`, while the E3 acceptance review and H9 evaluation report completion. The HEAD subject also says `SpecKit etapa 2` although the E3 tree exists. These provenance/status differences require researcher review; they are not silently normalized here.

## COP/USD contract conflict — unresolved

The inherited E3 implementation and its specification use COP. The supplied E4 decision summary assumes a different USD/EUR/GBP contract:

- **D-01/D-02:** E3 has two COP accounts and existing IDs/balances. The reference expects `CHK-1001` USD 2,500.00, `SAV-2001` USD 10,000.00, plus zero-balance EUR and GBP accounts.
- **D-07:** E3 defaults are COP 5,000,000 per operation / COP 10,000,000 daily and MFA at `>= COP 1,000,000`. The reference instead specifies USD-equivalent limits of 5,000/10,000 and MFA strictly above an unrounded USD equivalent of 1,000.
- No approved COP-to-USD mapping or FX rate for inherited balances/limits is available. Converting, relabeling, or replacing any seed/limit would change the research baseline.

**Researcher must choose and document a prospective reconciliation before Gate A.** Recommended single question: *Should Stage 4 preserve the inherited COP accounts, balances, limits, and MFA semantics with explicitly approved compatibility rules, or use the D-02/D-07 USD/EUR/GBP reference with a researcher-approved migration/mapping and declared deviation?* No choice has been made.

Full original D-01–D-14 decisions are also missing. The pending-review file records the supplied summaries without treating them as approved for Spec Kit.

## Historical E3 evidence (not E4 baseline results)

The following are historical E3 claims and references only; no Stage 4 test or scan was run:

- `specs/003-shift-bank-stage3/checklists/acceptance_review.md` and E3 `reports/h9-01-final-experimental-evaluation.md` report **97/97 backend**, **13/13 frontend**, production build PASS, and isolated Docker smoke **9/9**. The E3 HITO 0 checkpoint separately recorded 47 inherited backend tests and 12 frontend tests. These are different E3 checkpoints/scopes; none is a fresh E4 result.
- E3 H9 reports three Locust attempts; its third attempt is reported at 30 users/60 seconds, read p95 138.84 ms, transfer p95 357.77 ms, zero unexpected errors, and COP 600,000,000.00 conservation. Results are not rerun or imported as E4 measurements.
- Validated E3 Sonar JSON reports Quality Gate `OK`, 6,204 NCLOC, 3 bugs, 1 vulnerability, 70 code smells, 0.0% duplication, 508 minutes technical debt, and 0.0 reported coverage. Coverage import/scope metadata is unverified, and the gate export has an empty conditions list. These values are not Stage 4 quality results.
- `Etapa 3/_experiment_logs/Spec Kit/registro_metricas_sesion_gemini_e3.md` summarizes two Gemini sessions. Its reported input/cache/output totals are 49,384,049 / 46,515,753 / 177,120 and 110,724,586 / 104,170,281 / 153,613 tokens respectively; costs are N/D. The register cites screenshots, but raw Gemini/Codex JSONL and those screenshots were not found in the accessible E3 tree. No raw session archive is claimed.

## Environment observed

| Component | Observed version/result |
|---|---|
| OS version / architecture | Windows version `10.0.26300.0`, x64 |
| PowerShell | 5.1.26100.9818 |
| Python | 3.13.2 |
| E3 virtualenv packages (inspection only) | FastAPI 0.163.1; pytest 9.2.0; Uvicorn 0.54.0 |
| Node.js / npm | 20.17.0 / 11.6.3 |
| Git | 2.48.1.windows.1 |
| VS Code | 1.146.0 |
| Spec Kit CLI / Gemini integration | `specify` 1.0.6 / 1.0.6 |
| Gemini CLI | 0.65.0 |
| Future measured model | **N/D — not selected or confirmed** |

The historical continuity candidate is **Gemini CLI 0.65.0 with the copied Spec Kit Gemini integration 1.0.6**, because the E3 integration and E3 metric register identify Gemini. This is a recommendation for researcher review, not authorization or a final agent selection; the model is N/D and must be explicitly selected. The code CLI's filtered extension listing showed no matching Copilot/Spec Kit/Gemini extension version. No model was inferred from the E3 session register. Gemini CLI was queried for its version only; no measured session was started. Copilot performed this preparation and must not be attributed as the measured Stage 4 agent.

## Baseline verification

E4 baseline test status is **NOT RUN**. The E4 copy intentionally excludes the E3 `.venv` and `frontend/node_modules`; the preparation contract forbids dependency installation. E3's historical test results do not prove E4 tests. See `BASELINE_TESTS.md` for exact commands that remain unexecuted and the safe-run rationale.

Other non-destructive checks:

| Check | Result |
|---|---|
| E4 `Spec Kit` and E4 Spec Kit evidence destination before setup | Absent; safe to create |
| Seed SHA-256 vs packet declaration | Match; standalone approved original unavailable |
| E3→E4 copied-file hashes | 105/105 matches; 0 mismatches |
| Sensitive DB/key/env/dependency/test output exclusions | Confirmed absent from E4 copy |
| E3 Git status after copy | Same pre-existing E3 modified/untracked paths; no E3 changes caused by preparation |
| E4 Stage 4 spec/feature/tests | None authored |
| E3/E2/E1 writes, tests, Docker, Locust, SonarQube, dependency install | None |

## D1–D5 measurement and traceability plan

1. **D1 Effort:** preserve each measured-agent prompt/session ID and transcript; record model, input/cache/output tokens separately, cost only from a documented source, messages, tool calls, active/wall time, and changed LOC. Keep Copilot setup separate from the measured agent; unavailable values remain N/D.
2. **D2 Quality:** use the same source scope and analyzer/coverage provenance across E3/E4; record LOC/diff LOC, Sonar findings/ratings, debt, complexity, duplication, and coverage import. The existing E3 report is historical and has coverage provenance limitations.
3. **D3 Specifications:** count only approved native Spec Kit specification artifacts, not preparation notes, seed, README, tasks, or evidence. Freeze counting rules, file/line counts, atomic requirements, density, code-to-spec ratio, and distribution before comparison.
4. **D4 Functional:** map each common REQ-01–REQ-06 and approved inherited acceptance scenario to observed evidence; classify PASS/FAIL/NOT VERIFIED and keep extras separate.
5. **D5 Human interventions:** log each intervention in sequence with issue, severity/relevance, researcher correction, resulting spec update, deviation, and transcript/test evidence. Do not combine tool attributions.

## Preparation checklist and gates

| Item | Status |
|---|---|
| Read all five supplied Markdown files | PASS |
| Confirm source/destination and no prior E4 Spec Kit target | PASS |
| Copy current E3 worktree snapshot with explicit exclusions | PASS, with dirty-source provenance recorded |
| Verify copied SHA-256 manifest | PASS, 105/105 |
| Exclude DBs, credentials, certs, dependency/cache/build outputs and H8/H9 scratch | PASS |
| Preserve E3 source/evidence and avoid previous-stage writes | PASS |
| Create separate E4 evidence directories | PASS |
| Inspect E3 functionality and native Spec Kit workflow | PASS, read-only |
| Inspect runtime/CLI versions | PASS; future model N/D |
| Verify standalone seed/original D-01–D-14 approvals and referenced PDFs/DOCX | BLOCKED — MISSING |
| Resolve COP/USD baseline and D-07 thresholds | BLOCKED — researcher decision |
| Fresh E4 baseline tests/build | NOT RUN — see `BASELINE_TESTS.md` |
| Prepare native Spec Kit plan and next prompt proposal | PASS, proposal only |
| Gate A approval | PENDING |
| Gate B implementation approval | PENDING |

**Readiness:** the physical baseline/evidence setup is prepared, but the measured Stage 4 experiment is **NOT READY**. Stop for researcher review. Do not start discovery, clarification, specification authoring, implementation, or measured-agent execution until Gate A is explicitly approved. Do not implement until the separate Gate B is approved.
