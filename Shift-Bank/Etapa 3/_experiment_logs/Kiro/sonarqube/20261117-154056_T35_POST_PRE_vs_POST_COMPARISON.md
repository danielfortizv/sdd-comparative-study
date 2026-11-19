# T35 — SonarQube FINAL/POST verification & PRE→POST comparison (Shift Bank Stage 3, Kiro)

**Purpose:** Read-only evidence consolidation comparing the frozen **PRE-remediation** scan (T32)
with the researcher-gated **POST-remediation** scan (T35). No scan was re-run, no application code
was modified, no tests were re-run, and no value was fabricated — every figure below traces to a
preserved raw file in this directory (`Etapa 3/_experiment_logs/Kiro/sonarqube/`).

- **PRE evidence prefix:** `20261117-143156_T32_PRE_`
- **POST evidence prefix:** `20261117-154056_T35_POST_` (+ staged config/coverage copies `20261117-154056_T35_*`)
- **Note generated (local):** 2026-11-17 15:40:56
- **SonarQube server:** Community Build 26.9.0.129388 · Scanner CLI 8.1.0.6389 (both runs)

---

## 1. Analysis identity & Compute Engine task (both SUCCESS)

Sources: `..._PRE_ce_task.json`, `..._POST_ce_task.json`.

| Field | PRE (T32) | POST (T35) |
|---|---|---|
| CE task id | `104e3187-6709-49a3-a6fb-60d8c2ca5263` | `e36a0259-5d05-4e0f-9284-4c2057cca02a` |
| Task type | REPORT | REPORT |
| Status | **SUCCESS** | **SUCCESS** |
| analysisId | `b330beea-9010-4b1c-b036-6f61d6ac6675` | `1f9cb39d-4247-4c27-826e-0bc22be409d7` |
| componentKey | `Shift-Bank---Stage-3---Kiro` | `Shift-Bank---Stage-3---Kiro` (identical) |
| componentId | `47a1d7c4-2b29-43a2-bd27-f92defc7349e` | `47a1d7c4-2b29-43a2-bd27-f92defc7349e` (identical) |
| componentName | `Shift Bank Etapa 3 (Kiro)` | `Shift Bank Etapa 3 (Kiro)` |
| submitter | admin | admin |
| executedAt | 2026-11-17T19:33:31+0000 | 2026-11-17T20:42:33+0000 |
| warningCount | 1 (SCM autodetection — benign) | 1 (SCM autodetection — benign) |

Both analyses live under the **same project** (identical `componentKey` + `componentId`), so PRE and
POST compare **1:1** on the same SonarQube component.

---

## 2. Scope comparability — CONFIRMED (identical analysis scope)

Sources: `..._PRE_scanner.log`, `..._POST_scanner.log`. The scanner "Project configuration" block is
**byte-identical** across the two runs.

**Excluded sources (both runs):**
```
**/node_modules/**, **/dist/**, **/.venv/**, **/__pycache__/**, **/*.db, frontend/vite.config.ts,
backend/app/seed.py, backend/tests/**/*.py, frontend/src/**/*.test.ts, frontend/src/**/*.test.tsx,
frontend/src/**/*.spec.ts, frontend/src/**/*.spec.tsx
```

**Included tests (both runs):**
```
backend/tests/**/*.py, frontend/src/**/*.test.ts, frontend/src/**/*.test.tsx,
frontend/src/**/*.spec.ts, frontend/src/**/*.spec.tsx
```

**Coverage exclusions (both runs):** `backend/tests/**, frontend/src/**/*.test.*, frontend/src/**/*.spec.*`

| Scope dimension | PRE | POST |
|---|---|---|
| Project key | `Shift-Bank---Stage-3---Kiro` | `Shift-Bank---Stage-3---Kiro` |
| Languages detected | 3 in 76 preprocessed files | 3 in 76 preprocessed files |
| Files indexed | 75 | 75 |
| Files ignored (incl/excl patterns) | 51 | 51 |
| Quality profiles | css / py / ts = "Sonar way" | css / py / ts = "Sonar way" |
| Backend coverage imported | `Parsing report '/usr/src/backend/coverage.xml'` | `Parsing report '/usr/src/backend/coverage.xml'` |
| Frontend coverage imported | `Analysing [/usr/src/frontend/coverage/lcov.info]` | `Analysing [/usr/src/frontend/coverage/lcov.info]` |
| Python source files analyzed | 60 | 60 |
| TS source files analyzed | 15 | 15 |
| Final result | ANALYSIS SUCCESSFUL / EXECUTION SUCCESS | ANALYSIS SUCCESSFUL / EXECUTION SUCCESS |

**Verdict: scope is identical** (same key, same exclusions/inclusions, both coverage reports imported,
same language/file counts). The PRE→POST deltas below are attributable to the T34 corrective pass, not
to a scope change.

---

## 3. PRE vs POST metrics (traditional + MQR, with deltas)

Sources: `..._PRE_measures.json`, `..._POST_measures.json`.

### 3.1 Traditional metrics

| Metric | PRE | POST | Δ |
|---|---:|---:|---:|
| bugs | 0 | 0 | 0 |
| vulnerabilities | 0 | 0 | 0 |
| security_hotspots | 0 | 0 | 0 |
| **code_smells** | **172** | **131** | **−41** |
| reliability_rating | A (1.0) | A (1.0) | unchanged |
| security_rating | A (1.0) | A (1.0) | unchanged |
| security_review_rating | A (1.0) | A (1.0) | unchanged |
| sqale_rating (maintainability) | A (1.0) | A (1.0) | unchanged |
| **sqale_index (total debt)** | **831 min** (~13h51m) | **617 min** (~10h17m) | **−214 min (~3h34m)** |
| sqale_debt_ratio | 0.6% | 0.4% | −0.2 pp |
| reliability_remediation_effort | 0 | 0 | 0 |
| security_remediation_effort | 0 | 0 | 0 |
| duplicated_lines_density | 0.0% | 0.0% | unchanged |
| coverage | 44.1% | 44.4% | +0.3 pp |
| line_coverage | 44.2% | 44.4% | +0.2 pp |
| branch_coverage | 31.8% | 31.8% | unchanged |
| ncloc | 4,970 | 5,000 | +30 |
| cognitive_complexity | 449 | 440 | −9 |
| complexity | 659 | 666 | +7 |
| files | 40 | 40 | unchanged |
| lines_to_cover | 3,585 | 3,608 | +23 |
| uncovered_lines | 2,000 | 2,005 | +5 |
| ncloc language distribution | css=313; py=2,909; ts=1,748 | css=313; py=2,939; ts=1,748 | py +30 |

### 3.2 MQR (Multi-Quality Rule) metrics

| MQR metric | PRE | POST | Δ |
|---|---:|---:|---:|
| software_quality_maintainability_rating | A (1.0) | A (1.0) | unchanged |
| software_quality_security_rating | A (1.0) | A (1.0) | unchanged |
| software_quality_reliability_rating | **C (3.0)** | **C (3.0)** | **still C** |
| software_quality_maintainability_remediation_effort | 811 min | 597 min | −214 min |
| software_quality_reliability_remediation_effort | 205 min | 20 min | −185 min |
| software_quality_security_remediation_effort | 0 | 0 | 0 |
| software_quality_maintainability_debt_ratio | 0.5% | 0.4% | −0.1 pp |

**Reading:** overall code quality improved materially — **41 fewer smells** and **214 fewer minutes of
maintainability debt**, with MQR reliability effort dropping from 205→20 min. All ratings stayed at **A**
except the **MQR reliability rating, which remains C (3.0)** — it did not improve to B/A because one
RELIABILITY:MEDIUM finding (regex backtracking, S8786) still exists after the corrective pass (see §4).
The small increases in ncloc/lines/complexity (+30 ncloc, +7 complexity) reflect the behavior-preserving
refactors (extracted helper functions, a module-level SQL constant, and explicit-spacing JSX markers)
introduced by T34; they are expected and are not regressions.

---

## 4. Issue resolution breakdown (authoritative, via the resolved filter)

Sources: `..._POST_issues_RESOLVED.json` (resolved=true), `..._POST_issues_UNRESOLVED.json`
(resolved=false), `..._POST_issues_p1_with_facets.json`.

- **POST UNRESOLVED total = 131** — matches `code_smells = 131` exactly.
- **POST RESOLVED total = 42 — ALL `resolution = FIXED`** (`status = CLOSED`).

### 4.1 RESOLVED (42) by rule — exactly the 42 T34 targets

| Rule | Count | Description |
|---|---:|---|
| typescript:S6772 | 37 | Explicit spacing between inline JSX elements |
| python:S3776 | 3 | Cognitive Complexity ≤ 15 (audit.py, config.py, crypto.py) |
| python:S1192 | 1 | Define a constant instead of duplicating a literal (repository.py) |
| typescript:S8786 | 1 | Regex super-linear backtracking (AccountsPanel.tsx:14) |
| **Total** | **42** | all `resolution=FIXED` |

### 4.2 Scoped-rule verification against UNRESOLVED (POST)

| Scoped rule | PRE count | POST UNRESOLVED | Status |
|---|---:|---:|---|
| python:S3776 | 3 | 0 | fully resolved |
| python:S1192 | 1 | 0 | fully resolved |
| typescript:S6772 | 37 | 0 | fully resolved |
| typescript:S8786 | 1 | **1** | fixed-but-new-appeared (see §4.3) |

### 4.3 ⚠ S8786 caveat — 1 FIXED, 1 NEW (NOT net-resolved)

The T34 regex correction **closed the original S8786** at
`frontend/src/components/AccountsPanel.tsx:14` — confirmed `resolution=FIXED`, `status=CLOSED`,
closeDate `2026-11-17T20:41:18+0000` in `..._POST_issues_RESOLVED.json`.

However, the POST scan flagged a **NEW S8786** at
`frontend/src/components/AccountsPanel.tsx:17` — confirmed `status=OPEN`, `issueStatus=OPEN`,
creationDate `2026-11-17T20:41:18+0000` (created during this POST analysis), issue key
`69307daa-a793-4b7c-a338-9cdcb248593a`, in `..._POST_issues_UNRESOLVED.json`. The replacement regex
`/\d(?=(?:\d{3})+$)/g` still triggers the super-linear-backtracking rule (RELIABILITY:MEDIUM).

**Therefore S8786 is NOT net-resolved.** Net outcome: **41 of the 42 targeted findings are confirmed
FIXED and stay fixed; the S8786 correction was superseded by a new equivalent finding** (1 fixed + 1
new of the same rule). This single remaining S8786 is why the MQR reliability rating stays at C and is
the one `new_violation` in the Quality Gate (§6).

---

## 5. Remaining 131 UNRESOLVED — summary (deliberately out of T34 scope)

Source: `..._POST_issues_UNRESOLVED.json` (rule tally over the 131 open issues).

| Rule | Count | Area | Note |
|---|---:|---|---|
| python:S9073 | 86 | backend/tests | Composite assertions should be split (test-only; lowest priority) |
| python:S9083 | 12 | backend/tests | Pytest decorator parentheses (test-only) |
| python:S5778 | 8 | backend/tests | One method invocation per exception test (test-only) |
| typescript:S6759 | 8 | frontend/src | React props should be read-only |
| python:S8410 | 5 | backend/app | Use `Annotated` for FastAPI DI |
| python:S5713 | 3 | backend/app | Redundant exception class already caught |
| typescript:S3358 | 2 | frontend/src | Extract nested ternary |
| **typescript:S8786** | **1** | frontend/src | **NEW regex finding at AccountsPanel.tsx:17 (see §4.3)** |
| python:S1135 | 1 | backend/app | Complete the TODO comment |
| python:S107 | 1 | backend/app | Too many function parameters |
| python:S8409 | 1 | backend/app | Redundant FastAPI `response_model` |
| python:S9100 | 1 | backend/tests | Remove useless `yield` (test-only) |
| typescript:S7721 | 1 | frontend/src | TS rule (singleton) |
| typescript:S6819 | 1 | frontend/src | Prefer semantic element |
| **Total** | **131** | | matches `code_smells=131` |

The remaining set is dominated by test-only smells (`python:S9073 ×86`, plus S9083/S5778/S9100 =
107 test-only findings) that T34 deliberately left untouched, plus a handful of low-severity
backend/frontend production smells and the single new S8786. There are **0 bugs, 0 vulnerabilities,
0 security hotspots** in either scan.

---

## 6. Quality Gate — PRE vs POST, with new-code-gate explanation

Sources: `..._PRE_quality_gate.json`, `..._POST_quality_gate.json`.

### 6.1 PRE Quality Gate — OK
```json
{"projectStatus":{"status":"OK","conditions":[],"ignoredConditions":false,"caycStatus":"compliant"}}
```
PRE passed because it was the **first analysis**: there is no new-code baseline, so the default
"Sonar way" gate (which evaluates *new code*) had **no conditions to evaluate**. The 172 PRE findings
are overall-code debt and do not fail the new-code gate.

### 6.2 POST Quality Gate — ERROR (on new-code conditions)
```json
{"projectStatus":{"status":"ERROR","conditions":[
  {"status":"ERROR","metricKey":"new_coverage","comparator":"LT","errorThreshold":"80","actualValue":"39.7"},
  {"status":"OK","metricKey":"new_duplicated_lines_density","comparator":"GT","errorThreshold":"3","actualValue":"0.0"},
  {"status":"ERROR","metricKey":"new_violations","comparator":"GT","errorThreshold":"0","actualValue":"1"}],
  "ignoredConditions":false,"period":{"mode":"PREVIOUS_VERSION","date":"2026-11-17T19:32:10+0000"},
  "caycStatus":"compliant"}}
```

| Condition | Threshold | Actual | Status |
|---|---|---:|---|
| new_coverage | ≥ 80% | 39.7% | **ERROR** |
| new_duplicated_lines_density | ≤ 3% | 0.0% | OK |
| new_violations | ≤ 0 | 1 | **ERROR** |

**Explanation (reported without spin).** The POST gate is the **Clean-as-You-Code (CAYC) NEW-CODE gate**.
Its comparison period is `PREVIOUS_VERSION` dated `2026-11-17T19:32:10+0000` — i.e. it measures only the
lines **changed/added since the PRE analysis**, not the whole codebase. It fails for two reasons:

1. **new_coverage 39.7% < 80%** — the lines touched by the corrective pass are not well covered by tests.
   This is driven by the frontend, which has only the 3 Task-30 smoke tests (frontend line coverage ~2.78%);
   the JSX spacing edits sit in components with near-zero test coverage, so the new-code coverage falls short.
2. **new_violations 1 > 0** — exactly the one **new S8786** finding at `AccountsPanel.tsx:17` (§4.3).

`caycStatus` is **compliant** (the gate itself is the standard CAYC gate). Crucially, the gate ERROR is
about **new-code hygiene**, not a regression of existing functionality: overall code quality **improved**
(−41 smells, −214 min debt, MQR reliability effort 205→20 min), all existing ratings stayed A (except the
MQR reliability C that persists because of the surviving S8786), and there are still 0 bugs / 0
vulnerabilities / 0 hotspots. Both facts hold simultaneously: **the project got cleaner overall, and the
new-code gate failed on coverage of changed lines + the one new regex finding.**

---

## 7. POST raw evidence inventory (full)

All files are preserved under `Etapa 3/_experiment_logs/Kiro/sonarqube/`.

| File | Contents |
|---|---|
| `20261117-154056_T35_POST_ce_task.json` | CE task: SUCCESS + analysisId `1f9cb39d-…` + componentKey/Id |
| `20261117-154056_T35_POST_measures.json` | POST project measures (traditional + MQR) |
| `20261117-154056_T35_POST_quality_gate.json` | POST Quality Gate (ERROR, new-code conditions) |
| `20261117-154056_T35_POST_issues_p1.json` | Issues page 1 |
| `20261117-154056_T35_POST_issues_p1_with_facets.json` | Issues + facet aggregations (total 173 incl. closed) |
| `20261117-154056_T35_POST_issues_UNRESOLVED.json` | 131 unresolved issues (= code_smells) |
| `20261117-154056_T35_POST_issues_RESOLVED.json` | 42 resolved issues, all FIXED |
| `20261117-154056_T35_POST_scanner.log` | POST scanner stdout — ANALYSIS/EXECUTION SUCCESS |
| `20261117-154056_T35_backend_coverage.xml` | Staged backend Cobertura report imported by the POST scan |
| `20261117-154056_T35_frontend_lcov.info` | Staged frontend LCOV report imported by the POST scan |
| `20261117-154056_T35_original_coverage.xml` | Staged original backend coverage copy |
| `20261117-154056_T35_properties.txt` | Staged scanner properties used for the POST scan |

---

## 8. Verified vs. the one limitation

**Verified (traces to preserved raw files):**
- Both analyses are SUCCESS on the same project (same componentKey + componentId). [§1]
- Analysis scope is identical PRE↔POST (exclusions, inclusions, both coverage reports, file/language counts). [§2]
- Overall improvement: code_smells 172→131 (−41); sqale_index 831→617 min (−214); cognitive_complexity 449→440;
  MQR maintainability effort 811→597; MQR reliability effort 205→20. [§3]
- 42 issues resolved, all FIXED, matching exactly the T34 targets (S6772×37, S3776×3, S1192×1, S8786×1). [§4]
- Scoped rules S3776, S1192, S6772 fully resolved (0 unresolved each). [§4.2]
- 131 unresolved = the deliberately out-of-scope set (test-dominated) + 1 new S8786. [§5]
- Ratings unchanged: traditional reliability/security/security_review/maintainability all A; MQR maintainability A,
  security A, reliability C(3.0); bugs/vulnerabilities/hotspots 0 in both. [§3]
- Quality Gate: PRE OK (no new-code baseline); POST ERROR on new_coverage 39.7<80 and new_violations 1>0. [§6]

**The one limitation (reported honestly):**
- **S8786 is NOT net-resolved.** The original finding at `AccountsPanel.tsx:14` was FIXED/CLOSED, but the
  replacement regex produced a **NEW** S8786 at `AccountsPanel.tsx:17` (OPEN). Net = 41/42 scoped findings
  confirmed fixed-and-staying-fixed; the S8786 correction was superseded by an equivalent new finding. This
  single finding keeps the MQR reliability rating at C and is the one `new_violation` failing the new-code gate.
  Per researcher instruction, no further corrective pass was performed.

---

## 9. PRE evidence integrity

All frozen `20261117-143156_T32_PRE_*` files (and the PRE index
`20261117-143156_T32_PRE_EVIDENCE_INDEX_and_SUMMARY.md`) are **unchanged** by this T35 consolidation.
This note is additive, read-only evidence; no PRE file was overwritten, and no scan/test was re-run.

**Decisions D-E3-01..D-E3-04 preserved.** No application code changed during this task.
